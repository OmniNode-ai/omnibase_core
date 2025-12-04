# Validation Protocol Compliance

This document describes the validation domain's protocol compliance with omnibase_spi validation protocols.

> **Note (v0.3.6)**: The `omnibase_spi` dependency was removed in v0.3.6 as part of
> the dependency inversion refactoring. SPI now depends on Core (not the reverse).
> Protocol compliance tests that depended on SPI protocols have been removed.
> This document is retained for historical reference and will be updated when
> Core-native protocol compliance is implemented.

## Overview

The omnibase_core validation domain implements two key SPI protocols:

1. **ProtocolComplianceValidator** - Implemented by `ProtocolContractValidator`
2. **ProtocolQualityValidator** - Implemented by `ModelProtocolAuditor`

This provides standardized interfaces for validation operations across the ONEX ecosystem while maintaining backward compatibility with existing functionality.

## Protocol Implementations

### ProtocolContractValidator

**File**: `src/omnibase_core/validation/contract_validator.py`

**Implements**: `omnibase_spi.protocols.validation.protocol_compliance_validator.ProtocolComplianceValidator`

#### Protocol Attributes

- `onex_standards: ProtocolONEXStandards | None` - ONEX naming and architectural standards
- `architecture_rules: ProtocolArchitectureCompliance | None` - Architecture compliance rules
- `custom_rules: list[ProtocolComplianceRule]` - Custom validation rules
- `strict_mode: bool` - Enable strict validation mode (default: False)

#### Protocol Methods

| Method | Status | Description |
|--------|--------|-------------|
| `validate_file_compliance()` | Stub | Validate file compliance with ONEX standards |
| `validate_repository_compliance()` | Stub | Validate entire repository compliance |
| `validate_onex_naming()` | Stub | Validate ONEX naming conventions |
| `validate_architecture_compliance()` | Stub | Validate architecture compliance |
| `validate_directory_structure()` | Stub | Validate repository directory structure |
| `validate_dependency_compliance()` | Stub | Validate dependency compliance |
| `aggregate_compliance_results()` | Stub | Aggregate compliance results |
| `add_custom_rule()` | ✅ Implemented | Add custom compliance rule |
| `configure_onex_standards()` | ✅ Implemented | Configure ONEX standards |
| `get_compliance_summary()` | Stub | Get compliance summary |

#### Existing Methods (Backward Compatible)

All existing methods remain unchanged and fully functional:

- `validate_contract_yaml()` - Validate YAML contracts
- `validate_model_compliance()` - Validate model code compliance
- `validate_contract_file()` - Validate contract from file

### ModelProtocolAuditor

**File**: `src/omnibase_core/validation/auditor_protocol.py`

**Implements**: `omnibase_spi.protocols.validation.protocol_quality_validator.ProtocolQualityValidator`

#### Protocol Attributes

- `standards: ProtocolQualityStandards | None` - Quality standards configuration
- `enable_complexity_analysis: bool` - Enable complexity analysis (default: True)
- `enable_duplication_detection: bool` - Enable duplication detection (default: True)
- `enable_style_checking: bool` - Enable style checking (default: True)

#### Protocol Methods

| Method | Status | Description |
|--------|--------|-------------|
| `validate_file_quality()` | Stub | Validate file quality metrics |
| `validate_directory_quality()` | Stub | Validate directory quality |
| `calculate_quality_metrics()` | Stub | Calculate quality metrics |
| `detect_code_smells()` | Stub | Detect code smells |
| `check_naming_conventions()` | Stub | Check naming conventions |
| `analyze_complexity()` | Stub | Analyze code complexity |
| `validate_documentation()` | Stub | Validate documentation quality |
| `suggest_refactoring()` | Stub | Suggest refactoring opportunities |
| `configure_standards()` | ✅ Implemented | Configure quality standards |
| `get_validation_summary()` | Stub | Get validation summary |

#### Existing Methods (Backward Compatible)

All existing methods remain unchanged and fully functional:

- `check_current_repository()` - Audit current repository
- `check_against_spi()` - Check against SPI for duplicates
- `audit_ecosystem()` - Comprehensive ecosystem audit

## Usage Examples

### Using ProtocolContractValidator

```
from omnibase_core.validation.contract_validator import ProtocolContractValidator
from omnibase_spi.protocols.validation.protocol_compliance_validator import (
    ProtocolComplianceValidator
)

# Create validator with protocol compliance
validator = ProtocolContractValidator(strict_mode=True)

# Use as protocol type
compliance_validator: ProtocolComplianceValidator = validator

# Use existing methods (backward compatible)
result = validator.validate_contract_yaml(yaml_content, "effect")
print(f"Valid: {result.is_valid}, Score: {result.score}")

# Add custom rules (protocol method implemented)
# validator.add_custom_rule(custom_rule)

# Protocol methods (stubs - will be implemented in future versions)
# await validator.validate_file_compliance("path/to/file.py")
```

### Using ModelProtocolAuditor

```
from omnibase_core.validation.auditor_protocol import ModelProtocolAuditor
from omnibase_spi.protocols.validation.protocol_quality_validator import (
    ProtocolQualityValidator
)

# Create auditor with protocol compliance
auditor = ModelProtocolAuditor(
    enable_complexity_analysis=True,
    enable_duplication_detection=True
)

# Use as protocol type
quality_validator: ProtocolQualityValidator = auditor

# Use existing methods (backward compatible)
result = auditor.check_current_repository()
print(f"Protocols found: {result.protocols_found}")
print(f"Duplicates: {result.duplicates_found}")

# Protocol methods (stubs - will be implemented in future versions)
# await auditor.validate_file_quality("path/to/file.py")
```

## Protocol Compliance Testing

> **Note (v0.3.6)**: The protocol compliance tests (`tests/unit/validation/test_protocol_compliance.py`)
> were removed in v0.3.6 because they depended on `omnibase_spi` protocols. These tests verified:
>
> - Protocol implementation verification (`isinstance()` checks against SPI protocols)
> - Required attributes presence and types
> - Required methods presence and callability
> - Backward compatibility verification
> - Optional parameter handling
> - Stub method behavior (NotImplementedError with helpful messages)
> - Polymorphic usage validation
>
> Future work: Implement Core-native protocol compliance testing once Core defines its own
> protocol interfaces independent of SPI.

### Running Tests

```
# Run all validation tests (verify backward compatibility)
poetry run pytest tests/unit/validation/ -v
```

## Implementation Status

### Current State (v0.1.0)

- ✅ Protocol interfaces implemented
- ✅ Protocol attributes added
- ✅ Configuration methods implemented
- ✅ Backward compatibility maintained
- ✅ Comprehensive tests added
- ⏳ Protocol methods are stubs (NotImplementedError)

### Future Enhancements

Protocol method implementations will be added incrementally:

1. **Phase 1**: ONEX naming validation
   - `validate_onex_naming()`
   - Integration with existing naming patterns

2. **Phase 2**: File compliance validation
   - `validate_file_compliance()`
   - Quality metrics integration

3. **Phase 3**: Repository-level validation
   - `validate_repository_compliance()`
   - `validate_directory_structure()`

4. **Phase 4**: Full protocol compliance
   - Complete all stub implementations
   - Enhanced quality metrics
   - Advanced compliance reporting

## Migration Guide

### For Existing Code

No changes required! All existing code continues to work:

```
# This still works exactly as before
validator = ProtocolContractValidator()
result = validator.validate_contract_yaml(yaml_content)
```

### For New Code Using Protocols

```
# New code can use protocol types for flexibility
from omnibase_spi.protocols.validation.protocol_compliance_validator import (
    ProtocolComplianceValidator
)

def validate_with_protocol(validator: ProtocolComplianceValidator) -> None:
    """Works with any ProtocolComplianceValidator implementation."""
    # Use existing methods
    result = validator.validate_contract_yaml(content)

    # Or future protocol methods
    # await validator.validate_file_compliance("file.py")
```

## Design Decisions

### Stub Methods with NotImplementedError

Protocol methods that are not yet implemented raise `NotImplementedError` with clear messages indicating:

1. The method is a protocol stub
2. What existing methods can be used instead
3. That implementation is pending

This approach:
- ✅ Satisfies protocol interface requirements
- ✅ Provides clear error messages to users
- ✅ Allows incremental implementation
- ✅ Maintains backward compatibility

### Backward Compatibility

All changes are purely additive:
- No existing methods modified
- No existing signatures changed
- Optional parameters added with defaults
- New methods are additional protocol implementations

### Type Annotations

Protocol attributes use union types with None to indicate optional dependencies:
```
self.onex_standards: ProtocolONEXStandards | None = None
```

This allows:
- Gradual adoption of protocol features
- Flexibility in configuration
- Clear indication of optional vs required

## Benefits

1. **Standardization**: Consistent interfaces across ONEX ecosystem
2. **Interoperability**: Validators can be used polymorphically
3. **Evolution**: Room for future enhancements without breaking changes
4. **Testing**: Protocol compliance is verifiable
5. **Documentation**: Clear contracts for implementers and users

## See Also

- [Contract Validator](../../src/omnibase_core/validation/contract_validator.py)
- [Protocol Auditor](../../src/omnibase_core/validation/auditor_protocol.py)

> **Note (v0.3.6)**: The link to omnibase_spi validation protocols was removed as
> SPI now depends on Core. See the omnibase_spi repository for SPI-specific protocols.
