"""Web 错误与接口标签的 zh / en。CLI 语言等 CLI 里程碑再接。"""

from __future__ import annotations

import re
from urllib.parse import unquote

SUPPORTED = ("zh", "en")

EXACT_EN = {
    "请选择视频文件": "Please choose a video file",
    "请选择图片文件": "Please choose an image file",
    "请选择 PDF 文件": "Please choose a PDF file",
    "请选择 CSV 文件": "Please choose a CSV file",
    "请选择 Excel 文件": "Please choose an Excel file",
    "请选择文件": "Please choose a file",
    "请至少选择 2 个 PDF 文件": "Please choose at least 2 PDF files",
    "文件为空": "File is empty",
    "CSV 文件为空": "CSV file is empty",
    "表格为空": "The spreadsheet is empty",
    "文件过大，最大支持 500MB": "File is too large (max 500MB)",
    "文件过大，最大支持 50MB": "File is too large (max 50MB)",
    "文件过大，最大支持 80MB": "File is too large (max 80MB)",
    "文件过大，最大支持 20MB": "File is too large (max 20MB)",
    "文件过大，最大支持 10MB": "File is too large (max 10MB)",
    "文件总大小超过上限（最大 200MB）": "Total size exceeds the limit (max 200MB)",
    "目标体积请输入整数（KB）": "Enter the size cap as an integer (KB)",
    "指定体积模式需要填写目标上限（KB）": "Size-cap mode needs a target limit (KB)",
    "请填写有效的目标体积上限": "Enter a valid size cap",
    "Base64 格式无效": "Invalid Base64",
    "解码结果为空": "Decoded result is empty",
    "无法识别 CSV 文件编码": "Could not detect the CSV encoding",
    "仅支持 .xlsx / .xlsm 格式": "Only .xlsx / .xlsm is supported",
    "暂不支持动图": "Animated images are not supported yet",
    "暂不支持动图，请使用静态图片": "Animated images are not supported. Use a still image",
    "无法读取图片，请确认文件是否有效": "Could not read the image. Check that the file is valid",
    "精确缩放需同时填写宽和高": "Exact resize needs both width and height",
    "裁剪填充需同时填写宽和高": "Fill-crop needs both width and height",
    "宽高须在 1～10000 之间": "Width and height must be between 1 and 10000",
    "合并至少需要 2 个 PDF": "Merging needs at least 2 PDFs",
    "拆分方式仅支持按页或页码范围": "Split mode must be by page or page range",
    "请填写页码范围，例如 1-3,5": "Enter a page range, e.g. 1-3,5",
    "页码格式无效，请使用如 1-3,5": "Invalid page range. Use e.g. 1-3,5",
    "请填写有效页码，例如 1-3,5": "Enter valid pages, e.g. 1-3,5",
    "请上传 PDF 文件": "Please upload a PDF file",
    "请上传 Word 文件（.doc / .docx）": "Please upload a Word file (.doc / .docx)",
    "请上传 PPT 文件（.ppt / .pptx）": "Please upload a PPT file (.ppt / .pptx)",
    "该转换类型仅支持单个文件": "This conversion accepts one file only",
    "未找到有效图片": "No valid images found",
    "图片转 OFD 未生成有效文件": "Image to OFD did not produce a file",
    "PDF 转 OFD 未生成有效文件": "PDF to OFD did not produce a file",
    "PDF 转 Word 未生成有效文件": "PDF to Word did not produce a file",
    "LibreOffice 未生成 PDF 文件": "LibreOffice did not produce a PDF",
    "Microsoft Office 未生成 PDF 文件": "Microsoft Office did not produce a PDF",
    "未检测到 Microsoft Word": "Microsoft Word was not found",
    "未检测到 Microsoft PowerPoint": "Microsoft PowerPoint was not found",
    "处理完成但输出为空": "Finished but the output was empty",
    "转换完成但未生成输出文件": "Finished but no output file was created",
    "压缩完成但未生成输出文件": "Finished but no output file was created",
    "fail_mode 仅支持 continue 或 fail_fast": "fail_mode only supports continue or fail_fast",
    "保持原格式": "Keep original format",
    "保持原分辨率": "Keep original resolution",
    "最大 1080p": "Max 1080p",
    "最大 720p": "Max 720p",
    "最大 480p": "Max 480p",
    "轻度（清理冗余，尽量保真）": "Light (clean extras, keep fidelity)",
    "标准（重压较大图片）": "Standard (recompress large images)",
    "强力（更小体积，画质下降更明显）": "Strong (smaller file, more quality loss)",
    "图片 → PDF": "Images → PDF",
    "图片 → OFD": "Images → OFD",
    "PDF → OFD": "PDF → OFD",
    "PDF → Word": "PDF → Word",
    "Word → PDF": "Word → PDF",
    "PPT → PDF": "PPT → PDF",
    "支持多张图片合并为一个 PDF": "Merge multiple images into one PDF",
    "中国电子公文格式，支持多图": "Chinese official document format. Multiple images allowed",
    "版式尽量保留；复杂矢量可能有差异": "Layout is kept where possible. Complex vectors may differ",
    "可编辑文本效果较好；扫描件无 OCR": "Works best on real text. Scans have no OCR",
    "需要本机安装 LibreOffice 或 Microsoft Word": "Needs LibreOffice or Microsoft Word on this machine",
    "需要本机安装 LibreOffice 或 Microsoft PowerPoint": "Needs LibreOffice or Microsoft PowerPoint on this machine",
    "未发现可清除的拍摄信息，已按无元数据重新保存": "No shooting info found. Saved again without metadata",
    "已尽量清除元数据；个别格式可能仍残留少量非位置字段": "Cleared what we could. A few non-location fields may remain",
    "当前文件已较紧凑，保持原文件": "This file is already compact. Kept the original",
    "已优化 PNG 编码并移除元数据": "Optimized PNG encoding and removed metadata",
    "已优化 WebP 编码": "Optimized WebP encoding",
    "无法在保持 PNG 格式下达到目标体积，已输出优化后的 PNG": "Could not hit the size cap as PNG. Saved an optimized PNG",
    "无法在保持 PNG 格式下达到目标体积，已保持原文件": "Could not hit the size cap as PNG. Kept the original",
}

PATTERNS = (
    (re.compile(r"^文件为空: (.+)$"), "File is empty: {0}"),
    (re.compile(r"^(.+) 过大，单文件最大 (\d+)MB$"), "{0} is too large (max {1}MB per file)"),
    (re.compile(r"^不支持的图片格式: (.+)$"), "Unsupported image format: {0}"),
    (re.compile(r"^不支持的输出格式: (.+)$"), "Unsupported output format: {0}"),
    (re.compile(r"^不支持的格式: (.+)$"), "Unsupported format: {0}"),
    (re.compile(r"^不支持的视频格式: (.+)$"), "Unsupported video format: {0}"),
    (re.compile(r"^不支持的转换类型: (.+)$"), "Unsupported conversion: {0}"),
    (re.compile(r"^不支持的压缩强度: (.+)$"), "Unsupported compression preset: {0}"),
    (re.compile(r"^一次最多处理 (\d+) 个文件$"), "Up to {0} files at a time"),
    (re.compile(r"^一次最多合并 (\d+) 个文件$"), "Up to {0} files can be merged at a time"),
    (re.compile(r"^文件总大小超过上限（最大 (\d+)MB）$"), "Total size exceeds the limit (max {0}MB)"),
    (re.compile(r"^请上传 PDF 文件: (.+)$"), "Please upload a PDF: {0}"),
    (re.compile(r"^无法读取 PDF: (.+)$"), "Could not read PDF: {0}"),
    (re.compile(r"^(.+) 已加密，暂不支持（加密/解密将在后续提供）$"), "{0} is encrypted and not supported yet"),
    (re.compile(r"^(.+) 没有有效页面$"), "{0} has no valid pages"),
    (re.compile(r"^页码 (.+) 超出范围（共 (\d+) 页）$"), "Page {0} is out of range ({1} pages)"),
    (re.compile(r"^页数过多（最多 (\d+) 页按页拆分）$"), "Too many pages (max {0} when splitting by page)"),
    (re.compile(r"^已清除拍摄信息（原 (\d+) 项）$"), "Cleared shooting info ({0} fields)"),
    (re.compile(r"^已压缩 (.+)%（(.+)）$"), "Compressed {0}% ({1})"),
    (re.compile(r"^Excel 解析失败: (.+)$"), "Failed to parse Excel: {0}"),
    (re.compile(r"^图片转 OFD 失败: (.+)$"), "Image to OFD failed: {0}"),
    (re.compile(r"^PDF 转 OFD 失败: (.+)$"), "PDF to OFD failed: {0}"),
    (re.compile(r"^PDF 转 Word 失败: (.+)$"), "PDF to Word failed: {0}"),
    (re.compile(r"^LibreOffice 转换失败: (.+)$"), "LibreOffice conversion failed: {0}"),
    (re.compile(r"^视频压缩失败: (.+)$"), "Video compression failed: {0}"),
    (re.compile(r"^音频提取失败: (.+)$"), "Audio extraction failed: {0}"),
    (re.compile(r"^全部文件处理失败。(.+)$"), "All files failed. {0}"),
    (re.compile(r"^未找到可用的 Office 转换引擎$"), "No Office conversion engine is available"),
    (re.compile(r"^已转为 WebP 高画质（(\d+)），视觉差异极小$"), "Saved as high-quality WebP ({0}) with little visual change"),
    (re.compile(r"^以 WebP 高画质（(\d+)）重新编码$"), "Re-encoded as high-quality WebP ({0})"),
    (re.compile(r"^以 JPEG 高画质（(\d+)）重新编码，视觉差异极小$"), "Re-encoded as high-quality JPEG ({0}) with little visual change"),
    (re.compile(r"^JPEG 优化有限，已转为 WebP 高画质（(\d+)）$"), "JPEG gains were limited. Saved as high-quality WebP ({0})"),
)


def parse_lang(header: str | None) -> str:
    raw = (header or "").strip()
    if not raw:
        return "zh"
    for part in raw.split(","):
        tag = part.split(";")[0].strip().lower()
        if tag.startswith("zh"):
            return "zh"
        if tag.startswith("en"):
            return "en"
    return "zh"


def translate_text(text: str | None, lang: str) -> str:
    if not text or lang != "en":
        return text or ""
    if text in EXACT_EN:
        return EXACT_EN[text]
    for pattern, template in PATTERNS:
        match = pattern.match(text)
        if match:
            groups = [translate_text(item, lang) if isinstance(item, str) else item for item in match.groups()]
            return template.format(*groups)
    return text


def localize_items(items: list[dict], lang: str, fields: tuple[str, ...] = ("label", "hint")) -> list[dict]:
    localized = []
    for item in items:
        cloned = dict(item)
        for field in fields:
            value = cloned.get(field)
            if isinstance(value, str):
                cloned[field] = translate_text(value, lang)
        localized.append(cloned)
    return localized


def localize_header_value(value: str | None, lang: str) -> str | None:
    if value is None:
        return None
    return translate_text(unquote(value), lang)
