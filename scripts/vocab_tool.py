#!/usr/bin/env python3
"""Simple vocabulary capture and review CLI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vocab import (
    DEFAULT_STORAGE,
    VocabularyStore,
    create_entry,
    get_due_entries,
    sort_entries,
    update_review_state,
)


def load_entries(store: VocabularyStore) -> list[dict[str, object]]:
    try:
        return store.load()
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture and review vocabulary quickly.")
    parser.add_argument("command", choices=["add", "list", "review"], help="Action to perform.")
    parser.add_argument("word", nargs="?", help="Word or phrase to add.")
    parser.add_argument("definition", nargs="?", help="Meaning, translation, or note for the word.")
    parser.add_argument("--context", help="Optional context sentence or note.")
    parser.add_argument("--storage", type=Path, default=DEFAULT_STORAGE, help="Path to the storage JSON file.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum entries to list during review or listing.")
    return parser.parse_args()


def add_entry(store: VocabularyStore, args: argparse.Namespace) -> None:
    if not args.word or not args.definition:
        raise SystemExit("add command requires WORD and DEFINITION arguments.")

    entries = load_entries(store)
    entry = create_entry(args.word, args.definition, args.context or "")
    entries.append(entry)
    store.save(entries)
    print(f"Added '{args.word}' to your vocabulary list. Next review: {entry['next_review']}")


def list_entries(store: VocabularyStore, limit: int) -> None:
    entries = load_entries(store)
    if not entries:
        print("No vocabulary saved yet. Use the add command to capture a new word.")
        return

    sorted_entries = sort_entries(entries)
    print(f"Showing up to {limit} entries (sorted by next review date):")
    for entry in sorted_entries[:limit]:
        print(
            "- {word} :: {definition} "
            "(next review {next}, streak {streak}, reviews {count})".format(
                word=entry["word"],
                definition=entry["definition"],
                next=entry["next_review"],
                streak=entry["success_streak"],
                count=entry.get("review_count", 0),
            )
        )


def review_entries(store: VocabularyStore, limit: int) -> None:
    entries = load_entries(store)
    if not entries:
        print("Your list is empty. Add words first.")
        return

    due_entries = get_due_entries(entries)

    if not due_entries:
        print("No words are due for review today. Great job!")
        return

    count = 0
    print("Type 'y' if you remembered the meaning, 'n' if not, or 'q' to stop.")
    for entry in due_entries:
        if count >= limit:
            break
        print("\nWord:", entry["word"])
        if entry["context"]:
            print("Context:", entry["context"])
        input("Press Enter to reveal the definition...")
        print("Definition:", entry["definition"])
        while True:
            response = input("Did you remember correctly? [y/n/q]: ").strip().lower()
            if response not in {"y", "n", "q"}:
                print("Please respond with 'y', 'n', or 'q'.")
                continue
            break
        if response == "q":
            break
        update_review_state(entry, remembered=response == "y")
        count += 1

    store.save(entries)
    print("Review session complete. Keep going!")

def main() -> None:
    args = parse_args()
    store = VocabularyStore(args.storage)
    if args.command == "add":
        add_entry(store, args)
    elif args.command == "list":
        list_entries(store, args.limit)
    elif args.command == "review":
        review_entries(store, args.limit)
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
