#!/usr/bin/env python3
"""Discover downloadable source PDFs from Mind Released pages."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


USER_AGENT = "Mozilla/5.0"
DEFAULT_PAGES = [
    "https://www.mindreleased.com/pali-suttas",
    "https://www.mindreleased.com/sutta-nipata",
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            text = " ".join("".join(self._text).split())
            self.links.append((self._href, text))
            self._href = None
            self._text = []


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", "replace")


def canonical_id(label: str, url: str) -> str | None:
    text = f"{label} {url}"
    roman_an_match = re.search(
        r"\bAN\s+VIII\b.*?\bSuttas?\s+(\d+)\s*-\s*(\d+)\b",
        text,
        flags=re.IGNORECASE,
    )
    if roman_an_match:
        return f"AN 8.{roman_an_match.group(1)}-{roman_an_match.group(2)}"

    patterns = [
        r"\bDN\s*[-.]?\s*(\d+)\b",
        r"\bMN\s*[-.]?\s*(\d+)\b",
        r"\bSN\s*[-.]?\s*(\d+)[.-](\d+)\b",
        r"\bAN\s*[-.]?\s*(\d+)[.-](\d+)\b",
        r"\bUd\.?\s*[-.]?\s*(\d+)[.-](\d+)\b",
        r"\bSnp\.?\s*[-.]?\s*(\d+)[.-](\d+)\b",
        r"\bThag\.?\s*[-.]?\s*(\d+)[.-](\d+)\b",
        r"\bDhp\.?\s*[-.]?\s*(\d+)[.-](\d+)\b",
        r"\bMil\.?\s*[-.]?\s*(\d+)[.-](\d+)(?:[.-](\d+))?\b",
    ]
    prefixes = ["DN", "MN", "SN", "AN", "Ud", "Snp", "Thag", "Dhp", "Mil"]
    for prefix, pattern in zip(prefixes, patterns):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return f"{prefix} " + ".".join(part for part in match.groups() if part)
    return None


def source_id_for_page_link(page_url: str, source_url: str, label: str) -> str | None:
    if page_url.rstrip("/") == "https://www.mindreleased.com/sutta-nipata":
        return "Snp complete"
    return canonical_id(label, source_url)


def source_label_for_page_link(page_url: str, label: str) -> str | None:
    if page_url.rstrip("/") == "https://www.mindreleased.com/sutta-nipata":
        return "Sutta Nipata complete PDF"
    if label:
        return label
    return None


def discover_page(page_url: str) -> list[dict[str, str | None]]:
    parser = LinkParser()
    parser.feed(fetch_text(page_url))
    rows: list[dict[str, str | None]] = []
    for href, text in parser.links:
        source_url = urllib.parse.urljoin(page_url, href)
        if ".pdf" not in source_url.lower():
            continue
        if not text and not page_url.rstrip("/") == "https://www.mindreleased.com/sutta-nipata":
            continue
        if text == "C":
            continue
        rows.append(
            {
                "page_url": page_url,
                "source_url": source_url,
                "label": source_label_for_page_link(page_url, text),
                "canonical_id": source_id_for_page_link(page_url, source_url, text),
            }
        )
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--page", action="append", dest="pages", default=[])
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    pages = args.pages or DEFAULT_PAGES
    seen_urls: set[str] = set()
    rows: list[dict[str, str | None]] = []
    for page in pages:
        for row in discover_page(page):
            source_url = row["source_url"]
            if source_url and source_url not in seen_urls:
                seen_urls.add(source_url)
                rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    with_ids = sum(1 for row in rows if row["canonical_id"])
    print(f"Wrote {len(rows)} source rows to {args.output}")
    print(f"Rows with parsed canonical ids: {with_ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
