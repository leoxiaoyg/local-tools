"""CSV 清洗：去空行、去重、留列。不做透视或公式。"""

from __future__ import annotations

import csv
import io
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.csv_excel import _decode_text

MAX_CSV_BYTES = 20 * 1024 * 1024
MAX_ROWS = 200_000


@dataclass
class CleanResult:
    path: Path
    filename: str
    mime: str
    original_size: int
    output_size: int
    message: str
    rows_in: int
    rows_out: int


def clean_csv(
    content: bytes,
    filename: str,
    *,
    drop_empty: bool = True,
    dedupe: bool = True,
    keep_columns: str = "",
) -> CleanResult:
    name = Path(filename).name
    if Path(filename).suffix.lower() != ".csv":
        raise ValueError(f"请上传 CSV 文件: {name or '未知'}")
    if not content:
        raise ValueError(f"文件为空: {name}")
    if len(content) > MAX_CSV_BYTES:
        raise ValueError(f"{name} 过大，单文件最大 20MB")

    text = _decode_text(content)
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise ValueError("CSV 文件为空")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"行数过多（最多 {MAX_ROWS} 行）")

    header = [_cell(value) for value in rows[0]]
    if not any(header):
        raise ValueError("表头为空")

    indexes = _resolve_columns(header, keep_columns)
    projected_header = [header[i] for i in indexes]
    body = [[_cell(row[i] if i < len(row) else "") for i in indexes] for row in rows[1:]]

    empty_dropped = 0
    if drop_empty:
        kept: list[list[str]] = []
        for row in body:
            if any(row):
                kept.append(row)
            else:
                empty_dropped += 1
        body = kept

    dup_dropped = 0
    if dedupe:
        seen: set[tuple[str, ...]] = set()
        unique: list[list[str]] = []
        for row in body:
            key = tuple(row)
            if key in seen:
                dup_dropped += 1
                continue
            seen.add(key)
            unique.append(row)
        body = unique

    out_rows = [projected_header, *body]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(out_rows)
    csv_text = buf.getvalue()

    stem = Path(filename).stem or "data"
    out_name = f"{stem}_clean.csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        path = Path(tmp.name)
    path.write_text(csv_text, encoding="utf-8-sig")

    bits = [f"去掉空行 {empty_dropped}", f"去重 {dup_dropped}", f"保留 {len(indexes)} 列"]
    return CleanResult(
        path=path,
        filename=out_name,
        mime="text/csv; charset=utf-8",
        original_size=len(content),
        output_size=path.stat().st_size,
        message="已清洗：" + " · ".join(bits),
        rows_in=max(0, len(rows) - 1),
        rows_out=len(body),
    )


def _cell(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _resolve_columns(header: list[str], spec: str) -> list[int]:
    cleaned = spec.replace("，", ",").strip()
    if not cleaned:
        return list(range(len(header)))

    indexes: list[int] = []
    seen: set[int] = set()
    for part in [item.strip() for item in cleaned.split(",") if item.strip()]:
        if part.isdigit():
            index = int(part)
            if index < 1 or index > len(header):
                raise ValueError(f"列序号 {part} 超出范围（共 {len(header)} 列）")
            resolved = index - 1
        else:
            matches = [i for i, name in enumerate(header) if name == part]
            if not matches:
                raise ValueError(f"找不到列: {part}")
            resolved = matches[0]
        if resolved not in seen:
            seen.add(resolved)
            indexes.append(resolved)
    if not indexes:
        raise ValueError("请填写要保留的列，例如 sku,name 或 1,3")
    return indexes
