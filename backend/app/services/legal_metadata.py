"""Shared conversion for parser/backend/guardrail boundaries."""
import calendar
import re
from datetime import date, datetime


def date_status(effective, expiry, as_of):
    """Trạng thái hiệu lực suy ra từ ngày tại as_of; không phải xác minh pháp lý."""
    day = lambda v: v.date() if isinstance(v, datetime) else v
    effective, expiry, as_of = day(effective), day(expiry), day(as_of)
    if expiry is not None and as_of >= expiry:
        return "HET_HIEU_LUC"
    if effective is None:
        return "CHUA_XAC_DINH"
    return "CHUA_CO_HIEU_LUC" if as_of < effective else "CON_HIEU_LUC"


def clause_label(value):
    if value is None:
        return None
    label = str(value).strip()
    return None if label in {"", "0"} else label


def period_bounds(value):
    """Inclusive bounds for explicit year/month/quarter; never guess free text."""
    if not value:
        return None
    value = value.strip()
    if re.fullmatch(r"\d{4}", value):
        year = int(value)
        return date(year, 1, 1), date(year, 12, 31)
    if re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    if re.fullmatch(r"\d{4}-Q[1-4]", value):
        year, quarter = int(value[:4]), int(value[-1])
        month = quarter * 3
        return date(year, month - 2, 1), date(year, month, calendar.monthrange(year, month)[1])
    raise ValueError("Kỳ thuế cần dạng YYYY, YYYY-MM hoặc YYYY-Q1..Q4.")
