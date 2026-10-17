// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <QFileSystemWatcher>
#include <QObject>
#include <QString>
#include <QTimer>

class KStatusNotifierItem;

/**
 * Icon in the system tray (catholic-background-settings --tray), started at
 * login when the option is on. It does not download anything: it watches
 * ~/.config/catholicbackgroundrc, where the provider writes the data of each
 * new image, shows them in its tooltip and notifies when the image changes.
 */
class Tray : public QObject
{
    Q_OBJECT

public:
    explicit Tray(QObject *parent = nullptr);

    /** Whether the option is on (General/TrayIcon in catholicbackgroundrc). */
    static bool enabled();
    /** Turns the option on or off: autostart file, and starts the icon now. */
    static void setEnabled(bool enabled);

private:
    void onConfigChanged();
    void updateTooltip();
    void notify();
    void openSettings();
    void refresh();
    QString configPath() const;

    KStatusNotifierItem *m_item = nullptr;
    QFileSystemWatcher m_watcher;
    QTimer m_reload;
    QString m_hash;
    QString m_reason;
    QString m_title;
    QString m_author;
};
