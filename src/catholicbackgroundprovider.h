// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <QColor>
#include <QMargins>

#include <plasma/potdprovider/potdprovider.h>

class KJob;

/**
 * Plasma "Picture of the Day" provider for a Catholic background of the day server.
 *
 * It requests a base URL (~/.config/catholicbackgroundrc, [General] Url=..., or the
 * one set at build time with WALLPAPER_URL) adding the parameter
 * ts = Unix timestamp (seconds) of today's local midnight:
 *     https://my-server.example/background?ts=1790200800
 *
 * The server answers with JSON:
 *     {
 *       "image":  "<base64 image>",       // required (a data:...;base64, prefix is accepted)
 *       "title":  "The Starry Night",     // optional
 *       "author": "Vincent van Gogh",     // optional
 *       "date":   "1889"                  // optional, free text
 *     }
 *
 * The image is scaled, keeping its proportions, to the largest size that fits
 * entirely in the part of the primary screen not covered by panels
 * ([General] PanelTop/PanelBottom/PanelLeft/PanelRight=, logical pixels). The
 * rest of the screen is filled according to [General] Background=:
 *     blur    (default) the image enlarged and blurred
 *     average the average color of the image
 *     color   the color in BackgroundColor= (e.g. #1f2933)
 */
class CatholicBackgroundProvider : public PotdProvider
{
    Q_OBJECT

public:
    explicit CatholicBackgroundProvider(QObject *parent, const KPluginMetaData &data, const QVariantList &args);

private:
    void requestFinished(KJob *job);

    QString m_background;
    QColor m_backgroundColor;
    QMargins m_panelMargins;
};
