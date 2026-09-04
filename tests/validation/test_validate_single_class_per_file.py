# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression tests for the single-class-per-file validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

VALIDATOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "validation"
    / "validate-single-class-per-file.py"
)


def _load_validator_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "validate_single_class_per_file", VALIDATOR_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_delegation_terminal_v2_exception_is_scoped_to_its_canonical_path(
    tmp_path: Path,
) -> None:
    """An identically named file elsewhere must remain subject to the rule."""
    validator = _load_validator_module()
    canonical_path = Path(
        "src/omnibase_core/models/delegation/wire/model_delegation_terminal_v2.py"
    )
    shadow_path = (
        tmp_path.parent
        / "single_class_scope_shadow"
        / "model_delegation_terminal_v2.py"
    )
    shadow_path.parent.mkdir()
    shadow_path.write_text("class First:\n    pass\n\nclass Second:\n    pass\n")

    assert validator.should_exclude_file(canonical_path)
    assert not validator.should_exclude_file(shadow_path)
    assert not validator.check_file(shadow_path)["valid"]
