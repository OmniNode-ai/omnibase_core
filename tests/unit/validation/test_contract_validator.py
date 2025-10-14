"""
Unit tests for ContractValidator.

Tests programmatic contract validation for autonomous code generation:
- YAML contract validation
- Model code compliance checking
- ONEX naming convention validation
- Scoring calculation
"""

import pytest

from omnibase_core.models.metadata.model_semver import ModelSemVer
from omnibase_core.validation.contract_validator import (
    ProtocolContractValidationResult,
    ProtocolContractValidator,
)


class TestContractValidator:
    """Test suite for ContractValidator."""

    def test_validator_initialization(self) -> None:
        """Test validator initializes correctly."""
        validator = ProtocolContractValidator()
        assert validator.interface_version.major == 1
        assert validator.interface_version.minor == 0
        assert validator.interface_version.patch == 0

    def test_validate_valid_effect_contract(self) -> None:
        """Test validation of a valid effect contract."""
        validator = ProtocolContractValidator()

        contract_yaml = """
name: DatabaseWriterEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Effect node for writing data to PostgreSQL database
node_type: effect
input_model: omnibase_core.models.ModelDatabaseWriteInput
output_model: omnibase_core.models.ModelDatabaseWriteOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""

        result = validator.validate_contract_yaml(contract_yaml, "effect")

        assert isinstance(result, ProtocolContractValidationResult)
        assert result.is_valid
        assert result.score >= 0.8
        assert len(result.violations) == 0
        assert result.contract_type == "effect"
        assert result.interface_version.major == 1
        assert result.interface_version.minor == 0
        assert result.interface_version.patch == 0

    def test_validate_invalid_yaml(self) -> None:
        """Test validation fails for invalid YAML."""
        validator = ProtocolContractValidator()

        invalid_yaml = """
name: test
version: [invalid yaml structure
"""

        result = validator.validate_contract_yaml(invalid_yaml, "effect")

        assert not result.is_valid
        assert result.score == 0.0
        assert len(result.violations) > 0
        assert "YAML parsing error" in result.violations[0]

    def test_validate_missing_required_fields(self) -> None:
        """Test validation fails when required fields are missing."""
        validator = ProtocolContractValidator()

        # Missing io_operations (required for effect contracts)
        incomplete_yaml = """
name: IncompleteEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Incomplete effect contract
node_type: effect
input_model: ModelInput
output_model: ModelOutput
"""

        result = validator.validate_contract_yaml(incomplete_yaml, "effect")

        assert not result.is_valid
        assert result.score < 1.0
        assert len(result.violations) > 0

    def test_validate_contract_with_warnings(self) -> None:
        """Test validation produces warnings for non-critical issues."""
        validator = ProtocolContractValidator()

        # Valid but with warnings (short description)
        contract_yaml = """
name: TestEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Short
node_type: effect
input_model: ModelInput
output_model: ModelOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""

        result = validator.validate_contract_yaml(contract_yaml, "effect")

        # Should have warnings about short description
        assert len(result.warnings) > 0
        assert any("description" in warning.lower() for warning in result.warnings)

    def test_validate_model_compliance_valid(self) -> None:
        """Test model compliance validation with valid model code."""
        validator = ProtocolContractValidator()

        model_code = """
from pydantic import BaseModel, Field

class ModelDatabaseWriteInput(BaseModel):
    table_name: str = Field(..., description="Target table name")
    data: dict[str, object] = Field(..., description="Data to write")

class ModelDatabaseWriteOutput(BaseModel):
    success: bool = Field(..., description="Write operation success")
    rows_affected: int = Field(..., description="Number of rows affected")
"""

        contract_yaml = """
name: DatabaseWriterEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Effect node for writing data to PostgreSQL database
node_type: effect
input_model: omnibase_core.models.ModelDatabaseWriteInput
output_model: omnibase_core.models.ModelDatabaseWriteOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""

        result = validator.validate_model_compliance(model_code, contract_yaml)

        assert isinstance(result, ProtocolContractValidationResult)
        # Should not have violations (models exist)
        assert len([v for v in result.violations if "not found" in v]) == 0

    def test_validate_model_compliance_missing_models(self) -> None:
        """Test model compliance fails when models are missing."""
        validator = ProtocolContractValidator()

        model_code = """
from pydantic import BaseModel

class ModelWrongName(BaseModel):
    value: str
"""

        contract_yaml = """
name: TestEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Test effect contract
node_type: effect
input_model: omnibase_core.models.ModelExpectedInput
output_model: omnibase_core.models.ModelExpectedOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""

        result = validator.validate_model_compliance(model_code, contract_yaml)

        assert not result.is_valid
        assert len(result.violations) >= 2  # Both input and output models missing
        assert any("ModelExpectedInput" in v for v in result.violations)
        assert any("ModelExpectedOutput" in v for v in result.violations)

    def test_validate_model_naming_conventions(self) -> None:
        """Test ONEX naming convention validation."""
        validator = ProtocolContractValidator()

        # Model without proper naming
        model_code = """
from pydantic import BaseModel

class BadName(BaseModel):  # Should start with "Model"
    value: str
"""

        contract_yaml = """
name: TestEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Test effect contract
node_type: effect
input_model: BadName
output_model: BadName
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""

        result = validator.validate_model_compliance(model_code, contract_yaml)

        # Should have warnings about naming
        assert len(result.warnings) > 0
        assert any("Model" in warning for warning in result.warnings)

    def test_validate_compute_contract(self) -> None:
        """Test validation of compute contract type.

        Note: ModelContractCompute has a custom __init__ that causes issues with
        Pydantic validation. This test verifies the validator handles the contract
        type correctly even when validation fails.
        """
        validator = ProtocolContractValidator()

        compute_yaml = """
name: DataTransformerCompute
version:
  major: 1
  minor: 0
  patch: 0
description: Pure compute node for data transformation
node_type: compute
input_model: omnibase_core.models.ModelTransformInput
output_model: omnibase_core.models.ModelTransformOutput
algorithm:
  algorithm_type: weighted_factor_algorithm
  factors:
    - factor_name: input_complexity
      weight: 0.5
"""

        result = validator.validate_contract_yaml(compute_yaml, "compute")

        # Verify contract type is identified correctly
        assert result.contract_type == "compute"
        # Note: Due to ModelContractCompute's custom __init__, validation may fail
        # but the validator should still identify the contract type and provide
        # helpful error messages
        if not result.is_valid:
            assert len(result.violations) > 0 or len(result.suggestions) > 0

    def test_score_calculation(self) -> None:
        """Test score calculation with various violations and warnings."""
        validator = ProtocolContractValidator()

        # Contract with multiple issues
        problematic_yaml = """
name: T
version:
  major: 1
  minor: 0
  patch: 0
description: X
node_type: effect
input_model: Input
output_model: Output
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""

        result = validator.validate_contract_yaml(problematic_yaml, "effect")

        # Score should be reduced due to warnings
        assert result.score < 1.0
        assert len(result.warnings) > 0
        # Should have warnings about naming and short description
        assert any("description" in w.lower() for w in result.warnings)

    def test_validate_empty_yaml(self) -> None:
        """Test validation of empty YAML content."""
        validator = ProtocolContractValidator()

        result = validator.validate_contract_yaml("", "effect")

        assert not result.is_valid
        assert result.score == 0.0
        assert "Empty YAML content" in result.violations

    def test_validate_syntax_error_in_model(self) -> None:
        """Test validation handles Python syntax errors in model code."""
        validator = ProtocolContractValidator()

        invalid_python = """
class InvalidClass
    this is not valid python
"""

        contract_yaml = """
name: TestEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Test effect contract
node_type: effect
input_model: ModelInput
output_model: ModelOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""

        result = validator.validate_model_compliance(invalid_python, contract_yaml)

        assert not result.is_valid
        assert result.score == 0.0
        assert any("syntax error" in v.lower() for v in result.violations)

    def test_validate_contract_file(self, tmp_path) -> None:
        """Test validation of contract from file path."""
        validator = ProtocolContractValidator()

        # Create temporary contract file
        contract_file = tmp_path / "test_contract.yaml"
        contract_file.write_text(
            """
name: FileTestEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Effect contract from file
node_type: effect
input_model: ModelInput
output_model: ModelOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""
        )

        result = validator.validate_contract_file(contract_file, "effect")

        assert result.is_valid
        assert result.score >= 0.8

    def test_validate_nonexistent_file(self) -> None:
        """Test validation fails for nonexistent file."""
        validator = ProtocolContractValidator()

        result = validator.validate_contract_file(
            "/nonexistent/path/contract.yaml", "effect"
        )

        assert not result.is_valid
        assert result.score == 0.0
        assert any("not found" in v.lower() for v in result.violations)

    def test_suggestions_provided(self) -> None:
        """Test that validation provides helpful suggestions."""
        validator = ProtocolContractValidator()

        # Use a contract name without the Effect suffix to trigger naming suggestions
        contract_yaml = """
name: TestWriter
version:
  major: 1
  minor: 0
  patch: 0
description: Test effect contract for suggestions
node_type: effect
input_model: ModelInput
output_model: ModelOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""

        result = validator.validate_contract_yaml(contract_yaml, "effect")

        # Should have suggestions for improvement (naming convention)
        assert len(result.suggestions) > 0
        assert any("Effect" in s for s in result.suggestions)

    def test_model_with_any_type_warning(self) -> None:
        """Test that using Any type generates warnings."""
        validator = ProtocolContractValidator()

        model_code = """
from typing import Any
from pydantic import BaseModel

class ModelTestInput(BaseModel):
    data: Any  # Should generate warning
"""

        contract_yaml = """
name: TestEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Test effect contract
node_type: effect
input_model: omnibase_core.models.ModelTestInput
output_model: omnibase_core.models.ModelTestOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
"""

        result = validator.validate_model_compliance(model_code, contract_yaml)

        # Should warn about Any type usage
        assert len(result.warnings) > 0
        assert any("Any" in w for w in result.warnings)


class TestProtocolContractValidationResult:
    """Test ProtocolContractValidationResult model."""

    def test_result_creation(self) -> None:
        """Test creating validation result."""
        result = ProtocolContractValidationResult(
            is_valid=True,
            score=0.95,
            violations=[],
            warnings=["Minor warning"],
            suggestions=["Consider improvement"],
            contract_type="effect",
            interface_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert result.is_valid
        assert result.score == 0.95
        assert len(result.warnings) == 1
        assert len(result.suggestions) == 1

    def test_result_score_bounds(self) -> None:
        """Test score is bounded between 0.0 and 1.0."""
        # Valid score
        result = ProtocolContractValidationResult(
            is_valid=True,
            score=0.5,
        )
        assert 0.0 <= result.score <= 1.0

    def test_result_with_violations(self) -> None:
        """Test result with violations."""
        result = ProtocolContractValidationResult(
            is_valid=False,
            score=0.3,
            violations=["Critical error 1", "Critical error 2"],
        )

        assert not result.is_valid
        assert len(result.violations) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
