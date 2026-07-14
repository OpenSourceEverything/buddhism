# Buddhism Corpus

Static, file-oriented Buddhist text corpus organized for simple mirroring and
plain static hosting.

Current focus:

- Theravada
- Tipitaka
- Sutta Pitaka
- Candana Bhikkhu / Mind Released PDF sources

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
      candana-bhikkhu-text-ledger.tsv
      candana-bhikkhu-coverage-status.txt
    abhidhamma/
    site/
      index.html
      dhamma.html
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
      downloads.html
      assets/style.css
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

The build reads the committed Candana Bhikkhu playlist manifests and adds a
YouTube listening link to each sutta page where the canonical ID can be
matched reliably. Grouped recordings are labeled with their complete playlist
title rather than presented as one-sutta recordings.

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
