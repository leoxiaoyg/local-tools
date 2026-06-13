from pathlib import Path
from urllib.parse import quote
import base64
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from app.converter import AUDIO_FORMATS, convert_uploaded_file
from app.csv_excel import csv_to_excel, excel_to_csv
from app.image_compressor import OUTPUT_FORMATS, compress_image
from app.image_transform import EXPORT_FORMATS, transform_image
from app.video_compressor import RESOLUTIONS, VIDEO_OUTPUT, compress_video_file

app = FastAPI(title="Local Tools", version="2.0.0")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/api/formats")
def list_formats():
    return [
        {"id": key, "label": val["label"], "ext": val["ext"]}
        for key, val in AUDIO_FORMATS.items()
    ]


@app.get("/api/image/formats")
def list_image_formats():
    return [
        {"id": key, "label": val["label"]}
        for key, val in OUTPUT_FORMATS.items()
    ]


@app.get("/api/image/export-formats")
def list_image_export_formats():
    return [{"id": k, "label": v["label"]} for k, v in EXPORT_FORMATS.items()]


@app.get("/api/video/compress-options")
def list_video_compress_options():
    return {
        "formats": [{"id": k, "label": v["label"]} for k, v in VIDEO_OUTPUT.items()],
        "resolutions": [{"id": k, "label": v["label"]} for k, v in RESOLUTIONS.items()],
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

    max_size = 500 * 1024 * 1024
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

    max_size = 500 * 1024 * 1024
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


def _cleanup(path: Path) -> None:
    path.unlink(missing_ok=True)


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
