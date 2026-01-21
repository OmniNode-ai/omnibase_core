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

    def test_both_version_and_contract_version_passes(self, tmp_path: Path) -> None:
        """Test that YAML with both 'version:' and 'contract_version:' passes.

        When a YAML contract has both fields (perhaps during migration),
        the presence of 'contract_version' means the guardrail should not
        raise an error. The 'contract_version' field takes precedence.
        """
        contract = create_test_contract()
        validator = ValidatorContractLinter(contract=contract)

        # YAML data with both fields (migration state)
        data: dict[str, object] = {
            "name": "TestContract",
            "version": "1.0.0",  # Deprecated but contract_version present
            "contract_version": "1.0.0",  # New field takes precedence
            "node_type": "compute_generic",
        }
        test_path = tmp_path / "test_contract.yaml"

        issues = validator._validate_deprecated_field_names(data, test_path, contract)

        assert len(issues) == 0

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
