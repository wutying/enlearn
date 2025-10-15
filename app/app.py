"""Flask web application for capturing and reviewing vocabulary."""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Optional
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


@functools.lru_cache(maxsize=256)
def lookup_translation(word: str) -> Optional[str]:
    """Fetch a translation for ``word`` from the external API."""

    sanitized = word.strip()
    if not sanitized:
        return None

    params = {"q": sanitized, "langpair": "auto|zh-TW"}
    url = f"{TRANSLATION_ENDPOINT}?{parse.urlencode(params)}"
    req = urlrequest.Request(
        url,
        headers={"User-Agent": "enlearn-vocab-app/1.0"},
    )

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
        # Primary response field
        translation = _normalize_translation(
            data.get("responseData", {}).get("translatedText"), sanitized
        )
        if translation:
            return translation

        # Occasionally there are matches in the response details; pick the first hit
        matches = data.get("matches")
        if isinstance(matches, list):
            for match in matches:
                if not isinstance(match, dict):
                    continue
                translation = _normalize_translation(
                    match.get("translation"), sanitized
                )
                if translation:
                    return translation
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
