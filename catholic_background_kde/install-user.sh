#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Build and install the provider for the current user only (no root needed).
# Extra arguments are passed to CMake, e.g.:
#     ./install-user.sh -DWALLPAPER_URL=https://my-server.example/background
set -eu

cd "$(dirname "$0")"

PREFIX="$HOME/.local"
PLUGINDIR="lib/qt6/plugins"
ENVFILE="${XDG_CONFIG_HOME:-$HOME/.config}/plasma-workspace/env/catholic-background.sh"

cmake -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" \
    -DKDE_INSTALL_PLUGINDIR="$PLUGINDIR" \
    -DKDE_INSTALL_SYSTEMDUSERUNITDIR=share/systemd/user \
    "$@"
cmake --build build
cmake --install build

# Plasma only looks for providers in Qt's plugin paths: add ours to the session.
mkdir -p "$(dirname "$ENVFILE")"
cat > "$ENVFILE" <<ENV
# Added by catholic_background_kde/install-user.sh
case ":\${QT_PLUGIN_PATH:-}:" in
    *":$PREFIX/$PLUGINDIR:"*) ;;
    *) export QT_PLUGIN_PATH="$PREFIX/$PLUGINDIR\${QT_PLUGIN_PATH:+:\$QT_PLUGIN_PATH}" ;;
esac
ENV

# Check the server every 30 minutes during Plasma sessions
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable catholic-background-update.timer
    systemctl --user start catholic-background-update.timer || true
fi

echo
echo "Installed in $PREFIX/$PLUGINDIR/potd"
echo "Session environment: $ENVFILE"
echo "Log out and log back in, then choose 'Catholic background of the day'"
echo "in Configure Desktop and Wallpaper > Picture of the Day."
