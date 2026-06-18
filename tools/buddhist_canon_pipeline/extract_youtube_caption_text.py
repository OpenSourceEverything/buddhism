#!/usr/bin/env python3
"""Extract public YouTube caption text for one video.

This proof-of-concept reads caption metadata from the watch page and writes
plain text from a selected caption track. It does not download audio/video.
Use only where permission and platform terms allow.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = "Mozilla/5.0"


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", "replace")


def extract_caption_tracks(watch_html: str) -> list[dict[str, Any]]:
    match = re.search(r'"captionTracks":(\[.*?\]),"audioTracks"', watch_html)
    if not match:
        return []
    return json.loads(match.group(1))


def track_label(track: dict[str, Any]) -> str:
    name = track.get("name", {})
    if isinstance(name, dict):
        if "simpleText" in name:
            return name["simpleText"]
        if "runs" in name:
            return "".join(run.get("text", "") for run in name["runs"])
    return track.get("languageCode", "unknown")


def caption_url(track: dict[str, Any]) -> str:
    parsed = urllib.parse.urlparse(track["baseUrl"])
    query = urllib.parse.parse_qs(parsed.query)
    query["fmt"] = ["json3"]
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query, doseq=True)))


def json3_to_lines(payload: dict[str, Any], max_events: int | None) -> list[str]:
    lines: list[str] = []
    events = payload.get("events", [])
    for event in events:
        if max_events is not None and len(lines) >= max_events:
            break
        segments = event.get("segs") or []
        text = "".join(segment.get("utf8", "") for segment in segments).strip()
        text = html.unescape(re.sub(r"\s+", " ", text))
        if text:
            lines.append(text)
    return lines


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--language", default="en")
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Limit caption events for a quick proof run. Omit for full caption text.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    watch_html = fetch_text(f"https://www.youtube.com/watch?v={args.video_id}")
    tracks = extract_caption_tracks(watch_html)
    if not tracks:
        print(f"No public caption tracks found for {args.video_id}", file=sys.stderr)
        return 2

    selected = next(
        (track for track in tracks if track.get("languageCode") == args.language),
        tracks[0],
    )
    caption_payload = json.loads(fetch_text(caption_url(selected)))
    lines = json3_to_lines(caption_payload, args.max_events)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"video_id: {args.video_id}\n")
        handle.write(f"caption_track: {track_label(selected)}\n")
        handle.write(f"caption_kind: {selected.get('kind', 'manual')}\n")
        handle.write("\n")
        for line in lines:
            handle.write(line + "\n")

    print(f"Wrote {len(lines)} caption lines to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

