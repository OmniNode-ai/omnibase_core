# Omnibase Core Validation Tools

Comprehensive validation framework for ONEX compliance across the omni* ecosystem. This module provides reusable validation tools that can be imported and used by other repositories to maintain code quality and architectural standards.

## Features

- **Architecture Validation**: Enforce ONEX one-model-per-file principle
- **Type Validation**: Detect problematic Union usage and type patterns
- **Contract Validation**: Validate YAML contract files
- **Pattern Validation**: Check code patterns and naming conventions
- **Unified CLI**: Single command-line interface for all validation tools
- **Programmatic API**: Import and use validation functions in code

## Installation

Since this is part of `omnibase_core`, install the package:

```
pip install omnibase_core
```

## Quick Start

### CLI Usage

The easiest way to use validation tools is through the CLI:

```
# Run all validations
python -m omnibase_core.validation all

# Run specific validation
python -m omnibase_core.validation architecture src/
python -m omnibase_core.validation union-usage --strict
python -m omnibase_core.validation contracts
python -m omnibase_core.validation patterns --strict

# List available validators
python -m omnibase_core.validation list
```

### Programmatic Usage

Import and use validation functions in your code:

```
from omnibase_core.validation import (
    validate_architecture,
    validate_union_usage,
    validate_contracts,
    validate_patterns,
    validate_all
)

# Validate architecture compliance
result = validate_architecture("src/")
if not result.success:
    print(f"Architecture violations: {len(result.errors)}")
    for error in result.errors:
        print(f"  - {error}")

# Validate union usage
result = validate_union_usage("src/", max_unions=50, strict=True)
if result.success:
    print(f"✅ Union validation passed: {result.metadata['total_unions']} unions found")

# Run all validations
results = validate_all("src/", strict=True)
for validation_type, result in results.items():
    status = "✅ PASSED" if result.success else "❌ FAILED"
    print(f"{validation_type}: {status}")
```

## Validation Types

### 1. Architecture Validation

Enforces ONEX one-model-per-file architectural principle:

- One model per file
- No mixed types (models + enums + protocols in same file)
- Proper separation of concerns

```
# CLI
python -m omnibase_core.validation architecture src/ --max-violations 0

# Python
from omnibase_core.validation import validate_architecture
result = validate_architecture("src/", max_violations=0)
```

#### Common Issues Fixed:

- Multiple Pydantic models in one file
- Mixed model types in single file
- Poor architectural organization

### 2. Union Usage Validation

Detects problematic Union type patterns:

- Complex unions that should be models
- Primitive-heavy unions
- Overly broad unions
- Union[T, None] instead of Optional[T]

```
# CLI
python -m omnibase_core.validation union-usage src/ --max-unions 100 --strict

# Python
from omnibase_core.validation import validate_union_usage
result = validate_union_usage("src/", max_unions=100, strict=True)
```

#### Examples of Issues Detected:

```
# ❌ Problematic patterns
Union[str, int, bool, float]  # Too many primitives
Union[str, int, dict, list]   # Mixed primitive/complex
Union[str, None]              # Use Optional[str]

# ✅ Better alternatives
Optional[str]                 # For nullable strings
ModelConfigValue              # For complex unions
T = TypeVar('T')              # For generic patterns
```

### 3. Contract Validation

Validates YAML contract files:

- Valid YAML syntax
- Required contract fields
- No manual YAML in restricted areas
- Proper contract structure

```
# CLI
python -m omnibase_core.validation contracts contracts/

# Python
from omnibase_core.validation import validate_contracts
result = validate_contracts("contracts/")
```

### 4. Pattern Validation

Checks code patterns and conventions:

- Pydantic model naming (should start with "Model")
- String ID fields (should use UUID)
- Category/status fields (should use enums)
- Anti-pattern detection (Manager, Handler, etc.)
- Function naming conventions

```
# CLI
python -m omnibase_core.validation patterns src/ --strict

# Python
from omnibase_core.validation import validate_patterns
result = validate_patterns("src/", strict=True)
```

#### Examples of Issues Fixed:

```
# ❌ Problematic patterns
class User(BaseModel):           # Should be ModelUser
    user_id: str                 # Should be UUID
    status: str                  # Should be enum

class UserManager:               # Anti-pattern name

# ✅ ONEX compliant
class ModelUser(BaseModel):
    user_id: UUID
    status: EnumUserStatus

class ModelUserService:          # Specific domain name
```

## Integration in Other Repositories

### Pre-commit Hook Integration

Add to your `.pre-commit-config.yaml`:

```
repos:
  - repo: local
    hooks:
      - id: onex-validation
        name: ONEX Validation
        entry: python -m omnibase_core.validation
        args: [all, --strict]
        language: python
        pass_filenames: false
        additional_dependencies: [omnibase_core]
```

### CI/CD Integration

Add to your GitHub Actions workflow:

```
- name: ONEX Validation
  run: |
    pip install omnibase_core
    python -m omnibase_core.validation all --strict
```

### Custom Validation Scripts

Create custom validation scripts for your repository:

```
#!/usr/bin/env python3
"""Custom validation for my-repo."""

from omnibase_core.validation import validate_all
import sys

def main():
    # Run all validations with custom parameters
    results = validate_all(
        "src/",
        strict=True,
        max_unions=50,
        max_violations=0
    )

    success = all(result.success for result in results.values())

    # Custom reporting
    print("🔍 My Repo Validation Results")
    print("=" * 40)

    for validation_type, result in results.items():
        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"{validation_type:15} {status}")

        if not result.success:
            print(f"  Issues: {len(result.errors)}")
            for error in result.errors[:3]:  # Show first 3
                print(f"    • {error}")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
```

## Advanced Usage

### Custom Validation Suite

Create a custom validation suite for specific needs:

```
from omnibase_core.validation import ValidationSuite
from pathlib import Path

# Create custom suite
suite = ValidationSuite()

# Run specific validations
directory = Path("src/")
arch_result = suite.run_validation("architecture", directory, max_violations=0)
union_result = suite.run_validation("union-usage", directory, strict=True)

# Custom analysis
if not arch_result.success:
    files_with_violations = arch_result.metadata.get("files_with_violations", [])
    print(f"Architecture violations in {len(files_with_violations)} files")
```

### File-level Validation

Validate individual files:

```
from omnibase_core.validation.types import validate_union_usage_file
from omnibase_core.validation.patterns import validate_patterns_file
from pathlib import Path

# Validate single file
file_path = Path("src/models/model_user.py")

# Check union usage
union_count, issues, patterns = validate_union_usage_file(file_path)
print(f"Found {union_count} unions with {len(issues)} issues")

# Check patterns
pattern_issues = validate_patterns_file(file_path)
print(f"Found {len(pattern_issues)} pattern issues")
```

## Configuration

### Environment Variables

- `VALIDATION_TIMEOUT`: Timeout for validation operations (default: 300s)
- `MAX_FILE_SIZE`: Maximum file size for validation (default: 50MB)

### Custom Configuration

For repositories with special needs, create custom validation wrappers:

```
# my_repo_validation.py
from omnibase_core.validation import validate_all

def validate_my_repo(strict=True):
    """Custom validation for my repository."""
    return validate_all(
        "src/",
        strict=strict,
        max_unions=25,        # Stricter union limit
        max_violations=0,     # No architecture violations allowed
    )
```

## API Reference

### ValidationResult

All validation functions return a `ValidationResult` object:

```
@dataclass
class ValidationResult:
    success: bool                    # Overall success status
    errors: list[str]               # List of error messages
    files_checked: int              # Number of files validated
    violations_found: int           # Number of violations detected
    files_with_violations: int      # Number of files with violations
    metadata: dict                  # Additional validation-specific data
```

### Main Functions

- `validate_architecture(directory, max_violations=0)` → `ValidationResult`
- `validate_union_usage(directory, max_unions=100, strict=False)` → `ValidationResult`
- `validate_contracts(directory)` → `ValidationResult`
- `validate_patterns(directory, strict=False)` → `ValidationResult`
- `validate_all(directory, **kwargs)` → `Dict[str, ValidationResult]`

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `omnibase_core` is installed and in Python path
2. **Permission Errors**: Check file/directory permissions
3. **Timeout Errors**: Increase timeout for large codebases
4. **Memory Issues**: Validate smaller directories for very large codebases

### Debug Mode

Run with verbose output:

```
python -m omnibase_core.validation all --verbose
```

### Performance Tips

- Use `--strict` only when needed (slower but more thorough)
- Validate specific directories instead of entire codebase
- Consider running different validations in parallel for large codebases

## Contributing

To add new validation tools:

1. Create new module in `src/omnibase_core/validation/`
2. Follow the pattern of existing validators
3. Add CLI integration in `cli.py`
4. Update `__init__.py` exports
5. Add tests and documentation

## Examples for Different Repository Types

### FastAPI Service Repository

```
# validate_service.py
from omnibase_core.validation import validate_all

def validate_service():
    """Validate FastAPI service for ONEX compliance."""
    results = validate_all(
        "src/",
        strict=True,
        max_unions=30,        # Services typically have fewer unions
        max_violations=0,     # Strict architecture
    )

    # Check API-specific patterns
    contract_result = results.get("contracts")
    if contract_result and not contract_result.success:
        print("⚠️  API contract validation failed")

    return all(r.success for r in results.values())
```

### CLI Tool Repository

```
# validate_cli.py  
from omnibase_core.validation import validate_patterns, validate_union_usage

def validate_cli_tool():
    """Validate CLI tool for ONEX compliance."""
    # CLI tools may have more unions for parameter handling
    union_result = validate_union_usage("src/", max_unions=150, strict=False)

    # Strict pattern validation for CLI commands
    pattern_result = validate_patterns("src/", strict=True)

    return union_result.success and pattern_result.success
```

This validation framework helps maintain high code quality and ONEX compliance across all repositories in the omni* ecosystem.
