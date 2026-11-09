# TODO

## Formatting in the comments of the artworks (Markdown)

Now the comment (`description`) is plain text: only line breaks are kept. Markdown
or HTML written in it is shown as it is (asterisks, tags) in the browser page and
in the applications. The browser page escapes it on purpose, so no code can be
put in the page.

Plan:

1. **Server**
   - Editors write the comment as now, but Markdown is accepted: `**bold**`,
     `*italic*`, links `[text](https://…)`, paragraphs and lists. No free HTML
     (risky, and harder for editors).
   - The API sends two versions:
     - `description`: clean text, without the marks, so that the current
       applications go on showing it well (no asterisks).
     - `description_html` (new): converted to HTML and sanitized, allowing only
       bold, italic, http(s) links, paragraphs and lists.
   - Help text of the field in the content manager explaining the marks.
   - Tests: conversion, sanitizing (scripts, `javascript:` links and the like are
     removed), clean text.
2. **Browser page** (`/background/browser/`): shows the comment with its format.
3. **Applications** (they can be updated one by one; until then they show the
   clean text):
   - KDE: `Text.StyledText` / `RichText` in QML.
   - GNOME: Pango markup in `Gtk.Label` (convert the allowed HTML to Pango).
   - Android: `AnnotatedString.fromHtml` in Compose.
   - Windows: needs another text control (e.g. `RichTextBox` or a small
     `WebView2`): the one that costs most.

The label drawn by the server below the image does not include the comment, so it
is not affected.

## Move the server from simba to a cloud server

Not now; notes for when it is done.

- **Size**: a small VPS is enough: 1-2 vCPU, 2 GB of RAM, 20-40 GB of disk
  (depending on the images uploaded).
- **Providers** (prices of late 2026, check them before):
  Clouding.io (Barcelona, from about 3 €/month, billed by the hour; backups
  extra), IONOS VPS S (2 vCPU, 2 GB, 80 GB; 3 €/month + VAT the first 24 months,
  then 4 €; 10 € setup), Hetzner CX23 (Germany/Finland, 5.99 €/month with
  IPv4), Contabo (from 5.50 €), Arsys Cloud (Spain, from 6.10 € with VAT),
  OVHcloud VPS-1 (7.79 €/month since April 2026), Raiola Networks (Madrid, from
  12.04 € with VAT).
- **Address of the server**: every application (Android, Windows, KDE, GNOME,
  Python module) has `https://simba.fdi.ucm.es/background` as the default server.
  - Keep a permanent redirect (301) of `/background` on simba's nginx to the
    new address: the five applications follow redirects, so the installed ones
    go on working.
  - New versions of the applications with the new default URL, in case simba
    disappears.
- **Domain** of our own (about 10-15 €/year) with an HTTPS certificate from
  Let's Encrypt.
- **Login with Google and Microsoft**: add the new callback URL in their consoles.
- **Data**: copy `data/` (database and images) with
  `catholic-background-backup.sh -f` and install the server as its README says
  (`migrate`, `collectstatic`, systemd units, nginx snippet).
