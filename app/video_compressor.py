import subprocess
import tempfile
from pathlib import Path

from app.converter import FFMPEG, MAX_VIDEO_BYTES, VIDEO_EXTENSIONS

VIDEO_OUTPUT = {
    "mp4": {
        "label": "MP4 (H.264)",
        "ext": "mp4",
        "mime": "video/mp4",
        "video_codec": ["-c:v", "libx264", "-preset", "medium"],
        "audio_codec": ["-c:a", "aac", "-b:a", "128k"],
        "extra": ["-movflags", "+faststart"],
    },
    "webm": {
        "label": "WebM (VP9)",
        "ext": "webm",
        "mime": "video/webm",
        "video_codec": ["-c:v", "libvpx-vp9", "-row-mt", "1"],
        "audio_codec": ["-c:a", "libopus", "-b:a", "128k"],
        "extra": [],
    },
}

RESOLUTIONS = {
    "original": {"label": "保持原分辨率", "max_height": None},
    "1080": {"label": "最大 1080p", "max_height": 1080},
    "720": {"label": "最大 720p", "max_height": 720},
    "480": {"label": "最大 480p", "max_height": 480},
}


def compress_video_file(
    file_bytes: bytes,
    original_name: str,
    output_format: str = "mp4",
    crf: int = 23,
    resolution: str = "original",
) -> tuple[Path, dict]:
    if not file_bytes:
        raise ValueError("文件为空")
    if len(file_bytes) > MAX_VIDEO_BYTES:
        raise ValueError("文件过大，最大支持 500MB")
    if output_format not in VIDEO_OUTPUT:
        raise ValueError(f"不支持的输出格式: {output_format}")

    suffix = Path(original_name).suffix.lower()
    if suffix and suffix not in VIDEO_EXTENSIONS:
        raise ValueError(f"不支持的视频格式: {suffix}")

    crf = max(18, min(35, crf))
    res = RESOLUTIONS.get(resolution, RESOLUTIONS["original"])
    info = VIDEO_OUTPUT[output_format]
    stem = Path(original_name).stem or "video"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".mp4") as tmp_in:
        tmp_in.write(file_bytes)
        input_path = Path(tmp_in.name)

    output_path = input_path.parent / f"{stem}_compressed.{info['ext']}"

    cmd = [FFMPEG, "-y", "-i", str(input_path)]
    if res["max_height"]:
        cmd.extend(["-vf", f"scale=-2:'min(ih,{res['max_height']})'"])
    cmd.extend(info["video_codec"])
    cmd.extend(["-crf", str(crf)])
    cmd.extend(info["audio_codec"])
    cmd.extend(info["extra"])
    cmd.append(str(output_path))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or "未知错误"
            raise RuntimeError(f"视频压缩失败: {stderr[-500:]}")
    finally:
        input_path.unlink(missing_ok=True)

    if not output_path.exists():
        raise RuntimeError("压缩完成但未生成输出文件")

    return output_path, {
        "filename": output_path.name,
        "mime": info["mime"],
        "format": output_format,
    }
