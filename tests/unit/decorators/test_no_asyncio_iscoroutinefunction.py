# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Guard: omnibase_core never calls ``asyncio.iscoroutinefunction``.

CPython 3.14 deprecates ``asyncio.iscoroutinefunction`` (removal slated for
3.16). Under ``-W error`` the call in ``standard_error_handling`` raised a
DeprecationWarning while ``ModelONEXContainer`` was being defined, so the
OMN-17870 Werror teardown regression failed at collection on 3.14. CI pins
3.12, where the call is silent, so this test reads the source instead of
relying on the warning. ``inspect.iscoroutinefunction`` is the replacement.
"""

import ast
import warnings
from pathlib import Path

import pytest

import omnibase_core

SRC_ROOT = Path(omnibase_core.__file__).parent


def _asyncio_iscoroutinefunction_calls() -> list[str]:
    hits: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "iscoroutinefunction"
                and isinstance(node.value, ast.Name)
                and node.value.id == "asyncio"
            ):
                hits.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno}")
    return hits


@pytest.mark.unit
def test_src_has_no_asyncio_iscoroutinefunction() -> None:
    assert _asyncio_iscoroutinefunction_calls() == []


@pytest.mark.unit
def test_error_handling_decorators_emit_no_deprecation_warning() -> None:
    from omnibase_core.decorators.decorator_error_handling import (
        io_error_handling,
        standard_error_handling,
        validation_error_handling,
    )

    async def async_op() -> None:
        return None

    def sync_op() -> None:
        return None

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        standard_error_handling("op")(async_op)
        standard_error_handling("op")(sync_op)
        validation_error_handling("op")(async_op)
        io_error_handling("op")(async_op)
