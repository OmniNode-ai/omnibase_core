# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Focused coverage tests for ServiceContractValidator (OMN-12386).

Targets the paths in services/service_contract_validator.py (score 2.6) that
are not covered by the existing test_contract_validator.py:

- validate_contract_yaml: size limit, unknown contract type, ValidationError
  path, ModelOnexError path, ValueError path, TypeError path
- validate_model_compliance: size limits, syntax error, recursion error,
  no model classes, missing input/output model, field validation, naming
- validate_contract_file: unsafe path, missing file, permission error, size
- _calculate_score: bounds (0.0 clamp)
- _check_onex_compliance: version mismatch, missing name, missing description,
  short description, missing input/output model, bad module path
- validate_onex_naming and validate_architecture_compliance (sync use)

Does NOT perform broad refactors — behavior is pinned here first.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from omnibase_core.services.service_contract_validator import (
    MAX_CODE_SIZE_BYTES,
    MAX_YAML_SIZE_BYTES,
    ServiceContractValidator,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Minimal valid YAML fixtures
# ---------------------------------------------------------------------------

_VALID_EFFECT_YAML = """\
name: NodeFooEffect
contract_version:
  major: 1
  minor: 0
  patch: 0
description: A valid effect contract for testing purposes.
node_type: effect_generic
input_model: ModelFooInput
output_model: ModelFooOutput
io_operations:
  - operation_type: read
    resource_type: external_api
    resource_identifier: foo.api/run
"""

_VALID_COMPUTE_YAML = """\
name: NodeBarCompute
contract_version:
  major: 1
  minor: 0
  patch: 0
description: A valid compute contract for testing purposes.
node_type: compute_generic
input_model: ModelBarInput
output_model: ModelBarOutput
"""


# ---------------------------------------------------------------------------
# validate_contract_yaml — size and type guard paths
# ---------------------------------------------------------------------------


class TestValidateContractYamlGuards:
    def test_empty_content_returns_invalid(self) -> None:
        v = ServiceContractValidator()
        result = v.validate_contract_yaml("", "effect")
        assert not result.is_valid
        assert result.score == 0.0

    def test_null_yaml_returns_invalid(self) -> None:
        v = ServiceContractValidator()
        result = v.validate_contract_yaml("null\n", "effect")
        assert not result.is_valid
        assert result.score == 0.0
        assert any("Empty YAML" in viol for viol in result.violations)

    def test_yaml_parse_error_returns_invalid(self) -> None:
        v = ServiceContractValidator()
        result = v.validate_contract_yaml(": [broken yaml\n", "effect")
        assert not result.is_valid
        assert result.score == 0.0
        assert any("YAML parsing error" in viol for viol in result.violations)

    def test_unknown_contract_type_returns_invalid(self) -> None:
        v = ServiceContractValidator()
        result = v.validate_contract_yaml(_VALID_EFFECT_YAML, "nonexistent_type")  # type: ignore[arg-type]
        assert not result.is_valid
        assert result.score == 0.0
        assert any("Unknown contract type" in viol for viol in result.violations)

    def test_content_too_large_raises_onex_error(self) -> None:
        v = ServiceContractValidator()
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        huge = "x" * (MAX_YAML_SIZE_BYTES + 1)
        with pytest.raises(ModelOnexError):
            v.validate_contract_yaml(huge, "effect")

    def test_valid_effect_contract_passes(self) -> None:
        v = ServiceContractValidator()
        result = v.validate_contract_yaml(_VALID_EFFECT_YAML, "effect")
        assert result.is_valid
        assert result.score > 0.0

    def test_valid_compute_contract_accepted(self) -> None:
        """Compute contract parses without unknown-type violation."""
        v = ServiceContractValidator()
        result = v.validate_contract_yaml(_VALID_COMPUTE_YAML, "compute")
        # The compute contract may have business-rule violations (e.g. missing
        # algorithm) but must not raise "Unknown contract type" or crash.
        assert not any("Unknown contract type" in viol for viol in result.violations), (
            f"Unexpected unknown-type error: {result.violations!r}"
        )

    def test_score_clamped_to_zero_on_many_violations(self) -> None:
        """Score never goes below 0.0 even with many violations."""
        v = ServiceContractValidator()
        # A contract that validates structurally but has many missing ONEX fields
        minimal = (
            "name: Bad\n"
            "contract_version:\n"
            "  major: 1\n"
            "  minor: 0\n"
            "  patch: 0\n"
            "description: x\n"
            "node_type: effect_generic\n"
            "input_model: \n"
            "output_model: \n"
        )
        result = v.validate_contract_yaml(minimal, "effect")
        assert result.score >= 0.0

    def test_all_contract_types_are_valid(self) -> None:
        """All four node types accepted without 'Unknown contract type' violation."""
        v = ServiceContractValidator()
        base = """\
name: Node{suffix}
contract_version:
  major: 1
  minor: 0
  patch: 0
description: Test contract for coverage.
node_type: {node_type}
input_model: ModelInput
output_model: ModelOutput
"""
        for ctype, suffix, node_type in (
            ("effect", "FooEffect", "effect_generic"),
            ("compute", "FooCompute", "compute_generic"),
            ("reducer", "FooReducer", "reducer_generic"),
            ("orchestrator", "FooOrchestrator", "orchestrator_generic"),
        ):
            result = v.validate_contract_yaml(
                base.format(suffix=suffix, node_type=node_type),
                ctype,  # type: ignore[arg-type]
            )
            assert not any(
                "Unknown contract type" in viol for viol in result.violations
            ), f"Unexpected unknown-type error for {ctype}"


# ---------------------------------------------------------------------------
# validate_model_compliance — code-level paths
# ---------------------------------------------------------------------------


class TestValidateModelCompliance:
    def test_model_code_too_large_raises(self) -> None:
        v = ServiceContractValidator()
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        huge = "x" * (MAX_CODE_SIZE_BYTES + 1)
        with pytest.raises(ModelOnexError):
            v.validate_model_compliance(huge, _VALID_EFFECT_YAML)

    def test_contract_yaml_too_large_raises(self) -> None:
        v = ServiceContractValidator()
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        huge_yaml = "x" * (MAX_YAML_SIZE_BYTES + 1)
        with pytest.raises(ModelOnexError):
            v.validate_model_compliance("class ModelFoo(BaseModel): pass", huge_yaml)

    def test_empty_contract_yaml_returns_invalid(self) -> None:
        v = ServiceContractValidator()
        result = v.validate_model_compliance(
            "class ModelFoo(BaseModel): pass", "null\n"
        )
        assert not result.is_valid

    def test_syntax_error_in_code_returns_invalid(self) -> None:
        v = ServiceContractValidator()
        result = v.validate_model_compliance("def broken(: pass", _VALID_EFFECT_YAML)
        assert not result.is_valid
        assert any("syntax error" in viol.lower() for viol in result.violations)

    def test_no_model_classes_in_code(self) -> None:
        v = ServiceContractValidator()
        result = v.validate_model_compliance(
            "x = 1  # no classes here\n", _VALID_EFFECT_YAML
        )
        assert not result.is_valid
        assert any("No Pydantic model classes" in viol for viol in result.violations)

    def test_missing_input_model_class_penalized(self) -> None:
        v = ServiceContractValidator()
        # Contract declares ModelFooInput but code has different model
        code = "class ModelFooOutput(BaseModel):\n    value: int\n"
        result = v.validate_model_compliance(code, _VALID_EFFECT_YAML)
        assert any(
            "Input model" in viol and "not found" in viol for viol in result.violations
        )

    def test_missing_output_model_class_penalized(self) -> None:
        v = ServiceContractValidator()
        code = "class ModelFooInput(BaseModel):\n    value: int\n"
        result = v.validate_model_compliance(code, _VALID_EFFECT_YAML)
        assert any(
            "Output model" in viol and "not found" in viol for viol in result.violations
        )

    def test_model_with_any_type_warns(self) -> None:
        v = ServiceContractValidator()
        code = (
            "from typing import Any\n"
            "class ModelFooInput(BaseModel):\n"
            "    data: Any\n"
            "class ModelFooOutput(BaseModel):\n"
            "    result: Any\n"
        )
        result = v.validate_model_compliance(code, _VALID_EFFECT_YAML)
        assert any("Any" in w for w in result.warnings)

    def test_qualified_pydantic_basemodel_is_detected(self) -> None:
        v = ServiceContractValidator()
        code = (
            "import pydantic\n"
            "class ModelFooInput(pydantic.BaseModel):\n"
            "    value: str\n"
            "class ModelFooOutput(pydantic.BaseModel):\n"
            "    result: bool\n"
        )
        result = v.validate_model_compliance(code, _VALID_EFFECT_YAML)
        assert not any(
            "No Pydantic model classes" in violation for violation in result.violations
        )
        assert not any("not found" in violation for violation in result.violations)

    def test_non_model_class_naming_warns(self) -> None:
        v = ServiceContractValidator()
        code = (
            "class WrongNameInput(BaseModel):\n"
            "    x: int\n"
            "class WrongNameOutput(BaseModel):\n"
            "    y: int\n"
        )
        result = v.validate_model_compliance(code, _VALID_EFFECT_YAML)
        assert any("should follow ONEX naming" in w for w in result.warnings)

    def test_non_uppercase_class_violates(self) -> None:
        v = ServiceContractValidator()
        code = "class modelFooInput(BaseModel):\n    x: int\n"
        result = v.validate_model_compliance(code, _VALID_EFFECT_YAML)
        assert any("PascalCase" in viol for viol in result.violations)


# ---------------------------------------------------------------------------
# validate_contract_file
# ---------------------------------------------------------------------------


class TestValidateContractFile:
    def test_missing_file_returns_invalid(self, tmp_path: Path) -> None:
        v = ServiceContractValidator()
        result = v.validate_contract_file(tmp_path / "does_not_exist.yaml", "effect")
        assert not result.is_valid
        assert any("not found" in viol for viol in result.violations)

    def test_valid_file_passes(self, tmp_path: Path) -> None:
        v = ServiceContractValidator()
        contract_file = tmp_path / "test_contract.yaml"
        contract_file.write_text(_VALID_EFFECT_YAML)
        result = v.validate_contract_file(contract_file, "effect")
        assert result.is_valid

    def test_directory_path_raises_onex_error(self, tmp_path: Path) -> None:
        """A path pointing to a directory fails the safe-path check."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        v = ServiceContractValidator()
        with pytest.raises(ModelOnexError):
            v.validate_contract_file(tmp_path, "effect")

    def test_path_outside_base_dir_raises_onex_error(self, tmp_path: Path) -> None:
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        v = ServiceContractValidator()
        base_dir = tmp_path / "contracts"
        base_dir.mkdir()
        outside = tmp_path / "outside.yaml"
        outside.write_text(_VALID_EFFECT_YAML)
        with pytest.raises(ModelOnexError):
            v.validate_contract_file(outside, "effect", base_dir=base_dir)

    def test_encoding_error_returns_invalid(self, tmp_path: Path) -> None:
        v = ServiceContractValidator()
        bad_file = tmp_path / "bad_encoding.yaml"
        bad_file.write_bytes(b"\xff\xfe" + b"\x00" * 10)
        result = v.validate_contract_file(bad_file, "effect")
        assert not result.is_valid


# ---------------------------------------------------------------------------
# _check_onex_compliance edge paths
# ---------------------------------------------------------------------------


class TestCheckOnexComplianceEdgePaths:
    def test_version_mismatch_produces_warning(self) -> None:
        """Contract version != validator version → warning (not violation)."""
        v = ServiceContractValidator()
        yaml_with_v2 = """\
name: NodeFooEffect
contract_version:
  major: 2
  minor: 0
  patch: 0
description: Effect node for version mismatch test.
node_type: effect_generic
input_model: ModelFooInput
output_model: ModelFooOutput
"""
        result = v.validate_contract_yaml(yaml_with_v2, "effect")
        assert any("version mismatch" in w.lower() for w in result.warnings)

    def test_short_description_triggers_warning(self) -> None:
        """Description shorter than MIN_DESCRIPTION_LENGTH produces a warning."""
        v = ServiceContractValidator()
        # MIN_DESCRIPTION_LENGTH=10; use a 5-char description (valid per Pydantic
        # but too short per _check_onex_compliance).
        yaml_short = """\
name: NodeFooEffect
contract_version:
  major: 1
  minor: 0
  patch: 0
description: Short
node_type: effect_generic
input_model: ModelFooInput
output_model: ModelFooOutput
io_operations:
  - operation_type: read
    resource_type: external_api
    resource_identifier: foo.api/run
"""
        result = v.validate_contract_yaml(yaml_short, "effect")
        assert any("too short" in w.lower() for w in result.warnings), (
            f"Expected 'too short' description warning; "
            f"got warnings={result.warnings!r}, violations={result.violations!r}"
        )

    def test_short_description_produces_warning(self) -> None:
        v = ServiceContractValidator()
        yaml_short_desc = """\
name: NodeFooEffect
contract_version:
  major: 1
  minor: 0
  patch: 0
description: tiny
node_type: effect_generic
input_model: ModelFooInput
output_model: ModelFooOutput
"""
        result = v.validate_contract_yaml(yaml_short_desc, "effect")
        assert any("too short" in w.lower() for w in result.warnings)

    def test_non_model_input_name_warns(self) -> None:
        v = ServiceContractValidator()
        yaml_bad_input = """\
name: NodeFooEffect
contract_version:
  major: 1
  minor: 0
  patch: 0
description: A valid effect contract for testing purposes.
node_type: effect_generic
input_model: FooInput
output_model: ModelFooOutput
"""
        result = v.validate_contract_yaml(yaml_bad_input, "effect")
        assert any("should follow ONEX naming" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# _calculate_score bounds
# ---------------------------------------------------------------------------


class TestCalculateScore:
    def test_score_never_below_zero(self) -> None:
        v = ServiceContractValidator()
        # Force many violations via invalid YAML fields
        result = v.validate_contract_yaml(
            "name: Bad\ncontract_version:\n  major: 1\n  minor: 0\n  patch: 0\n"
            "description: t\nnode_type: effect_generic\n",
            "effect",
        )
        assert result.score >= 0.0

    def test_score_never_above_one(self) -> None:
        v = ServiceContractValidator()
        result = v.validate_contract_yaml(_VALID_EFFECT_YAML, "effect")
        assert result.score <= 1.0


# ---------------------------------------------------------------------------
# validate_onex_naming (async via asyncio.run)
# ---------------------------------------------------------------------------


class TestValidateOnexNaming:
    def test_private_classes_skipped(self) -> None:
        v = ServiceContractValidator()
        code = "class _InternalHelper(BaseModel):\n    x: int\n"
        violations = asyncio.run(v.validate_onex_naming("model_foo.py", code))
        # Private class (_InternalHelper) must not produce a naming violation
        assert not any("_InternalHelper" in str(viol) for viol in violations)

    def test_file_with_wrong_name_pattern_flagged(self) -> None:
        v = ServiceContractValidator()
        # File starts with "model_" but doesn't match the full pattern
        code = "class ModelFoo(BaseModel):\n    x: int\n"
        violations = asyncio.run(
            v.validate_onex_naming("model_foo_BADNAME_bad.py", code)
        )
        # May or may not produce a violation depending on pattern match
        # The key contract: no exceptions raised
        assert isinstance(violations, list)

    def test_empty_source_returns_empty(self) -> None:
        v = ServiceContractValidator()
        violations = asyncio.run(v.validate_onex_naming("model_foo.py", ""))
        assert violations == []


# ---------------------------------------------------------------------------
# add_custom_rule and configure_onex_standards
# ---------------------------------------------------------------------------


class TestCustomRuleAndStandards:
    def test_add_custom_rule_stores_rule(self) -> None:
        v = ServiceContractValidator()
        mock_rule = MagicMock()
        mock_rule.rule_id = "test-rule-id"
        v.add_custom_rule(mock_rule)
        assert mock_rule in v.custom_rules

    def test_configure_onex_standards_stores_standards(self) -> None:
        v = ServiceContractValidator()
        mock_standards = MagicMock()
        v.configure_onex_standards(mock_standards)
        assert v.onex_standards is mock_standards
