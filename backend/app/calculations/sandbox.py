"""AST-whitelisted Python evaluator.

The LLM never executes arbitrary code; the only stored "user code" is the
formula string it produces inside a tool call, and even that is bounded by
the tool schema. This evaluator allows:

  - arithmetic: + - * / // % **
  - unary + and -
  - calls only to a fixed whitelist: abs, min, max, round, sum, pow
  - reading variables from a passed-in dict
  - numeric literals

Everything else (imports, attribute access, subscripts on arbitrary objects,
comprehensions, function definitions, assignments, augmented assignments,
lambdas, etc.) raises SandboxError. The implementation is ~70 lines and
auditable.
"""

from __future__ import annotations

import ast
from typing import Any


class SandboxError(Exception):
    pass


_ALLOWED_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sum": sum,
    "pow": pow,
}


class _Eval(ast.NodeVisitor):
    def __init__(self, env: dict[str, float]) -> None:
        self.env = env

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return node.value
        raise SandboxError(f"only numeric constants allowed: {node.value!r}")

    def visit_Name(self, node: ast.Name) -> Any:
        if isinstance(node.ctx, ast.Load):
            if node.id in self.env:
                v = self.env[node.id]
                if isinstance(v, (int, float)):
                    return v
                raise SandboxError(f"non-numeric variable: {node.id}")
            raise SandboxError(f"undefined variable: {node.id}")
        raise SandboxError("write/del not allowed")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise SandboxError(f"unsupported unary op: {ast.dump(node.op)}")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        a = self.visit(node.left)
        b = self.visit(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return a + b
        if isinstance(op, ast.Sub):
            return a - b
        if isinstance(op, ast.Mult):
            return a * b
        if isinstance(op, ast.Div):
            if b == 0:
                raise SandboxError("division by zero")
            return a / b
        if isinstance(op, ast.FloorDiv):
            if b == 0:
                raise SandboxError("division by zero")
            return a // b
        if isinstance(op, ast.Mod):
            if b == 0:
                raise SandboxError("modulo by zero")
            return a % b
        if isinstance(op, ast.Pow):
            return a ** b
        raise SandboxError(f"unsupported binary op: {ast.dump(op)}")

    def visit_List(self, node: ast.List) -> Any:
        # Numeric list — used by sum([...]).
        return [self.visit(elt) for elt in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        return tuple(self.visit(elt) for elt in node.elts)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise SandboxError("only direct function calls allowed")
        fn = _ALLOWED_BUILTINS.get(node.func.id)
        if fn is None:
            raise SandboxError(f"call to disallowed function: {node.func.id}")
        if node.keywords:
            raise SandboxError("keyword args not allowed")
        args = [self.visit(a) for a in node.args]
        try:
            return fn(*args)
        except (TypeError, ValueError) as e:
            raise SandboxError(f"call failed: {e}") from e

    # Block everything else.
    def generic_visit(self, node: ast.AST) -> Any:
        raise SandboxError(f"unsupported syntax: {type(node).__name__}")


def safe_eval(expression: str, variables: dict[str, float] | None = None) -> float:
    """Evaluate `expression` against `variables` under the sandbox rules."""
    env = variables or {}
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise SandboxError(f"parse error: {e.msg}") from e
    result = _Eval(env).visit(tree)
    if not isinstance(result, (int, float)):
        raise SandboxError(f"expression produced non-numeric: {result!r}")
    return float(result)
