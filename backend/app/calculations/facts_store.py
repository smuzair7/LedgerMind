"""Per-session DuckDB store of typed financial facts.

The schema is intentionally small. Tools query it with named-parameter SQL.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from app.calculations.types import Fact

__all__ = ["FactsStore", "Fact", "store_path", "SCHEMA"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id              VARCHAR PRIMARY KEY,
    session_id      VARCHAR NOT NULL,
    doc_id          VARCHAR NOT NULL,
    page            INTEGER,
    table_id        VARCHAR,
    statement       VARCHAR,
    period          VARCHAR,
    period_kind     VARCHAR,
    line_item_raw   VARCHAR,
    line_item       VARCHAR,
    value           DOUBLE,
    currency        VARCHAR,
    unit_scale      DOUBLE DEFAULT 1.0,
    bbox_l          DOUBLE,
    bbox_t          DOUBLE,
    bbox_r          DOUBLE,
    bbox_b          DOUBLE
);
CREATE INDEX IF NOT EXISTS facts_lookup_idx ON facts(session_id, line_item, period);
CREATE INDEX IF NOT EXISTS facts_doc_idx    ON facts(session_id, doc_id);
"""


class FactsStore:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        self._con = duckdb.connect(self.path)
        self._con.execute(SCHEMA)

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> FactsStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def upsert_many(self, facts: list[Fact]) -> int:
        if not facts:
            return 0
        rows = [
            (
                f.id,
                f.session_id,
                f.doc_id,
                f.page,
                f.table_id,
                f.statement,
                f.period,
                f.period_kind,
                f.line_item_raw,
                f.line_item,
                f.value,
                f.currency,
                f.unit_scale,
                f.bbox[0] if f.bbox else None,
                f.bbox[1] if f.bbox else None,
                f.bbox[2] if f.bbox else None,
                f.bbox[3] if f.bbox else None,
            )
            for f in facts
        ]
        self._con.executemany(
            """
            INSERT OR REPLACE INTO facts VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            rows,
        )
        return len(rows)

    def lookup(
        self,
        *,
        session_id: str,
        line_item: str,
        period: str | None = None,
        statement: str | None = None,
    ) -> list[dict[str, Any]]:
        q = "SELECT * FROM facts WHERE session_id = ? AND lower(line_item) = lower(?)"
        params: list[Any] = [session_id, line_item]
        if period is not None:
            q += " AND lower(period) = lower(?)"
            params.append(period)
        if statement is not None:
            q += " AND lower(statement) = lower(?)"
            params.append(statement)
        q += " ORDER BY page LIMIT 50"
        rows = self._con.execute(q, params).fetchdf().to_dict("records")
        return rows

    def list_for_session(self, session_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        return (
            self._con.execute(
                "SELECT * FROM facts WHERE session_id = ? ORDER BY page LIMIT ?",
                [session_id, limit],
            )
            .fetchdf()
            .to_dict("records")
        )


def store_path(data_dir: Path | str, session_id: str) -> Path:
    p = Path(data_dir) / "sessions" / f"{session_id}.duckdb"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
