from pathlib import Path
from contextlib import contextmanager
import io, os, shutil, subprocess, sys, tempfile
from dataclasses import dataclass
from PIL import Image, ImageOps
from app.image_compressor import IMAGE_EXTENSIONS

MAX_DOC_BYTES = 80 * 1024 * 1024

CONVERSIONS = {
    "image_to_pdf": {
        "label": "图片 → PDF",
        "accept": ".jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff",
        "multiple": True,
        "needs_office": False,
        "hint": "支持多张图片合并为一个 PDF",
    },
    "image_to_ofd": {
        "label": "图片 → OFD",
        "accept": ".jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff",
        "multiple": True,
        "needs_office": False,
        "hint": "中国电子公文格式，支持多图",
    },
    "pdf_to_ofd": {
        "label": "PDF → OFD",
        "accept": ".pdf",
        "multiple": False,
        "needs_office": False,
        "hint": "版式尽量保留；复杂矢量可能有差异",
    },
    "pdf_to_word": {
        "label": "PDF → Word",
        "accept": ".pdf",
        "multiple": False,
        "needs_office": False,
        "hint": "可编辑文本效果较好；扫描件无 OCR",
    },
    "word_to_pdf": {
        "label": "Word → PDF",
        "accept": ".doc,.docx",
        "multiple": False,
        "needs_office": True,
        "hint": "需要本机安装 LibreOffice 或 Microsoft Word",
    },
    "ppt_to_pdf": {
        "label": "PPT → PDF",
        "accept": ".ppt,.pptx",
        "multiple": False,
        "needs_office": True,
        "hint": "需要本机安装 LibreOffice 或 Microsoft PowerPoint",
    },
}

@dataclass
class ConvertResult:
    path: Path
    filename: str
    mime: str

def list_conversions() -> list[dict]:
    office = detect_office_backend()
    items = []
    for key, meta in CONVERSIONS.items():
        items.append({
            "id": key,
            "label": meta["label"],
            "accept": meta["accept"],
            "multiple": meta["multiple"],
            "needs_office": meta["needs_office"],
            "hint": meta["hint"],
            "available": (not meta["needs_office"]) or office["available"],
        })
    return items

def detect_office_backend() -> dict:
    soffice = _find_libreoffice()
    if soffice:
        return {"available": True, "backend": "libreoffice", "path": soffice}
    if sys.platform == "win32":
        try:
            import comtypes.client  # noqa: F401
        except ImportError:
            comtypes_ok = False
        else:
            comtypes_ok = True
        if comtypes_ok:
            word = _com_available("Word.Application")
            ppt = _com_available("PowerPoint.Application")
            if word or ppt:
                return {"available": True, "backend": "msoffice", "word": word, "powerpoint": ppt}
    return {"available": False, "backend": None, "message": "未检测到 LibreOffice 或 Microsoft Office。Word/PPT 转 PDF 需要其一。"}

def convert_documents(conversion: str, files: list[tuple[bytes, str]]) -> ConvertResult:
    if conversion not in CONVERSIONS:
        raise ValueError(f"不支持的转换类型: {conversion}")
    if not files:
        raise ValueError("请选择文件")
    total = sum(len(b) for b, _ in files)
    if total > MAX_DOC_BYTES:
        raise ValueError("文件过大，最大支持 80MB")
    meta = CONVERSIONS[conversion]
    if not meta["multiple"] and len(files) > 1:
        raise ValueError("该转换类型仅支持单个文件")
    handlers = {
        "image_to_pdf": _image_to_pdf,
        "image_to_ofd": _image_to_ofd,
        "pdf_to_ofd": _pdf_to_ofd,
        "pdf_to_word": _pdf_to_word,
        "word_to_pdf": _word_to_pdf,
        "ppt_to_pdf": _ppt_to_pdf,
    }
    return handlers[conversion](files)

@contextmanager
def _ofd_workdir():
    work = Path(tempfile.mkdtemp(prefix="ofd_work_"))
    old = Path.cwd()
    try:
        os.chdir(work)
        yield work
    finally:
        os.chdir(old)
        shutil.rmtree(work, ignore_errors=True)

def _stem_from(files: list[tuple[bytes, str]], fallback: str = "document") -> str:
    name = Path(files[0][1]).stem if files else fallback
    return name or fallback

def _write_temp(data: bytes, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        return Path(tmp.name)

def _save_bytes(data: bytes, filename: str, mime: str) -> ConvertResult:
    suffix = Path(filename).suffix or ".bin"
    path = _write_temp(data, suffix)
    return ConvertResult(path=path, filename=filename, mime=mime)

def _open_images(files: list[tuple[bytes, str]]) -> list[Image.Image]:
    images: list[Image.Image] = []
    for data, name in files:
        ext = Path(name).suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            raise ValueError(f"不支持的图片格式: {ext or '未知'}")
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        if getattr(img, "n_frames", 1) > 1:
            raise ValueError("暂不支持动图")
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            alpha = img.split()[-1] if img.mode in ("RGBA", "LA") else None
            background.paste(img, mask=alpha)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        images.append(img)
    if not images:
        raise ValueError("未找到有效图片")
    return images

def _image_to_pdf(files: list[tuple[bytes, str]]) -> ConvertResult:
    images = _open_images(files)
    stem = _stem_from(files, "images")
    out_name = f"{stem}.pdf" if len(files) == 1 else f"{stem}_merged.pdf"
    buf = io.BytesIO()
    first, rest = images[0], images[1:]
    first.save(buf, format="PDF", save_all=True, append_images=rest, resolution=100.0)
    for img in images:
        img.close()
    return _save_bytes(buf.getvalue(), out_name, "application/pdf")

def _image_to_ofd(files: list[tuple[bytes, str]]) -> ConvertResult:
    from easyofd.ofd import OFD
    images = _open_images(files)
    stem = _stem_from(files, "images")
    out_name = f"{stem}.ofd" if len(files) == 1 else f"{stem}_merged.ofd"
    try:
        with _ofd_workdir():
            ofd_bytes = OFD().jpg2ofd(images)
    except Exception as exc:
        raise RuntimeError(f"图片转 OFD 失败: {exc}") from exc
    finally:
        for img in images:
            img.close()
    if not ofd_bytes:
        raise RuntimeError("图片转 OFD 未生成有效文件")
    return _save_bytes(ofd_bytes, out_name, "application/ofd")

def _pdf_to_ofd(files: list[tuple[bytes, str]]) -> ConvertResult:
    from easyofd.ofd import OFD
    data, name = files[0]
    if Path(name).suffix.lower() != ".pdf":
        raise ValueError("请上传 PDF 文件")
    stem = Path(name).stem or "document"
    try:
        with _ofd_workdir():
            ofd = OFD()
            ofd_bytes = ofd.pdf2ofd(data, optional_text=False)
            ofd.del_data()
    except Exception as exc:
        raise RuntimeError(f"PDF 转 OFD 失败: {exc}") from exc
    if not ofd_bytes:
        raise RuntimeError("PDF 转 OFD 未生成有效文件")
    return _save_bytes(ofd_bytes, f"{stem}.ofd", "application/ofd")

def _pdf_to_word(files: list[tuple[bytes, str]]) -> ConvertResult:
    from pdf2docx import Converter
    data, name = files[0]
    if Path(name).suffix.lower() != ".pdf":
        raise ValueError("请上传 PDF 文件")
    stem = Path(name).stem or "document"
    pdf_path = _write_temp(data, ".pdf")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        docx_path = Path(tmp.name)
    try:
        cv = Converter(str(pdf_path))
        try:
            cv.convert(str(docx_path))
        finally:
            cv.close()
        if not docx_path.exists() or docx_path.stat().st_size == 0:
            raise RuntimeError("PDF 转 Word 未生成有效文件")
        final = docx_path.parent / f"{stem}.docx"
        if final.resolve() != docx_path.resolve():
            shutil.copy2(docx_path, final)
            docx_path.unlink(missing_ok=True)
            docx_path = final
        return ConvertResult(
            path=docx_path,
            filename=f"{stem}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as exc:
        docx_path.unlink(missing_ok=True)
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(f"PDF 转 Word 失败: {exc}") from exc
    finally:
        pdf_path.unlink(missing_ok=True)

def _word_to_pdf(files: list[tuple[bytes, str]]) -> ConvertResult:
    data, name = files[0]
    ext = Path(name).suffix.lower()
    if ext not in {".doc", ".docx"}:
        raise ValueError("请上传 Word 文件（.doc / .docx）")
    return _office_to_pdf(data, name, kind="word")

def _ppt_to_pdf(files: list[tuple[bytes, str]]) -> ConvertResult:
    data, name = files[0]
    ext = Path(name).suffix.lower()
    if ext not in {".ppt", ".pptx"}:
        raise ValueError("请上传 PPT 文件（.ppt / .pptx）")
    return _office_to_pdf(data, name, kind="ppt")

def _office_to_pdf(data: bytes, name: str, kind: str) -> ConvertResult:
    office = detect_office_backend()
    if not office["available"]:
        raise RuntimeError(office.get("message") or "未找到可用的 Office 转换引擎")
    stem = Path(name).stem or "document"
    suffix = Path(name).suffix.lower() or (".docx" if kind == "word" else ".pptx")
    input_path = _write_temp(data, suffix)
    out_dir = Path(tempfile.mkdtemp(prefix="docconv_"))
    try:
        if office["backend"] == "libreoffice":
            pdf_path = _libreoffice_to_pdf(office["path"], input_path, out_dir)
        else:
            if kind == "word" and not office.get("word", True):
                raise RuntimeError("未检测到 Microsoft Word")
            if kind == "ppt" and not office.get("powerpoint", True):
                raise RuntimeError("未检测到 Microsoft PowerPoint")
            pdf_path = _msoffice_to_pdf(input_path, out_dir, kind)
        # 移到独立临时文件，便于后台清理
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            final = Path(tmp.name)
        shutil.move(str(pdf_path), str(final))
        shutil.rmtree(out_dir, ignore_errors=True)
        return ConvertResult(path=final, filename=f"{stem}.pdf", mime="application/pdf")
    except Exception:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise
    finally:
        input_path.unlink(missing_ok=True)

def _libreoffice_to_pdf(soffice: str, input_path: Path, out_dir: Path) -> Path:
    cmd = [soffice, "--headless", "--nologo", "--nofirststartwizard", "--convert-to", "pdf", "--outdir", str(out_dir), str(input_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "未知错误").strip()
        raise RuntimeError(f"LibreOffice 转换失败: {err[-500:]}")
    expected = out_dir / f"{input_path.stem}.pdf"
    if expected.exists():
        return expected
    pdfs = list(out_dir.glob("*.pdf"))
    if not pdfs:
        raise RuntimeError("LibreOffice 未生成 PDF 文件")
    return pdfs[0]

def _msoffice_to_pdf(input_path: Path, out_dir: Path, kind: str) -> Path:
    try:
        import comtypes.client
    except ImportError as exc:
        raise RuntimeError("检测到 Microsoft Office，但缺少 comtypes。请安装 LibreOffice，或执行: pip install comtypes") from exc
    abs_in = str(input_path.resolve())
    abs_out = str((out_dir / f"{input_path.stem}.pdf").resolve())
    if kind == "word":
        app = comtypes.client.CreateObject("Word.Application")
        app.Visible = False
        try:
            doc = app.Documents.Open(abs_in)
            doc.SaveAs(abs_out, FileFormat=17)
            doc.Close(False)
        finally:
            app.Quit()
    else:
        app = comtypes.client.CreateObject("PowerPoint.Application")
        try:
            app.Visible = 1
        except Exception:
            pass
        try:
            deck = app.Presentations.Open(abs_in, WithWindow=False)
            deck.SaveAs(abs_out, 32)
            deck.Close()
        finally:
            app.Quit()
    out = Path(abs_out)
    if not out.exists():
        raise RuntimeError("Microsoft Office 未生成 PDF 文件")
    return out

def _find_libreoffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/bin/libreoffice",
        "/snap/bin/libreoffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None

def _com_available(prog_id: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog_id):
            return True
    except OSError:
        return False