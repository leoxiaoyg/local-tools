"""批量处理：逐条 handler → zip。供 Web / 未来 CLI 共用。"""

from __future__ import annotations

import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

MAX_FILES_DEFAULT = 50
MAX_TOTAL_BYTES_DEFAULT = 200 * 1024 * 1024

HandlerResult = Path | bytes | tuple[Path | bytes, str]
Handler = Callable[[bytes, str], HandlerResult]


@dataclass
class BatchError:
    name: str
    detail: str


@dataclass
class BatchOk:
    name: str
    output_name: str


@dataclass
class BatchResult:
    zip_path: Path
    zip_name: str
    ok: list[BatchOk]
    errors: list[BatchError]


def safe_entry_name(name: str) -> str:
    base = Path(name).name.replace("\\", "_").replace("/", "_")
    if not base or base in {".", ".."}:
        return "file.bin"
    return base


def _unique_name(used: set[str], name: str) -> str:
    name = safe_entry_name(name)
    if name not in used:
        used.add(name)
        return name
    stem = Path(name).stem
    suffix = Path(name).suffix
    index = 2
    while True:
        candidate = f"{stem}_{index}{suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def _normalize_handler_output(result: HandlerResult) -> tuple[bytes, str]:
    if isinstance(result, tuple) and len(result) >= 2:
        data, name = result[0], str(result[1])
        if isinstance(data, Path):
            content = data.read_bytes()
            data.unlink(missing_ok=True)
            return content, name
        if isinstance(data, (bytes, bytearray)):
            return bytes(data), name
        raise TypeError("handler 返回的元组首项须为 Path 或 bytes")

    if isinstance(result, Path):
        content = result.read_bytes()
        name = result.name
        result.unlink(missing_ok=True)
        return content, name

    if isinstance(result, (bytes, bytearray)):
        return bytes(result), "output.bin"

    raise TypeError("不支持的 handler 返回类型")


def run_batch(
    files: list[tuple[bytes, str]],
    handler: Handler,
    *,
    max_files: int = MAX_FILES_DEFAULT,
    max_total_bytes: int = MAX_TOTAL_BYTES_DEFAULT,
    zip_name: str = "results.zip",
    fail_mode: str = "continue",
) -> BatchResult:
    if not files:
        raise ValueError("请选择文件")
    if len(files) > max_files:
        raise ValueError(f"一次最多处理 {max_files} 个文件")

    total = sum(len(data) for data, _ in files)
    if total > max_total_bytes:
        limit_mb = max_total_bytes // (1024 * 1024)
        raise ValueError(f"文件总大小超过上限（最大 {limit_mb}MB）")

    if fail_mode not in {"continue", "fail_fast"}:
        raise ValueError("fail_mode 仅支持 continue 或 fail_fast")

    ok: list[BatchOk] = []
    errors: list[BatchError] = []
    entries: list[tuple[str, bytes]] = []
    used_names: set[str] = set()

    for data, name in files:
        display = safe_entry_name(name)
        try:
            if not data:
                raise ValueError("文件为空")
            out_bytes, out_name = _normalize_handler_output(handler(data, name))
            if not out_bytes:
                raise RuntimeError("处理完成但输出为空")
            entry = _unique_name(used_names, out_name)
            entries.append((entry, out_bytes))
            ok.append(BatchOk(name=display, output_name=entry))
        except Exception as exc:
            errors.append(BatchError(name=display, detail=str(exc)))
            if fail_mode == "fail_fast":
                break

    if not ok:
        preview = "；".join(f"{item.name}: {item.detail}" for item in errors[:5])
        raise ValueError(f"全部文件处理失败。{preview}")

    archive_name = safe_entry_name(zip_name)
    if not archive_name.lower().endswith(".zip"):
        archive_name = f"{archive_name}.zip"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        zip_path = Path(tmp.name)

    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for entry_name, content in entries:
                archive.writestr(entry_name, content)
            if errors:
                lines = ["# 失败清单", ""]
                lines.extend(f"{item.name}\t{item.detail}" for item in errors)
                archive.writestr("errors.txt", "\n".join(lines) + "\n")
    except Exception:
        zip_path.unlink(missing_ok=True)
        raise

    return BatchResult(
        zip_path=zip_path,
        zip_name=archive_name,
        ok=ok,
        errors=errors,
    )
