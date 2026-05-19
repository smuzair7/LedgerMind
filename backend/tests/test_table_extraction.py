from app.ingestion.parser_docling import ParsedTable
from app.ingestion.tables import extract_facts


def _table(cells: list[list[str]], section: tuple[str, ...] = ()) -> ParsedTable:
    return ParsedTable(
        table_id="t1",
        page=14,
        bbox=(0.0, 0.0, 1.0, 1.0),
        markdown="",
        cells=cells,
        section_path=section,
    )


def test_basic_income_statement_en() -> None:
    table = _table(
        [
            ["", "FY2024", "FY2023"],
            ["Revenue", "1,234,567", "1,100,000"],
            ["Cost of sales", "(678,900)", "(610,000)"],
            ["Net income", "300,000", "275,000"],
        ],
        section=("Consolidated Income Statement",),
    )
    facts = extract_facts(session_id="s1", doc_id="d1", table=table)
    # 3 rows × 2 periods = 6 facts.
    assert len(facts) == 6
    rev24 = next(f for f in facts if f.line_item == "Revenue" and f.period == "FY2024")
    assert rev24.value == 1_234_567
    cogs24 = next(f for f in facts if f.line_item == "Cost of revenue" and f.period == "FY2024")
    assert cogs24.value == -678_900  # parens → negative
    assert rev24.statement == "income"


def test_quarterly_periods() -> None:
    table = _table(
        [
            ["", "Q1 2024", "Q1 2023"],
            ["Revenue", "300,000", "250,000"],
        ]
    )
    facts = extract_facts(session_id="s", doc_id="d", table=table)
    assert {f.period for f in facts} == {"Q1 2024", "Q1 2023"}
    assert all(f.period_kind == "quarter" for f in facts)


def test_arabic_revenue_row() -> None:
    table = _table(
        [
            ["", "FY2024", "FY2023"],
            ["الإيرادات", "1٬234٬567", "1٬100٬000"],
        ]
    )
    facts = extract_facts(session_id="s", doc_id="d", table=table)
    # AR-indic thousands separator handled.
    assert len(facts) == 2
    assert all(f.line_item == "Revenue" for f in facts)
    assert facts[0].value == 1_234_567


def test_no_periods_no_facts() -> None:
    table = _table([["foo", "bar"], ["1", "2"]])
    facts = extract_facts(session_id="s", doc_id="d", table=table)
    assert facts == []


def test_unit_scale_thousands() -> None:
    table = _table(
        [
            ["(in thousands of USD)", "FY2024"],
            ["Revenue", "1,234"],
        ]
    )
    facts = extract_facts(session_id="s", doc_id="d", table=table)
    assert len(facts) == 1
    assert facts[0].value == 1_234_000
    assert facts[0].currency == "USD"
    assert facts[0].unit_scale == 1_000


def test_arabic_indic_digits() -> None:
    table = _table(
        [
            ["", "FY٢٠٢٤"],
            ["Revenue", "١٬٢٣٤٬٥٦٧"],
        ]
    )
    facts = extract_facts(session_id="s", doc_id="d", table=table)
    assert len(facts) == 1
    assert facts[0].period == "FY2024"
    assert facts[0].value == 1_234_567
