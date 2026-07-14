from __future__ import annotations

import sys
import unittest
from pathlib import Path


PIPELINE_DIR = Path(__file__).resolve().parents[1] / "tools" / "buddhist_canon_pipeline"
sys.path.insert(0, str(PIPELINE_DIR))

from youtube_metadata import (  # noqa: E402
    canonical_lookup_keys,
    parse_ids,
    read_youtube_index,
    videos_for_canonical_id,
)


class YouTubeMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        manifest_dir = Path(__file__).resolve().parents[1] / "metadata" / "youtube-playlists" / "manifests"
        cls.index = read_youtube_index(manifest_dir)

    def test_parses_foundational_sutta_ids(self) -> None:
        self.assertEqual(
            parse_ids(
                "The Middle Length Discourses: Sutta 117 - Mahācattārisaka Sutta",
                "majjhima-nikaya",
            ),
            {"MN 117"},
        )
        self.assertEqual(
            parse_ids("The Connected Discourses: SN 56.11 Dhammacakkappavattana Sutta", "samyutta-nikaya"),
            {"SN 56.11"},
        )

    def test_expands_grouped_anguttara_recordings(self) -> None:
        parsed = parse_ids(
            'The Numerical Discourses: Book V: Suttas 171-180: "The Section on Lay Disciples."',
            "anguttara-nikaya",
        )
        self.assertIn("AN 5.177", parsed)
        self.assertEqual(len(parsed), 10)
        abbreviated = parse_ids(
            'The Numerical Discourses: Book VIII: 21-30: "The Section on the Householders."',
            "anguttara-nikaya",
        )
        self.assertIn("AN 8.22", abbreviated)
        self.assertIn("AN 8.30", abbreviated)

    def test_maps_special_corpus_ids_to_audio(self) -> None:
        self.assertEqual(canonical_lookup_keys("Dhp 2.21")[0][0], "Dhp 21")
        self.assertEqual(canonical_lookup_keys("Snp 1.1")[1], ["Snp book 1"])
        self.assertEqual(canonical_lookup_keys("Thag 17.3")[1], ["Thag book 17"])

    def test_finds_exact_and_book_level_candana_audio(self) -> None:
        expected = {
            "MN 117": "WXslrgXOL3w",
            "SN 56.11": "IUKWjEWJ6js",
            "AN 5.177": "B3Q9IohRYoA",
            "Dhp 2.21": "N6i0zYYM9AE",
            "Snp 1.1": "UyzIIBy47g8",
            "Snp complete": "XzPcVwEZdoE",
            "Thag 17.3": "KcCrGi-N6rU",
        }
        for canonical_id, video_id in expected.items():
            with self.subTest(canonical_id=canonical_id):
                matches = videos_for_canonical_id(canonical_id, self.index)
                self.assertTrue(matches)
                self.assertEqual(matches[0].video_id, video_id)

    def test_does_not_invent_missing_audio(self) -> None:
        self.assertEqual(videos_for_canonical_id("SN 45.8", self.index), [])
        self.assertEqual(videos_for_canonical_id("Mil 7.8.7", self.index), [])


if __name__ == "__main__":
    unittest.main()
