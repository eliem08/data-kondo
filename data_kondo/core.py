"""CSV profiling, agent-readiness scoring and cleaning."""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from datetime import datetime

__all__ = ["NULL_TOKENS", "infer_type", "profile", "readiness", "clean", "snake"]

NULL_TOKENS = {"", "na", "n/a", "null", "none", "nil", "-", "--", "?", "nan", "#n/a"}
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%d-%m-%Y", "%b %d %Y", "%d %b %Y", "%Y%m%d"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[\d\s().-]{7,20}$")
BOOL_MAP = {
    "true": "true",
    "yes": "true",
    "y": "true",
    "1": "true",
    "false": "false",
    "no": "false",
    "n": "false",
    "0": "false",
}


def snake(name: str) -> str:
    s = re.sub(r"\(.*?\)", "", name)
    s = re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_").lower()
    return s or "column"


def is_null(v: str) -> bool:
    return v.strip().lower() in NULL_TOKENS


def parse_date(v: str) -> str | None:
    v = v.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def infer_type(v: str) -> str:
    v = v.strip()
    if re.fullmatch(r"-?\d+", v):
        return "int"
    if re.fullmatch(r"-?\d*\.\d+", v):
        return "float"
    if v.lower() in BOOL_MAP and not v.isdigit():
        return "bool"
    if EMAIL_RE.match(v):
        return "email"
    if parse_date(v):
        return "date"
    if PHONE_RE.match(v) and sum(c.isdigit() for c in v) >= 7:
        return "phone"
    return "text"


def _read(text: str):
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], []
    return rows[0], [r + [""] * (len(rows[0]) - len(r)) for r in rows[1:]]


def profile(text: str) -> dict:
    header, rows = _read(text)
    cols = []
    for i, name in enumerate(header):
        vals = [r[i] for r in rows]
        non_null = [v for v in vals if not is_null(v)]
        types = Counter(infer_type(v) for v in non_null)
        null_variants = {v for v in vals if is_null(v)}
        date_formats = {fmt for v in non_null if infer_type(v) == "date" for fmt in DATE_FORMATS if _fmt_ok(v, fmt)}
        cols.append(
            {
                "name": name,
                "type": types.most_common(1)[0][0] if types else "empty",
                "type_mix": dict(types),
                "null_rate": 1 - len(non_null) / len(vals) if vals else 1.0,
                "null_variants": sorted(null_variants),
                "distinct": len(set(non_null)),
                "whitespace_issues": sum(1 for v in non_null if v != v.strip() or "  " in v),
                "date_formats": len(date_formats),
            }
        )
    dupes = len(rows) - len({tuple(r) for r in rows})
    return {
        "rows": len(rows),
        "columns": cols,
        "duplicate_rows": dupes,
        "header_issues": [h for h in header if snake(h) != h],
    }


def _fmt_ok(v, fmt):
    try:
        datetime.strptime(v.strip(), fmt)
        return True
    except ValueError:
        return False


def readiness(prof: dict) -> tuple[int, list[str]]:
    score, issues = 100.0, []
    if prof["header_issues"]:
        score -= min(15, 3 * len(prof["header_issues"]))
        issues.append(f"{len(prof['header_issues'])} headers not snake_case")
    if prof["duplicate_rows"]:
        score -= min(15, 100 * prof["duplicate_rows"] / max(prof["rows"], 1))
        issues.append(f"{prof['duplicate_rows']} duplicate rows")
    for c in prof["columns"]:
        if c["type"] == "empty":
            score -= 5
            issues.append(f"{c['name']}: entirely empty")
            continue
        if len(c["null_variants"]) > 1:
            score -= 4
            issues.append(f"{c['name']}: {len(c['null_variants'])} different null spellings")
        if len(c["type_mix"]) > 1:
            score -= 4
            issues.append(f"{c['name']}: mixed types {c['type_mix']}")
        if c["date_formats"] > 1:
            score -= 5
            issues.append(f"{c['name']}: {c['date_formats']} date formats")
        if c["whitespace_issues"]:
            score -= 2
            issues.append(f"{c['name']}: {c['whitespace_issues']} values with stray whitespace")
    return max(0, round(score)), issues


def _clean_value(v: str, ctype: str) -> str:
    if is_null(v):
        return ""
    v = re.sub(r"\s+", " ", v.strip())
    if ctype == "date":
        return parse_date(v) or v
    if ctype == "email":
        return v.lower()
    if ctype == "phone":
        return ("+" if v.startswith("+") else "") + re.sub(r"\D", "", v)
    if ctype == "bool":
        return BOOL_MAP.get(v.lower(), v)
    return v


def clean(text: str, key: str | None = None) -> tuple[str, list[str]]:
    prof = profile(text)
    header, rows = _read(text)
    log = []
    keep = [i for i, c in enumerate(prof["columns"]) if c["type"] != "empty"]
    for i, c in enumerate(prof["columns"]):
        if i not in keep:
            log.append(f"dropped empty column {c['name']!r}")
    new_header, seen = [], Counter()
    for i in keep:
        h = snake(header[i])
        seen[h] += 1
        h = h if seen[h] == 1 else f"{h}_{seen[h]}"
        if h != header[i]:
            log.append(f"renamed {header[i]!r} -> {h!r}")
        new_header.append(h)
    out_rows, seen_keys, changed = [], set(), 0
    key_idx = new_header.index(key) if key and key in new_header else None
    for r in rows:
        new = [_clean_value(r[i], prof["columns"][i]["type"]) for i in keep]
        changed += sum(1 for i, nv in zip(keep, new) if nv != r[i])
        k = new[key_idx] if key_idx is not None else tuple(new)
        if k in seen_keys and k != "":
            continue
        seen_keys.add(k)
        out_rows.append(new)
    if len(out_rows) != len(rows):
        log.append(
            f"removed {len(rows) - len(out_rows)} duplicate rows" + (f" by {key}" if key_idx is not None else "")
        )
    log.append(f"normalised {changed} cell values")
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(new_header)
    w.writerows(out_rows)
    return buf.getvalue(), log
