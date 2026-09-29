// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Address of the image requested to the server. Shared by the Plasma provider and the
// settings application: both must ask for exactly the same thing (same day, language and
// label), otherwise they would get different images and the automatic check would see a
// "new" image every time.

#pragma once

#include <KConfigGroup>
#include <QDate>
#include <QLocale>
#include <QUrl>
#include <QUrlQuery>

namespace CatholicBackground
{

/// Language of the texts: the one chosen in the settings, or else the language of the system.
inline QString languageCode(const KConfigGroup &group)
{
    const QString chosen = group.readEntry("Language", QString());
    return chosen.isEmpty() ? QLocale::system().bcp47Name().toLower() : chosen;
}

/// Day shown as wallpaper: the one chosen with "Use as wallpaper", or else today.
inline QDate wallpaperDay(const KConfigGroup &group)
{
    const QDate day = QDate::fromString(group.readEntry("ShowDate", QString()), Qt::ISODate);
    return day.isValid() ? day : QDate::currentDate();
}

inline bool showLabel(const KConfigGroup &group)
{
    return group.readEntry("ShowLabel", true);
}

/// base?ts=<local midnight of day>&lang=<language>[&caption=0], keeping other parameters of base.
inline QUrl requestUrl(const QString &base, const QDate &day, const QString &language, bool label)
{
    QUrl url(base.trimmed());
    QUrlQuery query(url);
    for (const auto &name : {QStringLiteral("ts"), QStringLiteral("lang"), QStringLiteral("caption")}) {
        query.removeAllQueryItems(name);
    }
    query.addQueryItem(QStringLiteral("ts"), QString::number(day.startOfDay().toSecsSinceEpoch()));
    if (!language.isEmpty()) {
        query.addQueryItem(QStringLiteral("lang"), language);
    }
    if (!label) {
        query.addQueryItem(QStringLiteral("caption"), QStringLiteral("0"));
    }
    url.setQuery(query);
    return url;
}

/// The image that must be the wallpaper, according to the settings.
inline QUrl wallpaperUrl(const KConfigGroup &group, const QString &defaultBase)
{
    return requestUrl(group.readEntry("Url", defaultBase), wallpaperDay(group), languageCode(group), showLabel(group));
}

/// Address of the list of languages of the content: <base>/languages.
inline QUrl languagesUrl(const QString &base)
{
    QUrl url(base.trimmed());
    QString path = url.path();
    while (path.endsWith(QLatin1Char('/'))) {
        path.chop(1);
    }
    url.setPath(path + QStringLiteral("/languages"));
    url.setQuery(QString());
    return url;
}

}
