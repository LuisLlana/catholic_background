// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <QColor>
#include <QFileSystemWatcher>
#include <QNetworkAccessManager>
#include <QObject>
#include <QStringList>
#include <QTimer>
#include <QUrl>
#include <QVariant>

#include <functional>

/**
 * Logic of the settings application, exposed to QML as the "Backend" singleton.
 *
 * - Reads and writes the server URL in ~/.config/catholicbackgroundrc.
 * - Shows the image Plasma has cached for today (~/.cache/plasma_engine_potd/).
 * - Asks plasmashell (D-Bus scripting API) to download the image again or to
 *   use the provider as wallpaper.
 */
class Backend : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString serverUrl READ serverUrl NOTIFY serverUrlChanged)
    Q_PROPERTY(QString defaultUrl READ defaultUrl CONSTANT)
    Q_PROPERTY(QString background READ background NOTIFY backgroundChanged)
    Q_PROPERTY(QColor backgroundColor READ backgroundColor NOTIFY backgroundChanged)
    Q_PROPERTY(int checkInterval READ checkInterval NOTIFY checkIntervalChanged)
    Q_PROPERTY(int defaultCheckInterval READ defaultCheckInterval CONSTANT)
    Q_PROPERTY(QUrl imageUrl READ imageUrl NOTIFY imageChanged)
    Q_PROPERTY(QString title READ title NOTIFY imageChanged)
    Q_PROPERTY(QString author READ author NOTIFY imageChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(QVariant aboutData READ aboutData CONSTANT)
    Q_PROPERTY(QString problem READ problem NOTIFY problemChanged)
    Q_PROPERTY(QString lastCheck READ lastCheck NOTIFY lastCheckChanged)
    Q_PROPERTY(bool canRestartPlasma READ canRestartPlasma NOTIFY problemChanged)

public:
    explicit Backend(QObject *parent = nullptr);

    QString serverUrl() const;
    QString defaultUrl() const;
    /// How to fill the screen around the image: "blur", "average" or "color".
    QString background() const;
    QColor backgroundColor() const;
    /// Minutes between automatic checks of the server.
    int checkInterval() const;
    int defaultCheckInterval() const;
    QUrl imageUrl() const;
    QString title() const;
    QString author() const;
    bool busy() const;
    QVariant aboutData() const;
    /// Description of an installation problem that makes the settings have no effect, or empty.
    QString problem() const;
    /// Description of the last automatic check of the server.
    QString lastCheck() const;
    bool canRestartPlasma() const;

    /// Saves the URL (an empty string restores the default). Returns false if it is not valid.
    Q_INVOKABLE bool setServerUrl(const QString &url);
    /// Saves URL and background settings and, if something changed, refreshes the wallpaper.
    /// Returns false if the URL is not valid.
    Q_INVOKABLE bool applySettings(const QString &url, const QString &background, const QColor &color, int checkInterval);
    /// Downloads today's image from the given URL without touching Plasma. Emits testFinished().
    Q_INVOKABLE void testConnection(const QString &url);
    /// Deletes the cached image and makes Plasma download it again. Emits refreshFinished().
    Q_INVOKABLE void refreshWallpaper();
    /// Restarts plasmashell so that it loads the installed version of the provider.
    Q_INVOKABLE void restartPlasma();
    /// Downloads today's image and refreshes the wallpaper only if it is
    /// different from the current one (used every 30 minutes). Emits refreshFinished().
    Q_INVOKABLE void updateIfChanged();
    /// Makes "Catholic background of the day" the wallpaper of every desktop. Emits refreshFinished().
    Q_INVOKABLE void setAsWallpaper();

Q_SIGNALS:
    void serverUrlChanged();
    void backgroundChanged();
    void checkIntervalChanged();
    void imageChanged();
    void busyChanged();
    void problemChanged();
    void lastCheckChanged();
    void testFinished(bool ok, const QString &message);
    void refreshFinished(bool ok, const QString &message);

private:
    void setBusy(bool busy);
    void loadCachedInfo();
    void onCacheChanged();
    void waitForDownload();
    void finishRefresh(bool ok, const QString &message);
    void evaluateScript(const QString &script, const std::function<void(bool, const QString &)> &callback);
    /// callback(ok, message, SHA-1 of the image in hex)
    void checkServer(const QString &url, const std::function<void(bool, const QString &, const QByteArray &)> &callback);
    void doRefresh(bool automatic);
    void doSetAsWallpaper();
    void updatePanelMargins(const std::function<void()> &done);
    QString cachePath() const;
    void checkInstallation();
    void setCheckInterval(int minutes);
    void setProblem(const QString &problem, bool canRestart);

    QNetworkAccessManager m_network;
    QFileSystemWatcher m_watcher;
    QTimer m_timeout;
    bool m_busy = false;
    bool m_waitingForDownload = false;
    int m_imageVersion = 0;
    QString m_title;
    QString m_author;
    QString m_problem;
    bool m_canRestartPlasma = false;
    bool m_recordCheck = false;
    QTimer m_lastCheckTimer;
};
