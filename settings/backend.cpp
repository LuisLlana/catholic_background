// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#include "backend.h"

#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusPendingCallWatcher>
#include <QDBusPendingReply>
#include <QDate>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QCoreApplication>
#include <algorithm>
#include <QCryptographicHash>
#include <QLocale>
#include <QFileInfo>
#include <QGuiApplication>
#include <QImage>
#include <QJsonDocument>
#include <QJsonObject>
#include <QImageReader>
#include <QNetworkReply>
#include <QProcess>
#include <QScreen>
#include <QStandardPaths>
#include <QUrlQuery>

#include <KAboutData>
#include <KConfigGroup>
#include <KSharedConfig>

using namespace Qt::Literals::StringLiterals;

namespace
{
constexpr auto PROVIDER_ID = "catholicbackground";
constexpr auto POTD_PLUGIN = "org.kde.potd";
constexpr auto TEMP_PLUGIN = "org.kde.color";
constexpr int SWITCH_BACK_DELAY_MS = 500;
// Image.PreserveAspectFit: the provider already composes an image of the size
// of the screen, but if that ever does not match (several screens, fractional
// scaling, an old provider still loaded by plasmashell) the image must still be
// shown complete, never cropped.
constexpr int FILL_MODE = 1;
constexpr int DOWNLOAD_TIMEOUT_MS = 30000;
constexpr int DEFAULT_CHECK_INTERVAL = 30;  // minutes, as in catholic-background-update.timer
constexpr int MIN_CHECK_INTERVAL = 5;
constexpr int MAX_CHECK_INTERVAL = 24 * 60;
constexpr auto TIMER_UNIT = "catholic-background-update.timer";

/// "30 minutes", "1 hour", "2 hours", "90 minutes"
QString describeInterval(int minutes)
{
    if (minutes % 60 == 0) {
        return minutes == 60 ? u"hour"_s : u"%1 hours"_s.arg(minutes / 60);
    }
    return u"%1 minutes"_s.arg(minutes);
}

KConfigGroup configGroup()
{
    return KSharedConfig::openConfig(u"catholicbackgroundrc"_s)->group(u"General"_s);
}

/// Same URL the provider requests: base URL + ts = today's local midnight.
QUrl urlForToday(const QString &base)
{
    QUrl url(base);
    QUrlQuery query(url);
    query.removeAllQueryItems(u"ts"_s);
    query.addQueryItem(u"ts"_s, QString::number(QDate::currentDate().startOfDay().toSecsSinceEpoch()));
    url.setQuery(query);
    return url;
}

bool isValidServerUrl(const QUrl &url)
{
    return url.isValid() && (url.scheme() == "http"_L1 || url.scheme() == "https"_L1 || url.scheme() == "file"_L1)
        && (url.isLocalFile() || !url.host().isEmpty());
}
}

Backend::Backend(QObject *parent)
    : QObject(parent)
{
    const QString dir = QFileInfo(cachePath()).absolutePath();
    QDir().mkpath(dir);
    m_watcher.addPath(dir);
    connect(&m_watcher, &QFileSystemWatcher::directoryChanged, this, &Backend::onCacheChanged);

    m_timeout.setSingleShot(true);
    m_timeout.setInterval(DOWNLOAD_TIMEOUT_MS);
    connect(&m_timeout, &QTimer::timeout, this, [this] {
        finishRefresh(false,
                      u"Plasma did not download a new image in %1 seconds. Check that the server is reachable."_s.arg(DOWNLOAD_TIMEOUT_MS / 1000));
    });

    loadCachedInfo();
    checkInstallation();

    // The automatic check runs in another process (systemd timer)
    m_lastCheckTimer.setInterval(60 * 1000);
    connect(&m_lastCheckTimer, &QTimer::timeout, this, &Backend::lastCheckChanged);
    m_lastCheckTimer.start();
}

QString Backend::lastCheck() const
{
    KSharedConfigPtr config = KSharedConfig::openConfig(u"catholicbackgroundrc"_s);
    config->reparseConfiguration();
    const KConfigGroup group = config->group(u"General"_s);
    const QDateTime when = group.readEntry("LastCheck", QDateTime());
    if (!when.isValid()) {
        return u"The server is checked every %1."_s.arg(describeInterval(checkInterval()));
    }
    const QString time = when.date() == QDate::currentDate() ? QLocale().toString(when.time(), QLocale::ShortFormat)
                                                              : QLocale().toString(when, QLocale::ShortFormat);
    return u"The server is checked every %1. Last check at %2: %3"_s.arg(describeInterval(checkInterval()), time, group.readEntry("LastCheckResult", QString()));
}

QString Backend::problem() const
{
    return m_problem;
}

bool Backend::canRestartPlasma() const
{
    return m_canRestartPlasma;
}

void Backend::setProblem(const QString &problem, bool canRestart)
{
    if (m_problem != problem || m_canRestartPlasma != canRestart) {
        m_problem = problem;
        m_canRestartPlasma = canRestart;
        Q_EMIT problemChanged();
    }
}

void Backend::checkInstallation()
{
    // 1. Several copies of the provider: Plasma may load an old one
    QStringList copies;
    const QStringList libraryPaths = QCoreApplication::libraryPaths();
    for (const QString &dir : libraryPaths) {
        const QFileInfo file(dir + "/potd/plasma_potd_catholicbackgroundprovider.so"_L1);
        if (file.exists() && !copies.contains(file.canonicalFilePath())) {
            copies << file.canonicalFilePath();
        }
    }
    if (copies.size() > 1) {
        setProblem(u"There are %1 copies of the wallpaper provider installed and Plasma may be using an old one:\n%2\n"
                   "Remove the ones you do not use (for example with uninstall-user.sh) and restart Plasma."_s
                       .arg(copies.size())
                       .arg(copies.join("\n"_L1)),
                   true);
        return;
    }

    // 2. The cached image was not composed by this version of the provider:
    //    plasmashell is still running an older one.
    if (!m_busy && QFileInfo::exists(cachePath())) {
        const QSize cached = QImageReader(cachePath()).size();
        QSize expected;
        if (const QScreen *screen = QGuiApplication::primaryScreen()) {
            expected = screen->size() * screen->devicePixelRatio();
        }
        if (cached.isValid() && expected.isValid() && cached != expected) {
            setProblem(u"Plasma is using an older version of the wallpaper provider, so the image is not fitted to the "
                       "screen and the background options have no effect. Restart Plasma to load the installed version."_s,
                       true);
            return;
        }
    }

    setProblem(QString(), false);
}

void Backend::restartPlasma()
{
    // Plasma 6 runs plasmashell as a systemd user service; otherwise, replace it.
    const int result = QProcess::execute(u"systemctl"_s, {u"--user"_s, u"restart"_s, u"plasma-plasmashell.service"_s});
    if (result != 0) {
        QProcess::startDetached(u"plasmashell"_s, {u"--replace"_s});
    }
    setProblem(QString(), false);
    QTimer::singleShot(8000, this, &Backend::checkInstallation);
}

QString Backend::serverUrl() const
{
    return configGroup().readEntry("Url", defaultUrl());
}

QString Backend::defaultUrl() const
{
    return QStringLiteral(DEFAULT_WALLPAPER_URL);
}

QString Backend::background() const
{
    const QString value = configGroup().readEntry("Background", u"blur"_s);
    return (value == "average"_L1 || value == "color"_L1) ? value : u"blur"_s;
}

QColor Backend::backgroundColor() const
{
    const QColor color = QColor::fromString(configGroup().readEntry("BackgroundColor", u"#000000"_s));
    return color.isValid() ? color : QColor(Qt::black);
}

int Backend::checkInterval() const
{
    return std::clamp(configGroup().readEntry("CheckInterval", DEFAULT_CHECK_INTERVAL), MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL);
}

int Backend::defaultCheckInterval() const
{
    return DEFAULT_CHECK_INTERVAL;
}

void Backend::setCheckInterval(int minutes)
{
    minutes = std::clamp(minutes, MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL);
    KConfigGroup group = configGroup();
    group.writeEntry("CheckInterval", minutes);
    group.sync();

    // The systemd user timer reads the interval from a drop-in in the user's configuration
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation) + "/systemd/user/"_L1
        + QLatin1String(TIMER_UNIT) + ".d"_L1;
    const QString dropIn = dir + "/interval.conf"_L1;
    if (minutes == DEFAULT_CHECK_INTERVAL) {
        QFile::remove(dropIn);
        QDir().rmdir(dir);
    } else {
        QDir().mkpath(dir);
        QFile file(dropIn);
        if (file.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text)) {
            file.write(u"# Written by Catholic Background Settings\n"
                       "[Timer]\n"
                       "OnUnitActiveSec=\n"
                       "OnUnitActiveSec=%1min\n"_s.arg(minutes).toUtf8());
        }
    }
    QProcess::startDetached(u"sh"_s,
                            {u"-c"_s,
                             u"systemctl --user daemon-reload && systemctl --user try-restart %1"_s.arg(QLatin1String(TIMER_UNIT))});
    Q_EMIT checkIntervalChanged();
    Q_EMIT lastCheckChanged();
}

bool Backend::applySettings(const QString &url, const QString &background, const QColor &color, int checkInterval)
{
    if (checkInterval != this->checkInterval()) {
        setCheckInterval(checkInterval);
    }
    const bool urlChanged = url.trimmed() != serverUrl();
    const bool backgroundChanged = background != this->background() || (background == "color"_L1 && color != backgroundColor());

    if (urlChanged && !setServerUrl(url)) {
        return false;
    }
    if (backgroundChanged) {
        KConfigGroup group = configGroup();
        group.writeEntry("Background", background);
        group.writeEntry("BackgroundColor", color.name());
        group.sync();
        Q_EMIT this->backgroundChanged();
    }
    if (urlChanged || backgroundChanged) {
        refreshWallpaper();
    }
    return true;
}

QString Backend::cachePath() const
{
    return QStandardPaths::writableLocation(QStandardPaths::GenericCacheLocation) + "/plasma_engine_potd/"_L1 + QLatin1String(PROVIDER_ID);
}

QUrl Backend::imageUrl() const
{
    if (!QFileInfo::exists(cachePath())) {
        return {};
    }
    QUrl url = QUrl::fromLocalFile(cachePath());
    // Different URL on every change so that QML does not show the old image
    url.setQuery(u"v=%1"_s.arg(m_imageVersion));
    return url;
}

QString Backend::title() const
{
    return m_title;
}

QString Backend::author() const
{
    return m_author;
}

bool Backend::busy() const
{
    return m_busy;
}

QVariant Backend::aboutData() const
{
    return QVariant::fromValue(KAboutData::applicationData());
}

void Backend::setBusy(bool busy)
{
    if (m_busy != busy) {
        m_busy = busy;
        Q_EMIT busyChanged();
    }
}

void Backend::loadCachedInfo()
{
    m_title.clear();
    m_author.clear();
    QFile file(cachePath() + ".json"_L1);
    if (file.open(QIODevice::ReadOnly)) {
        const QJsonObject obj = QJsonDocument::fromJson(file.readAll()).object();
        m_title = obj.value("Title"_L1).toString();
        m_author = obj.value("Author"_L1).toString();
    }
    ++m_imageVersion;
    Q_EMIT imageChanged();
}

void Backend::onCacheChanged()
{
    loadCachedInfo();
    if (m_waitingForDownload && QFileInfo::exists(cachePath())) {
        finishRefresh(true, u"The wallpaper has been updated."_s);
    }
}

bool Backend::setServerUrl(const QString &url)
{
    const QString trimmed = url.trimmed();
    KConfigGroup group = configGroup();

    if (trimmed.isEmpty() || trimmed == defaultUrl()) {
        group.deleteEntry("Url");
    } else {
        if (!isValidServerUrl(QUrl(trimmed))) {
            return false;
        }
        group.writeEntry("Url", trimmed);
    }
    group.sync();
    Q_EMIT serverUrlChanged();
    return true;
}

void Backend::testConnection(const QString &url)
{
    if (m_busy) {
        return;
    }
    setBusy(true);
    checkServer(url, [this](bool ok, const QString &message, const QByteArray &) {
        setBusy(false);
        Q_EMIT testFinished(ok, message);
    });
}

void Backend::checkServer(const QString &url, const std::function<void(bool, const QString &, const QByteArray &)> &callback)
{
    const QUrl base(url.trimmed().isEmpty() ? defaultUrl() : url.trimmed());
    if (!isValidServerUrl(base)) {
        callback(false, u"The URL is not valid. It must start with http:// or https://."_s, {});
        return;
    }

    QNetworkRequest request(urlForToday(base.toString()));
    request.setTransferTimeout(DOWNLOAD_TIMEOUT_MS);
    QNetworkReply *reply = m_network.get(request);
    connect(reply, &QNetworkReply::finished, this, [reply, callback] {
        reply->deleteLater();

        if (reply->error() != QNetworkReply::NoError) {
            callback(false, u"Could not connect to the server: %1"_s.arg(reply->errorString()), {});
            return;
        }
        const QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) {
            callback(false, u"The server did not answer with JSON."_s, {});
            return;
        }
        const QJsonObject obj = doc.object();
        QByteArray base64 = obj.value("image"_L1).toString().toLatin1();
        if (base64.startsWith("data:")) {
            base64 = base64.mid(base64.indexOf(',') + 1);
        }
        const auto decoded = QByteArray::fromBase64Encoding(base64);
        const QImage image = decoded ? QImage::fromData(*decoded) : QImage();
        if (image.isNull()) {
            callback(false, u"The server answered, but the \"image\" field does not contain a valid image."_s, {});
            return;
        }

        QString description = obj.value("title"_L1).toString();
        const QString date = obj.value("date"_L1).toVariant().toString();
        if (!date.isEmpty()) {
            description += description.isEmpty() ? date : u" (%1)"_s.arg(date);
        }
        const QString author = obj.value("author"_L1).toString();
        if (!author.isEmpty()) {
            description += u", "_s + author;
        }
        if (description.isEmpty()) {
            description = u"an image without title"_s;
        }
        callback(true, u"Connection OK: %1 (%2×%3)."_s.arg(description).arg(image.width()).arg(image.height()),
                 QCryptographicHash::hash(*decoded, QCryptographicHash::Sha1).toHex());
    });
}

void Backend::evaluateScript(const QString &script, const std::function<void(bool, const QString &)> &callback)
{
    QDBusMessage message = QDBusMessage::createMethodCall(u"org.kde.plasmashell"_s,
                                                          u"/PlasmaShell"_s,
                                                          u"org.kde.PlasmaShell"_s,
                                                          u"evaluateScript"_s);
    message << script;
    auto *watcher = new QDBusPendingCallWatcher(QDBusConnection::sessionBus().asyncCall(message), this);
    connect(watcher, &QDBusPendingCallWatcher::finished, this, [callback](QDBusPendingCallWatcher *w) {
        w->deleteLater();
        const QDBusPendingReply<QString> reply = *w;
        if (reply.isError()) {
            callback(false, reply.error().message());
        } else {
            callback(true, reply.value().trimmed());
        }
    });
}

void Backend::refreshWallpaper()
{
    if (m_busy) {
        return;
    }
    setBusy(true);

    // Check the server before touching Plasma, so that a server that is down
    // does not leave the desktop without today's image.
    checkServer(serverUrl(), [this](bool ok, const QString &message, const QByteArray &) {
        if (!ok) {
            finishRefresh(false, message + u" The current wallpaper has been kept."_s);
            return;
        }
        updatePanelMargins([this] {
            doRefresh(false);
        });
    });
}

void Backend::updateIfChanged()
{
    if (m_busy) {
        return;
    }
    setBusy(true);
    m_recordCheck = true;

    checkServer(serverUrl(), [this](bool ok, const QString &message, const QByteArray &hash) {
        if (!ok) {
            finishRefresh(false, message + u" The current wallpaper has been kept."_s);
            return;
        }
        KSharedConfigPtr config = KSharedConfig::openConfig(u"catholicbackgroundrc"_s);
        config->reparseConfiguration();
        const QByteArray current = config->group(u"General"_s).readEntry("CurrentImageHash", QString()).toLatin1();
        if (hash == current && QFileInfo::exists(cachePath())) {
            finishRefresh(true, u"The image has not changed."_s);
            return;
        }
        updatePanelMargins([this] {
            doRefresh(true);
        });
    });
}

void Backend::updatePanelMargins(const std::function<void()> &done)
{
    // Space taken by the visible panels of the primary screen (screen 0), so
    // that the provider places the image where no panel covers it.
    const QString script = uR"JS(
var m = {top: 0, bottom: 0, left: 0, right: 0};
panels().forEach(function (p) {
    if (p.screen !== 0 || p.hiding === "autohide" || p.hiding === "dodgewindows") return;
    if (!(p.location in m)) return;
    var size = p.height + (p.floating ? 8 : 0);
    if (size > m[p.location]) m[p.location] = size;
});
print(JSON.stringify(m));
)JS"_s;

    evaluateScript(script, [this, done](bool ok, const QString &output) {
        const QJsonObject margins = QJsonDocument::fromJson(output.toUtf8()).object();
        KConfigGroup group = configGroup();
        // Without an answer from Plasma, keep the values saved last time
        if (ok && !margins.isEmpty()) {
            group.writeEntry("PanelTop", margins.value("top"_L1).toInt());
            group.writeEntry("PanelBottom", margins.value("bottom"_L1).toInt());
            group.writeEntry("PanelLeft", margins.value("left"_L1).toInt());
            group.writeEntry("PanelRight", margins.value("right"_L1).toInt());
            group.sync();
        }
        done();
    });
}

void Backend::doRefresh(bool automatic)
{
    // Plasma only downloads again when there is no cached image...
    QFile::remove(cachePath());
    QFile::remove(cachePath() + ".json"_L1);

    // ...and when the wallpaper is loaded again. Switch the desktops that use
    // our provider to another wallpaper and, after a short pause, back again
    // (doing both in the same script is not enough).
    const QString step1 = uR"JS(
var ids = [];
desktops().forEach(function (d) {
    if (d.wallpaperPlugin !== "%1") return;
    d.currentConfigGroup = ["Wallpaper", "%1", "General"];
    if (d.readConfig("Provider") !== "%2") return;
    d.wallpaperPlugin = "%3";
    ids.push(d.id);
});
print(ids.join(","));
)JS"_s.arg(QLatin1String(POTD_PLUGIN), QLatin1String(PROVIDER_ID), QLatin1String(TEMP_PLUGIN));

    evaluateScript(step1, [this, automatic](bool ok, const QString &output) {
        if (!ok) {
            finishRefresh(false, u"Could not talk to Plasma: %1"_s.arg(output));
            return;
        }
        if (output.isEmpty()) {
            // For automatic updates this is not an error: there is nothing to do
            finishRefresh(automatic, u"No desktop is using Catholic background of the day as wallpaper."_s);
            return;
        }

        QTimer::singleShot(SWITCH_BACK_DELAY_MS, this, [this, output] {
            const QString step2 = uR"JS(
"%1".split(",").forEach(function (id) {
    var d = desktopById(parseInt(id));
    if (!d) return;
    d.wallpaperPlugin = "%2";
    d.currentConfigGroup = ["Wallpaper", "%2", "General"];
    d.writeConfig("FillMode", %3);
});
)JS"_s.arg(output, QLatin1String(POTD_PLUGIN), QString::number(FILL_MODE));
            evaluateScript(step2, [this](bool ok, const QString &error) {
                if (!ok) {
                    finishRefresh(false, u"Could not talk to Plasma: %1"_s.arg(error));
                    return;
                }
                waitForDownload();
            });
        });
    });
}

void Backend::setAsWallpaper()
{
    if (m_busy) {
        return;
    }
    setBusy(true);
    updatePanelMargins([this] {
        doSetAsWallpaper();
    });
}

void Backend::doSetAsWallpaper()
{

    const QString script = uR"JS(
desktops().forEach(function (d) {
    d.wallpaperPlugin = "%1";
    d.currentConfigGroup = ["Wallpaper", "%1", "General"];
    d.writeConfig("Provider", "%2");
    d.writeConfig("FillMode", %3);
});
)JS"_s.arg(QLatin1String(POTD_PLUGIN), QLatin1String(PROVIDER_ID), QString::number(FILL_MODE));

    evaluateScript(script, [this](bool ok, const QString &error) {
        if (!ok) {
            finishRefresh(false, u"Could not talk to Plasma: %1"_s.arg(error));
            return;
        }
        if (QFileInfo::exists(cachePath())) {
            finishRefresh(true, u"Catholic background of the day is now your wallpaper."_s);
        } else {
            waitForDownload();
        }
    });
}

void Backend::waitForDownload()
{
    if (QFileInfo::exists(cachePath())) {
        finishRefresh(true, u"The wallpaper has been updated."_s);
        return;
    }
    m_waitingForDownload = true;
    m_timeout.start();
}

void Backend::finishRefresh(bool ok, const QString &message)
{
    m_waitingForDownload = false;
    m_timeout.stop();
    setBusy(false);

    if (m_recordCheck) {
        m_recordCheck = false;
        KConfigGroup group = configGroup();
        group.writeEntry("LastCheck", QDateTime::currentDateTime());
        group.writeEntry("LastCheckResult", message);
        group.sync();
        Q_EMIT lastCheckChanged();
    }
    checkInstallation();
    if (ok && !m_problem.isEmpty()) {
        Q_EMIT refreshFinished(false, m_problem);
        return;
    }
    Q_EMIT refreshFinished(ok, message);
}
