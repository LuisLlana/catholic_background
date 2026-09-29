// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <QColor>
#include <QDate>
#include <QPointer>
#include <QVariantList>
#include <QVariantMap>
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
    // Language of the texts ("" = the language of the system) and languages offered by the server
    Q_PROPERTY(QString language READ language NOTIFY languageChanged)
    Q_PROPERTY(QString systemLanguageName READ systemLanguageName CONSTANT)
    Q_PROPERTY(QVariantList languages READ languages NOTIFY languagesChanged)
    Q_PROPERTY(bool showLabel READ showLabel NOTIFY showLabelChanged)
    // The day shown in the window (any day) and the day used as wallpaper
    Q_PROPERTY(QDate viewDate READ viewDate NOTIFY dayChanged)
    Q_PROPERTY(QString viewDateText READ viewDateText NOTIFY dayChanged)
    Q_PROPERTY(int viewYear READ viewYear NOTIFY dayChanged)
    Q_PROPERTY(int viewMonth READ viewMonth NOTIFY dayChanged)   // 1–12
    Q_PROPERTY(int viewDay READ viewDay NOTIFY dayChanged)
    Q_PROPERTY(bool viewIsToday READ viewIsToday NOTIFY dayChanged)
    Q_PROPERTY(bool viewIsWallpaper READ viewIsWallpaper NOTIFY dayChanged)
    Q_PROPERTY(QString wallpaperDateText READ wallpaperDateText NOTIFY dayChanged)
    Q_PROPERTY(bool dayLoading READ dayLoading NOTIFY dayChanged)
    Q_PROPERTY(QString dayError READ dayError NOTIFY dayChanged)
    Q_PROPERTY(QUrl dayImage READ dayImage NOTIFY dayChanged)
    Q_PROPERTY(QVariantMap dayInfo READ dayInfo NOTIFY dayChanged)

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
    QString language() const;
    QString systemLanguageName() const;
    QVariantList languages() const;
    bool showLabel() const;
    QDate viewDate() const;
    QString viewDateText() const;
    int viewYear() const;
    int viewMonth() const;
    int viewDay() const;
    bool viewIsToday() const;
    bool viewIsWallpaper() const;
    QString wallpaperDateText() const;
    bool dayLoading() const;
    QString dayError() const;
    QUrl dayImage() const;
    QVariantMap dayInfo() const;

    /// Loads the languages and today's image (only for the window, not for the command line).
    void startInteractive();
    /// Shows the image and texts of any day (it does not change the wallpaper).
    Q_INVOKABLE void loadDay(const QDate &day);
    Q_INVOKABLE void shiftDay(int days);
    /// Dates from QML as numbers (a JavaScript Date may move a day with some time zones)
    Q_INVOKABLE void loadDate(int year, int month, int day);
    Q_INVOKABLE void goToToday();
    /// Makes the day shown the wallpaper until the next automatic check, which returns to today.
    Q_INVOKABLE void useViewedDayAsWallpaper();

    /// Saves the URL (an empty string restores the default). Returns false if it is not valid.
    Q_INVOKABLE bool setServerUrl(const QString &url);
    /// Saves URL and background settings and, if something changed, refreshes the wallpaper.
    /// Returns false if the URL is not valid.
    Q_INVOKABLE bool applySettings(const QString &url, const QString &background, const QColor &color, int checkInterval,
                                   const QString &language, bool showLabel);
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
    void languageChanged();
    void languagesChanged();
    void showLabelChanged();
    void dayChanged();

private:
    void setBusy(bool busy);
    void loadCachedInfo();
    void onCacheChanged();
    void waitForDownload();
    void finishRefresh(bool ok, const QString &message);
    void evaluateScript(const QString &script, const std::function<void(bool, const QString &)> &callback);
    /// callback(ok, message, SHA-1 of the image in hex)
    void checkServer(const QUrl &url, const std::function<void(bool, const QString &, const QByteArray &)> &callback);
    void loadLanguages();
    void setDayResult(const QString &error, const QUrl &image, const QVariantMap &info);
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
    QVariantList m_languages;
    QDate m_viewDate;
    bool m_dayLoading = false;
    QString m_dayError;
    QUrl m_dayImage;
    QVariantMap m_dayInfo;
    int m_dayVersion = 0;
    QPointer<QNetworkReply> m_dayReply;
};
