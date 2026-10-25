"""CLI P0 冒烟。对应 docs/04-testing/cli-smoke.md。在项目根目录执行：python tests/cli_smoke.py"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image
import fitz

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(args: list[str], *, lang: str = "zh") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [PY, "-m", "app", "--lang", lang, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def expect_ok(step: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode != 0:
        raise AssertionError(f"{step} exit {result.returncode}\n{result.stdout}\n{result.stderr}")


def expect_fail(step: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode == 0:
        raise AssertionError(f"{step} expected non-zero\n{result.stdout}")


def make_image(path: Path, color: str) -> None:
    Image.new("RGB", (80, 60), color).save(path, quality=95)


def make_pdf(path: Path, text: str, pages: int = 1) -> None:
    doc = fitz.open()
    for index in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"{text} {index + 1}")
    doc.save(path)
    doc.close()


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="lt-cli-smoke-"))
    try:
        img1 = work / "a.jpg"
        img2 = work / "b.png"
        make_image(img1, "red")
        make_image(img2, "blue")
        pdf1 = work / "one.pdf"
        pdf2 = work / "two.pdf"
        make_pdf(pdf1, "one")
        make_pdf(pdf2, "two")

        help_out = run(["--help"])
        expect_ok("1 help", help_out)
        if "image" not in help_out.stdout or "pdf" not in help_out.stdout:
            raise AssertionError("help missing image/pdf")

        missing = run(["image", "compress", str(work / "nope.jpg")], lang="en")
        expect_fail("2 missing file", missing)
        if "File not found" not in (missing.stderr + missing.stdout):
            raise AssertionError(f"2 expected File not found, got {missing.stderr!r}")

        small = work / "a_small.jpg"
        r = run(["image", "compress", str(img1), "-o", str(small)])
        expect_ok("3 compress", r)
        if not small.exists():
            raise AssertionError("3 no output")
        if "已写入" not in r.stdout and "Wrote" not in r.stdout:
            raise AssertionError(f"3 missing wrote: {r.stdout!r}")

        webp = work / "a.webp"
        r = run(["image", "convert", str(img1), "--format", "webp", "-o", str(webp)])
        expect_ok("4 convert", r)
        if not webp.exists():
            raise AssertionError("4 no webp")

        zipped = work / "imgs.zip"
        r = run(["image", "compress", str(img1), str(img2), "-o", str(zipped)])
        expect_ok("5 batch zip", r)
        with zipfile.ZipFile(zipped) as archive:
            if not archive.namelist():
                raise AssertionError("5 empty zip")

        r = run(["exif", "inspect", str(img1), "--json"], lang="en")
        expect_ok("6 exif inspect", r)
        data = json.loads(r.stdout)
        if data.get("width") != 80 or "has_gps" not in data:
            raise AssertionError(f"6 bad json: {data}")

        clean = work / "a_clean.jpg"
        r = run(["exif", "strip", str(img1), "-o", str(clean)])
        expect_ok("7 exif strip", r)
        if not clean.exists():
            raise AssertionError("7 no clean file")

        merged = work / "merged.pdf"
        r = run(["pdf", "merge", str(pdf1), str(pdf2), "-o", str(merged)])
        expect_ok("8 merge", r)
        doc = fitz.open(merged)
        if doc.page_count < 2:
            doc.close()
            raise AssertionError("8 expected 2 pages")
        doc.close()

        compressed = work / "one_c.pdf"
        r = run(["pdf", "compress", str(pdf1), "--preset", "light", "-o", str(compressed)])
        expect_ok("9 compress pdf", r)
        if not compressed.exists():
            raise AssertionError("9 no compressed pdf")

        pages_zip = work / "pages.zip"
        r = run(["pdf", "split", str(merged), "--mode", "pages", "-o", str(pages_zip)])
        expect_ok("10 split pages", r)
        with zipfile.ZipFile(pages_zip) as archive:
            pdf_entries = [name for name in archive.namelist() if name.lower().endswith(".pdf")]
            if len(pdf_entries) != 2:
                raise AssertionError(f"10 expected 2 pages, got {pdf_entries}")

        page1 = work / "p1.pdf"
        r = run(["pdf", "split", str(merged), "--mode", "range", "--pages", "1", "-o", str(page1)])
        expect_ok("11 extract page", r)
        doc = fitz.open(page1)
        if doc.page_count != 1:
            doc.close()
            raise AssertionError("11 expected 1 page")
        doc.close()

        only_one = run(["pdf", "merge", str(pdf1)])
        expect_fail("12 merge one file", only_one)

        locked = work / "locked.pdf"
        r = run(["pdf", "encrypt", str(pdf1), "--user-pw", "secret", "-o", str(locked)])
        expect_ok("13 encrypt", r)
        locked_doc = fitz.open(locked)
        if not (locked_doc.needs_pass or locked_doc.is_encrypted):
            locked_doc.close()
            raise AssertionError("13 output is not encrypted")
        if not locked_doc.authenticate("secret"):
            locked_doc.close()
            raise AssertionError("13 password rejected")
        locked_doc.close()

        opened = work / "opened.pdf"
        r = run(["pdf", "decrypt", str(locked), "--password", "secret", "-o", str(opened)])
        expect_ok("14 decrypt", r)
        opened_doc = fitz.open(opened)
        if opened_doc.needs_pass:
            opened_doc.close()
            raise AssertionError("14 still locked")
        opened_doc.close()

        wrong = run(["pdf", "decrypt", str(locked), "--password", "nope", "-o", str(work / "bad.pdf")], lang="en")
        expect_fail("15 bad password", wrong)

        marked = work / "a_wm.jpg"
        r = run(["image", "watermark", str(img1), "--text", "Shop", "-o", str(marked)])
        expect_ok("16 watermark", r)
        if not marked.exists() or marked.stat().st_size < 1:
            raise AssertionError("16 no watermarked file")

        print("CLI_SMOKE_OK")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
