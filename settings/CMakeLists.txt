# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

add_executable(catholic-background-settings
    main.cpp
    backend.cpp
    backend.h
)

qt_add_resources(catholic-background-settings "qml"
    PREFIX "/"
    FILES Main.qml
)

target_compile_definitions(catholic-background-settings PRIVATE
    DEFAULT_WALLPAPER_URL="${WALLPAPER_URL}"
    APP_VERSION="${PROJECT_VERSION}"
)

target_link_libraries(catholic-background-settings
    Qt6::Widgets
    Qt6::Quick
    Qt6::QuickControls2
    Qt6::DBus
    Qt6::Network
    KF6::CoreAddons
    KF6::ConfigCore
)

install(TARGETS catholic-background-settings ${KDE_INSTALL_TARGETS_DEFAULT_ARGS})
install(FILES catholic-background-settings.desktop DESTINATION ${KDE_INSTALL_APPDIR})

# Check the server every 30 minutes during Plasma sessions
configure_file(catholic-background-update.service.in ${CMAKE_CURRENT_BINARY_DIR}/catholic-background-update.service @ONLY)
install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/catholic-background-update.service
    catholic-background-update.timer
    DESTINATION ${KDE_INSTALL_SYSTEMDUSERUNITDIR}
)
