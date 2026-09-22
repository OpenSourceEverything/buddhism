#!/usr/bin/env python3
"""Import pinned CC0 SuttaCentral translations as readable plain text."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK = REPO_ROOT / "metadata/source-manifests/suttacentral-bilara.json"
DEFAULT_OUTPUT = REPO_ROOT / "theravada/tipitaka/translations/en/suttacentral/sujato/sutta"
DEFAULT_LEDGER = REPO_ROOT / "theravada/tipitaka/sutta/suttacentral-sujato-text-ledger.tsv"

COLLECTION_PATHS = {
    "dn": "digha-nikaya",
    "mn": "majjhima-nikaya",
    "sn": "samyutta-nikaya",
    "an": "anguttara-nikaya",
    "kp": "khuddaka-nikaya/khuddakapatha",
    "dhp": "khuddaka-nikaya/dhammapada",
    "ud": "khuddaka-nikaya/udana",
    "iti": "khuddaka-nikaya/itivuttaka",
    "snp": "khuddaka-nikaya/sutta-nipata",
    "thag": "khuddaka-nikaya/theragatha",
    "thig": "khuddaka-nikaya/therigatha",
    "ja": "khuddaka-nikaya/jataka",
    "cp": "khuddaka-nikaya/cariyapitaka",
}

DISPLAY_PREFIXES = {
    "dn": "DN",
    "mn": "MN",
    "sn": "SN",
    "an": "AN",
    "kp": "Kp",
    "dhp": "Dhp",
    "ud": "Ud",
    "iti": "Iti",
    "snp": "Snp",
    "thag": "Thag",
    "thig": "Thig",
    "ja": "Ja",
    "cp": "Cp",
}

LEDGER_FIELDS = (
    "canonical_id",
    "collection_path",
    "txt_path",
    "label",
    "version_label",
    "source_url",
    "license",
    "source_commit",
    "upstream_file",
)


class InlineTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_inline_text(value: str) -> str:
    parser = InlineTextParser()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts)


def source_prefix(source_id: str) -> str:
    match = re.fullmatch(r"([a-z]+)([0-9].*)", source_id)
    if not match or match.group(1) not in COLLECTION_PATHS:
        raise ValueError(f"Unsupported SuttaCentral identifier: {source_id}")
    return match.group(1)


def canonical_id(source_id: str) -> str:
    prefix = source_prefix(source_id)
    value = source_id[len(prefix) :]
    return f"{DISPLAY_PREFIXES[prefix]} {value}"


def collection_path(source_id: str) -> str:
    return COLLECTION_PATHS[source_prefix(source_id)]


def flush_block(blocks: list[str], words: list[str]) -> None:
    text = " ".join(words).strip()
    if text:
        blocks.append(re.sub(r"\s+", " ", text))
    words.clear()


def render_text(
    source_id: str,
    segments: list[tuple[str, str]],
    templates: dict[str, str],
    translator: str,
    license_name: str,
    source_url: str,
) -> tuple[str, str]:
    title = ""
    blocks: list[str] = []
    words: list[str] = []

    for key, value in segments:
        template = templates.get(key, "{}")
        clean_value = re.sub(r"\s+", " ", plain_inline_text(value)).strip()
        if "sutta-title" in template and clean_value and not clean_value.isdigit():
            title = clean_value

        is_heading = bool(re.search(r"<h[1-6]\b", template))
        is_verse_line = "verse-line" in template
        starts_block = bool(re.search(r"<(?:p|li|h[1-6])\b", template))
        ends_block = bool(re.search(r"</(?:p|li|h[1-6])>", template))

        if is_heading or is_verse_line or starts_block:
            flush_block(blocks, words)
        if clean_value:
            if is_heading or is_verse_line:
                blocks.append(clean_value)
            else:
                words.append(clean_value)
        if ends_block:
            flush_block(blocks, words)

    flush_block(blocks, words)
    heading = canonical_id(source_id)
    if title:
        heading = f"{heading} - {title}"
    header = [
        heading,
        f"Translated by {translator}",
        f"Source: {source_url}",
        f"License: {license_name}",
        "",
    ]
    return title, "\n".join([*header, *blocks]).rstrip() + "\n"


def load_lock(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "repository",
        "commit",
        "translation_path",
        "html_path",
        "translator",
        "license",
    }
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Source lock is missing: {', '.join(sorted(missing))}")
    return data


def checkout_source(lock: dict[str, str], destination: Path) -> Path:
    commands = [
        ["git", "init", "--quiet", str(destination)],
        ["git", "-C", str(destination), "remote", "add", "origin", lock["repository"]],
        ["git", "-C", str(destination), "sparse-checkout", "init", "--no-cone"],
        [
            "git",
            "-C",
            str(destination),
            "sparse-checkout",
            "set",
            "--no-cone",
            "/LICENSE.md",
            f"/{lock['translation_path']}/",
            f"/{lock['html_path']}/",
        ],
        ["git", "-C", str(destination), "fetch", "--quiet", "--depth", "1", "origin", lock["commit"]],
        ["git", "-C", str(destination), "checkout", "--quiet", "--detach", "FETCH_HEAD"],
    ]
    for command in commands:
        subprocess.run(command, check=True)
    return destination


def verify_source(source: Path, lock: dict[str, str]) -> None:
    license_text = (source / "LICENSE.md").read_text(encoding="utf-8")
    if "Creative Commons Zero" not in license_text and "CC0" not in license_text:
        raise ValueError("The upstream checkout does not contain the expected CC0 license")
    if not (source / ".git").exists():
        raise ValueError("The Bilara source must be a Git checkout so its revision can be verified")
    actual = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual != lock["commit"]:
        raise ValueError(f"Expected Bilara commit {lock['commit']}, found {actual}")


def old_output_paths(ledger: Path, output_root: Path) -> list[Path]:
    if not ledger.exists():
        return []
    paths: list[Path] = []
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, dialect="excel-tab"):
            path = REPO_ROOT / row["txt_path"]
            try:
                path.relative_to(output_root)
            except ValueError:
                raise ValueError(f"Refusing to remove output outside {output_root}: {path}")
            paths.append(path)
    return paths


def import_source(source: Path, lock: dict[str, str], output_root: Path, ledger: Path) -> int:
    verify_source(source, lock)
    translation_root = source / lock["translation_path"]
    html_root = source / lock["html_path"]
    records: list[dict[str, str]] = []
    written: set[Path] = set()

    for translation_file in sorted(translation_root.rglob("*_translation-en-sujato.json")):
        relative = translation_file.relative_to(translation_root)
        html_relative = Path(str(relative).replace("_translation-en-sujato.json", "_html.json"))
        html_file = html_root / html_relative
        if not html_file.is_file():
            raise FileNotFoundError(f"Missing Bilara HTML structure: {html_file}")

        translations = json.loads(translation_file.read_text(encoding="utf-8"))
        templates = json.loads(html_file.read_text(encoding="utf-8"))
        grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for key, value in translations.items():
            grouped[key.split(":", 1)[0]].append((key, value))

        destination_dir = output_root / relative.parent
        destination_dir.mkdir(parents=True, exist_ok=True)
        for source_id, segments in grouped.items():
            text_path = destination_dir / f"{source_id}.txt"
            source_url = f"https://suttacentral.net/{source_id}/en/sujato"
            title, text = render_text(
                source_id,
                segments,
                templates,
                lock["translator"],
                lock["license"],
                source_url,
            )
            text_path.write_text(text, encoding="utf-8", newline="\n")
            written.add(text_path)
            records.append(
                {
                    "canonical_id": canonical_id(source_id),
                    "collection_path": collection_path(source_id),
                    "txt_path": text_path.relative_to(REPO_ROOT).as_posix(),
                    "label": title,
                    "version_label": f"{lock['translator']} translation ({lock['license']})",
                    "source_url": source_url,
                    "license": lock["license"],
                    "source_commit": lock["commit"],
                    "upstream_file": relative.as_posix(),
                }
            )

    for path in old_output_paths(ledger, output_root):
        if path not in written and path.is_file():
            path.unlink()

    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=LEDGER_FIELDS,
            dialect="excel-tab",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(records)
    return len(records)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--source", type=Path, help="Use an existing checkout instead of downloading")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    lock = load_lock(args.lock)
    if args.source:
        count = import_source(args.source, lock, args.output, args.ledger)
    else:
        with tempfile.TemporaryDirectory(prefix="suttacentral-bilara-") as temp_dir:
            source = checkout_source(lock, Path(temp_dir) / "bilara-data")
            count = import_source(source, lock, args.output, args.ledger)
    print(f"Imported {count} CC0 SuttaCentral texts at {lock['commit']}")
    print(f"Ledger: {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
