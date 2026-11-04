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
