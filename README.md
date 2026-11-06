# Local Tools

Small local web tools for product images, PDFs, spreadsheets, and video. Files stay on your machine.

Source is **AGPL-3.0**. You need Python to run it; there is no packaged installer yet.

中文说明见 [README.zh-CN.md](README.zh-CN.md).

## Tools

| Tool | Path | Notes |
|------|------|------|
| Video → audio | `/video.html` | Extract MP3, WAV, AAC, M4A, OGG, FLAC |
| Video compress | `/video-compress.html` | Resolution + CRF; MP4 / WebM |
| Image compress | `/image.html` | Shrink size; optional size cap; batch zip |
| Image convert | `/image-convert.html` | JPG / PNG / WebP, scale, crop; batch zip |
| EXIF strip | `/exif.html` | View and remove camera time, model, GPS |
| Text watermark | `/watermark.html` | Position or diagonal tile; opacity; batch zip |
| JSON format | `/json.html` | Format / minify / validate in the browser |
| Base64 | `/base64.html` | Text in-browser; files via local API |
| CSV ↔ Excel | `/csv-excel.html` | CSV and `.xlsx` |
| CSV clean | `/csv-clean.html` | Drop empty rows, exact dupes, keep columns; batch zip |
| Doc convert | `/doc-convert.html` | Image / PDF / OFD / Word / PPT |
| PDF tools | `/pdf.html` | Merge, compress, split / extract, encrypt / decrypt |
| Recent jobs | `/` | Last 20 local summaries on the home page; clearable |

UI is Chinese / English (top-right). API error language follows `Accept-Language`. Home “recent” stores tool name, time, and a short summary only — not file contents.

## Requirements

- Python 3.10+
- Windows or Linux
- FFmpeg comes via `imageio-ffmpeg` (no separate install)
- Word / PPT → PDF needs **LibreOffice** (preferred) or **Microsoft Office** (Windows)

## Quick start

Either remote is fine:

```text
https://github.com/leoxiaoyg/local-tools.git
https://gitee.com/xyg-dev/local-tools.git
```

### Windows

```bat
git clone https://github.com/leoxiaoyg/local-tools.git
cd local-tools
run.bat
```

Open the URL printed in the terminal (usually [http://127.0.0.1:8000](http://127.0.0.1:8000)). If the port is taken, the script tries 8080, then 8765.

### Linux / macOS

```bash
git clone https://github.com/leoxiaoyg/local-tools.git
cd local-tools
chmod +x run.sh
./run.sh
```

### Manual start

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux:    source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

There is no `main.py`. The app entry is `app.main:app`, or just use `run.bat` / `run.sh`.

### Optional pip proxy

Scripts talk to PyPI directly by default. If you need a local proxy:

```bat
set LT_PIP_PROXY=http://127.0.0.1:7897
run.bat
```

```bash
export LT_PIP_PROXY=http://127.0.0.1:7897
./run.sh
```

## CLI

Same handlers as the web UI; no HTTP. Covers image compress / convert / watermark, video audio / compress, EXIF, PDF merge / compress / split / encrypt / decrypt, CSV clean. No Office convert on CLI.

```bash
python -m app --help
python -m app --lang en image compress photo.jpg -o small.jpg
python -m app image convert a.png b.png --format webp -o converted.zip
python -m app image watermark photo.jpg --text ShopName
python -m app exif inspect photo.jpg
python -m app exif strip *.jpg -o clean.zip
python -m app pdf merge a.pdf b.pdf -o merged.pdf
python -m app pdf compress invoice.pdf --preset strong
python -m app pdf split doc.pdf --mode range --pages 1-3,5
python -m app pdf encrypt invoice.pdf --user-pw secret -o locked.pdf
python -m app pdf decrypt locked.pdf --password secret -o opened.pdf
python -m app csv clean data.csv --keep sku,name
python -m app video audio clip.mp4 --format mp3
python -m app video compress clip.mp4 --crf 28 --resolution 720
```

`--lang zh|en` (or `LT_LANG`) sets message language. Multiple inputs become a zip by default; `-o` to an existing directory writes files one by one.

CLI details: [docs/01-product/cli.md](docs/01-product/cli.md). Doc index: [docs/00-governance/wiki.md](docs/00-governance/wiki.md).

## Limits

- No Windows installer / single-file exe (see ADR-004)
- Office conversion needs software already installed on the machine
- PDF work uses PyMuPDF (AGPL). Encrypt / EXIF strip are not legal or compliance certifications
- `.cursor/skills/` is for Cursor agents; ignore if unused

## Sponsoring

Everything listed above works without paying. If you want to tip maintenance later, real Afdian / GitHub Sponsors links will go here — no placeholder URLs.

## License

[AGPL-3.0](LICENSE). Chosen mainly because PyMuPDF is AGPL too. Other dependencies keep their own licenses.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Layout

```
local-tools/
├── app/                  # FastAPI backend
├── static/               # Web UI
├── tests/                # CLI smoke: python tests/cli_smoke.py
├── docs/                 # Guides, ADRs, tests (start at wiki.md)
├── _qa_workdir/          # QA scripts; fixtures/outputs stay local
├── requirements.txt
├── run.bat / run.sh
├── LICENSE
├── CONTRIBUTING.md
└── SECURITY.md
```

## Size caps

| Kind | Cap |
|------|------|
| Video | 500 MB per file; CLI batch up to 10 |
| Images | 50 MB per file; batch 200 MB / 50 files |
| CSV / Excel | 20 MB per file; clean batch 200 MB / 50 files |
| Doc convert | 80 MB |
| PDF | 80 MB per file; merge 200 MB / 30 files |
| Base64 file encode | 10 MB |

## Doc convert notes

| Conversion | How | Notes |
|------|------|------|
| Image → PDF | Pillow | Pure Python; multi-image OK |
| Image → OFD | easyofd | Pure Python |
| PDF → OFD | easyofd | Pure Python; complex layout may drift |
| PDF → Word | pdf2docx | Pure Python; no OCR for scans |
| Word → PDF | LibreOffice / MS Word | Needs a local Office engine |
| PPT → PDF | LibreOffice / MS PowerPoint | Needs a local Office engine |

## FAQ

**Port in use:** the start script tries 8080, then 8765.

**Image format changed after compress:** “keep format” only optimizes inside the original type. For a much smaller PNG, pick WebP.

**Video compress is slow:** depends on length and resolution.

## Remotes

- GitHub: https://github.com/leoxiaoyg/local-tools  
- Gitee: https://gitee.com/xyg-dev/local-tools  

Publish checklist (Chinese): [docs/05-project/github-publish-checklist.md](docs/05-project/github-publish-checklist.md).
