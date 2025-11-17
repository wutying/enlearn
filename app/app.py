"""Flask web application for capturing and reviewing vocabulary."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

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

from vocab import DEFAULT_STORAGE, VocabularyStore, get_due_entries, sort_entries
from vocab.services import (
    DEFAULT_TRANSLATION_LANGPAIR,
    add_vocab_entry,
    delete_vocab_entry,
    is_valid_word,
    load_entries,
    lookup_translation,
    lookup_translation_details,
    record_review_result,
    resolve_langpair,
    summarize_reviews,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "enlearn-secret-key"  # Needed for flashing messages

app.config["TRANSLATION_LANGPAIR"] = os.environ.get(
    "TRANSLATION_LANGPAIR", DEFAULT_TRANSLATION_LANGPAIR
)


def get_store() -> VocabularyStore:
    storage_path = Path(app.config.get("VOCAB_STORAGE", DEFAULT_STORAGE))
    return VocabularyStore(storage_path)


def _resolve_langpair() -> tuple[str, str]:
    raw = str(app.config.get("TRANSLATION_LANGPAIR", DEFAULT_TRANSLATION_LANGPAIR))
    return resolve_langpair(raw)


@app.get("/")
def index() -> str:
    store = get_store()
    entries = load_entries(store)
    due_entries = get_due_entries(entries)
    return render_template(
        "index.html",
        due_count=len(due_entries),
        total_count=len(entries),
        storage_path=store.path,
    )


@app.get("/vocab")
def vocab_book() -> str:
    store = get_store()
    entries = load_entries(store)
    sorted_entries = sort_entries(entries)
    due_entries = get_due_entries(entries)
    return render_template(
        "vocab.html",
        entries=sorted_entries,
        due_count=len(due_entries),
        storage_path=store.path,
    )


@app.get("/lookup")
def lookup() -> Response:
    """Lookup a translation for the requested word."""

    word = request.args.get("word", "").strip()
    if not word:
        return jsonify({"status": "empty", "translation": "", "examples": []}), 200

    if not is_valid_word(word):
        return jsonify({"status": "invalid", "translation": "", "examples": []}), 200

    details = lookup_translation_details(word, langpair=_resolve_langpair())
    if not details:
        return jsonify({"status": "not_found", "translation": "", "examples": []}), 200

    translations = details.get("translations") or []
    examples = details.get("examples") or []
    if translations:
        joined = "；".join(translations)
        return (
            jsonify(
                {
                    "status": "ok",
                    "translation": joined,
                    "meanings": translations,
                    "examples": examples[:5],
                }
            ),
            200,
        )

    return (
        jsonify({"status": "not_found", "translation": "", "examples": examples[:5]}),
        200,
    )


@app.get("/api/v1/lookup")
def api_lookup() -> Response:
    word = request.args.get("word", "").strip()
    if not word:
        return jsonify({"error": "empty", "message": "word is required"}), 400
    if not is_valid_word(word):
        return jsonify({"error": "invalid", "message": "word format is invalid"}), 400

    details = lookup_translation_details(word, langpair=_resolve_langpair())
    if not details:
        return jsonify({"error": "not_found", "message": "no translation found"}), 404

    return jsonify({"word": word, **details}), 200


@app.post("/add")
def add_entry_route() -> str:
    store = get_store()
    word = request.form.get("word", "").strip()
    definition = request.form.get("definition", "").strip()
    context = request.form.get("context", "").strip()
    lookup_state = request.form.get("lookup_state", "").strip()

    if not word or not definition:
        flash("請提供單字和解釋，才能新增！", "error")
        return redirect(url_for("index"))

    if not is_valid_word(word):
        flash("請輸入有效的英文單字或片語（僅限英文字母、空格、連字符或撇號）。", "error")
        return redirect(url_for("index"))

    if lookup_state in {"warning", "error", "invalid"}:
        flash("查無此單字，請檢查拼字後再試。", "error")
        return redirect(url_for("index"))

    if lookup_state == "loading":
        flash("請等待翻譯查詢完成後再新增。", "info")
        return redirect(url_for("index"))

    if lookup_state != "success":
        translations = lookup_translation(word)
        if not translations:
            flash("查無此單字，請檢查拼字後再試。", "error")
            return redirect(url_for("index"))

    entry, created = add_vocab_entry(store, word, definition, context)
    if created:
        flash(f"已新增單字 {word}：{definition}", "success")
    else:
        flash(
            f"單字 {word} 已在單字本中，已更新新增次數至 {entry['addition_count']}。",
            "info",
        )
    return redirect(url_for("index"))


@app.post("/vocab/<entry_id>/delete")
def delete_entry(entry_id: str) -> str:
    store = get_store()
    removed_entry = delete_vocab_entry(store, entry_id)

    if removed_entry is None:
        flash("找不到要刪除的單字，可能已被移除。", "error")
        return redirect(url_for("vocab_book"))
    word = removed_entry.get("word") or ""
    flash(f"已刪除單字 {word}", "info")
    return redirect(url_for("vocab_book"))


# ----- JSON APIs for local network clients ---------------------------------


def _load_sorted_entries(store: VocabularyStore) -> List[dict]:
    entries = load_entries(store)
    return sort_entries(entries)


@app.get("/api/v1/vocab")
def api_list_vocab() -> Response:
    store = get_store()
    entries = _load_sorted_entries(store)
    stats = summarize_reviews(entries)
    return jsonify({"entries": entries, **stats}), 200


@app.post("/api/v1/vocab")
def api_add_vocab() -> Response:
    store = get_store()
    payload = request.get_json(silent=True) or {}
    word = str(payload.get("word", "")).strip()
    definition = str(payload.get("definition", "")).strip()
    context = str(payload.get("context", "")).strip()

    if not word or not definition:
        return (
            jsonify({"error": "missing_fields", "message": "word and definition are required"}),
            400,
        )

    if not is_valid_word(word):
        return jsonify({"error": "invalid_word", "message": "word format is invalid"}), 400

    entry, created = add_vocab_entry(store, word, definition, context)
    stats = summarize_reviews(load_entries(store))
    status = "created" if created else "updated"
    return jsonify({"entry": entry, "status": status, **stats}), 201 if created else 200


@app.delete("/api/v1/vocab/<entry_id>")
def api_delete_vocab(entry_id: str) -> Response:
    store = get_store()
    removed = delete_vocab_entry(store, entry_id)
    if removed is None:
        return jsonify({"error": "not_found", "message": "entry does not exist"}), 404
    stats = summarize_reviews(load_entries(store))
    return jsonify({"deleted": entry_id, **stats}), 200


@app.get("/review")
def review() -> str:
    store = get_store()
    entries = load_entries(store)
    due_entries = get_due_entries(entries)
    mode = request.args.get("mode", "").strip()
    if mode not in {"word-first", "definition-first"}:
        return render_template(
            "review_select.html",
            due_count=len(due_entries),
            total_count=len(entries),
            storage_path=store.path,
        )

    current = due_entries[0] if due_entries else None
    remaining = len(due_entries)
    return render_template(
        "review.html",
        entry=current,
        remaining=remaining,
        storage_path=store.path,
        mode=mode,
        due_count=len(due_entries),
        total_count=len(entries),
    )


@app.post("/review/<entry_id>/result")
def review_result(entry_id: str) -> str:
    mode = request.form.get("mode", "word-first")
    result = request.form.get("result")
    remembered = result == "remembered"

    store = get_store()
    answer = request.form.get("answer", "").strip()
    target_entry = record_review_result(
        store,
        entry_id,
        remembered=remembered,
        answer=answer or None,
        mode=mode,
    )

    if target_entry is None:
        flash("找不到這個單字，可能已被刪除。", "error")
        return redirect(url_for("review", mode=mode))

    if mode == "definition-first":
        if answer:
            remembered = answer.casefold() == str(target_entry.get("word", "")).casefold()
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


@app.get("/api/v1/review")
def api_get_review() -> Response:
    store = get_store()
    entries = load_entries(store)
    due_entries = get_due_entries(entries)
    next_entry = due_entries[0] if due_entries else None
    stats = summarize_reviews(entries)
    return jsonify({"next": next_entry, "due_entries": due_entries, **stats}), 200


@app.post("/api/v1/review/<entry_id>")
def api_post_review(entry_id: str) -> Response:
    store = get_store()
    payload = request.get_json(silent=True) or {}
    mode = str(payload.get("mode", "word-first")).strip() or "word-first"
    if mode not in {"word-first", "definition-first"}:
        return jsonify({"error": "invalid_mode", "message": "mode is not supported"}), 400

    result = str(payload.get("result", "")).strip().lower()
    if result not in {"remembered", "forgot"}:
        return jsonify({"error": "invalid_result", "message": "result must be remembered or forgot"}), 400

    remembered = result == "remembered"
    answer = payload.get("answer")
    if isinstance(answer, str):
        answer = answer.strip() or None
    else:
        answer = None

    updated = record_review_result(
        store,
        entry_id,
        remembered=remembered,
        answer=answer,
        mode=mode,
    )
    if updated is None:
        return jsonify({"error": "not_found", "message": "entry does not exist"}), 404

    stats = summarize_reviews(load_entries(store))
    return jsonify({"entry": updated, **stats}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
