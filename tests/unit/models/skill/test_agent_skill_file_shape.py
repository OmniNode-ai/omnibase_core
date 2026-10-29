# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical locations and class declarations of Agent Skills modules (OMN-21373)."""

import ast
import importlib
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_canonical_file_shape_text import (
    ModelCanonicalFileShapeText,
)
from omnibase_core.models.validation.model_canonical_file_shape_tree import (
    ModelCanonicalFileShapeTree,
)
from omnibase_core.validation.checker_canonical_file_shape import file_rule_refusals
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import RULES


@pytest.mark.unit
@pytest.mark.parametrize(
    "module_name",
    [
        "enums.enum_agent_skill_render_profile",
        "validation.checker_agent_skill_codec",
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
    # This test checks locations; supply a handler binding for the codec.
    shape_tree = ModelCanonicalFileShapeTree(
        files=(relative,),
        contract_texts=(
            ModelCanonicalFileShapeText(
                path="src/omnibase_core/nodes/node_skill/contract.yaml",
                text="handler:\n  module: omnibase_core.validation.checker_agent_skill_codec\n",
            ),
        ),
    )
    assert relative not in file_rule_refusals(shape_tree, RULES)

    tree = ast.parse(path.read_text(encoding="utf-8"))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert len(classes) <= 1, f"{relative} declares multiple top-level classes"
    if classes:
        prefix = "Enum" if module_name.startswith("enums.") else "Model"
        assert classes[0].name.startswith(prefix)
