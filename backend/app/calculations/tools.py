"""LLM-callable tools for the calculations subsystem.

Every tool returns a uniform shape:

  {
    "value": <number>,
    "formula": "Revenue - COGS",                # human-readable
    "inputs": [
        {"fact_id": "...", "line_item": "Revenue", "period": "FY2024",
         "value": 1234567.0, "doc_id": "...", "page": 14},
        ...
    ],
    "unit": "ratio" | "currency" | "percent" | "scalar"
  }

The orchestrator wraps this with an audit trail and emits a `tool_result`
SSE event the frontend renders as a CalculationCard.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.calculations.facts_store import FactsStore, store_path
from app.calculations.sandbox import SandboxError, safe_eval
from app.providers.base import ToolSpec
from app.settings import get_settings


@dataclass(slots=True)
class ToolError(Exception):
    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code}: {self.message}"


# ---------------------------------------------------------------------------
# Tool specs (JSON Schema) — these get translated by each provider's adapter.
# ---------------------------------------------------------------------------

LOOKUP = ToolSpec(
    name="lookup_line_item",
    description=(
        "Look up a single financial line item for a specific period from the "
        "ingested documents. Use this any time you need a number — never "
        "compute or estimate values yourself."
    ),
    parameters={
        "type": "object",
        "properties": {
            "line_item": {
                "type": "string",
                "description": "Canonical or raw line item label, e.g. 'Revenue', 'Net income'.",
            },
            "period": {
                "type": "string",
                "description": "Period label, e.g. 'FY2024', 'Q1 2024', 'H1 2023'.",
            },
            "statement": {
                "type": "string",
                "enum": ["income", "balance", "cashflow", "equity"],
                "description": "Optional disambiguation when the same label appears in two statements.",
            },
        },
        "required": ["line_item", "period"],
    },
)

COMPUTE_YOY = ToolSpec(
    name="compute_yoy",
    description="Year-over-year change: (current - prior) / prior, returned as a ratio.",
    parameters={
        "type": "object",
        "properties": {
            "line_item": {"type": "string"},
            "period_current": {"type": "string"},
            "period_prior": {"type": "string"},
        },
        "required": ["line_item", "period_current", "period_prior"],
    },
)

COMPUTE_RATIO = ToolSpec(
    name="compute_ratio",
    description=(
        "Compute one of a fixed catalog of named financial ratios for a period: "
        "gross_margin, operating_margin, net_margin, current_ratio, quick_ratio, "
        "debt_to_equity, debt_to_assets, roa, roe, interest_coverage, "
        "asset_turnover, inventory_turnover."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "enum": [
                    "gross_margin",
                    "operating_margin",
                    "net_margin",
                    "current_ratio",
                    "quick_ratio",
                    "debt_to_equity",
                    "debt_to_assets",
                    "roa",
                    "roe",
                    "interest_coverage",
                    "asset_turnover",
                    "inventory_turnover",
                ],
            },
            "period": {"type": "string"},
        },
        "required": ["name", "period"],
    },
)

CAGR = ToolSpec(
    name="cagr",
    description="Compound annual growth rate between two FY periods: (end/start)^(1/years) - 1.",
    parameters={
        "type": "object",
        "properties": {
            "line_item": {"type": "string"},
            "period_start": {"type": "string"},
            "period_end": {"type": "string"},
        },
        "required": ["line_item", "period_start", "period_end"],
    },
)

PYTHON_EVAL = ToolSpec(
    name="python_eval",
    description=(
        "Evaluate a sandboxed arithmetic expression. Variables must be a dict "
        "of named numeric values. Allowed builtins: abs, min, max, round, sum, "
        "pow. No imports, no attribute access, no I/O."
    ),
    parameters={
        "type": "object",
        "properties": {
            "expression": {"type": "string"},
            "variables": {
                "type": "object",
                "additionalProperties": {"type": "number"},
            },
        },
        "required": ["expression"],
    },
)


def all_tools() -> list[ToolSpec]:
    return [LOOKUP, COMPUTE_YOY, COMPUTE_RATIO, CAGR, PYTHON_EVAL]


# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------


# Each named ratio is a (numerator_line_item, denominator_line_item, label) tuple.
# Some ratios have additive numerators or denominators; we keep a small DSL.
RATIOS: dict[str, dict[str, Any]] = {
    "gross_margin": {
        "label": "Gross margin",
        "num": ["Revenue", "-", "Cost of revenue"],
        "den": ["Revenue"],
        "unit": "percent",
    },
    "operating_margin": {
        "label": "Operating margin",
        "num": ["Operating income"],
        "den": ["Revenue"],
        "unit": "percent",
    },
    "net_margin": {
        "label": "Net margin",
        "num": ["Net income"],
        "den": ["Revenue"],
        "unit": "percent",
    },
    "current_ratio": {
        "label": "Current ratio",
        "num": ["Current assets"],
        "den": ["Current liabilities"],
        "unit": "ratio",
    },
    "quick_ratio": {
        "label": "Quick ratio",
        "num": ["Current assets", "-", "Inventory"],
        "den": ["Current liabilities"],
        "unit": "ratio",
    },
    "debt_to_equity": {
        "label": "Debt to equity",
        "num": ["Total liabilities"],
        "den": ["Total equity"],
        "unit": "ratio",
    },
    "debt_to_assets": {
        "label": "Debt to assets",
        "num": ["Total liabilities"],
        "den": ["Total assets"],
        "unit": "ratio",
    },
    "roa": {
        "label": "Return on assets",
        "num": ["Net income"],
        "den": ["Total assets"],
        "unit": "percent",
    },
    "roe": {
        "label": "Return on equity",
        "num": ["Net income"],
        "den": ["Total equity"],
        "unit": "percent",
    },
    "interest_coverage": {
        "label": "Interest coverage",
        "num": ["Operating income"],
        "den": ["Interest expense"],
        "unit": "ratio",
    },
    "asset_turnover": {
        "label": "Asset turnover",
        "num": ["Revenue"],
        "den": ["Total assets"],
        "unit": "ratio",
    },
    "inventory_turnover": {
        "label": "Inventory turnover",
        "num": ["Cost of revenue"],
        "den": ["Inventory"],
        "unit": "ratio",
    },
}


def _facts_path(session_id: str) -> Path:
    return store_path(get_settings().data_dir, session_id)


def _lookup_value(
    store: FactsStore,
    *,
    session_id: str,
    line_item: str,
    period: str,
    statement: str | None = None,
) -> dict[str, Any]:
    rows = store.lookup(session_id=session_id, line_item=line_item, period=period, statement=statement)
    if not rows:
        raise ToolError("not_found", f"{line_item} for {period} not found in indexed documents")
    # Prefer the row whose value isn't zero; ties broken by lowest page.
    rows.sort(key=lambda r: (r["value"] == 0, r["page"] or 0))
    return rows[0]


def _input_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "fact_id": row["id"],
        "line_item": row["line_item"],
        "period": row["period"],
        "value": row["value"],
        "doc_id": row["doc_id"],
        "page": row["page"],
    }


def _eval_dsl(
    store: FactsStore,
    session_id: str,
    period: str,
    expr: list[str],
) -> tuple[float, list[dict[str, Any]], str]:
    """Tiny DSL: alternating line-item names and '+'/'-' operators.

    Example: ["Revenue", "-", "Cost of revenue"] → Revenue - Cost of revenue.
    """
    inputs: list[dict[str, Any]] = []
    parts: list[str] = []
    total = 0.0
    op = "+"
    for token in expr:
        if token in {"+", "-"}:
            op = token
            parts.append(op)
            continue
        row = _lookup_value(store, session_id=session_id, line_item=token, period=period)
        value = float(row["value"])
        total += value if op == "+" else -value
        inputs.append(_input_from_row(row))
        parts.append(token)
        op = "+"
    formula = " ".join(parts)
    return total, inputs, formula


# ---------------------------------------------------------------------------
# Dispatcher — called by the generation orchestrator.
# ---------------------------------------------------------------------------


def run_tool(
    *,
    session_id: str,
    name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    store_p = _facts_path(session_id)
    with FactsStore(store_p) as store:
        if name == "lookup_line_item":
            row = _lookup_value(
                store,
                session_id=session_id,
                line_item=args["line_item"],
                period=args["period"],
                statement=args.get("statement"),
            )
            return {
                "value": row["value"],
                "formula": f"{row['line_item']} · {row['period']}",
                "inputs": [_input_from_row(row)],
                "unit": "currency",
            }

        if name == "compute_yoy":
            curr = _lookup_value(
                store,
                session_id=session_id,
                line_item=args["line_item"],
                period=args["period_current"],
            )
            prior = _lookup_value(
                store,
                session_id=session_id,
                line_item=args["line_item"],
                period=args["period_prior"],
            )
            if prior["value"] == 0:
                raise ToolError("division_by_zero", "prior-period value is zero")
            yoy = (curr["value"] - prior["value"]) / prior["value"]
            return {
                "value": yoy,
                "formula": (
                    f"({curr['line_item']}_{curr['period']} − "
                    f"{prior['line_item']}_{prior['period']}) / "
                    f"{prior['line_item']}_{prior['period']}"
                ),
                "inputs": [_input_from_row(curr), _input_from_row(prior)],
                "unit": "percent",
            }

        if name == "compute_ratio":
            ratio = RATIOS.get(args["name"])
            if ratio is None:
                raise ToolError("unknown_ratio", args["name"])
            period = args["period"]
            num_value, num_inputs, num_formula = _eval_dsl(store, session_id, period, ratio["num"])
            den_value, den_inputs, den_formula = _eval_dsl(store, session_id, period, ratio["den"])
            if den_value == 0:
                raise ToolError("division_by_zero", "denominator is zero")
            value = num_value / den_value
            formula = f"({num_formula}) / ({den_formula})"
            return {
                "value": value,
                "formula": formula,
                "label": ratio["label"],
                "inputs": num_inputs + den_inputs,
                "unit": ratio["unit"],
                "period": period,
            }

        if name == "cagr":
            start = _lookup_value(
                store,
                session_id=session_id,
                line_item=args["line_item"],
                period=args["period_start"],
            )
            end = _lookup_value(
                store,
                session_id=session_id,
                line_item=args["line_item"],
                period=args["period_end"],
            )
            years = _years_between(args["period_start"], args["period_end"])
            if years <= 0:
                raise ToolError("bad_period", "period_end must be after period_start")
            if start["value"] <= 0:
                raise ToolError("non_positive_base", "starting value must be positive for CAGR")
            value = (end["value"] / start["value"]) ** (1 / years) - 1
            return {
                "value": value,
                "formula": f"({end['line_item']}_{end['period']} / {start['line_item']}_{start['period']})^(1/{years}) - 1",
                "inputs": [_input_from_row(start), _input_from_row(end)],
                "unit": "percent",
                "years": years,
            }

        if name == "python_eval":
            try:
                value = safe_eval(args["expression"], args.get("variables") or {})
            except SandboxError as e:
                raise ToolError("sandbox", str(e)) from e
            return {
                "value": value,
                "formula": args["expression"],
                "inputs": [
                    {"line_item": k, "value": v} for k, v in (args.get("variables") or {}).items()
                ],
                "unit": "scalar",
            }

    raise ToolError("unknown_tool", name)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

import re as _re


def _years_between(start: str, end: str) -> int:
    s = _re.search(r"(20\d{2})", start)
    e = _re.search(r"(20\d{2})", end)
    if not s or not e:
        return 0
    return int(e.group(1)) - int(s.group(1))
