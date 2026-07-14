# Buddhist Canon Pipeline Tools

Small Python tools for discovering source PDFs, extracting text, inventorying
YouTube metadata, comparing coverage, and generating the static site.

## Setup

From the repository root:

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r tools/buddhist_canon_pipeline/requirements.txt
```

On a machine where Python packages are already available, the scripts can also
be run directly with `python`.

## Tool Order

Discover Mind Released source PDFs:

```text
python tools/buddhist_canon_pipeline/discover_mindreleased_sources.py --output metadata/source-manifests/mindreleased-source-manifest.jsonl
```

Download PDFs and extract TXT:

```text
python tools/buddhist_canon_pipeline/pull_mindreleased_texts.py --manifest metadata/source-manifests/mindreleased-source-manifest.jsonl --force
```

Inventory Candana Bhikkhu YouTube playlists:

```text
python tools/buddhist_canon_pipeline/inventory_playlist_set.py --playlist-set metadata/youtube-playlists/candana-major-playlists.tsv --output-dir metadata/youtube-playlists/manifests
```

Compare extracted text coverage against playlist metadata:

```text
python tools/buddhist_canon_pipeline/compare_youtube_text_coverage.py
```

Build canonical per-sutta folders, HTML pages, site pages, and generated ZIPs:

```text
python tools/buddhist_canon_pipeline/build_static_site.py
```

The site build also reads `metadata/youtube-playlists/manifests/*.jsonl` and
adds Candana Bhikkhu listening links for exact canonical matches. It can also
honestly associate a sutta with a grouped Aṅguttara recording or its containing
Sutta Nipāta/Theragāthā book. It does not download or embed video or audio.

ZIPs are generated artifacts. They are written under:

```text
theravada/tipitaka/downloads/
```

and ignored by git.

## Notes

- `pull_mindreleased_texts.py` prefers PyMuPDF for better newline/layout
  preservation and falls back to PyPDF2 if PyMuPDF is unavailable.
- YouTube tooling inventories metadata only. It does not download audio/video.
- Public captions are not a reliable source path yet.
