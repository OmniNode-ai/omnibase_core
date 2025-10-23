# Validators Package

Reusable validation tools for code quality and compliance checks.

## Overview

The `validators` package provides validation tools that can be used by any project consuming `omnibase_core` as a dependency. These validators help ensure code quality and detect common issues.

## Available Validators

### CircularImportValidator

Detects circular import issues in Python codebases by attempting to import all modules and identifying circular dependencies.

#### Features

- **Comprehensive scanning**: Discovers and tests all Python files in a codebase
- **Detailed reporting**: Provides structured results with success/failure categorization
- **Customizable patterns**: Include/exclude file patterns for targeted validation
- **Progress tracking**: Optional callbacks for real-time progress updates
- **Type-safe**: Full mypy strict mode compliance

#### Quick Start

```python
from omnibase_core.validators import CircularImportValidator

# Basic usage
validator = CircularImportValidator(source_path="/path/to/src")
result = validator.validate()

if result.has_circular_imports:
    print(f"Found {len(result.circular_imports)} circular imports!")
    for ci in result.circular_imports:
        print(f"  - {ci.module_name}: {ci.error_message}")
else:
    print("No circular imports detected!")
```

#### Advanced Usage

```python
from omnibase_core.validators import CircularImportValidator

# Custom patterns and verbosity
validator = CircularImportValidator(
    source_path="/path/to/src",
    include_patterns=["*.py"],           # Only .py files
    exclude_patterns=["test_*.py"],      # Skip test files
    verbose=True,                        # Print detailed progress
)

# Run validation
result = validator.validate()

# Access structured results
print(f"Success rate: {result.success_rate:.1f}%")
print(f"Total files: {result.total_files}")
print(f"Successful: {result.success_count}")
print(f"Failed: {result.failure_count}")

# Get summary dictionary
summary = result.get_summary()
# Returns: {
#   'total_files': 100,
#   'successful': 95,
#   'circular_imports': 0,
#   'import_errors': 3,
#   'unexpected_errors': 2,
#   'skipped': 0
# }
```

#### Progress Callbacks

```python
def on_progress(message: str) -> None:
    print(f"Progress: {message}")

validator = CircularImportValidator(
    source_path="/path/to/src",
    progress_callback=on_progress
)

result = validator.validate()
```

#### Validation and Reporting

```python
# One-shot validation with formatted report
validator = CircularImportValidator(source_path="/path/to/src", verbose=True)
exit_code = validator.validate_and_report()

# Prints:
# Testing for circular imports...
# Source path: /path/to/src
#
# Found 100 Python files to test
# ================================================================================
# ✓ module.name.one
# ✓ module.name.two
# ...
# ================================================================================
# RESULTS
# ================================================================================
# Total files: 100
# ✓ Successful imports: 95
# ✗ Circular imports detected: 0
# ...
# Success rate: 95.0%
#
# 🎉 No circular imports detected!
```

#### Result Structure

```python
from omnibase_core.validators import ValidationResult, ModuleImportResult, ImportStatus

# ValidationResult properties
result.total_files: int                           # Total files scanned
result.successful_imports: list[ModuleImportResult]
result.circular_imports: list[ModuleImportResult]
result.import_errors: list[ModuleImportResult]
result.unexpected_errors: list[ModuleImportResult]
result.skipped: list[ModuleImportResult]

# Properties
result.has_circular_imports: bool                 # Any circular imports?
result.has_errors: bool                           # Any errors at all?
result.success_count: int                         # Count of successful imports
result.failure_count: int                         # Count of failed imports
result.success_rate: float                        # Success rate (0-100)

# ModuleImportResult attributes
import_result.module_name: str                    # Module name
import_result.status: ImportStatus                # Status enum
import_result.error_message: Optional[str]        # Error if failed
import_result.file_path: Optional[str]            # Path to file

# ImportStatus enum values
ImportStatus.SUCCESS
ImportStatus.CIRCULAR_IMPORT
ImportStatus.IMPORT_ERROR
ImportStatus.UNEXPECTED_ERROR
ImportStatus.SKIPPED
```

## Integration Examples

### CI/CD Pipeline

```python
#!/usr/bin/env python3
"""Pre-commit hook to detect circular imports."""
import sys
from omnibase_core.validators import CircularImportValidator

def main() -> int:
    validator = CircularImportValidator(
        source_path="src/",
        verbose=False
    )
    result = validator.validate()

    if result.has_circular_imports:
        print("❌ Circular imports detected - commit blocked!")
        for ci in result.circular_imports:
            print(f"  {ci.module_name}")
        return 1

    print("✅ No circular imports")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Library/Package Validation

```python
from omnibase_core.validators import CircularImportValidator

def validate_package(package_path: str) -> bool:
    """Validate package has no circular imports."""
    validator = CircularImportValidator(
        source_path=package_path,
        verbose=False
    )
    result = validator.validate()
    return not result.has_circular_imports
```

## CLI Script

A CLI script is included for direct usage:

```bash
# From project root
poetry run python scripts/test_circular_imports.py

# Output:
# Testing for circular imports...
# Source path: /path/to/src
#
# Found 100 Python files to test
# ...
# ✓ Successful imports: 95
# ✗ Circular imports detected: 0
# 🎉 No circular imports detected!
```

## Type Safety

All validators are fully type-safe and pass `mypy --strict` validation:

```bash
poetry run mypy src/omnibase_core/validators/ --strict
# Success: no issues found in 3 source files
```

## Requirements

- Python 3.11+
- No external dependencies (uses only stdlib)

## Future Validators

Additional validators planned for this package:

- `DependencyValidator` - Validate dependency usage and circular dependencies
- `TypeSafetyValidator` - Automated mypy validation
- `ONEXComplianceValidator` - ONEX architecture compliance checking
- `ImportStyleValidator` - Enforce consistent import styles
