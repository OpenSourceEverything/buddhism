#!/usr/bin/env python3
"""Inventory a public YouTube playlist into JSONL.

This is a low-cost proof-of-concept tool. It inventories metadata only:
video id, title, duration text, playlist id, and collection name.

It intentionally does not download audio/video. For a production corpus,
obtain permission and prefer official/source files where available.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = "Mozilla/5.0"


def fetch_text(url: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> str:
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=data, headers=request_headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", "replace")


def extract_initial_data(html: str) -> dict[str, Any]:
    match = re.search(r"var ytInitialData = (\{.*?\});</script>", html)
    if not match:
        raise ValueError("Could not find ytInitialData in YouTube page")
    return json.loads(match.group(1))


def extract_innertube(html: str) -> tuple[str, dict[str, Any]]:
    key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
    context_match = re.search(
        r'"INNERTUBE_CONTEXT":(\{.*?\}),"INNERTUBE_CONTEXT_CLIENT_NAME"',
        html,
    )
    if not key_match or not context_match:
        raise ValueError("Could not find YouTube continuation API context")
    return key_match.group(1), json.loads(context_match.group(1))


def find_duration(serialized: str) -> str | None:
    for match in re.finditer(r'"text"\s*:\s*"([^"\\]+)"', serialized):
        value = match.group(1)
        if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", value):
            return value
    return None


def extract_items_and_continuations(payload: Any) -> tuple[list[dict[str, str | None]], list[str]]:
    items: list[dict[str, str | None]] = []
    continuations: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "lockupViewModel" in node:
                view_model = node["lockupViewModel"]
                video_id = view_model.get("contentId")
                title = None
                try:
                    title = view_model["metadata"]["lockupMetadataViewModel"]["title"]["content"]
                except (KeyError, TypeError):
                    title = None
                if title and video_id and not video_id.startswith("PL"):
                    items.append(
                        {
                            "video_id": video_id,
                            "title": title,
                            "duration": find_duration(json.dumps(view_model, ensure_ascii=False)),
                        }
                    )

            continuation = node.get("continuationCommand")
            if isinstance(continuation, dict) and continuation.get("token"):
                continuations.append(continuation["token"])

            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return items, continuations


def inventory_playlist(playlist_id: str) -> list[dict[str, str | None]]:
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    html = fetch_text(playlist_url)
    api_key, context = extract_innertube(html)

    items, continuations = extract_items_and_continuations(extract_initial_data(html))
    seen_video_ids = {item["video_id"] for item in items}
    seen_tokens: set[str] = set()
    queue = list(continuations)

    while queue:
        token = queue.pop(0)
        if token in seen_tokens:
            continue
        seen_tokens.add(token)

        body = json.dumps({"context": context, "continuation": token}).encode("utf-8")
        response = fetch_text(
            f"https://www.youtube.com/youtubei/v1/browse?key={api_key}",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Origin": "https://www.youtube.com",
                "Referer": playlist_url,
            },
        )
        more_items, more_continuations = extract_items_and_continuations(json.loads(response))

        for item in more_items:
            video_id = item["video_id"]
            if video_id not in seen_video_ids:
                seen_video_ids.add(video_id)
                items.append(item)

        for next_token in more_continuations:
            if next_token not in seen_tokens:
                queue.append(next_token)

    return items


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist-id", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    rows = inventory_playlist(args.playlist_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for index, row in enumerate(rows, start=1):
            enriched = {
                "collection": args.collection,
                "playlist_id": args.playlist_id,
                "playlist_index": index,
                **row,
            }
            handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

