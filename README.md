# Catholic Background of the Day — Windows

Sets a Catholic artwork as your Windows wallpaper, downloaded from a Catholic
background of the day server (the same protocol used by the
`catholic_background_kde` and `catholic_background_gnome` projects).

Author: Luis Llana <luis.llana.diaz@gmail.com>
License: GPL-3.0-or-later (see `LICENSE`)

Requirements: Windows 10 (1809) or later, x64 (arm64 can be built with `ARCH=arm64`).

## What it does

- Runs in the notification area. Left click opens the settings; the menu has
  Settings, Refresh wallpaper and Exit.
- Shortly after starting, every N minutes (5–1440, 30 by default) and after
  resuming from sleep, it downloads
  `GET <server-url>?ts=<Unix timestamp of today's local midnight>`. The
  wallpaper changes only when the SHA-1 of the image is different, so the
  server may have several images a day. If the server fails, the current
  wallpaper is kept.
- For each monitor (`IDesktopWallpaper`) it composes a wallpaper of its size:
  the whole artwork, as big as possible without cropping it, in the area not
  covered by the taskbar, and the rest filled with a blurred copy of it, its
  average color or a chosen color. It composes again when monitors, the
  resolution or the taskbar change.
- Starts with Windows (without opening the window): Run registry key for the
  standalone `.exe` (enabled on first run), startup task for the MSIX package.
  It can be turned off in the settings.
- Files: `%LOCALAPPDATA%\CatholicBackground` (standalone) or the package's
  local folder (MSIX): `settings.json`, `original` and `wallpapers\`.

Server images: JPEG or PNG (Windows' GDI+ cannot read WebP).

## Build on Linux

Needs the .NET 10 SDK (https://dot.net). For the MSIX package also:

    sudo apt install git cmake clang make zlib1g-dev libicu-dev
    sh tools/build-makemsix.sh          # once: builds Microsoft's makemsix

Then:

    sh build.sh          # both
    sh build.sh exe      # dist/CatholicBackground-<version>-x64.exe  (standalone, 58 MB)
    sh build.sh msix     # dist/CatholicBackground-<version>-x64.msix (for the Microsoft Store)

The version is taken from `VERSION` (x.y.z; the package uses x.y.z.0, as the
Store requires).

The `.exe` is not signed, so Windows SmartScreen warns the first time
("More info" > "Run anyway").

## Publish on the Microsoft Store

1. Create a developer account (free) at https://storedeveloper.microsoft.com.
2. Reserve the app name in Partner Center and copy the values of
   Product identity into `packaging/identity.env`.
3. `sh build.sh msix` and upload the `.msix` in a new submission. It does not
   need to be signed: the Store signs it.
4. The `runFullTrust` capability needs a justification, e.g. "Desktop
   application that sets the wallpaper and runs in the notification area".

The MSIX package cannot be installed on a PC without being signed; to test
the application, use the `.exe`.
