"""Read and write the table formats data-kondo accepts: CSV (any common delimiter), TSV, JSON, JSONL and Excel.

Everything is converted to CSV text for profiling and cleaning, then written back in the format the output file
name asks for. Excel is read with the standard library (an .xlsx file is a zip of XML); the first sheet is used
unless one is named, and date-formatted cells come out as ISO dates.
"""

from __future__ import annotations

import csv
import io
import json
import pathlib
import re
import zipfile
from datetime import date, timedelta
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
DATE_FMT_IDS = set(range(14, 23)) | {45, 46, 47}
EXCEL_EPOCH = date(1899, 12, 30)
TABLE_EXTS = (".csv", ".tsv", ".txt", ".json", ".jsonl", ".ndjson", ".xlsx")


def _to_csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _records(records: list) -> str:
    if not all(isinstance(r, dict) for r in records):
        raise ValueError("JSON must be a list of objects (one object per row)")
    header: list[str] = []
    for r in records:
        header.extend(k for k in r if k not in header)
    return _to_csv(header, [[_cell(r.get(k)) for k in header] for r in records])


def _json(text: str) -> str:
    doc = json.loads(text)
    if isinstance(doc, dict):  # {"data": [...]} / {"rows": [...]} / {"records": [...]}
        lists = [v for v in doc.values() if isinstance(v, list)]
        if len(lists) != 1:
            raise ValueError("JSON object must hold exactly one list of rows")
        doc = lists[0]
    if not isinstance(doc, list):
        raise ValueError("JSON must be a list of objects")
    return _records(doc)


def _jsonl(text: str) -> str:
    recs = []
    for n, line in enumerate(text.splitlines(), 1):
        if line.strip():
            try:
                recs.append(json.loads(line))
            except ValueError as e:
                raise ValueError(f"line {n} is not JSON: {e}") from None
    return _records(recs)


def _delimited(text: str, delimiter: str | None = None) -> str:
    if delimiter is None:
        sample = text[:20000]
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    if delimiter == ",":
        return text
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    return _to_csv(rows[0], rows[1:]) if rows else ""


def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def _xlsx(data: bytes, sheet: str | None = None) -> str:
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("not a valid .xlsx file") from None
    with z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        date_styles = set()
        if "xl/styles.xml" in names:
            st = ET.fromstring(z.read("xl/styles.xml"))
            custom = {int(f.get("numFmtId")): f.get("formatCode", "") for f in st.findall("m:numFmts/m:numFmt", NS)}
            for i, xf in enumerate(st.findall("m:cellXfs/m:xf", NS)):
                fid = int(xf.get("numFmtId", "0"))
                code = re.sub(r'"[^"]*"|\[[^\]]*\]', "", custom.get(fid, "")).lower()
                if fid in DATE_FMT_IDS or (fid in custom and re.search(r"[dy]", code)):
                    date_styles.add(i)
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        sheets = wb.findall("m:sheets/m:sheet", NS)
        if not sheets:
            raise ValueError("the workbook has no sheets")
        chosen = next((s for s in sheets if s.get("name") == sheet), None) if sheet else sheets[0]
        if chosen is None:
            raise ValueError(f"no sheet named {sheet!r}; sheets: {[s.get('name') for s in sheets]}")
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = next(r.get("Target") for r in rels if r.get("Id") == chosen.get(REL))
        path = target.lstrip("/") if target.startswith("/") else f"xl/{target}"
        grid: dict[int, dict[int, str]] = {}
        for row in ET.fromstring(z.read(path)).iter(f"{{{NS['m']}}}row"):
            r = int(row.get("r")) - 1
            for c in row.findall("m:c", NS):
                t, v = c.get("t", "n"), c.find("m:v", NS)
                if t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
                elif v is None:
                    continue
                elif t == "s":
                    val = shared[int(v.text)]
                elif t == "b":
                    val = "true" if v.text == "1" else "false"
                elif t in ("str", "e"):
                    val = v.text or ""
                elif int(c.get("s", "0")) in date_styles:
                    val = (EXCEL_EPOCH + timedelta(days=float(v.text))).isoformat()
                else:
                    num = float(v.text)
                    val = str(int(num)) if num.is_integer() and abs(num) < 1e15 else v.text
                grid.setdefault(r, {})[_col(c.get("r"))] = val
    if not grid:
        return ""
    width = max(max(cols) for cols in grid.values()) + 1
    table = [[grid.get(r, {}).get(i, "") for i in range(width)] for r in range(max(grid) + 1)]
    while table and not any(table[0]):  # skip blank rows above the header
        table.pop(0)
    return _to_csv(table[0], table[1:]) if table else ""


def load_table(path: str, sheet: str | None = None) -> str:
    """Return the file at path as CSV text."""
    ext = pathlib.Path(path).suffix.lower()
    if ext == ".xlsx":
        with open(path, "rb") as fh:
            return _xlsx(fh.read(), sheet)
    if ext == ".xls":
        raise ValueError("old .xls files are not supported; save as .xlsx or CSV")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    if ext == ".json":
        return _json(text)
    if ext in (".jsonl", ".ndjson"):
        return _jsonl(text)
    if ext == ".tsv":
        return _delimited(text, "\t")
    return _delimited(text)


def write_table(path: str, csv_text: str):
    """Write CSV text to path in the format its extension names (.csv, .tsv, .json, .jsonl)."""
    ext = pathlib.Path(path).suffix.lower()
    rows = list(csv.reader(io.StringIO(csv_text)))
    header, body = (rows[0], rows[1:]) if rows else ([], [])
    with open(path, "w", encoding="utf-8", newline="") as fh:
        if ext == ".json":
            json.dump([dict(zip(header, r)) for r in body], fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        elif ext in (".jsonl", ".ndjson"):
            for r in body:
                fh.write(json.dumps(dict(zip(header, r)), ensure_ascii=False) + "\n")
        elif ext == ".tsv":
            csv.writer(fh, delimiter="\t", lineterminator="\n").writerows(rows)
        else:
            fh.write(csv_text)
