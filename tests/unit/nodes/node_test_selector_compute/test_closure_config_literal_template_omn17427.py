# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-17427: the closure-config error text is a template argument.

``PydanticCustomError`` types its ``message_template`` as ``LiteralString``.
``_invalid`` in ``model_closure_config.py`` passed the formatted error text
there, which pyright refuses (reportArgumentType) and which turned dev's
pyright step red. The fix passes a constant ``"{msg}"`` template and the text
as its ``msg`` context. These tests fail at merge base 3f994354e, where the
text itself is the template and the error carries no context.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.test_selector import model_closure_config
from omnibase_core.models.nodes.test_selector.model_closure_config import (
    ModelClosureConfig,
)

pytestmark = pytest.mark.unit


def _custom_error_calls() -> list[ast.Call]:
    tree = ast.parse(Path(model_closure_config.__file__).read_text())
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "PydanticCustomError"
    ]


def test_every_closure_config_error_template_is_a_string_literal() -> None:
    calls = _custom_error_calls()
    assert calls, "model_closure_config.py no longer builds a PydanticCustomError"
    for call in calls:
        assert len(call.args) >= 2
        template = call.args[1]
        assert isinstance(template, ast.Constant), ast.unparse(template)
        assert isinstance(template.value, str)


def test_closure_config_error_text_is_carried_as_the_msg_context() -> None:
    raw = "/abs{root}/"
    with pytest.raises(ValidationError) as excinfo:
        ModelClosureConfig(candidate_roots=(raw,))
    (error,) = excinfo.value.errors()
    expected = f"candidate root must be repo-relative with no '..': {raw!r}"
    assert error["type"] == "closure_config"
    assert error["ctx"] == {"msg": expected}
    assert error["msg"] == expected
