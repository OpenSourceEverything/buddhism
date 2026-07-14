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

    def test_homepage_uses_the_minimal_linked_summary(self) -> None:
        homepage = (SITE / "index.html").read_text(encoding="utf-8")
        expected = (
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
