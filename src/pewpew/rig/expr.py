"""Restricted arithmetic over an entity's `dims`.

An expression uses numbers, dims names, `+ - * /`, unary minus and
parentheses (docs/studio/domain-model.md:23). The parser refuses every other
node before evaluation, so a catalog file can never run code. Only Python
evaluates expressions; the browser never does.
"""

from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable, Mapping
from functools import lru_cache
from typing import cast

_BINARY: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY: dict[type, Callable[[float], float]] = {ast.USub: operator.neg, ast.UAdd: operator.pos}

#: The longest expression source, in characters.
MAX_SOURCE = 256
#: The deepest expression tree, and the longest chain of dims that name dims.
MAX_DEPTH = 64


class ExprError(ValueError):
    """An expression that is not allowed, names an unknown dim, or has a cycle."""


@lru_cache(maxsize=4096)
def parse(src: str) -> ast.expr:
    """The checked syntax tree of `src`; raises ExprError for anything not allowed."""
    if len(src) > MAX_SOURCE:
        raise ExprError(f"an expression has at most {MAX_SOURCE} characters, this one {len(src)}")
    try:
        body = ast.parse(src.strip(), mode="eval").body
    except SyntaxError as exc:
        raise ExprError(f"{src!r} is not an expression: {exc.msg}") from None
    except (RecursionError, MemoryError):
        raise ExprError(f"{src!r} nests too deeply") from None
    stack: list[tuple[ast.AST, int]] = [(body, 1)]
    while stack:
        node, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise ExprError(f"{src!r} nests more than {MAX_DEPTH} deep")
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            continue
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            continue
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if not _finite(cast(float, node.value)):
                raise ExprError(f"{src!r} has a number too large for a float")
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            continue
        if isinstance(node, (ast.operator, ast.unaryop, ast.expr_context)):
            continue  # the op nodes of the BinOp and UnaryOp checked above
        raise ExprError(
            f"{src!r}: {type(node).__name__} is not allowed; use numbers, dims names, + - * / and parentheses"
        )
    return body


def _finite(n: float) -> bool:
    try:
        return math.isfinite(float(n))
    except OverflowError:
        return False


def names(src: str) -> frozenset[str]:
    """The dims names `src` refers to."""
    return frozenset(n.id for n in ast.walk(parse(src)) if isinstance(n, ast.Name))


def evaluate(src: str, env: Mapping[str, float]) -> float:
    """The value of `src` with names looked up in `env`."""
    try:
        result = _eval(parse(src), env)
    except ZeroDivisionError:
        raise ExprError(f"{src!r} divides by zero") from None
    except OverflowError:
        raise ExprError(f"{src!r} is too large for a float") from None
    except KeyError as exc:
        known = ", ".join(sorted(env)) or "(none)"
        raise ExprError(f"{src!r} names {exc.args[0]!r}, which is not a dim; dims: {known}") from None
    if not math.isfinite(result):
        raise ExprError(f"{src!r} is not finite ({result})")
    return result


def _eval(node: ast.expr, env: Mapping[str, float]) -> float:
    if isinstance(node, ast.Constant):
        return float(cast(float, node.value))
    if isinstance(node, ast.Name):
        return float(env[node.id])
    if isinstance(node, ast.UnaryOp):
        return _UNARY[type(node.op)](_eval(node.operand, env))
    assert isinstance(node, ast.BinOp)
    return _BINARY[type(node.op)](_eval(node.left, env), _eval(node.right, env))


def resolve(dims: Mapping[str, float | str]) -> dict[str, float]:
    """Every dim as a number, each expression evaluated after the dims it names.

    Raises ExprError on an unknown name, a cycle (and names it), or a chain of
    dims more than MAX_DEPTH long.
    """
    out: dict[str, float] = {}
    path: list[str] = []

    def visit(name: str) -> float:
        if name in out:
            return out[name]
        if name in path:
            cycle = path[path.index(name) :] + [name]
            raise ExprError(f"dims cycle: {' -> '.join(cycle)}")
        if len(path) >= MAX_DEPTH:
            raise ExprError(f"dim {path[0]!r} depends on a chain of more than {MAX_DEPTH} dims")
        raw = dims[name]
        if not isinstance(raw, str):
            out[name] = float(raw)
            return out[name]
        path.append(name)
        for dep in sorted(names(raw)):
            if dep not in dims:
                raise ExprError(f"dim {name!r} = {raw!r} names {dep!r}, which is not a dim")
            visit(dep)
        path.pop()
        out[name] = evaluate(raw, out)
        return out[name]

    for name in dims:
        visit(name)
    return out
