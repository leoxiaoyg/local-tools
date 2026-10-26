from pathlib import Path
import base64
import json
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from urllib.parse import quote, unquote

from app.i18n import current_lang, localize_items, parse_lang, translate_text

from app.batch import run_batch
from app.converter import AUDIO_FORMATS, MAX_VIDEO_BYTES, convert_uploaded_file
from app.csv_clean import clean_csv
from app.csv_excel import csv_to_excel, excel_to_csv
from app.doc_converter import (
    convert_documents,
    detect_office_backend,
    list_conversions,
)
from app.exif_tools import inspect_exif, strip_exif
from app.image_compressor import OUTPUT_FORMATS, compress_image
from app.image_transform import EXPORT_FORMATS, transform_image
from app.pdf_tools import (
    compress_pdf,
    decrypt_pdf,
    encrypt_pdf,
    list_compress_presets,
    merge_pdfs,
    split_pdf,
)
from app.watermark import apply_text_watermark
from app.video_compressor import RESOLUTIONS, VIDEO_OUTPUT, compress_video_file

app = FastAPI(title="Local Tools", version="2.0.0")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
MESSAGE_HEADERS = ("x-exif-message", "x-pdf-message", "x-compress-message", "x-watermark-message", "x-csv-message")


@app.middleware("http")
async def localize_http(request: Request, call_next):
    lang = parse_lang(request.headers.get("accept-language"))
    request.state.lang = lang
    token = current_lang.set(lang)
    try:
        return await _localize_response(request, call_next, lang)
    finally:
        current_lang.reset(token)


async def _localize_response(request: Request, call_next, lang: str):
    response = await call_next(request)

    for header in MESSAGE_HEADERS:
        raw = response.headers.get(header)
        if raw:
            response.headers[header] = quote(translate_text(unquote(raw), lang), safe="")

    errors = response.headers.get("x-batch-errors")
    if errors:
        try:
            payload = json.loads(unquote(errors))
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and isinstance(item.get("detail"), str):
                        item["detail"] = translate_text(item["detail"], lang)
                response.headers["x-batch-errors"] = quote(
                    json.dumps(payload, ensure_ascii=False),
                    safe="",
                )
        except Exception:
            pass

    content_type = response.headers.get("content-type", "")
    if response.status_code >= 400 and "application/json" in content_type:
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in {"content-length", "content-type"}
        }
        try:
            payload = json.loads(body)
            if isinstance(payload.get("detail"), str):
                payload["detail"] = translate_text(payload["detail"], lang)
            return JSONResponse(payload, status_code=response.status_code, headers=headers)
        except Exception:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type="application/json",
            )
    return response


def _lang(request: Request) -> str:
    return getattr(request.state, "lang", None) or parse_lang(request.headers.get("accept-language"))


@app.get("/api/formats")
def list_formats(request: Request):
    return localize_items(
        [
            {"id": key, "label": val["label"], "ext": val["ext"]}
            for key, val in AUDIO_FORMATS.items()
        ],
        _lang(request),
    )


@app.get("/api/image/formats")
def list_image_formats(request: Request):
    return localize_items(
        [{"id": key, "label": val["label"]} for key, val in OUTPUT_FORMATS.items()],
        _lang(request),
    )


@app.get("/api/image/export-formats")
def list_image_export_formats(request: Request):
    return localize_items(
        [{"id": k, "label": v["label"]} for k, v in EXPORT_FORMATS.items()],
        _lang(request),
    )


@app.get("/api/video/compress-options")
def list_video_compress_options(request: Request):
    lang = _lang(request)
    return {
        "formats": localize_items(
            [{"id": k, "label": v["label"]} for k, v in VIDEO_OUTPUT.items()],
            lang,
        ),
        "resolutions": localize_items(
            [{"id": k, "label": v["label"]} for k, v in RESOLUTIONS.items()],
            lang,
        ),
    }


@app.post("/api/convert")
async def convert_video(
    file: UploadFile = File(...),
    format: str = Form("mp3"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择视频文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    max_size = MAX_VIDEO_BYTES
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件过大，最大支持 500MB")

    try:
        output_path, info = convert_uploaded_file(content, file.filename, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(
        path=output_path,
        media_type=info["mime"],
        filename=info["filename"],
        background=BackgroundTask(_cleanup, output_path),
    )


@app.post("/api/video/compress")
async def compress_video(
    file: UploadFile = File(...),
    format: str = Form("mp4"),
    crf: int = Form(23),
    resolution: str = Form("original"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择视频文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    max_size = MAX_VIDEO_BYTES
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件过大，最大支持 500MB")

    try:
        output_path, info = compress_video_file(
            content, file.filename, format, crf, resolution
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    original_size = len(content)
    compressed_size = output_path.stat().st_size
    headers = {
        "X-Original-Size": str(original_size),
        "X-Compressed-Size": str(compressed_size),
    }

    return FileResponse(
        path=output_path,
        media_type=info["mime"],
        filename=info["filename"],
        headers=headers,
        background=BackgroundTask(_cleanup, output_path),
    )


@app.post("/api/image/compress")
async def compress_image_file(
    file: UploadFile = File(...),
    mode: str = Form("smart"),
    target_kb: str = Form(""),
    output_format: str = Form("auto"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择图片文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    max_size = 50 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件过大，最大支持 50MB")

    parsed_target = None
    if target_kb.strip():
        try:
            parsed_target = int(target_kb.strip())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="目标体积请输入整数（KB）") from exc

    if mode == "target" and not parsed_target:
        raise HTTPException(status_code=400, detail="指定体积模式需要填写目标上限（KB）")

    try:
        result = compress_image(
            content,
            file.filename,
            mode=mode,
            target_kb=parsed_target,
            output_format=output_format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headers = {
        "X-Original-Size": str(result.original_size),
        "X-Compressed-Size": str(result.compressed_size),
        "X-Output-Format": result.output_format,
        "X-Compress-Message": quote(result.message, safe=""),
    }
    if result.quality is not None:
        headers["X-Quality-Used"] = str(result.quality)

    return FileResponse(
        path=result.path,
        media_type=result.mime,
        filename=result.filename,
        headers=headers,
        background=BackgroundTask(_cleanup, result.path),
    )


@app.post("/api/image/compress-batch")
async def compress_image_batch(
    files: list[UploadFile] = File(...),
    mode: str = Form("smart"),
    target_kb: str = Form(""),
    output_format: str = Form("auto"),
):
    parsed_target = _parse_optional_int(target_kb, "目标体积请输入整数（KB）")
    if mode == "target" and not parsed_target:
        raise HTTPException(status_code=400, detail="指定体积模式需要填写目标上限（KB）")

    payload = await _read_image_uploads(files)

    def handler(content: bytes, filename: str):
        result = compress_image(
            content,
            filename,
            mode=mode,
            target_kb=parsed_target,
            output_format=output_format,
        )
        return result.path, result.filename

    return _batch_zip_response(payload, handler, "compressed-images.zip")


@app.post("/api/image/transform")
async def transform_image_file(
    file: UploadFile = File(...),
    output_format: str = Form("jpeg"),
    width: str = Form(""),
    height: str = Form(""),
    resize_mode: str = Form("fit"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择图片文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    max_size = 50 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件过大，最大支持 50MB")

    try:
        result = transform_image(
            content,
            file.filename,
            output_format,
            width,
            height,
            resize_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headers = {
        "X-Output-Width": str(result.width),
        "X-Output-Height": str(result.height),
    }

    return FileResponse(
        path=result.path,
        media_type=result.mime,
        filename=result.filename,
        headers=headers,
        background=BackgroundTask(_cleanup, result.path),
    )


@app.post("/api/image/transform-batch")
async def transform_image_batch(
    files: list[UploadFile] = File(...),
    output_format: str = Form("jpeg"),
    width: str = Form(""),
    height: str = Form(""),
    resize_mode: str = Form("fit"),
):
    payload = await _read_image_uploads(files)

    def handler(content: bytes, filename: str):
        result = transform_image(
            content,
            filename,
            output_format,
            width,
            height,
            resize_mode,
        )
        return result.path, result.filename

    return _batch_zip_response(payload, handler, "converted-images.zip")


@app.post("/api/image/watermark")
async def watermark_image_file(
    file: UploadFile = File(...),
    text: str = Form(...),
    position: str = Form("bottom-right"),
    opacity: str = Form("40"),
):
    payload = await _read_image_uploads([file])
    try:
        result = apply_text_watermark(
            payload[0][0],
            payload[0][1],
            text=text,
            position=position,
            opacity=_parse_opacity(opacity),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(
        path=result.path,
        media_type=result.mime,
        filename=result.filename,
        headers={
            "X-Original-Size": str(result.original_size),
            "X-Output-Size": str(result.output_size),
            "X-Watermark-Message": quote(result.message, safe=""),
        },
        background=BackgroundTask(_cleanup, result.path),
    )


@app.post("/api/image/watermark-batch")
async def watermark_image_batch(
    files: list[UploadFile] = File(...),
    text: str = Form(...),
    position: str = Form("bottom-right"),
    opacity: str = Form("40"),
):
    payload = await _read_image_uploads(files)
    opacity_pct = _parse_opacity(opacity)

    def handler(content: bytes, filename: str):
        result = apply_text_watermark(
            content,
            filename,
            text=text,
            position=position,
            opacity=opacity_pct,
        )
        return result.path, result.filename

    return _batch_zip_response(payload, handler, "watermarked-images.zip")


def _parse_opacity(raw: str) -> int:
    try:
        return int((raw or "").strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="透明度请填写 10～100 的整数") from exc


@app.post("/api/image/exif")
async def inspect_image_exif(file: UploadFile = File(...)):
    payload = await _read_image_uploads([file])
    try:
        return inspect_exif(payload[0][0], payload[0][1])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/image/exif-strip")
async def strip_image_exif(file: UploadFile = File(...)):
    payload = await _read_image_uploads([file])
    try:
        result = strip_exif(payload[0][0], payload[0][1])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    headers = {
        "X-Original-Size": str(result.original_size),
        "X-Output-Size": str(result.output_size),
        "X-Exif-Removed": str(result.removed),
        "X-Exif-Message": quote(result.message, safe=""),
    }
    return FileResponse(
        path=result.path,
        media_type=result.mime,
        filename=result.filename,
        headers=headers,
        background=BackgroundTask(_cleanup, result.path),
    )


@app.post("/api/image/exif-strip-batch")
async def strip_image_exif_batch(files: list[UploadFile] = File(...)):
    payload = await _read_image_uploads(files)

    def handler(content: bytes, filename: str):
        result = strip_exif(content, filename)
        return result.path, result.filename

    return _batch_zip_response(payload, handler, "images-noexif.zip")


@app.get("/api/pdf/options")
def list_pdf_options(request: Request):
    return {"compress_presets": localize_items(list_compress_presets(), _lang(request))}


@app.post("/api/pdf/merge")
async def merge_pdf_files(files: list[UploadFile] = File(...)):
    payload = await _read_pdf_uploads(files, min_count=2)
    try:
        result = merge_pdfs(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _pdf_file_response(result)


@app.post("/api/pdf/compress")
async def compress_pdf_file(
    file: UploadFile = File(...),
    preset: str = Form("standard"),
):
    payload = await _read_pdf_uploads([file], min_count=1)
    try:
        result = compress_pdf(payload[0][0], payload[0][1], preset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _pdf_file_response(result)


@app.post("/api/pdf/compress-batch")
async def compress_pdf_batch(
    files: list[UploadFile] = File(...),
    preset: str = Form("standard"),
):
    payload = await _read_pdf_uploads(files, min_count=1)

    def handler(content: bytes, filename: str):
        result = compress_pdf(content, filename, preset)
        return result.path, result.filename

    return _batch_zip_response(payload, handler, "compressed-pdfs.zip")


@app.post("/api/pdf/split")
async def split_pdf_file(
    file: UploadFile = File(...),
    mode: str = Form("pages"),
    ranges: str = Form(""),
):
    payload = await _read_pdf_uploads([file], min_count=1)
    try:
        result = split_pdf(payload[0][0], payload[0][1], mode=mode, ranges=ranges)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _pdf_file_response(result)


def _parse_allow_list(raw: str) -> list[str]:
    items = [part.strip() for part in raw.replace("，", ",").split(",") if part.strip()]
    return items


@app.post("/api/pdf/encrypt")
async def encrypt_pdf_file(
    file: UploadFile = File(...),
    user_password: str = Form(...),
    owner_password: str = Form(""),
    allow: str = Form("print,modify,copy,annotate"),
):
    payload = await _read_pdf_uploads([file], min_count=1)
    try:
        result = encrypt_pdf(
            payload[0][0],
            payload[0][1],
            user_password=user_password,
            owner_password=owner_password,
            allow=_parse_allow_list(allow),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _pdf_file_response(result)


@app.post("/api/pdf/encrypt-batch")
async def encrypt_pdf_batch(
    files: list[UploadFile] = File(...),
    user_password: str = Form(...),
    owner_password: str = Form(""),
    allow: str = Form("print,modify,copy,annotate"),
):
    payload = await _read_pdf_uploads(files, min_count=1)
    allowed = _parse_allow_list(allow)

    def handler(content: bytes, filename: str):
        result = encrypt_pdf(
            content,
            filename,
            user_password=user_password,
            owner_password=owner_password,
            allow=allowed,
        )
        return result.path, result.filename

    return _batch_zip_response(payload, handler, "locked-pdfs.zip")


@app.post("/api/pdf/decrypt")
async def decrypt_pdf_file(
    file: UploadFile = File(...),
    password: str = Form(...),
):
    payload = await _read_pdf_uploads([file], min_count=1)
    try:
        result = decrypt_pdf(payload[0][0], payload[0][1], password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _pdf_file_response(result)


@app.post("/api/pdf/decrypt-batch")
async def decrypt_pdf_batch(
    files: list[UploadFile] = File(...),
    password: str = Form(...),
):
    payload = await _read_pdf_uploads(files, min_count=1)

    def handler(content: bytes, filename: str):
        result = decrypt_pdf(content, filename, password)
        return result.path, result.filename

    return _batch_zip_response(payload, handler, "unlocked-pdfs.zip")


def _form_flag(raw: str) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "on", "yes"}


@app.post("/api/csv/clean")
async def clean_csv_file(
    file: UploadFile = File(...),
    drop_empty: str = Form("true"),
    dedupe: str = Form("true"),
    keep: str = Form(""),
):
    payload = await _read_csv_uploads([file])
    try:
        result = clean_csv(
            payload[0][0],
            payload[0][1],
            drop_empty=_form_flag(drop_empty),
            dedupe=_form_flag(dedupe),
            keep_columns=keep,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(
        path=result.path,
        media_type=result.mime,
        filename=result.filename,
        headers={
            "X-Original-Size": str(result.original_size),
            "X-Output-Size": str(result.output_size),
            "X-Csv-Message": quote(result.message, safe=""),
        },
        background=BackgroundTask(_cleanup, result.path),
    )


@app.post("/api/csv/clean-batch")
async def clean_csv_batch(
    files: list[UploadFile] = File(...),
    drop_empty: str = Form("true"),
    dedupe: str = Form("true"),
    keep: str = Form(""),
):
    payload = await _read_csv_uploads(files)
    drop = _form_flag(drop_empty)
    unique = _form_flag(dedupe)

    def handler(content: bytes, filename: str):
        result = clean_csv(
            content,
            filename,
            drop_empty=drop,
            dedupe=unique,
            keep_columns=keep,
        )
        return result.path, result.filename

    return _batch_zip_response(payload, handler, "cleaned-csv.zip")


@app.post("/api/csv/to-excel")
async def convert_csv_to_excel(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择 CSV 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    max_size = 20 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件过大，最大支持 20MB")

    try:
        output_path, out_name = csv_to_excel(content, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FileResponse(
        path=output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=out_name,
        background=BackgroundTask(_cleanup, output_path),
    )


@app.post("/api/excel/to-csv")
async def convert_excel_to_csv(
    file: UploadFile = File(...),
    sheet: str = Form("0"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择 Excel 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    max_size = 20 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件过大，最大支持 20MB")

    try:
        output_path, out_name = excel_to_csv(content, file.filename, sheet)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel 解析失败: {exc}") from exc

    return FileResponse(
        path=output_path,
        media_type="text/csv; charset=utf-8",
        filename=out_name,
        background=BackgroundTask(_cleanup, output_path),
    )


@app.get("/api/doc/conversions")
def list_doc_conversions(request: Request):
    return {
        "conversions": localize_items(list_conversions(), _lang(request)),
        "office": detect_office_backend(),
    }


@app.post("/api/doc/convert")
async def convert_document(
    conversion: str = Form(...),
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="请选择文件")

    payload: list[tuple[bytes, str]] = []
    for upload in files:
        if not upload.filename:
            raise HTTPException(status_code=400, detail="请选择文件")
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"文件为空: {upload.filename}")
        payload.append((content, upload.filename))

    try:
        result = convert_documents(conversion, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(
        path=result.path,
        media_type=result.mime,
        filename=result.filename,
        background=BackgroundTask(_cleanup, result.path),
    )


@app.post("/api/base64/encode")
async def base64_encode_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    max_size = 10 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件过大，最大支持 10MB")

    encoded = base64.b64encode(content).decode("ascii")
    return JSONResponse({"text": encoded, "filename": file.filename})


@app.post("/api/base64/decode")
async def base64_decode_text(text: str = Form(...), filename: str = Form("decoded.bin")):
    cleaned = text.strip()
    if "," in cleaned and cleaned.startswith("data:"):
        cleaned = cleaned.split(",", 1)[1]

    try:
        data = base64.b64decode(cleaned, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Base64 格式无效") from exc

    if not data:
        raise HTTPException(status_code=400, detail="解码结果为空")

    safe_name = Path(filename).name or "decoded.bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(safe_name).suffix) as tmp:
        tmp.write(data)
        output_path = Path(tmp.name)

    return FileResponse(
        path=output_path,
        media_type="application/octet-stream",
        filename=safe_name,
        background=BackgroundTask(_cleanup, output_path),
    )


def _parse_optional_int(value: str, error: str) -> int | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=error) from exc


async def _read_csv_uploads(files: list[UploadFile]) -> list[tuple[bytes, str]]:
    if not files:
        raise HTTPException(status_code=400, detail="请选择 CSV 文件")
    max_size = 20 * 1024 * 1024
    payload: list[tuple[bytes, str]] = []
    for upload in files:
        if not upload.filename:
            raise HTTPException(status_code=400, detail="请选择 CSV 文件")
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"文件为空: {upload.filename}")
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail=f"{upload.filename} 过大，单文件最大 20MB")
        payload.append((content, upload.filename))
    return payload


async def _read_image_uploads(files: list[UploadFile]) -> list[tuple[bytes, str]]:
    if not files:
        raise HTTPException(status_code=400, detail="请选择图片文件")

    max_size = 50 * 1024 * 1024
    payload: list[tuple[bytes, str]] = []
    for upload in files:
        if not upload.filename:
            raise HTTPException(status_code=400, detail="请选择图片文件")
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"文件为空: {upload.filename}")
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail=f"{upload.filename} 过大，单文件最大 50MB")
        payload.append((content, upload.filename))
    return payload


async def _read_pdf_uploads(
    files: list[UploadFile],
    *,
    min_count: int,
) -> list[tuple[bytes, str]]:
    if not files or len(files) < min_count:
        raise HTTPException(
            status_code=400,
            detail="请至少选择 2 个 PDF 文件" if min_count > 1 else "请选择 PDF 文件",
        )

    payload: list[tuple[bytes, str]] = []
    for upload in files:
        if not upload.filename:
            raise HTTPException(status_code=400, detail="请选择 PDF 文件")
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"文件为空: {upload.filename}")
        if len(content) > 80 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"{upload.filename} 过大，单文件最大 80MB")
        payload.append((content, upload.filename))
    return payload


def _pdf_file_response(result) -> FileResponse:
    headers = {
        "X-Original-Size": str(result.original_size),
        "X-Output-Size": str(result.output_size),
        "X-Pdf-Message": quote(result.message, safe=""),
        "X-Pdf-Pages": str(result.pages),
    }
    return FileResponse(
        path=result.path,
        media_type=result.mime,
        filename=result.filename,
        headers=headers,
        background=BackgroundTask(_cleanup, result.path),
    )


def _batch_zip_response(payload, handler, zip_name: str) -> FileResponse:
    try:
        batch = run_batch(payload, handler, zip_name=zip_name, lang=current_lang.get())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    error_payload = [{"name": item.name, "detail": item.detail} for item in batch.errors]
    headers = {
        "X-Batch-Ok": str(len(batch.ok)),
        "X-Batch-Failed": str(len(batch.errors)),
        "X-Batch-Errors": quote(json.dumps(error_payload, ensure_ascii=False), safe=""),
    }
    return FileResponse(
        path=batch.zip_path,
        media_type="application/zip",
        filename=batch.zip_name,
        headers=headers,
        background=BackgroundTask(_cleanup, batch.zip_path),
    )


def _cleanup(path: Path) -> None:
    path.unlink(missing_ok=True)


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
