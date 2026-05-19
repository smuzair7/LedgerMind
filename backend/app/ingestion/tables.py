"""Turn ParsedTable instances into typed Fact rows.

The classifier is heuristic — header keywords in EN + AR plus a small synonym
map for common line items. We intentionally bias toward emitting MORE facts
with raw line-item names; tool calls use both canonical and raw matches.

Numeric parsing handles:
  - Thousands separators in AR ("1,234,567" / "١٬٢٣٤٬٥٦٧")
  - Parentheses-as-negative ("(123)" → -123)
  - Trailing scale markers in headers ("in thousands of USD" → unit_scale 1000)
  - AR-Indic digits → Latin digits before parsing
"""

from __future__ import annotations

import hashlib
import re

from app.calculations.types import Fact
from app.ingestion.arabic import looks_arabic, normalize_arabic
from app.ingestion.parser_docling import ParsedTable

# --- Statement detection ---------------------------------------------------

_STATEMENT_HINTS: dict[str, tuple[str, ...]] = {
    "income": (
        "income statement",
        "statement of operations",
        "statement of comprehensive income",
        "profit or loss",
        "قائمة الدخل",
        "قائمة الأرباح",
        "بيان الدخل",
    ),
    "balance": (
        "balance sheet",
        "statement of financial position",
        "قائمة المركز المالي",
        "الميزانية",
    ),
    "cashflow": (
        "cash flow",
        "statement of cash flows",
        "قائمة التدفقات النقدية",
    ),
    "equity": (
        "statement of equity",
        "changes in equity",
        "قائمة حقوق الملكية",
    ),
}

# --- Line item canonical map ----------------------------------------------

_LINE_ITEM_CANONICAL: dict[str, tuple[str, ...]] = {
    "Revenue": ("revenue", "net revenue", "sales", "net sales", "total revenue", "الإيرادات", "صافي الإيرادات", "المبيعات"),
    "Cost of revenue": ("cost of revenue", "cost of sales", "cost of goods sold", "cogs", "تكلفة الإيرادات", "تكلفة المبيعات"),
    "Gross profit": ("gross profit", "إجمالي الربح", "الربح الإجمالي"),
    "Operating expenses": ("operating expenses", "total operating expenses", "المصروفات التشغيلية"),
    "Operating income": ("operating income", "income from operations", "operating profit", "الدخل التشغيلي", "الربح التشغيلي"),
    "Net income": ("net income", "net profit", "net earnings", "صافي الدخل", "صافي الربح"),
    "Total assets": ("total assets", "إجمالي الأصول"),
    "Total liabilities": ("total liabilities", "إجمالي الالتزامات", "إجمالي المطلوبات"),
    "Total equity": ("total equity", "total stockholders equity", "حقوق المساهمين", "حقوق الملكية"),
    "Current assets": ("current assets", "total current assets", "الأصول المتداولة"),
    "Current liabilities": ("current liabilities", "total current liabilities", "الالتزامات المتداولة"),
    "Cash and equivalents": ("cash and cash equivalents", "cash", "النقد", "النقد وما في حكمه"),
    "Inventory": ("inventory", "inventories", "المخزون"),
    "Cash from operations": ("net cash from operating activities", "cash from operations", "النقد من الأنشطة التشغيلية"),
    "Interest expense": ("interest expense", "مصروف الفوائد", "تكاليف التمويل"),
}


def _canonicalize_line_item(label: str) -> str | None:
    """Longest-matching alias wins so 'cost of sales' beats 'sales'."""
    lo = label.strip().lower()
    best: tuple[int, str] | None = None
    for canonical, aliases in _LINE_ITEM_CANONICAL.items():
        for a in aliases:
            if a in lo and (best is None or len(a) > best[0]):
                best = (len(a), canonical)
    return best[1] if best else None


# --- Period detection ------------------------------------------------------

_FY_RE = re.compile(r"\b(?:fy|f\.y\.|year ended)\s*(20\d{2})\b", re.IGNORECASE)
_FOUR_DIGIT_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_QUARTER_RE = re.compile(r"\bq([1-4])\s*(20\d{2})\b", re.IGNORECASE)
_HALF_RE = re.compile(r"\bh([12])\s*(20\d{2})\b", re.IGNORECASE)


def _detect_period(label: str) -> tuple[str, str] | None:
    """Return (period_label, period_kind) or None."""
    lo = label.translate(_AR_DIGIT_TRANS).strip().lower()
    m = _QUARTER_RE.search(lo)
    if m:
        return (f"Q{m.group(1)} {m.group(2)}", "quarter")
    m = _HALF_RE.search(lo)
    if m:
        return (f"H{m.group(1)} {m.group(2)}", "half")
    m = _FY_RE.search(lo)
    if m:
        return (f"FY{m.group(1)}", "fy")
    m = _FOUR_DIGIT_YEAR_RE.search(lo)
    if m:
        return (f"FY{m.group(1)}", "fy")
    return None


# --- Number parsing --------------------------------------------------------

_AR_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_LATIN_DIGITS = "0123456789"
_AR_DIGIT_TRANS = str.maketrans(_AR_INDIC_DIGITS, _LATIN_DIGITS)
_AR_THOUSANDS = "٬"  # Arabic thousands separator

_NUMBER_RE = re.compile(r"^[\s]*\(?\s*([\d,٬.\-]+)\s*\)?[\s%]*$")


def _parse_number(cell: str) -> float | None:
    if cell is None:
        return None
    s = cell.translate(_AR_DIGIT_TRANS).replace(_AR_THOUSANDS, ",").strip()
    if not s:
        return None
    negative = "(" in s and ")" in s
    m = _NUMBER_RE.match(s)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    return -value if negative else value


_UNIT_RE = re.compile(
    r"(thousands?|millions?|billions?|usd|eur|sar|aed|egp|بآلاف|بملايين|بمليارات|دولار|درهم|ريال)",
    re.IGNORECASE,
)
_UNIT_SCALE = {
    "thousand": 1_000.0,
    "thousands": 1_000.0,
    "million": 1_000_000.0,
    "millions": 1_000_000.0,
    "billion": 1_000_000_000.0,
    "billions": 1_000_000_000.0,
    "بآلاف": 1_000.0,
    "بملايين": 1_000_000.0,
    "بمليارات": 1_000_000_000.0,
}
_CURRENCY_HINTS = {
    "usd": "USD",
    "dollar": "USD",
    "دولار": "USD",
    "eur": "EUR",
    "sar": "SAR",
    "ريال": "SAR",
    "aed": "AED",
    "درهم": "AED",
    "egp": "EGP",
}


def _detect_unit_currency(header_text: str) -> tuple[float, str | None]:
    scale = 1.0
    currency = None
    for m in _UNIT_RE.finditer(header_text.lower()):
        token = m.group(1).lower()
        scale = _UNIT_SCALE.get(token, scale)
        if token in _CURRENCY_HINTS:
            currency = _CURRENCY_HINTS[token]
    return (scale, currency)


# --- Public API ------------------------------------------------------------


def extract_facts(
    *,
    session_id: str,
    doc_id: str,
    table: ParsedTable,
    statement_hint: str | None = None,
) -> list[Fact]:
    """Walk a table grid and emit typed facts.

    Returns an empty list when the table doesn't look like a financial
    statement (e.g. no recognizable periods in the header row).
    """
    if not table.cells:
        return []
    rows = table.cells
    if len(rows) < 2:
        return []

    header_row = rows[0]
    statement = statement_hint or _classify_statement(table)

    # Each header cell maps to either a period or another descriptor.
    period_per_col: list[tuple[str, str] | None] = []
    for header in header_row:
        period_per_col.append(_detect_period(header))

    if not any(period_per_col):
        return []

    unit_scale, currency_default = _detect_unit_currency(" ".join(header_row))

    facts: list[Fact] = []
    for r_idx, row in enumerate(rows[1:], start=1):
        if not row:
            continue
        line_label = (row[0] or "").strip()
        if not line_label:
            continue
        canonical = _canonicalize_line_item(line_label) or line_label
        for c_idx in range(1, len(row)):
            if c_idx >= len(period_per_col):
                break
            period_info = period_per_col[c_idx]
            if period_info is None:
                continue
            value = _parse_number(row[c_idx])
            if value is None:
                continue
            period, period_kind = period_info
            fact_id = _fact_id(session_id, doc_id, table.table_id, r_idx, c_idx)
            label_for_lang = line_label if not looks_arabic(line_label) else normalize_arabic(line_label)
            facts.append(
                Fact(
                    id=fact_id,
                    session_id=session_id,
                    doc_id=doc_id,
                    page=table.page,
                    table_id=table.table_id,
                    statement=statement,
                    period=period,
                    period_kind=period_kind,
                    line_item_raw=label_for_lang,
                    line_item=canonical,
                    value=value * unit_scale,
                    currency=currency_default,
                    unit_scale=unit_scale,
                    bbox=table.bbox,
                )
            )
    return facts


def _classify_statement(table: ParsedTable) -> str | None:
    surface = " ".join(("/".join(table.section_path), table.markdown[:512])).lower()
    for kind, hints in _STATEMENT_HINTS.items():
        if any(h in surface for h in hints):
            return kind
    return None


def _fact_id(session_id: str, doc_id: str, table_id: str, row: int, col: int) -> str:
    h = hashlib.sha1(f"{session_id}/{doc_id}/{table_id}/{row}/{col}".encode()).hexdigest()
    return h[:16]
