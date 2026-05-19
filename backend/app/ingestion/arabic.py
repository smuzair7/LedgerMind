"""Arabic text normalization for the indexing copy.

The original raw text is kept in the chunk payload for display; the indexed
text is normalized so retrieval is robust against tatweel, presentation forms,
and alef/ya/hamza spelling variants.
"""

from __future__ import annotations

import re
import unicodedata

# U+0640 ARABIC TATWEEL (decorative kashida) is purely cosmetic.
_TATWEEL = "ـ"

# Diacritics / harakat block (U+064B..U+065F + tatwil/shadda variants).
_DIACRITICS_RE = re.compile(r"[ً-ٰٟۖ-ۭ]")

# Common alef variants that should fold to bare alef during indexing only.
_ALEF_VARIANTS = "أإآٱ"
_BARE_ALEF = "ا"

# Ya variants (alif maksura ↔ ya). At index time fold to ya so queries match.
_YA_VARIANTS = "ى"
_BARE_YA = "ي"

# Ta marbuta ↔ ha — leave as-is by default to avoid changing meaning, but
# folding to ha is a common indexing trick. Off by default.


def normalize_arabic(text: str, *, fold_alef: bool = True, fold_ya: bool = True) -> str:
    """Return a Unicode-normalized, tatweel-free copy suitable for indexing."""
    if not text:
        return text
    # NFKC collapses presentation-form ligatures (FB50-FDFF, FE70-FEFF).
    out = unicodedata.normalize("NFKC", text)
    out = out.replace(_TATWEEL, "")
    out = _DIACRITICS_RE.sub("", out)
    if fold_alef:
        out = out.translate({ord(c): _BARE_ALEF for c in _ALEF_VARIANTS})
    if fold_ya:
        out = out.translate({ord(c): _BARE_YA for c in _YA_VARIANTS})
    return out


# Quick language sniff (single-pass over the string). Robust enough for routing
# decisions; we don't need full langdetect for chunk-level dispatch.
#
# Codepoint ranges (inclusive):
#   U+0600..U+06FF  Arabic
#   U+0750..U+077F  Arabic Supplement
#   U+0870..U+089F  Arabic Extended-B
#   U+08A0..U+08FF  Arabic Extended-A
#   U+FB50..U+FDFF  Arabic Presentation Forms-A
#   U+FE70..U+FEFC  Arabic Presentation Forms-B (excluding the noncharacters at end)
_ARABIC_RANGES: tuple[tuple[int, int], ...] = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x0870, 0x089F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFC),
)


def _is_arabic_char(c: str) -> bool:
    cp = ord(c)
    return any(lo <= cp <= hi for lo, hi in _ARABIC_RANGES)


def looks_arabic(text: str, *, threshold: float = 0.15) -> bool:
    if not text:
        return False
    arabic_chars = sum(1 for c in text if _is_arabic_char(c))
    return arabic_chars / max(len(text), 1) >= threshold
