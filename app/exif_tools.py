"""查看并清除图片 EXIF / GPS 等元数据。免费能力，不得赞助锁定。"""

from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import ExifTags, Image, ImageOps
from PIL.ExifTags import GPSTAGS, TAGS

from app.image_compressor import IMAGE_EXTENSIONS

MAX_IMAGE_BYTES = 50 * 1024 * 1024
SAVE_FORMATS = {
    ".jpg": ("JPEG", "image/jpeg", "jpg"),
    ".jpeg": ("JPEG", "image/jpeg", "jpg"),
    ".png": ("PNG", "image/png", "png"),
    ".webp": ("WEBP", "image/webp", "webp"),
    ".bmp": ("BMP", "image/bmp", "bmp"),
    ".tif": ("TIFF", "image/tiff", "tif"),
    ".tiff": ("TIFF", "image/tiff", "tif"),
}
SENSITIVE_KEYS = {
    "GPSInfo",
    "GPSLatitude",
    "GPSLongitude",
    "GPSAltitude",
    "Make",
    "Model",
    "DateTime",
    "DateTimeOriginal",
    "DateTimeDigitized",
    "Software",
    "Artist",
    "Copyright",
    "LensModel",
    "BodySerialNumber",
    "LensSerialNumber",
    "CameraOwnerName",
}
STRIP_INFO_KEYS = {
    "exif",
    "xmp",
    "xml",
    "comment",
    "iptc",
    "photoshop",
    "Raw profile type iptc",
    "Raw profile type exif",
    "Raw profile type xmp",
}


@dataclass
class StripResult:
    path: Path
    filename: str
    mime: str
    original_size: int
    output_size: int
    removed: int
    message: str


def inspect_exif(content: bytes, filename: str) -> dict:
    img = _open_image(content, filename)
    try:
        fields = _collect_fields(img)
        has_gps = any(item["key"].startswith("GPS") for item in fields)
        return {
            "filename": Path(filename).name,
            "format": (img.format or Path(filename).suffix.lstrip(".")).upper(),
            "width": img.width,
            "height": img.height,
            "has_exif": bool(fields),
            "has_gps": has_gps,
            "sensitive_count": sum(1 for item in fields if item["sensitive"]),
            "fields": fields,
        }
    finally:
        img.close()


def strip_exif(content: bytes, filename: str) -> StripResult:
    before = inspect_exif(content, filename)
    img = _open_image(content, filename)
    try:
        if getattr(img, "n_frames", 1) > 1:
            raise ValueError("暂不支持动图")
        oriented = ImageOps.exif_transpose(img)
        ext = Path(filename).suffix.lower()
        pil_format, mime, out_ext = SAVE_FORMATS[ext]
        cleaned = _prepare_pixels(oriented, pil_format)
        _drop_metadata(cleaned)
        save_kwargs = _save_kwargs(cleaned, pil_format)

        buf = io.BytesIO()
        cleaned.save(buf, format=pil_format, **save_kwargs)
        data = buf.getvalue()
    finally:
        img.close()

    stem = Path(filename).stem or "image"
    out_name = f"{stem}_noexif.{out_ext}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{out_ext}") as tmp:
        tmp.write(data)
        path = Path(tmp.name)

    after = inspect_exif(data, out_name)
    removed = max(0, before["sensitive_count"] + (len(before["fields"]) - len(after["fields"])))
    if not before["has_exif"] and not before["has_gps"]:
        message = "未发现可清除的拍摄信息，已按无元数据重新保存"
    elif after["has_gps"] or after["sensitive_count"]:
        message = "已尽量清除元数据；个别格式可能仍残留少量非位置字段"
    else:
        message = f"已清除拍摄信息（原 {len(before['fields'])} 项）"

    return StripResult(
        path=path,
        filename=out_name,
        mime=mime,
        original_size=len(content),
        output_size=len(data),
        removed=len(before["fields"]),
        message=message,
    )


def _open_image(content: bytes, filename: str) -> Image.Image:
    ext = Path(filename).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise ValueError(f"不支持的图片格式: {ext or '未知'}")
    if not content:
        raise ValueError("文件为空")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("文件过大，最大支持 50MB")
    try:
        return Image.open(io.BytesIO(content))
    except Exception as exc:
        raise ValueError("无法读取图片，请确认文件是否有效") from exc


def _collect_fields(img: Image.Image) -> list[dict]:
    fields: list[dict] = []
    seen: set[str] = set()

    def add(key: str, value) -> None:
        text = _stringify(value)
        if not text or key in seen:
            return
        seen.add(key)
        fields.append(
            {
                "key": key,
                "value": text,
                "sensitive": key in SENSITIVE_KEYS or key.startswith("GPS"),
            }
        )

    try:
        exif = img.getexif()
    except Exception:
        exif = None

    if exif:
        for tag_id, value in exif.items():
            name = TAGS.get(tag_id, f"Tag_{tag_id}")
            if name == "GPSInfo":
                continue
            add(name, value)

        gps = _gps_ifd(exif)
        if gps:
            for gps_id, value in gps.items():
                add(GPSTAGS.get(gps_id, f"GPS_{gps_id}"), value)
            coords = _decimal_gps(gps)
            if coords:
                add("GPSLatitude", f"{coords[0]:.6f}")
                add("GPSLongitude", f"{coords[1]:.6f}")

    for key in ("comment", "software", "description"):
        if key in img.info:
            add(key, img.info[key])

    return fields


def _gps_ifd(exif):
    try:
        ifd = getattr(ExifTags, "IFD", None)
        if ifd is not None and hasattr(exif, "get_ifd"):
            return exif.get_ifd(ifd.GPSInfo)
    except Exception:
        pass
    raw = exif.get(34853)
    return raw if isinstance(raw, dict) else None


def _decimal_gps(gps: dict) -> tuple[float, float] | None:
    try:
        lat = _to_degrees(gps.get(2) or gps.get("GPSLatitude"))
        lon = _to_degrees(gps.get(4) or gps.get("GPSLongitude"))
        if lat is None or lon is None:
            return None
        lat_ref = str(gps.get(1) or gps.get("GPSLatitudeRef") or "N")
        lon_ref = str(gps.get(3) or gps.get("GPSLongitudeRef") or "E")
        if lat_ref.upper().startswith("S"):
            lat = -lat
        if lon_ref.upper().startswith("W"):
            lon = -lon
        return lat, lon
    except Exception:
        return None


def _to_degrees(value) -> float | None:
    if not value:
        return None
    parts = list(value)
    if len(parts) < 3:
        return None

    def num(item) -> float:
        if hasattr(item, "numerator"):
            return float(item.numerator) / float(item.denominator or 1)
        if isinstance(item, tuple) and len(item) == 2:
            return float(item[0]) / float(item[1] or 1)
        return float(item)

    return num(parts[0]) + num(parts[1]) / 60 + num(parts[2]) / 3600


def _stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace").strip("\x00").strip()
        except Exception:
            return f"<二进制 {len(value)} 字节>"
    if isinstance(value, (list, tuple)):
        if len(value) > 8:
            return f"<{len(value)} 项>"
        return ", ".join(_stringify(item) for item in value)
    text = str(value).strip()
    if len(text) > 180:
        return text[:177] + "…"
    return text


def _prepare_pixels(img: Image.Image, pil_format: str) -> Image.Image:
    if pil_format == "JPEG":
        if img.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            return background
        if img.mode == "P":
            return img.convert("RGB")
        if img.mode != "RGB":
            return img.convert("RGB")
    return img.copy()


def _drop_metadata(img: Image.Image) -> None:
    for key in list(img.info):
        if key in STRIP_INFO_KEYS or str(key).lower().startswith("raw profile type"):
            img.info.pop(key, None)
    img.info.pop("exif", None)


def _save_kwargs(img: Image.Image, pil_format: str) -> dict:
    kwargs: dict = {}
    icc = img.info.get("icc_profile")
    if icc:
        kwargs["icc_profile"] = icc
    if pil_format == "JPEG":
        kwargs.update(quality=95, optimize=True)
    elif pil_format == "PNG":
        kwargs.update(optimize=True)
    elif pil_format == "WEBP":
        kwargs.update(quality=90, method=4)
    return kwargs
