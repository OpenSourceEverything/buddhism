#!/usr/bin/env python3
"""Parse Candana Bhikkhu playlist metadata and match videos to canonical IDs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


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

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


@dataclass(frozen=True)
class YouTubeVideo:
    video_id: str
    title: str
    duration: str
    collection: str
    playlist_id: str

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


def expand_range(prefix: str, group: int, start: int, end: int) -> set[str]:
    if end < start:
        return {f"{prefix} {group}.{start}"}
    return {f"{prefix} {group}.{number}" for number in range(start, end + 1)}


def parse_ids(title: str, collection: str) -> set[str]:
    """Return canonical IDs explicitly covered by a playlist title."""
    ids: set[str] = set()

    for prefix in ("DN", "MN"):
        expected_collection = {"DN": "digha", "MN": "majjhima"}[prefix]
        if collection.startswith(expected_collection):
            for match in re.finditer(r"\bSutta\s*:?[ -]*(\d+)\b", title, flags=re.IGNORECASE):
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

    ids.update(parse_book_scopes(title, collection))
    return ids


def parse_book_scopes(title: str, collection: str) -> set[str]:
    """Return honest book-level keys for recordings that contain several texts."""
    keys: set[str] = set()
    lower_title = title.lower()

    if collection == "sutta-nipata":
        if "full audiobook" in lower_title:
            keys.add("Snp complete")
        word_match = re.search(r"\bbook\s+(one|two|three|four|five)\b", lower_title)
        if word_match:
            keys.add(f"Snp book {NUMBER_WORDS[word_match.group(1)]}")

    if collection == "theragatha":
        numbered = re.search(r"\bbook\s+(\d+)\b", lower_title)
        if numbered:
            keys.add(f"Thag book {int(numbered.group(1))}")

        verse_book = re.search(r"\bbook of the\s+(20|30|40|50|60)", lower_title)
        if verse_book:
            group = {20: 16, 30: 17, 40: 18, 50: 19, 60: 20}[int(verse_book.group(1))]
            keys.add(f"Thag book {group}")
        if "great book of verses" in lower_title:
            keys.add("Thag book 21")

    return keys


def canonical_lookup_keys(canonical_id: str) -> tuple[list[str], list[str]]:
    """Return exact keys first and broader book-level fallbacks second."""
    canonical_id = " ".join(canonical_id.strip().split())
    exact: list[str] = []
    fallback: list[str] = []

    range_match = re.fullmatch(r"(AN|SN)\s+(\d+)\.(\d+)-(\d+)", canonical_id, flags=re.IGNORECASE)
    if range_match:
        exact.extend(
            sorted(
                expand_range(
                    range_match.group(1).upper(),
                    int(range_match.group(2)),
                    int(range_match.group(3)),
                    int(range_match.group(4)),
                )
            )
        )
    else:
        exact.append(canonical_id)

    dhp = re.fullmatch(r"Dhp\s+(\d+)\.(\d+)", canonical_id, flags=re.IGNORECASE)
    if dhp:
        exact.insert(0, f"Dhp {int(dhp.group(2))}")

    snp = re.fullmatch(r"Snp\s+(\d+)\.(\d+)", canonical_id, flags=re.IGNORECASE)
    if snp:
        fallback.append(f"Snp book {int(snp.group(1))}")

    thag = re.fullmatch(r"Thag\s+(\d+)\.(\d+)", canonical_id, flags=re.IGNORECASE)
    if thag:
        fallback.append(f"Thag book {int(thag.group(1))}")

    if canonical_id.lower() == "snp complete":
        exact = ["Snp complete"]

    return exact, fallback


def read_youtube_index(manifest_dir: Path) -> dict[str, list[YouTubeVideo]]:
    """Index playlist records by exact canonical or honest book-level key."""
    index: dict[str, list[YouTubeVideo]] = {}
    for path in sorted(manifest_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                video_id = str(row.get("video_id", "")).strip()
                title = str(row.get("title", "")).strip()
                collection = str(row.get("collection", "")).strip()
                if not video_id or not title:
                    continue
                video = YouTubeVideo(
                    video_id=video_id,
                    title=title,
                    duration=str(row.get("duration") or ""),
                    collection=collection,
                    playlist_id=str(row.get("playlist_id", "")),
                )
                for key in parse_ids(title, collection):
                    videos = index.setdefault(key, [])
                    if all(existing.video_id != video.video_id for existing in videos):
                        videos.append(video)
    return index


def videos_for_canonical_id(
    canonical_id: str,
    index: dict[str, list[YouTubeVideo]],
) -> list[YouTubeVideo]:
    """Find exact Candana recordings, falling back to a labeled book recording."""
    exact_keys, fallback_keys = canonical_lookup_keys(canonical_id)
    videos: list[YouTubeVideo] = []
    seen: set[str] = set()

    for key in exact_keys:
        for video in index.get(key, []):
            if video.video_id not in seen:
                seen.add(video.video_id)
                videos.append(video)
    if videos:
        return videos

    for key in fallback_keys:
        for video in index.get(key, []):
            if video.video_id not in seen:
                seen.add(video.video_id)
                videos.append(video)
    return videos
