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
    dhamma_href = site_href(site_prefix, "dhamma.html")
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
        f'<a href="{html.escape(dhamma_href)}">Dhamma</a>\n'
        f'<a href="{html.escape(truths_href)}">Four Noble Truths</a>\n'
        f'<a href="{html.escape(path_href)}">Eightfold Path</a>\n'
        f'<a href="{html.escape(tipitaka_href)}">Tipiṭaka</a>\n'
        f'<a href="{html.escape(sutta_href)}">Suttas</a>\n'
        "</nav>\n"
        "</header>\n"
        f"<main>\n{body}\n</main>\n"
        '<footer class="site-footer">\n'
        '<p>Contact: <a href="mailto:admin@opensourceeverything.net">admin@opensourceeverything.net</a></p>\n'
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
  --ink: #20231f;
  --muted: #626760;
  --paper: #fcfcf9;
  --soft: #f2f3ee;
  --link: #274f3b;
  --line: #d9ddd5;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: 1.08rem;
  line-height: 1.7;
}
a { color: var(--link); text-decoration-thickness: 1px; text-underline-offset: 0.2em; }
a:hover { color: #111; }
.site-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem 2rem;
  width: min(48rem, calc(100% - 2rem));
  margin: 0 auto;
  padding: 1.25rem 0;
  border-bottom: 1px solid var(--line);
}
.site-name { color: var(--ink); font-size: 1.05rem; font-weight: 700; text-decoration: none; }
nav { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; }
nav a { font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.78rem; text-decoration: none; }
main { width: min(48rem, calc(100% - 2rem)); margin: 0 auto; padding: 4rem 0 6rem; }
h1, h2, h3 { line-height: 1.25; }
h1 { margin: 0 0 2rem; font-size: clamp(2rem, 7vw, 3.4rem); font-weight: 500; letter-spacing: -0.025em; }
h2 { margin-top: 3rem; font-size: 1.55rem; font-weight: 600; }
h3 { margin-top: 2.25rem; font-size: 1.12rem; }
p { max-width: 44rem; }
.eyebrow {
  color: var(--muted);
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.72rem;
  font-weight: 650;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.home-statement { padding: 1.5rem 0 3rem; }
.home-statement p { margin: 0 0 2rem; font-size: clamp(1.18rem, 3vw, 1.42rem); }
.home-statement .canon-statement { margin-top: 3.5rem; }
.section-intro { color: var(--muted); font-size: 1.12rem; }
.numbered-teachings { padding-left: 1.5rem; }
.numbered-teachings > li { margin: 0 0 1rem; padding-left: 0.25rem; }
.numbered-teachings ul { margin-top: 0.5rem; }
.teaching-section { padding: 1.5rem 0 2rem; border-top: 1px solid var(--line); scroll-margin-top: 2rem; }
.practice-note, .scope-note { margin: 1.5rem 0; padding: 1rem 1.1rem; background: var(--soft); }
.resource-list { display: grid; gap: 0.75rem; padding-left: 1.25rem; }
.resource-list li { padding-left: 0.1rem; }
.resource-list small, .listen-card span { display: block; color: var(--muted); font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.78rem; }
.listen-card { margin: 2rem 0; padding: 1rem 1.1rem; border: 1px solid var(--line); background: var(--soft); }
.listen-card h2 { margin: 0.15rem 0 0.5rem; font-size: 1.3rem; }
.resource-actions { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; }
.resource-actions a { font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.8rem; }
.source-text { margin-top: 2.5rem; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; line-height: 1.6; }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 0.7rem 0.8rem; border-bottom: 1px solid var(--line); vertical-align: top; text-align: left; }
th { background: var(--soft); font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.78rem; }
.site-footer { width: min(48rem, calc(100% - 2rem)); margin: 0 auto; padding: 2rem 0 3rem; color: var(--muted); border-top: 1px solid var(--line); font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.78rem; }
.site-footer p { margin: 0.25rem 0; }

@media (max-width: 760px) {
  .site-header { align-items: flex-start; flex-direction: column; }
  main { padding: 2.5rem 0 4rem; }
}
""",
        encoding="utf-8",
        newline="\n",
    )

    items_by_id: dict[str, list[GeneratedItem]] = defaultdict(list)
    for item in items:
        items_by_id[item.canonical_id].append(item)

    index_body = """
<h1>Free Buddhism</h1>
<section class="home-statement">
  <p>This website attempts to present the teachings of <a href="tipitaka.html">Theravāda Buddhism</a> without distortion.</p>
  <p>The <a href="dhamma.html">Dhamma</a> is the Buddha’s teaching as a whole.</p>
  <p>The <a href="four-noble-truths.html">Four Noble Truths</a> are its core framework.<br>
  The <a href="eightfold-path.html">Noble Eightfold Path</a> is the fourth truth: the path to the <a href="four-noble-truths.html#cessation">cessation of suffering</a>.</p>
  <p class="canon-statement">The <a href="tipitaka.html">Pāli Tipiṭaka</a> is the Theravāda tradition’s primary textual record of the Buddha’s <a href="dhamma.html">Dhamma</a>.</p>
</section>
"""
    (site_dir / "index.html").write_text(page("Free Buddhism", index_body), encoding="utf-8", newline="\n")

    dhamma_page = site_dir / "dhamma.html"
    dhamma_body = f"""
<p class="eyebrow">The teaching as a whole</p>
<h1>The Dhamma</h1>
<p class="section-intro">The Dhamma is the Buddha’s teaching and the reality that teaching makes known.</p>
<p>Its purpose is the ending of suffering. Its core framework is the <a href="four-noble-truths.html">Four Noble Truths</a>. Its path of practice is the <a href="eightfold-path.html">Noble Eightfold Path</a>.</p>
<p>The teachings are preserved primarily in the <a href="tipitaka.html">Pāli Tipiṭaka</a>. Understanding is tested through conduct, cultivation of mind, and direct knowledge—not through belief alone.</p>
<h2>Relevant suttas</h2>
{resource_list([
    local_sutta_resource("SN 56.11", items_by_id, dhamma_page, "SN 56.11 — Setting the Wheel of Dhamma in Motion"),
    youtube_resource("SN 56.11", youtube_index, "Listen to SN 56.11"),
    local_sutta_resource("MN 9", items_by_id, dhamma_page, "MN 9 — Right View"),
])}
"""
    dhamma_page.write_text(page("The Dhamma", dhamma_body), encoding="utf-8", newline="\n")

    truths_page = site_dir / "four-noble-truths.html"
    sn5611_read = local_sutta_resource("SN 56.11", items_by_id, truths_page, "Read SN 56.11 — Setting the Wheel of Dhamma in Motion")
    sn5611_listen = youtube_resource("SN 56.11", youtube_index, "Listen to SN 56.11")
    mn141_listen = youtube_resource("MN 141", youtube_index, "Listen to MN 141 — Exposition on the Truths")
    mn9_read = local_sutta_resource("MN 9", items_by_id, truths_page, "Read MN 9 — Discourse on Right View")
    mn117_listen = youtube_resource("MN 117", youtube_index, "Listen to MN 117 — The Great Forty")
    truths_body = f"""
<h1>The Four Noble Truths</h1>
<ol class="numbered-teachings">
  <li id="dukkha">Clinging to conditioned existence is unsatisfactory.</li>
  <li id="origin">Craving sustains that clinging and dissatisfaction.</li>
  <li id="cessation">Ending craving ends that clinging and dissatisfaction.</li>
  <li id="path">The <a href="eightfold-path.html">Noble Eightfold Path</a> leads to that ending.</li>
</ol>
<p class="practice-note">The first truth is to be understood. The second is to be abandoned. The third is to be realized. The fourth is to be developed.</p>
<h2>Relevant suttas</h2>
{resource_list([sn5611_read, sn5611_listen, mn141_listen, mn9_read, mn117_listen])}
"""
    truths_page.write_text(page("The Four Noble Truths", truths_body), encoding="utf-8", newline="\n")

    path_page = site_dir / "eightfold-path.html"
    path_dir = site_dir / "path"
    path_dir.mkdir(parents=True, exist_ok=True)
    path_sections = [
        {
            "slug": "right-view",
            "name": "Right view",
            "summary": "Understand suffering, its cause, ending, and path.",
            "details": "<p><strong>Mundane right view:</strong> Understand karma: intentional actions have consequences in this life and across lives.</p><p><strong>Supramundane right view:</strong> Directly understand the Four Noble Truths.</p><p>Right view gives direction to every other factor of the path.</p>",
            "resources": [("local", "MN 9", "MN 9 — Discourse on Right View"), ("youtube", "MN 9", "Listen to MN 9"), ("youtube", "MN 117", "MN 117 — The Great Forty")],
        },
        {
            "slug": "right-intention",
            "name": "Right intention",
            "summary": "Intend renunciation, goodwill, and harmlessness.",
            "details": "<p>Right intention turns the mind away from sensual grasping, ill will, and cruelty.</p><p>It inclines thought and purpose toward letting go, goodwill, and compassion.</p>",
            "resources": [("youtube", "MN 19", "MN 19 — Two Kinds of Thoughts"), ("youtube", "MN 117", "MN 117 — The Great Forty"), ("external", "", "SN 45.8 — Analysis of the Path")],
        },
        {
            "slug": "right-speech",
            "name": "Right speech",
            "summary": "Avoid lying, division, abuse, and idle chatter.",
            "details": "<p>Right speech abstains from false, divisive, harsh, and purposeless speech.</p><p>Speech is considered in light of truth, benefit, timing, and the intention behind it.</p>",
            "resources": [("youtube", "MN 58", "MN 58 — To Prince Abhaya"), ("youtube", "MN 61", "MN 61 — Advice to Rāhula"), ("youtube", "MN 117", "MN 117 — The Great Forty")],
        },
        {
            "slug": "right-action",
            "name": "Right action",
            "summary": "Avoid killing, stealing, and sexual misconduct.",
            "details": "<p>Right action abstains from intentionally taking life, taking what is not given, and sexual misconduct.</p><p>It makes bodily conduct consistent with non-harm and restraint.</p>",
            "resources": [("youtube", "MN 41", "MN 41 — Brahmins of Sālā"), ("youtube", "MN 61", "MN 61 — Advice to Rāhula"), ("external", "", "SN 45.8 — Analysis of the Path")],
        },
        {
            "slug": "right-livelihood",
            "name": "Right livelihood",
            "summary": "Earn without causing harm.",
            "details": "<p>Right livelihood brings one’s means of support into accord with right speech and right action.</p><p>For lay followers, the texts specifically reject trade in weapons, living beings, meat, intoxicants, and poison.</p>",
            "resources": [("youtube", "AN 5.177", "AN 5.177 within the AN 5.171–180 reading"), ("youtube", "MN 117", "MN 117 — The Great Forty"), ("external", "", "SN 45.8 — Analysis of the Path")],
        },
        {
            "slug": "right-effort",
            "name": "Right effort",
            "summary": "Prevent and abandon unskillful states; develop skillful ones.",
            "details": "<p>Right effort has four tasks: prevent unarisen unskillful states, abandon arisen unskillful states, develop unarisen skillful states, and sustain arisen skillful states.</p><p>It is purposeful cultivation, guided by right view.</p>",
            "resources": [("youtube", "MN 117", "MN 117 — The Great Forty"), ("external", "", "SN 45.8 — Analysis of the Path")],
        },
        {
            "slug": "right-mindfulness",
            "name": "Right mindfulness",
            "summary": "Clearly observe body, feeling, mind, and phenomena.",
            "details": "<p>Right mindfulness establishes clear observation of body, feeling, mind, and phenomena.</p><p>It is practiced ardently, with clear comprehension, while putting away craving and distress regarding the world.</p>",
            "resources": [("local", "MN 10", "MN 10 — Foundations of Mindfulness"), ("youtube", "MN 10", "Listen to MN 10"), ("local", "DN 22", "DN 22 — Great Discourse on Mindfulness"), ("youtube", "DN 22", "Listen to DN 22")],
        },
        {
            "slug": "right-concentration",
            "name": "Right concentration",
            "summary": "Develop a unified mind through the four jhānas.",
            "details": "<p>Right concentration is the unification of mind developed through the four jhānas.</p><p>Supported by the other seven factors, collectedness steadies the mind for direct knowledge and release.</p>",
            "resources": [("local", "MN 44", "MN 44 — Shorter Series of Questions and Answers"), ("youtube", "MN 44", "Listen to MN 44"), ("youtube", "MN 117", "MN 117 — The Great Forty")],
        },
    ]

    overview_items = []
    for section in path_sections:
        nested = ""
        if section["slug"] == "right-view":
            nested = "<ul><li>Mundane: Understand karma: actions have consequences across lives.</li><li>Supramundane: Directly understand the Four Noble Truths.</li></ul>"
        overview_items.append(
            f'<li><a href="path/{section["slug"]}.html">{html.escape(section["name"])}</a>: '
            f'{html.escape(section["summary"])}{nested}</li>'
        )

    path_body = "\n".join(
        [
            "<h1>The Noble Eightfold Path</h1>",
            '<ol class="numbered-teachings">',
            *overview_items,
            "</ol>",
            '<p class="practice-note">The path is one training with eight mutually supporting factors.</p>',
            "<h2>Relevant suttas</h2>",
            resource_list(
                [
                    '<a href="https://suttacentral.net/sn45.8/en/sujato" rel="external">SN 45.8 — Analysis of the Path</a> <small>external text; Candana audio not currently found</small>',
                    youtube_resource("MN 117", youtube_index, "MN 117 — The Great Forty"),
                    local_sutta_resource("SN 56.11", items_by_id, path_page, "SN 56.11 — Setting the Wheel of Dhamma in Motion"),
                    youtube_resource("SN 56.11", youtube_index, "Listen to SN 56.11"),
                ]
            ),
        ]
    )
    path_page.write_text(page("The Noble Eightfold Path", path_body), encoding="utf-8", newline="\n")

    for section in path_sections:
        detail_page = path_dir / f'{section["slug"]}.html'
        rendered_resources = []
        for kind, canonical_id, label in section["resources"]:
            if kind == "local":
                rendered_resources.append(local_sutta_resource(canonical_id, items_by_id, detail_page, label))
            elif kind == "youtube":
                rendered_resources.append(youtube_resource(canonical_id, youtube_index, label))
            else:
                rendered_resources.append(
                    f'<a href="https://suttacentral.net/sn45.8/en/sujato" rel="external">{html.escape(label)}</a> '
                    '<small>external text; Candana audio not currently found</small>'
                )
        detail_body = "\n".join(
            [
                '<p class="eyebrow"><a href="../eightfold-path.html">The Noble Eightfold Path</a></p>',
                f'<h1>{html.escape(section["name"])}</h1>',
                f'<p class="section-intro">{html.escape(section["summary"])}</p>',
                str(section["details"]),
                "<h2>Relevant suttas</h2>",
                resource_list(rendered_resources),
            ]
        )
        detail_page.write_text(page(str(section["name"]), detail_body, ".."), encoding="utf-8", newline="\n")

    unique_ids = len({item.canonical_id for item in items})
    tipitaka_body = f"""
<h1>The Pāli Tipiṭaka</h1>
<p class="section-intro">The Theravāda scriptural collection is known as the Pāli Canon or Tipiṭaka, “three baskets”: discipline, discourses, and systematic teachings.</p>
<ol class="numbered-teachings">
  <li><strong>Vinaya Piṭaka:</strong> monastic discipline, procedures, and the life of the early monastic community.</li>
  <li><strong>Sutta Piṭaka:</strong> discourses, dialogues, verses, and instructions attributed to the Buddha and close disciples.</li>
  <li><strong>Abhidhamma Piṭaka:</strong> systematic analysis of mental and material phenomena.</li>
</ol>
<p class="scope-note">This site currently focuses on the Sutta Piṭaka. It contains {len(items)} source pages representing {unique_ids} canonical or source IDs. Vinaya and Abhidhamma texts have not yet been collected here.</p>
<h2>The five Nikāyas of the Sutta Piṭaka</h2>
<ol class="numbered-teachings">
  <li><a href="../sutta/digha-nikaya/index.html">Dīgha Nikāya</a>: long discourses.</li>
  <li><a href="../sutta/majjhima-nikaya/index.html">Majjhima Nikāya</a>: middle-length discourses.</li>
  <li><a href="../sutta/samyutta-nikaya/index.html">Saṁyutta Nikāya</a>: connected discourses arranged by topic.</li>
  <li><a href="../sutta/anguttara-nikaya/index.html">Aṅguttara Nikāya</a>: numerical discourses arranged by numbered sets.</li>
  <li><a href="../sutta/khuddaka-nikaya/sutta-nipata/index.html">Khuddaka Nikāya</a>: a varied collection of shorter books, verses, stories, and later canonical works.</li>
</ol>
<p><a href="sutta.html">Browse the available texts</a> · <a href="downloads.html">Downloads and mirrors</a></p>
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
