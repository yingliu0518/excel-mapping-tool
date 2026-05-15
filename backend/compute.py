from datetime import datetime, date

import pandas as pd


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y.%m.%d",
)


def _parse_date(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day)
    s = str(val).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    parsed = pd.to_datetime(s, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _parse_num(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    n = pd.to_numeric(val, errors="coerce")
    if pd.isna(n):
        return None
    return float(n)


def _max_date(row, cols):
    vals = [d for c in cols if (d := _parse_date(row.get(c))) is not None]
    return max(vals) if vals else ""


def _min_date(row, cols):
    vals = [d for c in cols if (d := _parse_date(row.get(c))) is not None]
    return min(vals) if vals else ""


def _max_num(row, cols):
    vals = [n for c in cols if (n := _parse_num(row.get(c))) is not None]
    return max(vals) if vals else ""


def _min_num(row, cols):
    vals = [n for c in cols if (n := _parse_num(row.get(c))) is not None]
    return min(vals) if vals else ""


def _concat(row, cols):
    parts = []
    for c in cols:
        v = row.get(c)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            continue
        parts.append(str(v))
    return "".join(parts)


COMPUTE_FUNCTIONS = {
    "max_date": _max_date,
    "min_date": _min_date,
    "max_num": _max_num,
    "min_num": _min_num,
    "concat": _concat,
}
