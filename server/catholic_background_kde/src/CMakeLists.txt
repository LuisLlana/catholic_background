# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

add_library(plasma_potd_catholicbackgroundprovider MODULE catholicbackgroundprovider.cpp)

target_compile_definitions(plasma_potd_catholicbackgroundprovider PRIVATE
    DEFAULT_WALLPAPER_URL="${WALLPAPER_URL}"
)

target_link_libraries(plasma_potd_catholicbackgroundprovider
    Plasma::PotdProvider
    Qt6::Gui
    KF6::KIOCore
    KF6::CoreAddons
    KF6::ConfigCore
)

install(TARGETS plasma_potd_catholicbackgroundprovider DESTINATION ${KDE_INSTALL_PLUGINDIR}/potd)
