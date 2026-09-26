# Catholic Background — server and content manager

Server of the Catholic background of the day, with a web content manager so that
people without technical knowledge can upload artworks and their annotations.

Author: Luis Llana <luis.llana.diaz@gmail.com>
License: GPL-3.0-or-later (see `LICENSE`)

It serves the applications of the other projects (`catholic_background_kde`,
`catholic_background_gnome`, `catholic_background_windows` and the Python module)
with the same protocol:

    GET /background?ts=<Unix timestamp of the client's local midnight>
    -> {"image": "<base64>", "title", "author", "date", "description", "source", "license", "extra": {...}}

`date` is the year of the artwork (free text); `extra` contains the additional data.

## Content manager (`/admin/`)

- **Login without passwords**, with Google or Microsoft accounts. New users wait
  until an administrator approves them; e-mails in `ADMIN_EMAILS` become
  administrators and users from `AUTO_APPROVE_DOMAINS` become editors.
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

## Privacy

`/privacy/` shows the privacy policy. The server stores the IP address of each
request for `ACCESS_LOG_DAYS` days (30); `manage.py process_access_logs` (every
night, see `deploy/`) turns them into daily statistics without IP addresses and
deletes the old ones. Uploaded images are only visible to logged-in editors; the
applications receive them through `/background`.

## Development

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    DEBUG=true python manage.py migrate
    DEBUG=true python manage.py runserver
    DEBUG=true python manage.py test

## Installation on Debian 13 (simba)

    sudo apt install python3-venv nginx
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

Add `deploy/nginx.conf` to the HTTPS server block of nginx and reload it. Then
log in at `https://simba.fdi.ucm.es/` with an account listed in `ADMIN_EMAILS`.

## Google and Microsoft login

Callback addresses (replace the host if it is different):

- Google: `https://simba.fdi.ucm.es/accounts/google/login/callback/`
- Microsoft: `https://simba.fdi.ucm.es/accounts/microsoft/login/callback/`

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
