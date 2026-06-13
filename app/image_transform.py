import io
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from app.image_compressor import IMAGE_EXTENSIONS, OUTPUT_FORMATS, _prepare_for_format

EXPORT_FORMATS = {
    k: v for k, v in OUTPUT_FORMATS.items() if k != "auto"
}


@dataclass
class TransformResult:
    path: Path
    filename: str
    mime: str
    width: int
    height: int
    output_format: str


def _parse_size(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    size = int(value)
    if size <= 0 or size > 10000:
        raise ValueError("宽高须在 1～10000 之间")
    return size


def transform_image(
    content: bytes,
    filename: str,
    output_format: str = "jpeg",
    width: str = "",
    height: str = "",
    resize_mode: str = "fit",
) -> TransformResult:
    ext = Path(filename).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise ValueError(f"不支持的图片格式: {ext or '未知'}")
    if output_format not in EXPORT_FORMATS:
        raise ValueError(f"不支持的输出格式: {output_format}")

    img = Image.open(io.BytesIO(content))
    img = ImageOps.exif_transpose(img)
    if getattr(img, "n_frames", 1) > 1:
        raise ValueError("暂不支持动图")

    target_w = _parse_size(width)
    target_h = _parse_size(height)

    if target_w or target_h:
        orig_w, orig_h = img.size
        if resize_mode == "exact":
            if not target_w or not target_h:
                raise ValueError("精确缩放需同时填写宽和高")
            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        elif resize_mode == "fill":
            if not target_w or not target_h:
                raise ValueError("裁剪填充需同时填写宽和高")
            img = ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
        else:
            if target_w and target_h:
                img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            elif target_w:
                ratio = target_w / orig_w
                img = img.resize((target_w, max(1, round(orig_h * ratio))), Image.Resampling.LANCZOS)
            else:
                ratio = target_h / orig_h
                img = img.resize((max(1, round(orig_w * ratio)), target_h), Image.Resampling.LANCZOS)

    prepared = _prepare_for_format(img, output_format)
    buf = io.BytesIO()

    if output_format == "jpeg":
        prepared.save(buf, format="JPEG", quality=92, optimize=True, progressive=True)
    elif output_format == "png":
        prepared.save(buf, format="PNG", optimize=True, compress_level=9)
    elif output_format == "webp":
        prepared.save(buf, format="WEBP", quality=90, method=6)
    else:
        raise ValueError(f"不支持的输出格式: {output_format}")

    data = buf.getvalue()
    stem = Path(filename).stem or "image"
    out_ext = EXPORT_FORMATS[output_format]["ext"]
    out_name = f"{stem}_converted.{out_ext}"

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{out_ext}") as tmp:
        tmp.write(data)
        output_path = Path(tmp.name)

    return TransformResult(
        path=output_path,
        filename=out_name,
        mime=EXPORT_FORMATS[output_format]["mime"],
        width=prepared.width,
        height=prepared.height,
        output_format=output_format,
    )
