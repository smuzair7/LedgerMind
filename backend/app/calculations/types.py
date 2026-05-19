"""Pure data types for the calculations subsystem.

Kept dependency-free so the ingestion logic (which produces these) can be
unit-tested without DuckDB.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Fact:
    id: str
    session_id: str
    doc_id: str
    page: int | None
    table_id: str | None
    statement: str | None             # income | balance | cashflow | equity | other
    period: str | None                # "FY2024", "Q1 2024", "31-Dec-2024", …
    period_kind: str | None           # fy | quarter | half | date
    line_item_raw: str
    line_item: str                    # canonical name (e.g. "Revenue")
    value: float
    currency: str | None
    unit_scale: float = 1.0
    bbox: tuple[float, float, float, float] | None = None
