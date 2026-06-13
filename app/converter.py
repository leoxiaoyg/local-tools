import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

AUDIO_FORMATS = {
    "mp3": {
        "label": "MP3",
        "ext": "mp3",
        "mime": "audio/mpeg",
        "args": ["-c:a", "libmp3lame", "-q:a", "2"],
    },
    "wav": {
        "label": "WAV",
        "ext": "wav",
        "mime": "audio/wav",
        "args": ["-c:a", "pcm_s16le"],
    },
    "aac": {
        "label": "AAC",
        "ext": "aac",
        "mime": "audio/aac",
        "args": ["-c:a", "aac", "-b:a", "192k"],
    },
    "m4a": {
        "label": "M4A",
        "ext": "m4a",
        "mime": "audio/mp4",
        "args": ["-c:a", "aac", "-b:a", "192k"],
    },
    "ogg": {
        "label": "OGG",
        "ext": "ogg",
        "mime": "audio/ogg",
        "args": ["-c:a", "libvorbis", "-q:a", "5"],
    },
    "flac": {
        "label": "FLAC",
        "ext": "flac",
        "mime": "audio/flac",
        "args": ["-c:a", "flac"],
    },
}

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpeg", ".mpg", ".3gp", ".ts",
}


def get_format_info(fmt: str) -> dict:
    if fmt not in AUDIO_FORMATS:
        raise ValueError(f"不支持的格式: {fmt}")
    return AUDIO_FORMATS[fmt]


def extract_audio(input_path: Path, output_path: Path, fmt: str) -> None:
    info = get_format_info(fmt)
    cmd = [
        FFMPEG,
        "-y",
        "-i", str(input_path),
        "-vn",
        *info["args"],
        str(output_path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "未知错误"
        raise RuntimeError(f"音频提取失败: {stderr[-500:]}")


def convert_uploaded_file(file_bytes: bytes, original_name: str, fmt: str) -> tuple[Path, dict]:
    suffix = Path(original_name).suffix.lower()
    if suffix and suffix not in VIDEO_EXTENSIONS:
        raise ValueError(f"不支持的视频格式: {suffix}")

    info = get_format_info(fmt)
    stem = Path(original_name).stem or "audio"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".mp4") as tmp_in:
        tmp_in.write(file_bytes)
        input_path = Path(tmp_in.name)

    output_path = input_path.with_suffix(f".{info['ext']}")
    output_path = output_path.parent / f"{stem}.{info['ext']}"

    try:
        extract_audio(input_path, output_path, fmt)
    finally:
        input_path.unlink(missing_ok=True)

    if not output_path.exists():
        raise RuntimeError("转换完成但未生成输出文件")

    return output_path, {**info, "filename": output_path.name}
