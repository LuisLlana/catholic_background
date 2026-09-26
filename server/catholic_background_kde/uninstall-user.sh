#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Remove what install-user.sh installed.
set -eu

cd "$(dirname "$0")"

ENVFILE="${XDG_CONFIG_HOME:-$HOME/.config}/plasma-workspace/env/catholic-background.sh"

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user disable --now catholic-background-update.timer 2>/dev/null || true
fi

if [ -f build/install_manifest.txt ]; then
    xargs -d '\n' rm -fv < build/install_manifest.txt
else
    rm -fv "$HOME/.local/lib/qt6/plugins/potd/plasma_potd_catholicbackgroundprovider.so"
fi
rm -fv "$ENVFILE"
rm -rfv "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/catholic-background-update.timer.d"
command -v systemctl >/dev/null 2>&1 && systemctl --user daemon-reload || true
rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/plasma_engine_potd"

echo
echo "Uninstalled. The configuration file ~/.config/catholicbackgroundrc was kept."
echo "Log out and log back in to finish."
