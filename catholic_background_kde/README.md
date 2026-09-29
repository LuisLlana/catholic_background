# Catholic background of the day — Picture of the Day provider for KDE Plasma 6

A provider for Plasma's **Picture of the Day** wallpaper that downloads the
daily wallpaper from your own server, and a small application to configure it.

The same feature for GNOME is the `catholic_background_gnome` project.

Author: Luis Llana <luis.llana.diaz@gmail.com>
License: GPL-3.0-or-later (see `LICENSE`)

## Icon

`icons/` contains the application icon, installed in the hicolor theme as
`catholic-background`: a scalable version drawn on a 48x48 grid and a
simplified 16x16 version for small sizes.

## Server protocol

Request:

    GET <Url>?ts=<Unix timestamp of today's local midnight>

The URL is the same for the whole day and changes every day, so responses can
be cached safely. Any query parameters already present in `<Url>` are kept.

Response (JSON):

    {
      "image":  "<base64 image; a data:...;base64, prefix is accepted>",
      "title":  "The Starry Night",
      "author": "Vincent van Gogh",
      "date":   "1889"
    }

Only `image` is required. Any format Qt can read (JPEG, PNG, WebP…) works;
it is detected from the content. `date` is free text (a number is also
accepted). Plasma shows the title as "The Starry Night (1889)".

Note for server implementers: `ts` is the *local* midnight of the client, so
it can be up to ~14 h away from the UTC midnight of the same day. Adding 12 h
before converting it to a UTC date gives the client's calendar day for common
time zones. Do not blindly trust `ts` (e.g. refuse dates in the future).

## Dependencies

Debian 13 (trixie):

    sudo apt install build-essential cmake extra-cmake-modules qt6-base-dev \
        libkf6kio-dev libkf6coreaddons-dev libkf6config-dev qt6-declarative-dev \
        qml6-module-org-kde-kirigami qml6-module-org-kde-desktop \
        plasma-dataengines-addons plasma-wallpapers-addons

Other distributions need CMake, extra-cmake-modules, Qt 6 (Core, Gui, Widgets,
Quick, QuickControls2, DBus, Network), Kirigami,
KF6 (KIO, CoreAddons, Config) and kdeplasma-addons.

Debian does not package the headers of the provider library
(`libplasmapotdprovidercore`), so this project bundles a copy in
`third_party/` (from kdeplasma-addons 6.3.5, the version in trixie) and links
against the installed library. If the system provides the `PlasmaPotdProvider`
CMake package, it is used instead. When Plasma is upgraded to another version,
the bundled header should be updated to match it.

## Build and install

    cmake -B build -DCMAKE_INSTALL_PREFIX=/usr -DWALLPAPER_URL="https://simba.fdi.ucm.es/background"
    cmake --build build
    sudo cmake --install build
    plasmashell --replace &>/dev/null & disown   # or log out and back in

## Debian package (trixie)

    sudo apt install build-essential dpkg-dev debhelper fakeroot
    dpkg-buildpackage -us -uc -b
    sudo apt install ../catholic-background_0.1.0_amd64.deb

To compile a different default server URL into the package:

    WALLPAPER_URL=https://my-server.example/background dpkg-buildpackage -us -uc -b

The package depends on `plasma-dataengines-addons` 6.3.x, because the bundled
header in `third_party/` must match the installed provider library. When
Plasma moves to a new version, update that header and the version range in
`debian/control`.

## Install for the current user only

    ./install-user.sh            # extra arguments go to CMake, e.g. -DWALLPAPER_URL=...
    ./uninstall-user.sh

The plugin is installed in `~/.local/lib/qt6/plugins/potd/`, and
`~/.config/plasma-workspace/env/catholic-background.sh` adds that directory to
`QT_PLUGIN_PATH` when the Plasma session starts. Log out and back in after
installing.

## Catholic Background Settings

`catholic-background-settings` is a small Kirigami application. Its main page
shows the image of a day, as big as the window allows, with its data: the reason
why it is shown (saint, celebration or liturgical season), title, author, year,
comment, other data, license and source. From there:

- **choose the day**: previous and next day, a calendar and "Today" (any day,
  past or future);
- **Use as wallpaper**: the day shown becomes the wallpaper until the next
  automatic check, which returns to today;
- **Edit this image**: opens the page of the artwork in the content manager of
  the server (editors must log in);
- **Refresh wallpaper**.

**Settings** (in their own dialog): server URL (with Test), language of the
texts (by default that of the system; the list comes from the server), label
below the artwork (reason, title, author; drawn by the server), how to fill the
screen around the image, and how often to check the server.

It can also be used from the command line:

    catholic-background-settings --refresh         # download the image again
    catholic-background-settings --set-wallpaper   # use it as wallpaper
    catholic-background-settings --update          # refresh only if the image changed

Before refreshing, it checks that the server answers with a valid image, so
a server that is down never leaves the desktop without today's image.

The Plasma provider and the application build the address of the image in the
same way (`common/catholicbackground_request.h`: day, `lang` and `caption`), so
that both get exactly the same image.

How the refresh works: Plasma only downloads a new image when there is no
cached one and the wallpaper is loaded again. The application deletes the
cache, switches the desktops that use the provider to a plain color and,
half a second later, back again (both steps in the same script are not
enough), using plasmashell's D-Bus scripting API.

## Several images a day

The server may return different images during the same day. The user timer
`catholic-background-update.timer` runs `catholic-background-settings --update`
every 30 minutes (adjustable in the settings application, from 5 minutes
to 24 hours) during Plasma sessions: it downloads today's image and
compares its SHA-1 with the one of the current wallpaper (stored by the
provider as `CurrentImageHash`), and refreshes the wallpaper only when it is
different, so the wallpaper does not flicker when nothing changed. The
result of the last check is shown in the settings application.

The Debian package enables the timer for every user (it starts at the next
login); `install-user.sh` enables it for the current user.

The settings application stores the interval as `CheckInterval` (minutes)
and writes it to the timer as a drop-in,
`~/.config/systemd/user/catholic-background-update.timer.d/interval.conf`.

    systemctl --user status catholic-background-update.timer
    journalctl --user -u catholic-background-update.service

Before refreshing, it checks that the server answers with a valid image, so
a server that is down never leaves the desktop without today's image.

How the refresh works: Plasma only downloads a new image when there is no
cached one and the wallpaper is loaded again. The application deletes the
cache, switches the desktops that use the provider to a plain color and,
half a second later, back again (both steps in the same script are not
enough), using plasmashell's D-Bus scripting API.

## Configuration (optional)

`~/.config/catholicbackgroundrc`:

    [General]
    Url=https://my-server.example/background
    InfoUrl=https://my-server.example/

Other keys, written by the settings application:

    Language=en          # language of the texts (none: the language of the system)
    ShowLabel=false      # without the label below the artwork
    ShowDate=2026-03-19  # day used as wallpaper until the next automatic check

`Url` overrides the URL set at build time (by default
https://simba.fdi.ucm.es/background).

The image is always shown complete: it is scaled, keeping its proportions,
to the largest size that fits entirely in the part of the primary screen not
covered by panels, whatever the resolution of the image and of the screen.
The rest of the screen is filled according to `Background`:

    Background=blur        # default: the image enlarged and blurred
    Background=average     # the average color of the image
    Background=color       # the color in BackgroundColor
    BackgroundColor=#1f3a5f

The settings application stores the space taken by the panels of the
primary screen (`PanelTop`, `PanelBottom`, `PanelLeft`, `PanelRight`, in
logical pixels) every time it refreshes the wallpaper, so refresh it after
moving or resizing a panel. Autohiding panels are ignored.

The provider composes an image of the size of the primary screen, and the
application sets Plasma to "Scaled, keep proportions", so on other screens the
image is also shown complete.

After installing a new version, log out and back in (or run
`systemctl --user restart plasma-plasmashell`): plasmashell keeps using the
provider it had already loaded until it is restarted.

`Url` `InfoUrl` is the link shown as
"more information" in Plasma.

It can also be changed from the command line:

    kwriteconfig6 --file catholicbackgroundrc --group General --key Url https://my-server.example/background

The provider reads it when Plasma requests a new image, so clear
`~/.cache/plasma_engine_potd/` and restart plasmashell to apply it right away.

## Usage

Right-click the desktop → Configure Desktop and Wallpaper →
Wallpaper type: Picture of the Day → Provider: Catholic background of the day.

## Local testing

    python3 -c '
    import base64, json
    img = base64.b64encode(open("test.jpg", "rb").read()).decode()
    json.dump({"image": img, "title": "Test", "author": "Me", "date": "2026"}, open("background", "w"))
    '
    python3 -m http.server 8000

`http.server` ignores the `ts` parameter and serves the `background` file.
Point the provider to it (the default server is https://simba.fdi.ucm.es/background):

    kwriteconfig6 --file catholicbackgroundrc --group General --key Url http://localhost:8000/background

To discard cached images: `rm -rf ~/.cache/plasma_engine_potd/`
To see log messages: `journalctl --user -f | grep -i potd`

## Troubleshooting

If the image is not fitted to the screen or the background options have no
effect, Plasma is not using the installed version of the provider. The
settings application detects both usual causes and shows a warning with a
"Restart Plasma" button:

- plasmashell is still running the provider it loaded before the last
  upgrade: restart Plasma (or log out and back in);
- there are several copies of the provider (for example one installed with
  `install-user.sh` in `~/.local` and another one from the Debian package),
  and the one in `~/.local` takes precedence: remove the one you do not use
  (`./uninstall-user.sh`) and restart Plasma.

You can check it by hand with:

    ls -l ~/.local/lib/qt6/plugins/potd/ /usr/lib/x86_64-linux-gnu/qt6/plugins/potd/ | grep catholic
