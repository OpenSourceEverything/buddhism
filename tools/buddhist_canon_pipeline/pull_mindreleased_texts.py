#!/usr/bin/env python3
"""Pull Mind Released PDF sources and extract text into the canon tree.

Input is the JSONL source manifest produced by discover_mindreleased_sources.py.
Outputs:
  - one PDF per source
  - one TXT extracted from the PDF
  - one ledger TSV recording status, paths, source URL, and extraction stats
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

try:
    import fitz  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency fallback
    fitz = None

from PyPDF2 import PdfReader


USER_AGENT = "Mozilla/5.0"

PREFIX_PATHS = {
    "DN": Path("digha-nikaya"),
    "MN": Path("majjhima-nikaya"),
    "SN": Path("samyutta-nikaya"),
    "AN": Path("anguttara-nikaya"),
    "Dhp": Path("khuddaka-nikaya/dhammapada"),
    "Ud": Path("khuddaka-nikaya/udana"),
    "Iti": Path("khuddaka-nikaya/itivuttaka"),
    "Snp": Path("khuddaka-nikaya/sutta-nipata"),
    "Thag": Path("khuddaka-nikaya/theragatha"),
    "Thig": Path("khuddaka-nikaya/therigatha"),
    "Ja": Path("khuddaka-nikaya/jataka"),
    "Mil": Path("khuddaka-nikaya/milindapanha"),
}

LEDGER_COLUMNS = [
    "canonical_id",
    "status",
    "collection_path",
    "pdf_path",
    "txt_path",
    "pdf_bytes",
    "txt_chars",
    "text_extractor",
    "pdf_sha256",
    "source_url",
    "label",
    "page_url",
    "error",
]


def slug(value: str | None) -> str:
    if not value:
        return "unmapped"
    value = value.strip().lower()
    value = value.replace(".", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unmapped"


def collection_path(canonical_id: str | None) -> Path:
    if not canonical_id:
        return Path("source-unmapped")
    prefix = canonical_id.split()[0]
    return PREFIX_PATHS.get(prefix, Path("source-unmapped"))


def source_basename(url: str) -> str:
    stem = Path(urllib.request.url2pathname(url.split("?")[0])).stem
    return slug(stem)


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_pdf_text_with_pymupdf(pdf_path: Path) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not available")

    document = fitz.open(pdf_path)
    parts: list[str] = []
    for page_number, page in enumerate(document, start=1):
        text = page.get_text("text").strip()
        if text:
            parts.append(f"[page {page_number}]\n{text}")
    return "\n\n".join(parts).strip() + "\n"


def extract_pdf_text_with_pypdf2(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(f"[page {page_number}]\n{page_text.strip()}")
    return "\n\n".join(parts).strip() + "\n"


def extract_pdf_text(pdf_path: Path) -> tuple[str, str]:
    if fitz is not None:
        return extract_pdf_text_with_pymupdf(pdf_path), "pymupdf"
    return extract_pdf_text_with_pypdf2(pdf_path), "pypdf2"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def pull_row(row: dict[str, Any], sutta_root: Path, force: bool) -> dict[str, str]:
    canonical_id = row.get("canonical_id")
    source_url = row["source_url"]
    target_dir = sutta_root / collection_path(canonical_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    base = f"{slug(canonical_id)}__{source_basename(source_url)}"
    pdf_path = target_dir / f"{base}.pdf"
    txt_path = target_dir / f"{base}.txt"

    record = {
        "canonical_id": canonical_id or "",
        "status": "",
        "collection_path": relative(target_dir, sutta_root),
        "pdf_path": relative(pdf_path, sutta_root),
        "txt_path": relative(txt_path, sutta_root),
        "pdf_bytes": "",
        "txt_chars": "",
        "text_extractor": "",
        "pdf_sha256": "",
        "source_url": source_url,
        "label": row.get("label") or "",
        "page_url": row.get("page_url") or "",
        "error": "",
    }

    try:
        if force or not pdf_path.exists():
            data = download(source_url)
            pdf_path.write_bytes(data)
        else:
            data = pdf_path.read_bytes()

        record["pdf_bytes"] = str(len(data))
        record["pdf_sha256"] = sha256(data)

        if force or not txt_path.exists():
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_pdf = Path(tmpdir) / "source.pdf"
                temp_pdf.write_bytes(data)
                text, extractor = extract_pdf_text(temp_pdf)
            txt_path.write_text(text, encoding="utf-8", newline="\n")
        else:
            text = txt_path.read_text(encoding="utf-8")
            extractor = "existing"

        record["txt_chars"] = str(len(text))
        record["text_extractor"] = extractor
        record["status"] = "TEXT_EXTRACTED" if text.strip() else "PDF_ONLY_EMPTY_TEXT"
    except Exception as exc:  # noqa: BLE001 - ledger should capture per-row failures.
        record["status"] = "ERROR"
        record["error"] = f"{type(exc).__name__}: {exc}"

    return record


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="JSONL source manifest from discover_mindreleased_sources.py",
    )
    parser.add_argument(
        "--sutta-root",
        default=Path("theravada/tipitaka/sutta"),
        type=Path,
    )
    parser.add_argument(
        "--ledger",
        default=Path("theravada/tipitaka/sutta/candana-bhikkhu-text-ledger.tsv"),
        type=Path,
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    rows = read_jsonl(args.manifest)
    if args.limit is not None:
        rows = rows[: args.limit]

    args.sutta_root.mkdir(parents=True, exist_ok=True)
    records = [pull_row(row, args.sutta_root, args.force) for row in rows]

    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    with args.ledger.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS, dialect="excel-tab")
        writer.writeheader()
        writer.writerows(records)

    ok = sum(1 for record in records if record["status"] == "TEXT_EXTRACTED")
    errors = sum(1 for record in records if record["status"] == "ERROR")
    print(f"Wrote ledger: {args.ledger}")
    print(f"Processed: {len(records)}; text extracted: {ok}; errors: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
