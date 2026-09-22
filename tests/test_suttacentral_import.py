from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "buddhist_canon_pipeline"))

from import_suttacentral_bilara import canonical_id, collection_path, render_text


class SuttaCentralImportTests(unittest.TestCase):
    def test_committed_import_matches_the_pinned_source(self) -> None:
        lock = json.loads(
            (ROOT / "metadata/source-manifests/suttacentral-bilara.json").read_text(encoding="utf-8")
        )
        ledger = ROOT / "theravada/tipitaka/sutta/suttacentral-sujato-text-ledger.tsv"
        with ledger.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, dialect="excel-tab"))

        self.assertEqual(len(rows), 5308)
        self.assertEqual(len({row["canonical_id"] for row in rows}), 5308)
        self.assertEqual(sum(row["canonical_id"].startswith("Dhp ") for row in rows), 423)
        self.assertEqual({row["source_commit"] for row in rows}, {lock["commit"]})
        self.assertEqual({row["license"] for row in rows}, {"CC0-1.0"})
        missing = [row["txt_path"] for row in rows if not (ROOT / row["txt_path"]).is_file()]
        self.assertEqual(missing, [])

    def test_maps_canonical_ids_and_collections(self) -> None:
        cases = {
            "mn1": ("MN 1", "majjhima-nikaya"),
            "sn1.20": ("SN 1.20", "samyutta-nikaya"),
            "dhp21": ("Dhp 21", "khuddaka-nikaya/dhammapada"),
            "thig1.1": ("Thig 1.1", "khuddaka-nikaya/therigatha"),
        }
        for source_id, expected in cases.items():
            with self.subTest(source_id=source_id):
                self.assertEqual(canonical_id(source_id), expected[0])
                self.assertEqual(collection_path(source_id), expected[1])

    def test_renders_title_paragraphs_verses_and_provenance(self) -> None:
        segments = [
            ("sn1.20:0.1", "Linked Discourses 1.20 "),
            ("sn1.20:0.2", "With Samiddhi "),
            ("sn1.20:1.1", "So I have heard. "),
            ("sn1.20:1.2", "At one <em>time</em> ... <j>"),
            ("sn1.20:2.1", "First verse line "),
            ("sn1.20:2.2", "Second verse line "),
        ]
        templates = {
            "sn1.20:0.1": "<header><li>{}</li>",
            "sn1.20:0.2": "<h1 class='sutta-title'>{}</h1></header>",
            "sn1.20:1.1": "<p>{}",
            "sn1.20:1.2": "{}</p>",
            "sn1.20:2.1": "<span class='verse-line'>{}</span>",
            "sn1.20:2.2": "<span class='verse-line'>{}</span>",
        }
        title, text = render_text(
            "sn1.20", segments, templates, "Bhikkhu Sujato", "CC0-1.0", "https://example.test"
        )
        self.assertEqual(title, "With Samiddhi")
        self.assertIn("SN 1.20 - With Samiddhi", text)
        self.assertIn("So I have heard. At one time ...", text)
        self.assertNotIn("<em>", text)
        self.assertNotIn("<j>", text)
        self.assertIn("First verse line\nSecond verse line", text)
        self.assertIn("License: CC0-1.0", text)


if __name__ == "__main__":
    unittest.main()
