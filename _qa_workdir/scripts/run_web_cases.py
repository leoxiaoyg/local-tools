"""按 docs/04-testing/v1-web-cases.md 用 Playwright 模拟浏览器操作。"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
WORK = ROOT / "_qa_workdir"
FIX = WORK / "fixtures"
OUT = WORK / "outputs" / "web"
REPORT_DIR = WORK / "reports"
DOCS_REPORT = ROOT / "docs" / "04-testing" / "reports" / "2026-10-26-v1-web-report.md"


@dataclass
class Row:
    seq: str
    module: str
    item: str
    inputs: str
    outputs: str
    passed: str
    note: str = ""


def ensure_fixtures() -> None:
    if not (FIX / "a.jpg").exists():
        subprocess.check_call([PY, str(WORK / "scripts" / "gen_fixtures.py")], cwd=ROOT)


def pdf_pages(path: Path) -> int:
    doc = fitz.open(path)
    try:
        return doc.page_count
    finally:
        doc.close()


def pdf_needs_password(path: Path) -> bool:
    doc = fitz.open(path)
    try:
        return bool(doc.needs_pass)
    finally:
        doc.close()


def write_report(rows: list[Row], path: Path, base: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for r in rows if r.passed == "通过")
    failed = sum(1 for r in rows if r.passed == "失败")
    lines = [
        "# v1 Web 测试报告",
        "",
        f"- 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 用例文档：`docs/04-testing/v1-web-cases.md`",
        f"- 被测服务：`{base}`",
        f"- 工作目录：`_qa_workdir/`",
        f"- 合计：{len(rows)} · 通过：{passed} · 失败：{failed}",
        "",
        "| 序号 | 测试模块 | 测试项 | 输入项 | 输出项 | 是否通过 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r.seq} | {r.module} | {r.item} | {r.inputs} | {r.outputs} | {r.passed} |")
    lines.extend(["", "## 明细", ""])
    for r in rows:
        lines.append(f"### {r.seq} {r.item} — {r.passed}")
        lines.append(f"- 输入：{r.inputs}")
        lines.append(f"- 输出：{r.outputs}")
        if r.note:
            lines.append(f"- 备注：{r.note}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("需要先安装：pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    ensure_fixtures()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[Row] = []

    def add(seq, module, item, inputs, outputs, passed, note=""):
        rows.append(Row(seq, module, item, inputs, outputs, "通过" if passed else "失败", note))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True, locale="zh-CN")
        page = context.new_page()

        # W01
        try:
            page.goto(f"{base}/", wait_until="domcontentloaded", timeout=30000)
            body = page.inner_text("body")
            ok = all(x in body for x in ("图片", "文档", "视频")) and "watermark.html" in page.content()
            add("W01", "首页", "工具入口可见", "无", "首页 DOM 含分组与入口", ok, body[:120].replace("\n", " "))
        except Exception as exc:
            add("W01", "首页", "工具入口可见", "无", str(exc), False, str(exc))

        # W02 image compress
        try:
            page.goto(f"{base}/image.html", wait_until="domcontentloaded")
            page.set_input_files("#fileInput", str(FIX / "a.jpg"))
            page.wait_for_function("() => !document.getElementById('compressBtn').disabled")
            page.click("#compressBtn")
            page.wait_for_selector("#resultBox:not(.hidden)", timeout=60000)
            with page.expect_download(timeout=30000) as dl_info:
                page.click("#downloadLink")
            download = dl_info.value
            target = OUT / f"w02_{download.suggested_filename or 'out.jpg'}"
            download.save_as(str(target))
            add("W02", "图片压缩", "单张压缩并下载", "fixtures/a.jpg", str(target.relative_to(ROOT)),
                target.exists() and target.stat().st_size > 0, f"size={target.stat().st_size if target.exists() else 0}")
        except Exception as exc:
            add("W02", "图片压缩", "单张压缩并下载", "fixtures/a.jpg", str(exc), False, str(exc))

        # W03 watermark position
        try:
            page.goto(f"{base}/watermark.html", wait_until="domcontentloaded")
            page.set_input_files("#fileInput", str(FIX / "a.jpg"))
            page.fill("#textInput", "测试店")
            page.select_option("#positionSelect", "bottom-right")
            if page.is_checked("#tileInput"):
                page.uncheck("#tileInput")
            page.wait_for_function("() => !document.getElementById('submitBtn').disabled")
            page.click("#submitBtn")
            page.wait_for_selector("#resultBox:not(.hidden)", timeout=60000)
            meta = page.inner_text("#resultMeta") if page.locator("#resultMeta").count() else ""
            with page.expect_download(timeout=30000) as dl_info:
                page.click("#downloadLink")
            download = dl_info.value
            target = OUT / "w03_wm.jpg"
            download.save_as(str(target))
            add("W03", "文字水印", "右下单点水印", "a.jpg + 测试店", str(target.relative_to(ROOT)),
                target.exists() and target.stat().st_size > 0, meta[:120])
        except Exception as exc:
            add("W03", "文字水印", "右下单点水印", "a.jpg + 测试店", str(exc), False, str(exc))

        # W04 tile
        try:
            page.goto(f"{base}/watermark.html", wait_until="domcontentloaded")
            page.set_input_files("#fileInput", str(FIX / "a.jpg"))
            page.fill("#textInput", "铺满")
            page.check("#tileInput")
            page.wait_for_function("() => !document.getElementById('submitBtn').disabled")
            page.click("#submitBtn")
            page.wait_for_selector("#resultBox:not(.hidden)", timeout=60000)
            meta = page.inner_text("#resultMeta") if page.locator("#resultMeta").count() else ""
            pos_hidden = page.locator("#positionField.hidden").count() > 0 or not page.locator("#positionField").is_visible()
            with page.expect_download(timeout=30000) as dl_info:
                page.click("#downloadLink")
            download = dl_info.value
            target = OUT / "w04_tile.jpg"
            download.save_as(str(target))
            ok = target.exists() and target.stat().st_size > 0 and pos_hidden
            add("W04", "文字水印", "斜向平铺", "a.jpg + tile", str(target.relative_to(ROOT)), ok,
                f"pos_hidden={pos_hidden}; meta={meta[:80]}")
        except Exception as exc:
            add("W04", "文字水印", "斜向平铺", "a.jpg + tile", str(exc), False, str(exc))

        # W05 EXIF
        try:
            page.goto(f"{base}/exif.html", wait_until="domcontentloaded")
            page.set_input_files("#fileInput", str(FIX / "a_exif.jpg"))
            page.wait_for_selector("#exifPanel:not(.hidden), #exifSummary", timeout=30000)
            page.wait_for_function("() => !document.getElementById('submitBtn').disabled")
            page.click("#submitBtn")
            page.wait_for_selector("#resultBox:not(.hidden)", timeout=60000)
            with page.expect_download(timeout=30000) as dl_info:
                page.click("#downloadLink")
            download = dl_info.value
            target = OUT / "w05_clean.jpg"
            download.save_as(str(target))
            add("W05", "EXIF", "清除并下载", "a_exif.jpg", str(target.relative_to(ROOT)),
                target.exists() and target.stat().st_size > 0)
        except Exception as exc:
            add("W05", "EXIF", "清除并下载", "a_exif.jpg", str(exc), False, str(exc))

        # W06 PDF merge
        try:
            page.goto(f"{base}/pdf.html", wait_until="domcontentloaded")
            page.select_option("#actionSelect", "merge")
            page.set_input_files("#fileInput", [str(FIX / "one.pdf"), str(FIX / "two.pdf")])
            page.wait_for_function("() => !document.getElementById('submitBtn').disabled")
            page.click("#submitBtn")
            page.wait_for_selector("#resultBox:not(.hidden)", timeout=60000)
            with page.expect_download(timeout=30000) as dl_info:
                page.click("#downloadLink")
            download = dl_info.value
            target = OUT / "w06_merged.pdf"
            download.save_as(str(target))
            pages = pdf_pages(target) if target.exists() else 0
            add("W06", "PDF", "合并两个 PDF", "one.pdf + two.pdf", str(target.relative_to(ROOT)),
                pages >= 2, f"pages={pages}")
        except Exception as exc:
            add("W06", "PDF", "合并两个 PDF", "one.pdf + two.pdf", str(exc), False, str(exc))

        # W07 encrypt
        try:
            page.goto(f"{base}/pdf.html", wait_until="domcontentloaded")
            page.select_option("#actionSelect", "encrypt")
            page.wait_for_selector("#encryptFields:not(.hidden)")
            page.set_input_files("#fileInput", str(FIX / "one.pdf"))
            page.fill("#userPwInput", "secret")
            page.wait_for_function("() => !document.getElementById('submitBtn').disabled")
            page.click("#submitBtn")
            page.wait_for_selector("#resultBox:not(.hidden)", timeout=60000)
            with page.expect_download(timeout=30000) as dl_info:
                page.click("#downloadLink")
            download = dl_info.value
            target = OUT / "w07_locked.pdf"
            download.save_as(str(target))
            needs = pdf_needs_password(target) if target.exists() else False
            add("W07", "PDF", "加密", "one.pdf + secret", str(target.relative_to(ROOT)),
                target.exists() and needs, f"needs_pass={needs}")
        except Exception as exc:
            add("W07", "PDF", "加密", "one.pdf + secret", str(exc), False, str(exc))

        # W08 CSV
        try:
            page.goto(f"{base}/csv-clean.html", wait_until="domcontentloaded")
            page.set_input_files("#fileInput", str(FIX / "dirty.csv"))
            page.check("#dropEmpty")
            page.check("#dedupe")
            page.fill("#keepInput", "sku,name")
            page.wait_for_function("() => !document.getElementById('submitBtn').disabled")
            page.click("#submitBtn")
            page.wait_for_selector("#resultBox:not(.hidden)", timeout=60000)
            with page.expect_download(timeout=30000) as dl_info:
                page.click("#downloadLink")
            download = dl_info.value
            target = OUT / "w08.csv"
            download.save_as(str(target))
            text = target.read_text(encoding="utf-8-sig") if target.exists() else ""
            lines = [ln for ln in text.splitlines() if ln.strip()]
            ok = lines[:1] == ["sku,name"] and "extra" not in text and lines.count("A1,苹果") == 1
            add("W08", "CSV 清洗", "去空行去重留列", "dirty.csv + sku,name", str(target.relative_to(ROOT)),
                ok, repr(text[:100]))
        except Exception as exc:
            add("W08", "CSV 清洗", "去空行去重留列", "dirty.csv", str(exc), False, str(exc))

        # W09 history
        try:
            page.goto(f"{base}/", wait_until="domcontentloaded")
            empty_hidden = page.locator("#historyEmpty.hidden").count() > 0
            list_visible = page.locator("#historyList:not(.hidden) li").count() > 0
            text = page.inner_text("#historyList") if list_visible else page.inner_text("#historyEmpty")
            ok = empty_hidden or list_visible or ("水印" in text) or ("历史" not in text and len(text) > 0)
            # Prefer real list after W03
            ok = list_visible or empty_hidden and "还没有" not in page.inner_text("body")
            list_count = page.locator("#historyList li").count()
            ok = list_count > 0
            add("W09", "本地历史", "处理后首页有记录", "前置 W03", f"historyList count={list_count}", ok, text[:120].replace("\n", " "))
        except Exception as exc:
            add("W09", "本地历史", "处理后首页有记录", "前置 W03", str(exc), False, str(exc))

        # W10 button disabled
        try:
            page.goto(f"{base}/watermark.html", wait_until="domcontentloaded")
            disabled = page.is_disabled("#submitBtn")
            add("W10", "边界", "未选文件时按钮禁用", "无文件", f"submitBtn.disabled={disabled}", disabled)
        except Exception as exc:
            add("W10", "边界", "未选文件时按钮禁用", "无文件", str(exc), False, str(exc))

        browser.close()

    report = REPORT_DIR / "v1-web-report.md"
    write_report(rows, report, base)
    write_report(rows, DOCS_REPORT, base)
    csv_path = REPORT_DIR / "v1-web-report.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["序号", "测试模块", "测试项", "输入项", "输出项", "是否通过"])
        for row in rows:
            writer.writerow([row.seq, row.module, row.item, row.inputs, row.outputs, row.passed])

    print(f"WEB_REPORT {report}")
    print(f"PASS {sum(1 for r in rows if r.passed == '通过')}/{len(rows)}")
    failed = [r for r in rows if r.passed != "通过"]
    for row in failed:
        print(f"FAIL {row.seq} {row.item}: {row.note or row.outputs}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
