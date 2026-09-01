#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fail-closed gate: no ``async def`` fixture may use a bare ``@pytest.fixture``.

OMN-17319. An ``async def`` fixture declared with a plain ``@pytest.fixture``
is NOT executed under pytest-asyncio's STRICT mode -- pytest hands the
requesting test an un-awaited ``async_generator`` object and the fixture body
never runs. ``tests/pytest.ini`` (the effective config for ``tests/``) does not
set ``asyncio_mode``, so STRICT is in force there regardless of the
``asyncio_mode = "auto"`` in ``pyproject.toml``, and its ``--disable-warnings``
plus ``filterwarnings = ignore::DeprecationWarning`` swallow the deprecation
warning that would otherwise surface the mistake.

pytest 9.1 promoted that silent no-op to a hard setup error
(https://docs.pytest.org/en/stable/deprecations.html#sync-test-depending-on-async-fixture),
which is how OMN-17319 was found: 24 tests errored on 9.1.1 that passed on
9.0.3. The failure mode this gate prevents is the SILENT one -- cleanup or
setup code that looks wired and is not.

Correct forms: ``@pytest_asyncio.fixture`` for a fixture only async tests
consume, or a synchronous ``@pytest.fixture`` when sync tests consume it too.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = ("src", "tests")


def _is_bare_pytest_fixture(decorator: ast.expr) -> bool:
    """True when the decorator is ``pytest.fixture`` / ``fixture`` (not pytest_asyncio)."""
    node = decorator.func if isinstance(decorator, ast.Call) else decorator

    if isinstance(node, ast.Attribute):
        # pytest.fixture(...) -> reject; pytest_asyncio.fixture(...) -> allow.
        return node.attr == "fixture" and (
            not isinstance(node.value, ast.Name) or node.value.id == "pytest"
        )
    if isinstance(node, ast.Name):
        # A bare ``fixture`` from ``from pytest import fixture``.
        return node.id == "fixture"
    return False


def find_violations() -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    for scan_root in SCAN_ROOTS:
        root = REPO_ROOT / scan_root
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.AsyncFunctionDef):
                    continue
                for decorator in node.decorator_list:
                    if _is_bare_pytest_fixture(decorator):
                        violations.append(
                            (path.relative_to(REPO_ROOT), node.lineno, node.name)
                        )
                        break
    return violations


def main() -> int:
    violations = find_violations()
    if not violations:
        sys.stdout.write("async-fixture-decorator gate: OK (0 violations)\n")
        return 0

    sys.stderr.write(
        "async-fixture-decorator gate FAILED (OMN-17319): "
        f"{len(violations)} async fixture(s) declared with a bare @pytest.fixture.\n"
        "Under pytest-asyncio STRICT mode these fixtures SILENTLY DO NOT RUN, "
        "and pytest >= 9.1 errors on them.\n"
        "Fix: use @pytest_asyncio.fixture, or make the fixture synchronous if "
        "synchronous tests also consume it.\n"
    )
    for path, lineno, name in violations:
        sys.stderr.write(f"  {path}:{lineno}: async fixture '{name}'\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
