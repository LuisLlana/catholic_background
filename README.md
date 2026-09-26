# Catholic Background of the Day — GNOME Shell extension

Sets a Catholic artwork as your GNOME wallpaper every day, downloaded from a
Catholic background of the day server (by default
https://simba.fdi.ucm.es/background; the same protocol used by the
`catholic_background_kde` KDE Plasma project).

Author: Luis Llana <luis.llana.diaz@gmail.com>
License: GPL-3.0-or-later

Supported GNOME Shell versions: 48, 49, 50, 51 (tested on GNOME Shell 48,
Debian 13).

## What it does

- At login and every 30 minutes (adjustable in the preferences, from 5
  minutes to 24 hours) it downloads
  `GET <server-url>?ts=<Unix timestamp of today's local midnight>`. The
  server may have several images for the same day: the wallpaper changes
  only when the SHA-1 of the image is different from the current one. If the
  server fails, the current wallpaper is kept and it retries later.
- It composes a wallpaper of the size of the primary monitor: the whole
  artwork, as big as possible without cropping it, in the area not covered
  by the top bar or docks, and the rest filled with a blurred copy of the
  artwork, its average color or a chosen color.
- It sets it in `org.gnome.desktop.background` (light and dark styles),
  recomposing it when the options, the monitors or the work area change.
- Files: `~/.local/share/backgrounds/catholic-background/` (wallpaper) and
  `~/.cache/catholic-background/original` (today's original image).

Disabling the extension (which GNOME also does while the screen is locked)
leaves the wallpaper as it is.

## Preferences

Open them from the Extensions application, or with
`gnome-extensions prefs catholic-background@luis.llana.diaz`:
today's image with title and author, the result of the last check, a
refresh button, the server URL (with
Test and Restore default), how often to check the server and how to fill
the screen around the image.

## Install from source

    make install
    # log out and back in, then:
    gnome-extensions enable catholic-background@luis.llana.diaz

## Publish on extensions.gnome.org

1. The UUID (`catholic-background@luis.llana.diaz`) cannot change after
   the first upload. If the code is published somewhere, add its address as
   `url` in `metadata.json`.
2. `make pack` creates `catholic-background@luis.llana.diaz.shell-extension.zip`.
3. Log in at https://extensions.gnome.org and upload the zip at
   https://extensions.gnome.org/upload/. It is reviewed by hand.

Compiled schemas are not included in the zip: GNOME Shell 44 and later
compile them when the extension is installed.

## New GNOME versions

The extension only uses stable platform APIs (GLib, Gio, Soup, GdkPixbuf,
GSettings) and a few layout properties of GNOME Shell. For each new GNOME
version: read its porting guide at https://gjs.guide/extensions/upgrading/,
test the extension, and add the version to `shell-version` in
`metadata.json`.
