"""命令行入口。与 Web 共用 handler，不经 HTTP。"""

from __future__ import annotations

import argparse
import glob
import json
import shutil
import sys
from pathlib import Path

from app.batch import run_batch
from app.exif_tools import inspect_exif, strip_exif
from app.i18n import detect_cli_lang, translate_text
from app.image_compressor import OUTPUT_FORMATS, compress_image
from app.image_transform import EXPORT_FORMATS, transform_image
from app.pdf_tools import compress_pdf, merge_pdfs, split_pdf

HELP = {
    "zh": {
        "prog": "本地处理图片与 PDF，不经 HTTP。",
        "lang": "界面语言（默认跟系统；也可用 LT_LANG）",
        "inputs": "输入文件，支持通配符",
        "output": "输出路径：单文件写文件，多文件写 zip；目录则逐个写出",
        "format_image": "输出格式",
        "mode": "压缩模式",
        "target": "目标体积上限（KB），mode=target 时必填",
        "width": "宽度（px）",
        "height": "高度（px）",
        "resize": "缩放方式",
        "json": "以 JSON 输出",
        "preset": "压缩强度",
        "split_mode": "拆分方式：pages 按页打包 zip，range 提取页码",
        "pages": "页码范围，例如 1-3,5",
        "image": "图片工具",
        "compress": "压缩图片",
        "convert": "转换图片格式 / 尺寸",
        "exif": "EXIF 工具",
        "inspect": "查看拍摄信息",
        "strip": "清除拍摄信息",
        "pdf": "PDF 工具",
        "merge": "合并多个 PDF",
        "pdf_compress": "压缩 PDF",
        "split": "拆分或提取页",
    },
    "en": {
        "prog": "Process images and PDFs locally. Does not use HTTP.",
        "lang": "UI language (defaults to the system; LT_LANG also works)",
        "inputs": "Input files. Globs are allowed",
        "output": "Output path: one file, a zip for many, or a directory",
        "format_image": "Output format",
        "mode": "Compression mode",
        "target": "Size cap in KB (required when mode=target)",
        "width": "Width (px)",
        "height": "Height (px)",
        "resize": "Resize mode",
        "json": "Print JSON",
        "preset": "Compression strength",
        "split_mode": "pages = zip per page; range = extract pages",
        "pages": "Page range, e.g. 1-3,5",
        "image": "Image tools",
        "compress": "Compress images",
        "convert": "Convert format / size",
        "exif": "EXIF tools",
        "inspect": "Show shooting info",
        "strip": "Strip shooting info",
        "pdf": "PDF tools",
        "merge": "Merge PDFs",
        "pdf_compress": "Compress PDFs",
        "split": "Split or extract pages",
    },
}


def _t(lang: str, text: str) -> str:
    return translate_text(text, lang) if lang == "en" else text


def _die(lang: str, text: str, code: int = 1) -> int:
    print(_t(lang, text), file=sys.stderr)
    return code


def collect_paths(items: list[str], lang: str) -> list[Path]:
    found: list[Path] = []
    for item in items:
        if any(ch in item for ch in "*?["):
            matches = [Path(p) for p in sorted(glob.glob(item, recursive=True))]
        else:
            matches = [Path(item)]
        if not matches:
            raise ValueError(f"找不到文件: {item}")
        for path in matches:
            if not path.exists():
                raise ValueError(f"找不到文件: {path}")
            if not path.is_file():
                raise ValueError(f"不是文件: {path}")
            found.append(path)
    if not found:
        raise ValueError("请选择文件")
    return found


def read_files(paths: list[Path]) -> list[tuple[bytes, str]]:
    return [(path.read_bytes(), path.name) for path in paths]


def resolve_dest(output: str | None, *, single_name: str, default_zip: str, count: int) -> Path:
    if output:
        dest = Path(output)
        if dest.exists() and dest.is_dir():
            return dest / (single_name if count == 1 else default_zip)
        if count > 1 and dest.suffix.lower() != ".zip" and not dest.exists():
            dest.mkdir(parents=True, exist_ok=True)
            return dest / default_zip
        return dest
    if count == 1:
        return Path.cwd() / single_name
    return Path.cwd() / default_zip


def write_bytes(dest: Path, data: bytes) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def write_path(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.copyfile(src, dest)
        src.unlink(missing_ok=True)
    return dest


def write_batch_dir(files: list[tuple[bytes, str]], handler, dest_dir: Path) -> tuple[int, int]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    fail = 0
    used: set[str] = set()
    for data, name in files:
        try:
            result = handler(data, name)
            out_name = Path(result.filename).name
            if out_name in used:
                stem, suffix = Path(out_name).stem, Path(out_name).suffix
                index = 2
                while f"{stem}_{index}{suffix}" in used:
                    index += 1
                out_name = f"{stem}_{index}{suffix}"
            used.add(out_name)
            write_path(result.path, dest_dir / out_name)
            ok += 1
        except Exception as exc:
            fail += 1
            print(f"{Path(name).name}\t{exc}", file=sys.stderr)
    if not ok:
        raise ValueError("全部文件处理失败。")
    return ok, fail


def report_written(lang: str, dest: Path, extra: str = "") -> int:
    line = _t(lang, f"已写入 {dest}")
    if extra:
        line = f"{line} · {extra}"
    print(line)
    return 0


def cmd_image_compress(args: argparse.Namespace) -> int:
    lang = args.lang
    try:
        paths = collect_paths(args.inputs, lang)
        files = read_files(paths)
        if args.mode == "target" and not args.target_kb:
            return _die(lang, "指定体积模式需要填写目标上限（KB）")

        def handle(data: bytes, name: str):
            return compress_image(
                data,
                name,
                mode=args.mode,
                target_kb=args.target_kb,
                output_format=args.format,
            )

        if len(files) == 1:
            result = handle(*files[0])
            dest = resolve_dest(args.output, single_name=result.filename, default_zip="compressed-images.zip", count=1)
            write_path(result.path, dest)
            extra = _t(lang, result.message) if result.message else ""
            return report_written(lang, dest, extra)

        if args.output and Path(args.output).is_dir():
            ok, fail = write_batch_dir(files, handle, Path(args.output))
            return report_written(lang, Path(args.output), _t(lang, f"成功 {ok} · 失败 {fail}"))

        dest = resolve_dest(args.output, single_name="compressed.jpg", default_zip="compressed-images.zip", count=len(files))
        batch = run_batch(files, lambda data, name: _handler_file(handle, data, name), zip_name=dest.name)
        write_path(batch.zip_path, dest)
        extra = _t(lang, f"成功 {len(batch.ok)} · 失败 {len(batch.errors)}")
        return report_written(lang, dest, extra)
    except Exception as exc:
        return _die(lang, str(exc))


def _handler_file(handle, data: bytes, name: str):
    result = handle(data, name)
    return result.path, result.filename


def cmd_image_convert(args: argparse.Namespace) -> int:
    lang = args.lang
    try:
        paths = collect_paths(args.inputs, lang)
        files = read_files(paths)

        def handle(data: bytes, name: str):
            return transform_image(
                data,
                name,
                output_format=args.format,
                width=str(args.width or ""),
                height=str(args.height or ""),
                resize_mode=args.resize,
            )

        if len(files) == 1:
            result = handle(*files[0])
            dest = resolve_dest(args.output, single_name=result.filename, default_zip="converted-images.zip", count=1)
            write_path(result.path, dest)
            extra = _t(lang, f"输出尺寸：{result.width} × {result.height} px")
            return report_written(lang, dest, extra)

        dest = resolve_dest(args.output, single_name="converted.jpg", default_zip="converted-images.zip", count=len(files))
        if args.output and Path(args.output).is_dir():
            ok, fail = write_batch_dir(files, handle, Path(args.output))
            return report_written(lang, Path(args.output), _t(lang, f"成功 {ok} · 失败 {fail}"))

        batch = run_batch(files, lambda data, name: _handler_file(handle, data, name), zip_name=dest.name)
        write_path(batch.zip_path, dest)
        return report_written(lang, dest, _t(lang, f"成功 {len(batch.ok)} · 失败 {len(batch.errors)}"))
    except Exception as exc:
        return _die(lang, str(exc))


def cmd_exif_inspect(args: argparse.Namespace) -> int:
    lang = args.lang
    try:
        paths = collect_paths(args.inputs, lang)
        reports = []
        for path in paths:
            data = inspect_exif(path.read_bytes(), path.name)
            reports.append(data)
            if args.json:
                continue
            bits = [f"{data['width']} × {data['height']}", data["format"]]
            if data.get("has_gps"):
                bits.append(_t(lang, "含 GPS 位置"))
            if data.get("sensitive_count"):
                bits.append(_t(lang, f"{data['sensitive_count']} 项敏感信息"))
            elif not data.get("has_exif"):
                bits.append(_t(lang, "未发现拍摄信息"))
            print(f"{path.name}  " + " · ".join(bits))
            for item in data.get("fields") or []:
                mark = "!" if item.get("sensitive") else " "
                print(f"  {mark} {item['key']}: {item['value']}")
        if args.json:
            print(json.dumps(reports if len(reports) > 1 else reports[0], ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        return _die(lang, str(exc))


def cmd_exif_strip(args: argparse.Namespace) -> int:
    lang = args.lang
    try:
        paths = collect_paths(args.inputs, lang)
        files = read_files(paths)

        def handle(data: bytes, name: str):
            return strip_exif(data, name)

        if len(files) == 1:
            result = handle(*files[0])
            dest = resolve_dest(args.output, single_name=result.filename, default_zip="images-noexif.zip", count=1)
            write_path(result.path, dest)
            return report_written(lang, dest, _t(lang, result.message))

        dest = resolve_dest(args.output, single_name="noexif.jpg", default_zip="images-noexif.zip", count=len(files))
        if args.output and Path(args.output).is_dir():
            ok, fail = write_batch_dir(files, handle, Path(args.output))
            return report_written(lang, Path(args.output), _t(lang, f"成功 {ok} · 失败 {fail}"))

        batch = run_batch(files, lambda data, name: _handler_file(handle, data, name), zip_name=dest.name)
        write_path(batch.zip_path, dest)
        return report_written(lang, dest, _t(lang, f"成功 {len(batch.ok)} · 失败 {len(batch.errors)}"))
    except Exception as exc:
        return _die(lang, str(exc))


def cmd_pdf_merge(args: argparse.Namespace) -> int:
    lang = args.lang
    try:
        paths = collect_paths(args.inputs, lang)
        if len(paths) < 2:
            return _die(lang, "合并至少需要 2 个 PDF")
        result = merge_pdfs(read_files(paths))
        dest = Path(args.output) if args.output else Path.cwd() / result.filename
        if dest.exists() and dest.is_dir():
            dest = dest / result.filename
        write_path(result.path, dest)
        return report_written(lang, dest, _t(lang, result.message))
    except Exception as exc:
        return _die(lang, str(exc))


def cmd_pdf_compress(args: argparse.Namespace) -> int:
    lang = args.lang
    try:
        paths = collect_paths(args.inputs, lang)
        files = read_files(paths)

        def handle(data: bytes, name: str):
            return compress_pdf(data, name, preset=args.preset)

        if len(files) == 1:
            result = handle(*files[0])
            dest = resolve_dest(args.output, single_name=result.filename, default_zip="compressed-pdfs.zip", count=1)
            write_path(result.path, dest)
            return report_written(lang, dest, _t(lang, result.message))

        dest = resolve_dest(args.output, single_name="compressed.pdf", default_zip="compressed-pdfs.zip", count=len(files))
        if args.output and Path(args.output).is_dir():
            ok, fail = write_batch_dir(files, handle, Path(args.output))
            return report_written(lang, Path(args.output), _t(lang, f"成功 {ok} · 失败 {fail}"))

        batch = run_batch(files, lambda data, name: _handler_file(handle, data, name), zip_name=dest.name)
        write_path(batch.zip_path, dest)
        return report_written(lang, dest, _t(lang, f"成功 {len(batch.ok)} · 失败 {len(batch.errors)}"))
    except Exception as exc:
        return _die(lang, str(exc))


def cmd_pdf_split(args: argparse.Namespace) -> int:
    lang = args.lang
    try:
        paths = collect_paths(args.inputs, lang)
        if len(paths) != 1:
            return _die(lang, "该转换类型仅支持单个文件")
        if args.mode == "range" and not (args.pages or "").strip():
            return _die(lang, "提取页码范围时请使用 --pages，例如 1-3,5")
        src = paths[0]
        result = split_pdf(src.read_bytes(), src.name, mode=args.mode, ranges=args.pages or "")
        dest = Path(args.output) if args.output else Path.cwd() / result.filename
        if dest.exists() and dest.is_dir():
            dest = dest / result.filename
        write_path(result.path, dest)
        return report_written(lang, dest, _t(lang, result.message))
    except Exception as exc:
        return _die(lang, str(exc))


def build_parser(lang: str) -> argparse.ArgumentParser:
    text = HELP[lang]
    lang_parent = argparse.ArgumentParser(add_help=False)
    lang_parent.add_argument("--lang", choices=("zh", "en"), default=lang, help=text["lang"])
    parser = argparse.ArgumentParser(prog="python -m app", description=text["prog"], parents=[lang_parent])
    groups = parser.add_subparsers(dest="group", required=True)

    image = groups.add_parser("image", help=text["image"], parents=[lang_parent])
    image_cmds = image.add_subparsers(dest="cmd", required=True)

    compress = image_cmds.add_parser("compress", help=text["compress"], parents=[lang_parent])
    compress.add_argument("inputs", nargs="+", help=text["inputs"])
    compress.add_argument("-o", "--output", help=text["output"])
    compress.add_argument("--format", choices=list(OUTPUT_FORMATS), default="auto", help=text["format_image"])
    compress.add_argument("--mode", choices=("smart", "target"), default="smart", help=text["mode"])
    compress.add_argument("--target-kb", type=int, default=None, help=text["target"])
    compress.set_defaults(func=cmd_image_compress)

    convert = image_cmds.add_parser("convert", help=text["convert"], parents=[lang_parent])
    convert.add_argument("inputs", nargs="+", help=text["inputs"])
    convert.add_argument("-o", "--output", help=text["output"])
    convert.add_argument("--format", choices=list(EXPORT_FORMATS), default="jpeg", help=text["format_image"])
    convert.add_argument("--width", type=int, default=None, help=text["width"])
    convert.add_argument("--height", type=int, default=None, help=text["height"])
    convert.add_argument("--resize", choices=("fit", "fill", "exact"), default="fit", help=text["resize"])
    convert.set_defaults(func=cmd_image_convert)

    exif = groups.add_parser("exif", help=text["exif"], parents=[lang_parent])
    exif_cmds = exif.add_subparsers(dest="cmd", required=True)

    inspect = exif_cmds.add_parser("inspect", help=text["inspect"], parents=[lang_parent])
    inspect.add_argument("inputs", nargs="+", help=text["inputs"])
    inspect.add_argument("--json", action="store_true", help=text["json"])
    inspect.set_defaults(func=cmd_exif_inspect)

    strip = exif_cmds.add_parser("strip", help=text["strip"], parents=[lang_parent])
    strip.add_argument("inputs", nargs="+", help=text["inputs"])
    strip.add_argument("-o", "--output", help=text["output"])
    strip.set_defaults(func=cmd_exif_strip)

    pdf = groups.add_parser("pdf", help=text["pdf"], parents=[lang_parent])
    pdf_cmds = pdf.add_subparsers(dest="cmd", required=True)

    merge = pdf_cmds.add_parser("merge", help=text["merge"], parents=[lang_parent])
    merge.add_argument("inputs", nargs="+", help=text["inputs"])
    merge.add_argument("-o", "--output", help=text["output"])
    merge.set_defaults(func=cmd_pdf_merge)

    pdf_compress = pdf_cmds.add_parser("compress", help=text["pdf_compress"], parents=[lang_parent])
    pdf_compress.add_argument("inputs", nargs="+", help=text["inputs"])
    pdf_compress.add_argument("-o", "--output", help=text["output"])
    pdf_compress.add_argument("--preset", choices=("light", "standard", "strong"), default="standard", help=text["preset"])
    pdf_compress.set_defaults(func=cmd_pdf_compress)

    split = pdf_cmds.add_parser("split", help=text["split"], parents=[lang_parent])
    split.add_argument("inputs", nargs="+", help=text["inputs"])
    split.add_argument("-o", "--output", help=text["output"])
    split.add_argument("--mode", choices=("pages", "range"), default="pages", help=text["split_mode"])
    split.add_argument("--pages", default="", help=text["pages"])
    split.set_defaults(func=cmd_pdf_split)

    return parser


def _ensure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8()
    raw = list(sys.argv[1:] if argv is None else argv)
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang", choices=("zh", "en"), default=None)
    known, _ = pre.parse_known_args(raw)
    lang = detect_cli_lang(known.lang)
    parser = build_parser(lang)
    try:
        args = parser.parse_args(raw)
    except SystemExit as exc:
        return int(exc.code or 0)
    args.lang = detect_cli_lang(getattr(args, "lang", None))
    return args.func(args)
