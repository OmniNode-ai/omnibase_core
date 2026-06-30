# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the generated-node model-class-existence enforcement gate (OMN-13609).

This validator is the thin pre-commit / CI wrapper around the canonical platform
authority ``validate_model_class_existence``. It scans generated-node
``contract.yaml`` files (those with a co-located ``handler.py``) and fails when a
contract declares a model class absent from the handler.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators.generated_node_model_class_exists import (
    main,
    validate_file,
    validate_paths,
)

pytestmark = pytest.mark.unit


_CONTRACT = """\
name: node_foo
contract_version: "1.0.0"
node_type: compute
input_model:
  name: ModelFooInput
  module: generated.models
output_model:
  name: ModelFooOutput
  module: generated.models
"""

_HANDLER_MATCHING = """\
from pydantic import BaseModel


class ModelFooInput(BaseModel):
    value: int


class ModelFooOutput(BaseModel):
    result: int


def handle(input_data: dict) -> dict:
    return {"result": 0}
"""

_HANDLER_MISMATCH = """\
from pydantic import BaseModel


class ModelWrongInput(BaseModel):
    value: int


class ModelFooOutput(BaseModel):
    result: int


def handle(input_data: dict) -> dict:
    return {"result": 0}
"""


def _write_node(tmp_path: Path, contract: str, handler: str | None) -> Path:
    node_dir = tmp_path / "node_foo"
    node_dir.mkdir()
    (node_dir / "contract.yaml").write_text(contract, encoding="utf-8")
    if handler is not None:
        (node_dir / "handler.py").write_text(handler, encoding="utf-8")
    return node_dir / "contract.yaml"


def test_matching_handler_passes(tmp_path: Path) -> None:
    contract_path = _write_node(tmp_path, _CONTRACT, _HANDLER_MATCHING)
    assert validate_file(contract_path) == []


def test_mismatched_handler_fails(tmp_path: Path) -> None:
    contract_path = _write_node(tmp_path, _CONTRACT, _HANDLER_MISMATCH)
    issues = validate_file(contract_path)
    assert len(issues) == 1
    assert "ModelFooInput" in issues[0].message


def test_contract_without_handler_is_out_of_scope(tmp_path: Path) -> None:
    """No co-located handler.py => model-class existence cannot be proven => skip."""
    contract_path = _write_node(tmp_path, _CONTRACT, handler=None)
    assert validate_file(contract_path) == []


def test_validate_paths_scans_directory(tmp_path: Path) -> None:
    _write_node(tmp_path, _CONTRACT, _HANDLER_MISMATCH)
    issues = validate_paths([tmp_path])
    assert len(issues) == 1


def test_main_returns_nonzero_on_violation(tmp_path: Path) -> None:
    _write_node(tmp_path, _CONTRACT, _HANDLER_MISMATCH)
    assert main([str(tmp_path)]) == 1


def test_main_returns_zero_on_clean(tmp_path: Path) -> None:
    _write_node(tmp_path, _CONTRACT, _HANDLER_MATCHING)
    assert main([str(tmp_path)]) == 0
