"""
Tests for ValidatorPydanticConventions - AST-based validator for Pydantic model conventions.

This module provides comprehensive tests for the ValidatorPydanticConventions class,
covering:
- Detection of models without model_config (Rule 1: missing-config)
- Detection of empty ConfigDict() declarations (Rule 2: empty-config)
- Detection of frozen=True without from_attributes=True (Rule 3: frozen-without-from-attributes)
- Detection of contract models missing extra= policy (Rule 4: contract-missing-extra)
- Detection of unnecessary Field(default=None) patterns (Rule 5: unnecessary-field-default-none)
- Suppression comment handling
- Known base model exemptions
- Edge cases and error handling

Ticket: OMN-1314
"""

import textwrap
from pathlib import Path

import pytest

from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_pydantic_conventions import (
    KNOWN_BASE_MODELS,
    RULE_CONTRACT_MISSING_EXTRA,
    RULE_EMPTY_CONFIG,
    RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES,
    RULE_MISSING_CONFIG,
    RULE_UNNECESSARY_FIELD_DEFAULT_NONE,
    ValidatorPydanticConventions,
)

# =============================================================================
# Test Helpers
# =============================================================================


def create_test_contract(
    suppression_comments: list[str] | None = None,
    severity_default: EnumValidationSeverity = EnumValidationSeverity.ERROR,
    rules: list[ModelValidatorRule] | None = None,
) -> ModelValidatorSubcontract:
    """Create a test contract for ValidatorPydanticConventions.

    Note: Rules must be explicitly defined since missing rules default to disabled
    per validator_base.py:615 alignment (OMN-1291 PR #360).
    """
    default_rules = [
        ModelValidatorRule(
            rule_id=RULE_MISSING_CONFIG,
            description="Detects models without model_config",
            severity=EnumValidationSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_EMPTY_CONFIG,
            description="Detects empty ConfigDict()",
            severity=EnumValidationSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES,
            description="Detects frozen=True without from_attributes=True",
            severity=EnumValidationSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_CONTRACT_MISSING_EXTRA,
            description="Detects contract models missing extra= policy",
            severity=EnumValidationSeverity.WARNING,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_UNNECESSARY_FIELD_DEFAULT_NONE,
            description="Detects unnecessary Field(default=None)",
            severity=EnumValidationSeverity.WARNING,
            enabled=True,
        ),
    ]
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="pydantic_conventions",
        validator_name="Pydantic Conventions Validator",
        validator_description="Test validator for Pydantic conventions",
        target_patterns=["**/*.py"],
        exclude_patterns=[],
        suppression_comments=suppression_comments
        or ["# noqa:", "# onex: ignore-pydantic-conventions", "# pydantic-ok:"],
        fail_on_error=True,
        fail_on_warning=False,
        severity_default=severity_default,
        rules=rules if rules is not None else default_rules,
    )


def write_python_file(tmp_path: Path, content: str, filename: str = "test.py") -> Path:
    """Write Python content to a temporary file."""
    file_path = tmp_path / filename
    file_path.write_text(textwrap.dedent(content).strip())
    return file_path


def create_contracts_structure(tmp_path: Path) -> Path:
    """Create a mock models/contracts directory structure."""
    contracts_dir = tmp_path / "src" / "models" / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    return contracts_dir


# =============================================================================
# ValidatorPydanticConventions Initialization Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsInit:
    """Tests for ValidatorPydanticConventions initialization."""

    def test_validator_id(self) -> None:
        """Test that validator_id is set correctly."""
        assert ValidatorPydanticConventions.validator_id == "pydantic_conventions"

    def test_init_with_contract(self) -> None:
        """Test initialization with a pre-loaded contract."""
        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)

        assert validator.contract is contract

    def test_init_without_contract(self) -> None:
        """Test initialization without a contract (lazy loading behavior).

        When no contract is provided, the validator should still be created
        successfully and will load the contract lazily when needed.
        """
        validator = ValidatorPydanticConventions()
        # Validator should be created successfully without a contract
        # The contract will be loaded lazily when first accessed via the property
        assert validator is not None
        assert validator.validator_id == "pydantic_conventions"


# =============================================================================
# Rule 1: missing-config Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsMissingConfig:
    """Tests for Rule 1: missing-config detection."""

    def test_model_without_config_flagged(self, tmp_path: Path) -> None:
        """Test that models without model_config are flagged."""
        source = """
        from pydantic import BaseModel

        class MyModel(BaseModel):
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 1
        assert "MyModel" in missing_config_issues[0].message
        assert "no model_config" in missing_config_issues[0].message

    def test_model_with_config_not_flagged(self, tmp_path: Path) -> None:
        """Test that models with model_config are not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 0

    def test_model_inheriting_known_base_not_flagged(self, tmp_path: Path) -> None:
        """Test that models inheriting from known base models are not flagged."""
        # ModelOnexEvent is in KNOWN_BASE_MODELS
        source = """
        from pydantic import BaseModel, ConfigDict

        class ModelOnexEvent(BaseModel):
            model_config = ConfigDict(extra="forbid")

        class MyEvent(ModelOnexEvent):
            data: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        # MyEvent should not be flagged because it inherits from ModelOnexEvent
        # ModelOnexEvent itself WILL be flagged since it inherits from BaseModel
        # and IS in KNOWN_BASE_MODELS (but validator skips subclasses, not the base itself)
        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        # Only check that MyEvent is not flagged
        flagged_names = [i.message for i in missing_config_issues]
        assert not any("MyEvent" in name for name in flagged_names)

    def test_legacy_config_class_without_model_config_flagged(
        self, tmp_path: Path
    ) -> None:
        """Test that legacy 'class Config:' without model_config is flagged as missing.

        When a model has only the legacy 'class Config:' style (Pydantic v1) and no
        modern 'model_config = ConfigDict(...)', the validator flags it as missing
        model_config. This is because the legacy Config class is not recognized as
        a modern model_config declaration.
        """
        source = """
        from pydantic import BaseModel

        class MyModel(BaseModel):
            class Config:
                extra = "forbid"

            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        # Model with legacy Config class (no model_config) is flagged as missing
        assert len(missing_config_issues) == 1
        assert "no model_config" in missing_config_issues[0].message

    def test_legacy_config_class_with_model_config_flagged(
        self, tmp_path: Path
    ) -> None:
        """Test that having both model_config AND legacy Config class is flagged.

        When a model has both modern 'model_config = ConfigDict(...)' AND a legacy
        'class Config:' inner class, the validator flags the legacy class as it
        should be removed.
        """
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")

            class Config:
                # This legacy class shouldn't exist alongside model_config
                validate_assignment = True

            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        # When model_config exists but legacy Config class is also present
        assert len(missing_config_issues) == 1
        assert "legacy" in missing_config_issues[0].message.lower()
        assert "class Config:" in missing_config_issues[0].message

    def test_non_pydantic_class_not_flagged(self, tmp_path: Path) -> None:
        """Test that non-Pydantic classes are not flagged."""
        source = """
        class RegularClass:
            def __init__(self):
                self.name = "test"
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 0

    def test_annotated_model_config_not_flagged(self, tmp_path: Path) -> None:
        """Test that annotated model_config assignments are detected."""
        source = """
        from pydantic import BaseModel, ConfigDict
        from typing import ClassVar

        class MyModel(BaseModel):
            model_config: ClassVar = ConfigDict(extra="forbid")
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 0


# =============================================================================
# Rule 2: empty-config Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsEmptyConfig:
    """Tests for Rule 2: empty-config detection."""

    def test_empty_config_dict_flagged(self, tmp_path: Path) -> None:
        """Test that empty ConfigDict() is flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict()
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        empty_config_issues = [i for i in result.issues if i.code == RULE_EMPTY_CONFIG]
        assert len(empty_config_issues) == 1
        assert "empty ConfigDict" in empty_config_issues[0].message

    def test_config_dict_with_args_not_flagged(self, tmp_path: Path) -> None:
        """Test that ConfigDict with arguments is not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        empty_config_issues = [i for i in result.issues if i.code == RULE_EMPTY_CONFIG]
        assert len(empty_config_issues) == 0

    def test_multiline_empty_config_dict_flagged(self, tmp_path: Path) -> None:
        """Test that multi-line empty ConfigDict is flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(
            )
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        empty_config_issues = [i for i in result.issues if i.code == RULE_EMPTY_CONFIG]
        assert len(empty_config_issues) == 1


# =============================================================================
# Rule 3: frozen-without-from-attributes Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsFrozenWithoutFromAttributes:
    """Tests for Rule 3: frozen-without-from-attributes detection."""

    def test_frozen_without_from_attributes_flagged(self, tmp_path: Path) -> None:
        """Test that frozen=True without from_attributes=True is flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(frozen=True)
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        frozen_issues = [
            i for i in result.issues if i.code == RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES
        ]
        assert len(frozen_issues) == 1
        assert "frozen=True" in frozen_issues[0].message
        assert "from_attributes" in frozen_issues[0].message

    def test_frozen_with_from_attributes_not_flagged(self, tmp_path: Path) -> None:
        """Test that frozen=True with from_attributes=True is not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(frozen=True, from_attributes=True)
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        frozen_issues = [
            i for i in result.issues if i.code == RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES
        ]
        assert len(frozen_issues) == 0

    def test_no_frozen_not_flagged(self, tmp_path: Path) -> None:
        """Test that models without frozen are not flagged for this rule."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        frozen_issues = [
            i for i in result.issues if i.code == RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES
        ]
        assert len(frozen_issues) == 0

    def test_frozen_false_not_flagged(self, tmp_path: Path) -> None:
        """Test that frozen=False is not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(frozen=False, extra="forbid")
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        frozen_issues = [
            i for i in result.issues if i.code == RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES
        ]
        assert len(frozen_issues) == 0

    def test_frozen_with_multiple_options_not_flagged(self, tmp_path: Path) -> None:
        """Test frozen with from_attributes and other options is not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(
                frozen=True,
                extra="forbid",
                from_attributes=True,
                validate_assignment=True
            )
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        frozen_issues = [
            i for i in result.issues if i.code == RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES
        ]
        assert len(frozen_issues) == 0


# =============================================================================
# Rule 4: contract-missing-extra Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsContractMissingExtra:
    """Tests for Rule 4: contract-missing-extra detection."""

    def test_contract_model_without_extra_flagged(self, tmp_path: Path) -> None:
        """Test that contract models without extra= are flagged."""
        contracts_dir = create_contracts_structure(tmp_path)
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyContract(BaseModel):
            model_config = ConfigDict(frozen=True, from_attributes=True)
            name: str
        """
        file_path = contracts_dir / "model_contract.py"
        file_path.write_text(textwrap.dedent(source).strip())

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        contract_issues = [
            i for i in result.issues if i.code == RULE_CONTRACT_MISSING_EXTRA
        ]
        assert len(contract_issues) == 1
        assert "without explicit extra=" in contract_issues[0].message

    def test_contract_model_with_extra_not_flagged(self, tmp_path: Path) -> None:
        """Test that contract models with extra= are not flagged."""
        contracts_dir = create_contracts_structure(tmp_path)
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyContract(BaseModel):
            model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")
            name: str
        """
        file_path = contracts_dir / "model_contract.py"
        file_path.write_text(textwrap.dedent(source).strip())

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        contract_issues = [
            i for i in result.issues if i.code == RULE_CONTRACT_MISSING_EXTRA
        ]
        assert len(contract_issues) == 0

    def test_non_contract_model_without_extra_not_flagged(self, tmp_path: Path) -> None:
        """Test that non-contract models without extra= are not flagged for this rule."""
        # Regular directory (not contracts/)
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(frozen=True, from_attributes=True)
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        contract_issues = [
            i for i in result.issues if i.code == RULE_CONTRACT_MISSING_EXTRA
        ]
        assert len(contract_issues) == 0

    def test_alternate_contracts_path_detected(self, tmp_path: Path) -> None:
        """Test that /contracts/ path (without models/) is detected."""
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir(parents=True, exist_ok=True)
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyContract(BaseModel):
            model_config = ConfigDict(frozen=True, from_attributes=True)
            name: str
        """
        file_path = contracts_dir / "model_contract.py"
        file_path.write_text(textwrap.dedent(source).strip())

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        contract_issues = [
            i for i in result.issues if i.code == RULE_CONTRACT_MISSING_EXTRA
        ]
        assert len(contract_issues) == 1


# =============================================================================
# Rule 5: unnecessary-field-default-none Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsUnnecessaryFieldDefaultNone:
    """Tests for Rule 5: unnecessary-field-default-none detection."""

    def test_field_default_none_flagged(self, tmp_path: Path) -> None:
        """Test that Field(default=None) with no other kwargs is flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict, Field

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str | None = Field(default=None)
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        field_issues = [
            i for i in result.issues if i.code == RULE_UNNECESSARY_FIELD_DEFAULT_NONE
        ]
        assert len(field_issues) == 1
        assert "name" in field_issues[0].message
        assert "Field(default=None)" in field_issues[0].message

    def test_field_none_positional_flagged(self, tmp_path: Path) -> None:
        """Test that Field(None) is flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict, Field

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str | None = Field(None)
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        field_issues = [
            i for i in result.issues if i.code == RULE_UNNECESSARY_FIELD_DEFAULT_NONE
        ]
        assert len(field_issues) == 1

    def test_field_default_none_with_description_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """Test that Field(default=None, description=...) is not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict, Field

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str | None = Field(default=None, description="The name")
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        field_issues = [
            i for i in result.issues if i.code == RULE_UNNECESSARY_FIELD_DEFAULT_NONE
        ]
        assert len(field_issues) == 0

    def test_simple_none_default_not_flagged(self, tmp_path: Path) -> None:
        """Test that field: str | None = None is not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str | None = None
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        field_issues = [
            i for i in result.issues if i.code == RULE_UNNECESSARY_FIELD_DEFAULT_NONE
        ]
        assert len(field_issues) == 0

    def test_field_default_zero_not_flagged(self, tmp_path: Path) -> None:
        """Test that Field(default=0) is not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict, Field

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            count: int = Field(default=0)
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        field_issues = [
            i for i in result.issues if i.code == RULE_UNNECESSARY_FIELD_DEFAULT_NONE
        ]
        assert len(field_issues) == 0

    def test_field_with_other_kwargs_not_flagged(self, tmp_path: Path) -> None:
        """Test that Field(default=None, ge=0) is not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict, Field

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            value: int | None = Field(default=None, ge=0)
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        field_issues = [
            i for i in result.issues if i.code == RULE_UNNECESSARY_FIELD_DEFAULT_NONE
        ]
        assert len(field_issues) == 0

    def test_multiple_fields_with_issues(self, tmp_path: Path) -> None:
        """Test that multiple fields with issues are all flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict, Field

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            field1: str | None = Field(default=None)
            field2: str | None = Field(None)
            field3: str | None = Field(default=None, description="ok")  # not flagged
            field4: str | None = None  # not flagged
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        field_issues = [
            i for i in result.issues if i.code == RULE_UNNECESSARY_FIELD_DEFAULT_NONE
        ]
        assert len(field_issues) == 2


# =============================================================================
# Suppression Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsSuppression:
    """Tests for suppression comment handling."""

    def test_onex_ignore_suppresses_issue(self, tmp_path: Path) -> None:
        """Test that # onex: ignore-pydantic-conventions suppresses issues."""
        source = """
        from pydantic import BaseModel

        class MyModel(BaseModel):  # onex: ignore-pydantic-conventions
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 0

    def test_pydantic_ok_suppresses_issue(self, tmp_path: Path) -> None:
        """Test that # pydantic-ok: suppresses issues."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict()  # pydantic-ok: intentionally empty
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        empty_config_issues = [i for i in result.issues if i.code == RULE_EMPTY_CONFIG]
        assert len(empty_config_issues) == 0

    def test_noqa_suppresses_issue(self, tmp_path: Path) -> None:
        """Test that # noqa: suppresses issues."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(frozen=True)  # noqa: frozen without from_attributes
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        frozen_issues = [
            i for i in result.issues if i.code == RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES
        ]
        assert len(frozen_issues) == 0

    def test_no_suppression_issue_reported(self, tmp_path: Path) -> None:
        """Test that issues without suppression are reported."""
        source = """
        from pydantic import BaseModel

        class MyModel(BaseModel):
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 1


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsIntegration:
    """Tests for integration functionality."""

    def test_validate_returns_model_validation_result(self, tmp_path: Path) -> None:
        """Test that validate() returns ModelValidationResult."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate(file_path)

        from omnibase_core.models.common.model_validation_result import (
            ModelValidationResult,
        )

        assert isinstance(result, ModelValidationResult)

    def test_exit_code_success_for_clean_file(self, tmp_path: Path) -> None:
        """Test exit code 0 for clean file."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate(file_path)
        exit_code = validator.get_exit_code(result)

        assert exit_code == 0

    def test_exit_code_error_for_violations(self, tmp_path: Path) -> None:
        """Test exit code 1 for errors."""
        source = """
        from pydantic import BaseModel

        class MyModel(BaseModel):
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate(file_path)
        exit_code = validator.get_exit_code(result)

        assert exit_code == 1

    def test_exit_code_warning_for_warnings_only(self, tmp_path: Path) -> None:
        """Test exit code 2 for warnings only when fail_on_warning is True."""
        contracts_dir = create_contracts_structure(tmp_path)
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(frozen=True, from_attributes=True)
            name: str
        """
        file_path = contracts_dir / "model_contract.py"
        file_path.write_text(textwrap.dedent(source).strip())

        # Create contract with fail_on_warning=True and only warning rules enabled
        rules = [
            ModelValidatorRule(
                rule_id=RULE_MISSING_CONFIG,
                description="Detects models without model_config",
                severity=EnumValidationSeverity.ERROR,
                enabled=False,  # Disable error rules
            ),
            ModelValidatorRule(
                rule_id=RULE_EMPTY_CONFIG,
                description="Detects empty ConfigDict()",
                severity=EnumValidationSeverity.ERROR,
                enabled=False,  # Disable error rules
            ),
            ModelValidatorRule(
                rule_id=RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES,
                description="Detects frozen=True without from_attributes=True",
                severity=EnumValidationSeverity.ERROR,
                enabled=False,  # Disable error rules
            ),
            ModelValidatorRule(
                rule_id=RULE_CONTRACT_MISSING_EXTRA,
                description="Detects contract models missing extra= policy",
                severity=EnumValidationSeverity.WARNING,
                enabled=True,  # Enable warning rule
            ),
            ModelValidatorRule(
                rule_id=RULE_UNNECESSARY_FIELD_DEFAULT_NONE,
                description="Detects unnecessary Field(default=None)",
                severity=EnumValidationSeverity.WARNING,
                enabled=False,
            ),
        ]
        contract = ModelValidatorSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            validator_id="pydantic_conventions",
            validator_name="Pydantic Conventions Validator",
            validator_description="Test validator",
            target_patterns=["**/*.py"],
            exclude_patterns=[],
            suppression_comments=["# noqa:"],
            fail_on_error=True,
            fail_on_warning=True,  # Fail on warnings
            severity_default=EnumValidationSeverity.WARNING,
            rules=rules,
        )
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate(file_path)
        exit_code = validator.get_exit_code(result)

        assert exit_code == 2


# =============================================================================
# Edge Cases Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_nested_classes(self, tmp_path: Path) -> None:
        """Test that nested classes are analyzed."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class OuterModel(BaseModel):
            model_config = ConfigDict(extra="forbid")

            class InnerModel(BaseModel):
                value: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        # InnerModel should be flagged for missing config
        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 1
        assert "InnerModel" in missing_config_issues[0].message

    def test_handles_multiple_models_in_file(self, tmp_path: Path) -> None:
        """Test that multiple models in one file are all analyzed."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class Model1(BaseModel):
            name: str

        class Model2(BaseModel):
            value: int

        class Model3(BaseModel):
            model_config = ConfigDict(extra="forbid")
            data: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        # Model1 and Model2 should be flagged
        assert len(missing_config_issues) == 2

    def test_handles_empty_file(self, tmp_path: Path) -> None:
        """Test that empty files are handled."""
        file_path = write_python_file(tmp_path, "")

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        assert result.is_valid
        assert len(result.issues) == 0

    def test_handles_syntax_error_gracefully(self, tmp_path: Path) -> None:
        """Test that syntax errors are handled gracefully."""
        source = """
        from pydantic import BaseModel

        class MyModel(BaseModel
            # Missing closing paren
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        # Should not crash, return valid result (no issues can be detected)
        assert result.is_valid

    def test_handles_non_python_file(self, tmp_path: Path) -> None:
        """Test handling of non-Python files."""
        text_file = tmp_path / "readme.txt"
        text_file.write_text("Not a Python file")

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(text_file)

        # Should handle gracefully
        assert result.is_valid

    def test_handles_class_without_bases(self, tmp_path: Path) -> None:
        """Test that classes without bases are not flagged."""
        source = """
        class PlainClass:
            def __init__(self):
                pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        assert result.is_valid
        assert len(result.issues) == 0

    def test_handles_qualified_base_model_import(self, tmp_path: Path) -> None:
        """Test that pydantic.BaseModel is detected."""
        source = """
        import pydantic

        class MyModel(pydantic.BaseModel):
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        # BaseModel attribute should be detected
        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 1


# =============================================================================
# Rule Enablement Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsRuleEnablement:
    """Tests for selective rule enablement."""

    def test_disable_missing_config_rule(self, tmp_path: Path) -> None:
        """Test that missing-config rule can be disabled."""
        source = """
        from pydantic import BaseModel

        class MyModel(BaseModel):
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_MISSING_CONFIG,
                description="Missing config",
                enabled=False,
            )
        ]
        contract = create_test_contract(rules=rules)
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 0

    def test_disable_empty_config_rule(self, tmp_path: Path) -> None:
        """Test that empty-config rule can be disabled."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict()
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_MISSING_CONFIG,
                description="Missing config",
                enabled=True,
            ),
            ModelValidatorRule(
                rule_id=RULE_EMPTY_CONFIG,
                description="Empty config",
                enabled=False,
            ),
        ]
        contract = create_test_contract(rules=rules)
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        empty_config_issues = [i for i in result.issues if i.code == RULE_EMPTY_CONFIG]
        assert len(empty_config_issues) == 0

    def test_custom_severity_override(self, tmp_path: Path) -> None:
        """Test that custom severity can be set per rule."""
        source = """
        from pydantic import BaseModel

        class MyModel(BaseModel):
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_MISSING_CONFIG,
                description="Missing config",
                enabled=True,
                severity=EnumValidationSeverity.WARNING,
            )
        ]
        contract = create_test_contract(rules=rules)
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 1
        assert missing_config_issues[0].severity == EnumValidationSeverity.WARNING


# =============================================================================
# Validate Directory Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsDirectory:
    """Tests for directory validation."""

    def test_validates_multiple_files(self, tmp_path: Path) -> None:
        """Test validation of multiple files in a directory."""
        # Create files with different issues
        write_python_file(
            tmp_path,
            "from pydantic import BaseModel\nclass Bad1(BaseModel):\n    x: str",
            "file1.py",
        )
        write_python_file(
            tmp_path,
            "from pydantic import BaseModel, ConfigDict\n"
            "class Bad2(BaseModel):\n"
            "    model_config = ConfigDict()\n"
            "    x: str",
            "file2.py",
        )
        write_python_file(
            tmp_path,
            "from pydantic import BaseModel, ConfigDict\n"
            "class Good(BaseModel):\n"
            '    model_config = ConfigDict(extra="forbid")\n'
            "    x: str",
            "file3.py",
        )

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate(tmp_path)

        # Should find issues in file1 and file2
        assert len(result.issues) >= 2


# =============================================================================
# Known Base Models Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsKnownBaseModels:
    """Tests for known base model exemptions."""

    def test_known_base_models_frozenset(self) -> None:
        """Test that KNOWN_BASE_MODELS is a frozenset."""
        assert isinstance(KNOWN_BASE_MODELS, frozenset)

    def test_known_base_models_contains_expected(self) -> None:
        """Test that KNOWN_BASE_MODELS contains expected models."""
        expected = {
            "ModelIntentPayloadBase",
            "ModelActionPayloadBase",
            "ModelOnexEvent",
            "ModelContractBase",
        }
        assert expected.issubset(KNOWN_BASE_MODELS)

    def test_subclass_of_known_base_not_flagged(self, tmp_path: Path) -> None:
        """Test that subclasses of known bases are not flagged."""
        source = """
        from pydantic import BaseModel, ConfigDict

        # Simulating a known base model
        class ModelContractBase(BaseModel):
            model_config = ConfigDict(extra="forbid")

        # This should NOT be flagged
        class MyContract(ModelContractBase):
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        # Only ModelContractBase should potentially be flagged (it inherits from BaseModel)
        # but MyContract should NOT be flagged (inherits from known base)
        flagged_names = [i.message for i in missing_config_issues]
        assert not any("MyContract" in name for name in flagged_names)


# =============================================================================
# Import Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsImports:
    """Tests for module imports."""

    def test_import_validator(self) -> None:
        """Test that ValidatorPydanticConventions can be imported."""
        from omnibase_core.validation.validator_pydantic_conventions import (
            ValidatorPydanticConventions,
        )

        assert ValidatorPydanticConventions is not None

    def test_import_rule_constants(self) -> None:
        """Test that rule constants can be imported."""
        from omnibase_core.validation.validator_pydantic_conventions import (
            RULE_CONTRACT_MISSING_EXTRA,
            RULE_EMPTY_CONFIG,
            RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES,
            RULE_MISSING_CONFIG,
            RULE_UNNECESSARY_FIELD_DEFAULT_NONE,
        )

        assert RULE_MISSING_CONFIG == "missing-config"
        assert RULE_EMPTY_CONFIG == "empty-config"
        assert RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES == "frozen-without-from-attributes"
        assert RULE_CONTRACT_MISSING_EXTRA == "contract-missing-extra"
        assert RULE_UNNECESSARY_FIELD_DEFAULT_NONE == "unnecessary-field-default-none"

    def test_import_known_base_models(self) -> None:
        """Test that KNOWN_BASE_MODELS can be imported."""
        from omnibase_core.validation.validator_pydantic_conventions import (
            KNOWN_BASE_MODELS,
        )

        assert KNOWN_BASE_MODELS is not None
        assert isinstance(KNOWN_BASE_MODELS, frozenset)


# =============================================================================
# Suggestion Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorPydanticConventionsSuggestions:
    """Tests for suggestion generation."""

    def test_missing_config_has_suggestion(self, tmp_path: Path) -> None:
        """Test that missing-config issues have suggestions."""
        source = """
        from pydantic import BaseModel

        class MyModel(BaseModel):
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        missing_config_issues = [
            i for i in result.issues if i.code == RULE_MISSING_CONFIG
        ]
        assert len(missing_config_issues) == 1
        assert missing_config_issues[0].suggestion is not None
        assert "model_config" in missing_config_issues[0].suggestion

    def test_frozen_without_from_attributes_has_suggestion(
        self, tmp_path: Path
    ) -> None:
        """Test that frozen-without-from-attributes issues have suggestions."""
        source = """
        from pydantic import BaseModel, ConfigDict

        class MyModel(BaseModel):
            model_config = ConfigDict(frozen=True)
            name: str
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        frozen_issues = [
            i for i in result.issues if i.code == RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES
        ]
        assert len(frozen_issues) == 1
        assert frozen_issues[0].suggestion is not None
        assert "from_attributes=True" in frozen_issues[0].suggestion

    def test_unnecessary_field_has_suggestion(self, tmp_path: Path) -> None:
        """Test that unnecessary-field-default-none issues have suggestions."""
        source = """
        from pydantic import BaseModel, ConfigDict, Field

        class MyModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str | None = Field(default=None)
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorPydanticConventions(contract=contract)
        result = validator.validate_file(file_path)

        field_issues = [
            i for i in result.issues if i.code == RULE_UNNECESSARY_FIELD_DEFAULT_NONE
        ]
        assert len(field_issues) == 1
        assert field_issues[0].suggestion is not None
        assert "name" in field_issues[0].suggestion
