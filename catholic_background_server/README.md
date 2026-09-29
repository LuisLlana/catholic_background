# Catholic Background — server and content manager

Server of the Catholic background of the day, with a web content manager so that
people without technical knowledge can upload artworks and their annotations.

Author: Luis Llana <luis.llana.diaz@gmail.com>
License: GPL-3.0-or-later (see `LICENSE`)

It serves the applications of the other projects (`catholic_background_kde`,
`catholic_background_gnome`, `catholic_background_windows` and the Python module)
with the same protocol:

    GET /background?ts=<Unix timestamp of the client's local midnight>
    GET /background?ts=<…>&lang=<language code>&caption=0     (lang and caption are optional)
    -> {"image": "<base64>", "title", "author", "date", "description", "source", "license", "extra": {...},
        "language": "<language of the texts>", "reason": "…", "reason_type": "saint|celebration|season|",
        "id": <artwork>, "edit_url": "<page of the admin site to edit it>"}

Any day can be asked for with `ts` (past or future): the settings applications use it
to show the image of another day. When a day has several artworks, the one of the
current time of day is sent, also for other days.

    GET /background/languages
    -> {"default": "es", "languages": [{"code": "es", "name": "Español"}, …]}

The languages of the content, for the language selector of the applications.

`date` is the year of the artwork (free text); `extra` contains the additional data.

## Addresses

Everything hangs from the base path, `BASE_PATH` (default `background`):

| Address | |
|---|---|
| `/background?ts=…` | the image of the day (used by the applications) |
| `/background/languages` | languages of the content (used by the applications) |
| `/background/home/` | start page after logging in |
| `/background/admin/` | content management |
| `/background/accounts/…` | login with Google or Microsoft |
| `/background/privacy/` | privacy policy |
| `/background/static/`, `/background/media/` | files of the admin site and uploaded images |

## Content manager (`/background/admin/`)

- **Login with Google or Microsoft accounts**. New users wait until an
  administrator approves them; e-mails in `ADMIN_EMAILS` become administrators
  and users from `AUTO_APPROVE_DOMAINS` become editors. While Google and
  Microsoft are not set up, **login with e-mail and password** is available
  (see "Password login").
- **Roles**: *Editors* upload and edit artworks; *Reviewers* also approve them and
  edit the calendar. Nothing is served until it is approved, and a change by an
  editor must be approved again.
- **Artwork**: the image (JPEG or PNG, the only required field), title, author,
  year (free text), comment, origin and license, and **other data**: name–value
  pairs whose names (museum, technique…) are a catalogue editable from the admin.
- **When it is shown**: one or more conditions, and it is shown on any day that
  meets at least one of them (OR): liturgical season, celebration, saint of the
  day, date of every year, specific date, or "any day" (reserve used when no
  artwork matches a day). When several artworks match a day, they are shown in
  turns during the day.
- **Calendar**: the next 60 days with their season, celebrations and artworks.
- **Liturgical calendar**: movable celebrations are computed from Easter every
  year (Spain by default: Epiphany on 6 January, Ascension and Corpus Christi on
  Sunday; see `CATHOLIC_BACKGROUND` in `config/settings.py`). Fixed celebrations
  and saints come from an initial catalogue (General Roman Calendar and Spain)
  that can be completed from the admin. Precedence between celebrations is not
  applied: every celebration of the day counts.

## Languages

The web site is available in English and Spanish. The language is taken from the
language cookie, if the user chose one with the language selector (in the header of
every page), or else from the browser (`Accept-Language`); English if the browser
language is not available. A notice about cookies is shown until it is acknowledged.

The interface texts are translated with Django's standard system
(`locale/es/LC_MESSAGES/django.po`, compiled into `django.mo`, both in the
repository, so the server does not need the gettext tools). After changing texts:

    sudo apt install gettext
    python manage.py makemessages -l es     # updates django.po; translate the new entries
    python manage.py compilemessages -l es  # updates django.mo

### Languages of the content

The texts of the artworks are multilingual, independently of the interface:

- **Languages** (admin site, only for administrators): Spanish (default) and English
  to start with; more can be added (e.g. `fr`, `pt-br`). The default language is used
  when an application does not ask for a language or asks for one that is not available.
- **Texts of an artwork**: title, author, year, comment and license, in one block per
  language (all optional). The image, its source and the conditions are common.
- **Other data**: each value has a language; the names of the kinds of data (Museum,
  Technique…) have a name in each language.

The image has a museum-style **label below the artwork**: the reason (in gold), the
title and the author and year, in the language asked. The applications fit the whole
image on the screen, so the size of the text is computed for a 16:9 screen. With
`caption=0` the original image is sent; `CAPTION_DEFAULT=false` makes that the
default (then `caption=1` asks for the label). Labelled images are cached in
`media/caption-cache/` (the same request always gets the same bytes, which the
applications compare to detect a new image) and removed by `process_access_logs` when
they have not been used for `CAPTION_CACHE_DAYS` days. The label uses the DejaVu Sans
font (`sudo apt install fonts-dejavu-core`; `CAPTION_FONT` and `CAPTION_FONT_BOLD` to
use others).

`reason` says why the artwork is shown that day when the reason is special: the saint
or the celebration of the day, or else the liturgical season (the most specific one if
the artwork meets several conditions), in the language asked. It is empty for artworks
shown because of a date or as a reserve.

`/background` returns the texts in the language asked with `?lang=xx`, else in the
default language; every empty field is taken from the default language (or from any
other). The `Accept-Language` header is not used on purpose: with the label, each
language gives a different image, and the same request must give the same image
whatever HTTP library the application uses. The answer includes `"language"` and a
`Content-Language` header.

The celebrations of the calendar are content, not interface: each one has a name and
a name in Spanish, editable in the admin site (the initial catalogue has both).

## Privacy

`/background/privacy/` shows the privacy policy (in English or Spanish), which also lists the cookies of the site. The server stores the IP address of each
request for `ACCESS_LOG_DAYS` days (30); `manage.py process_access_logs` (every
night, see `deploy/`) turns them into daily statistics without IP addresses and
deletes the old ones. Uploaded images are only visible to logged-in editors; the
applications receive them through `/background`.

## Development

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    DEBUG=true python manage.py migrate
    DEBUG=true python manage.py runserver     # http://127.0.0.1:8000/background/home/
    DEBUG=true python manage.py test

## Installation on Debian 13 (simba)

    sudo apt install python3-venv nginx fonts-dejavu-core
    sudo useradd --system --home /opt/catholic-background catholic
    sudo mkdir -p /opt/catholic-background /var/lib/catholic-background /etc/catholic-background
    # copy the project to /opt/catholic-background
    cd /opt/catholic-background
    sudo python3 -m venv venv
    sudo venv/bin/pip install -r requirements.txt
    sudo cp .env.example /etc/catholic-background/env      # and fill it in
    sudo chown -R catholic: /var/lib/catholic-background
    sudo chmod 640 /etc/catholic-background/env && sudo chgrp catholic /etc/catholic-background/env
    sudo -u catholic sh -c 'set -a; . /etc/catholic-background/env; venv/bin/python manage.py migrate; venv/bin/python manage.py collectstatic --noinput'
    sudo cp deploy/*.service deploy/*.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now catholic-background catholic-background-maintenance.timer

### nginx

The application lives under a path of an existing site, so its configuration is a
snippet included in the `server` block of that site (not a separate site):

    sudo cp deploy/nginx/*.conf /etc/nginx/snippets/
    sudo -u catholic sh -c 'set -a; . /etc/catholic-background/env; venv/bin/python manage.py collectstatic --noinput'

Then add this line inside the `server` block (the HTTPS one) of the site, e.g. in
`/etc/nginx/sites-available/default`:

    include snippets/catholic-background.conf;

and reload: `sudo nginx -t && sudo systemctl reload nginx`. Only `/background` and
`/background/…` go to the application; the rest of the site is untouched. If
`BASE_PATH` is different, replace `/background` in `catholic-background.conf`; if
gunicorn listens on another port, change it in `catholic-background-proxy.conf`.

If the site is served over plain HTTP (no HTTPS), set `BEHIND_PROXY=false` in the
environment file, otherwise the session cookies are marked as HTTPS-only and
logging in does not work.

Then log in at `https://simba.fdi.ucm.es/background/home/`.

## Password login

`PASSWORD_LOGIN=true` shows an e-mail and password form on the login page. If the
variable is not set, it is enabled only while no Google or Microsoft login is
configured. There is no self sign-up: an administrator creates the accounts.

The first administrator:

    python manage.py createsuperuser

Other users: in `/background/admin/` → Users → Add user (username and password),
then give them an e-mail, "Staff status" and the group *Editors* or *Reviewers*.

When Google or Microsoft is set up and password login is turned off, users who log
in with a Google or Microsoft account with the same e-mail keep their user and
permissions.

## Google and Microsoft login

Callback addresses (replace the host if it is different):

- Google: `https://simba.fdi.ucm.es/background/accounts/google/login/callback/`
- Microsoft: `https://simba.fdi.ucm.es/background/accounts/microsoft/login/callback/`

**Google**: Google Cloud Console → APIs & Services → Credentials → Create
credentials → OAuth client ID → Web application; add the callback address as an
authorised redirect URI. Put the client ID and secret in `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET`.

**Microsoft**: Microsoft Entra admin center → App registrations → New
registration; supported account types: "Accounts in any organizational directory
and personal Microsoft accounts"; redirect URI (Web): the callback address. Then
Certificates & secrets → New client secret. Put the Application (client) ID and
the secret value in `MICROSOFT_CLIENT_ID` and `MICROSOFT_CLIENT_SECRET`
(`MICROSOFT_TENANT=common`).

Only the configured providers are shown on the login page.

## Moving to PostgreSQL or MariaDB

The code only uses features that work in SQLite, PostgreSQL and MariaDB (the
tests pass in the three), and images are files, not database content.

    sudo apt install postgresql            # or mariadb-server
    venv/bin/pip install "psycopg[binary]" # or mysqlclient (apt install libmariadb-dev pkg-config)
    # create an empty database and a user, then:
    python manage.py migrate_database postgres://catholic:password@localhost/catholic
    # set DATABASE_URL to that address and restart the service

`migrate_database` creates the tables in the new database, copies all the data
(artworks, conditions, catalogues, users and permissions) and checks that the
counts match. To run the tests against another database:
`DATABASE_URL=postgres://… python manage.py test`.
