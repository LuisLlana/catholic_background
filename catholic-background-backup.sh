#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Local backup of the data of the Catholic Background server (database and uploaded
# images), through SSH. Each backup goes to <backup folder>/data-YYYYMMDDhhmmss.
#
# Usage: catholic-background-backup.sh [-H host] [-d remote data folder] [-o local backup folder] [-f] [-s]
#   -H  server, also as user@server         (default: simba.fdi.ucm.es)
#   -d  data folder on the server           (default: /opt/catholic-background/data)
#   -o  local folder for the backups        (default: web-backup)
#   -f  flat: a full copy of every image, without hard links to the previous backup
#   -s  use sudo on the server (it must not ask for a password: sudo -n)
#
# - The SQLite database is copied on the server with SQLite's online backup, which is
#   consistent even while the server is writing to it; then it is downloaded.
# - The images (media/) are downloaded with rsync, without the cache of labelled images
#   (the server regenerates it). Images that did not change since the previous backup are
#   hard links to it, so each backup looks complete but only takes the space of what is new
#   (unless -f). Any backup can be deleted without affecting the others.
# - The backup is written to data-….partial and renamed only when everything went well.
set -eu

HOST=simba.fdi.ucm.es
DATA=/opt/catholic-background/data
OUT=web-backup
SUDO=
FLAT=0

usage() {
    sed -n '8,14p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while getopts "H:d:o:fsh" option; do
    case "$option" in
        H) HOST=$OPTARG ;;
        d) DATA=${OPTARG%/} ;;
        o) OUT=${OPTARG%/} ;;
        f) FLAT=1 ;;
        s) SUDO="sudo -n" ;;
        h) usage 0 ;;
        *) usage 1 ;;
    esac
done

for tool in ssh rsync python3; do
    command -v "$tool" > /dev/null || { echo "Error: $tool is not installed" >&2; exit 1; }
done

# Quote a value for the remote shell
quote() {
    printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

# Test on the server: 0 = yes, 1 = no; stops if the server cannot be reached
remote_test() {
    status=0
    ssh "$HOST" "$SUDO test $1 $(quote "$2")" || status=$?
    if [ "$status" -eq 255 ]; then
        echo "Error: could not connect to $HOST with ssh" >&2
        exit 1
    fi
    return "$status"
}

if ! remote_test -d "$DATA"; then
    echo "Error: $DATA does not exist on $HOST (or cannot be read: try -s)" >&2
    exit 1
fi

mkdir -p "$OUT"
# A new name, even if two backups start within the same second
while :; do
    STAMP=$(date +%Y%m%d%H%M%S)
    TARGET="$OUT/data-$STAMP"
    PARTIAL="$TARGET.partial"
    [ -e "$TARGET" ] || [ -e "$PARTIAL" ] || break
    sleep 1
done
PREVIOUS=$(find "$OUT" -maxdepth 1 -type d -name 'data-[0-9]*' ! -name '*.partial' | sort | tail -n 1)
REMOTE_COPY=

cleanup() {
    status=$?
    trap - EXIT
    if [ -n "$REMOTE_COPY" ]; then
        ssh "$HOST" "$SUDO rm -f $(quote "$REMOTE_COPY")" 2> /dev/null || true
    fi
    if [ "$status" -ne 0 ]; then
        rm -rf "$PARTIAL"
        echo "Backup FAILED: nothing was kept." >&2
    fi
}
trap cleanup EXIT
trap 'exit 1' INT TERM HUP

mkdir -p "$PARTIAL"
if [ "$FLAT" -eq 1 ]; then
    echo "Backup of $HOST:$DATA in $TARGET (full copy)"
else
    echo "Backup of $HOST:$DATA in $TARGET"
fi

# 1. Database: consistent copy on the server, then download it
FOUND=0
if remote_test -f "$DATA/db.sqlite3"; then
    FOUND=1
    REMOTE_COPY=$(ssh "$HOST" "$SUDO python3 - $(quote "$DATA/db.sqlite3")" <<'EOF'
import os, sqlite3, sys, tempfile
handle, copy = tempfile.mkstemp(prefix="catholic-background-", suffix=".sqlite3")
os.close(handle)
source = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
target = sqlite3.connect(copy)
with target:
    source.backup(target)
source.close()
target.close()
os.chmod(copy, 0o644)
print(copy)
EOF
)
    echo "  database"
    rsync -a ${SUDO:+--rsync-path="$SUDO rsync"} "$HOST:$REMOTE_COPY" "$PARTIAL/db.sqlite3"
    ssh "$HOST" "$SUDO rm -f $(quote "$REMOTE_COPY")"
    REMOTE_COPY=
    result=$(python3 -c 'import sqlite3, sys; print(sqlite3.connect(sys.argv[1]).execute("PRAGMA integrity_check").fetchone()[0])' "$PARTIAL/db.sqlite3")
    if [ "$result" != "ok" ]; then
        echo "Error: the copy of the database is damaged ($result)" >&2
        exit 1
    fi
else
    echo "  no db.sqlite3 in $DATA (PostgreSQL or MariaDB? back it up with pg_dump or mariadb-dump)"
fi

# 2. Uploaded images, hard-linking the ones that did not change since the previous backup
if remote_test -d "$DATA/media"; then
    FOUND=1
    echo "  images"
    LINK=
    if [ "$FLAT" -eq 0 ] && [ -n "$PREVIOUS" ] && [ -d "$PREVIOUS/media" ]; then
        LINK="--link-dest=$(cd "$PREVIOUS/media" && pwd)"
    fi
    rsync -a --exclude caption-cache ${LINK:+"$LINK"} ${SUDO:+--rsync-path="$SUDO rsync"} \
        "$HOST:$DATA/media/" "$PARTIAL/media/"
else
    echo "  no media folder in $DATA"
fi

if [ "$FOUND" -eq 0 ]; then
    echo "Error: $DATA has neither db.sqlite3 nor media: is it the data folder?" >&2
    exit 1
fi
mv "$PARTIAL" "$TARGET"
images=$(find "$TARGET" -path '*/media/*' -type f 2> /dev/null | wc -l | tr -d ' ')
if [ -n "$PREVIOUS" ] && [ "$FLAT" -eq 0 ]; then
    # du counts each hard-linked file once: the second line is what this backup added
    added=$(du -sh "$PREVIOUS" "$TARGET" | tail -n 1 | cut -f1)
else
    added=$(du -sh "$TARGET" | cut -f1)
fi
echo "Backup done: $TARGET ($images image files, $added new on disk)"
