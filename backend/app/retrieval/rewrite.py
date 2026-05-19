"""Lightweight query expansion.

For the GitHub-portfolio scope this is intentionally cheap: it does NOT call
the LLM (which would cost a round-trip + the user's tokens). Instead it
extracts entity hints and emits 1-2 paraphrases via simple rules. A future
upgrade can swap in an LLM-driven expansion behind the same interface.
"""

from __future__ import annotations

import re

from app.ingestion.arabic import looks_arabic, normalize_arabic


_PERIOD_HINT_RE = re.compile(r"\b(?:fy|q[1-4]|h[12])\s*\d{2,4}\b|\b20\d{2}\b", re.IGNORECASE)


def expand_query(query: str) -> list[str]:
    """Return 1-3 query variants, ALL of which will be searched and RRF-fused.

    Variant 1: original.
    Variant 2: normalized (NFKC + tatweel) when text contains Arabic.
    Variant 3: period-extracted phrase if periods are mentioned (helps the
              sparse index hit table chunks containing those periods).
    """
    q = query.strip()
    if not q:
        return []
    variants: list[str] = [q]
    if looks_arabic(q):
        variants.append(normalize_arabic(q))
    periods = _PERIOD_HINT_RE.findall(q)
    if periods:
        variants.append(" ".join(periods + [q]))
    # Dedupe while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out
