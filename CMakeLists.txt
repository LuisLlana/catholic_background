# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

cmake_minimum_required(VERSION 3.18)
project(catholic-background-potd-provider VERSION 0.4.1)

set(QT_MIN_VERSION "6.6.0")
set(KF6_MIN_VERSION "6.0.0")

# Default server URL (override at configure time with -DWALLPAPER_URL=...)
set(WALLPAPER_URL "https://simba.fdi.ucm.es/background" CACHE STRING "Base URL of the wallpaper of the day (?ts=... is appended)")

find_package(ECM ${KF6_MIN_VERSION} REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})

include(KDEInstallDirs)
include(KDECMakeSettings)
include(KDECompilerSettings NO_POLICY_SCOPE)
include(FeatureSummary)

find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS Core Gui Widgets Quick QuickControls2 DBus Network)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS KIO CoreAddons Config)

# Picture of the Day provider library (kdeplasma-addons)
find_package(PlasmaPotdProvider CONFIG QUIET)
if(NOT PlasmaPotdProvider_FOUND)
    # Some distributions (e.g. Debian 13) ship the library but neither its
    # headers nor its CMake package. In that case, use the headers bundled in
    # third_party/ (copied from kdeplasma-addons 6.3.5) and the system library.
    find_library(PLASMA_POTD_LIBRARY
        NAMES plasmapotdprovidercore libplasmapotdprovidercore.so.2
        REQUIRED
    )
    message(STATUS "PlasmaPotdProvider headers not installed; using third_party/ and ${PLASMA_POTD_LIBRARY}")

    add_library(Plasma::PotdProvider SHARED IMPORTED)
    set_target_properties(Plasma::PotdProvider PROPERTIES
        IMPORTED_LOCATION "${PLASMA_POTD_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/third_party"
        INTERFACE_LINK_LIBRARIES "Qt6::Gui;KF6::CoreAddons;KF6::ConfigCore;KF6::KIOCore"
    )
endif()

add_subdirectory(src)
add_subdirectory(icons)
add_subdirectory(settings)

feature_summary(WHAT ALL INCLUDE_QUIET_PACKAGES FATAL_ON_MISSING_REQUIRED_PACKAGES)
