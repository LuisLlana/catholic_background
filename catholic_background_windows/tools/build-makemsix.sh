#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Builds Microsoft's makemsix (MSIX SDK, https://github.com/microsoft/msix-packaging)
# with packaging support, and installs it in tools/msix/. Needed once.
#
# Debian 13: sudo apt install git cmake clang make zlib1g-dev libicu-dev
set -eu

cd "$(dirname "$0")"
DEST="$(pwd)/msix"
SRC="$(pwd)/msix-packaging"

if [ ! -d "$SRC" ]; then
    git clone --depth 1 https://github.com/microsoft/msix-packaging.git "$SRC"
fi
cd "$SRC"

# Current ICU headers need C++17
sed -i 's/set(CMAKE_CXX_STANDARD 14)/set(CMAKE_CXX_STANDARD 17)/' CMakeLists.txt lib/xerces/CMakeLists.txt

rm -rf .vs
./makelinux.sh --pack --skip-samples --skip-tests

mkdir -p "$DEST"
cp .vs/bin/makemsix .vs/lib/libmsix.so "$DEST/"
echo "makemsix installed in $DEST"
