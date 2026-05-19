from app.ingestion.arabic import looks_arabic, normalize_arabic


def test_strips_tatweel() -> None:
    raw = "إيـــــــــرادات"
    assert normalize_arabic(raw) == "ايرادات"


def test_strips_diacritics() -> None:
    assert normalize_arabic("اَلَّـذِيـن") == "الذين"


def test_folds_alef_variants() -> None:
    assert normalize_arabic("أبو الإمارات") == "ابو الامارات"


def test_folds_alef_maksura() -> None:
    assert normalize_arabic("على") == "علي"


def test_nfkc_collapses_presentation_forms() -> None:
    # FEED-FEEE are Arabic presentation form ligatures; NFKC should fold them.
    raw = "ﻣ"  # Final-form Meem
    assert normalize_arabic(raw) != "ﻣ"


def test_looks_arabic() -> None:
    assert looks_arabic("هذا نص عربي")
    assert not looks_arabic("This is English text.")
    assert not looks_arabic("")


def test_idempotent() -> None:
    text = "إيرادات"
    once = normalize_arabic(text)
    twice = normalize_arabic(once)
    assert once == twice
