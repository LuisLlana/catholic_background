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
  `GET <server-url>?ts=<Unix timestamp of today's local midnight>&lang=<language>`,
  in the language of the system or the one chosen in the preferences. The
  server adds a label below the artwork with the reason (saint, celebration
  or liturgical season), title, author and year; it can be turned off. The
  server may have several images for the same day: the wallpaper changes
  only when the SHA-1 of the image is different from the current one. If the
  server fails, the current wallpaper is kept and it retries later.
- It composes a wallpaper of the size of the primary monitor: the whole
  artwork, as big as possible without cropping it, in the area not covered
  by the top bar or docks, and the rest filled with a blurred copy of the
  artwork, its average color or a chosen color.
- It sets it in `org.gnome.desktop.background` (light and dark styles),
  recomposing it when the options, the monitors or the work area change.
- Optionally (**Icon in the top bar**, off by default), an icon in the top bar
  whose menu shows the reason, title and author of the current image, with
  **Image of the Day…** (the preferences) and **Refresh Wallpaper**. With it,
  when a periodic check finds a new image (a new day, or another image of the
  same day) a GNOME notification shows its reason, title and author; clicking it
  opens the preferences.
- Files: `~/.local/share/backgrounds/catholic-background/` (wallpaper) and
  `~/.cache/catholic-background/original` (today's original image).

Disabling the extension (which GNOME also does while the screen is locked)
leaves the wallpaper as it is.

## Preferences

Open them from the Extensions application, or with
`gnome-extensions prefs catholic-background@luis.llana.diaz`. Two pages:

- **Image of the Day**: the image of any day, as big as the window allows, with
  its data (reason, title, author, year, comment, other data, license and
  source). Previous and next day, a calendar and Today (any day, past or
  future); **Next Image** (only when the day has several images, with "Image 2 of
  3 of this day": the following one of the same day, back to the first after the
  last; it only changes what is seen); **Use as Wallpaper** (the day shown becomes the wallpaper until the
  next automatic check, which returns to today); **Edit this Image** (opens the
  page of the artwork in the content manager of the server; editors must log
  in); **Refresh Wallpaper** and the result of the last check.
- **Settings**: server URL (with Test and Restore default), how often to check
  the server, language of the texts (by default that of the system; the list
  comes from the server), label below the artwork, how to fill the screen
  around the image, and the icon in the top bar (with the notifications).

The extension and the preferences build the address of the image in the same
way (`wallpaperUrl` in `lib/server.js`: day, `lang` and `caption`).

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
