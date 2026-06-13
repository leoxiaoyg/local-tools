from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff",
}

OUTPUT_FORMATS = {
    "auto": {"label": "保持原格式"},
    "jpeg": {"label": "JPEG", "pil": "JPEG", "ext": "jpg", "mime": "image/jpeg"},
    "png": {"label": "PNG", "pil": "PNG", "ext": "png", "mime": "image/png"},
    "webp": {"label": "WebP", "pil": "WEBP", "ext": "webp", "mime": "image/webp"},
}

EXT_TO_FORMAT = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".webp": "webp",
    ".bmp": "bmp",
    ".tif": "tiff",
    ".tiff": "tiff",
}


@dataclass
class CompressResult:
    path: Path
    filename: str
    mime: str
    original_size: int
    compressed_size: int
    quality: int | None
    output_format: str
    message: str


@dataclass
class _Candidate:
    data: bytes
    output_format: str
    quality: int | None
    message: str


def _detect_input_format(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in EXT_TO_FORMAT:
        raise ValueError(f"不支持的图片格式: {ext or '未知'}")
    return EXT_TO_FORMAT[ext]


def _resolve_output_format(input_format: str, requested: str) -> str:
    if requested == "auto":
        if input_format in {"jpeg", "png", "webp"}:
            return input_format
        return "jpeg"
    if requested not in OUTPUT_FORMATS or requested == "auto":
        raise ValueError(f"不支持的输出格式: {requested}")
    return requested


def _load_image(content: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(content))
        img = ImageOps.exif_transpose(img)
        return img
    except Exception as exc:
        raise ValueError("无法读取图片，请确认文件是否有效") from exc


def _has_alpha(img: Image.Image) -> bool:
    if img.mode in {"RGBA", "LA"}:
        return True
    if img.mode == "P" and "transparency" in img.info:
        return True
    return False


def _prepare_png(img: Image.Image) -> Image.Image:
    """保留原始色彩模式，避免 RGB 被扩成 RGBA 导致体积膨胀。"""
    if img.mode in {"1", "L", "P", "RGB", "RGBA", "LA"}:
        return img.copy()
    if img.mode == "CMYK":
        return img.convert("RGB")
    return img.convert("RGBA" if _has_alpha(img) else "RGB")


def _prepare_for_format(img: Image.Image, output_format: str) -> Image.Image:
    if output_format == "png":
        return _prepare_png(img)

    if _has_alpha(img):
        if output_format == "webp":
            if img.mode != "RGBA":
                return img.convert("RGBA")
            return img.copy()

        background = Image.new("RGB", img.size, (255, 255, 255))
        source = img.convert("RGBA") if img.mode != "RGBA" else img
        background.paste(source, mask=source.split()[-1])
        return background

    if img.mode != "RGB":
        return img.convert("RGB")
    return img.copy()


def _encode(img: Image.Image, output_format: str, quality: int, lossless: bool = False) -> bytes:
    buf = io.BytesIO()
    pil_format = OUTPUT_FORMATS[output_format]["pil"]

    if output_format == "jpeg":
        img.save(
            buf,
            format=pil_format,
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=0,
        )
    elif output_format == "png":
        img.save(buf, format=pil_format, optimize=True, compress_level=9)
    elif output_format == "webp":
        img.save(
            buf,
            format=pil_format,
            quality=quality,
            method=6,
            lossless=lossless,
        )
    else:
        raise ValueError(f"不支持的输出格式: {output_format}")

    return buf.getvalue()


def _try_encode(img: Image.Image, output_format: str, quality: int, lossless: bool = False) -> _Candidate | None:
    try:
        prepared = _prepare_for_format(img, output_format)
        data = _encode(prepared, output_format, quality, lossless=lossless)
    except Exception:
        return None

    label = "无损" if lossless else str(quality)
    return _Candidate(
        data=data,
        output_format=output_format,
        quality=None if lossless else quality,
        message=f"已使用 {output_format.upper()}（{label}）编码",
    )


def _pick_best(candidates: list[_Candidate], original_size: int) -> _Candidate | None:
    valid = [c for c in candidates if len(c.data) < original_size]
    if not valid:
        return None
    return min(valid, key=lambda c: len(c.data))


def _collect_smart_candidates(
    img: Image.Image,
    resolved_format: str,
    *,
    keep_format: bool,
) -> list[_Candidate]:
    candidates: list[_Candidate] = []

    if resolved_format == "png":
        candidate = _try_encode(img, "png", 95)
        if candidate:
            candidate.message = "已优化 PNG 编码并移除元数据"
            candidates.append(candidate)
        if keep_format:
            return candidates

        for lossless in (True, False):
            candidate = _try_encode(img, "webp", 100, lossless=lossless)
            if candidate:
                candidate.message = (
                    "PNG 重新编码效果有限，已转为 WebP 无损"
                    if lossless
                    else "PNG 重新编码效果有限，已转为 WebP 高画质"
                )
                candidates.append(candidate)

        for quality in (95, 92, 90, 88):
            candidate = _try_encode(img, "webp", quality)
            if candidate:
                candidate.message = f"已转为 WebP 高画质（{quality}），视觉差异极小"
                candidates.append(candidate)
        return candidates

    if resolved_format == "webp":
        for lossless in (True, False):
            candidate = _try_encode(img, "webp", 100, lossless=lossless)
            if candidate:
                candidate.message = "已优化 WebP 编码"
                candidates.append(candidate)
        for quality in (95, 92, 88, 85):
            candidate = _try_encode(img, "webp", quality)
            if candidate:
                candidate.message = f"以 WebP 高画质（{quality}）重新编码"
                candidates.append(candidate)
        return candidates

    for quality in (95, 92, 88, 85):
        candidate = _try_encode(img, "jpeg", quality)
        if candidate:
            candidate.message = f"以 JPEG 高画质（{quality}）重新编码，视觉差异极小"
            candidates.append(candidate)

    if not keep_format and not _has_alpha(img):
        for quality in (95, 92, 90):
            candidate = _try_encode(img, "webp", quality)
            if candidate:
                candidate.message = f"JPEG 优化有限，已转为 WebP 高画质（{quality}）"
                candidates.append(candidate)

    return candidates


def _smart_compress(
    img: Image.Image,
    resolved_format: str,
    original_content: bytes,
    original_size: int,
    input_format: str,
    *,
    keep_format: bool,
) -> _Candidate:
    best = _pick_best(
        _collect_smart_candidates(img, resolved_format, keep_format=keep_format),
        original_size,
    )
    if best:
        return best

    return _Candidate(
        data=original_content,
        output_format=input_format,
        quality=None,
        message="当前图片已足够优化，保持原文件",
    )


def _binary_search_quality(
    img: Image.Image,
    output_format: str,
    target_bytes: int,
    min_quality: int = 60,
    max_quality: int = 98,
) -> tuple[bytes, int]:
    best_data = _encode(_prepare_for_format(img, output_format), output_format, min_quality)
    best_quality = min_quality
    low, high = min_quality, max_quality

    while low <= high:
        mid = (low + high) // 2
        data = _encode(_prepare_for_format(img, output_format), output_format, mid)
        if len(data) <= target_bytes:
            best_data = data
            best_quality = mid
            low = mid + 1
        else:
            high = mid - 1

    return best_data, best_quality


def _target_compress(
    img: Image.Image,
    resolved_format: str,
    original_content: bytes,
    original_size: int,
    target_bytes: int,
    stem: str,
    original_filename: str,
    *,
    keep_format: bool,
) -> tuple[_Candidate, str, str, str]:
    if target_bytes >= original_size:
        return (
            _Candidate(original_content, resolved_format, None, "原图已小于目标体积，无需压缩"),
            f"{stem}_compressed.{OUTPUT_FORMATS.get(resolved_format, {}).get('ext', 'bin')}",
            _guess_mime(resolved_format),
            resolved_format,
        )

    if resolved_format == "png":
        png_data = _encode(_prepare_png(img), "png", 95)
        if len(png_data) <= target_bytes:
            return (
                _Candidate(png_data, "png", None, "已通过 PNG 无损优化达到目标"),
                f"{stem}_compressed.png",
                "image/png",
                "png",
            )

        if keep_format:
            if len(png_data) < original_size:
                message = "无法在保持 PNG 格式下达到目标体积，已输出优化后的 PNG"
                data = png_data
            else:
                message = "无法在保持 PNG 格式下达到目标体积，已保持原文件"
                data = original_content
            return (
                _Candidate(data, "png", None, message),
                f"{stem}_compressed.png" if data is not original_content else original_filename,
                "image/png",
                "png",
            )

        data, quality = _binary_search_quality(
            img, "webp", target_bytes, min_quality=60, max_quality=98
        )
        message = (
            f"PNG 无损无法达到目标，已转为 WebP（画质 {quality}）"
            if len(data) <= target_bytes
            else f"在可接受画质范围内无法压至目标，已输出最小体积版本（WebP {quality}）"
        )
        return (
            _Candidate(data, "webp", quality, message),
            f"{stem}_compressed.webp",
            "image/webp",
            "webp",
        )

    data, quality = _binary_search_quality(img, resolved_format, target_bytes)
    ext = OUTPUT_FORMATS[resolved_format]["ext"]
    message = (
        f"已压至目标体积以内，使用画质 {quality}"
        if len(data) <= target_bytes
        else f"在可接受画质范围内无法压至目标，已输出最小体积版本（画质 {quality}）"
    )
    return (
        _Candidate(data, resolved_format, quality, message),
        f"{stem}_compressed.{ext}",
        OUTPUT_FORMATS[resolved_format]["mime"],
        resolved_format,
    )


def compress_image(
    content: bytes,
    filename: str,
    mode: str = "smart",
    target_kb: int | None = None,
    output_format: str = "auto",
) -> CompressResult:
    if not content:
        raise ValueError("文件为空")

    input_format = _detect_input_format(filename)
    resolved_format = _resolve_output_format(input_format, output_format)
    original_size = len(content)

    img = _load_image(content)
    if getattr(img, "n_frames", 1) > 1:
        raise ValueError("暂不支持动图，请使用静态图片")

    stem = Path(filename).stem or "image"
    keep_format = output_format == "auto"

    if mode == "target":
        if not target_kb or target_kb <= 0:
            raise ValueError("请填写有效的目标体积上限")
        candidate, out_name, mime, final_format = _target_compress(
            img,
            resolved_format,
            content,
            original_size,
            int(target_kb * 1024),
            stem,
            filename,
            keep_format=keep_format,
        )
    else:
        candidate = _smart_compress(
            img,
            resolved_format,
            content,
            original_size,
            input_format,
            keep_format=keep_format,
        )
        if candidate.output_format in OUTPUT_FORMATS and candidate.output_format != input_format:
            ext = OUTPUT_FORMATS[candidate.output_format]["ext"]
            out_name = f"{stem}_compressed.{ext}"
            mime = OUTPUT_FORMATS[candidate.output_format]["mime"]
            final_format = candidate.output_format
        elif candidate.data is content:
            out_name = Path(filename).name
            mime = _guess_mime(input_format)
            final_format = input_format
        else:
            ext = OUTPUT_FORMATS[resolved_format]["ext"]
            out_name = f"{stem}_compressed.{ext}"
            mime = OUTPUT_FORMATS[resolved_format]["mime"]
            final_format = resolved_format

    suffix = Path(out_name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(candidate.data)
        output_path = Path(tmp.name)

    return CompressResult(
        path=output_path,
        filename=out_name,
        mime=mime,
        original_size=original_size,
        compressed_size=len(candidate.data),
        quality=candidate.quality,
        output_format=final_format,
        message=candidate.message,
    )


def _guess_mime(input_format: str) -> str:
    mapping = {
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
    }
    return mapping.get(input_format, "application/octet-stream")
