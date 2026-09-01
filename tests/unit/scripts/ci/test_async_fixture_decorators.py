# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the async-fixture-decorator gate (OMN-17319).

The gate exists because an ``async def`` fixture with a bare ``@pytest.fixture``
fails SILENTLY under pytest-asyncio STRICT mode -- the body never executes.
``test_bare_pytest_fixture_on_async_def_is_rejected`` is the RED case (the exact
shape of the ``cleanup_async_tasks`` fixture this ticket removed);
``test_repo_is_clean`` is the live repo-wide assertion.
"""

from __future__ import annotations

import ast

import pytest

from scripts.ci.check_async_fixture_decorators import (
    _is_bare_pytest_fixture,
    find_violations,
)


def _decorator_of(source: str) -> ast.expr:
    """Return the sole decorator of the sole function in ``source``."""
    tree = ast.parse(source)
    func = tree.body[0]
    assert isinstance(func, ast.AsyncFunctionDef | ast.FunctionDef)
    return func.decorator_list[0]


@pytest.mark.unit
@pytest.mark.parametrize(
    "decorator_source",
    [
        "@pytest.fixture",
        "@pytest.fixture(autouse=True)",
        "@pytest.fixture(scope='session', autouse=True)",
        "@fixture",
        "@fixture(autouse=True)",
    ],
)
def test_bare_pytest_fixture_on_async_def_is_rejected(decorator_source: str) -> None:
    """RED case: the shape that silently never runs must be classified a violation."""
    source = f"{decorator_source}\nasync def broken():\n    yield\n"
    assert _is_bare_pytest_fixture(_decorator_of(source)) is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "decorator_source",
    [
        "@pytest_asyncio.fixture",
        "@pytest_asyncio.fixture(autouse=True)",
        "@pytest_asyncio.fixture(loop_scope='function')",
    ],
)
def test_pytest_asyncio_fixture_is_allowed(decorator_source: str) -> None:
    """GREEN case: the correct decorator for an async fixture must not be flagged."""
    source = f"{decorator_source}\nasync def ok():\n    yield\n"
    assert _is_bare_pytest_fixture(_decorator_of(source)) is False


@pytest.mark.unit
def test_unrelated_decorators_are_not_flagged() -> None:
    """A decorator that merely ends in a call must not be misread as a fixture."""
    for source in ("@pytest.mark.asyncio\nasync def t():\n    pass\n",):
        assert _is_bare_pytest_fixture(_decorator_of(source)) is False


@pytest.mark.unit
def test_repo_is_clean() -> None:
    """No async fixture in src/ or tests/ may carry a bare @pytest.fixture."""
    violations = find_violations()
    assert violations == [], (
        "async fixtures with a bare @pytest.fixture do not run under "
        "pytest-asyncio STRICT mode and error on pytest >= 9.1: "
        + ", ".join(f"{p}:{ln} ({name})" for p, ln, name in violations)
    )
