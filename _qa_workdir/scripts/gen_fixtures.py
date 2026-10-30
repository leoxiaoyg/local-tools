"""在 _qa_workdir/fixtures 生成全部用例输入。勿写到其它目录。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import fitz
import imageio_ffmpeg
from PIL import Image
from PIL.ExifTags import Base as ExifBase

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "_qa_workdir" / "fixtures"


def make_image(path: Path, color: str, size=(240, 180)) -> None:
    Image.new("RGB", size, color).save(path, quality=92)


def make_exif_jpeg(path: Path) -> None:
    img = Image.new("RGB", (320, 240), "green")
    exif = img.getexif()
    exif[ExifBase.Make] = "LocalToolsQA"
    exif[ExifBase.Model] = "FixtureCam"
    exif[ExifBase.DateTime] = "2026:10:26 12:00:00"
    img.save(path, quality=92, exif=exif)


def make_pdf(path: Path, text: str, pages: int = 1) -> None:
    doc = fitz.open()
    for index in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"{text} {index + 1}")
    doc.save(path)
    doc.close()


def make_video(path: Path) -> None:
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-f", "lavfi", "-i", "testsrc=size=160x120:rate=8:duration=1",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        "-c:a", "aac",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0 or not path.exists():
        raise SystemExit(f"make video failed\n{result.stderr[-800:]}")


def make_csv(path: Path) -> None:
    path.write_text(
        "sku,name,extra\n"
        "A1,苹果,x\n"
        "\n"
        "A1,苹果,x\n"
        "B2,香蕉,y\n",
        encoding="utf-8",
    )


def main() -> int:
    FIX.mkdir(parents=True, exist_ok=True)
    make_image(FIX / "a.jpg", "red")
    make_image(FIX / "b.png", "blue")
    make_exif_jpeg(FIX / "a_exif.jpg")
    make_pdf(FIX / "one.pdf", "one")
    make_pdf(FIX / "two.pdf", "two")
    make_csv(FIX / "dirty.csv")
    (FIX / "not_image.txt").write_text("not an image\n", encoding="utf-8")
    make_video(FIX / "clip.mp4")
    print(f"FIXTURES_OK {FIX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
