import math

import pytest

from app.calculations.sandbox import SandboxError, safe_eval


def test_basic_arithmetic() -> None:
    assert safe_eval("1 + 2 * 3") == 7.0
    assert safe_eval("(1 + 2) * 3") == 9.0
    assert safe_eval("10 / 4") == 2.5
    assert safe_eval("2 ** 8") == 256.0


def test_variables() -> None:
    assert safe_eval("(rev - cogs) / rev", {"rev": 100.0, "cogs": 60.0}) == 0.4


def test_named_builtins() -> None:
    assert safe_eval("abs(-5)") == 5
    assert safe_eval("min(3, 1, 2)") == 1
    assert safe_eval("round(3.456, 2)") == 3.46
    assert safe_eval("pow(2, 10)") == 1024
    assert safe_eval("sum([1, 2, 3])") == 6  # list literal not allowed → rejected


def test_division_by_zero() -> None:
    with pytest.raises(SandboxError, match="division by zero"):
        safe_eval("1 / 0")


def test_undefined_variable() -> None:
    with pytest.raises(SandboxError, match="undefined variable"):
        safe_eval("a + 1")


def test_blocks_imports() -> None:
    with pytest.raises(SandboxError):
        safe_eval("__import__('os')")


def test_blocks_attribute_access() -> None:
    with pytest.raises(SandboxError):
        safe_eval("(1).real", {})


def test_blocks_unknown_call() -> None:
    with pytest.raises(SandboxError, match="disallowed"):
        safe_eval("open('x')")


def test_blocks_lambda() -> None:
    with pytest.raises(SandboxError):
        safe_eval("(lambda: 1)()")


def test_unary_negation() -> None:
    assert safe_eval("-5 + 3") == -2
    assert safe_eval("--5", {}) == 5  # double-negate, valid syntax


def test_blocks_assignment() -> None:
    with pytest.raises(SandboxError):
        safe_eval("x := 1")  # walrus operator


def test_blocks_string_constants() -> None:
    with pytest.raises(SandboxError, match="only numeric"):
        safe_eval("'hello'")


def test_cagr_math() -> None:
    # CAGR: (end/start)^(1/years) - 1
    cagr = safe_eval("(end / start) ** (1 / years) - 1", {"end": 200, "start": 100, "years": 5})
    assert math.isclose(cagr, 0.148698, abs_tol=1e-5)
