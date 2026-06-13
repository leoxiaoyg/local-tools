import csv
import io
import tempfile
from pathlib import Path

from openpyxl import Workbook, load_workbook


def csv_to_excel(content: bytes, original_name: str) -> tuple[Path, str]:
    text = _decode_text(content)
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV 文件为空")

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for row in rows:
        ws.append(row)

    stem = Path(original_name).stem or "data"
    out_name = f"{stem}.xlsx"
    output_path = Path(tempfile.mktemp(suffix=".xlsx"))
    wb.save(output_path)
    return output_path, out_name


def excel_to_csv(content: bytes, original_name: str, sheet: str = "0") -> tuple[Path, str]:
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".xlsx", ".xlsm"}:
        raise ValueError("仅支持 .xlsx / .xlsm 格式")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        input_path = Path(tmp.name)

    try:
        wb = load_workbook(input_path, read_only=True, data_only=True)
        if sheet.isdigit():
            ws = wb.worksheets[int(sheet)]
        else:
            ws = wb[sheet] if sheet in wb.sheetnames else wb.active

        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        for row in ws.iter_rows(values_only=True):
            writer.writerow(["" if cell is None else cell for cell in row])
        csv_text = buf.getvalue()
    finally:
        input_path.unlink(missing_ok=True)

    if not csv_text.strip():
        raise ValueError("表格为空")

    stem = Path(original_name).stem or "data"
    out_name = f"{stem}.csv"
    output_path = Path(tempfile.mktemp(suffix=".csv"))
    output_path.write_text(csv_text, encoding="utf-8-sig")
    return output_path, out_name


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别 CSV 文件编码")
