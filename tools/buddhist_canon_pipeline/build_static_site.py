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

from youtube_metadata import YouTubeVideo, read_youtube_index, videos_for_canonical_id


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
    youtube_videos: list[YouTubeVideo]


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


def site_href(site_prefix: str, path: str) -> str:
    if site_prefix in ("", "."):
        return path
    return f"{site_prefix.rstrip('/')}/{path}"


def page(title: str, body: str, site_prefix: str = ".") -> str:
    css_href = site_href(site_prefix, "assets/style.css")
    home_href = site_href(site_prefix, "index.html")
    truths_href = site_href(site_prefix, "four-noble-truths.html")
    path_href = site_href(site_prefix, "eightfold-path.html")
    tipitaka_href = site_href(site_prefix, "tipitaka.html")
    sutta_href = site_href(site_prefix, "sutta.html")
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f'<link rel="stylesheet" href="{html.escape(css_href)}">\n'
        "</head>\n"
        "<body>\n"
        '<header class="site-header">\n'
        f'<a class="site-name" href="{html.escape(home_href)}">Free Buddhism</a>\n'
        '<nav aria-label="Primary navigation">\n'
        f'<a href="{html.escape(truths_href)}">Four Noble Truths</a>\n'
        f'<a href="{html.escape(path_href)}">Eightfold Path</a>\n'
        f'<a href="{html.escape(tipitaka_href)}">Tipiṭaka</a>\n'
        f'<a href="{html.escape(sutta_href)}">Suttas</a>\n'
        "</nav>\n"
        "</header>\n"
        f"<main>\n{body}\n</main>\n"
        '<footer class="site-footer">\n'
        '<p>Questions or corrections? <a href="mailto:admin@opensourceeverything.net">admin@opensourceeverything.net</a></p>\n'
        '<p>May these freely available teachings support understanding and practice.</p>\n'
        "</footer>\n"
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
    body_parts = [
        '<article class="sutta-text">',
        f'<p class="eyebrow">{html.escape(COLLECTION_TITLES.get(item.collection_path, item.collection_path))}</p>',
        f"<h1>{html.escape(item.canonical_id)} {html.escape(item.title)}</h1>",
        '<p class="resource-actions">',
        f'<a href="{txt_link}">Download TXT</a>',
        f'<a href="{pdf_link}">Download PDF</a>',
        f'<a href="{parent}">Browse this collection</a>',
        f'<a href="{home}">Home</a>',
        "</p>",
    ]
    if item.youtube_videos:
        body_parts.extend(
            [
                '<section class="listen-card" aria-labelledby="listen-heading">',
                '<p class="eyebrow">Candana Bhikkhu audio</p>',
                '<h2 id="listen-heading">Listen on YouTube</h2>',
                '<ul class="resource-list">',
            ]
        )
        for video in item.youtube_videos:
            duration = f"<span>Duration: {html.escape(video.duration)}</span>" if video.duration else ""
            body_parts.append(
                "<li>"
                f'<a href="{html.escape(video.url)}" rel="external">{html.escape(video.title)}</a>'
                f"{duration}"
                "</li>"
            )
        body_parts.extend(["</ul>", "</section>"])
    body_parts.extend(['<div class="source-text">', convert_text_to_html(txt_text), "</div>", "</article>"])
    body = "\n".join(body_parts)
    site_prefix = html_relative(item.html_path, tipitaka_root / "site")
    item.html_path.write_text(
        page(f"{item.canonical_id} {item.title}", body, site_prefix),
        encoding="utf-8",
        newline="\n",
    )
    index_path = item.folder / "index.html"
    if index_path != item.html_path:
        index_path.write_text(item.html_path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")


def copy_item(
    row: SourceRow,
    sutta_root: Path,
    tipitaka_root: Path,
    ordinal: int,
    youtube_index: dict[str, list[YouTubeVideo]],
) -> GeneratedItem:
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
        youtube_videos=videos_for_canonical_id(row.canonical_id, youtube_index),
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
        site_prefix = html_relative(collection_dir / "index.html", tipitaka_root / "site")
        (collection_dir / "index.html").write_text(
            page(COLLECTION_TITLES.get(collection, collection), body, site_prefix),
            encoding="utf-8",
            newline="\n",
        )


def local_sutta_resource(
    canonical_id: str,
    items_by_id: dict[str, list[GeneratedItem]],
    from_page: Path,
    label: str,
) -> str:
    matches = items_by_id.get(canonical_id, [])
    if not matches:
        return f'<span>{html.escape(label)} <small>(text not yet in this collection)</small></span>'
    href = html_relative(from_page, matches[0].html_path)
    return f'<a href="{html.escape(href)}">{html.escape(label)}</a> <small>read here</small>'


def youtube_resource(
    canonical_id: str,
    youtube_index: dict[str, list[YouTubeVideo]],
    label: str,
) -> str:
    videos = videos_for_canonical_id(canonical_id, youtube_index)
    if not videos:
        return f'<span>{html.escape(label)} <small>(Candana audio not currently found)</small></span>'
    video = videos[0]
    duration = f" · {video.duration}" if video.duration else ""
    return (
        f'<a href="{html.escape(video.url)}" rel="external">{html.escape(label)}</a> '
        f'<small>Candana Bhikkhu audio{html.escape(duration)}</small>'
    )


def resource_list(resources: list[str]) -> str:
    return '<ul class="resource-list">' + "".join(f"<li>{resource}</li>" for resource in resources) + "</ul>"


def write_site(
    items: list[GeneratedItem],
    tipitaka_root: Path,
    youtube_index: dict[str, list[YouTubeVideo]],
) -> None:
    site_dir = tipitaka_root / "site"
    assets = site_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "style.css").write_text(
        """:root {
  --ink: #22332b;
  --muted: #5d6a63;
  --paper: #fffdf7;
  --cream: #f4efe2;
  --leaf: #315f4b;
  --leaf-dark: #214435;
  --gold: #bb7c2b;
  --line: #d8cfbd;
  --shadow: 0 16px 40px rgba(44, 58, 48, 0.08);
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.05rem;
  line-height: 1.65;
}
a { color: var(--leaf-dark); text-underline-offset: 0.18em; }
a:hover { color: #7b4d14; }
.site-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1rem clamp(1rem, 5vw, 4rem);
  border-bottom: 1px solid var(--line);
  background: rgba(255, 253, 247, 0.96);
}
.site-name { font-size: 1.3rem; font-weight: 700; text-decoration: none; }
nav { display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem; }
nav a { font-family: system-ui, sans-serif; font-size: 0.9rem; text-decoration: none; }
main { width: min(76rem, calc(100% - 2rem)); margin: 0 auto; padding: 3rem 0 5rem; }
h1, h2, h3 { color: var(--leaf-dark); line-height: 1.15; }
h1 { font-size: clamp(2.3rem, 7vw, 5.3rem); margin: 0 0 1rem; letter-spacing: -0.035em; }
h2 { font-size: clamp(1.7rem, 4vw, 2.6rem); margin-top: 2.5rem; }
h3 { font-size: 1.25rem; }
.eyebrow {
  color: var(--gold);
  font-family: system-ui, sans-serif;
  font-size: 0.78rem;
  font-weight: 750;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.hero { padding: clamp(2rem, 8vw, 6.5rem) 0; max-width: 60rem; }
.hero p { max-width: 47rem; color: var(--muted); font-size: clamp(1.15rem, 2.4vw, 1.5rem); }
.button, .resource-actions a {
  display: inline-block;
  padding: 0.65rem 0.95rem;
  border: 1px solid var(--leaf);
  border-radius: 999px;
  font-family: system-ui, sans-serif;
  font-size: 0.88rem;
  font-weight: 650;
  text-decoration: none;
}
.button.primary { color: #fff; background: var(--leaf); }
.button-row, .resource-actions { display: flex; flex-wrap: wrap; gap: 0.65rem; }
.section-intro { max-width: 48rem; color: var(--muted); }
.card-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.card-grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.card {
  padding: clamp(1.2rem, 3vw, 2rem);
  border: 1px solid var(--line);
  border-radius: 1rem;
  background: #fff;
  box-shadow: var(--shadow);
}
.card h3 { margin-top: 0; }
.card p { color: var(--muted); }
.card-link { font-family: system-ui, sans-serif; font-size: 0.9rem; font-weight: 700; }
.teaching-section { padding: 2.25rem 0; border-top: 1px solid var(--line); scroll-margin-top: 2rem; }
.teaching-section > p { max-width: 52rem; }
.practice-note { padding: 0.8rem 1rem; border-left: 4px solid var(--gold); background: var(--cream); }
.resource-list { display: grid; gap: 0.6rem; padding-left: 1.25rem; }
.resource-list li { padding-left: 0.2rem; }
.resource-list small, .listen-card span { display: block; color: var(--muted); font-family: system-ui, sans-serif; font-size: 0.8rem; }
.listen-card { margin: 2rem 0; padding: 1.25rem 1.5rem; border: 1px solid var(--line); border-radius: 0.9rem; background: var(--cream); }
.listen-card h2 { margin: 0.15rem 0 0.5rem; font-size: 1.55rem; }
.source-text { margin-top: 2.5rem; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; line-height: 1.6; }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 0.75rem; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 0.7rem 0.8rem; border-bottom: 1px solid var(--line); vertical-align: top; text-align: left; }
th { color: var(--leaf-dark); background: var(--cream); font-family: system-ui, sans-serif; font-size: 0.82rem; }
.scope-note { margin: 2rem 0; padding: 1.25rem; border: 1px solid var(--line); border-radius: 0.8rem; background: var(--cream); }
.site-footer { padding: 2rem clamp(1rem, 5vw, 4rem); color: var(--muted); border-top: 1px solid var(--line); background: var(--cream); font-family: system-ui, sans-serif; font-size: 0.86rem; }
.site-footer p { margin: 0.25rem 0; }

@media (max-width: 760px) {
  .site-header { align-items: flex-start; flex-direction: column; }
  main { padding-top: 2rem; }
  .card-grid, .card-grid.three { grid-template-columns: 1fr; }
  h1 { font-size: clamp(2.2rem, 15vw, 4rem); }
}
""",
        encoding="utf-8",
        newline="\n",
    )

    items_by_id: dict[str, list[GeneratedItem]] = defaultdict(list)
    for item in items:
        items_by_id[item.canonical_id].append(item)

    index_body = """
<section class="hero">
  <p class="eyebrow">Teachings preserved in the Theravāda tradition</p>
  <h1>A practical path to the end of suffering.</h1>
  <p>Begin with the Four Noble Truths, follow the Noble Eightfold Path, and read or listen to the suttas in this growing collection of Candana Bhikkhu translations.</p>
  <div class="button-row">
    <a class="button primary" href="four-noble-truths.html">Begin with the Four Noble Truths</a>
    <a class="button" href="sutta.html">Browse all suttas</a>
  </div>
</section>

<section aria-labelledby="truths-heading">
  <p class="eyebrow">The framework</p>
  <h2 id="truths-heading">The Four Noble Truths</h2>
  <p class="section-intro">The Buddha’s teaching begins with a problem that can be understood, its cause that can be abandoned, its ending that can be realized, and a path that can be developed.</p>
  <div class="card-grid">
    <article class="card"><h3>1. Dukkha</h3><p>Conditioned life includes suffering, stress, change, and experiences that cannot provide lasting satisfaction.</p><a class="card-link" href="four-noble-truths.html#dukkha">Understand the first truth and read the suttas →</a></article>
    <article class="card"><h3>2. Samudaya</h3><p>Craving—for pleasure, continued existence, or escape—feeds the arising and continuation of suffering.</p><a class="card-link" href="four-noble-truths.html#origin">Explore the origin of suffering →</a></article>
    <article class="card"><h3>3. Nirodha</h3><p>When craving fades and ceases, release from suffering is possible: this is the peace of Nibbāna.</p><a class="card-link" href="four-noble-truths.html#cessation">Explore the cessation of suffering →</a></article>
    <article class="card"><h3>4. Magga</h3><p>The way leading to cessation is the Noble Eightfold Path, a complete training in wisdom, conduct, and mind.</p><a class="card-link" href="four-noble-truths.html#path">Explore the path leading to cessation →</a></article>
  </div>
</section>

<section aria-labelledby="path-heading">
  <p class="eyebrow">The practice</p>
  <h2 id="path-heading">The Noble Eightfold Path</h2>
  <p class="section-intro">Eight mutually supporting factors are commonly gathered into three trainings.</p>
  <div class="card-grid three">
    <article class="card"><h3>Wisdom</h3><p><a href="eightfold-path.html#right-view">Right View</a> sees actions and experience clearly. <a href="eightfold-path.html#right-intention">Right Intention</a> inclines toward renunciation, goodwill, and harmlessness.</p></article>
    <article class="card"><h3>Ethical conduct</h3><p><a href="eightfold-path.html#right-speech">Right Speech</a>, <a href="eightfold-path.html#right-action">Right Action</a>, and <a href="eightfold-path.html#right-livelihood">Right Livelihood</a> cultivate ways of living that do not cause harm.</p></article>
    <article class="card"><h3>Mental development</h3><p><a href="eightfold-path.html#right-effort">Right Effort</a>, <a href="eightfold-path.html#right-mindfulness">Right Mindfulness</a>, and <a href="eightfold-path.html#right-concentration">Right Concentration</a> train and steady the mind.</p></article>
  </div>
  <p><a class="button" href="eightfold-path.html">Study all eight factors and their suttas</a></p>
</section>

<section aria-labelledby="canon-heading">
  <p class="eyebrow">The collection</p>
  <h2 id="canon-heading">Theravāda and the Tipiṭaka</h2>
  <p class="section-intro">The Theravāda scriptural collection is known as the Pāli Canon or Tipiṭaka, “three baskets”: discipline, discourses, and systematic teachings. This site currently focuses on the Sutta Piṭaka and clearly marks areas not yet collected.</p>
  <div class="button-row">
    <a class="button primary" href="tipitaka.html">See how the Tipiṭaka is organized</a>
    <a class="button" href="downloads.html">Downloads and mirrors</a>
  </div>
</section>
"""
    (site_dir / "index.html").write_text(page("Free Buddhism", index_body), encoding="utf-8", newline="\n")

    truths_page = site_dir / "four-noble-truths.html"
    sn5611_read = local_sutta_resource("SN 56.11", items_by_id, truths_page, "Read SN 56.11 — Setting the Wheel of Dhamma in Motion")
    sn5611_listen = youtube_resource("SN 56.11", youtube_index, "Listen to SN 56.11")
    mn141_listen = youtube_resource("MN 141", youtube_index, "Listen to MN 141 — Exposition on the Truths")
    mn9_read = local_sutta_resource("MN 9", items_by_id, truths_page, "Read MN 9 — Discourse on Right View")
    mn117_listen = youtube_resource("MN 117", youtube_index, "Listen to MN 117 — The Great Forty")
    truth_resources = resource_list([sn5611_read, sn5611_listen, mn141_listen])
    truths_body = f"""
<p class="eyebrow">The framework of the teaching</p>
<h1>The Four Noble Truths</h1>
<p class="section-intro">These truths are not presented only as beliefs. Each carries a task: suffering is to be fully understood, its origin abandoned, its cessation realized, and the path developed.</p>

<article class="teaching-section" id="dukkha"><h2>1. The truth of suffering — dukkha</h2><p>Birth, aging, illness, death, separation from what is loved, contact with what is disliked, and not getting what is wanted are forms of dukkha. More broadly, whatever is grasped as “mine” is unstable and cannot serve as a lasting refuge.</p><p class="practice-note"><strong>Task:</strong> Dukkha is to be fully understood.</p><h3>Suttas to read and hear</h3>{truth_resources}{resource_list([mn9_read])}</article>
<article class="teaching-section" id="origin"><h2>2. The origin of suffering — samudaya</h2><p>The immediate origin is craving: craving for sensual pleasure, craving for becoming, and craving for non-becoming. Fed by ignorance, craving leads to grasping and renewed suffering.</p><p class="practice-note"><strong>Task:</strong> Craving is to be abandoned.</p><h3>Suttas to read and hear</h3>{truth_resources}</article>
<article class="teaching-section" id="cessation"><h2>3. The cessation of suffering — nirodha</h2><p>Cessation is the fading away and relinquishment of craving. It is release from dependence on what is impermanent and the peace toward which the teaching points.</p><p class="practice-note"><strong>Task:</strong> Cessation is to be realized.</p><h3>Suttas to read and hear</h3>{truth_resources}</article>
<article class="teaching-section" id="path"><h2>4. The path leading to cessation — magga</h2><p>The fourth truth is the Noble Eightfold Path. Its factors develop together as training in wisdom, ethical conduct, and mental cultivation.</p><p class="practice-note"><strong>Task:</strong> The path is to be developed.</p><h3>Suttas to read and hear</h3>{resource_list([sn5611_read, sn5611_listen, mn117_listen, mn9_read])}<p><a class="button primary" href="eightfold-path.html">Continue to the Noble Eightfold Path</a></p></article>
"""
    truths_page.write_text(page("The Four Noble Truths", truths_body), encoding="utf-8", newline="\n")

    path_page = site_dir / "eightfold-path.html"
    sn458 = '<a href="https://suttacentral.net/sn45.8/en/sujato" rel="external">Read SN 45.8 — Analysis of the Path</a> <small>external text; Candana audio not currently found</small>'
    mn117 = youtube_resource("MN 117", youtube_index, "Listen to MN 117 — The Great Forty")
    path_sections = [
        ("right-view", "1. Right View", "Understanding actions and their results, seeing what is skillful and unskillful, and understanding the Four Noble Truths.", [local_sutta_resource("MN 9", items_by_id, path_page, "Read MN 9 — Discourse on Right View"), youtube_resource("MN 9", youtube_index, "Listen to MN 9"), mn117]),
        ("right-intention", "2. Right Intention", "Intentions of renunciation, goodwill, and harmlessness replace intentions rooted in grasping, ill will, and cruelty.", [youtube_resource("MN 19", youtube_index, "Listen to MN 19 — Two Kinds of Thoughts"), mn117, sn458]),
        ("right-speech", "3. Right Speech", "Refraining from false, divisive, harsh, and idle speech, while learning to speak truthfully, helpfully, and at the right time.", [youtube_resource("MN 58", youtube_index, "Listen to MN 58 — To Prince Abhaya"), youtube_resource("MN 61", youtube_index, "Listen to MN 61 — Advice to Rāhula"), mn117]),
        ("right-action", "4. Right Action", "Refraining from killing, taking what is not given, and sexual misconduct; acting with care for oneself and others.", [youtube_resource("MN 41", youtube_index, "Listen to MN 41 — Brahmins of Sālā"), youtube_resource("MN 61", youtube_index, "Listen to MN 61 — Advice to Rāhula"), sn458]),
        ("right-livelihood", "5. Right Livelihood", "Earning a living without deception or harm and abandoning ways of livelihood that work against the path.", [youtube_resource("AN 5.177", youtube_index, "Listen to AN 5.177 within Candana’s AN 5.171–180 reading"), mn117, sn458]),
        ("right-effort", "6. Right Effort", "Preventing unskillful qualities, abandoning those that arise, cultivating skillful qualities, and sustaining them once present.", [mn117, sn458]),
        ("right-mindfulness", "7. Right Mindfulness", "Clearly observing body, feeling, mind, and qualities of experience with diligence, clear comprehension, and freedom from grasping.", [local_sutta_resource("MN 10", items_by_id, path_page, "Read MN 10 — Foundations of Mindfulness"), youtube_resource("MN 10", youtube_index, "Listen to MN 10"), local_sutta_resource("DN 22", items_by_id, path_page, "Read DN 22 — Great Discourse on Mindfulness"), youtube_resource("DN 22", youtube_index, "Listen to DN 22")]),
        ("right-concentration", "8. Right Concentration", "Unifying and steadying the mind through skillful collectedness, classically described through the four jhānas.", [local_sutta_resource("MN 44", items_by_id, path_page, "Read MN 44 — Shorter Series of Questions and Answers"), youtube_resource("MN 44", youtube_index, "Listen to MN 44"), mn117]),
    ]
    path_body_parts = [
        '<p class="eyebrow">The fourth noble truth in practice</p>',
        '<h1>The Noble Eightfold Path</h1>',
        '<p class="section-intro">The factors support one another. Right View gives direction; ethical conduct makes the mind less troubled; and mental development creates the steadiness needed for liberating understanding.</p>',
        '<div class="scope-note"><strong>Core readings:</strong> SN 45.8 defines all eight factors, while MN 117 examines how Right View, Right Effort, and Right Mindfulness work around the other factors.</div>',
    ]
    for section_id, heading, description, resources in path_sections:
        path_body_parts.extend(
            [
                f'<article class="teaching-section" id="{section_id}">',
                f"<h2>{heading}</h2>",
                f"<p>{description}</p>",
                "<h3>Suttas to read and hear</h3>",
                resource_list(resources),
                "</article>",
            ]
        )
    path_page.write_text(page("The Noble Eightfold Path", "\n".join(path_body_parts)), encoding="utf-8", newline="\n")

    unique_ids = len({item.canonical_id for item in items})
    tipitaka_body = f"""
<p class="eyebrow">The Theravāda textual tradition</p>
<h1>How the Tipiṭaka is organized</h1>
<p class="section-intro"><em>Tipiṭaka</em> means “three baskets.” It is the traditional name for the Pāli Canon preserved by the Theravāda tradition.</p>
<div class="card-grid three">
  <article class="card"><h2>Vinaya Piṭaka</h2><p>The basket of monastic discipline: training rules, procedures, and accounts surrounding the life of the early monastic community.</p><p><strong>Current site status:</strong> organization reserved; texts not yet collected.</p></article>
  <article class="card"><h2>Sutta Piṭaka</h2><p>The basket of discourses: teachings, dialogues, verses, and training instructions attributed to the Buddha and close disciples.</p><p><strong>Current site status:</strong> {len(items)} source pages representing {unique_ids} canonical or source IDs.</p><p><a class="card-link" href="sutta.html">Browse the Sutta Piṭaka collection →</a></p></article>
  <article class="card"><h2>Abhidhamma Piṭaka</h2><p>The basket of systematic teaching: detailed analytical arrangements of experience and mental and material phenomena.</p><p><strong>Current site status:</strong> organization reserved; texts not yet collected.</p></article>
</div>
<section><h2>The five Nikāyas</h2><p class="section-intro">The Sutta Piṭaka is commonly organized into five collections.</p><div class="card-grid">
  <article class="card"><h3><a href="../sutta/digha-nikaya/index.html">Dīgha Nikāya</a></h3><p>Long discourses.</p></article>
  <article class="card"><h3><a href="../sutta/majjhima-nikaya/index.html">Majjhima Nikāya</a></h3><p>Middle-length discourses.</p></article>
  <article class="card"><h3><a href="../sutta/samyutta-nikaya/index.html">Saṁyutta Nikāya</a></h3><p>Connected discourses arranged by topic.</p></article>
  <article class="card"><h3><a href="../sutta/anguttara-nikaya/index.html">Aṅguttara Nikāya</a></h3><p>Numerical discourses arranged by numbered sets.</p></article>
  <article class="card"><h3><a href="../sutta/khuddaka-nikaya/sutta-nipata/index.html">Khuddaka Nikāya</a></h3><p>A varied collection of shorter books, verses, stories, and later canonical works. The present site includes selected books and texts.</p></article>
</div></section>
<div class="scope-note"><strong>Collection scope:</strong> this is a growing, Sutta-focused corpus. The description above explains the traditional canon; it does not claim that all three baskets are hosted here.</div>
"""
    (site_dir / "tipitaka.html").write_text(page("Theravāda and the Tipiṭaka", tipitaka_body), encoding="utf-8", newline="\n")

    rows = []
    for item in sorted(items, key=lambda x: (x.collection_path, x.base_name)):
        if item.youtube_videos:
            audio = f'<a href="{html.escape(item.youtube_videos[0].url)}" rel="external">YouTube</a>'
        else:
            audio = "—"
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.collection_path)}</td>"
            f"<td>{html.escape(item.canonical_id)}</td>"
            f"<td><a href=\"{html_relative(site_dir / 'sutta.html', item.html_path)}\">{html.escape(item.title)}</a></td>"
            f"<td><a href=\"{html_relative(site_dir / 'sutta.html', item.txt_path)}\">txt</a></td>"
            f"<td><a href=\"{html_relative(site_dir / 'sutta.html', item.pdf_path)}\">pdf</a></td>"
            f"<td>{audio}</td>"
            "</tr>"
        )
    sutta_body = "\n".join(
        [
            '<p class="eyebrow">Read and listen</p>',
            "<h1>Sutta Piṭaka</h1>",
            f'<p class="section-intro">{len(items)} source pages, with Candana Bhikkhu YouTube audio linked wherever the playlist metadata provides a reliable match.</p>',
            '<div class="table-wrap"><table>',
            "<tr><th>Collection</th><th>ID</th><th>Title</th><th>TXT</th><th>PDF</th><th>Audio</th></tr>",
            *rows,
            "</table></div>",
        ]
    )
    (site_dir / "sutta.html").write_text(page("Sutta Piṭaka", sutta_body), encoding="utf-8", newline="\n")

    downloads_body = """
<p class="eyebrow">Keep a local copy</p>
<h1>Downloads</h1>
<p>ZIP bundles are generated artifacts for releases and local mirrors. They are not stored in git.</p>
<ul>
  <li><a href="../downloads/tipitaka-txt.zip">Tipiṭaka text files</a></li>
  <li><a href="../downloads/tipitaka-pdf.zip">Tipiṭaka PDF files</a></li>
  <li><a href="../downloads/tipitaka-html.zip">Tipiṭaka HTML files</a></li>
  <li><a href="../downloads/tipitaka-all.zip">Complete available collection</a></li>
</ul>
"""
    (site_dir / "downloads.html").write_text(page("Downloads", downloads_body), encoding="utf-8", newline="\n")


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
    parser.add_argument(
        "--youtube-manifest-dir",
        default=Path("metadata/youtube-playlists/manifests"),
        type=Path,
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    sutta_root = args.tipitaka_root / "sutta"
    rows = read_ledger(args.ledger, sutta_root)
    youtube_index = read_youtube_index(args.youtube_manifest_dir)
    by_id_counter: dict[str, int] = defaultdict(int)
    generated: list[GeneratedItem] = []
    for row in rows:
        by_id_counter[row.canonical_id] += 1
        generated.append(
            copy_item(
                row,
                sutta_root,
                args.tipitaka_root,
                by_id_counter[row.canonical_id],
                youtube_index,
            )
        )
    write_collection_indexes(generated, args.tipitaka_root)
    write_site(generated, args.tipitaka_root, youtube_index)
    write_zips(args.tipitaka_root)
    print(f"Generated {len(generated)} source pages")
    print(f"Site root: {args.tipitaka_root / 'site/index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
