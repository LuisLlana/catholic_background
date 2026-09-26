#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Builds on Linux (or anywhere with the .NET 10 SDK):
#   dist/CatholicBackground-<version>-<arch>.exe   standalone executable (no installation needed)
#   dist/CatholicBackground-<version>-<arch>.msix  package for the Microsoft Store
#
# Usage: ./build.sh [exe|msix|all]        (default: all)
# Environment: ARCH=x64|arm64 (default x64), DOTNET (default: dotnet),
#              MAKEMSIX (default: tools/msix/makemsix, see tools/build-makemsix.sh)
set -eu

cd "$(dirname "$0")"
TARGET="${1:-all}"
ARCH="${ARCH:-x64}"
DOTNET="${DOTNET:-dotnet}"
MAKEMSIX="${MAKEMSIX:-$(pwd)/tools/msix/makemsix}"
VERSION="$(tr -d ' \n' < VERSION)"            # x.y.z
PROJECT=src/CatholicBackground/CatholicBackground.csproj

. packaging/identity.env

export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
mkdir -p dist

build_exe() {
    echo "==> Standalone executable"
    rm -rf build/exe
    "$DOTNET" publish "$PROJECT" -c Release -r "win-$ARCH" --self-contained true \
        -p:Version="$VERSION" \
        -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true \
        -p:EnableCompressionInSingleFile=true -p:DebugType=none \
        -o build/exe
    cp build/exe/CatholicBackground.exe "dist/CatholicBackground-$VERSION-$ARCH.exe"
    echo "    dist/CatholicBackground-$VERSION-$ARCH.exe"
}

build_msix() {
    echo "==> MSIX package"
    if [ ! -x "$MAKEMSIX" ]; then
        echo "makemsix not found at $MAKEMSIX; build it once with tools/build-makemsix.sh" >&2
        exit 1
    fi
    ROOT=build/msix-root
    rm -rf build/msix-root
    # A normal (not single-file) self-contained publish: starts faster, and the MSIX is compressed anyway
    "$DOTNET" publish "$PROJECT" -c Release -r "win-$ARCH" --self-contained true \
        -p:Version="$VERSION" -p:DebugType=none \
        -o "$ROOT"

    mkdir -p "$ROOT/Assets"
    cp assets/StoreLogo.png assets/Square44x44Logo.png assets/Square150x150Logo.png "$ROOT/Assets/"
    # The Store requires the last part of the version to be 0
    sed -e "s|@PACKAGE_NAME@|$PACKAGE_NAME|g" \
        -e "s|@PUBLISHER@|$PUBLISHER|g" \
        -e "s|@PUBLISHER_DISPLAY_NAME@|$PUBLISHER_DISPLAY_NAME|g" \
        -e "s|@DISPLAY_NAME@|$DISPLAY_NAME|g" \
        -e "s|@VERSION@|$VERSION.0|g" \
        -e "s|@ARCH@|$ARCH|g" \
        packaging/AppxManifest.xml.in > "$ROOT/AppxManifest.xml"

    OUT="$(pwd)/dist/CatholicBackground-$VERSION-$ARCH.msix"
    rm -f "$OUT"
    LD_LIBRARY_PATH="$(dirname "$MAKEMSIX")${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
        "$MAKEMSIX" pack -d "$(pwd)/$ROOT" -p "$OUT"
    echo "    dist/CatholicBackground-$VERSION-$ARCH.msix (unsigned: the Microsoft Store signs it)"
}

case "$TARGET" in
    exe) build_exe ;;
    msix) build_msix ;;
    all) build_exe; build_msix ;;
    *) echo "Usage: $0 [exe|msix|all]" >&2; exit 1 ;;
esac
