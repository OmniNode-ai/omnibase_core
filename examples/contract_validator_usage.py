# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract Validator Usage Examples.

Demonstrates how to use the ContractValidator API for contract validation.
"""

from omnibase_core.services.service_contract_validator import ServiceContractValidator


def example_1_validate_yaml_contract():
    """Example 1: Validate a YAML contract."""
    print("\n=== Example 1: Validate YAML Contract ===\n")

    validator = ServiceContractValidator()

    # Effect contract YAML
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

    print(f"Valid: {result.is_valid}")
    print(f"Score: {result.score:.2f}")
    print(f"Contract Type: {result.contract_type}")
    print(f"Interface Version: {result.interface_version}")

    if result.violations:
        print("\nViolations:")
        for violation in result.violations:
            print(f"  - {violation}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.suggestions:
        print("\nSuggestions:")
        for suggestion in result.suggestions:
            print(f"  - {suggestion}")


def example_2_validate_model_compliance():
    """Example 2: Validate model code against contract."""
    print("\n=== Example 2: Validate Model Compliance ===\n")

    validator = ServiceContractValidator()

    # Pydantic model code
    model_code = """
from pydantic import BaseModel, Field

class ModelDatabaseWriteInput(BaseModel):
    table_name: str = Field(..., description="Target table name")
    data: dict[str, object] = Field(..., description="Data to write")

class ModelDatabaseWriteOutput(BaseModel):
    success: bool = Field(..., description="Write operation success")
    rows_affected: int = Field(..., description="Number of rows affected")
"""

    # Contract YAML
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

    print(f"Valid: {result.is_valid}")
    print(f"Score: {result.score:.2f}")

    if result.violations:
        print("\nViolations:")
        for violation in result.violations:
            print(f"  - {violation}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.suggestions:
        print("\nSuggestions:")
        for suggestion in result.suggestions:
            print(f"  - {suggestion}")


def example_3_validate_contract_file():
    """Example 3: Validate contract from file."""
    print("\n=== Example 3: Validate Contract File ===\n")

    validator = ServiceContractValidator()

    # Create a temporary contract file
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
name: FileReaderEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Effect node for reading files from filesystem
node_type: effect
input_model: omnibase_core.models.ModelFileReadInput
output_model: omnibase_core.models.ModelFileReadOutput
io_operations:
  - operation_type: READ
    operation_target: FILE
    atomic: false
    validation_enabled: true
    error_handling_strategy: RETRY
"""
        )
        temp_file = f.name

    try:
        result = validator.validate_contract_file(temp_file, "effect")

        print(f"Valid: {result.is_valid}")
        print(f"Score: {result.score:.2f}")
        print(f"File: {temp_file}")

        if result.violations:
            print("\nViolations:")
            for violation in result.violations:
                print(f"  - {violation}")
    finally:
        # Cleanup
        Path(temp_file).unlink()


def example_4_handle_validation_errors():
    """Example 4: Handle validation errors gracefully."""
    print("\n=== Example 4: Handle Validation Errors ===\n")

    validator = ServiceContractValidator()

    # Invalid contract (missing required fields)
    invalid_yaml = """
name: IncompleteContract
version:
  major: 1
  minor: 0
  patch: 0
"""

    result = validator.validate_contract_yaml(invalid_yaml, "effect")

    print(f"Valid: {result.is_valid}")
    print(f"Score: {result.score:.2f}")

    if not result.is_valid:
        print("\nValidation failed with the following issues:")

        for i, violation in enumerate(result.violations, 1):
            print(f"\n{i}. VIOLATION: {violation}")

        for i, suggestion in enumerate(result.suggestions, 1):
            print(f"\n{i}. SUGGESTION: {suggestion}")


def example_5_scoring_system():
    """Example 5: Understanding the scoring system."""
    print("\n=== Example 5: Scoring System ===\n")

    validator = ServiceContractValidator()

    test_cases = [
        (
            "Perfect contract",
            """
name: PerfectEffect
version:
  major: 1
  minor: 0
  patch: 0
description: This is a well-documented effect contract with all required fields
node_type: effect
input_model: omnibase_core.models.ModelPerfectInput
output_model: omnibase_core.models.ModelPerfectOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
""",
        ),
        (
            "Short description",
            """
name: TestEffect
version:
  major: 1
  minor: 0
  patch: 0
description: Short
node_type: effect
input_model: omnibase_core.models.ModelInput
output_model: omnibase_core.models.ModelOutput
io_operations:
  - operation_type: WRITE
    operation_target: DATABASE
    atomic: true
    validation_enabled: true
    error_handling_strategy: RETRY
""",
        ),
        (
            "Missing fields",
            """
name: BadContract
version:
  major: 1
  minor: 0
  patch: 0
description: Missing required fields
node_type: effect
""",
        ),
    ]

    for name, yaml_content in test_cases:
        result = validator.validate_contract_yaml(yaml_content, "effect")
        print(f"{name}:")
        print(f"  Score: {result.score:.2f}")
        print(f"  Valid: {result.is_valid}")
        print(f"  Violations: {len(result.violations)}")
        print(f"  Warnings: {len(result.warnings)}")
        print()


if __name__ == "__main__":
    print("=== Contract Validator Usage Examples ===")
    print("Interface Version: 1.0.0")

    example_1_validate_yaml_contract()
    example_2_validate_model_compliance()
    example_3_validate_contract_file()
    example_4_handle_validation_errors()
    example_5_scoring_system()

    print("\n=== All examples completed ===")
