from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "theravada" / "tipitaka" / "site"
PATH_FACTORS = (
    "right-view",
    "right-intention",
    "right-speech",
    "right-action",
    "right-livelihood",
    "right-effort",
    "right-mindfulness",
    "right-concentration",
)
TEACHING_PAGES = (
    "three-characteristics",
    "five-aggregates",
    "dependent-origination",
    "kamma",
    "rebirth",
    "nibbana",
    "ten-fetters",
)
PRACTICE_PAGES = (
    "five-precepts",
    "five-recollections",
    "four-foundations-of-mindfulness",
    "five-hindrances",
    "seven-awakening-factors",
    "four-jhanas",
)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


class StaticSiteStructureTests(unittest.TestCase):
    def test_every_page_uses_unstyled_browser_defaults(self) -> None:
        styled: list[str] = []
        for page in ROOT.rglob("*.html"):
            source = page.read_text(encoding="utf-8")
            if any(marker in source for marker in ("stylesheet", "<style", "style=", 'class="')):
                styled.append(str(page.relative_to(ROOT)))
        self.assertEqual(styled, [], "Styled pages:\n" + "\n".join(styled))

    def test_only_core_pages_show_contact(self) -> None:
        incorrect: list[str] = []
        contact_pages = {
            SITE / "index.html",
        }
        for page in ROOT.rglob("*.html"):
            source = page.read_text(encoding="utf-8")
            if "Free Buddhism" in source or not source.rstrip().endswith("</body>\n</html>"):
                incorrect.append(str(page.relative_to(ROOT)))
                continue
            has_contact = "gregcooper@protonmail.com" in source
            if has_contact != (page in contact_pages):
                incorrect.append(str(page.relative_to(ROOT)))
        self.assertEqual(incorrect, [], "Incorrect page shell:\n" + "\n".join(incorrect))

    def test_homepage_uses_the_minimal_linked_summary(self) -> None:
        homepage = (SITE / "index.html").read_text(encoding="utf-8")
        expected = (
            "<title>Home</title>",
            "<h1>Home</h1>",
            '<a href="theravada.html">Theravāda Buddhism</a>',
            '<a href="dhamma.html">Dhamma</a>',
            '<a href="four-noble-truths.html">Four Noble Truths</a>',
            '<a href="eightfold-path.html">Noble Eightfold Path</a>',
            '<a href="tipitaka.html">Buddhist Texts</a>',
            "Pāli Tipiṭaka",
            "without distortion",
            "cessation of suffering",
        )
        for text in expected:
            with self.subTest(text=text):
                self.assertIn(text, homepage)
        self.assertNotIn("stylesheet", homepage)
        self.assertNotIn("<style", homepage)

    def test_every_generated_page_has_the_three_item_navigation(self) -> None:
        incorrect: list[str] = []
        for page in (ROOT / "theravada").rglob("*.html"):
            source = page.read_text(encoding="utf-8")
            first_paragraph = source.split("<body>\n", 1)[1].split("</p>", 1)[0]
            labels = re.findall(r">([^<]+)</a>", first_paragraph)
            if labels != ["Home", "Dhamma", "Buddhist Texts"]:
                incorrect.append(str(page.relative_to(ROOT)))
        self.assertEqual(incorrect, [], "Incorrect navigation:\n" + "\n".join(incorrect))

    def test_dhamma_tree_keeps_only_the_primary_branches(self) -> None:
        dhamma = (SITE / "dhamma.html").read_text(encoding="utf-8")
        tree = dhamma.split("<pre>", 1)[1].split("</pre>", 1)[0]
        required_links = (
            "four-noble-truths.html",
            "eightfold-path.html",
            "teachings.html",
            "practice.html",
            "tipitaka.html",
            "glossary.html",
        )
        for href in required_links:
            with self.subTest(href=href):
                self.assertIn(f'href="{href}"', tree)
        self.assertNotIn('href="teachings/', tree)
        self.assertNotIn('href="practice/', tree)

    def test_reference_pages_and_glossary_cover_the_proposed_terms(self) -> None:
        teachings = (SITE / "teachings.html").read_text(encoding="utf-8")
        practice = (SITE / "practice.html").read_text(encoding="utf-8")
        glossary = (SITE / "glossary.html").read_text(encoding="utf-8")
        for slug in TEACHING_PAGES:
            with self.subTest(teaching=slug):
                self.assertIn(f'href="teachings/{slug}.html"', teachings)
                detail = (SITE / "teachings" / f"{slug}.html").read_text(encoding="utf-8")
                self.assertIn('href="../teachings.html"', detail)
                self.assertIn("Relevant suttas", detail)
        for slug in PRACTICE_PAGES:
            with self.subTest(practice=slug):
                self.assertIn(f'href="practice/{slug}.html"', practice)
                detail = (SITE / "practice" / f"{slug}.html").read_text(encoding="utf-8")
                self.assertIn('href="../practice.html"', detail)
                self.assertIn("Relevant suttas", detail)
        glossary_list = glossary.split("<h1>Glossary</h1>", 1)[1]
        glossary_terms = ("Dependent origination", "Dhamma", "Five aggregates", "Nibbāna", "Ten fetters")
        positions = [glossary_list.index(term) for term in glossary_terms]
        self.assertEqual(positions, sorted(positions))

    def test_theravada_page_defines_the_tradition(self) -> None:
        page = (SITE / "theravada.html").read_text(encoding="utf-8")
        self.assertIn("oldest surviving Buddhist tradition", page)
        self.assertIn('<a href="tipitaka.html">Buddhist Texts</a>', page)
        self.assertIn("later Mahāyāna sūtras are not part of its canon", page)

    def test_buddhist_texts_page_contains_the_tipitaka_tree_and_resources(self) -> None:
        page = (SITE / "tipitaka.html").read_text(encoding="utf-8")
        tree = page.split("<pre>", 1)[1].split("</pre>", 1)[0]
        for name in ("Vinaya Piṭaka", "Sutta Piṭaka", "Abhidhamma Piṭaka", "Khuddaka Nikāya"):
            with self.subTest(name=name):
                self.assertIn(name, tree)
        self.assertIn('href="sutta-texts.html">Texts</a>', page)
        self.assertIn('href="sutta-audio.html">Audio and video</a>', page)
        self.assertIn('href="downloads.html">Downloads</a>', page)
        self.assertIn('href="sutta.html">Sutta Piṭaka</a>', tree)
        self.assertIn('href="../sutta/khuddaka-nikaya/index.html">Khuddaka Nikāya</a>', tree)

    def test_sutta_hub_separates_texts_audio_and_downloads(self) -> None:
        hub = (SITE / "sutta.html").read_text(encoding="utf-8")
        self.assertIn('href="tipitaka.html">Buddhist Texts</a>', hub)
        self.assertIn('href="../sutta/samyutta-nikaya/index.html">Saṁyutta Nikāya</a>', hub)
        self.assertIn('href="../sutta/khuddaka-nikaya/index.html">Khuddaka Nikāya</a>', hub)
        self.assertIn('href="sutta-texts.html">Texts</a>', hub)
        self.assertIn('href="sutta-audio.html">Audio</a>', hub)
        self.assertIn('href="downloads.html">Downloads</a>', hub)

        texts = (SITE / "sutta-texts.html").read_text(encoding="utf-8")
        self.assertIn("Digha Nikaya", texts)
        self.assertIn("Majjhima Nikaya", texts)
        self.assertIn("Samyutta Nikaya", texts)
        self.assertIn("Anguttara Nikaya", texts)
        self.assertIn("Sutta Nipata", texts)

    def test_audio_index_exposes_every_manifest_video_once(self) -> None:
        audio = (SITE / "sutta-audio.html").read_text(encoding="utf-8")
        video_ids = re.findall(r"youtube\.com/watch\?v=([A-Za-z0-9_-]+)", audio)
        self.assertEqual(len(video_ids), 1115)
        self.assertEqual(len(set(video_ids)), len(video_ids))

    def test_reference_pages_route_suttas_through_the_local_indexes(self) -> None:
        offenders: list[str] = []
        for page in SITE.rglob("*.html"):
            if page.name == "sutta-audio.html":
                continue
            if "youtube.com/watch" in page.read_text(encoding="utf-8"):
                offenders.append(str(page.relative_to(SITE)))
        self.assertEqual(offenders, [], "Direct YouTube links outside audio index:\n" + "\n".join(offenders))

    def test_related_sutta_links_use_only_canonical_ids(self) -> None:
        page = (SITE / "teachings" / "five-aggregates.html").read_text(encoding="utf-8")
        related = page.split("<h2>Relevant suttas</h2>", 1)[1].split("</ul>", 1)[0]
        labels = re.findall(r">([^<]+)</a>", related)
        self.assertEqual(labels, ["SN 22.59", "SN 22.95"])
        self.assertNotIn("(text, audio, and downloads)", page)

    def test_sutta_pages_combine_text_and_audio_links(self) -> None:
        folder = ROOT / "theravada" / "tipitaka" / "sutta" / "majjhima-nikaya" / "mn121"
        landing = (folder / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="../index.html">Majjhima Nikaya</a>', landing)
        self.assertIn("<h1>MN 121 —", landing)
        self.assertIn("<h2>Texts</h2>", landing)
        self.assertIn('href="mn121.html"', landing)
        self.assertIn('href="mn121-02.html"', landing)
        self.assertIn("<h2>Audio</h2>", landing)
        self.assertIn("youtube.com/watch", landing)
        self.assertNotIn("Download TXT", landing)
        self.assertNotIn("Browse this collection", landing)
        self.assertFalse((folder / "texts.html").exists())
        self.assertFalse((folder / "audio.html").exists())

        translation = (folder / "mn121.html").read_text(encoding="utf-8")
        self.assertIn('href="index.html">MN 121</a>', translation)
        self.assertIn("Download TXT", translation)
        self.assertIn("Download PDF", translation)
        self.assertNotIn("youtube.com/watch", translation)

    def test_collection_pages_link_suttas_once_and_offer_collection_downloads(self) -> None:
        collection = (
            ROOT / "theravada" / "tipitaka" / "sutta" / "majjhima-nikaya" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertEqual(collection.count("<td>MN 121</td>"), 1)
        self.assertIn('href="mn121/index.html"', collection)
        self.assertIn("Download this collection", collection)
        self.assertIn("majjhima-nikaya.zip", collection)

        samyutta = (
            ROOT / "theravada" / "tipitaka" / "sutta" / "samyutta-nikaya" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn('href="../../site/sutta.html">Sutta Pitaka</a>', samyutta)
        self.assertIn('href="../../site/sutta.html">Sutta Pitaka</a>', collection)

        khuddaka = (
            ROOT / "theravada" / "tipitaka" / "sutta" / "khuddaka-nikaya" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn('href="../../site/sutta.html">Sutta Pitaka</a>', khuddaka)
        self.assertIn('href="dhammapada/index.html">Dhammapada</a>', khuddaka)

        dhammapada = (
            ROOT
            / "theravada"
            / "tipitaka"
            / "sutta"
            / "khuddaka-nikaya"
            / "dhammapada"
            / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn('href="../index.html">Khuddaka Nikaya</a>', dhammapada)

        downloads = (SITE / "downloads.html").read_text(encoding="utf-8")
        self.assertIn("All available material", downloads)
        self.assertIn('href="../downloads/majjhima-nikaya.zip">Majjhima Nikaya</a>', downloads)

    def test_each_path_factor_has_a_terse_page_with_sources(self) -> None:
        overview = (SITE / "eightfold-path.html").read_text(encoding="utf-8")
        for factor in PATH_FACTORS:
            with self.subTest(factor=factor):
                self.assertIn(f'href="path/{factor}.html"', overview)
                page = (SITE / "path" / f"{factor}.html").read_text(encoding="utf-8")
                self.assertIn("Relevant suttas", page)
                self.assertIn('href="../eightfold-path.html"', page)
                self.assertNotIn("gregcooper@protonmail.com", page)

    def test_all_committed_local_page_links_resolve(self) -> None:
        broken: list[str] = []
        for source in ROOT.rglob("*.html"):
            parser = LinkParser()
            parser.feed(source.read_text(encoding="utf-8"))
            for href in parser.links:
                parsed = urlsplit(href)
                if parsed.scheme or href.startswith("//") or not parsed.path:
                    continue
                if parsed.path.startswith("/"):
                    target = ROOT / unquote(parsed.path).lstrip("/")
                else:
                    target = source.parent / unquote(parsed.path)
                target = target.resolve()
                if target.suffix == ".zip":
                    continue
                if not target.exists():
                    broken.append(f"{source.relative_to(ROOT)} -> {href}")
        self.assertEqual(broken, [], "Broken local links:\n" + "\n".join(broken))


if __name__ == "__main__":
    unittest.main()
