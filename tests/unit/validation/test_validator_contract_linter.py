# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ValidatorContractLinter - Contract-driven YAML contract file validator.

Tests comprehensive contract linting functionality including:
- Deprecated field name validation (version -> contract_version migration)
- YAML syntax validation
- Required and recommended fields
- Naming conventions
- Fingerprint validation

Ticket: OMN-1431
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_contract_linter import (
    RULE_DEPRECATED_FIELD_NAMES,
    ValidatorContractLinter,
)

# =============================================================================
# Test Helpers
# =============================================================================


def create_test_contract(
    validator_id: str = "contract_linter",
    target_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    severity_default: EnumSeverity = EnumSeverity.ERROR,
) -> ModelValidatorSubcontract:
    """Create a test contract with specified configuration."""
    return ModelValidatorSubcontract(
        # NOTE: ModelValidatorSubcontract uses its own 'version' field (not contract_version).
        # This is intentional - only ModelContractBase was renamed per OMN-1431.
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id=validator_id,
        validator_name="Contract Linter",
        validator_description="Contract linter for testing",
        target_patterns=target_patterns or ["**/*.yaml"],
        exclude_patterns=exclude_patterns or [],
        suppression_comments=["# noqa:"],
        fail_on_error=True,
        fail_on_warning=False,
        max_violations=0,
        severity_default=severity_default,
    )


# =============================================================================
# Deprecated Field Names Guardrail Tests (OMN-1431)
# =============================================================================


@pytest.mark.unit
class TestValidateDeprecatedFieldNames:
    """Tests for _validate_deprecated_field_names guardrail.

    This guardrail enforces the OMN-1431 migration from 'version' to 'contract_version'
    in YAML contracts. It always runs and returns ERROR severity when deprecated
    field names are detected.
    """

    def test_version_only_returns_error(self, tmp_path: Path) -> None:
        """Test that YAML with only 'version:' (no 'contract_version:') returns ERROR.

        When a YAML contract uses the deprecated 'version' field without the
        new 'contract_version' field, the guardrail should return an error
        indicating the field needs to be renamed.
        """
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        # YAML data with deprecated 'version' field only
        data: dict[str, object] = {
            "name": "TestContract",
            "version": "1.0.0",  # Deprecated field
            "node_type": "compute_generic",
        }
        test_path = tmp_path / "test_contract.yaml"

        issues = validator._validate_deprecated_field_names(data, test_path, contract)

        assert len(issues) == 1
        assert issues[0].code == RULE_DEPRECATED_FIELD_NAMES
        assert issues[0].severity == EnumSeverity.ERROR
        assert "version" in issues[0].message
        assert "contract_version" in issues[0].message
        assert "OMN-1431" in issues[0].message
        assert issues[0].file_path == test_path
        assert issues[0].suggestion is not None
        assert "Rename" in issues[0].suggestion
        # Verify context contains migration information
        assert issues[0].context is not None
        assert issues[0].context.get("found_field") == "version"
        assert issues[0].context.get("expected_field") == "contract_version"
        assert issues[0].context.get("migration_ticket") == "OMN-1431"

    def test_contract_version_only_passes(self, tmp_path: Path) -> None:
        """Test that YAML with only 'contract_version:' passes validation.

        When a YAML contract uses the new 'contract_version' field (without
        the deprecated 'version' field), no deprecation issues should be raised.
        """
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        # YAML data with new 'contract_version' field only
        data: dict[str, object] = {
            "name": "TestContract",
            "contract_version": "1.0.0",  # New field
            "node_type": "compute_generic",
        }
        test_path = tmp_path / "test_contract.yaml"

        issues = validator._validate_deprecated_field_names(data, test_path, contract)

        assert len(issues) == 0

    def test_both_version_and_contract_version_returns_error(
        self, tmp_path: Path
    ) -> None:
        """Test that YAML with both 'version:' and 'contract_version:' returns ERROR.

        Since v0.9.0 is a breaking change, we don't support transitional dual-field
        state. The deprecated 'version' field must be removed entirely, even if
        'contract_version' is present.
        """
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        # YAML data with both fields (invalid - must remove deprecated field)
        data: dict[str, object] = {
            "name": "TestContract",
            "version": "1.0.0",  # Deprecated - must be removed
            "contract_version": "1.0.0",  # New field is present but version must go
            "node_type": "compute_generic",
        }
        test_path = tmp_path / "test_contract.yaml"

        issues = validator._validate_deprecated_field_names(data, test_path, contract)

        assert len(issues) == 1
        assert issues[0].code == RULE_DEPRECATED_FIELD_NAMES
        assert issues[0].severity == EnumSeverity.ERROR
        assert "Remove" in issues[0].message
        assert "contract_version" in issues[0].message
        assert issues[0].suggestion is not None
        assert "Remove" in issues[0].suggestion

    def test_neither_version_field_passes(self, tmp_path: Path) -> None:
        """Test that YAML with neither version field passes the deprecation check.

        When a YAML contract has neither 'version' nor 'contract_version',
        the deprecation guardrail should not raise an error. Other validators
        (like required_fields) would catch missing required fields.
        """
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        # YAML data with no version fields
        data: dict[str, object] = {
            "name": "TestContract",
            "node_type": "compute_generic",
            "description": "A test contract without version fields",
        }
        test_path = tmp_path / "test_contract.yaml"

        issues = validator._validate_deprecated_field_names(data, test_path, contract)

        assert len(issues) == 0

    def test_error_severity_is_always_error(self, tmp_path: Path) -> None:
        """Test that deprecated field names always produce ERROR severity.

        The guardrail should always use ERROR severity regardless of the
        contract's severity_default setting, as this is a migration enforcement
        mechanism that should not be configurable.
        """
        # Create contract with WARNING as default severity
        contract = create_test_contract(severity_default=EnumSeverity.WARNING)
        validator = ValidatorContractLinter(contract=contract)

        # YAML data with deprecated 'version' field
        data: dict[str, object] = {
            "name": "TestContract",
            "version": "1.0.0",
            "node_type": "compute_generic",
        }
        test_path = tmp_path / "test_contract.yaml"

        issues = validator._validate_deprecated_field_names(data, test_path, contract)

        # Should still be ERROR, not WARNING
        assert len(issues) == 1
        assert issues[0].severity == EnumSeverity.ERROR

    def test_rule_name_matches_code(self, tmp_path: Path) -> None:
        """Test that rule_name matches the code for consistency."""
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        data: dict[str, object] = {
            "name": "TestContract",
            "version": "1.0.0",
            "node_type": "compute_generic",
        }
        test_path = tmp_path / "test_contract.yaml"

        issues = validator._validate_deprecated_field_names(data, test_path, contract)

        assert len(issues) == 1
        assert issues[0].code == RULE_DEPRECATED_FIELD_NAMES
        assert issues[0].rule_name == RULE_DEPRECATED_FIELD_NAMES

    def test_line_number_is_set(self, tmp_path: Path) -> None:
        """Test that line_number is set in the validation issue."""
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        data: dict[str, object] = {
            "name": "TestContract",
            "version": "1.0.0",
            "node_type": "compute_generic",
        }
        test_path = tmp_path / "test_contract.yaml"

        issues = validator._validate_deprecated_field_names(data, test_path, contract)

        assert len(issues) == 1
        # Line number is set to 1 as we don't track exact line in parsed dict
        assert issues[0].line_number == 1


@pytest.mark.unit
class TestValidateDeprecatedFieldNamesIntegration:
    """Integration tests for deprecated field names validation via validate_file."""

    def test_validate_file_catches_deprecated_version(self, tmp_path: Path) -> None:
        """Test that validate_file catches deprecated 'version' field via guardrail.

        The _validate_file method should call _validate_deprecated_field_names
        as a guardrail check and include any issues in the result.
        """
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        # Create actual YAML file with deprecated field
        yaml_file = tmp_path / "deprecated_contract.yaml"
        yaml_file.write_text(
            """
name: TestContract
version: "1.0.0"
node_type: compute_generic
description: A contract using deprecated version field
"""
        )

        result = validator.validate_file(yaml_file)

        # Should fail validation due to deprecated field
        assert not result.is_valid
        # Find the deprecation issue
        deprecation_issues = [
            i for i in result.issues if i.code == RULE_DEPRECATED_FIELD_NAMES
        ]
        assert len(deprecation_issues) == 1
        assert "version" in deprecation_issues[0].message
        assert "contract_version" in deprecation_issues[0].message

    def test_validate_file_passes_with_contract_version(self, tmp_path: Path) -> None:
        """Test that validate_file passes when 'contract_version' is used.

        The _validate_file method should not produce deprecation errors when
        the correct 'contract_version' field is used.
        """
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        # Create actual YAML file with new field
        yaml_file = tmp_path / "valid_contract.yaml"
        yaml_file.write_text(
            """
name: TestContract
contract_version: "1.0.0"
node_type: compute_generic
description: A contract using correct contract_version field
"""
        )

        result = validator.validate_file(yaml_file)

        # Should not have deprecation issues
        deprecation_issues = [
            i for i in result.issues if i.code == RULE_DEPRECATED_FIELD_NAMES
        ]
        assert len(deprecation_issues) == 0


@pytest.mark.unit
class TestValidatorContractLinterImports:
    """Tests for module imports and exports."""

    def test_import_validator_contract_linter(self) -> None:
        """Test that ValidatorContractLinter can be imported."""
        from omnibase_core.validation.validator_contract_linter import (
            ValidatorContractLinter,
        )

        assert ValidatorContractLinter is not None

    def test_import_rule_deprecated_field_names(self) -> None:
        """Test that RULE_DEPRECATED_FIELD_NAMES constant can be imported."""
        from omnibase_core.validation.validator_contract_linter import (
            RULE_DEPRECATED_FIELD_NAMES,
        )

        assert RULE_DEPRECATED_FIELD_NAMES == "deprecated_field_names"

    def test_rule_deprecated_field_names_in_all(self) -> None:
        """Test that RULE_DEPRECATED_FIELD_NAMES is in __all__ exports."""
        from omnibase_core.validation import validator_contract_linter

        assert "RULE_DEPRECATED_FIELD_NAMES" in validator_contract_linter.__all__


@pytest.mark.unit
class TestValidatorContractLinterInit:
    """Tests for ValidatorContractLinter initialization."""

    def test_init_with_contract(self) -> None:
        """Test initialization with a pre-loaded contract."""
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        assert validator.contract is contract

    def test_init_without_contract(self) -> None:
        """Test initialization without a contract (lazy loading)."""
        validator = ValidatorContractLinter()

        assert validator is not None
        assert validator.validator_id == "contract_linter"

    def test_init_with_registry(self) -> None:
        """Test initialization with a ContractHashRegistry."""
        from omnibase_core.contracts import ContractHashRegistry

        contract = create_test_contract()
        registry = ContractHashRegistry()
        validator = ValidatorContractLinter(contract=contract, registry=registry)

        assert validator.registry is registry


# =============================================================================
# Model Class Existence Tests (OMN-13609 - WS-C Phase 1.1)
#
# Ported from SEA pipeline/validator.py model_types check: a generated node's
# contract-declared input_model/output_model class names must exist as top-level
# classes in the co-located generated handler. If a declared class name is
# undefined in the handler, the validator rejects the contract.
# =============================================================================


@pytest.mark.unit
class TestValidateModelClassExistence:
    """Tests for the model-class-existence check (OMN-13609)."""

    def test_undefined_model_class_is_rejected(self, tmp_path: Path) -> None:
        """Contract declaring a model class absent from the handler is rejected."""
        from omnibase_core.validation.validator_contract_linter import (
            RULE_MODEL_CLASS_EXISTS,
            validate_model_class_existence,
        )

        contract_data: dict[str, object] = {
            "name": "node_foo",
            "contract_version": "1.0.0",
            "node_type": "compute",
            "input_model": {"name": "ModelFooInput", "module": "generated.models"},
            "output_model": {"name": "ModelFooOutput", "module": "generated.models"},
        }
        handler_source = (
            "from pydantic import BaseModel\n"
            "\n"
            "class ModelBarInput(BaseModel):\n"
            "    value: int\n"
            "\n"
            "class ModelFooOutput(BaseModel):\n"
            "    result: int\n"
            "\n"
            "def handle(input_data: dict) -> dict:\n"
            "    return {'result': input_data.get('value', 0)}\n"
        )

        issues = validate_model_class_existence(
            contract_data,
            handler_source,
            path=tmp_path / "contract.yaml",
            severity=EnumSeverity.ERROR,
        )

        assert len(issues) == 1
        assert issues[0].code == RULE_MODEL_CLASS_EXISTS
        assert issues[0].severity == EnumSeverity.ERROR
        assert "ModelFooInput" in issues[0].message

    def test_all_model_classes_present_passes(self, tmp_path: Path) -> None:
        """Contract whose declared model classes all exist in the handler passes."""
        from omnibase_core.validation.validator_contract_linter import (
            validate_model_class_existence,
        )

        contract_data: dict[str, object] = {
            "name": "node_foo",
            "contract_version": "1.0.0",
            "node_type": "compute",
            "input_model": {"name": "ModelFooInput", "module": "generated.models"},
            "output_model": {"name": "ModelFooOutput", "module": "generated.models"},
        }
        handler_source = (
            "from pydantic import BaseModel\n"
            "\n"
            "class ModelFooInput(BaseModel):\n"
            "    value: int\n"
            "\n"
            "class ModelFooOutput(BaseModel):\n"
            "    result: int\n"
            "\n"
            "def handle(input_data: dict) -> dict:\n"
            "    return {'result': input_data.get('value', 0)}\n"
        )

        issues = validate_model_class_existence(
            contract_data,
            handler_source,
            path=tmp_path / "contract.yaml",
            severity=EnumSeverity.ERROR,
        )

        assert issues == []

    def test_bare_flat_string_model_field_is_checked(self, tmp_path: Path) -> None:
        """A bare (un-dotted) flat-string model name is the inline form: checked."""
        from omnibase_core.validation.validator_contract_linter import (
            RULE_MODEL_CLASS_EXISTS,
            validate_model_class_existence,
        )

        contract_data: dict[str, object] = {
            "name": "node_foo",
            "contract_version": "1.0.0",
            "node_type": "compute",
            "input_model": "ModelFlatInput",
            "output_model": "ModelFlatOutput",
        }
        handler_source = (
            "from pydantic import BaseModel\n"
            "\n"
            "class ModelFlatInput(BaseModel):\n"
            "    value: int\n"
            "\n"
            "def handle(input_data: dict) -> dict:\n"
            "    return {'result': 0}\n"
        )

        issues = validate_model_class_existence(
            contract_data,
            handler_source,
            path=tmp_path / "contract.yaml",
            severity=EnumSeverity.ERROR,
        )

        assert len(issues) == 1
        assert issues[0].code == RULE_MODEL_CLASS_EXISTS
        assert "ModelFlatOutput" in issues[0].message

    def test_dotted_importable_path_is_out_of_scope(self, tmp_path: Path) -> None:
        """A fully-qualified dotted model path is a hand-authored reference whose
        model lives in its own module: out of scope, never flagged here."""
        from omnibase_core.validation.validator_contract_linter import (
            validate_model_class_existence,
        )

        contract_data: dict[str, object] = {
            "name": "node_foo",
            "contract_version": "1.0.0",
            "node_type": "compute",
            "input_model": "omnibase_core.models.nodes.foo.ModelFooInput",
            "output_model": "omnibase_core.models.nodes.foo.ModelFooOutput",
        }
        # Handler does not define/import the model names at all — still no issue,
        # because dotted references are resolved by import, not by handler scan.
        handler_source = (
            "def handle(input_data: dict) -> dict:\n    return {'result': 0}\n"
        )

        issues = validate_model_class_existence(
            contract_data,
            handler_source,
            path=tmp_path / "contract.yaml",
            severity=EnumSeverity.ERROR,
        )

        assert issues == []

    def test_nested_model_imported_into_handler_passes(self, tmp_path: Path) -> None:
        """Inline model declared with the generated sentinel, satisfied by an
        import binding in the handler (not only a ClassDef)."""
        from omnibase_core.validation.validator_contract_linter import (
            validate_model_class_existence,
        )

        contract_data: dict[str, object] = {
            "name": "node_foo",
            "contract_version": "1.0.0",
            "node_type": "compute",
            "input_model": {"name": "ModelFooInput", "module": "generated.models"},
        }
        handler_source = (
            "from generated.models import ModelFooInput\n"
            "\n"
            "def handle(input_data: dict) -> dict:\n"
            "    return {'result': 0}\n"
        )

        issues = validate_model_class_existence(
            contract_data,
            handler_source,
            path=tmp_path / "contract.yaml",
            severity=EnumSeverity.ERROR,
        )

        assert issues == []

    def test_unparseable_handler_yields_no_class_existence_issue(
        self, tmp_path: Path
    ) -> None:
        """A handler that cannot be AST-parsed yields no model-class issue.

        Syntax errors are owned by the separate syntax check; the model-class
        check emits nothing rather than masking a syntax error.
        """
        from omnibase_core.validation.validator_contract_linter import (
            validate_model_class_existence,
        )

        contract_data: dict[str, object] = {
            "name": "node_foo",
            "contract_version": "1.0.0",
            "node_type": "compute",
            "input_model": {"name": "ModelFooInput", "module": "generated.models"},
        }
        handler_source = "def handle(:\n    pass\n"  # invalid syntax

        issues = validate_model_class_existence(
            contract_data,
            handler_source,
            path=tmp_path / "contract.yaml",
            severity=EnumSeverity.ERROR,
        )

        assert issues == []


@pytest.mark.unit
class TestModelClassExistenceWiredInLinter:
    """The check is wired into the per-file linter loop via co-located handler."""

    def test_contract_with_undefined_model_class_fails_linter(
        self, tmp_path: Path
    ) -> None:
        """A generated node dir (contract.yaml + handler.py) with a mismatched
        model class name is rejected by ValidatorContractLinter.validate()."""
        from omnibase_core.validation.validator_contract_linter import (
            RULE_MODEL_CLASS_EXISTS,
        )

        node_dir = tmp_path / "node_foo"
        node_dir.mkdir()
        (node_dir / "contract.yaml").write_text(
            "name: node_foo\n"
            'contract_version: "1.0.0"\n'
            "node_type: compute\n"
            "description: A foo node\n"
            "input_model:\n"
            "  name: ModelFooInput\n"
            "  module: generated.models\n"
            "output_model:\n"
            "  name: ModelFooOutput\n"
            "  module: generated.models\n",
            encoding="utf-8",
        )
        (node_dir / "handler.py").write_text(
            "from pydantic import BaseModel\n"
            "\n"
            "class ModelWrongInput(BaseModel):\n"
            "    value: int\n"
            "\n"
            "class ModelFooOutput(BaseModel):\n"
            "    result: int\n"
            "\n"
            "def handle(input_data: dict) -> dict:\n"
            "    return {'result': 0}\n",
            encoding="utf-8",
        )

        contract = create_test_contract(target_patterns=["**/contract.yaml"])
        validator = ValidatorContractLinter(contract=contract)
        result = validator.validate(node_dir / "contract.yaml")

        assert not result.is_valid
        codes = {issue.code for issue in result.issues}
        assert RULE_MODEL_CLASS_EXISTS in codes
        assert any(
            "ModelFooInput" in issue.message
            for issue in result.issues
            if issue.code == RULE_MODEL_CLASS_EXISTS
        )

    def test_contract_with_matching_model_classes_passes_linter(
        self, tmp_path: Path
    ) -> None:
        """A generated node dir whose handler defines all declared model classes
        produces no model-class-existence issue."""
        from omnibase_core.validation.validator_contract_linter import (
            RULE_MODEL_CLASS_EXISTS,
        )

        node_dir = tmp_path / "node_foo"
        node_dir.mkdir()
        (node_dir / "contract.yaml").write_text(
            "name: node_foo\n"
            'contract_version: "1.0.0"\n'
            "node_type: compute\n"
            "description: A foo node\n"
            "input_model:\n"
            "  name: ModelFooInput\n"
            "  module: generated.models\n"
            "output_model:\n"
            "  name: ModelFooOutput\n"
            "  module: generated.models\n",
            encoding="utf-8",
        )
        (node_dir / "handler.py").write_text(
            "from pydantic import BaseModel\n"
            "\n"
            "class ModelFooInput(BaseModel):\n"
            "    value: int\n"
            "\n"
            "class ModelFooOutput(BaseModel):\n"
            "    result: int\n"
            "\n"
            "def handle(input_data: dict) -> dict:\n"
            "    return {'result': 0}\n",
            encoding="utf-8",
        )

        contract = create_test_contract(target_patterns=["**/contract.yaml"])
        validator = ValidatorContractLinter(contract=contract)
        result = validator.validate(node_dir / "contract.yaml")

        codes = {issue.code for issue in result.issues}
        assert RULE_MODEL_CLASS_EXISTS not in codes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
