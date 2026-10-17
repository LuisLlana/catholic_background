// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#include "tray.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QMenu>
#include <QProcess>
#include <QStandardPaths>

#include <KConfigGroup>
#include <KNotification>
#include <KSharedConfig>
#include <KStatusNotifierItem>

using namespace Qt::Literals::StringLiterals;

namespace
{
constexpr auto AUTOSTART_FILE = "catholic-background-tray.desktop";

KConfigGroup generalGroup()
{
    KSharedConfigPtr config = KSharedConfig::openConfig(u"catholicbackgroundrc"_s);
    config->reparseConfiguration();
    return config->group(u"General"_s);
}

QString autostartPath()
{
    return QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation) + "/autostart/"_L1 + QLatin1String(AUTOSTART_FILE);
}
}

bool Tray::enabled()
{
    return generalGroup().readEntry("TrayIcon", false);
}

void Tray::setEnabled(bool enabled)
{
    KConfigGroup group = generalGroup();
    group.writeEntry("TrayIcon", enabled);
    group.sync();

    // Started at every login while the option is on; a running icon quits by
    // itself when it sees the option off (it watches the configuration)
    const QString path = autostartPath();
    if (enabled) {
        QDir().mkpath(QFileInfo(path).absolutePath());
        QFile file(path);
        if (file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
            file.write("[Desktop Entry]\n"
                       "Type=Application\n"
                       "Name=Catholic Background\n"
                       "Comment=Icon in the system tray, with a notification when the image of the day changes\n"
                       "Exec=catholic-background-settings --tray\n"
                       "Icon=catholic-background\n"
                       "X-KDE-autostart-phase=2\n"
                       "NoDisplay=true\n");
        }
        QProcess::startDetached(QCoreApplication::applicationFilePath(), {u"--tray"_s});
    } else {
        QFile::remove(path);
    }
}

Tray::Tray(QObject *parent)
    : QObject(parent)
{
    m_item = new KStatusNotifierItem(u"catholic-background"_s, this);
    m_item->setCategory(KStatusNotifierItem::ApplicationStatus);
    m_item->setStatus(KStatusNotifierItem::Active);
    m_item->setIconByName(u"catholic-background"_s);
    m_item->setTitle(u"Catholic Background"_s);
    m_item->setStandardActionsEnabled(true);   // Quit

    auto *menu = new QMenu();
    menu->addAction(QIcon::fromTheme(u"catholic-background"_s), u"Open…"_s, this, &Tray::openSettings);
    menu->addAction(QIcon::fromTheme(u"view-refresh"_s), u"Refresh wallpaper"_s, this, &Tray::refresh);
    m_item->setContextMenu(menu);
    connect(m_item, &KStatusNotifierItem::activateRequested, this, &Tray::openSettings);

    const KConfigGroup group = generalGroup();
    m_hash = group.readEntry("CurrentImageHash", QString());
    m_reason = group.readEntry("CurrentReason", QString());
    m_title = group.readEntry("CurrentTitle", QString());
    m_author = group.readEntry("CurrentAuthor", QString());
    updateTooltip();

    // KConfig writes a new file and renames it: watch the folder too, and
    // read again a moment later (several writes usually come together)
    m_reload.setSingleShot(true);
    m_reload.setInterval(500);
    connect(&m_reload, &QTimer::timeout, this, &Tray::onConfigChanged);
    m_watcher.addPath(QFileInfo(configPath()).absolutePath());
    if (QFileInfo::exists(configPath())) {
        m_watcher.addPath(configPath());
    }
    connect(&m_watcher, &QFileSystemWatcher::directoryChanged, &m_reload, qOverload<>(&QTimer::start));
    connect(&m_watcher, &QFileSystemWatcher::fileChanged, &m_reload, qOverload<>(&QTimer::start));
}

QString Tray::configPath() const
{
    return QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation) + "/catholicbackgroundrc"_L1;
}

void Tray::onConfigChanged()
{
    if (QFileInfo::exists(configPath()) && !m_watcher.files().contains(configPath())) {
        m_watcher.addPath(configPath());
    }
    const KConfigGroup group = generalGroup();
    if (!group.readEntry("TrayIcon", false)) {
        QCoreApplication::quit();   // the option was turned off
        return;
    }
    const QString hash = group.readEntry("CurrentImageHash", QString());
    m_reason = group.readEntry("CurrentReason", QString());
    m_title = group.readEntry("CurrentTitle", QString());
    m_author = group.readEntry("CurrentAuthor", QString());
    updateTooltip();
    if (hash == m_hash) {
        return;
    }
    const bool first = m_hash.isEmpty();
    m_hash = hash;
    // A day chosen by hand with "Use as wallpaper" is not news
    if (!first && !group.hasKey("ShowDate")) {
        notify();
    }
}

void Tray::updateTooltip()
{
    m_item->setToolTipIconByName(u"catholic-background"_s);
    m_item->setToolTipTitle(m_reason.isEmpty() ? u"Catholic Background of the Day"_s : m_reason);
    QStringList lines;
    for (const QString &text : {m_title, m_author}) {
        if (!text.isEmpty()) {
            lines << text.toHtmlEscaped();
        }
    }
    m_item->setToolTipSubTitle(lines.join("<br>"_L1));
}

void Tray::notify()
{
    auto *notification = new KNotification(u"imageChanged"_s, KNotification::CloseOnTimeout);
    notification->setTitle(m_reason.isEmpty() ? u"New image of the day"_s : m_reason);
    QStringList parts;
    for (const QString &text : {m_title, m_author}) {
        if (!text.isEmpty()) {
            parts << text;
        }
    }
    notification->setText(parts.isEmpty() ? u"The wallpaper has changed."_s : parts.join(u" — "_s));
    notification->setIconName(u"catholic-background"_s);
    KNotificationAction *open = notification->addDefaultAction(u"Open"_s);
    connect(open, &KNotificationAction::activated, this, &Tray::openSettings);
    notification->sendEvent();
}

void Tray::openSettings()
{
    QProcess::startDetached(QCoreApplication::applicationFilePath(), {});
}

void Tray::refresh()
{
    QProcess::startDetached(QCoreApplication::applicationFilePath(), {u"--refresh"_s});
}
