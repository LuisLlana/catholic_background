# Catholic Background

A work of Catholic sacred art as the desktop wallpaper, every day.

A server chooses the artwork of each day according to the liturgical calendar
(liturgical season, celebration, saint of the day or date) and a desktop
application for each system sets it as the wallpaper, always complete and as big as
possible, with a museum-style label that says why it is shown that day, its title,
author and year. The artworks and their texts are managed from a web content
manager by people without technical knowledge.

Author: Luis Llana <luis.llana.diaz@gmail.com>
License: GPL-3.0-or-later (each project has its `LICENSE`)


## Projects

Each project is a git subtree of this repository, with its own README:

| Folder | What it is | Technology | Version |
|---|---|---|---|
| [`catholic_background_server`](catholic_background_server) | Server and content manager | Python, Django | — |
| [`catholic_background_kde`](catholic_background_kde) | KDE Plasma: wallpaper provider and settings application | C++, Qt 6, KDE Frameworks 6, QML | 0.5.0 |
| [`catholic_background_gnome`](catholic_background_gnome) | GNOME Shell extension | JavaScript (GJS) | 0.4.1 |
| [`catholic_background_windows`](catholic_background_windows) | Windows application (standalone `.exe` and MSIX for the Microsoft Store) | C#, .NET 10, Windows Forms | 0.5.0 |

## How it works

```
  editors ──(browser)──▶  content manager  ─┐
                          /background/admin/ │  artworks, texts in each language,
                                             │  conditions, liturgical calendar
                                             ▼
                        server  /background?ts=…&lang=…
                                             │  image of the day (with its label) + data
             ┌───────────────────────────────┼───────────────────────────────┐
             ▼                               ▼                               ▼
        KDE Plasma                      GNOME Shell                       Windows
  provider + settings app                extension                  notification area app
             └───────── compose the wallpaper for each screen and set it ────┘
```

### The server

- **Artworks**: the image (JPEG or PNG) and, in each language, title, author, year,
  comment and license; its source; additional data (museum, technique…) whose names
  are also translated. Only the image is required.
- **When each artwork is shown**: one or more conditions, and it is shown on any day
  that meets at least one of them: liturgical season, celebration, saint of the day,
  date of every year, specific date, or "any day" (reserve for days without an
  artwork). Movable celebrations are computed from Easter every year (calendar of
  Spain by default); fixed celebrations and saints come from an editable catalogue.
  When several artworks match a day, they are shown in turns during the day.
- **Content manager**: login with Google or Microsoft (and, while they are not set
  up, e-mail and password); editors upload, reviewers approve; drag and drop of
  images; calendar of the next days; interface in English and Spanish.
- **Label**: the server draws it below the artwork, in the language asked, so every
  application shows it without drawing anything.
- **Languages of the content**: Spanish (default) and English; administrators can
  add more.
- **Privacy**: IP addresses are kept 30 days and then turned into statistics without
  them; the privacy policy is at `/background/privacy/`.

### The applications

All of them:

- check the server periodically (every 30 minutes by default) and change the
  wallpaper only when the image changes (the server may have several a day);
- ask for the texts in the language of the system, or in the one chosen;
- show the artwork complete, as big as possible and not covered by panels or the
  taskbar, filling the rest of the screen with a blurred copy of it, its average
  color or a color;
- keep the current wallpaper if the server is down.

The KDE and Windows applications (and GNOME, in progress) also have a window with
the image of any day and all its data, a calendar to choose the day, **Use as
wallpaper** (until the next automatic check, which returns to today) and **Edit this
image** (opens the page of the artwork in the content manager).

## Protocol

```
GET <server>/background?ts=<Unix timestamp of the local midnight of the day>&lang=<language>[&caption=0]
-> {"image": "<base64>", "title", "author", "date", "description", "source", "license",
    "extra": {...}, "language", "reason", "reason_type", "id", "edit_url"}

GET <server>/background/languages
-> {"default": "es", "languages": [{"code": "es", "name": "Español"}, …]}
```

- `ts`: any day, past or future. The applications send the local midnight of the day,
  and the server adds 12 hours before taking the date, so time zones do not matter.
- `lang`: language of the texts (and of the label); if it is not available, the
  default one. Every empty field is taken from the default language.
- `caption=0`: the image without the label.
- `reason`: why the artwork is shown that day (saint, celebration or liturgical
  season), empty for dates and reserve artworks.
- The same request always gets exactly the same bytes: the applications compare
  them (SHA-1) to detect a new image.

Default server: `https://simba.fdi.ucm.es/background`.

## Quick start

Each README has the details.

**Server** (Debian 13):

    cd catholic_background_server
    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    DEBUG=true python manage.py migrate
    DEBUG=true python manage.py runserver      # http://127.0.0.1:8000/background/home/

For production (gunicorn, nginx snippets, systemd, Google and Microsoft login,
PostgreSQL or MariaDB) see [its README](catholic_background_server/README.md).

**KDE Plasma** (Debian 13):

    cd catholic_background_kde
    dpkg-buildpackage -us -uc -b
    sudo apt install ../catholic-background_*_amd64.deb

**GNOME Shell**:

    cd catholic_background_gnome
    make install          # then log out and in
    gnome-extensions enable catholic-background@luis.llana.diaz

**Windows** (built on Linux with the .NET 10 SDK):

    cd catholic_background_windows
    sh build.sh exe       # dist/CatholicBackground-<version>-x64.exe
    sh build.sh msix      # package for the Microsoft Store (see its README)
