# Catholic Background for GNOME (GTK)

A GTK 4 + libadwaita application that puts the Catholic image of the day, from a
[catholic_background_server](../catholic_background_server), as the background of:

- the **desktop** (GNOME, and any desktop that uses `org.gnome.desktop.background`: Budgie, Cinnamon…),
- the **lock screen** (`org.gnome.desktop.screensaver`; GNOME 42 or later always shows the desktop
  background blurred, so there it is the same picture),
- the **login screen**: SDDM (current theme, `theme.conf.user`) and LightDM with the GTK greeter or the
  Slick greeter. GDM is not supported yet (see `TODO.md` of the monorepo).

Every option can be turned on and off in *Preferences*. It needs no KDE library and does not need the
GNOME Shell extension (`catholic_background_gnome`), although both can be installed.

The window shows the image of any day with its reason, title, author, description and data, the other
images of the same day (*Next image*, only to see them), and *Use as Wallpaper*.

## Debian package

```sh
sudo apt install debhelper
dpkg-buildpackage -us -uc -b
sudo apt install ../catholic-background-gtk_0.6.0_all.deb
```

Another default server: `WALLPAPER_URL=https://my-server.example/background dpkg-buildpackage -us -uc -b`.

Dependencies: `python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1` (libadwaita 1.5 or later: Debian 13,
Ubuntu 24.10), `python3-pil`, `pkexec`.

## Without installing

```sh
./catholic-background-gtk
```

## How it works

| Part | What it does |
|------|--------------|
| `catholic-background-gtk` | The window; `--update` checks for a new image (if the interval of the settings has passed), `--refresh` puts it now. |
| `catholic-background-gtk-update.timer` (systemd **user** unit, enabled for every user by the package) | Runs `--update` every 5 minutes; nothing happens for users who have not turned the desktop background on. |
| `~/.config/catholic-background-gtk/settings.json` | Settings and state. |
| `~/.local/share/backgrounds/catholic-background/` | The composed wallpaper (a new file name for each image, so that GNOME notices the change) and `previous.json`, the backgrounds before ours, given back when an option is turned off. |
| `/usr/libexec/catholic-background-gtk/login-background` | Login screen, run as root with `pkexec` (asks for the administrator password). `enable` keeps a copy of the greeter files it changes, `disable` puts them back. |
| `catholic-background-gtk-login.timer` (system unit) | Updates `/var/lib/catholic-background-gtk/login.jpg` every hour while the login screen option is on. |

The login screen uses the size, label, language and background settings it had when it was turned on;
turn it off and on again to use new ones. Removing the package restores the login screens.
It is the same helper as in `catholic_background_kde`: turn it on in only one of the two applications.

## Tests

```sh
python3 -m unittest discover tests
```

`login-background` is tested on a fake root (`CATHOLIC_BACKGROUND_ROOT`) with SDDM, LightDM GTK and
Slick greeter configurations.

## License

GPL-3.0-or-later
