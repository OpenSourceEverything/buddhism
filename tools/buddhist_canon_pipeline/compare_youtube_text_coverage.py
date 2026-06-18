#!/usr/bin/env python3
"""Compare extracted text ledger coverage with YouTube playlist metadata."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


ROMAN_BOOKS = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
    "XI": 11,
}


def expand_range(prefix: str, group: int, start: int, end: int) -> set[str]:
    if end < start:
        return {f"{prefix} {group}.{start}"}
    return {f"{prefix} {group}.{number}" for number in range(start, end + 1)}


def parse_ids(title: str, collection: str) -> set[str]:
    ids: set[str] = set()

    for prefix in ("DN", "MN"):
        if collection.startswith({"DN": "digha", "MN": "majjhima"}[prefix]):
            for match in re.finditer(r"\bSutta\s+(\d+)\b", title, flags=re.IGNORECASE):
                ids.add(f"{prefix} {int(match.group(1))}")

    for match in re.finditer(
        r"\bSN\s*([0-9]{1,2})\.([0-9]{1,3})(?:\s*-\s*(?:(\d{1,2})\.)?(\d{1,3}))?",
        title,
        flags=re.IGNORECASE,
    ):
        group = int(match.group(1))
        start = int(match.group(2))
        if match.group(4):
            end_group = int(match.group(3) or group)
            end = int(match.group(4))
            if end_group == group:
                ids.update(expand_range("SN", group, start, end))
            else:
                ids.add(f"SN {group}.{start}")
                ids.add(f"SN {end_group}.{end}")
        else:
            ids.add(f"SN {group}.{start}")

    an_book = re.search(
        r"\bBook\s+([IVX]+|\d+)\s*:\s*Suttas?\s+(\d+)(?:\s*[-.]\s*(\d+))?",
        title,
        flags=re.IGNORECASE,
    )
    if an_book:
        raw_book = an_book.group(1).upper()
        book = ROMAN_BOOKS.get(raw_book, int(raw_book) if raw_book.isdigit() else 0)
        start = int(an_book.group(2))
        end = int(an_book.group(3) or start)
        ids.update(expand_range("AN", book, start, end))

    for match in re.finditer(r"\bAN\s*([0-9]{1,2})\.([0-9]{1,3})\b", title, flags=re.IGNORECASE):
        ids.add(f"AN {int(match.group(1))}.{int(match.group(2))}")

    dhammapada = re.search(r"\bDhammapada:\s*(\d+)(?:\s*-\s*(\d+))?", title, flags=re.IGNORECASE)
    if dhammapada:
        start = int(dhammapada.group(1))
        end = int(dhammapada.group(2) or start)
        ids.update({f"Dhp {number}" for number in range(start, end + 1)})

    udana = re.search(r"\bUdana:\s*(\d+)\.(\d+)\b", title, flags=re.IGNORECASE)
    if udana and int(udana.group(2)) > 0:
        ids.add(f"Ud {int(udana.group(1))}.{int(udana.group(2))}")

    iti = re.search(r"\bItivuttaka:\s*(\d+)(?:\s*-\s*(\d+))?", title, flags=re.IGNORECASE)
    if iti:
        start = int(iti.group(1))
        end = int(iti.group(2) or start)
        ids.update({f"Iti {number}" for number in range(start, end + 1)})

    snp = re.search(r"\bSnp\.?\s*(\d+)\.(\d+)\b", title, flags=re.IGNORECASE)
    if snp:
        ids.add(f"Snp {int(snp.group(1))}.{int(snp.group(2))}")

    return ids


def read_text_ids(ledger: Path) -> set[str]:
    ids: set[str] = set()
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, dialect="excel-tab"):
            if row["status"] == "TEXT_EXTRACTED" and row["canonical_id"]:
                ids.add(row["canonical_id"])
    return ids


def read_youtube_rows(manifest_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(manifest_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                parsed = parse_ids(row.get("title", ""), row.get("collection", ""))
                row["parsed_ids"] = sorted(parsed)
                row["manifest"] = path.name
                rows.append(row)
    return rows


def covered_by_text(row: dict[str, object], text_ids: set[str]) -> bool:
    ids = row["parsed_ids"]
    collection = str(row.get("collection", ""))
    if collection == "sutta-nipata" and "Snp complete" in text_ids:
        return True

    ids = set(ids)
    if not ids:
        return False
    if "Snp complete" in text_ids and all(item.startswith("Snp ") for item in ids):
        return True
    return ids.issubset(text_ids)


def write_report(text_ids: set[str], youtube_rows: list[dict[str, object]], output: Path) -> None:
    by_collection: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in youtube_rows:
        by_collection[str(row["collection"])].append(row)

    lines: list[str] = []
    lines.append("# Candana Bhikkhu Text vs YouTube Coverage")
    lines.append("")
    lines.append(f"Text canonical/source IDs: {len(text_ids)}")
    lines.append(f"YouTube playlist rows: {len(youtube_rows)}")
    lines.append("")
    lines.append("| Collection | YouTube rows | Rows with parsed IDs | Text-backed rows | Audio/metadata-only rows |")
    lines.append("|---|---:|---:|---:|---:|")

    for collection, rows in sorted(by_collection.items()):
        parsed_rows = [row for row in rows if row["parsed_ids"]]
        backed = [row for row in rows if covered_by_text(row, text_ids)]
        audio_or_metadata_only = [row for row in rows if not covered_by_text(row, text_ids)]
        lines.append(
            f"| {collection} | {len(rows)} | {len(parsed_rows)} | {len(backed)} | {len(audio_or_metadata_only)} |"
        )

    lines.append("")
    lines.append("## Audio/Metadata-Only Parsed Rows")
    lines.append("")
    for collection, rows in sorted(by_collection.items()):
        missing = [
            row
            for row in rows
            if row["parsed_ids"] and not covered_by_text(row, text_ids)
        ]
        if not missing:
            continue
        lines.append(f"### {collection}")
        for row in missing[:80]:
            ids = ", ".join(row["parsed_ids"])
            lines.append(f"- `{ids}` - {row['title']}")
        if len(missing) > 80:
            lines.append(f"- ... {len(missing) - 80} more")
        lines.append("")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        default=Path("theravada/tipitaka/sutta/candana-bhikkhu-text-ledger.tsv"),
        type=Path,
    )
    parser.add_argument(
        "--youtube-manifest-dir",
        default=Path("metadata/youtube-playlists/manifests"),
        type=Path,
    )
    parser.add_argument(
        "--output",
        default=Path("metadata/reports/candana-text-vs-youtube-coverage.md"),
        type=Path,
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    text_ids = read_text_ids(args.ledger)
    youtube_rows = read_youtube_rows(args.youtube_manifest_dir)
    write_report(text_ids, youtube_rows, args.output)

    parsed_count = sum(1 for row in youtube_rows if row["parsed_ids"])
    backed_count = sum(1 for row in youtube_rows if covered_by_text(row, text_ids))
    print(f"Wrote report: {args.output}")
    print(f"Parsed YouTube rows: {parsed_count}; text-backed parsed rows: {backed_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
