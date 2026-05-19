import tempfile
from pathlib import Path

from app.calculations.facts_store import FactsStore
from app.calculations.types import Fact


def _fact(**overrides) -> Fact:  # type: ignore[no-untyped-def]
    defaults = dict(
        id="f1",
        session_id="s1",
        doc_id="d1",
        page=14,
        table_id="t1",
        statement="income",
        period="FY2024",
        period_kind="fy",
        line_item_raw="Revenue",
        line_item="Revenue",
        value=1_234_567.0,
        currency="USD",
        unit_scale=1.0,
        bbox=(0.0, 0.0, 1.0, 1.0),
    )
    defaults.update(overrides)
    return Fact(**defaults)  # type: ignore[arg-type]


def test_upsert_and_lookup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "session.duckdb"
        with FactsStore(path) as store:
            n = store.upsert_many(
                [
                    _fact(id="a", line_item="Revenue", period="FY2024", value=100.0),
                    _fact(id="b", line_item="Revenue", period="FY2023", value=80.0),
                    _fact(id="c", line_item="Cost of revenue", period="FY2024", value=-50.0),
                ]
            )
            assert n == 3
            hits = store.lookup(session_id="s1", line_item="Revenue", period="FY2024")
            assert len(hits) == 1
            assert hits[0]["value"] == 100.0

            # Upsert idempotency.
            store.upsert_many([_fact(id="a", line_item="Revenue", period="FY2024", value=999.0)])
            hits = store.lookup(session_id="s1", line_item="Revenue", period="FY2024")
            assert hits[0]["value"] == 999.0
