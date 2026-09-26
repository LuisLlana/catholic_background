#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Minimal server for the "Catholic background of the day" Plasma provider.

On every request it picks a random image from a directory (./images by
default) and returns it wrapped in the JSON expected by the provider:

    GET /background?ts=<timestamp>  ->  {"image": "<base64>", "title": ..., "author": ..., "date": ...}

Metadata is optional: for an image "annunciation.jpg", the server reads
"annunciation.json" from the same directory if it exists, e.g.

    {"title": "The Annunciation", "author": "Fra Angelico", "date": "1426"}

Usage:
    ./serve_image.py [--images DIR] [--host HOST] [--port PORT] [--path PATH]
"""

import argparse
import base64
import json
import random
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
METADATA_KEYS = ("title", "author", "date")


def list_images(directory):
    """Images in the directory, read on every request so new files are picked up."""
    return [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]


def read_metadata(image):
    """Optional metadata from <image stem>.json next to the image."""
    sidecar = image.with_suffix(".json")
    if not sidecar.is_file():
        return {}
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"warning: ignoring {sidecar}: {e}", file=sys.stderr)
        return {}
    return {k: str(data[k]) for k in METADATA_KEYS if data.get(k) not in (None, "")}


def build_payload(image):
    payload = {"image": base64.b64encode(image.read_bytes()).decode("ascii")}
    payload.update(read_metadata(image))
    return json.dumps(payload).encode("utf-8")


def make_handler(path, directory):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            if url.path != path:
                self.send_error(404)
                return

            # Informational only: show which day the client is asking for.
            ts = parse_qs(url.query).get("ts", [None])[0]
            day = None
            if ts is not None:
                try:
                    # Local midnight + 12 h falls on the client's day in UTC.
                    day = datetime.fromtimestamp(int(ts) + 12 * 3600, tz=timezone.utc).date()
                except (ValueError, OverflowError, OSError):
                    self.send_error(400, "invalid ts")
                    return

            images = list_images(directory)
            if not images:
                self.send_error(503, f"no images in {directory}")
                return

            image = random.choice(images)
            try:
                body = build_payload(image)
            except OSError as e:
                self.send_error(500, f"cannot read {image.name}: {e}")
                return

            self.log_message("client day: %s -> %s", day, image.name)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            # The image is random on every request, so it must not be cached.
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Serve a random image from a directory as the background of the day.")
    parser.add_argument("--images", default="images", help="directory with the images (default: ./images)")
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="port (default: 8000)")
    parser.add_argument("--path", default="/background", help="URL path (default: /background)")
    args = parser.parse_args()

    directory = Path(args.images)
    if not directory.is_dir():
        sys.exit(f"error: {directory} is not a directory")
    count = len(list_images(directory))
    if count == 0:
        print(f"warning: {directory} has no images yet", file=sys.stderr)

    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.path, directory))
    print(f"Serving {count} image(s) from {directory.resolve()} at http://{args.host}:{args.port}{args.path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
