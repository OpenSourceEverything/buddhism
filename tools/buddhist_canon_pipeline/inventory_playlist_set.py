#!/usr/bin/env python3
"""Inventory a TSV set of YouTube playlists."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist-set", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--inventory-script",
        default=Path("tools/buddhist_canon_pipeline/youtube_playlist_inventory.py"),
        type=Path,
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.playlist_set.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, dialect="excel-tab"))

    for row in rows:
        output = args.output_dir / f"{row['collection']}.jsonl"
        command = [
            sys.executable,
            str(args.inventory_script),
            "--playlist-id",
            row["playlist_id"],
            "--collection",
            row["collection"],
            "--output",
            str(output),
        ]
        print(" ".join(command))
        subprocess.run(command, check=True)

    print(f"Inventoried {len(rows)} playlists into {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
