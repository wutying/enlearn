"""Shared data layer and translation utilities for the vocabulary app."""
from __future__ import annotations

import functools
import json
import re
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib import error, parse, request as urlrequest

from . import (
    DEFAULT_STORAGE,
    VocabularyStore,
    create_entry,
    get_due_entries,
    normalize_entries,
    update_review_state,
)

TRANSLATION_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
TRANSLATION_TIMEOUT = 6  # seconds
DEFAULT_TRANSLATION_LANGPAIR = "EN|ZH-TW"
DEFAULT_LANGPAIR_TUPLE: Tuple[str, str] = tuple(DEFAULT_TRANSLATION_LANGPAIR.split("|"))

_LANG_CODE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")
_WORD_VALIDATION_RE = re.compile(r"^[A-Za-z][A-Za-z\s'-]*$")


# ----- Persistence helpers -------------------------------------------------

def get_store(storage_path: Path | str | None = None) -> VocabularyStore:
    storage = Path(storage_path) if storage_path else Path(DEFAULT_STORAGE)
    return VocabularyStore(storage)


def load_entries(store: VocabularyStore) -> List[Dict[str, object]]:
    entries = store.load()
    # Normalization during load may mutate entries; persist if needed.
    if normalize_entries(entries):
        store.save(entries)
    return entries


def add_vocab_entry(
    store: VocabularyStore, word: str, definition: str, context: str = ""
) -> tuple[Dict[str, object], bool]:
    """Add a new vocabulary entry or increment the count if it exists.

    Returns a tuple of (entry, created) where ``created`` indicates whether a
    new record was inserted.
    """

    entries = load_entries(store)
    normalized_word = word.casefold()
    for entry in entries:
        existing_word = entry.get("word")
        if isinstance(existing_word, str) and existing_word.casefold() == normalized_word:
            entry["addition_count"] = entry.get("addition_count", 1) + 1
            store.save(entries)
            return entry, False

    entry = create_entry(word, definition, context)
    entries.append(entry)
    store.save(entries)
    return entry, True


def delete_vocab_entry(
    store: VocabularyStore, entry_id: str
) -> Optional[Dict[str, object]]:
    entries = load_entries(store)
    kept: List[Dict[str, object]] = []
    removed: Optional[Dict[str, object]] = None
    for entry in entries:
        if entry.get("id") == entry_id:
            removed = entry
        else:
            kept.append(entry)
    if removed is not None:
        store.save(kept)
    return removed


def record_review_result(
    store: VocabularyStore,
    entry_id: str,
    remembered: bool,
    *,
    answer: str | None = None,
    mode: str = "word-first",
) -> Optional[Dict[str, object]]:
    entries = load_entries(store)
    target = None
    for entry in entries:
        if entry.get("id") == entry_id:
            target = entry
            break
    if target is None:
        return None

    if mode == "definition-first" and answer is not None:
        remembered = answer.casefold() == str(target.get("word", "")).casefold()

    update_review_state(target, remembered=remembered)
    store.save(entries)
    return target


def summarize_reviews(entries: Iterable[Dict[str, object]]) -> Dict[str, int]:
    entries_list = list(entries)
    return {
        "due_count": len(get_due_entries(entries_list)),
        "total_count": len(entries_list),
    }


# ----- Translation helpers -------------------------------------------------

def _sanitize_lang_code(code: str) -> Optional[str]:
    code = code.strip()
    if not code:
        return None
    match = _LANG_CODE_RE.match(code)
    if not match:
        return None
    primary, _, rest = code.partition("-")
    primary = primary.upper()
    if len(primary) not in (2, 3):
        return None
    if not rest:
        return primary
    return f"{primary}-{rest.upper()}"


def resolve_langpair(raw: str | None) -> Tuple[str, str]:
    raw = str(raw or DEFAULT_TRANSLATION_LANGPAIR)
    segments = raw.split("|")
    if len(segments) != 2:
        return DEFAULT_LANGPAIR_TUPLE
    source = _sanitize_lang_code(segments[0])
    target = _sanitize_lang_code(segments[1])
    if not source or not target:
        return DEFAULT_LANGPAIR_TUPLE
    return source, target


def is_valid_word(word: str) -> bool:
    cleaned = word.strip()
    if not cleaned:
        return False
    return bool(_WORD_VALIDATION_RE.match(cleaned))


def _format_lang_for_google(code: str) -> str:
    primary, _, rest = code.partition("-")
    primary = primary.lower()
    if rest:
        return f"{primary}-{rest.lower()}"
    return primary


def _normalize_translation(raw: Optional[str], original: str) -> Optional[str]:
    if not raw:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    if cleaned.casefold() == original.casefold():
        return None
    return cleaned


def _strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _extract_translations(data: dict, original: str) -> List[str]:
    results: List[str] = []

    def add(value: Optional[str]) -> None:
        normalized = _normalize_translation(value, original)
        if normalized and normalized not in results:
            results.append(normalized)

    sentences = data.get("sentences")
    if isinstance(sentences, list):
        for sentence in sentences:
            if isinstance(sentence, dict):
                add(sentence.get("trans"))
            elif isinstance(sentence, list) and sentence:
                add(str(sentence[0]))

    dictionary_entries = data.get("dict")
    if isinstance(dictionary_entries, list):
        for entry in dictionary_entries:
            if not isinstance(entry, dict):
                continue
            terms = entry.get("terms")
            if isinstance(terms, list):
                for term in terms:
                    add(str(term))
            entry_terms = entry.get("entry")
            if isinstance(entry_terms, list):
                for item in entry_terms:
                    if isinstance(item, dict):
                        add(item.get("word"))

    alternative_translations = data.get("alternative_translations")
    if isinstance(alternative_translations, list):
        for alt in alternative_translations:
            if not isinstance(alt, dict):
                continue
            entries = alt.get("entries")
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        add(entry.get("word"))

    return results


def _extract_examples(data: dict) -> List[str]:
    results: List[str] = []

    examples_section = data.get("examples")
    if isinstance(examples_section, dict):
        items = examples_section.get("example")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                raw = item.get("text")
                if not isinstance(raw, str):
                    continue
                cleaned = unescape(_strip_html_tags(raw)).strip()
                if cleaned and cleaned not in results:
                    results.append(cleaned)

    return results


def _fetch_translation_payload(word: str, langpair: Tuple[str, str]) -> Optional[dict]:
    source, target = langpair
    params = {
        "client": "gtx",
        "sl": _format_lang_for_google(source),
        "tl": _format_lang_for_google(target),
        "dj": "1",
        "dt": ["t", "bd", "md", "at", "ex"],
        "q": word,
    }
    query_parts: List[Tuple[str, str]] = []
    for key, value in params.items():
        if isinstance(value, list):
            for item in value:
                query_parts.append((key, item))
        else:
            query_parts.append((key, value))
    url = f"{TRANSLATION_ENDPOINT}?{parse.urlencode(query_parts)}"
    req = urlrequest.Request(url, headers={"User-Agent": "enlearn-vocab-app/1.0"})

    try:
        with urlrequest.urlopen(req, timeout=TRANSLATION_TIMEOUT) as resp:
            payload = resp.read()
    except (error.URLError, TimeoutError, ValueError, OSError):
        return None

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict):
        return data
    return None


@functools.lru_cache(maxsize=256)
def _lookup_translation_data_cached(sanitized_word: str, langpair: Tuple[str, str]) -> Optional[dict]:
    data = _fetch_translation_payload(sanitized_word, langpair)
    if not data and langpair != DEFAULT_LANGPAIR_TUPLE:
        data = _fetch_translation_payload(sanitized_word, DEFAULT_LANGPAIR_TUPLE)
    return data


def _get_translation_data(word: str, langpair: Tuple[str, str]) -> Optional[dict]:
    sanitized = word.strip()
    if not sanitized:
        return None
    return _lookup_translation_data_cached(sanitized, langpair)


def lookup_translation(
    word: str, *, langpair: str | Tuple[str, str] | None = None
) -> Optional[List[str]]:
    sanitized = word.strip()
    if not sanitized:
        return None
    pair = resolve_langpair("|".join(langpair) if isinstance(langpair, tuple) else langpair)
    data = _get_translation_data(sanitized, pair)
    if not data:
        return None
    translations = _extract_translations(data, sanitized)
    return translations or None


def lookup_translation_details(
    word: str, *, langpair: str | Tuple[str, str] | None = None
) -> Optional[Dict[str, object]]:
    sanitized = word.strip()
    if not sanitized:
        return None
    pair = resolve_langpair("|".join(langpair) if isinstance(langpair, tuple) else langpair)
    data = _get_translation_data(sanitized, pair)
    if not data:
        return None
    translations = _extract_translations(data, sanitized)
    examples = _extract_examples(data)
    return {"translations": translations, "examples": examples}

