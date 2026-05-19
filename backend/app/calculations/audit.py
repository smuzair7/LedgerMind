"""Audit trail for tool invocations.

Every tool result is paired with an audit record that captures inputs, formula,
and the resolved value. The orchestrator includes the audit in the SSE
`tool_result` event so the UI can render a CalculationCard with traceable
provenance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ToolAudit:
    tool: str
    args: dict[str, Any]
    ok: bool
    result: Any
    error: str | None = None
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
