#!/usr/bin/env python3
"""Download a PDF source and extract text with PyPDF2."""

from __future__ import annotations

import argparse
import sys
import tempfile
import urllib.request
from pathlib import Path

from PyPDF2 import PdfReader


USER_AGENT = "Mozilla/5.0"


def download_pdf(url: str, output: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        output.write_bytes(response.read())


def extract_text(pdf_path: Path, max_pages: int | None) -> str:
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    pages = reader.pages[:max_pages] if max_pages is not None else reader.pages
    for page_number, page in enumerate(pages, start=1):
        text = page.extract_text() or ""
        parts.append(f"\n\n[page {page_number}]\n{text.strip()}")
    return "".join(parts).strip() + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-pages", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "source.pdf"
        download_pdf(args.url, pdf_path)
        args.output.write_text(extract_text(pdf_path, args.max_pages), encoding="utf-8", newline="\n")
    print(f"Wrote extracted text to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

