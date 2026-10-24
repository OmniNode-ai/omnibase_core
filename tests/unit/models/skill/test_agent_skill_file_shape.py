# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical locations and class declarations of Agent Skills modules (OMN-21373)."""

import ast
import importlib
from pathlib import Path

import pytest

from omnibase_core.validators.canonical_file_shape import is_canonical_location


@pytest.mark.unit
@pytest.mark.parametrize(
    "module_name",
    [
        "enums.enum_agent_skill_render_profile",
        "handlers.handler_agent_skill_codec",
        "models.skill.model_agent_skill",
        "models.skill.model_agent_skill_frontmatter",
        "models.skill.model_agent_skill_onex_keys",
        "models.skill.model_agent_skill_source",
        "models.skill.model_agent_skill_verdict",
        "models.skill.model_claude_code_skill_extensions",
    ],
)
def test_agent_skill_modules_have_canonical_file_shape(module_name: str) -> None:
    module = importlib.import_module(f"omnibase_core.{module_name}")
    assert module.__file__ is not None
    path = Path(module.__file__).resolve()
    root = Path(__file__).resolve().parents[4]
    relative = path.relative_to(root).as_posix()
    assert relative == f"src/omnibase_core/{module_name.replace('.', '/')}.py"
    assert is_canonical_location(relative)

    tree = ast.parse(path.read_text(encoding="utf-8"))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert len(classes) <= 1, f"{relative} declares multiple top-level classes"
    if classes:
        prefix = "Enum" if module_name.startswith("enums.") else "Model"
        assert classes[0].name.startswith(prefix)
