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

from youtube_metadata import (
    YouTubeVideo,
    read_youtube_index,
    read_youtube_videos,
    videos_for_canonical_id,
)


COLLECTION_TITLES = {
    "digha-nikaya": "Digha Nikaya",
    "majjhima-nikaya": "Majjhima Nikaya",
    "samyutta-nikaya": "Samyutta Nikaya",
    "anguttara-nikaya": "Anguttara Nikaya",
    "khuddaka-nikaya/dhammapada": "Dhammapada",
    "khuddaka-nikaya/khuddakapatha": "Khuddakapatha",
    "khuddaka-nikaya/udana": "Udana",
    "khuddaka-nikaya/itivuttaka": "Itivuttaka",
    "khuddaka-nikaya/sutta-nipata": "Sutta Nipata",
    "khuddaka-nikaya/theragatha": "Theragatha",
    "khuddaka-nikaya/therigatha": "Therigatha",
    "khuddaka-nikaya/jataka": "Jataka",
    "khuddaka-nikaya/cariyapitaka": "Cariyapitaka",
    "khuddaka-nikaya/milindapanha": "Milindapanha",
}

AUDIO_COLLECTION_TITLES = {
    "anguttara-nikaya": "Aṅguttara Nikāya",
    "dhammapada-chapters": "Dhammapada chapters",
    "dhammapada-verses": "Dhammapada verses",
    "digha-nikaya": "Dīgha Nikāya",
    "majjhima-nikaya": "Majjhima Nikāya",
    "samyutta-nikaya": "Saṁyutta Nikāya",
    "samyutta-nikaya-temporary": "Saṁyutta Nikāya supplemental recordings",
    "sutta-nipata": "Sutta Nipāta",
    "theragatha": "Theragāthā",
    "therigatha": "Therīgāthā",
    "udana-itivuttaka": "Udāna and Itivuttaka",
}


@dataclass
class SourceRow:
    canonical_id: str
    collection_path: str
    source_pdf: Path | None
    source_txt: Path
    label: str
    source_url: str
    page_url: str
    version_slug: str
    version_label: str
    license_name: str
    copy_text: bool


@dataclass
class GeneratedItem:
    canonical_id: str
    title: str
    collection_path: str
    folder: Path
    base_name: str
    html_path: Path
    txt_path: Path
    pdf_path: Path | None
    youtube_videos: list[YouTubeVideo]
    version_label: str
    source_url: str
    license_name: str


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


def natural_key(value: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


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
                    version_slug="",
                    version_label="Candana Bhikkhu / Mind Released",
                    license_name="Rights not yet verified",
                    copy_text=True,
                )
            )
    return rows


def read_suttacentral_ledger(ledger: Path, repo_root: Path) -> list[SourceRow]:
    if not ledger.exists():
        return []
    rows: list[SourceRow] = []
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle, dialect="excel-tab"):
            rows.append(
                SourceRow(
                    canonical_id=record["canonical_id"],
                    collection_path=record["collection_path"],
                    source_pdf=None,
                    source_txt=repo_root / record["txt_path"],
                    label=record["label"],
                    source_url=record["source_url"],
                    page_url=record["source_url"],
                    version_slug="sujato",
                    version_label=record["version_label"],
                    license_name=record["license"],
                    copy_text=False,
                )
            )
    return rows


def html_relative(from_file: Path, target: Path) -> str:
    return Path(os.path.relpath(target, start=from_file.parent)).as_posix()


def site_href(site_prefix: str, path: str) -> str:
    if site_prefix in ("", "."):
        return path
    return f"{site_prefix.rstrip('/')}/{path}"


def page(title: str, body: str, site_prefix: str = ".", show_contact: bool = False) -> str:
    home_href = site_href(site_prefix, "index.html")
    dhamma_href = site_href(site_prefix, "dhamma.html")
    tipitaka_href = site_href(site_prefix, "tipitaka.html")
    contact = (
        '<p>Contact: <a href="mailto:gregcooper@protonmail.com">gregcooper@protonmail.com</a></p>\n'
        if show_contact
        else ""
    )
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
        f'<a href="{html.escape(tipitaka_href)}">Buddhist Texts</a></p>\n'
        f"{body}\n"
        f"{contact}"
        "</body>\n"
        "</html>\n"
    )


def convert_text_to_html(text: str) -> str:
    return f"<pre>{html.escape(text)}</pre>"


def write_translation_html(item: GeneratedItem, txt_text: str, tipitaka_root: Path) -> None:
    sutta_page = item.folder / "index.html"
    txt_link = html_relative(item.html_path, item.txt_path)
    download_links = [f'<a href="{txt_link}">Download TXT</a>']
    if item.pdf_path:
        pdf_link = html_relative(item.html_path, item.pdf_path)
        download_links.append(f'<a href="{pdf_link}">Download PDF</a>')
    source_note = html.escape(item.version_label)
    if item.source_url:
        source_note = f'<a href="{html.escape(item.source_url)}" rel="external">{source_note}</a>'
    if item.license_name and item.license_name not in item.version_label:
        source_note += f"; {html.escape(item.license_name)}"
    body_parts = [
        f'<p><a href="{html_relative(item.html_path, sutta_page)}">{html.escape(item.canonical_id)}</a></p>',
        f"<h1>{html.escape(item.canonical_id)} {html.escape(item.title)}</h1>",
        f"<p>{source_note}</p>",
        f"<p>{' | '.join(download_links)}</p>",
        "<h2>Text</h2>",
        convert_text_to_html(txt_text),
    ]
    body = "\n".join(body_parts)
    site_prefix = html_relative(item.html_path, tipitaka_root / "site")
    item.html_path.write_text(
        page(f"{item.canonical_id} {item.title}", body, site_prefix),
        encoding="utf-8",
        newline="\n",
    )


def group_sutta_items(items: list[GeneratedItem]) -> dict[Path, list[GeneratedItem]]:
    grouped: dict[Path, list[GeneratedItem]] = defaultdict(list)
    for item in items:
        grouped[item.folder].append(item)
    return grouped


def sutta_name(item: GeneratedItem) -> str:
    name = re.sub(rf"\s+{re.escape(item.canonical_id)}\s*$", "", item.title).strip()
    return "" if name == item.canonical_id else name


def write_sutta_pages(items: list[GeneratedItem], tipitaka_root: Path) -> None:
    for folder, versions in group_sutta_items(items).items():
        versions.sort(key=lambda item: item.base_name)
        item = versions[0]
        landing_page = folder / "index.html"
        collection_page = tipitaka_root / "sutta" / item.collection_path / "index.html"
        site_prefix = html_relative(landing_page, tipitaka_root / "site")

        text_links = []
        label_counts: dict[str, int] = defaultdict(int)
        for index, version in enumerate(versions, start=1):
            label_counts[version.version_label] += 1
            label = version.version_label
            if label_counts[version.version_label] > 1:
                label = f"{label} {label_counts[version.version_label]}"
            text_links.append(
                f'<li><a href="{html_relative(landing_page, version.html_path)}">{html.escape(label)}</a></li>'
            )

        videos: list[YouTubeVideo] = []
        seen_video_ids: set[str] = set()
        for version in versions:
            for video in version.youtube_videos:
                if video.video_id not in seen_video_ids:
                    seen_video_ids.add(video.video_id)
                    videos.append(video)
        audio_parts = ["<h2>Audio</h2>"]
        if videos:
            audio_parts.append("<ul>")
            for video in videos:
                duration = f" ({html.escape(video.duration)})" if video.duration else ""
                audio_parts.append(
                    f'<li><a href="{html.escape(video.url)}" rel="external">{html.escape(video.title)}</a>'
                    f"{duration}</li>"
                )
            audio_parts.append("</ul>")
        else:
            audio_parts.append("<p>No matching audio is currently indexed.</p>")

        name = sutta_name(item)
        heading = f"{item.canonical_id} — {name}" if name else item.canonical_id
        landing_body = "\n".join(
            [
                f'<p><a href="{html_relative(landing_page, collection_page)}">{html.escape(COLLECTION_TITLES.get(item.collection_path, item.collection_path))}</a></p>',
                f"<h1>{html.escape(heading)}</h1>",
                "<h2>Texts</h2>",
                "<ul>",
                *text_links,
                "</ul>",
                *audio_parts,
            ]
        )
        landing_page.write_text(
            page(heading, landing_body, site_prefix),
            encoding="utf-8",
            newline="\n",
        )


def copy_item(
    row: SourceRow,
    sutta_root: Path,
    tipitaka_root: Path,
    ordinal: int,
    youtube_index: dict[str, list[YouTubeVideo]],
) -> GeneratedItem:
    folder_name = canonical_slug(row.canonical_id)
    base_name = f"{folder_name}-{row.version_slug}" if row.version_slug else folder_name
    folder = sutta_root / row.collection_path / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    existing_pdf = folder / f"{base_name}.pdf"
    if row.source_pdf and existing_pdf.exists() and existing_pdf.read_bytes() != row.source_pdf.read_bytes():
        base_name = f"{folder_name}-{ordinal:02d}"

    pdf_path = folder / f"{base_name}.pdf" if row.source_pdf else None
    txt_path = folder / f"{base_name}.txt" if row.copy_text else row.source_txt
    html_path = folder / f"{base_name}.html"
    if row.source_pdf and pdf_path and row.source_pdf.resolve() != pdf_path.resolve():
        shutil.copy2(row.source_pdf, pdf_path)
    if row.copy_text and row.source_txt.resolve() != txt_path.resolve():
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
        version_label=row.version_label,
        source_url=row.source_url,
        license_name=row.license_name,
    )
    write_translation_html(item, text, tipitaka_root)
    return item


def write_collection_indexes(items: list[GeneratedItem], tipitaka_root: Path) -> None:
    by_collection: dict[str, dict[Path, list[GeneratedItem]]] = defaultdict(lambda: defaultdict(list))
    for item in items:
        by_collection[item.collection_path][item.folder].append(item)

    for collection, collection_suttas in by_collection.items():
        collection_dir = tipitaka_root / "sutta" / collection
        if collection.startswith("khuddaka-nikaya/"):
            parent_page = tipitaka_root / "sutta" / "khuddaka-nikaya" / "index.html"
            parent_title = "Khuddaka Nikaya"
        else:
            parent_page = tipitaka_root / "site" / "sutta.html"
            parent_title = "Sutta Pitaka"
        rows = []
        for versions in sorted(collection_suttas.values(), key=lambda group: natural_key(group[0].canonical_id)):
            versions.sort(key=lambda item: item.base_name)
            item = versions[0]
            rows.append(
                "<tr>"
                f"<td>{html.escape(item.canonical_id)}</td>"
                f"<td><a href=\"{html_relative(collection_dir / 'index.html', item.folder / 'index.html')}\">{html.escape(item.title)}</a></td>"
                f"<td>{len(versions)}</td>"
                "</tr>"
            )
        archive_path = tipitaka_root / "downloads" / f"{slug(collection)}.zip"
        body = "\n".join(
            [
                f'<p><a href="{html_relative(collection_dir / "index.html", parent_page)}">{parent_title}</a></p>',
                f"<h1>{html.escape(COLLECTION_TITLES.get(collection, collection))}</h1>",
                f'<p><a href="{html_relative(collection_dir / "index.html", archive_path)}">Download this collection</a></p>',
                "<table>",
                "<tr><th>ID</th><th>Title</th><th>Texts</th></tr>",
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

    khuddaka_page = tipitaka_root / "sutta" / "khuddaka-nikaya" / "index.html"
    khuddaka_children = []
    for collection in sorted(
        (name for name in by_collection if name.startswith("khuddaka-nikaya/")),
        key=lambda value: COLLECTION_TITLES.get(value, value),
    ):
        child_page = tipitaka_root / "sutta" / collection / "index.html"
        khuddaka_children.append(
            f'<li><a href="{html_relative(khuddaka_page, child_page)}">'
            f'{html.escape(COLLECTION_TITLES.get(collection, collection))}</a></li>'
        )
    khuddaka_body = "\n".join(
        [
            f'<p><a href="{html_relative(khuddaka_page, tipitaka_root / "site" / "sutta.html")}">Sutta Pitaka</a></p>',
            "<h1>Khuddaka Nikaya</h1>",
            "<ul>",
            *khuddaka_children,
            "</ul>",
        ]
    )
    khuddaka_page.write_text(
        page("Khuddaka Nikaya", khuddaka_body, html_relative(khuddaka_page, tipitaka_root / "site")),
        encoding="utf-8",
        newline="\n",
    )


def sutta_resource(
    canonical_id: str,
    items_by_id: dict[str, list[GeneratedItem]],
    youtube_index: dict[str, list[YouTubeVideo]],
    from_page: Path,
    site_dir: Path,
    label: str,
) -> str:
    matches = items_by_id.get(canonical_id, [])
    if matches:
        item = matches[0]
        href = html_relative(from_page, item.folder / "index.html")
        return (
            f'<a href="{html.escape(href)}" title="{html.escape(item.title)}">'
            f'{html.escape(canonical_id)}</a>'
        )

    videos = videos_for_canonical_id(canonical_id, youtube_index)
    if videos:
        href = html_relative(from_page, site_dir / "sutta-audio.html")
        return (
            f'<a href="{html.escape(href)}#video-{html.escape(videos[0].video_id)}" '
            f'title="{html.escape(videos[0].title)}">{html.escape(canonical_id)}</a>'
        )

    href = html_relative(from_page, site_dir / "tipitaka.html")
    return f'<a href="{html.escape(href)}" title="{html.escape(label)}">{html.escape(canonical_id)}</a>'


def render_sutta_resources(
    resources: list[tuple[str, str, str]],
    items_by_id: dict[str, list[GeneratedItem]],
    youtube_index: dict[str, list[YouTubeVideo]],
    from_page: Path,
    site_dir: Path,
) -> list[str]:
    rendered: list[str] = []
    seen: set[str] = set()
    for _kind, canonical_id, label in resources:
        if canonical_id in seen:
            continue
        seen.add(canonical_id)
        rendered.append(
            sutta_resource(
                canonical_id,
                items_by_id,
                youtube_index,
                from_page,
                site_dir,
                label,
            )
        )
    return rendered


def resource_list(resources: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{resource}</li>" for resource in resources) + "</ul>"


def write_site(
    items: list[GeneratedItem],
    tipitaka_root: Path,
    youtube_index: dict[str, list[YouTubeVideo]],
    youtube_videos: list[YouTubeVideo],
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
<p><a href="tipitaka.html">Buddhist Texts</a> introduces the Pāli Tipiṭaka, the Theravāda tradition’s primary textual record of the Buddha’s <a href="dhamma.html">Dhamma</a>.</p>
"""
    (site_dir / "index.html").write_text(
        page("Home", index_body, show_contact=True),
        encoding="utf-8",
        newline="\n",
    )

    theravada_body = """
<h1>Theravāda Buddhism</h1>
<p>Theravāda is the oldest surviving Buddhist tradition.</p>
<p>Its primary scriptural authority is the Pāli Tipiṭaka, introduced under <a href="tipitaka.html">Buddhist Texts</a>. The later Mahāyāna sūtras are not part of its canon.</p>
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
+-- Core teachings
|   +-- <a href="four-noble-truths.html">Four Noble Truths</a>
|   +-- <a href="eightfold-path.html">Noble Eightfold Path</a>
|
+-- <a href="teachings.html">Teachings</a>
|
+-- <a href="practice.html">Practice</a>
|
+-- <a href="tipitaka.html">Buddhist Texts</a>
|
+-- <a href="glossary.html">Glossary</a></pre>
<h2>Relevant suttas</h2>
{resource_list([
    sutta_resource("SN 56.11", items_by_id, youtube_index, dhamma_page, site_dir, "SN 56.11 — Setting the Wheel of Dhamma in Motion"),
    sutta_resource("MN 9", items_by_id, youtube_index, dhamma_page, site_dir, "MN 9 — Right View"),
])}
"""
    dhamma_page.write_text(
        page("Dhamma", dhamma_body),
        encoding="utf-8",
        newline="\n",
    )

    teaching_sections = [
        {
            "slug": "three-characteristics",
            "name": "Three characteristics",
            "summary": "Conditioned things are impermanent and unsatisfactory; all phenomena are not-self.",
            "details": "<ul><li><strong>Impermanence:</strong> conditioned things arise, change, and cease.</li><li><strong>Unsatisfactoriness:</strong> what changes cannot provide lasting security.</li><li><strong>Not-self:</strong> no phenomenon can rightly be taken as a permanent self or possession.</li></ul><p>Seeing these characteristics directly leads to disenchantment, dispassion, and release.</p>",
            "resources": [("local", "SN 22.59", "SN 22.59 — The Characteristic of Not-Self"), ("youtube", "SN 22.59", "Listen to SN 22.59")],
        },
        {
            "slug": "five-aggregates",
            "name": "Five aggregates",
            "summary": "Form, feeling, perception, mental formations, and consciousness are the five bases of clinging.",
            "details": "<ol><li>Form: the material body and material phenomena.</li><li>Feeling: pleasant, painful, or neutral experience.</li><li>Perception: recognition and identification.</li><li>Mental formations: intentions and other constructed mental activities.</li><li>Consciousness: awareness through the six senses.</li></ol><p>None of the five is permanent, satisfactory, or self.</p>",
            "resources": [("local", "SN 22.59", "SN 22.59 — The Characteristic of Not-Self"), ("youtube", "SN 22.59", "Listen to SN 22.59"), ("local", "SN 22.95", "SN 22.95 — A Lump of Foam"), ("youtube", "SN 22.95", "Listen to SN 22.95")],
        },
        {
            "slug": "dependent-origination",
            "name": "Dependent origination",
            "summary": "Phenomena arise and cease according to conditions; the twelve-link sequence explains the arising and cessation of suffering.",
            "details": "<p>Ignorance conditions formations; formations condition consciousness; then name-and-form, the six sense bases, contact, feeling, craving, clinging, becoming, birth, and aging and death.</p><p>When ignorance and craving cease, the conditions that sustain suffering also cease.</p>",
            "resources": [("local", "SN 12.2", "SN 12.2 — Analysis of Dependent Origination"), ("youtube", "SN 12.2", "SN 12.2 within the SN 12.1–10 reading"), ("local", "SN 12.23", "SN 12.23 — Proximate Conditions"), ("youtube", "SN 12.23", "SN 12.23 within the SN 12.21–30 reading")],
        },
        {
            "slug": "kamma",
            "name": "Kamma",
            "summary": "Intentional actions of body, speech, and mind have consequences according to their ethical quality.",
            "details": "<p>Kamma means intention expressed through body, speech, or mind. Skillful intentions tend toward well-being; unskillful intentions tend toward suffering.</p><p>Kamma is not fate. Present choices remain part of the causal field.</p>",
            "resources": [("local", "AN 6.63", "AN 6.63 — Penetrative"), ("youtube", "AN 6.63", "AN 6.63 within the AN 6.55–64 reading"), ("local", "MN 135", "MN 135 — The Shorter Exposition of Kamma"), ("youtube", "MN 135", "Listen to MN 135")],
        },
        {
            "slug": "rebirth",
            "name": "Rebirth",
            "summary": "After death, continued existence arises according to conditions without a permanent self passing from one life to another.",
            "details": "<p>Craving, clinging, and kamma condition renewed existence. The continuity is causal, not the transmigration of an unchanging soul.</p><p>Ending craving ends the conditions for further birth.</p>",
            "resources": [("local", "MN 135", "MN 135 — The Shorter Exposition of Kamma"), ("youtube", "MN 135", "Listen to MN 135"), ("local", "MN 130", "MN 130 — The Divine Messengers"), ("youtube", "MN 130", "Listen to MN 130")],
        },
        {
            "slug": "nibbana",
            "name": "Nibbāna",
            "summary": "Nibbāna is the ending of greed, hatred, and delusion: release from suffering and rebirth.",
            "details": "<p>Nibbāna is unconditioned and is realized through the cessation of craving. It can be directly known in this life.</p><p>With the death of an arahant, no condition remains for renewed existence.</p>",
            "resources": [("youtube", "Ud 8.3", "Ud 8.3 — Nibbāna"), ("youtube", "Iti 44", "Itivuttaka 44 — The Nibbāna Element"), ("local", "DN 16", "DN 16 — The Buddha’s Final Days"), ("youtube", "DN 16", "Listen to DN 16")],
        },
        {
            "slug": "ten-fetters",
            "name": "Ten fetters",
            "summary": "Ten mental bonds bind beings to repeated existence.",
            "details": "<ol><li>Identity view.</li><li>Doubt.</li><li>Attachment to rites and observances.</li><li>Sensual desire.</li><li>Ill will.</li><li>Desire for form existence.</li><li>Desire for formless existence.</li><li>Conceit.</li><li>Restlessness.</li><li>Ignorance.</li></ol><p>Stream-entry breaks the first three. Non-returning breaks the first five. Arahantship breaks all ten.</p>",
            "resources": [("youtube", "AN 10.13", "AN 10.13 within the AN 10.11–20 reading — The Ten Fetters"), ("youtube", "Dhp 370", "Dhammapada 370 — Giving Up the Fetters")],
        },
    ]

    practice_sections = [
        {
            "slug": "five-precepts",
            "name": "Five precepts",
            "summary": "Abstain from killing, stealing, sexual misconduct, false speech, and intoxicants that cause heedlessness.",
            "details": "<ol><li>Do not intentionally kill living beings.</li><li>Do not take what is not given.</li><li>Do not engage in sexual misconduct.</li><li>Do not speak falsely.</li><li>Do not use intoxicants that cause heedlessness.</li></ol><p>The precepts are voluntary training rules that establish harmlessness and restraint.</p>",
            "resources": [("youtube", "Dhp 246", "Dhammapada 246–247 — The Five Precepts"), ("youtube", "AN 8.39", "AN 8.39 within the AN 8.31–40 reading — The Five Precepts")],
        },
        {
            "slug": "five-recollections",
            "name": "Five recollections",
            "summary": "Frequently recollect aging, illness, death, separation from what is dear, and ownership of one’s kamma.",
            "details": "<ol><li>I am subject to aging.</li><li>I am subject to illness.</li><li>I am subject to death.</li><li>I must be separated from everyone and everything dear to me.</li><li>I am the owner and heir of my kamma.</li></ol><p>These recollections counter complacency and clarify what deserves attention.</p>",
            "resources": [("youtube", "AN 5.57", "AN 5.57 within the AN 5.51–60 reading — Five Recollections"), ("local", "MN 130", "MN 130 — The Divine Messengers"), ("youtube", "MN 130", "Listen to MN 130")],
        },
        {
            "slug": "four-foundations-of-mindfulness",
            "name": "Four foundations of mindfulness",
            "summary": "Observe body, feeling, mind, and phenomena clearly and without clinging.",
            "details": "<ol><li>Body as body.</li><li>Feeling as feeling.</li><li>Mind as mind.</li><li>Phenomena as phenomena.</li></ol><p>Practice is ardent, clearly comprehending, and mindful, having put away craving and distress regarding the world.</p>",
            "resources": [("local", "MN 10", "MN 10 — Foundations of Mindfulness"), ("youtube", "MN 10", "Listen to MN 10"), ("local", "DN 22", "DN 22 — Great Discourse on Mindfulness"), ("youtube", "DN 22", "Listen to DN 22")],
        },
        {
            "slug": "five-hindrances",
            "name": "Five hindrances",
            "summary": "Sensual desire, ill will, sloth and torpor, restlessness and remorse, and doubt obstruct clarity and concentration.",
            "details": "<ol><li>Sensual desire.</li><li>Ill will.</li><li>Sloth and torpor.</li><li>Restlessness and remorse.</li><li>Doubt.</li></ol><p>Practice recognizes whether each hindrance is present, how it arises, how it is abandoned, and how its return is prevented.</p>",
            "resources": [("local", "SN 46.51", "SN 46.51 — Nourishment for the Hindrances"), ("youtube", "SN 46.51", "Listen to SN 46.51")],
        },
        {
            "slug": "seven-awakening-factors",
            "name": "Seven awakening factors",
            "summary": "Mindfulness, investigation, energy, rapture, tranquility, concentration, and equanimity support awakening.",
            "details": "<ol><li>Mindfulness.</li><li>Investigation of phenomena.</li><li>Energy.</li><li>Rapture.</li><li>Tranquility.</li><li>Concentration.</li><li>Equanimity.</li></ol><p>They are developed in dependence on seclusion, dispassion, and cessation, culminating in relinquishment.</p>",
            "resources": [("local", "SN 46.14", "SN 46.14 — Seven Factors of Awakening"), ("youtube", "SN 46.14", "Listen to SN 46.14"), ("local", "SN 46.54", "SN 46.54 — Awakening Factors with Loving-Kindness"), ("youtube", "SN 46.54", "Listen to SN 46.54")],
        },
        {
            "slug": "four-jhanas",
            "name": "Four jhānas",
            "summary": "Four stages of meditative unification progressively refine rapture, pleasure, equanimity, and mindfulness.",
            "details": "<ol><li>Seclusion, applied and sustained thought, rapture, and pleasure.</li><li>Applied and sustained thought subside; unification, rapture, and pleasure remain.</li><li>Rapture fades; equanimity, mindfulness, and bodily pleasure remain.</li><li>Pleasure and pain are abandoned; mindfulness is purified by equanimity.</li></ol>",
            "resources": [("local", "AN 5.28", "AN 5.28 — Five-Factored Concentration"), ("youtube", "AN 5.28", "AN 5.28 within the AN 5.21–30 reading"), ("local", "DN 2", "DN 2 — Fruits of the Contemplative Life"), ("youtube", "DN 2", "Listen to DN 2")],
        },
    ]

    def write_reference_pages(group_name: str, sections: list[dict[str, object]]) -> None:
        overview_file = site_dir / f"{group_name.lower()}.html"
        detail_dir = site_dir / group_name.lower()
        detail_dir.mkdir(parents=True, exist_ok=True)
        overview_parts = [f"<h1>{html.escape(group_name)}</h1>"]
        for section in sections:
            slug = str(section["slug"])
            name = str(section["name"])
            summary = str(section["summary"])
            overview_parts.extend(
                [
                    f'<h2><a href="{group_name.lower()}/{slug}.html">{html.escape(name)}</a></h2>',
                    f"<p>{html.escape(summary)}</p>",
                ]
            )
            detail_file = detail_dir / f"{slug}.html"
            rendered_resources = render_sutta_resources(
                section["resources"],
                items_by_id,
                youtube_index,
                detail_file,
                site_dir,
            )
            detail_body = "\n".join(
                [
                    f'<p><a href="../{group_name.lower()}.html">{html.escape(group_name)}</a></p>',
                    f"<h1>{html.escape(name)}</h1>",
                    f"<p>{html.escape(summary)}</p>",
                    str(section["details"]),
                    "<h2>Relevant suttas</h2>",
                    resource_list(rendered_resources),
                ]
            )
            detail_file.write_text(page(name, detail_body, ".."), encoding="utf-8", newline="\n")
        overview_file.write_text(
            page(group_name, "\n".join(overview_parts)),
            encoding="utf-8",
            newline="\n",
        )

    write_reference_pages("Teachings", teaching_sections)
    write_reference_pages("Practice", practice_sections)

    glossary_body = """
<h1>Glossary</h1>
<ul>
  <li><a href="teachings/dependent-origination.html">Dependent origination</a></li>
  <li><a href="dhamma.html">Dhamma</a></li>
  <li><a href="teachings/five-aggregates.html">Five aggregates</a></li>
  <li><a href="practice/five-hindrances.html">Five hindrances</a></li>
  <li><a href="practice/five-precepts.html">Five precepts</a></li>
  <li><a href="practice/five-recollections.html">Five recollections</a></li>
  <li><a href="practice/four-foundations-of-mindfulness.html">Four foundations of mindfulness</a></li>
  <li><a href="practice/four-jhanas.html">Four jhānas</a></li>
  <li><a href="four-noble-truths.html">Four Noble Truths</a></li>
  <li><a href="teachings/kamma.html">Kamma</a></li>
  <li><a href="teachings/nibbana.html">Nibbāna</a></li>
  <li><a href="eightfold-path.html">Noble Eightfold Path</a></li>
  <li><a href="teachings/rebirth.html">Rebirth</a></li>
  <li><a href="path/right-action.html">Right action</a></li>
  <li><a href="path/right-concentration.html">Right concentration</a></li>
  <li><a href="path/right-effort.html">Right effort</a></li>
  <li><a href="path/right-intention.html">Right intention</a></li>
  <li><a href="path/right-livelihood.html">Right livelihood</a></li>
  <li><a href="path/right-mindfulness.html">Right mindfulness</a></li>
  <li><a href="path/right-speech.html">Right speech</a></li>
  <li><a href="path/right-view.html">Right view</a></li>
  <li><a href="practice/seven-awakening-factors.html">Seven awakening factors</a></li>
  <li><a href="teachings/ten-fetters.html">Ten fetters</a></li>
  <li><a href="theravada.html">Theravāda Buddhism</a></li>
  <li><a href="teachings/three-characteristics.html">Three characteristics</a></li>
  <li><a href="tipitaka.html">Buddhist Texts</a></li>
</ul>
"""
    (site_dir / "glossary.html").write_text(page("Glossary", glossary_body), encoding="utf-8", newline="\n")

    truths_page = site_dir / "four-noble-truths.html"
    truth_resources = render_sutta_resources(
        [
            ("sutta", "SN 56.11", "SN 56.11 — Setting the Wheel of Dhamma in Motion"),
            ("sutta", "MN 141", "MN 141 — Exposition on the Truths"),
            ("sutta", "MN 9", "MN 9 — Discourse on Right View"),
            ("sutta", "MN 117", "MN 117 — The Great Forty"),
        ],
        items_by_id,
        youtube_index,
        truths_page,
        site_dir,
    )
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
{resource_list(truth_resources)}
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
            "resources": [("youtube", "MN 19", "MN 19 — Two Kinds of Thoughts"), ("youtube", "MN 117", "MN 117 — The Great Forty"), ("external", "SN 45.8", "SN 45.8 — Analysis of the Path")],
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
            "resources": [("youtube", "MN 41", "MN 41 — Brahmins of Sālā"), ("youtube", "MN 61", "MN 61 — Advice to Rāhula"), ("external", "SN 45.8", "SN 45.8 — Analysis of the Path")],
        },
        {
            "slug": "right-livelihood",
            "name": "Right livelihood",
            "summary": "Earn without causing harm.",
            "details": "<p>Right livelihood brings one’s means of support into accord with right speech and right action.</p><p>For lay followers, the texts specifically reject trade in weapons, living beings, meat, intoxicants, and poison.</p>",
            "resources": [("youtube", "AN 5.177", "AN 5.177 within the AN 5.171–180 reading"), ("youtube", "MN 117", "MN 117 — The Great Forty"), ("external", "SN 45.8", "SN 45.8 — Analysis of the Path")],
        },
        {
            "slug": "right-effort",
            "name": "Right effort",
            "summary": "Prevent and abandon unskillful states; develop skillful ones.",
            "details": "<p>Right effort has four tasks: prevent unarisen unskillful states, abandon arisen unskillful states, develop unarisen skillful states, and sustain arisen skillful states.</p><p>It is purposeful cultivation, guided by right view.</p>",
            "resources": [("youtube", "MN 117", "MN 117 — The Great Forty"), ("external", "SN 45.8", "SN 45.8 — Analysis of the Path")],
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
                render_sutta_resources(
                    [
                        ("sutta", "SN 45.8", "SN 45.8 — Analysis of the Path"),
                        ("sutta", "MN 117", "MN 117 — The Great Forty"),
                        ("sutta", "SN 56.11", "SN 56.11 — Setting the Wheel of Dhamma in Motion"),
                    ],
                    items_by_id,
                    youtube_index,
                    path_page,
                    site_dir,
                )
            ),
        ]
    )
    path_page.write_text(page("The Noble Eightfold Path", path_body), encoding="utf-8", newline="\n")

    for section in path_sections:
        detail_page = path_dir / f'{section["slug"]}.html'
        rendered_resources = render_sutta_resources(
            section["resources"],
            items_by_id,
            youtube_index,
            detail_page,
            site_dir,
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
<h1>Buddhist Texts</h1>
<p>The Theravāda tradition preserves its primary texts in the Pāli Tipiṭaka, or “three baskets”: discipline, discourses, and systematic teachings.</p>
<h2>Pāli Tipiṭaka</h2>
<pre>Tipiṭaka
|
+-- Vinaya Piṭaka (5 books)
|   +-- Sutta Vibhaṅga
|   |   +-- Mahā Vibhaṅga
|   |   +-- Bhikkhunī Vibhaṅga
|   +-- Khandhaka
|   |   +-- Mahāvagga
|   |   +-- Cullavagga
|   +-- Parivāra
|
+-- <a href="sutta.html">Sutta Piṭaka</a> (5 collections)
|   +-- <a href="../sutta/digha-nikaya/index.html">Dīgha Nikāya</a>
|   +-- <a href="../sutta/majjhima-nikaya/index.html">Majjhima Nikāya</a>
|   +-- <a href="../sutta/samyutta-nikaya/index.html">Saṁyutta Nikāya</a>
|   +-- <a href="../sutta/anguttara-nikaya/index.html">Aṅguttara Nikāya</a>
|   +-- <a href="../sutta/khuddaka-nikaya/index.html">Khuddaka Nikāya</a> (15 books)
|       +-- <a href="../sutta/khuddaka-nikaya/khuddakapatha/index.html">Khuddakapāṭha</a>
|       +-- <a href="../sutta/khuddaka-nikaya/dhammapada/index.html">Dhammapada</a>
|       +-- <a href="../sutta/khuddaka-nikaya/udana/index.html">Udāna</a>
|       +-- <a href="../sutta/khuddaka-nikaya/itivuttaka/index.html">Itivuttaka</a>
|       +-- <a href="../sutta/khuddaka-nikaya/sutta-nipata/index.html">Suttanipāta</a>
|       +-- Vimānavatthu
|       +-- Petavatthu
|       +-- <a href="../sutta/khuddaka-nikaya/theragatha/index.html">Theragāthā</a>
|       +-- <a href="../sutta/khuddaka-nikaya/therigatha/index.html">Therīgāthā</a>
|       +-- <a href="../sutta/khuddaka-nikaya/jataka/index.html">Jātaka</a>
|       +-- Niddesa
|       +-- Paṭisambhidāmagga
|       +-- Apadāna
|       +-- Buddhavaṃsa
|       +-- <a href="../sutta/khuddaka-nikaya/cariyapitaka/index.html">Cariyāpiṭaka</a>
|
+-- Abhidhamma Piṭaka (7 books)
    +-- Dhammasaṅgaṇī
    +-- Vibhaṅga
    +-- Dhātukathā
    +-- Puggalapaññatti
    +-- Kathāvatthu
    +-- Yamaka
    +-- Paṭṭhāna</pre>
<p>This site currently focuses on the Sutta Piṭaka. It contains {len(items)} source pages representing {unique_ids} canonical or source IDs, including the CC0 English translations available from Bhikkhu Sujato. Vinaya and Abhidhamma texts have not yet been collected here.</p>
<h2>Available here</h2>
<p><a href="sutta-texts.html">Texts</a> | <a href="sutta-audio.html">Audio and video</a> | <a href="downloads.html">Downloads</a></p>
"""
    (site_dir / "tipitaka.html").write_text(
        page("Buddhist Texts", tipitaka_body),
        encoding="utf-8",
        newline="\n",
    )

    sutta_body = f"""
<p><a href="tipitaka.html">Buddhist Texts</a></p>
<h1>Sutta Piṭaka</h1>
<h2>Collections</h2>
<ul>
  <li><a href="../sutta/digha-nikaya/index.html">Dīgha Nikāya</a></li>
  <li><a href="../sutta/majjhima-nikaya/index.html">Majjhima Nikāya</a></li>
  <li><a href="../sutta/samyutta-nikaya/index.html">Saṁyutta Nikāya</a></li>
  <li><a href="../sutta/anguttara-nikaya/index.html">Aṅguttara Nikāya</a></li>
  <li><a href="../sutta/khuddaka-nikaya/index.html">Khuddaka Nikāya</a></li>
</ul>
<h2>Library</h2>
<ul>
  <li><a href="sutta-texts.html">Texts</a>: {len(items)} available source pages, grouped by collection.</li>
  <li><a href="sutta-audio.html">Audio</a>: {len(youtube_videos)} Candana Bhikkhu recordings, grouped by collection.</li>
  <li><a href="downloads.html">Downloads</a>: local TXT, PDF, HTML, and complete archives.</li>
</ul>
"""
    (site_dir / "sutta.html").write_text(page("Sutta Piṭaka", sutta_body), encoding="utf-8", newline="\n")

    text_page = site_dir / "sutta-texts.html"
    text_parts = [
        '<p><a href="sutta.html">Sutta Pitaka</a></p>',
        "<h1>Sutta texts</h1>",
        f"<p>{len(items)} available texts for {unique_ids} suttas, grouped by collection.</p>",
    ]
    text_items: dict[str, dict[Path, list[GeneratedItem]]] = defaultdict(lambda: defaultdict(list))
    for item in items:
        text_items[item.collection_path][item.folder].append(item)
    for collection in sorted(text_items, key=lambda value: COLLECTION_TITLES.get(value, value)):
        text_parts.extend(
            [
                f'<h2 id="{slug(collection)}">{html.escape(COLLECTION_TITLES.get(collection, collection))}</h2>',
                "<table>",
                "<tr><th>ID</th><th>Title</th><th>Texts</th><th>Audio</th></tr>",
            ]
        )
        for versions in sorted(text_items[collection].values(), key=lambda group: natural_key(group[0].canonical_id)):
            versions.sort(key=lambda item: item.base_name)
            item = versions[0]
            audio = "yes" if any(version.youtube_videos for version in versions) else "—"
            text_parts.append(
                "<tr>"
                f"<td>{html.escape(item.canonical_id)}</td>"
                f'<td><a href="{html_relative(text_page, item.folder / "index.html")}">{html.escape(item.title)}</a></td>'
                f"<td>{len(versions)}</td>"
                f"<td>{audio}</td>"
                "</tr>"
            )
        text_parts.append("</table>")
    text_page.write_text(page("Sutta texts", "\n".join(text_parts)), encoding="utf-8", newline="\n")

    audio_page = site_dir / "sutta-audio.html"
    audio_parts = [
        '<p><a href="sutta.html">Sutta Pitaka</a></p>',
        "<h1>Candana Bhikkhu audio</h1>",
        f"<p>{len(youtube_videos)} recordings from the committed playlist index.</p>",
    ]
    audio_items: dict[str, list[YouTubeVideo]] = defaultdict(list)
    for video in youtube_videos:
        audio_items[video.collection].append(video)
    for collection in sorted(audio_items, key=lambda value: AUDIO_COLLECTION_TITLES.get(value, value)):
        collection_videos = audio_items[collection]
        audio_parts.append(
            f'<h2 id="{slug(collection)}">{html.escape(AUDIO_COLLECTION_TITLES.get(collection, collection))}</h2>'
        )
        playlist_id = collection_videos[0].playlist_id
        if playlist_id:
            playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
            audio_parts.append(f'<p><a href="{html.escape(playlist_url)}" rel="external">Open playlist on YouTube</a></p>')
        audio_parts.append("<ol>")
        for video in collection_videos:
            duration = f" ({html.escape(video.duration)})" if video.duration else ""
            audio_parts.append(
                f'<li id="video-{html.escape(video.video_id)}">'
                f'<a href="{html.escape(video.url)}" rel="external">{html.escape(video.title)}</a>'
                f"{duration}</li>"
            )
        audio_parts.append("</ol>")
    audio_page.write_text(page("Candana Bhikkhu audio", "\n".join(audio_parts)), encoding="utf-8", newline="\n")

    collection_downloads = []
    for collection in sorted({item.collection_path for item in items}, key=lambda value: COLLECTION_TITLES.get(value, value)):
        collection_downloads.append(
            f'<li><a href="../downloads/{slug(collection)}.zip">{html.escape(COLLECTION_TITLES.get(collection, collection))}</a></li>'
        )
    downloads_body = "\n".join(
        [
            '<p><a href="sutta.html">Sutta Pitaka</a></p>',
            "<h1>Downloads</h1>",
            "<p>These archives contain the material currently available here; they do not yet constitute the complete Pāli Canon.</p>",
            "<h2>All available material</h2>",
            "<ul>",
            '<li><a href="../downloads/tipitaka-all.zip">All formats</a></li>',
            '<li><a href="../downloads/tipitaka-txt.zip">TXT</a></li>',
            '<li><a href="../downloads/tipitaka-pdf.zip">PDF</a></li>',
            '<li><a href="../downloads/tipitaka-html.zip">HTML</a></li>',
            "</ul>",
            "<h2>Individual collections</h2>",
            "<ul>",
            *collection_downloads,
            "</ul>",
        ]
    )
    (site_dir / "downloads.html").write_text(page("Downloads", downloads_body), encoding="utf-8", newline="\n")


def write_zips(tipitaka_root: Path, items: list[GeneratedItem]) -> None:
    tipitaka_root = tipitaka_root.resolve()
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
            for root in [sutta, tipitaka_root / "site", tipitaka_root / "translations"]:
                if not root.exists():
                    continue
                for path in root.rglob("*"):
                    if "__" in path.name:
                        continue
                    if path.is_file() and path.suffix.lower() in extensions:
                        archive.write(path, path.relative_to(tipitaka_root))

    for collection in sorted({item.collection_path for item in items}):
        collection_root = sutta / collection
        archive_path = downloads / f"{slug(collection)}.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archived: set[Path] = set()
            for path in collection_root.rglob("*"):
                if path.is_file() and "__" not in path.name:
                    archive.write(path, path.relative_to(tipitaka_root))
                    archived.add(path.resolve())
            for item in (item for item in items if item.collection_path == collection):
                for path in (item.txt_path, item.pdf_path):
                    if path and path.resolve() not in archived:
                        archive.write(path, path.relative_to(tipitaka_root))
                        archived.add(path.resolve())


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tipitaka-root", default=Path("theravada/tipitaka"), type=Path)
    parser.add_argument(
        "--ledger",
        default=Path("theravada/tipitaka/sutta/candana-bhikkhu-text-ledger.tsv"),
        type=Path,
    )
    parser.add_argument(
        "--suttacentral-ledger",
        default=Path("theravada/tipitaka/sutta/suttacentral-sujato-text-ledger.tsv"),
        type=Path,
    )
    parser.add_argument(
        "--youtube-manifest-dir",
        default=Path("metadata/youtube-playlists/manifests"),
        type=Path,
    )
    parser.add_argument("--skip-zips", action="store_true", help="Skip download archives during quick previews")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    sutta_root = args.tipitaka_root / "sutta"
    rows = read_ledger(args.ledger, sutta_root)
    repo_root = args.tipitaka_root.resolve().parents[1]
    rows.extend(read_suttacentral_ledger(args.suttacentral_ledger, repo_root))
    youtube_index = read_youtube_index(args.youtube_manifest_dir)
    youtube_videos = read_youtube_videos(args.youtube_manifest_dir)
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
    write_sutta_pages(generated, args.tipitaka_root)
    write_collection_indexes(generated, args.tipitaka_root)
    write_site(generated, args.tipitaka_root, youtube_index, youtube_videos)
    if not args.skip_zips:
        write_zips(args.tipitaka_root, generated)
    print(f"Generated {len(generated)} source pages")
    print(f"Site root: {args.tipitaka_root / 'site/index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
