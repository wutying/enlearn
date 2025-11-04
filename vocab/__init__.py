"""Core utilities for the vocabulary tracker."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List

DEFAULT_STORAGE = Path.home() / ".enlearn" / "vocab.json"
DATE_FMT = "%Y-%m-%d"


class VocabularyStore:
    """Handle persistence of vocabulary entries."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Storage file {self.path} is corrupted. Please fix or delete it."
                ) from exc
        if not isinstance(data, list):
            raise ValueError("Storage file must contain a list of entries.")

        changed = normalize_entries(data)
        if changed:
            self.save(data)
        return data

    def save(self, entries: List[Dict[str, Any]]) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)


def normalize_entries(entries: Iterable[Dict[str, Any]]) -> bool:
    """Ensure entries contain all required fields.

    Returns True if any mutation was performed that should be persisted.
    """

    changed = False
    for entry in entries:
        if "id" not in entry:
            entry["id"] = str(uuid.uuid4())
            changed = True
        if "created_at" not in entry:
            entry["created_at"] = datetime.utcnow().strftime(DATE_FMT)
            changed = True
        if "interval_days" not in entry:
            entry["interval_days"] = 1
            changed = True
        if "success_streak" not in entry:
            entry["success_streak"] = 0
            changed = True
        if "context" not in entry:
            entry["context"] = ""
            changed = True
        if "next_review" not in entry:
            entry["next_review"] = entry["created_at"]
            changed = True
        if "review_count" not in entry:
            entry["review_count"] = 0
            changed = True
    return changed


def create_entry(word: str, definition: str, context: str = "", now: datetime | None = None) -> Dict[str, Any]:
    now = now or datetime.utcnow()
    return {
        "id": str(uuid.uuid4()),
        "word": word,
        "definition": definition,
        "context": context,
        "created_at": now.strftime(DATE_FMT),
        "next_review": now.strftime(DATE_FMT),
        "interval_days": 1,
        "success_streak": 0,
        "review_count": 0,
    }


def sort_entries(entries: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return entries sorted by review urgency and recency.

    Entries with the fewest reviews appear first. When review counts are
    identical we prioritise the most recently added words so that newly added
    vocabulary stays near the top of the list. As a final tie-breaker we sort
    alphabetically by the word itself to keep the ordering stable.
    """

    def _review_count(entry: Dict[str, Any]) -> int:
        try:
            return int(entry.get("review_count", 0))
        except (TypeError, ValueError):
            return 0

    def _created_at_order(entry: Dict[str, Any]) -> int:
        raw = entry.get("created_at")
        if isinstance(raw, str):
            try:
                created_at = datetime.strptime(raw, DATE_FMT)
            except ValueError:
                created_at = datetime.min
        else:
            created_at = datetime.min
        # Use a negative ordinal so that more recent dates (with a larger
        # ordinal) end up earlier in the ascending sort order.
        return -created_at.toordinal()

    def _word_key(entry: Dict[str, Any]) -> str:
        word = entry.get("word")
        if isinstance(word, str):
            return word
        return ""

    return sorted(
        entries,
        key=lambda entry: (_review_count(entry), _created_at_order(entry), _word_key(entry)),
    )


def get_due_entries(entries: Iterable[Dict[str, Any]], as_of: datetime | None = None) -> List[Dict[str, Any]]:
    as_of_date = (as_of or datetime.utcnow()).date()
    due_entries: List[tuple[Dict[str, Any], datetime]] = []
    for entry in entries:
        try:
            next_review = datetime.strptime(entry["next_review"], DATE_FMT).date()
        except (KeyError, ValueError):
            next_review = as_of_date
        if next_review <= as_of_date:
            due_entries.append((entry, datetime.combine(next_review, datetime.min.time())))
    due_entries.sort(key=lambda item: item[1])
    return [entry for entry, _ in due_entries]


def update_review_state(entry: Dict[str, Any], remembered: bool, today: datetime | None = None) -> None:
    today = (today or datetime.utcnow()).date()
    if remembered:
        entry["success_streak"] = entry.get("success_streak", 0) + 1
        interval = entry.get("interval_days", 1)
        interval = max(1, min(30, interval * 2))
        entry["interval_days"] = interval
    else:
        entry["success_streak"] = 0
        entry["interval_days"] = 1
    next_review_date = today + timedelta(days=entry["interval_days"])
    entry["next_review"] = next_review_date.strftime(DATE_FMT)
    entry["review_count"] = entry.get("review_count", 0) + 1

