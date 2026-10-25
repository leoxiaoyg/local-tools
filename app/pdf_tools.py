"""PDF 合并 / 压缩 / 拆分（PyMuPDF）。加密留到下一迭代。"""

from __future__ import annotations

import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import fitz

MAX_PDF_BYTES = 80 * 1024 * 1024
MAX_MERGE_FILES = 30
MAX_MERGE_TOTAL_BYTES = 200 * 1024 * 1024
MAX_SPLIT_PAGES = 400

COMPRESS_PRESETS = {
    "light": {
        "label": "轻度（清理冗余，尽量保真）",
        "rewrite": False,
    },
    "standard": {
        "label": "标准（重压较大图片）",
        "rewrite": True,
        "dpi_threshold": 150,
        "dpi_target": 120,
        "quality": 70,
    },
    "strong": {
        "label": "强力（更小体积，画质下降更明显）",
        "rewrite": True,
        "dpi_threshold": 110,
        "dpi_target": 96,
        "quality": 50,
    },
}


@dataclass
class PdfResult:
    path: Path
    filename: str
    mime: str
    original_size: int
    output_size: int
    message: str
    pages: int = 0


def list_compress_presets() -> list[dict]:
    return [{"id": key, "label": meta["label"]} for key, meta in COMPRESS_PRESETS.items()]


def merge_pdfs(files: list[tuple[bytes, str]]) -> PdfResult:
    if len(files) < 2:
        raise ValueError("合并至少需要 2 个 PDF")
    if len(files) > MAX_MERGE_FILES:
        raise ValueError(f"一次最多合并 {MAX_MERGE_FILES} 个文件")

    total = sum(len(data) for data, _ in files)
    if total > MAX_MERGE_TOTAL_BYTES:
        raise ValueError("文件总大小超过上限（最大 200MB）")

    merged = fitz.open()
    page_count = 0
    try:
        for data, name in files:
            _ensure_pdf_name(name)
            _ensure_size(data, name)
            src = _open_pdf(data, name)
            try:
                merged.insert_pdf(src)
                page_count += src.page_count
            finally:
                src.close()

        stem = Path(files[0][1]).stem or "merged"
        out_name = f"{stem}_merged.pdf"
        path = _save_document(merged)
    finally:
        merged.close()

    return PdfResult(
        path=path,
        filename=out_name,
        mime="application/pdf",
        original_size=total,
        output_size=path.stat().st_size,
        message=f"已合并 {len(files)} 个文件，共 {page_count} 页",
        pages=page_count,
    )


def compress_pdf(content: bytes, filename: str, preset: str = "standard") -> PdfResult:
    _ensure_pdf_name(filename)
    _ensure_size(content, filename)
    if preset not in COMPRESS_PRESETS:
        raise ValueError(f"不支持的压缩强度: {preset}")

    doc = _open_pdf(content, filename)
    try:
        if COMPRESS_PRESETS[preset]["rewrite"]:
            try:
                doc.rewrite_images(
                    dpi_threshold=COMPRESS_PRESETS[preset]["dpi_threshold"],
                    dpi_target=COMPRESS_PRESETS[preset]["dpi_target"],
                    quality=COMPRESS_PRESETS[preset]["quality"],
                )
            except Exception:
                # 个别 PDF 重写图片会失败，退回仅做结构压缩
                pass

        stem = Path(filename).stem or "document"
        out_name = f"{stem}_compressed.pdf"
        path = _save_document(doc)
        pages = doc.page_count
    finally:
        doc.close()

    output_size = path.stat().st_size
    if output_size >= len(content):
        path.unlink(missing_ok=True)
        path = _write_bytes(content, ".pdf")
        message = "当前文件已较紧凑，保持原文件"
        output_size = len(content)
        out_name = Path(filename).name
    else:
        reduced = (1 - output_size / len(content)) * 100
        message = f"已压缩 {reduced:.1f}%（{COMPRESS_PRESETS[preset]['label']}）"

    return PdfResult(
        path=path,
        filename=out_name,
        mime="application/pdf",
        original_size=len(content),
        output_size=output_size,
        message=message,
        pages=pages,
    )


def split_pdf(
    content: bytes,
    filename: str,
    mode: str = "pages",
    ranges: str = "",
) -> PdfResult:
    _ensure_pdf_name(filename)
    _ensure_size(content, filename)
    doc = _open_pdf(content, filename)
    stem = Path(filename).stem or "document"

    try:
        if mode == "range":
            indices = _parse_page_ranges(ranges, doc.page_count)
            extracted = fitz.open()
            try:
                for index in indices:
                    extracted.insert_pdf(doc, from_page=index, to_page=index)
                path = _save_document(extracted)
            finally:
                extracted.close()
            return PdfResult(
                path=path,
                filename=f"{stem}_p{ranges.replace(' ', '')}.pdf",
                mime="application/pdf",
                original_size=len(content),
                output_size=path.stat().st_size,
                message=f"已提取 {len(indices)} 页",
                pages=len(indices),
            )

        if mode != "pages":
            raise ValueError("拆分方式仅支持按页或页码范围")
        if doc.page_count > MAX_SPLIT_PAGES:
            raise ValueError(f"页数过多（最多 {MAX_SPLIT_PAGES} 页按页拆分）")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            zip_path = Path(tmp.name)

        try:
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                width = max(3, len(str(doc.page_count)))
                for index in range(doc.page_count):
                    one = fitz.open()
                    try:
                        one.insert_pdf(doc, from_page=index, to_page=index)
                        pdf_bytes = one.tobytes(garbage=4, deflate=True)
                    finally:
                        one.close()
                    archive.writestr(f"{stem}_p{index + 1:0{width}d}.pdf", pdf_bytes)
        except Exception:
            zip_path.unlink(missing_ok=True)
            raise

        return PdfResult(
            path=zip_path,
            filename=f"{stem}_pages.zip",
            mime="application/zip",
            original_size=len(content),
            output_size=zip_path.stat().st_size,
            message=f"已拆成 {doc.page_count} 个单页 PDF",
            pages=doc.page_count,
        )
    finally:
        doc.close()


def _ensure_pdf_name(filename: str) -> None:
    if Path(filename).suffix.lower() != ".pdf":
        raise ValueError(f"请上传 PDF 文件: {Path(filename).name or '未知'}")


def _ensure_size(content: bytes, filename: str) -> None:
    if not content:
        raise ValueError(f"文件为空: {Path(filename).name}")
    if len(content) > MAX_PDF_BYTES:
        raise ValueError(f"{Path(filename).name} 过大，单文件最大 80MB")


def _open_pdf(content: bytes, filename: str) -> fitz.Document:
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"无法读取 PDF: {Path(filename).name}") from exc

    if getattr(doc, "needs_pass", False) or getattr(doc, "is_encrypted", False):
        if not doc.authenticate(""):
            doc.close()
            raise ValueError(f"{Path(filename).name} 已加密，暂不支持（加密/解密将在后续提供）")

    if doc.page_count < 1:
        doc.close()
        raise ValueError(f"{Path(filename).name} 没有有效页面")
    return doc


def _parse_page_ranges(spec: str, page_count: int) -> list[int]:
    cleaned = spec.replace("，", ",").strip()
    if not cleaned:
        raise ValueError("请填写页码范围，例如 1-3,5")

    selected: list[int] = []
    seen: set[int] = set()
    try:
        parts = [part.strip() for part in cleaned.split(",") if part.strip()]
        for part in parts:
            if "-" in part:
                start_text, end_text = part.split("-", 1)
                start, end = int(start_text), int(end_text)
                if start > end:
                    start, end = end, start
                values = range(start, end + 1)
            else:
                values = [int(part)]
            for page in values:
                if page < 1 or page > page_count:
                    raise ValueError(f"页码 {page} 超出范围（共 {page_count} 页）")
                if page not in seen:
                    seen.add(page)
                    selected.append(page - 1)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("页码格式无效，请使用如 1-3,5") from exc

    if not selected:
        raise ValueError("请填写有效页码，例如 1-3,5")
    return selected


def _save_document(doc: fitz.Document) -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        path = Path(tmp.name)
    doc.save(
        path,
        garbage=4,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
        clean=True,
    )
    return path


def _write_bytes(data: bytes, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        return Path(tmp.name)
