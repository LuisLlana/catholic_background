// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#include "backend.h"

#include <QApplication>
#include <QCommandLineParser>
#include <QIcon>
#include <QQmlApplicationEngine>
#include <QQuickStyle>
#include <QUrl>

#include <KAboutData>

#include <cstdio>

using namespace Qt::Literals::StringLiterals;

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    KAboutData about(u"catholic-background-settings"_s,
                     u"Catholic Background Settings"_s,
                     QStringLiteral(APP_VERSION),
                     u"Settings for the Catholic background of the day wallpaper"_s,
                     KAboutLicense::GPL_V3,
                     u"© 2026 Luis Llana"_s);
    about.setLicense(KAboutLicense::GPL_V3, KAboutLicense::OrLaterVersions);
    about.addAuthor(u"Luis Llana"_s, QString(), u"luis.llana.diaz@gmail.com"_s);
    about.setDesktopFileName(u"catholic-background-settings"_s);
    KAboutData::setApplicationData(about);
    QApplication::setWindowIcon(QIcon::fromTheme(u"catholic-background"_s));

    QCommandLineParser parser;
    about.setupCommandLine(&parser);
    const QCommandLineOption refreshOption(u"refresh"_s, u"Download the image again and exit, without opening the window."_s);
    const QCommandLineOption setOption(u"set-wallpaper"_s, u"Use Catholic background of the day as wallpaper and exit."_s);
    const QCommandLineOption updateOption(u"update"_s,
                                          u"Download today's image and refresh the wallpaper only if it has changed, then exit "
                                          "(run every 30 minutes by catholic-background-update.timer)."_s);
    parser.addOption(refreshOption);
    parser.addOption(setOption);
    parser.addOption(updateOption);
    parser.process(app);
    about.processCommandLine(&parser);

    Backend backend;

    // Command line mode: useful for scripts and for testing
    if (parser.isSet(refreshOption) || parser.isSet(setOption) || parser.isSet(updateOption)) {
        QObject::connect(&backend, &Backend::refreshFinished, &app, [](bool ok, const QString &message) {
            std::fprintf(ok ? stdout : stderr, "%s\n", qPrintable(message));
            QCoreApplication::exit(ok ? 0 : 1);
        });
        if (parser.isSet(setOption)) {
            backend.setAsWallpaper();
        } else if (parser.isSet(updateOption)) {
            backend.updateIfChanged();
        } else {
            backend.refreshWallpaper();
        }
        return app.exec();
    }

    if (qEnvironmentVariableIsEmpty("QT_QUICK_CONTROLS_STYLE")) {
        QQuickStyle::setStyle(u"org.kde.desktop"_s);
    }

    qmlRegisterSingletonInstance("CatholicBackground", 1, 0, "Backend", &backend);
    backend.startInteractive();

    QQmlApplicationEngine engine;
    engine.load(QUrl(u"qrc:/Main.qml"_s));
    if (engine.rootObjects().isEmpty()) {
        return 1;
    }
    return app.exec();
}
