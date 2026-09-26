# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

UUID = catholic-background@luis.llana.diaz
ZIP = $(UUID).shell-extension.zip

.PHONY: pack install uninstall clean

# Zip ready to upload to https://extensions.gnome.org/upload/
pack: $(ZIP)

$(ZIP): metadata.json extension.js prefs.js lib/*.js schemas/*.xml LICENSE
	gnome-extensions pack --force \
		--extra-source=lib \
		--extra-source=LICENSE \
		.

install: $(ZIP)
	gnome-extensions install --force $(ZIP)
	@echo "Log out and back in (Wayland), then: gnome-extensions enable $(UUID)"

uninstall:
	gnome-extensions uninstall $(UUID)

clean:
	rm -f $(ZIP)
