# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""login-background on a fake / (CATHOLIC_BACKGROUND_ROOT): greeters configured and restored as they were.

    python3 -m unittest discover tests
"""

import base64
import filecmp
import http.server
import io
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest

from PIL import Image

HELPER = os.path.join(os.path.dirname(__file__), "..", "login", "login-background")


class FakeServer(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        picture = io.BytesIO()
        Image.new("RGB", (800, 600), "#336699").save(picture, "JPEG")
        body = json.dumps({"image": base64.b64encode(picture.getvalue()).decode(), "title": "Test"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class LoginBackgroundTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = http.server.HTTPServer(("127.0.0.1", 0), FakeServer)
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.http.server_port}/background"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()

    def setUp(self):
        self.root = tempfile.mkdtemp()
        for folder in ("usr/share/sddm/themes/breeze", "usr/bin", "usr/sbin", "etc/lightdm"):
            os.makedirs(os.path.join(self.root, folder))
        for program in ("usr/bin/sddm", "usr/sbin/lightdm-gtk-greeter", "usr/sbin/slick-greeter"):
            open(os.path.join(self.root, program), "w").close()
        with open(os.path.join(self.root, "etc/lightdm/slick-greeter.conf"), "w") as f:
            f.write("[Greeter]\ntheme-name=Adwaita\n")
        self.original = tempfile.mkdtemp()
        shutil.copytree(self.root, self.original, dirs_exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root)
        shutil.rmtree(self.original)

    def run_helper(self, *arguments):
        return subprocess.run([HELPER, *arguments], capture_output=True, text=True,
                              env=dict(os.environ, CATHOLIC_BACKGROUND_ROOT=self.root))

    def file(self, name):
        with open(os.path.join(self.root, name), encoding="utf-8") as f:
            return f.read()

    def test_enable_and_disable(self):
        status = json.loads(self.run_helper("status").stdout)
        self.assertFalse(status["enabled"])
        self.assertEqual(len(status["greeters"]), 3)
        result = self.run_helper("enable", "--server", self.url, "--size", "1280x800", "--background", "average")
        self.assertEqual(result.returncode, 0, result.stderr)
        image = "/var/lib/catholic-background/login.jpg"
        with Image.open(self.root + image) as login:
            self.assertEqual(login.size, (1280, 800))
        self.assertIn(image, self.file("usr/share/sddm/themes/breeze/theme.conf.user"))
        self.assertIn(f"background={image}", self.file("etc/lightdm/lightdm-gtk-greeter.conf.d/90-catholic-background.conf"))
        slick = self.file("etc/lightdm/slick-greeter.conf")
        self.assertIn(image, slick)
        self.assertIn("theme-name", slick)
        self.assertTrue(json.loads(self.run_helper("status").stdout)["enabled"])

        self.assertEqual(self.run_helper("disable").returncode, 0)
        self.assertFalse(json.loads(self.run_helper("status").stdout)["enabled"])
        for folder in ("usr", "etc/lightdm"):
            comparison = filecmp.dircmp(os.path.join(self.original, folder), os.path.join(self.root, folder))
            self.assertFalse(comparison.left_only or comparison.right_only or comparison.diff_files, folder)
        self.assertFalse(os.path.exists(os.path.join(self.root, "usr/share/sddm/themes/breeze/theme.conf.user")))

    def test_wrong_settings_are_refused(self):
        for arguments in (["--server", "file:///etc/shadow"], ["--server", self.url, "--size", "1x1"],
                          ["--server", self.url, "--color", "red;rm"], ["--server", self.url, "--lang", "../x"]):
            self.assertNotEqual(self.run_helper("enable", *arguments).returncode, 0, arguments)
        self.assertFalse(os.path.exists(os.path.join(self.root, "etc/catholic-background/login.conf")))

    def test_no_greeter(self):
        for program in ("usr/bin/sddm", "usr/sbin/lightdm-gtk-greeter", "usr/sbin/slick-greeter"):
            os.remove(os.path.join(self.root, program))
        shutil.rmtree(os.path.join(self.root, "usr/share/sddm"))
        self.assertNotEqual(self.run_helper("enable", "--server", self.url).returncode, 0)


if __name__ == "__main__":
    unittest.main()
