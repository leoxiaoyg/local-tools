"""文字水印。Pillow，支持单点位置与斜向平铺；不贴图。"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.image_compressor import (
    IMAGE_EXTENSIONS,
    OUTPUT_FORMATS,
    _detect_input_format,
    _encode,
    _load_image,
    _prepare_for_format,
    _resolve_output_format,
)

MAX_IMAGE_BYTES = 50 * 1024 * 1024
MAX_TEXT_CHARS = 40
POSITIONS = ("bottom-right", "bottom-left", "top-right", "top-left", "center")
DEFAULT_POSITION = "bottom-right"
DEFAULT_OPACITY = 40
DEFAULT_TILE = False

_FONT_CANDIDATES = (
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "msyh.ttc",
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "msyh.ttf",
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "simhei.ttf",
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "simsun.ttc",
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
)


@dataclass
class WatermarkResult:
    path: Path
    filename: str
    mime: str
    original_size: int
    output_size: int
    message: str
    width: int
    height: int


def apply_text_watermark(
    content: bytes,
    filename: str,
    text: str,
    position: str = DEFAULT_POSITION,
    opacity: int = DEFAULT_OPACITY,
    tile: bool = DEFAULT_TILE,
) -> WatermarkResult:
    if not content:
        raise ValueError("文件为空")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError(f"{Path(filename).name} 过大，单文件最大 50MB")
    if Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"不支持的图片格式: {Path(filename).suffix.lower() or '未知'}")

    label = (text or "").strip()
    if not label:
        raise ValueError("请填写水印文字")
    if len(label) > MAX_TEXT_CHARS:
        raise ValueError(f"水印文字最多 {MAX_TEXT_CHARS} 个字")
    if position not in POSITIONS:
        raise ValueError(f"不支持的水印位置: {position}")
    try:
        opacity_pct = int(opacity)
    except (TypeError, ValueError) as exc:
        raise ValueError("透明度请填写 10～100 的整数") from exc
    if opacity_pct < 10 or opacity_pct > 100:
        raise ValueError("透明度请填写 10～100 的整数")

    img = _load_image(content)
    try:
        if getattr(img, "n_frames", 1) > 1:
            raise ValueError("暂不支持动图，请使用静态图片")

        marked = _draw_text(img, label, position, opacity_pct, tile)
        input_format = _detect_input_format(filename)
        output_format = _resolve_output_format(input_format, "auto")
        prepared = _prepare_for_format(marked, output_format)
        quality = 90 if output_format in {"jpeg", "webp"} else 80
        data = _encode(prepared, output_format, quality)

        stem = Path(filename).stem or "image"
        ext = OUTPUT_FORMATS[output_format]["ext"]
        out_name = f"{stem}_wm.{ext}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            path = Path(tmp.name)
            tmp.write(data)
    finally:
        img.close()

    return WatermarkResult(
        path=path,
        filename=out_name,
        mime=OUTPUT_FORMATS[output_format]["mime"],
        original_size=len(content),
        output_size=path.stat().st_size,
        message=_message(position, opacity_pct, tile),
        width=prepared.width,
        height=prepared.height,
    )


def _message(position: str, opacity_pct: int, tile: bool) -> str:
    if tile:
        return f"已加水印（平铺，透明度 {opacity_pct}%）"
    return f"已加水印（{position}，透明度 {opacity_pct}%）"


def _draw_text(
    img: Image.Image,
    text: str,
    position: str,
    opacity_pct: int,
    tile: bool,
) -> Image.Image:
    if tile:
        return _draw_tiled_text(img, text, opacity_pct)
    return _draw_single_text(img, text, position, opacity_pct)


def _draw_single_text(img: Image.Image, text: str, position: str, opacity_pct: int) -> Image.Image:
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    short = min(base.size)
    font_size = max(14, int(short * 0.045))
    font = _load_font(font_size, text)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=max(1, font_size // 18))
    box_w = bbox[2] - bbox[0]
    box_h = bbox[3] - bbox[1]
    margin = max(8, int(short * 0.03))
    x, y = _xy(position, base.size[0], base.size[1], box_w, box_h, margin)

    alpha = int(255 * opacity_pct / 100)
    draw.text(
        (x - bbox[0], y - bbox[1]),
        text,
        font=font,
        fill=(255, 255, 255, alpha),
        stroke_width=max(1, font_size // 18),
        stroke_fill=(20, 20, 20, min(255, alpha + 40)),
    )
    return Image.alpha_composite(base, overlay)


def _draw_tiled_text(img: Image.Image, text: str, opacity_pct: int) -> Image.Image:
    base = img.convert("RGBA")
    width, height = base.size
    short = min(width, height)
    alpha = int(255 * opacity_pct / 100)
    font_size = max(14, min(42, int(short * 0.04)))
    if text:
        font_size = min(font_size, max(14, width // max(8, len(text) * 2)))
    font = _load_font(font_size, text)
    stroke = max(1, font_size // 18)

    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    bbox = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font, stroke_width=stroke)
    box_w = max(1, bbox[2] - bbox[0])
    box_h = max(1, bbox[3] - bbox[1])
    pad = max(8, font_size // 2)
    stamp = Image.new("RGBA", (box_w + pad * 2, box_h + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stamp)
    draw.text(
        (pad - bbox[0], pad - bbox[1]),
        text,
        font=font,
        fill=(255, 255, 255, alpha),
        stroke_width=stroke,
        stroke_fill=(20, 20, 20, min(255, alpha + 40)),
    )
    resample = Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC
    stamp = stamp.rotate(-28, expand=True, resample=resample)
    stamp_w, stamp_h = stamp.size

    step_x = min(max(int(stamp_w * 1.25), 1), max(1, width // 3))
    step_y = min(max(int(stamp_h * 1.15), 1), max(1, height // 3))

    layer = Image.new("RGBA", (width + stamp_w * 2, height + stamp_h * 2), (0, 0, 0, 0))
    row = 0
    y = 0
    while y < layer.size[1]:
        x = 0 if row % 2 == 0 else step_x // 2
        while x < layer.size[0]:
            layer.paste(stamp, (x, y), stamp)
            x += step_x
        y += step_y
        row += 1

    overlay = layer.crop((stamp_w, stamp_h, stamp_w + width, stamp_h + height))
    return Image.alpha_composite(base, overlay)


def _xy(position: str, img_w: int, img_h: int, box_w: int, box_h: int, margin: int) -> tuple[int, int]:
    if position == "top-left":
        return margin, margin
    if position == "top-right":
        return img_w - box_w - margin, margin
    if position == "bottom-left":
        return margin, img_h - box_h - margin
    if position == "center":
        return (img_w - box_w) // 2, (img_h - box_h) // 2
    return img_w - box_w - margin, img_h - box_h - margin


def _needs_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _load_font(size: int, text: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if not path.is_file():
            continue
        try:
            return ImageFont.truetype(str(path), size=size)
        except Exception:
            continue
    if _needs_cjk(text):
        raise ValueError("本机没有可用的中文字体，无法绘制店名水印")
    return ImageFont.load_default()
