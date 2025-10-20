"""Flask web application for capturing and reviewing vocabulary."""
from __future__ import annotations

import functools
import json
import os
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib import error, parse, request as urlrequest

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from vocab import (
    DEFAULT_STORAGE,
    VocabularyStore,
    create_entry,
    get_due_entries,
    sort_entries,
    update_review_state,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "enlearn-secret-key"  # Needed for flashing messages

TRANSLATION_ENDPOINT = "https://api.mymemory.translated.net/get"
TRANSLATION_TIMEOUT = 6  # seconds
DEFAULT_TRANSLATION_LANGPAIR = "EN|ZH-TW"
# Accept ISO-639 two/three letter language codes with an optional region/script
# segment (e.g. ``EN``, ``EN-US``, ``ZH-TW``, ``SR-LATN``). Wider values such as
# ``AUTO`` are rejected so we can gracefully fall back to the safe default.
_LANG_CODE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")


app.config["TRANSLATION_LANGPAIR"] = os.environ.get(
    "TRANSLATION_LANGPAIR", DEFAULT_TRANSLATION_LANGPAIR
)


def get_store() -> VocabularyStore:
    storage_path = Path(app.config.get("VOCAB_STORAGE", DEFAULT_STORAGE))
    return VocabularyStore(storage_path)


def _normalize_translation(raw: Optional[str], original: str) -> Optional[str]:
    if not raw:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    if cleaned.casefold() == original.casefold():
        # Some providers echo the source text when no translation is found.
        return None
    return cleaned


def _sanitize_lang_code(code: str) -> Optional[str]:
    code = code.strip()
    if not code:
        return None

    match = _LANG_CODE_RE.match(code)
    if not match:
        return None

    primary, _, rest = code.partition("-")
    primary = primary.upper()
    # ``_LANG_CODE_RE`` already guarantees 2-3 characters for the primary tag,
    # but we keep the explicit guard to make the intent obvious and future-
    # proof the check should the regex change.
    if len(primary) not in (2, 3):
        return None

    if not rest:
        return primary

    return f"{primary}-{rest.upper()}"


def _resolve_langpair() -> str:
    raw = str(app.config.get("TRANSLATION_LANGPAIR", DEFAULT_TRANSLATION_LANGPAIR))
    segments = raw.split("|")
    if len(segments) != 2:
        return DEFAULT_TRANSLATION_LANGPAIR
    source = _sanitize_lang_code(segments[0])
    target = _sanitize_lang_code(segments[1])
    if not source or not target:
        return DEFAULT_TRANSLATION_LANGPAIR
    return f"{source}|{target}"


def _fetch_translation_payload(word: str, langpair: str) -> Tuple[Optional[dict], Optional[str]]:
    params = {"q": word, "langpair": langpair}
    url = f"{TRANSLATION_ENDPOINT}?{parse.urlencode(params)}"
    req = urlrequest.Request(
        url,
        headers={"User-Agent": "enlearn-vocab-app/1.0"},
    )

    try:
        with urlrequest.urlopen(req, timeout=TRANSLATION_TIMEOUT) as resp:
            payload = resp.read()
    except (error.URLError, TimeoutError, ValueError, OSError):
        return None, None

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None, None

    if isinstance(data, dict):
        status = data.get("responseStatus")
        if isinstance(status, int) and status != 200:
            details = data.get("responseDetails")
            return data, str(details) if details else None
        return data, None
    return None, None


def _extract_translation(data: dict, original: str) -> Optional[str]:
    translation = _normalize_translation(
        data.get("responseData", {}).get("translatedText"), original
    )
    if translation:
        return translation

    matches = data.get("matches")
    if isinstance(matches, list):
        for match in matches:
            if not isinstance(match, dict):
                continue
            translation = _normalize_translation(match.get("translation"), original)
            if translation:
                return translation
    return None


def _should_retry_with_default(details: Optional[str]) -> bool:
    if not details:
        return False
    normalized = details.upper()
    return "INVALID SOURCE LANGUAGE" in normalized or "LANGPAIR" in normalized


@functools.lru_cache(maxsize=256)
def lookup_translation(word: str) -> Optional[str]:
    """Fetch a translation for ``word`` from the external API."""

    sanitized = word.strip()
    if not sanitized:
        return None

    langpair = _resolve_langpair()
    data, details = _fetch_translation_payload(sanitized, langpair)
    if data:
        translation = _extract_translation(data, sanitized)
        if translation:
            return translation

    if _should_retry_with_default(details) and langpair != DEFAULT_TRANSLATION_LANGPAIR:
        fallback_data, _ = _fetch_translation_payload(sanitized, DEFAULT_TRANSLATION_LANGPAIR)
        if fallback_data:
            return _extract_translation(fallback_data, sanitized)

    return None


@app.get("/")
def index() -> str:
    store = get_store()
    entries = store.load()
    sorted_entries = sort_entries(entries)
    due_entries = get_due_entries(entries)
    return render_template(
        "index.html",
        entries=sorted_entries,
        due_count=len(due_entries),
        storage_path=store.path,
    )


@app.get("/lookup")
def lookup() -> Response:
    """Lookup a translation for the requested word."""

    word = request.args.get("word", "").strip()
    if not word:
        return jsonify({"status": "empty", "translation": ""}), 200

    translation = lookup_translation(word)
    if translation:
        return jsonify({"status": "ok", "translation": translation}), 200

    return jsonify({"status": "not_found", "translation": ""}), 200


@app.post("/add")
def add_entry_route() -> str:
    store = get_store()
    word = request.form.get("word", "").strip()
    definition = request.form.get("definition", "").strip()
    context = request.form.get("context", "").strip()

    if not word or not definition:
        flash("請提供單字和解釋，才能新增！", "error")
        return redirect(url_for("index"))

    entries = store.load()
    entries.append(create_entry(word, definition, context))
    store.save(entries)
    flash(f"已新增單字 {word}：{definition}", "success")
    return redirect(url_for("index"))


@app.get("/review")
def review() -> str:
    store = get_store()
    entries = store.load()
    due_entries = get_due_entries(entries)
    current = due_entries[0] if due_entries else None
    remaining = len(due_entries)
    mode = request.args.get("mode", "word-first")
    if mode not in {"word-first", "definition-first"}:
        mode = "word-first"
    return render_template(
        "review.html",
        entry=current,
        remaining=remaining,
        storage_path=store.path,
        mode=mode,
    )


@app.post("/review/<entry_id>/result")
def review_result(entry_id: str) -> str:
    mode = request.form.get("mode", "word-first")
    result = request.form.get("result")
    remembered = result == "remembered"

    store = get_store()
    entries = store.load()
    target_entry = None
    for entry in entries:
        if entry.get("id") == entry_id:
            target_entry = entry
            if mode == "definition-first":
                answer = request.form.get("answer", "").strip()
                if answer:
                    remembered = answer.casefold() == entry.get("word", "").casefold()
            break
    else:
        flash("找不到這個單字，可能已被刪除。", "error")
        return redirect(url_for("review", mode=mode))

    update_review_state(target_entry, remembered=remembered)
    store.save(entries)

    if mode == "definition-first":
        if remembered:
            flash(
                f"回答正確！已累積複習 {target_entry['review_count']} 次。",
                "success",
            )
        else:
            flash(
                f"正確答案是 {target_entry.get('word', '')}，已累積複習 {target_entry['review_count']} 次。",
                "info",
            )
        return redirect(url_for("review", mode=mode))

    if remembered:
        flash(
            f"太棒了！繼續加油！已累積複習 {target_entry['review_count']} 次。",
            "success",
        )
    else:
        flash(
            f"沒關係，已幫你安排近期再複習。已累積複習 {target_entry['review_count']} 次。",
            "info",
        )
    return redirect(url_for("review", mode=mode))


@app.post("/review/<entry_id>/skip")
def review_skip(entry_id: str) -> str:
    """Skip reviewing the current word without changing its schedule."""
    mode = request.form.get("mode", "word-first")
    flash("已跳過此單字，下次再試！", "info")
    return redirect(url_for("review", mode=mode))


if __name__ == "__main__":
    app.run(debug=True)
