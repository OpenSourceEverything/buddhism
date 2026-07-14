from __future__ import annotations

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

    def test_every_page_uses_home_without_site_branding_and_ends_with_contact(self) -> None:
        incorrect: list[str] = []
        for page in ROOT.rglob("*.html"):
            source = page.read_text(encoding="utf-8")
            if "Free Buddhism" in source or not source.rstrip().endswith("</body>\n</html>"):
                incorrect.append(str(page.relative_to(ROOT)))
                continue
            body = source.split("<body>", 1)[1]
            if "admin@opensourceeverything.net</a></p>\n</body>" not in body:
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
            '<a href="tipitaka.html">Pāli Tipiṭaka</a>',
            "without distortion",
            "cessation of suffering",
        )
        for text in expected:
            with self.subTest(text=text):
                self.assertIn(text, homepage)
        self.assertNotIn("stylesheet", homepage)
        self.assertNotIn("<style", homepage)

    def test_dhamma_tree_links_to_teachings_practice_and_glossary(self) -> None:
        dhamma = (SITE / "dhamma.html").read_text(encoding="utf-8")
        required_links = (
            "four-noble-truths.html",
            "eightfold-path.html",
            "teachings.html#three-characteristics",
            "teachings.html#ten-fetters",
            "practice.html#five-precepts",
            "practice.html#five-hindrances",
            "practice.html#four-jhanas",
            "glossary.html",
        )
        for href in required_links:
            with self.subTest(href=href):
                self.assertIn(f'href="{href}"', dhamma)

    def test_reference_pages_and_glossary_cover_the_proposed_terms(self) -> None:
        teachings = (SITE / "teachings.html").read_text(encoding="utf-8")
        practice = (SITE / "practice.html").read_text(encoding="utf-8")
        glossary = (SITE / "glossary.html").read_text(encoding="utf-8")
        for anchor in (
            "three-characteristics",
            "five-aggregates",
            "dependent-origination",
            "kamma",
            "rebirth",
            "nibbana",
            "ten-fetters",
        ):
            self.assertIn(f'id="{anchor}"', teachings)
        for anchor in (
            "five-precepts",
            "five-recollections",
            "four-foundations-of-mindfulness",
            "five-hindrances",
            "seven-awakening-factors",
            "four-jhanas",
        ):
            self.assertIn(f'id="{anchor}"', practice)
        glossary_list = glossary.split("<h1>Glossary</h1>", 1)[1]
        glossary_terms = ("Dependent origination", "Dhamma", "Five aggregates", "Nibbāna", "Ten fetters")
        positions = [glossary_list.index(term) for term in glossary_terms]
        self.assertEqual(positions, sorted(positions))

    def test_theravada_page_defines_the_tradition(self) -> None:
        page = (SITE / "theravada.html").read_text(encoding="utf-8")
        self.assertIn("oldest surviving Buddhist tradition", page)
        self.assertIn('<a href="tipitaka.html">Pāli Tipiṭaka</a>', page)
        self.assertIn("later Mahāyāna sūtras are not part of its canon", page)

    def test_each_path_factor_has_a_terse_page_with_sources(self) -> None:
        overview = (SITE / "eightfold-path.html").read_text(encoding="utf-8")
        for factor in PATH_FACTORS:
            with self.subTest(factor=factor):
                self.assertIn(f'href="path/{factor}.html"', overview)
                page = (SITE / "path" / f"{factor}.html").read_text(encoding="utf-8")
                self.assertIn("Relevant suttas", page)
                self.assertIn('href="../eightfold-path.html"', page)
                self.assertIn("admin@opensourceeverything.net", page)

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
