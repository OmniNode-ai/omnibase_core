# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Guard against a function-scoped autouse fixture calling gc.collect per test.

OMN-19686 (child of OMN-19680, plan task A2). Lab measurement (A1 receipt,
`$OMNI_HOME/.claude_scratch/reports/ci-speed-83/a1/RECEIPT.md`) attributes 99.8%/99.9%
of the per-test median in shard groups 7 and 23 to `aggressive_gc_cleanup`
(`tests/conftest.py`), a function-scoped autouse fixture whose only real work is a
per-test `gc.collect()`. A full generational collection over a heap holding ~1.6M
tracked objects costs about one second, every single test. This test statically
proves no *function-scoped autouse fixture* in any `tests/**/conftest.py` calls
`gc.collect` (directly or via `gc.collect(...)`), while leaving hook functions
(``pytest_runtest_teardown``, ``pytest_sessionfinish``, ...), which are not fixtures,
and session-scoped fixtures out of scope: module-boundary and session-boundary
collection are the intended, much cheaper, floor.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _iter_conftest_files() -> list[Path]:
    return sorted((REPO_ROOT / "tests").rglob("conftest.py"))


def _fixture_scope_and_autouse(decorator: ast.expr) -> tuple[str, bool] | None:
    """Return (scope, autouse) for a `@pytest.fixture(...)` decorator, else None."""
    call: ast.Call
    if isinstance(decorator, ast.Call):
        call = decorator
    else:
        return None

    func = call.func
    is_fixture_call = (isinstance(func, ast.Attribute) and func.attr == "fixture") or (
        isinstance(func, ast.Name) and func.id == "fixture"
    )
    if not is_fixture_call:
        return None

    scope = "function"
    autouse = False
    for kw in call.keywords:
        if kw.arg == "scope" and isinstance(kw.value, ast.Constant):
            scope = str(kw.value.value)
        if kw.arg == "autouse" and isinstance(kw.value, ast.Constant):
            autouse = bool(kw.value.value)
    return scope, autouse


def _is_bare_fixture_decorator(decorator: ast.expr) -> bool:
    """`@pytest.fixture` with no call at all: scope defaults to function, autouse False."""
    return (isinstance(decorator, ast.Attribute) and decorator.attr == "fixture") or (
        isinstance(decorator, ast.Name) and decorator.id == "fixture"
    )


def _calls_gc_collect(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Attribute) and func.attr == "collect":
                value = func.value
                if isinstance(value, ast.Name) and value.id == "gc":
                    return True
            if isinstance(func, ast.Name) and func.id == "collect":
                # covers `from gc import collect as collect; collect()`-style aliasing
                return True
    return False


def _offending_function_scoped_autouse_gc_fixtures(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        autouse = False
        scope = "function"
        is_fixture = False
        for decorator in node.decorator_list:
            if _is_bare_fixture_decorator(decorator):
                is_fixture = True
                continue
            parsed = _fixture_scope_and_autouse(decorator)
            if parsed is not None:
                is_fixture = True
                scope, autouse = parsed

        if not is_fixture or not autouse or scope != "function":
            continue

        if _calls_gc_collect(node):
            offenders.append(node.name)

    return offenders


@pytest.mark.unit
def test_no_function_scoped_autouse_fixture_calls_gc_collect() -> None:
    conftest_files = _iter_conftest_files()
    assert conftest_files, "expected at least one tests/**/conftest.py to scan"

    all_offenders: dict[str, list[str]] = {}
    for path in conftest_files:
        offenders = _offending_function_scoped_autouse_gc_fixtures(path)
        if offenders:
            all_offenders[str(path.relative_to(REPO_ROOT))] = offenders

    assert not all_offenders, (
        "function-scoped autouse fixture(s) call gc.collect() per test, costing "
        "about one second per test at this repo's heap size (OMN-19686): "
        f"{all_offenders}. Module- or session-boundary collection belongs in a "
        "pytest_runtest_teardown/pytest_sessionfinish hook or a session-scoped "
        "fixture, never a function-scoped autouse fixture."
    )
