#!/usr/bin/env python3
"""Audit simple numbered-sutta coverage from a playlist manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--label", required=True, help="Example: Sutta")
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--end", required=True, type=int)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    covered: set[int] = set()
    pattern = re.compile(rf"{re.escape(args.label)}\s+(\d+)", re.IGNORECASE)

    with args.manifest.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            match = pattern.search(row.get("title", ""))
            if match:
                covered.add(int(match.group(1)))

    target = set(range(args.start, args.end + 1))
    missing = sorted(target - covered)
    extra = sorted(number for number in covered if number not in target)

    print(f"Manifest: {args.manifest}")
    print(f"Expected: {args.start}-{args.end} ({len(target)} ids)")
    print(f"Covered: {len(covered & target)}")
    print(f"Missing: {missing if missing else 'none'}")
    print(f"Out of range: {extra if extra else 'none'}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

