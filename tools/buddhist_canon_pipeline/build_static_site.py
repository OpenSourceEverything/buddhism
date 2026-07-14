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
    home_href = site_href(site_prefix, "index.html")
    dhamma_href = site_href(site_prefix, "dhamma.html")
    teachings_href = site_href(site_prefix, "teachings.html")
    practice_href = site_href(site_prefix, "practice.html")
    glossary_href = site_href(site_prefix, "glossary.html")
    tipitaka_href = site_href(site_prefix, "tipitaka.html")
    sutta_href = site_href(site_prefix, "sutta.html")
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        "</head>\n"
        "<body>\n"
        f'<p><a href="{html.escape(home_href)}">Home</a> | '
        f'<a href="{html.escape(dhamma_href)}">Dhamma</a> | '
        f'<a href="{html.escape(teachings_href)}">Teachings</a> | '
        f'<a href="{html.escape(practice_href)}">Practice</a> | '
        f'<a href="{html.escape(glossary_href)}">Glossary</a> | '
        f'<a href="{html.escape(tipitaka_href)}">Tipiṭaka</a> | '
        f'<a href="{html.escape(sutta_href)}">Suttas</a></p>\n'
        f"{body}\n"
        '<p>Contact: <a href="mailto:admin@opensourceeverything.net">admin@opensourceeverything.net</a></p>\n'
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
        f'<p>{html.escape(COLLECTION_TITLES.get(item.collection_path, item.collection_path))}</p>',
        f"<h1>{html.escape(item.canonical_id)} {html.escape(item.title)}</h1>",
        "<p>",
        f'<a href="{txt_link}">Download TXT</a>',
        f'<a href="{pdf_link}">Download PDF</a>',
        f'<a href="{parent}">Browse this collection</a>',
        f'<a href="{home}">Home</a>',
        "</p>",
    ]
    if item.youtube_videos:
        body_parts.extend(
            [
                "<p>Candana Bhikkhu audio</p>",
                '<h2 id="listen-heading">Listen on YouTube</h2>',
                "<ul>",
            ]
        )
        for video in item.youtube_videos:
            duration = f" (Duration: {html.escape(video.duration)})" if video.duration else ""
            body_parts.append(
                "<li>"
                f'<a href="{html.escape(video.url)}" rel="external">{html.escape(video.title)}</a>'
                f"{duration}"
                "</li>"
            )
        body_parts.append("</ul>")
    body_parts.extend(["<h2>Text</h2>", convert_text_to_html(txt_text)])
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
        return f'{html.escape(label)} (text not yet in this collection)'
    href = html_relative(from_page, matches[0].html_path)
    return f'<a href="{html.escape(href)}">{html.escape(label)}</a> (read here)'


def youtube_resource(
    canonical_id: str,
    youtube_index: dict[str, list[YouTubeVideo]],
    label: str,
) -> str:
    videos = videos_for_canonical_id(canonical_id, youtube_index)
    if not videos:
        return f'{html.escape(label)} (Candana audio not currently found)'
    video = videos[0]
    duration = f" · {video.duration}" if video.duration else ""
    return (
        f'<a href="{html.escape(video.url)}" rel="external">{html.escape(label)}</a> '
        f'(Candana Bhikkhu audio{html.escape(duration)})'
    )


def resource_list(resources: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{resource}</li>" for resource in resources) + "</ul>"


def write_site(
    items: list[GeneratedItem],
    tipitaka_root: Path,
    youtube_index: dict[str, list[YouTubeVideo]],
) -> None:
    site_dir = tipitaka_root / "site"

    items_by_id: dict[str, list[GeneratedItem]] = defaultdict(list)
    for item in items:
        items_by_id[item.canonical_id].append(item)

    index_body = """
<h1>Home</h1>
<p>This website attempts to present the teachings of <a href="theravada.html">Theravāda Buddhism</a> without distortion.</p>
<p>The <a href="dhamma.html">Dhamma</a> is the Buddha’s teaching as a whole.</p>
<p>The <a href="four-noble-truths.html">Four Noble Truths</a> are its core framework.<br>
The <a href="eightfold-path.html">Noble Eightfold Path</a> is the fourth truth: the path to the <a href="four-noble-truths.html#cessation">cessation of suffering</a>.</p>
<p>The <a href="tipitaka.html">Pāli Tipiṭaka</a> is the Theravāda tradition’s primary textual record of the Buddha’s <a href="dhamma.html">Dhamma</a>.</p>
"""
    (site_dir / "index.html").write_text(page("Home", index_body), encoding="utf-8", newline="\n")

    theravada_body = """
<h1>Theravāda Buddhism</h1>
<p>Theravāda is the oldest surviving Buddhist tradition.</p>
<p>It follows the <a href="tipitaka.html">Pāli Tipiṭaka</a> as its primary scriptural authority. The later Mahāyāna sūtras are not part of its canon.</p>
"""
    (site_dir / "theravada.html").write_text(
        page("Theravāda Buddhism", theravada_body),
        encoding="utf-8",
        newline="\n",
    )

    dhamma_page = site_dir / "dhamma.html"
    dhamma_body = f"""
<h1>Dhamma</h1>
<p>The Dhamma is the Buddha’s teaching as a whole. Its purpose is the ending of suffering.</p>
<pre>Dhamma
|
+-- Core teaching
|   +-- <a href="four-noble-truths.html">Four Noble Truths</a>
|   +-- <a href="eightfold-path.html">Noble Eightfold Path</a>
|
+-- <a href="teachings.html">Teachings</a>
|   +-- <a href="teachings.html#three-characteristics">Three characteristics</a>
|   +-- <a href="teachings.html#five-aggregates">Five aggregates</a>
|   +-- <a href="teachings.html#dependent-origination">Dependent origination</a>
|   +-- <a href="teachings.html#kamma">Kamma</a>
|   +-- <a href="teachings.html#rebirth">Rebirth</a>
|   +-- <a href="teachings.html#nibbana">Nibbāna</a>
|   +-- <a href="teachings.html#ten-fetters">Ten fetters</a>
|
+-- <a href="practice.html">Practice</a>
|   +-- <a href="practice.html#five-precepts">Five precepts</a>
|   +-- <a href="practice.html#five-recollections">Five recollections</a>
|   +-- <a href="practice.html#four-foundations-of-mindfulness">Four foundations of mindfulness</a>
|   +-- <a href="practice.html#five-hindrances">Five hindrances</a>
|   +-- <a href="practice.html#seven-awakening-factors">Seven awakening factors</a>
|   +-- <a href="practice.html#four-jhanas">Four jhānas</a>
|
+-- <a href="glossary.html">Glossary</a>
    +-- Alphabetical list of every term</pre>
<h2>Relevant suttas</h2>
{resource_list([
    local_sutta_resource("SN 56.11", items_by_id, dhamma_page, "SN 56.11 — Setting the Wheel of Dhamma in Motion"),
    youtube_resource("SN 56.11", youtube_index, "Listen to SN 56.11"),
    local_sutta_resource("MN 9", items_by_id, dhamma_page, "MN 9 — Right View"),
])}
"""
    dhamma_page.write_text(page("Dhamma", dhamma_body), encoding="utf-8", newline="\n")

    teachings_page = site_dir / "teachings.html"
    teachings_body = f"""
<h1>Teachings</h1>
<h2 id="three-characteristics">Three characteristics</h2>
<p>Conditioned things are impermanent and unsatisfactory; all phenomena are not-self.</p>
<h2 id="five-aggregates">Five aggregates</h2>
<p>Form, feeling, perception, mental formations, and consciousness are the five bases of clinging.</p>
<h2 id="dependent-origination">Dependent origination</h2>
<p>Phenomena arise and cease according to conditions; the twelve-link sequence explains the arising and cessation of suffering.</p>
<h2 id="kamma">Kamma</h2>
<p>Intentional actions of body, speech, and mind have consequences according to their ethical quality.</p>
<h2 id="rebirth">Rebirth</h2>
<p>After death, continued existence arises according to conditions without a permanent self passing from one life to another.</p>
<h2 id="nibbana">Nibbāna</h2>
<p>Nibbāna is the ending of greed, hatred, and delusion: release from suffering and rebirth.</p>
<h2 id="ten-fetters">Ten fetters</h2>
<p>Identity view, doubt, attachment to rites, sensual desire, ill will, desire for form existence, desire for formless existence, conceit, restlessness, and ignorance bind beings to repeated existence.</p>
<h2>Relevant suttas</h2>
{resource_list([
    local_sutta_resource("SN 22.59", items_by_id, teachings_page, "SN 22.59 — The Characteristic of Not-Self"),
    youtube_resource("SN 22.59", youtube_index, "Listen to SN 22.59"),
    local_sutta_resource("SN 12.2", items_by_id, teachings_page, "SN 12.2 — Analysis of Dependent Origination"),
    youtube_resource("SN 12.2", youtube_index, "Listen to SN 12.2"),
    local_sutta_resource("AN 6.63", items_by_id, teachings_page, "AN 6.63 — Penetrative"),
    youtube_resource("AN 6.63", youtube_index, "Listen to AN 6.63"),
    local_sutta_resource("MN 135", items_by_id, teachings_page, "MN 135 — The Shorter Exposition of Kamma"),
    youtube_resource("MN 135", youtube_index, "Listen to MN 135"),
    youtube_resource("Ud 8.3", youtube_index, "Ud 8.3 — Nibbāna"),
    youtube_resource("AN 10.13", youtube_index, "AN 10.13 within the AN 10.11–20 reading — The Ten Fetters"),
    youtube_resource("Dhp 370", youtube_index, "Dhammapada 370 — Giving Up the Fetters"),
])}
"""
    teachings_page.write_text(page("Teachings", teachings_body), encoding="utf-8", newline="\n")

    practice_page = site_dir / "practice.html"
    practice_body = f"""
<h1>Practice</h1>
<h2 id="five-precepts">Five precepts</h2>
<p>Abstain from killing, stealing, sexual misconduct, false speech, and intoxicants that cause heedlessness.</p>
<h2 id="five-recollections">Five recollections</h2>
<p>Frequently recollect aging, illness, death, separation from what is dear, and ownership of one’s kamma.</p>
<h2 id="four-foundations-of-mindfulness">Four foundations of mindfulness</h2>
<p>Observe body, feeling, mind, and phenomena clearly and without clinging.</p>
<h2 id="five-hindrances">Five hindrances</h2>
<p>Sensual desire, ill will, sloth and torpor, restlessness and remorse, and doubt obstruct clarity and concentration.</p>
<h2 id="seven-awakening-factors">Seven awakening factors</h2>
<p>Mindfulness, investigation, energy, rapture, tranquility, concentration, and equanimity support awakening.</p>
<h2 id="four-jhanas">Four jhānas</h2>
<p>Four stages of meditative unification progressively refine rapture, pleasure, equanimity, and mindfulness.</p>
<h2>Relevant suttas</h2>
{resource_list([
    youtube_resource("Dhp 246", youtube_index, "Dhammapada 246–247 — The Five Precepts"),
    youtube_resource("AN 5.57", youtube_index, "AN 5.57 within the AN 5.51–60 reading — Five Recollections"),
    local_sutta_resource("MN 10", items_by_id, practice_page, "MN 10 — Foundations of Mindfulness"),
    youtube_resource("MN 10", youtube_index, "Listen to MN 10"),
    local_sutta_resource("SN 46.51", items_by_id, practice_page, "SN 46.51 — Nourishment for the Hindrances and Awakening Factors"),
    youtube_resource("SN 46.51", youtube_index, "Listen to SN 46.51"),
    youtube_resource("SN 46.14", youtube_index, "SN 46.14 — Seven Factors of Awakening"),
    local_sutta_resource("MN 44", items_by_id, practice_page, "MN 44 — Shorter Series of Questions and Answers"),
    youtube_resource("MN 44", youtube_index, "Listen to MN 44"),
])}
"""
    practice_page.write_text(page("Practice", practice_body), encoding="utf-8", newline="\n")

    glossary_body = """
<h1>Glossary</h1>
<ul>
  <li><a href="teachings.html#dependent-origination">Dependent origination</a></li>
  <li><a href="dhamma.html">Dhamma</a></li>
  <li><a href="teachings.html#five-aggregates">Five aggregates</a></li>
  <li><a href="practice.html#five-hindrances">Five hindrances</a></li>
  <li><a href="practice.html#five-precepts">Five precepts</a></li>
  <li><a href="practice.html#five-recollections">Five recollections</a></li>
  <li><a href="practice.html#four-foundations-of-mindfulness">Four foundations of mindfulness</a></li>
  <li><a href="practice.html#four-jhanas">Four jhānas</a></li>
  <li><a href="four-noble-truths.html">Four Noble Truths</a></li>
  <li><a href="teachings.html#kamma">Kamma</a></li>
  <li><a href="teachings.html#nibbana">Nibbāna</a></li>
  <li><a href="eightfold-path.html">Noble Eightfold Path</a></li>
  <li><a href="teachings.html#rebirth">Rebirth</a></li>
  <li><a href="path/right-action.html">Right action</a></li>
  <li><a href="path/right-concentration.html">Right concentration</a></li>
  <li><a href="path/right-effort.html">Right effort</a></li>
  <li><a href="path/right-intention.html">Right intention</a></li>
  <li><a href="path/right-livelihood.html">Right livelihood</a></li>
  <li><a href="path/right-mindfulness.html">Right mindfulness</a></li>
  <li><a href="path/right-speech.html">Right speech</a></li>
  <li><a href="path/right-view.html">Right view</a></li>
  <li><a href="practice.html#seven-awakening-factors">Seven awakening factors</a></li>
  <li><a href="teachings.html#ten-fetters">Ten fetters</a></li>
  <li><a href="theravada.html">Theravāda Buddhism</a></li>
  <li><a href="teachings.html#three-characteristics">Three characteristics</a></li>
  <li><a href="tipitaka.html">Tipiṭaka</a></li>
</ul>
"""
    (site_dir / "glossary.html").write_text(page("Glossary", glossary_body), encoding="utf-8", newline="\n")

    truths_page = site_dir / "four-noble-truths.html"
    sn5611_read = local_sutta_resource("SN 56.11", items_by_id, truths_page, "Read SN 56.11 — Setting the Wheel of Dhamma in Motion")
    sn5611_listen = youtube_resource("SN 56.11", youtube_index, "Listen to SN 56.11")
    mn141_listen = youtube_resource("MN 141", youtube_index, "Listen to MN 141 — Exposition on the Truths")
    mn9_read = local_sutta_resource("MN 9", items_by_id, truths_page, "Read MN 9 — Discourse on Right View")
    mn117_listen = youtube_resource("MN 117", youtube_index, "Listen to MN 117 — The Great Forty")
    truths_body = f"""
<h1>The Four Noble Truths</h1>
<ol>
  <li id="dukkha">Clinging to conditioned existence is unsatisfactory.</li>
  <li id="origin">Craving sustains that clinging and dissatisfaction.</li>
  <li id="cessation">Ending craving ends that clinging and dissatisfaction.</li>
  <li id="path">The <a href="eightfold-path.html">Noble Eightfold Path</a> leads to that ending.</li>
</ol>
<p>The first truth is to be understood. The second is to be abandoned. The third is to be realized. The fourth is to be developed.</p>
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
            "<ol>",
            *overview_items,
            "</ol>",
            "<p>The path is one training with eight mutually supporting factors.</p>",
            "<h2>Relevant suttas</h2>",
            resource_list(
                [
                    '<a href="https://suttacentral.net/sn45.8/en/sujato" rel="external">SN 45.8 — Analysis of the Path</a> (external text; Candana audio not currently found)',
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
                    '(external text; Candana audio not currently found)'
                )
        detail_body = "\n".join(
            [
                '<p><a href="../eightfold-path.html">The Noble Eightfold Path</a></p>',
                f'<h1>{html.escape(section["name"])}</h1>',
                f'<p>{html.escape(section["summary"])}</p>',
                str(section["details"]),
                "<h2>Relevant suttas</h2>",
                resource_list(rendered_resources),
            ]
        )
        detail_page.write_text(page(str(section["name"]), detail_body, ".."), encoding="utf-8", newline="\n")

    unique_ids = len({item.canonical_id for item in items})
    tipitaka_body = f"""
<h1>The Pāli Tipiṭaka</h1>
<p>The Theravāda scriptural collection is known as the Pāli Canon or Tipiṭaka, “three baskets”: discipline, discourses, and systematic teachings.</p>
<ol>
  <li><strong>Vinaya Piṭaka:</strong> monastic discipline, procedures, and the life of the early monastic community.</li>
  <li><strong>Sutta Piṭaka:</strong> discourses, dialogues, verses, and instructions attributed to the Buddha and close disciples.</li>
  <li><strong>Abhidhamma Piṭaka:</strong> systematic analysis of mental and material phenomena.</li>
</ol>
<p>This site currently focuses on the Sutta Piṭaka. It contains {len(items)} source pages representing {unique_ids} canonical or source IDs. Vinaya and Abhidhamma texts have not yet been collected here.</p>
<h2>The five Nikāyas of the Sutta Piṭaka</h2>
<ol>
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
            "<p>Read and listen</p>",
            "<h1>Sutta Piṭaka</h1>",
            f"<p>{len(items)} source pages, with Candana Bhikkhu YouTube audio linked wherever the playlist metadata provides a reliable match.</p>",
            "<table>",
            "<tr><th>Collection</th><th>ID</th><th>Title</th><th>TXT</th><th>PDF</th><th>Audio</th></tr>",
            *rows,
            "</table>",
        ]
    )
    (site_dir / "sutta.html").write_text(page("Sutta Piṭaka", sutta_body), encoding="utf-8", newline="\n")

    downloads_body = """
<p>Keep a local copy</p>
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
