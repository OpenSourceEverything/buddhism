# Buddhism Corpus

Static, file-oriented Buddhist text corpus organized for simple mirroring and
plain static hosting.

Current focus:

- Theravada
- Tipitaka
- Sutta Pitaka
- CC0 English sutta translations by Bhikkhu Sujato from SuttaCentral
- Candana Bhikkhu / Mind Released PDF and recording sources

## Repository Layout

```text
theravada/
  tipitaka/
    vinaya/
    sutta/
      digha-nikaya/
      majjhima-nikaya/
      samyutta-nikaya/
      anguttara-nikaya/
      khuddaka-nikaya/
      <collection>/<sutta>/
        index.html
        <text-version>.html
        <text-version>.txt
        <text-version>.pdf
      candana-bhikkhu-text-ledger.tsv
      suttacentral-sujato-text-ledger.tsv
      candana-bhikkhu-coverage-status.txt
    translations/
      en/suttacentral/sujato/sutta/
    abhidhamma/
    site/
      index.html
      theravada.html
      dhamma.html
      teachings.html
      teachings/
        three-characteristics.html
        five-aggregates.html
        dependent-origination.html
        kamma.html
        rebirth.html
        nibbana.html
        ten-fetters.html
      practice.html
      practice/
        five-precepts.html
        five-recollections.html
        four-foundations-of-mindfulness.html
        five-hindrances.html
        seven-awakening-factors.html
        four-jhanas.html
      glossary.html
      four-noble-truths.html
      eightfold-path.html
      path/
        right-view.html
        right-intention.html
        right-speech.html
        right-action.html
        right-livelihood.html
        right-effort.html
        right-mindfulness.html
        right-concentration.html
      tipitaka.html
      sutta.html
      sutta-texts.html
      sutta-audio.html
      downloads.html
    downloads/
      README.md
metadata/
  reports/
  source-manifests/
  youtube-playlists/
tools/
  buddhist_canon_pipeline/
```

## Generated Artifacts

ZIP bundles are generated artifacts and are not stored in git.

Ignored path:

```text
theravada/tipitaka/downloads/*.zip
```

Regenerate site pages and ZIP bundles:

```text
python tools/buddhist_canon_pipeline/build_static_site.py
```

## Current Corpus State

Current extracted text ledger:

```text
theravada/tipitaka/sutta/candana-bhikkhu-text-ledger.tsv
```

Current coverage notes:

```text
theravada/tipitaka/sutta/candana-bhikkhu-coverage-status.txt
metadata/reports/candana-text-vs-youtube-coverage.md
```

Current source manifest:

```text
metadata/source-manifests/mindreleased-source-manifest.jsonl
```

The initial source pull found and extracted 195 usable PDF/text sources.

The pinned SuttaCentral import adds 5,308 CC0 English texts: the complete four
main Nikayas translated by Bhikkhu Sujato and all of his available Khuddaka
Nikaya translations, including all 423 Dhammapada verses.
The pinned SuttaCentral import adds the available CC0 Bhikkhu Sujato sutta
translations without claiming complete English coverage of every Tipiṭaka book.

## Pipeline Commands

Install tool dependencies on a fresh machine:

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r tools/buddhist_canon_pipeline/requirements.txt
```

Discover Mind Released PDF sources:

```text
python tools/buddhist_canon_pipeline/discover_mindreleased_sources.py --output metadata/source-manifests/mindreleased-source-manifest.jsonl
```

Pull PDFs and extract text:

```text
python tools/buddhist_canon_pipeline/pull_mindreleased_texts.py --manifest metadata/source-manifests/mindreleased-source-manifest.jsonl --force
```

Import the pinned CC0 SuttaCentral translations:

```text
python tools/buddhist_canon_pipeline/import_suttacentral_bilara.py
```

The source revision, paths, translator, and license are locked in
`metadata/source-manifests/suttacentral-bilara.json`. The importer downloads
only the required Bilara paths, verifies the commit and license, writes readable
TXT files, and rebuilds their ledger.

Import the pinned SuttaCentral translations:

```text
python tools/buddhist_canon_pipeline/import_suttacentral_bilara.py
```

The exact upstream commit and license are recorded in
`metadata/source-manifests/suttacentral-bilara.json`. The importer downloads
only the required Bilara paths, verifies that commit, and regenerates the text
ledger and normalized TXT files.

Inventory Candana YouTube playlists:

```text
python tools/buddhist_canon_pipeline/inventory_playlist_set.py --playlist-set metadata/youtube-playlists/candana-major-playlists.tsv --output-dir metadata/youtube-playlists/manifests
```

Compare extracted text coverage to YouTube playlist coverage:

```text
python tools/buddhist_canon_pipeline/compare_youtube_text_coverage.py
```

Build static HTML site and generated download ZIPs:

```text
python tools/buddhist_canon_pipeline/build_static_site.py
```

For a quick local preview without rebuilding ZIP downloads:

```text
python tools/buddhist_canon_pipeline/build_static_site.py --skip-zips
```

The build reads the committed Candana Bhikkhu playlist manifests. The Buddhist
Texts page presents the Pāli Tipiṭaka tree and links to every available text by
collection, all inventoried audio, and the generated downloads. Each sutta page
lists all available text versions and matching audio together. Each text version
has its own readable page and TXT/PDF downloads. Whole-library and per-collection
ZIPs are generated outside Git. Grouped recordings retain their complete playlist
title rather than being presented as one-sutta recordings.

## Git Notes

The intended remote is:

```text
https://github.com/OpenSourceEverything/buddhism.git
```

Use a neutral local git identity for this repo. Do not use work/employer
identity metadata.

Current local identity used during setup:

```text
user.name=OpenSourceEverything
user.email=opensourceeverything@users.noreply.github.com
```

## Before First Push

- Decide whether to keep both flat ingestion files and canonical generated
  per-sutta folders, or remove/ignore flat ingestion files.
- Ensure the committed ledger points to files that are actually committed.
- Re-run the static site generator after cleanup.
- Run a full relative-link check.
- Commit with neutral local identity.
