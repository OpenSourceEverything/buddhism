#!/usr/bin/env python3
"""Build canonical per-sutta folders, simple HTML pages, and zip downloads."""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
import shutil
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


COLLECTION_TITLES = {
    "digha-nikaya": "Digha Nikaya",
    "majjhima-nikaya": "Majjhima Nikaya",
    "samyutta-nikaya": "Samyutta Nikaya",
    "anguttara-nikaya": "Anguttara Nikaya",
    "khuddaka-nikaya/dhammapada": "Dhammapada",
    "khuddaka-nikaya/udana": "Udana",
    "khuddaka-nikaya/itivuttaka": "Itivuttaka",
    "khuddaka-nikaya/sutta-nipata": "Sutta Nipata",
    "khuddaka-nikaya/theragatha": "Theragatha",
    "khuddaka-nikaya/therigatha": "Therigatha",
    "khuddaka-nikaya/jataka": "Jataka",
    "khuddaka-nikaya/milindapanha": "Milindapanha",
}


@dataclass
class SourceRow:
    canonical_id: str
    collection_path: str
    source_pdf: Path
    source_txt: Path
    label: str
    source_url: str
    page_url: str


@dataclass
class GeneratedItem:
    canonical_id: str
    title: str
    collection_path: str
    folder: Path
    base_name: str
    html_path: Path
    txt_path: Path
    pdf_path: Path


def canonical_slug(canonical_id: str) -> str:
    match = re.fullmatch(r"([A-Za-z]+)\s+(.+)", canonical_id.strip())
    if not match:
        return slug(canonical_id)

    prefix = match.group(1).lower()
    value = match.group(2).lower().replace("complete", "complete")
    if re.fullmatch(r"\d+", value):
        return f"{prefix}{int(value):02d}"
    if re.fullmatch(r"\d+\.\d+", value):
        book, number = value.split(".")
        return f"{prefix}{int(book):02d}-{int(number):02d}"
    if re.fullmatch(r"\d+\.\d+-\d+", value):
        book, rest = value.split(".")
        start, end = rest.split("-")
        return f"{prefix}{int(book):02d}-{int(start):02d}-{int(end):02d}"
    if value == "complete":
        return f"{prefix}-complete"
    return slug(canonical_id)


def slug(value: str) -> str:
    value = value.strip().lower()
    value = value.replace(".", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def title_from_row(row: SourceRow) -> str:
    if row.label:
        return row.label
    return row.canonical_id


def read_ledger(ledger: Path, sutta_root: Path) -> list[SourceRow]:
    rows: list[SourceRow] = []
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle, dialect="excel-tab"):
            if record["status"] != "TEXT_EXTRACTED" or not record["canonical_id"]:
                continue
            rows.append(
                SourceRow(
                    canonical_id=record["canonical_id"],
                    collection_path=record["collection_path"],
                    source_pdf=sutta_root / record["pdf_path"],
                    source_txt=sutta_root / record["txt_path"],
                    label=record["label"],
                    source_url=record["source_url"],
                    page_url=record["page_url"],
                )
            )
    return rows


def html_relative(from_file: Path, target: Path) -> str:
    return Path(os.path.relpath(target, start=from_file.parent)).as_posix()


def page(title: str, body: str, css_href: str | None = None) -> str:
    css = f'<link rel="stylesheet" href="{html.escape(css_href)}">\n' if css_href else ""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"{css}"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def convert_text_to_html(text: str) -> str:
    return f"<pre>{html.escape(text)}</pre>"


def write_item_html(item: GeneratedItem, txt_text: str, tipitaka_root: Path) -> None:
    site_index = tipitaka_root / "site/index.html"
    collection_index = tipitaka_root / "sutta" / item.collection_path / "index.html"
    home = html_relative(item.html_path, site_index)
    parent = html_relative(item.html_path, collection_index)
    txt_link = html_relative(item.html_path, item.txt_path)
    pdf_link = html_relative(item.html_path, item.pdf_path)
    body = "\n".join(
        [
            f"<h1>{html.escape(item.canonical_id)} {html.escape(item.title)}</h1>",
            "<p>",
            f'<a href="{txt_link}">download txt</a> | ',
            f'<a href="{pdf_link}">download pdf</a> | ',
            f'<a href="{parent}">parent</a> | ',
            f'<a href="{home}">home</a>',
            "</p>",
            convert_text_to_html(txt_text),
        ]
    )
    item.html_path.write_text(page(f"{item.canonical_id} {item.title}", body), encoding="utf-8", newline="\n")
    index_path = item.folder / "index.html"
    if index_path != item.html_path:
        index_path.write_text(item.html_path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")


def copy_item(row: SourceRow, sutta_root: Path, tipitaka_root: Path, ordinal: int) -> GeneratedItem:
    folder_name = canonical_slug(row.canonical_id)
    base_name = folder_name
    folder = sutta_root / row.collection_path / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    existing_pdf = folder / f"{base_name}.pdf"
    if existing_pdf.exists() and existing_pdf.read_bytes() != row.source_pdf.read_bytes():
        base_name = f"{folder_name}-{ordinal:02d}"

    pdf_path = folder / f"{base_name}.pdf"
    txt_path = folder / f"{base_name}.txt"
    html_path = folder / f"{base_name}.html"
    if row.source_pdf.resolve() != pdf_path.resolve():
        shutil.copy2(row.source_pdf, pdf_path)
    if row.source_txt.resolve() != txt_path.resolve():
        shutil.copy2(row.source_txt, txt_path)
    text = txt_path.read_text(encoding="utf-8")

    item = GeneratedItem(
        canonical_id=row.canonical_id,
        title=title_from_row(row),
        collection_path=row.collection_path,
        folder=folder,
        base_name=base_name,
        html_path=html_path,
        txt_path=txt_path,
        pdf_path=pdf_path,
    )
    write_item_html(item, text, tipitaka_root)
    return item


def write_collection_indexes(items: list[GeneratedItem], tipitaka_root: Path) -> None:
    by_collection: dict[str, list[GeneratedItem]] = defaultdict(list)
    for item in items:
        by_collection[item.collection_path].append(item)

    for collection, collection_items in by_collection.items():
        collection_dir = tipitaka_root / "sutta" / collection
        rows = []
        for item in sorted(collection_items, key=lambda x: x.base_name):
            rows.append(
                "<tr>"
                f"<td>{html.escape(item.canonical_id)}</td>"
                f"<td><a href=\"{html_relative(collection_dir / 'index.html', item.html_path)}\">{html.escape(item.title)}</a></td>"
                f"<td><a href=\"{html_relative(collection_dir / 'index.html', item.txt_path)}\">txt</a></td>"
                f"<td><a href=\"{html_relative(collection_dir / 'index.html', item.pdf_path)}\">pdf</a></td>"
                "</tr>"
            )
        body = "\n".join(
            [
                f"<h1>{html.escape(COLLECTION_TITLES.get(collection, collection))}</h1>",
                f'<p><a href="{html_relative(collection_dir / "index.html", tipitaka_root / "site/index.html")}">home</a></p>',
                "<table>",
                "<tr><th>ID</th><th>Title</th><th>TXT</th><th>PDF</th></tr>",
                *rows,
                "</table>",
            ]
        )
        collection_dir.mkdir(parents=True, exist_ok=True)
        (collection_dir / "index.html").write_text(
            page(COLLECTION_TITLES.get(collection, collection), body),
            encoding="utf-8",
            newline="\n",
        )


def write_site(items: list[GeneratedItem], tipitaka_root: Path) -> None:
    site_dir = tipitaka_root / "site"
    assets = site_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "style.css").write_text(
        "\n".join(
            [
                "body { font-family: serif; margin: 2em; max-width: 80em; }",
                "table { border-collapse: collapse; }",
                "th, td { border: 1px solid #888; padding: 0.25em 0.5em; vertical-align: top; }",
                "pre { white-space: pre-wrap; line-height: 1.35; }",
                "a { color: #003399; }",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    index_body = """
<h1>Buddhism</h1>
<p>Theravada Tipitaka source texts and generated formats.</p>
<h2>Tipitaka</h2>
<ul>
  <li>Sutta Pitaka
    <ul>
      <li><a href="sutta.html">Sutta index</a></li>
      <li><a href="../sutta/digha-nikaya/index.html">Digha Nikaya</a></li>
      <li><a href="../sutta/majjhima-nikaya/index.html">Majjhima Nikaya</a></li>
      <li><a href="../sutta/samyutta-nikaya/index.html">Samyutta Nikaya</a></li>
      <li><a href="../sutta/anguttara-nikaya/index.html">Anguttara Nikaya</a></li>
      <li><a href="../sutta/khuddaka-nikaya/sutta-nipata/index.html">Sutta Nipata</a></li>
    </ul>
  </li>
  <li><a href="downloads.html">Downloads</a></li>
</ul>
"""
    (site_dir / "index.html").write_text(page("Buddhism", index_body, "assets/style.css"), encoding="utf-8", newline="\n")

    rows = []
    for item in sorted(items, key=lambda x: (x.collection_path, x.base_name)):
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.collection_path)}</td>"
            f"<td>{html.escape(item.canonical_id)}</td>"
            f"<td><a href=\"{html_relative(site_dir / 'sutta.html', item.html_path)}\">{html.escape(item.title)}</a></td>"
            f"<td><a href=\"{html_relative(site_dir / 'sutta.html', item.txt_path)}\">txt</a></td>"
            f"<td><a href=\"{html_relative(site_dir / 'sutta.html', item.pdf_path)}\">pdf</a></td>"
            "</tr>"
        )
    sutta_body = "\n".join(
        [
            "<h1>Sutta Pitaka</h1>",
            '<p><a href="index.html">home</a> | <a href="downloads.html">downloads</a></p>',
            "<table>",
            "<tr><th>Collection</th><th>ID</th><th>Title</th><th>TXT</th><th>PDF</th></tr>",
            *rows,
            "</table>",
        ]
    )
    (site_dir / "sutta.html").write_text(page("Sutta Pitaka", sutta_body, "assets/style.css"), encoding="utf-8", newline="\n")

    downloads_body = """
<h1>Downloads</h1>
<p><a href="index.html">home</a></p>
<p>ZIP bundles are generated artifacts for releases and local mirrors. They are not stored in git.</p>
<ul>
  <li>tipitaka-txt.zip</li>
  <li>tipitaka-pdf.zip</li>
  <li>tipitaka-html.zip</li>
  <li>tipitaka-all.zip</li>
</ul>
"""
    (site_dir / "downloads.html").write_text(page("Downloads", downloads_body, "assets/style.css"), encoding="utf-8", newline="\n")


def write_zips(tipitaka_root: Path) -> None:
    downloads = tipitaka_root / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    sutta = tipitaka_root / "sutta"
    specs = [
        ("tipitaka-txt.zip", {".txt", ".tsv"}),
        ("tipitaka-pdf.zip", {".pdf"}),
        ("tipitaka-html.zip", {".html", ".css"}),
        ("tipitaka-all.zip", {".txt", ".tsv", ".pdf", ".html", ".css"}),
    ]
    for name, extensions in specs:
        with zipfile.ZipFile(downloads / name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for root in [sutta, tipitaka_root / "site"]:
                if not root.exists():
                    continue
                for path in root.rglob("*"):
                    if "__" in path.name:
                        continue
                    if path.is_file() and path.suffix.lower() in extensions:
                        archive.write(path, path.relative_to(tipitaka_root))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tipitaka-root", default=Path("theravada/tipitaka"), type=Path)
    parser.add_argument(
        "--ledger",
        default=Path("theravada/tipitaka/sutta/candana-bhikkhu-text-ledger.tsv"),
        type=Path,
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    sutta_root = args.tipitaka_root / "sutta"
    rows = read_ledger(args.ledger, sutta_root)
    by_id_counter: dict[str, int] = defaultdict(int)
    generated: list[GeneratedItem] = []
    for row in rows:
        by_id_counter[row.canonical_id] += 1
        generated.append(copy_item(row, sutta_root, args.tipitaka_root, by_id_counter[row.canonical_id]))
    write_collection_indexes(generated, args.tipitaka_root)
    write_site(generated, args.tipitaka_root)
    write_zips(args.tipitaka_root)
    print(f"Generated {len(generated)} source pages")
    print(f"Site root: {args.tipitaka_root / 'site/index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
