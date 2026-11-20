# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Machine translation with LibreTranslate (https://libretranslate.com) of the texts of the artworks
into the languages that have no translation written by hand.

- Each text is translated once and kept in MachineTranslation; changing a text translates it again.
- Only for showing them: nothing is written into the texts of the artworks.
- If LibreTranslate cannot be reached, the texts are shown in their own language, as without it,
  and it is not asked again for a few minutes.
- What is shown translated always says so and gives the credit to LibreTranslate.
"""
import hashlib
import json
import logging
import re
import urllib.error
import urllib.request

from django.conf import settings
from django.conf.locale import LANG_INFO
from django.core.cache import cache
from django.db import IntegrityError
from django.utils import timezone

from .models import MachineTranslation

logger = logging.getLogger(__name__)

SERVICE = "LibreTranslate"
CREDIT_URL = "https://libretranslate.com"
NOTICE = "Machine translation"          # translated into each language, followed by "(LibreTranslate)"
DOWN = "libretranslate-down"
BATCH = 4000                            # characters per request


def _config(name):
    return settings.CATHOLIC_BACKGROUND.get(name)


def enabled():
    return bool(_config("LIBRETRANSLATE_URL"))


def _call(path, payload=None):
    url = _config("LIBRETRANSLATE_URL").rstrip("/") + path
    headers = {"Accept": "application/json", "User-Agent": "catholic-background-server"}
    data = None
    if payload is not None:
        if _config("LIBRETRANSLATE_API_KEY"):
            payload = {**payload, "api_key": _config("LIBRETRANSLATE_API_KEY")}
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=_config("LIBRETRANSLATE_TIMEOUT")) as answer:
        return json.load(answer)


def _available():
    return enabled() and not cache.get(DOWN)


def _failed(error):
    logger.warning("LibreTranslate could not be used: %s", error)
    cache.set(DOWN, True, 300)          # do not make every visitor wait for it


def local_name(code, fallback=""):
    """Name of a language in that language ("Français"), or the name LibreTranslate gives."""
    info = LANG_INFO.get(code.lower()) or LANG_INFO.get(code.lower().split("-")[0])
    name = (info or {}).get("name_local") or fallback or code
    return name[:1].upper() + name[1:]


def languages(source):
    """[(code, name)] of the languages LibreTranslate translates `source` into, by name (cached for a day)."""
    if not enabled():
        return []
    key = f"libretranslate-languages-{source}"
    found = cache.get(key)
    if found is not None:
        return found
    try:
        data = _call("/languages")
        codes = {entry["code"] for entry in data}
        origin = next((entry for entry in data if entry["code"] == source), None)
        if origin is None:
            found = []
        else:
            targets = set(origin.get("targets") or codes)      # old versions: every language
            found = sorted(((entry["code"], local_name(entry["code"], entry.get("name", "")))
                            for entry in data if entry["code"] in targets and entry["code"] != source),
                           key=lambda item: item[1].casefold())
        cache.set(key, found, 86400)
    except (OSError, ValueError, KeyError, TypeError) as error:
        logger.warning("LibreTranslate languages could not be read: %s", error)
        found = []
        cache.set(key, found, 600)
    return found


def _key(text):
    return hashlib.sha256(text.encode()).hexdigest()


def translate(texts, source, target):
    """The texts translated (same order), or None if LibreTranslate could not translate them."""
    texts = list(texts)
    if source == target:
        return texts
    result = [text if not text.strip() else None for text in texts]
    keys = {text: _key(text) for text in texts if text.strip()}
    stored = {row.key: row for row in MachineTranslation.objects.filter(source=source, target=target,
                                                                         key__in=set(keys.values()))}
    today = timezone.localdate()
    old = [row.pk for row in stored.values() if row.used != today]
    if old:
        MachineTranslation.objects.filter(pk__in=old).update(used=today)
    missing = []
    for index, text in enumerate(texts):
        if result[index] is None:
            row = stored.get(keys[text])
            if row is not None:
                result[index] = row.text
            elif text not in missing:
                missing.append(text)
    if missing:
        if not _available():
            return None
        translated = {}
        try:
            for batch in _batches(missing):
                answer = _call("/translate", {"q": batch, "source": source, "target": target, "format": "text"})
                outputs = answer["translatedText"]
                if isinstance(outputs, str):
                    outputs = [outputs]
                if len(outputs) != len(batch):
                    raise ValueError("LibreTranslate answered a different number of texts")
                translated.update(zip(batch, outputs))
        except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError) as error:
            _failed(error)
            return None
        for text, output in translated.items():
            try:
                MachineTranslation.objects.get_or_create(source=source, target=target, key=keys[text],
                                                         defaults={"text": output})
            except IntegrityError:      # translated at the same time by another request
                pass
        result = [translated.get(text, value) if value is None else value for text, value in zip(texts, result)]
    return result


def _batches(texts):
    batch, size = [], 0
    for text in texts:
        if batch and size + len(text) > BATCH:
            yield batch
            batch, size = [], 0
        batch.append(text)
        size += len(text)
    if batch:
        yield batch


def notice(target):
    """ "Machine translation (LibreTranslate)" in the target language (in English if it cannot be translated)."""
    translated = translate([NOTICE], "en", target) if target != "en" else [NOTICE]
    return f"{translated[0] if translated else NOTICE} ({SERVICE})"


def _worth(text):
    """Only texts with words: not "1668-1669", and not those with addresses (licenses with links)."""
    return bool(re.search(r"[^\W\d_]{2}", text)) and "://" not in text


def translate_artwork(texts, reason, extra, target):
    """
    Texts of an artwork (as Artwork.texts), its reason and additional data, translated into target:
    (texts, reason, extra, notice), or None if they could not be translated. The author is a name and
    is not translated.
    """
    source = texts.get("language") or ""
    if not source:
        return None
    fields = [field for field in ("title", "description", "year", "license") if texts.get(field) and _worth(texts[field])]
    names, values = list(extra.keys()), list(extra.values())
    originals = [texts[field] for field in fields] + ([reason] if reason else []) + names + values
    translated = translate(originals, source, target)
    if translated is None:
        return None
    new_texts = {**texts, **dict(zip(fields, translated[:len(fields)])), "language": target}
    rest = translated[len(fields):]
    new_reason = rest.pop(0) if reason else ""
    new_extra = dict(zip(rest[:len(names)], [value if _worth(value) else original
                                             for value, original in zip(rest[len(names):], values)]))
    return new_texts, new_reason, new_extra, notice(target)
