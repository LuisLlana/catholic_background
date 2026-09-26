// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#include "catholicbackgroundprovider.h"

#include <QColor>
#include <QCryptographicHash>
#include <QDate>
#include <QDateTime>
#include <QGuiApplication>
#include <QImage>
#include <QMargins>
#include <QPainter>
#include <QScreen>
#include <QJsonDocument>
#include <QJsonObject>
#include <QUrlQuery>

#include <KConfigGroup>
#include <KIO/StoredTransferJob>
#include <KPluginFactory>
#include <KSharedConfig>

namespace
{
/// Size of the image to compose: the primary screen, in physical pixels.
QSize targetSize()
{
    if (const QScreen *screen = QGuiApplication::primaryScreen()) {
        const QSize size = screen->size() * screen->devicePixelRatio();
        if (size.isValid() && !size.isEmpty()) {
            return size;
        }
    }
    return QSize(1920, 1080);
}

qreal devicePixelRatio()
{
    const QScreen *screen = QGuiApplication::primaryScreen();
    return screen ? screen->devicePixelRatio() : 1.0;
}

QColor averageColor(const QImage &image)
{
    const QImage small = image.scaled(64, 64, Qt::IgnoreAspectRatio, Qt::SmoothTransformation).convertToFormat(QImage::Format_RGB32);
    qint64 r = 0, g = 0, b = 0;
    for (int y = 0; y < small.height(); ++y) {
        const auto *line = reinterpret_cast<const QRgb *>(small.constScanLine(y));
        for (int x = 0; x < small.width(); ++x) {
            r += qRed(line[x]);
            g += qGreen(line[x]);
            b += qBlue(line[x]);
        }
    }
    const qint64 n = qint64(small.width()) * small.height();
    return QColor(int(r / n), int(g / n), int(b / n));
}

/// The image enlarged to cover the whole canvas, blurred and slightly darkened.
QImage blurredBackground(const QImage &image, const QSize &size)
{
    QImage cover = image.scaled(size, Qt::KeepAspectRatioByExpanding, Qt::SmoothTransformation);
    cover = cover.copy((cover.width() - size.width()) / 2, (cover.height() - size.height()) / 2, size.width(), size.height());

    // Blur: shrink to a few pixels and enlarge again in smooth steps, so that
    // only the colors remain (independent of the screen resolution).
    const int tinyWidth = 16;
    const QSize tiny(tinyWidth, qMax(1, tinyWidth * size.height() / size.width()));
    QImage result = cover.scaled(tiny, Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
    while (result.width() * 4 < size.width()) {
        result = result.scaled(result.size() * 2, Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
    }
    result = result.scaled(size, Qt::IgnoreAspectRatio, Qt::SmoothTransformation).convertToFormat(QImage::Format_RGB32);

    QPainter painter(&result);
    painter.fillRect(result.rect(), QColor(0, 0, 0, 70));
    return result;
}

/// The whole image, as big as possible without cropping it, inside the part of
/// the screen not covered by panels, on top of the chosen background (which
/// covers the whole screen). Margins are in logical pixels.
QImage compose(const QImage &image, const QString &mode, const QColor &color, const QMargins &panelMargins)
{
    const QSize size = targetSize();
    const qreal dpr = devicePixelRatio();
    QRect area(QPoint(0, 0), size);
    const QRect free = area.marginsRemoved(QMargins(qRound(panelMargins.left() * dpr),
                                                    qRound(panelMargins.top() * dpr),
                                                    qRound(panelMargins.right() * dpr),
                                                    qRound(panelMargins.bottom() * dpr)));
    // Ignore absurd margins (e.g. from another screen layout)
    if (free.width() >= size.width() / 2 && free.height() >= size.height() / 2) {
        area = free;
    }

    QImage canvas;
    if (mode == QLatin1String("color")) {
        canvas = QImage(size, QImage::Format_RGB32);
        canvas.fill(color.isValid() ? color : QColor(Qt::black));
    } else if (mode == QLatin1String("average")) {
        canvas = QImage(size, QImage::Format_RGB32);
        canvas.fill(averageColor(image));
    } else {
        canvas = blurredBackground(image, size);
    }

    // Largest size that keeps the proportions and fits entirely in the free
    // area, whether the image is bigger or smaller than the screen.
    const QImage fitted = image.scaled(area.size(), Qt::KeepAspectRatio, Qt::SmoothTransformation);
    QPainter painter(&canvas);
    painter.setRenderHint(QPainter::SmoothPixmapTransform);
    painter.drawImage(area.x() + (area.width() - fitted.width()) / 2, area.y() + (area.height() - fitted.height()) / 2, fitted);
    return canvas;
}
}

CatholicBackgroundProvider::CatholicBackgroundProvider(QObject *parent, const KPluginMetaData &data, const QVariantList &args)
    : PotdProvider(parent, data, args)
{
    KSharedConfigPtr config = KSharedConfig::openConfig(QStringLiteral("catholicbackgroundrc"));
    // plasmashell may keep this configuration open: read the latest values
    config->reparseConfiguration();
    const KConfigGroup group = config->group(QStringLiteral("General"));
    QUrl url(group.readEntry("Url", QStringLiteral(DEFAULT_WALLPAPER_URL)));

    if (!url.isValid()) {
        // Queued so that whoever created us is already connected to the signal
        QMetaObject::invokeMethod(this, [this] { Q_EMIT error(this); }, Qt::QueuedConnection);
        return;
    }

    // Timestamp of today's midnight in the user's local time
    const qint64 ts = QDate::currentDate().startOfDay().toSecsSinceEpoch();

    // Keep any query parameters already present in the configured URL
    QUrlQuery query(url);
    query.removeAllQueryItems(QStringLiteral("ts"));
    query.addQueryItem(QStringLiteral("ts"), QString::number(ts));
    url.setQuery(query);

    m_background = group.readEntry("Background", QStringLiteral("blur"));
    m_backgroundColor = QColor::fromString(group.readEntry("BackgroundColor", QStringLiteral("#000000")));
    // Space taken by panels on the primary screen (written by the settings application)
    m_panelMargins = QMargins(group.readEntry("PanelLeft", 0), group.readEntry("PanelTop", 0), group.readEntry("PanelRight", 0), group.readEntry("PanelBottom", 0));

    const QString info = group.readEntry("InfoUrl", QString());
    if (!info.isEmpty()) {
        m_infoUrl = QUrl(info);
    }

    // The URL is unique per day, so the cache can be used without getting yesterday's image.
    KIO::StoredTransferJob *job = KIO::storedGet(url, KIO::NoReload, KIO::HideProgressInfo);
    connect(job, &KIO::StoredTransferJob::finished, this, &CatholicBackgroundProvider::requestFinished);
}

void CatholicBackgroundProvider::requestFinished(KJob *_job)
{
    auto *job = static_cast<KIO::StoredTransferJob *>(_job);
    if (job->error()) {
        Q_EMIT error(this);
        return;
    }

    const QJsonDocument doc = QJsonDocument::fromJson(job->data());
    if (!doc.isObject()) {
        Q_EMIT error(this);
        return;
    }
    const QJsonObject obj = doc.object();

    // --- Image (base64, with or without a "data:image/...;base64," prefix) ---
    QByteArray base64 = obj.value(QStringLiteral("image")).toString().toLatin1();
    if (base64.startsWith("data:")) {
        const qsizetype comma = base64.indexOf(',');
        base64 = comma >= 0 ? base64.mid(comma + 1) : QByteArray();
    }
    const auto decoded = QByteArray::fromBase64Encoding(base64);
    if (!decoded) {
        Q_EMIT error(this);
        return;
    }
    const QImage image = QImage::fromData(*decoded);
    if (image.isNull()) {
        Q_EMIT error(this);
        return;
    }

    // Fingerprint of the image, so that the settings application can tell
    // whether the server has a different image later the same day
    KSharedConfigPtr config = KSharedConfig::openConfig(QStringLiteral("catholicbackgroundrc"));
    config->reparseConfiguration();
    KConfigGroup group = config->group(QStringLiteral("General"));
    group.writeEntry("CurrentImageHash", QString::fromLatin1(QCryptographicHash::hash(*decoded, QCryptographicHash::Sha1).toHex()));
    config->sync();

    // --- Metadata ---
    const QString title = obj.value(QStringLiteral("title")).toString().trimmed();
    // toVariant() accepts both "1889" and 1889
    const QString date = obj.value(QStringLiteral("date")).toVariant().toString().trimmed();
    m_author = obj.value(QStringLiteral("author")).toString().trimmed();

    // PotdProvider only has title and author, so the date goes next to the
    // title, museum-label style: "The Starry Night (1889)".
    if (!title.isEmpty() && !date.isEmpty()) {
        m_title = QStringLiteral("%1 (%2)").arg(title, date);
    } else {
        m_title = title.isEmpty() ? date : title;
    }

    Q_EMIT finished(this, compose(image, m_background, m_backgroundColor, m_panelMargins));
}

K_PLUGIN_CLASS_WITH_JSON(CatholicBackgroundProvider, "catholicbackgroundprovider.json")

#include "catholicbackgroundprovider.moc"
