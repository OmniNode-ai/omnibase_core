# Contract Validator API

**Version**: 1.0.0

## Overview

The Contract Validator API provides programmatic validation of YAML contracts and Pydantic model code against ONEX standards.

## Key Features

✅ **YAML Contract Validation** - Validates contracts against locked-down contract models
✅ **Model Code Compliance** - Validates Pydantic models against contract specifications
✅ **ONEX Compliance Checking** - Ensures naming conventions and architectural standards
✅ **Scoring System** - Provides 0.0 to 1.0 score based on completeness and correctness
✅ **Actionable Feedback** - Clear violations, warnings, and suggestions for improvement
✅ **Multi-Contract Support** - Supports effect, compute, reducer, and orchestrator contracts
✅ **File Validation** - Direct validation from YAML files

## Installation

```
from omnibase_core.validation import ContractValidator, ContractValidationResult
```

## Quick Start

### Validate YAML Contract

```
from omnibase_core.validation import ContractValidator

validator = ContractValidator()

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

if result.is_valid:
    print(f"✓ Contract valid! Score: {result.score:.2f}")
else:
    print(f"✗ Contract invalid! Score: {result.score:.2f}")
    for violation in result.violations:
        print(f"  - {violation}")
```

### Validate Model Compliance

```
model_code = """
from pydantic import BaseModel, Field

class ModelDatabaseWriteInput(BaseModel):
    table_name: str = Field(..., description="Target table name")
    data: dict[str, object] = Field(..., description="Data to write")

class ModelDatabaseWriteOutput(BaseModel):
    success: bool = Field(..., description="Write operation success")
    rows_affected: int = Field(..., description="Number of rows affected")
"""

result = validator.validate_model_compliance(model_code, contract_yaml)

if result.is_valid:
    print("✓ Model code complies with contract")
else:
    print("✗ Model code has issues:")
    for violation in result.violations:
        print(f"  - {violation}")
```

### Validate Contract File

```
result = validator.validate_contract_file("/path/to/contract.yaml", "effect")

if result.is_valid:
    print(f"✓ Contract file valid! Score: {result.score:.2f}")
```

## API Reference

### ContractValidator

Main validator class for contract validation.

#### Methods

##### `validate_contract_yaml(contract_content: str, contract_type: Literal["effect", "compute", "reducer", "orchestrator"]) -> ContractValidationResult`

Validates a YAML contract against ONEX standards.

- **Parameters:**
  - `contract_content`: YAML contract content as string
  - `contract_type`: Type of contract to validate against
- **Returns:** `ContractValidationResult` with validation details

##### `validate_model_compliance(model_code: str, contract_yaml: str) -> ContractValidationResult`

Validates Pydantic model code against a contract.

- **Parameters:**
  - `model_code`: Python code containing Pydantic model definition
  - `contract_yaml`: YAML contract content as string
- **Returns:** `ContractValidationResult` with compliance details

##### `validate_contract_file(file_path: str | Path, contract_type: Literal["effect", "compute", "reducer", "orchestrator"]) -> ContractValidationResult`

Validates a YAML contract file.

- **Parameters:**
  - `file_path`: Path to YAML contract file
  - `contract_type`: Type of contract to validate against
- **Returns:** `ContractValidationResult` with validation details

### ContractValidationResult

Validation result model with scoring and feedback.

#### Fields

- **`is_valid: bool`** - Whether the contract passes all validation checks
- **`score: float`** - Validation score from 0.0 to 1.0
- **`violations: list[str]`** - Critical errors that prevent validation
- **`warnings: list[str]`** - Non-critical issues that should be addressed
- **`suggestions: list[str]`** - Recommendations for improvement
- **`contract_type: str | None`** - Type of contract validated
- **`interface_version: str`** - INTERFACE_VERSION used for validation (1.0.0)

## Scoring System

The validator uses a weighted scoring system:

| Score Range | Status | Description |
|------------|--------|-------------|
| 1.0 | Perfect | No violations, warnings, or issues |
| 0.8 - 0.99 | Good | Valid but has warnings |
| 0.5 - 0.79 | Needs Work | Has violations but recoverable |
| 0.0 - 0.49 | Critical | Severe violations, needs major fixes |

### Scoring Formula:

- Base score: 1.0
- Each violation: -0.20
- Each warning: -0.05
- Minimum score: 0.0

## Contract Types Supported

### Effect Contracts
```
result = validator.validate_contract_yaml(yaml_content, "effect")
```
- Requires: `io_operations` field
- Validates: Transaction management, retry policies, external services

### Compute Contracts
```
result = validator.validate_contract_yaml(yaml_content, "compute")
```
- Requires: `algorithm` field
- Validates: Algorithm configuration, parallel processing

### Reducer Contracts
```
result = validator.validate_contract_yaml(yaml_content, "reducer")
```
- Validates: State management, aggregation logic

### Orchestrator Contracts
```
result = validator.validate_contract_yaml(yaml_content, "orchestrator")
```
- Validates: Workflow coordination, routing logic

## ONEX Compliance Checks

The validator enforces ONEX naming conventions and standards:

✓ **Naming Conventions**
- Contract names should end with node type suffix (e.g., `DatabaseWriterEffect`)
- Model names should start with `Model` prefix (e.g., `ModelDatabaseWriteInput`)
- File patterns follow `node_*_<type>.py` format

✓ **Type Safety**
- No `Any` types allowed (generates warnings)
- Strong typing enforced throughout
- Proper Pydantic field definitions

✓ **Interface Stability**
- Validates against INTERFACE_VERSION 1.0.0
- Ensures contract compatibility with locked-down models
- Checks for required fields and proper structure

## Error Handling

The validator provides three levels of feedback:

### Violations (Critical)
- Missing required fields
- Invalid field types
- ONEX standard violations
- Syntax errors

### Warnings (Non-Critical)
- Naming convention deviations
- Short descriptions
- Missing optional recommendations

### Suggestions (Improvements)
- Better naming patterns
- Field recommendations
- Best practice guidance

## Examples

See `/examples/contract_validator_usage.py` for comprehensive examples including:
- Basic YAML validation
- Model compliance checking
- File validation
- Error handling
- Scoring system demonstration

## Integration with Autonomous Systems

The validator is designed for autonomous code generation:

```
def generate_contract_autonomously(requirements):
    """Autonomous contract generation with validation."""

    # Generate contract from requirements
    contract_yaml = generate_from_requirements(requirements)

    # Validate contract
    validator = ContractValidator()
    result = validator.validate_contract_yaml(contract_yaml, "effect")

    # Auto-fix if score is good but has warnings
    if result.score >= 0.8 and not result.is_valid:
        contract_yaml = apply_suggestions(contract_yaml, result.suggestions)
        result = validator.validate_contract_yaml(contract_yaml, "effect")

    # Return validated contract
    if result.is_valid:
        return contract_yaml
    else:
        raise ValidationError(result.violations)
```

## Performance Characteristics

- **YAML Parsing**: ~5-10ms for typical contracts
- **Validation**: ~20-50ms for complete validation
- **File I/O**: ~2-5ms additional for file-based validation
- **Model Analysis**: ~10-30ms for AST parsing and validation

**Total**: ~50-100ms per validation (autonomous generation friendly)

## Testing

Comprehensive test suite with 19 test cases covering:
- Valid and invalid YAML contracts
- Model compliance checking
- ONEX naming convention validation
- Scoring calculation
- Error handling
- File validation
- Edge cases

Run tests:
```
poetry run pytest tests/unit/validation/test_contract_validator.py -v
```

## Version Information

- **Interface Version**: 1.0.0 (Locked)
- **Contract Model Version**: 1.0.0
- **Status**: Production Ready
- **Breaking Changes**: Requires major version bump

## Support

For issues or questions:
1. Check examples in `/examples/contract_validator_usage.py`
2. Review test cases in `/tests/unit/validation/test_contract_validator.py`
3. Consult ONEX architecture documentation

---

**Last Updated**: 2025-10-14
**Status**: Interface Stable
