#!/usr/bin/env python3
"""Print a Bible translation's JSON in plain, readable text.

Usage:
  read_bible.py TRANSLATION.json [BOOK] [CHAPTER]

Examples:
  read_bible.py ../formats/json/AKJV.json
  read_bible.py ../formats/json/AKJV.json Genesis
  read_bible.py ../formats/json/AKJV.json Genesis 1
"""
import json
import sys


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    book_filter = sys.argv[2] if len(sys.argv) > 2 else None
    chapter_filter = int(sys.argv[3]) if len(sys.argv) > 3 else None

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    print(data["translation"])
    print()

    for book in data["books"]:
        if book_filter and book["name"].lower() != book_filter.lower():
            continue
        for chapter in book["chapters"]:
            if chapter_filter and chapter["chapter"] != chapter_filter:
                continue
            print(f"== {book['name']} {chapter['chapter']} ==")
            for verse in chapter["verses"]:
                print(f"{verse['verse']}. {verse['text']}")
            print()


if __name__ == "__main__":
    main()
