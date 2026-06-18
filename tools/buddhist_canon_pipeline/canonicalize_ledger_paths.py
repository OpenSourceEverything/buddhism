#!/usr/bin/env python3
"""Rewrite the text ledger to point at canonical per-sutta folders."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def canonical_folder(sutta_root: Path, collection_path: str, canonical_id: str) -> Path:
    from build_static_site import canonical_slug

    return sutta_root / collection_path / canonical_slug(canonical_id)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        default=Path("theravada/tipitaka/sutta/candana-bhikkhu-text-ledger.tsv"),
        type=Path,
    )
    parser.add_argument("--sutta-root", default=Path("theravada/tipitaka/sutta"), type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    with args.ledger.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, dialect="excel-tab")
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    by_id: dict[str, int] = {}
    for row in rows:
        if row["status"] != "TEXT_EXTRACTED" or not row["canonical_id"]:
            continue
        by_id[row["canonical_id"]] = by_id.get(row["canonical_id"], 0) + 1
        folder = canonical_folder(args.sutta_root, row["collection_path"], row["canonical_id"])
        if by_id[row["canonical_id"]] > 1:
            suffix = f"-{by_id[row['canonical_id']]:02d}"
            pdf = folder / f"{folder.name}{suffix}.pdf"
            txt = folder / f"{folder.name}{suffix}.txt"
        else:
            pdf = folder / f"{folder.name}.pdf"
            txt = folder / f"{folder.name}.txt"

        if not pdf.exists() or not txt.exists():
            raise FileNotFoundError(f"Missing canonical files for {row['canonical_id']}: {pdf}, {txt}")

        row["pdf_path"] = pdf.relative_to(args.sutta_root).as_posix()
        row["txt_path"] = txt.relative_to(args.sutta_root).as_posix()
        row["pdf_bytes"] = str(pdf.stat().st_size)
        row["txt_chars"] = str(len(txt.read_text(encoding="utf-8")))

    with args.ledger.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, dialect="excel-tab")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Rewrote canonical ledger paths: {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
