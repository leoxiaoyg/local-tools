"""按 docs/04-testing/v1-cli-cases.md 执行 CLI 用例，写出报告到 _qa_workdir/reports。"""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
WORK = ROOT / "_qa_workdir"
FIX = WORK / "fixtures"
OUT = WORK / "outputs" / "cli"
REPORT_DIR = WORK / "reports"
CASES_DOC = ROOT / "docs" / "04-testing" / "v1-cli-cases.md"
DOCS_REPORT = ROOT / "docs" / "04-testing" / "reports" / "2026-10-26-v1-cli-report.md"


@dataclass
class Row:
    seq: str
    module: str
    item: str
    steps: str
    expected: str
    inputs: str
    outputs: str
    passed: str
    actual_output: str = ""


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


def ok(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


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


def ensure_fixtures() -> None:
    if not (FIX / "a.jpg").exists():
        subprocess.check_call([PY, str(WORK / "scripts" / "gen_fixtures.py")], cwd=ROOT)


def write_report(rows: list[Row], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for r in rows if r.passed == "通过")
    failed = sum(1 for r in rows if r.passed == "失败")
    lines = [
        "# v1 CLI 测试报告",
        "",
        f"- 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 用例文档：`docs/04-testing/v1-cli-cases.md`",
        f"- 工作目录：`_qa_workdir/`",
        f"- 合计：{len(rows)} · 通过：{passed} · 失败：{failed}",
        "",
        "| 序号 | 测试模块 | 测试项 | 输入项 | 输出项 | 是否通过 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        out = r.actual_output or r.outputs
        lines.append(
            f"| {r.seq} | {r.module} | {r.item} | {r.inputs} | {out} | {r.passed} |"
        )
    lines.extend(["", "## 明细", ""])
    for r in rows:
        lines.append(f"### {r.seq} {r.item} — {r.passed}")
        lines.append(f"- 预期：{r.expected}")
        lines.append(f"- 实际输出：{r.actual_output or r.outputs}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ensure_fixtures()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[Row] = []

    def add(seq, module, item, steps, expected, inputs, outputs, passed, actual=""):
        rows.append(Row(seq, module, item, steps, expected, inputs, outputs, passed, actual))

    # C01
    r = run(["--help"])
    passed = r.returncode == 0 and all(x in r.stdout for x in ("image", "exif", "pdf", "csv", "video"))
    add("C01", "CLI 入口", "帮助信息", "python -m app --help", "退出 0 且含主命令", "无", "帮助文本",
        "通过" if passed else "失败", r.stdout.splitlines()[0] if r.stdout else r.stderr[:200])

    # C02
    out = OUT / "c02_small.jpg"
    r = run(["image", "compress", str(FIX / "a.jpg"), "-o", str(out)])
    passed = r.returncode == 0 and ok(out)
    add("C02", "图片压缩", "单张压缩", "image compress a.jpg", "产出文件", "fixtures/a.jpg", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"{out.name} size={out.stat().st_size if out.exists() else 0}")

    # C03
    out = OUT / "c03.webp"
    r = run(["image", "convert", str(FIX / "a.jpg"), "--format", "webp", "-o", str(out)])
    passed = r.returncode == 0 and ok(out)
    add("C03", "图片转换", "JPG→WebP", "image convert --format webp", "产出 webp", "fixtures/a.jpg", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"{out.name} size={out.stat().st_size if out.exists() else 0}")

    # C04
    out = OUT / "c04.zip"
    r = run(["image", "compress", str(FIX / "a.jpg"), str(FIX / "b.png"), "-o", str(out)])
    zip_ok = False
    if out.exists():
        with zipfile.ZipFile(out) as zf:
            zip_ok = len(zf.namelist()) >= 1
    passed = r.returncode == 0 and zip_ok
    add("C04", "图片压缩", "批量 zip", "compress 两张图", "zip 可解压", "a.jpg + b.png", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"zip entries={len(zipfile.ZipFile(out).namelist()) if out.exists() else 0}")

    # C05
    out = OUT / "c05_wm.jpg"
    r = run(["image", "watermark", str(FIX / "a.jpg"), "--text", "Shop", "-o", str(out)])
    passed = r.returncode == 0 and ok(out)
    add("C05", "文字水印", "单点位置", "watermark --text Shop", "产出 JPEG", "a.jpg + Shop", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"size={out.stat().st_size if out.exists() else 0}")

    # C06
    out = OUT / "c06_tile.jpg"
    r = run(["image", "watermark", str(FIX / "a.jpg"), "--text", "Shop", "--tile", "-o", str(out)])
    passed = r.returncode == 0 and ok(out)
    add("C06", "文字水印", "斜向平铺", "watermark --tile", "产出 JPEG", "a.jpg + --tile", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"size={out.stat().st_size if out.exists() else 0}")

    # C07
    r = run(["exif", "inspect", str(FIX / "a_exif.jpg"), "--json"])
    data = {}
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        pass
    passed = r.returncode == 0 and "width" in data and "height" in data
    add("C07", "EXIF", "查看", "exif inspect --json", "JSON 含尺寸", "a_exif.jpg", "JSON stdout",
        "通过" if passed else "失败", json.dumps(data, ensure_ascii=False)[:200])

    # C08
    out = OUT / "c08_clean.jpg"
    r = run(["exif", "strip", str(FIX / "a_exif.jpg"), "-o", str(out)])
    inspect = run(["exif", "inspect", str(out), "--json"]) if out.exists() else None
    clean_data = {}
    if inspect and inspect.returncode == 0:
        try:
            clean_data = json.loads(inspect.stdout)
        except json.JSONDecodeError:
            pass
    passed = r.returncode == 0 and ok(out) and clean_data.get("has_gps") is not True
    add("C08", "EXIF", "清除", "exif strip", "产出且无 GPS", "a_exif.jpg", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", json.dumps(clean_data, ensure_ascii=False)[:200])

    # C09
    out = OUT / "c09_merged.pdf"
    r = run(["pdf", "merge", str(FIX / "one.pdf"), str(FIX / "two.pdf"), "-o", str(out)])
    pages = pdf_pages(out) if out.exists() else 0
    passed = r.returncode == 0 and pages >= 2
    add("C09", "PDF", "合并", "pdf merge", "≥2 页", "one.pdf + two.pdf", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"pages={pages}")

    # C10
    out = OUT / "c10.pdf"
    r = run(["pdf", "compress", str(FIX / "one.pdf"), "--preset", "light", "-o", str(out)])
    passed = r.returncode == 0 and ok(out)
    add("C10", "PDF", "压缩", "pdf compress --preset light", "产出 PDF", "one.pdf", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"size={out.stat().st_size if out.exists() else 0}")

    # C11
    src = OUT / "c09_merged.pdf"
    out = OUT / "c11_pages.zip"
    r = run(["pdf", "split", str(src), "--mode", "pages", "-o", str(out)])
    n = 0
    if out.exists():
        with zipfile.ZipFile(out) as zf:
            n = len([name for name in zf.namelist() if name.lower().endswith(".pdf")])
    passed = r.returncode == 0 and n == pdf_pages(src)
    add("C11", "PDF", "按页拆分", "pdf split --mode pages", "zip 页数=源", "c09_merged.pdf", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"pdf_entries={n}")

    # C12
    out = OUT / "c12_locked.pdf"
    r = run(["pdf", "encrypt", str(FIX / "one.pdf"), "--user-pw", "secret", "-o", str(out)])
    passed = r.returncode == 0 and ok(out) and pdf_needs_password(out)
    add("C12", "PDF", "加密", "pdf encrypt --user-pw secret", "需密码", "one.pdf + secret", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"needs_pass={pdf_needs_password(out) if out.exists() else None}")

    # C13
    locked = OUT / "c12_locked.pdf"
    out = OUT / "c13_opened.pdf"
    r = run(["pdf", "decrypt", str(locked), "--password", "secret", "-o", str(out)])
    passed = r.returncode == 0 and ok(out) and not pdf_needs_password(out)
    add("C13", "PDF", "解密", "pdf decrypt --password secret", "无密码可开", "c12_locked.pdf", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"needs_pass={pdf_needs_password(out) if out.exists() else None}")

    # C14
    r = run(["pdf", "decrypt", str(locked), "--password", "nope"], lang="en")
    passed = r.returncode != 0
    add("C14", "PDF", "错误密码", "decrypt 错误密码", "退出非 0", "locked + nope", (r.stderr or r.stdout)[:120],
        "通过" if passed else "失败", (r.stderr or r.stdout)[:200])

    # C15
    out = OUT / "c15.csv"
    r = run(["csv", "clean", str(FIX / "dirty.csv"), "--keep", "sku,name", "-o", str(out)])
    text = out.read_text(encoding="utf-8-sig") if out.exists() else ""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    passed = (
        r.returncode == 0
        and lines[:1] == ["sku,name"]
        and "extra" not in text
        and lines.count("A1,苹果") == 1
        and "B2,香蕉" in text
    )
    add("C15", "CSV 清洗", "去空行/去重/留列", "csv clean --keep sku,name", "仅 sku,name 无重复", "dirty.csv", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", repr(text[:120]))

    # C16
    out = OUT / "c16.mp3"
    r = run(["video", "audio", str(FIX / "clip.mp4"), "--format", "mp3", "-o", str(out)])
    passed = r.returncode == 0 and ok(out)
    add("C16", "视频", "转音频", "video audio --format mp3", "产出 mp3", "clip.mp4", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"size={out.stat().st_size if out.exists() else 0}; err={(r.stderr or '')[:100]}")

    # C17
    out = OUT / "c17.mp4"
    r = run(["video", "compress", str(FIX / "clip.mp4"), "--crf", "28", "--resolution", "480", "-o", str(out)])
    passed = r.returncode == 0 and ok(out)
    add("C17", "视频", "压缩", "video compress crf28 480", "产出 mp4", "clip.mp4", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", f"size={out.stat().st_size if out.exists() else 0}; err={(r.stderr or '')[:100]}")

    # C18
    r = run(["image", "compress", str(FIX / "nope.jpg")], lang="en")
    passed = r.returncode != 0 and "File not found" in (r.stderr + r.stdout)
    add("C18", "边界", "文件不存在", "compress 不存在文件", "File not found", "fixtures/nope.jpg", (r.stderr or r.stdout)[:80],
        "通过" if passed else "失败", (r.stderr or r.stdout)[:200])

    # C19
    out = OUT / "c19.zip"
    r = run(
        ["image", "compress", str(FIX / "a.jpg"), str(FIX / "not_image.txt"), "-o", str(out)],
        lang="en",
    )
    err_txt = ""
    if out.exists():
        with zipfile.ZipFile(out) as zf:
            if "errors.txt" in zf.namelist():
                err_txt = zf.read("errors.txt").decode("utf-8", errors="replace")
    passed = "Failed" in err_txt or "failed" in err_txt.lower() or "Unsupported" in err_txt or "not" in err_txt.lower()
    # Prefer English marker from prior smoke
    if out.exists() and err_txt:
        passed = "# Failed" in err_txt or "Failed items" in err_txt or "failed" in err_txt.lower()
    add("C19", "边界", "批量部分失败", "compress 图+非图", "zip 含 errors.txt 英文", "a.jpg + not_image.txt", str(out.relative_to(ROOT)),
        "通过" if passed else "失败", err_txt[:200] or (r.stderr or r.stdout)[:200])

    report = REPORT_DIR / "v1-cli-report.md"
    write_report(rows, report)
    write_report(rows, DOCS_REPORT)

    csv_path = REPORT_DIR / "v1-cli-report.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["序号", "测试模块", "测试项", "输入项", "输出项", "是否通过"])
        for row in rows:
            writer.writerow([row.seq, row.module, row.item, row.inputs, row.actual_output or row.outputs, row.passed])

    failed = [row for row in rows if row.passed != "通过"]
    print(f"CLI_REPORT {report}")
    print(f"PASS {sum(1 for r in rows if r.passed == '通过')}/{len(rows)}")
    if failed:
        for row in failed:
            print(f"FAIL {row.seq} {row.item}: {row.actual_output}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
