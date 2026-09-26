# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

include(ECMInstallIcons)

# sc-apps: scalable version (drawn on a 48x48 grid)
# 16-apps: simplified version for small sizes
ecm_install_icons(
    ICONS
        sc-apps-catholic-background.svg
        16-apps-catholic-background.svg
    DESTINATION ${KDE_INSTALL_ICONDIR}
    THEME hicolor
)
