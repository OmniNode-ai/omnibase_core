# Invalid Union Remediation Plan

**Project**: omnibase_core v0.1.0
**Generated**: 2025-10-28
**Correlation ID**: 43716f9a-4ac4-4a05-b9f3-ae2af0d139d7
**Status**: 232 Invalid Unions Identified
**Target**: 0 Invalid Unions (Zero Tolerance Policy)

---

## Executive Summary

This document provides a comprehensive remediation plan for eliminating all 232 invalid union patterns in omnibase_core. Invalid unions violate ONEX strong typing principles and introduce type safety risks.

### Current State

- **Total Unions**: 4,700
- **Legitimate Unions**: 4,468 (95.1%)
- **Invalid Unions**: 232 (4.9%)
- **Total Issues**: 1,060 (including suggestions)

### Pattern Breakdown

| Pattern Type | Count | % of Invalid | Priority |
|--------------|-------|--------------|----------|
| **Primitive Soup** | 186 | 80.2% | HIGH |
| **Complex Union** | 42 | 18.1% | MEDIUM |
| **Any Contaminated** | 4 | 1.7% | CRITICAL |

### Module Impact Analysis

| Module | Invalid Unions | % of Total | Impact |
|--------|----------------|------------|--------|
| **models/security** | 94 | 40.5% | CRITICAL |
| **models/core** | 59 | 25.4% | HIGH |
| **models/discovery** | 32 | 13.8% | MEDIUM |
| **models/service** | 12 | 5.2% | MEDIUM |
| **models/kafka** | 8 | 3.4% | LOW |
| **models/validation** | 7 | 3.0% | LOW |
| **models/docker** | 6 | 2.6% | LOW |
| **Other modules** | 14 | 6.0% | LOW |

---

## Part 1: Existing Replacement Models

### 1.1 ModelSchemaValue (Primary Replacement)

**Location**: `src/omnibase_core/models/common/model_schema_value.py`

**Purpose**: Type-safe representation of schema values without Any types

**Replaces**: `Union[str, int, float, bool, list, dict, None]` (186 instances)

**Key Features**:
- Discriminated union with `value_type` field
- Supports: string, number, boolean, null, array, object
- Factory methods: `from_value()`, `create_string()`, `create_number()`, etc.
- Type-safe accessors: `get_string()`, `get_number()`, etc.
- Recursive structure for nested values

**Example Usage**:
```python
# Before (Invalid)
field_value: Union[str, int, float, bool, list, dict] = ...

# After (Valid)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

field_value: ModelSchemaValue = ModelSchemaValue.from_value(raw_value)

# Type-safe access
if field_value.is_string():
    text = field_value.get_string()
elif field_value.is_number():
    num = field_value.get_number()
```

**Applicable To**:
- All primitive soup unions (186 instances)
- Security model data masking patterns (94 instances)
- Discovery tool parameters (32 instances)
- Workflow parameters (12 instances)

---

### 1.2 ModelFlexibleValue (Advanced Replacement)

**Location**: `src/omnibase_core/models/common/model_flexible_value.py`

**Purpose**: Discriminated union for mixed-type values with metadata

**Replaces**: Complex unions requiring source tracking or validation state

**Key Features**:
- Enum-based type discriminator (`EnumFlexibleValueType`)
- Supports: string, integer, float, boolean, dict, list, uuid, none
- Metadata fields: `source`, `is_validated`
- Factory methods: `from_any()`, `from_string()`, etc.
- Type checking: `is_primitive()`, `is_collection()`, `is_none()`
- Conversion: `to_schema_value()`, `get_value()`

**Example Usage**:
```python
# Before (Invalid)
config_value: Union[str, int, bool, dict[str, Any]] = ...

# After (Valid)
from omnibase_core.models.common.model_flexible_value import ModelFlexibleValue

config_value: ModelFlexibleValue = ModelFlexibleValue.from_any(
    raw_value,
    source="user_input"
)

# Type-safe access with validation state
if config_value.is_validated and config_value.is_primitive():
    value = config_value.get_value()
```

**Applicable To**:
- Configuration values requiring source tracking
- User input values needing validation state
- Environment properties (8-type unions)
- Extension data fields

---

### 1.3 Other Existing Models

#### ModelValueContainer
**Location**: `src/omnibase_core/models/common/model_typed_value.py`
**Purpose**: Generic value container for type-safe storage
**Use Case**: When you need a generic container with protocol constraints

#### ModelNumericValue
**Location**: `src/omnibase_core/models/common/model_numeric_value.py`
**Purpose**: Handles `Union[int, float]` with precision tracking
**Use Case**: Numeric values needing precision preservation

#### ModelTypedMapping
**Location**: `src/omnibase_core/models/common/model_typed_mapping.py`
**Purpose**: Type-safe mapping container
**Use Case**: Dictionary-like structures with strong typing

---

## Part 2: New Model Proposals

### 2.1 ModelFilterUnion (For Filter Discriminated Unions)

**Problem**: `Union[ModelComplexFilter, ModelDateTimeFilter, ModelListFilter, ModelMetadataFilter, ModelNumericFilter, ModelStatusFilter, ModelStringFilter]`

**File**: `src/omnibase_core/models/core/model_custom_filters.py:17`

**Proposed Solution**:
```python
# File: src/omnibase_core/models/core/model_filter_union.py

from typing import Annotated, Literal
from pydantic import BaseModel, Field, Discriminator

from .model_complex_filter import ModelComplexFilter
from .model_datetime_filter import ModelDateTimeFilter
from .model_list_filter import ModelListFilter
from .model_metadata_filter import ModelMetadataFilter
from .model_numeric_filter import ModelNumericFilter
from .model_status_filter import ModelStatusFilter
from .model_string_filter import ModelStringFilter

# Ensure all filter models have a 'filter_type' discriminator field
FilterType = Literal[
    "complex",
    "datetime",
    "list",
    "metadata",
    "numeric",
    "status",
    "string",
]

ModelFilterUnion = Annotated[
    ModelComplexFilter
    | ModelDateTimeFilter
    | ModelListFilter
    | ModelMetadataFilter
    | ModelNumericFilter
    | ModelStatusFilter
    | ModelStringFilter,
    Field(discriminator="filter_type"),
]
```

**Effort**: 4 hours (Medium complexity)
**Breaking Changes**: Yes - all filter models need `filter_type` field
**Priority**: HIGH (affects core filtering system)
**Impact**: 1 file, but used throughout filtering logic

---

### 2.2 ModelEnvironmentValue (For Environment Properties)

**Problem**: `Union[bool, datetime, float, int, list, str, dict, None]` (8 types)

**File**: `src/omnibase_core/models/core/model_environment_properties.py:17`

**Current Analysis**: This is essentially a ModelSchemaValue use case with datetime support

**Proposed Solution**:
```python
# Use ModelFlexibleValue with custom datetime handling

from datetime import datetime
from omnibase_core.models.common.model_flexible_value import ModelFlexibleValue

class ModelEnvironmentValue(BaseModel):
    """Environment property value with datetime support."""

    # Use ModelSchemaValue for base types
    value: ModelSchemaValue = Field(...)

    # Additional datetime support
    datetime_value: datetime | None = Field(
        default=None,
        description="Datetime value if applicable"
    )

    @classmethod
    def from_any(cls, value: object) -> "ModelEnvironmentValue":
        """Create from any supported type including datetime."""
        if isinstance(value, datetime):
            return cls(
                value=ModelSchemaValue.from_value(value.isoformat()),
                datetime_value=value
            )
        return cls(value=ModelSchemaValue.from_value(value))
```

**Effort**: 2 hours (Low complexity - extends existing model)
**Breaking Changes**: No - can be introduced gradually
**Priority**: MEDIUM
**Impact**: 1 file (environment_properties.py)

---

### 2.3 ModelMaskedDataValue (For Security Masking)

**Problem**: `Union[None, bool, dict, float, int, list, str]` (94 instances in security models)

**Files**:
- `model_masked_data.py`
- `model_masked_data_class.py`
- `model_masked_data_dict.py`
- `model_masked_data_list.py`
- `model_security_policy_data.py` (multiple fields)
- `model_condition_value.py`

**Current Analysis**: All security models use identical union pattern for masked data

**Proposed Solution**: Use `ModelSchemaValue` directly

```python
# In all security models, replace:
masked_value: Union[None, bool, dict, float, int, list, str]

# With:
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

masked_value: ModelSchemaValue = Field(
    ...,
    description="Masked data value - type-safe representation"
)
```

**Justification**:
- ModelSchemaValue already handles all these types
- No additional model needed
- Consistent with ONEX strong typing standards
- Enables type-safe masking operations

**Effort**: 8 hours (High impact - affects 94 instances across 10+ files)
**Breaking Changes**: Yes - API changes in security layer
**Priority**: CRITICAL (largest single pattern)
**Impact**: 10+ files in models/security

---

### 2.4 ModelWorkflowParameterValue

**Problem**: `Union[bool, dict, float, int, list, str, None]` (8 types)

**File**: `src/omnibase_core/models/service/model_workflow_parameters.py:18`

**Current Analysis**: Same as environment properties - use existing models

**Proposed Solution**: Use `ModelSchemaValue` directly

```python
# Replace:
parameter_value: Union[bool, dict, float, int, list, str, None]

# With:
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

parameter_value: ModelSchemaValue = Field(
    ...,
    description="Workflow parameter value - supports all JSON types"
)
```

**Effort**: 1 hour (Simple replacement)
**Breaking Changes**: Minimal - compatible serialization
**Priority**: MEDIUM
**Impact**: 1 file

---

### 2.5 ModelActionPayloadUnion (For Action Payloads)

**Problem**: Overly broad discriminated union (mentioned in validator suggestions)

**File**: `src/omnibase_core/models/core/model_action_payload_types.py:46`

**Current**: Likely already a discriminated union that needs refinement

**Proposed Solution**: Verify existing implementation and add explicit discriminator

```python
# Ensure this pattern:
from typing import Annotated, Literal
from pydantic import Field

ActionType = Literal[
    "custom",
    "data",
    "filesystem",
    "lifecycle",
    "management",
    "monitoring",
    "operational",
    "registry",
    "transformation",
    "validation",
]

ModelActionPayloadUnion = Annotated[
    ModelCustomActionPayload
    | ModelDataActionPayload
    | ModelFilesystemActionPayload
    | ModelLifecycleActionPayload
    | ModelManagementActionPayload
    | ModelMonitoringActionPayload
    | ModelOperationalActionPayload
    | ModelRegistryActionPayload
    | ModelTransformationActionPayload
    | ModelValidationActionPayload,
    Field(discriminator="action_type"),
]
```

**Effort**: 3 hours (Verify + refine existing pattern)
**Breaking Changes**: Minimal if already discriminated
**Priority**: HIGH (core action system)
**Impact**: 1 file, but critical infrastructure

---

## Part 3: Prioritized Implementation Plan

### Phase 1: Quick Wins (Week 1) - Primitive Soup Elimination

**Focus**: Replace primitive soup unions with `ModelSchemaValue`

**Targets**: 186 instances

#### Tasks:

1. **Security Models (94 instances)** - 8 hours
   - Files: `model_masked_data*.py`, `model_security_policy_data.py`, `model_condition_value.py`
   - Replace all `Union[None, bool, dict, float, int, list, str]` with `ModelSchemaValue`
   - Update masking logic to use `ModelSchemaValue` accessors
   - Add tests for type-safe masking operations

2. **Discovery Models (32 instances)** - 3 hours
   - Files: `model_tool_parameters.py`, `model_toolparameters.py`, `model_metric_value.py`
   - Replace parameter unions with `ModelSchemaValue`
   - Update tool introspection to handle typed values

3. **Core Models (30 instances)** - 4 hours
   - Files: `model_custom_fields.py`, `model_argument_value.py`, `model_extension_data.py`
   - Replace field value unions with `ModelSchemaValue`
   - Update serialization/deserialization logic

4. **Workflow & Service Models (12 instances)** - 2 hours
   - Files: `model_workflow_parameters.py`, `model_environment_properties.py`
   - Replace parameter/property unions with `ModelSchemaValue`

**Total Effort**: ~17 hours (2-3 days)
**Expected Reduction**: 186 → 0 primitive soup unions
**Validation**: Run `poetry run python scripts/validation/validate-union-usage.py --allow-invalid 0`

---

### Phase 2: Complex Unions (Week 2) - Discriminated Union Refinement

**Focus**: Refine existing discriminated unions and fix complex patterns

**Targets**: 42 instances

#### Tasks:

1. **Filter Union Refinement (1 instance)** - 4 hours
   - File: `model_custom_filters.py`
   - Add explicit discriminator to all filter models
   - Create `ModelFilterUnion` type alias
   - Update filter usage throughout codebase

2. **Action Payload Union (1 instance)** - 3 hours
   - File: `model_action_payload_types.py`
   - Verify discriminator implementation
   - Add explicit type hints for discriminator
   - Update action handlers

3. **Complex Union Investigation (40 instances)** - 10 hours
   - Analyze remaining complex unions case-by-case
   - Determine if they can use `ModelSchemaValue` or need custom models
   - Implement solutions with proper discriminators

**Total Effort**: ~17 hours (2-3 days)
**Expected Reduction**: 42 → 0 complex unions
**Validation**: Check discriminated union patterns with validator

---

### Phase 3: Any Contamination (Week 3) - Critical Cleanup

**Focus**: Eliminate `Any` types from unions

**Targets**: 4 instances

#### Tasks:

1. **Any Contaminated Union Analysis (4 instances)** - 6 hours
   - Identify exact locations and context
   - Determine proper strongly-typed replacements
   - Implement replacements with full type safety
   - Add tests to prevent Any reintroduction

**Total Effort**: ~6 hours (1 day)
**Expected Reduction**: 4 → 0 any-contaminated unions
**Validation**: Zero tolerance for Any types

---

### Phase 4: Validation & Documentation (Week 3-4)

#### Tasks:

1. **Comprehensive Testing** - 8 hours
   - Run full test suite: `poetry run pytest tests/`
   - Fix any test failures from type changes
   - Add new tests for `ModelSchemaValue` usage
   - Validate serialization/deserialization

2. **Type Checking** - 2 hours
   - Run mypy: `poetry run mypy src/omnibase_core/`
   - Fix any new type errors
   - Ensure 100% strict mode compliance

3. **Union Validation** - 1 hour
   - Run validator: `poetry run python scripts/validation/validate-union-usage.py --allow-invalid 0`
   - Verify zero invalid unions
   - Update threshold if needed

4. **Documentation Updates** - 4 hours
   - Update affected model documentation
   - Add migration guide for users
   - Document ModelSchemaValue patterns
   - Update CLAUDE.md with new patterns

5. **Breaking Change Communication** - 2 hours
   - Document all breaking changes
   - Create migration examples
   - Update CHANGELOG.md
   - Prepare release notes

**Total Effort**: ~17 hours (2-3 days)

---

## Part 4: Effort Estimation & Timeline

### Summary by Effort

| Effort Category | Count | Total Hours | % of Work |
|-----------------|-------|-------------|-----------|
| **< 1 hour** | 50 | 25 | 42.4% |
| **1-3 hours** | 150 | 225 | 48.1% |
| **3-6 hours** | 30 | 120 | 19.2% |
| **> 6 hours** | 2 | 18 | 3.8% |
| **Total** | 232 | 388 | 100% |

### Total Project Effort

- **Implementation**: 40 hours (5 days)
- **Testing**: 8 hours (1 day)
- **Type Checking**: 2 hours
- **Validation**: 1 hour
- **Documentation**: 4 hours
- **Breaking Changes**: 2 hours
- **Buffer (20%)**: 11 hours

**Total**: ~68 hours (~9 working days or ~2 calendar weeks)

### Milestone Schedule

| Milestone | Duration | Completion Date | Deliverables |
|-----------|----------|-----------------|--------------|
| **Phase 1 Complete** | Week 1 | Day 5 | 186 primitive soup unions eliminated |
| **Phase 2 Complete** | Week 2 | Day 10 | 42 complex unions refined |
| **Phase 3 Complete** | Week 3 | Day 12 | 4 any-contaminated unions eliminated |
| **Phase 4 Complete** | Week 3-4 | Day 15 | Full validation, testing, documentation |
| **Project Complete** | End Week 3-4 | Day 15 | **Zero invalid unions** |

---

## Part 5: Risk Analysis & Mitigation

### High-Risk Changes

#### 1. Security Model Changes (94 instances)
**Risk**: Breaking changes in security/masking layer
**Impact**: HIGH - Core security functionality
**Mitigation**:
- Comprehensive test coverage before changes
- Gradual rollout with feature flags
- Backward compatibility layer during transition
- Extra review by security expert

#### 2. Action Payload Changes
**Risk**: Breaking changes in action system
**Impact**: HIGH - Core action infrastructure
**Mitigation**:
- Verify existing discriminator implementation first
- Minimal changes if already properly discriminated
- Extensive integration testing
- Rollback plan prepared

### Medium-Risk Changes

#### 1. Discovery Model Changes (32 instances)
**Risk**: Tool introspection breakage
**Impact**: MEDIUM - Affects service discovery
**Mitigation**:
- Test with all registered tools
- Validate introspection metadata
- Update tool documentation

#### 2. Filter Union Changes
**Risk**: Filter query breakage
**Impact**: MEDIUM - Affects data querying
**Mitigation**:
- Test all filter types
- Validate query construction
- Performance testing

### Low-Risk Changes

#### Primitive Replacements in Non-Critical Models
**Risk**: Serialization incompatibility
**Impact**: LOW - ModelSchemaValue has compatible serialization
**Mitigation**:
- Test serialization roundtrips
- Verify JSON compatibility

---

## Part 6: Success Criteria

### Quantitative Metrics

1. ✅ **Zero Invalid Unions**: `0` (currently `232`)
2. ✅ **Zero Any Types**: `0` in union patterns
3. ✅ **100% Test Pass Rate**: All 400+ tests passing
4. ✅ **100% Mypy Compliance**: 0 errors in strict mode
5. ✅ **Coverage Maintained**: ≥60% (current requirement)

### Qualitative Metrics

1. ✅ **Type Safety**: All unions use discriminated patterns or ModelSchemaValue
2. ✅ **ONEX Compliance**: All changes follow ONEX architecture patterns
3. ✅ **Documentation**: All affected models documented with examples
4. ✅ **Migration Path**: Clear upgrade guide for users
5. ✅ **Performance**: No regression in serialization/deserialization

---

## Part 7: Implementation Examples

### Example 1: Security Model Migration

**Before** (`model_masked_data.py`):
```python
class ModelMaskedData(BaseModel):
    """Masked data representation."""

    original_value: Union[None, bool, dict, float, int, list, str] = Field(
        ...,
        description="Original unmasked value"
    )

    masked_value: Union[None, bool, dict, float, int, list, str] = Field(
        ...,
        description="Masked value"
    )
```

**After**:
```python
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

class ModelMaskedData(BaseModel):
    """Masked data representation with strong typing."""

    original_value: ModelSchemaValue = Field(
        ...,
        description="Original unmasked value - type-safe representation"
    )

    masked_value: ModelSchemaValue = Field(
        ...,
        description="Masked value - type-safe representation"
    )

    # Usage example
    def get_original_as_string(self) -> str:
        """Get original value as string if it is a string type."""
        if self.original_value.is_string():
            return self.original_value.get_string()
        return str(self.original_value.to_value())
```

**Migration Code**:
```python
# Automatic migration helper
def migrate_to_schema_value(old_value: Any) -> ModelSchemaValue:
    """Migrate old union values to ModelSchemaValue."""
    return ModelSchemaValue.from_value(old_value)

# In serialization
masked_data_dict = {
    "original_value": migrate_to_schema_value(old_data["original_value"]),
    "masked_value": migrate_to_schema_value(old_data["masked_value"]),
}
```

---

### Example 2: Discovery Model Migration

**Before** (`model_tool_parameters.py`):
```python
class ModelToolParameters(BaseModel):
    """Tool parameter definition."""

    default_value: Union[bool, dict, float, int, list, str] = Field(
        ...,
        description="Default parameter value"
    )
```

**After**:
```python
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

class ModelToolParameters(BaseModel):
    """Tool parameter definition with strong typing."""

    default_value: ModelSchemaValue = Field(
        ...,
        description="Default parameter value - supports all JSON types"
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelToolParameters":
        """Create from dictionary with automatic value conversion."""
        # Convert default_value to ModelSchemaValue if needed
        if "default_value" in data and not isinstance(data["default_value"], ModelSchemaValue):
            data["default_value"] = ModelSchemaValue.from_value(data["default_value"])
        return cls(**data)
```

---

### Example 3: Filter Union Migration

**Before** (`model_custom_filters.py`):
```python
# Overly broad union without explicit discriminator
FilterUnion = Union[
    ModelComplexFilter,
    ModelDateTimeFilter,
    ModelListFilter,
    ModelMetadataFilter,
    ModelNumericFilter,
    ModelStatusFilter,
    ModelStringFilter,
]
```

**After**:
```python
from typing import Annotated, Literal
from pydantic import Field

# Step 1: Add discriminator to each filter model
class ModelStringFilter(BaseModel):
    filter_type: Literal["string"] = "string"
    # ... other fields

class ModelNumericFilter(BaseModel):
    filter_type: Literal["numeric"] = "numeric"
    # ... other fields

# Step 2: Create discriminated union
ModelFilterUnion = Annotated[
    ModelComplexFilter
    | ModelDateTimeFilter
    | ModelListFilter
    | ModelMetadataFilter
    | ModelNumericFilter
    | ModelStatusFilter
    | ModelStringFilter,
    Field(discriminator="filter_type"),
]

# Step 3: Usage
def apply_filter(filter_obj: ModelFilterUnion) -> Any:
    """Apply filter with type-safe discrimination."""
    if filter_obj.filter_type == "string":
        # Type checker knows this is ModelStringFilter
        return apply_string_filter(filter_obj)
    elif filter_obj.filter_type == "numeric":
        # Type checker knows this is ModelNumericFilter
        return apply_numeric_filter(filter_obj)
    # ... other cases
```

---

## Part 8: Rollback Plan

### Rollback Triggers

1. Test suite pass rate < 95%
2. Mypy errors introduced
3. Performance regression > 10%
4. Critical security functionality broken

### Rollback Procedure

1. **Immediate**: Revert commit(s) from feature branch
2. **Short-term**: Keep old union patterns alongside new patterns
3. **Long-term**: Gradual migration with feature flags

### Backward Compatibility

```python
# Compatibility layer example
class ModelMaskedDataCompat(BaseModel):
    """Backward compatible masked data."""

    # New field (preferred)
    masked_value: ModelSchemaValue | None = None

    # Old field (deprecated)
    masked_value_legacy: Union[None, bool, dict, float, int, list, str] | None = None

    @model_validator(mode="after")
    def migrate_legacy(self) -> "ModelMaskedDataCompat":
        """Auto-migrate legacy field to new field."""
        if self.masked_value is None and self.masked_value_legacy is not None:
            self.masked_value = ModelSchemaValue.from_value(self.masked_value_legacy)
        return self
```

---

## Part 9: Testing Strategy

### Unit Tests

**New Tests Required**: ~50 tests

1. **ModelSchemaValue Usage** (20 tests)
   - Serialization roundtrips
   - Type checking methods
   - Factory method validation
   - Edge cases (empty lists, null values)

2. **Security Model Migration** (15 tests)
   - Masking with typed values
   - Type-safe unmasking
   - Serialization compatibility

3. **Discovery Model Migration** (10 tests)
   - Tool parameter handling
   - Introspection metadata
   - Default value handling

4. **Filter Union** (5 tests)
   - Discriminator validation
   - Filter query construction
   - Type-safe filter application

### Integration Tests

**New Tests Required**: ~15 tests

1. **End-to-End Security Workflows** (5 tests)
   - Data masking pipelines
   - Policy evaluation with typed values

2. **Discovery System** (5 tests)
   - Tool registration with typed parameters
   - Tool introspection

3. **Filter Queries** (5 tests)
   - Complex filter combinations
   - Query execution

### Performance Tests

**Benchmarks Required**: 5 benchmarks

1. ModelSchemaValue serialization vs old unions
2. Masking performance with typed values
3. Filter query construction time
4. Tool introspection overhead
5. Memory usage comparison

---

## Part 10: Post-Remediation Validation

### Validation Checklist

- [ ] Run union validator: `poetry run python scripts/validation/validate-union-usage.py --allow-invalid 0`
- [ ] Verify zero invalid unions reported
- [ ] Run full test suite: `poetry run pytest tests/ -xvs`
- [ ] Verify 100% test pass rate
- [ ] Run mypy: `poetry run mypy src/omnibase_core/`
- [ ] Verify zero mypy errors
- [ ] Run coverage: `poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing`
- [ ] Verify coverage ≥ 60%
- [ ] Run pre-commit hooks: `pre-commit run --all-files`
- [ ] Verify all hooks pass
- [ ] Performance benchmarks show no regression
- [ ] Documentation updated and reviewed
- [ ] Breaking changes documented
- [ ] Migration guide completed
- [ ] CHANGELOG.md updated
- [ ] Release notes prepared

### Final Metrics Report

**Target Metrics** (to be filled post-remediation):

```text
Union Validation Results:
  Total unions found: 4,700
  Legitimate unions: 4,700 (100%)
  Invalid unions: 0 (0%)

Test Results:
  Total tests: 450+
  Passed: 450+
  Failed: 0
  Coverage: ≥60%

Type Checking:
  Mypy errors: 0
  Files checked: 1,865
  Strict mode: Enabled

Performance:
  Serialization: <5% regression
  Memory: <10% increase
  Query time: No regression
```

---

## Part 11: Lessons Learned & Prevention

### Root Causes

1. **Lazy Typing**: Developers used `Union[str, int, float, bool, ...]` as quick solution
2. **Missing Models**: ModelSchemaValue existed but wasn't consistently used
3. **Pattern Awareness**: Lack of awareness about existing typed value models
4. **Validation Timing**: Union validation added late in development

### Prevention Strategies

1. **Pre-commit Hook**: Union validator runs on every commit (already implemented)
2. **Zero Tolerance**: Set `--allow-invalid 0` in CI/CD
3. **Code Review**: Require explicit approval for any Union usage
4. **Documentation**: Prominently document ModelSchemaValue in CLAUDE.md
5. **Templates**: Provide code snippets for common value patterns
6. **Training**: Educate developers on ONEX strong typing principles

### Updated Guidelines

**Add to CLAUDE.md**:

```markdown
## Handling Mixed-Type Values

❌ **NEVER** use primitive soup unions:
```python
# WRONG
field_value: Union[str, int, float, bool, list, dict]
```

✅ **ALWAYS** use ModelSchemaValue:
```python
# CORRECT
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

field_value: ModelSchemaValue = Field(...)

# Create from any value
value = ModelSchemaValue.from_value(raw_value)

# Type-safe access
if value.is_string():
    text = value.get_string()
```

✅ **For discriminated unions**, use Pydantic discriminator:
```python
# CORRECT
from typing import Annotated, Literal
from pydantic import Field

class ModelStringOption(BaseModel):
    option_type: Literal["string"] = "string"
    value: str

class ModelIntOption(BaseModel):
    option_type: Literal["int"] = "int"
    value: int

OptionUnion = Annotated[
    ModelStringOption | ModelIntOption,
    Field(discriminator="option_type")
]
```

---

## Appendix A: Complete Invalid Union Inventory

### By Module (Top 15)

1. **models/security** (94 unions)
   - `model_masked_data.py`: 6 unions
   - `model_masked_data_class.py`: 6 unions
   - `model_masked_data_dict.py`: 6 unions
   - `model_masked_data_list.py`: 6 unions
   - `model_security_policy_data.py`: 50 unions
   - `model_condition_value.py`: 10 unions
   - Others: 10 unions

2. **models/core** (59 unions)
   - `model_environment_properties.py`: 8 unions
   - `model_custom_filters.py`: 7 unions
   - `model_custom_fields.py`: 6 unions
   - `model_extension_data.py`: 6 unions
   - `model_node_action.py`: 6 unions
   - Others: 26 unions

3. **models/discovery** (32 unions)
   - `model_tool_parameters.py`: 12 unions
   - `model_toolparameters.py`: 15 unions
   - `model_metric_value.py`: 5 unions

4. **models/service** (12 unions)
   - `model_workflow_parameters.py`: 8 unions
   - Others: 4 unions

5. **models/kafka** (8 unions)

6. **models/validation** (7 unions)

7. **models/docker** (6 unions)

8. **Other modules** (14 unions)

---

## Appendix B: References

### Internal Documentation
- `/docs/guides/node-building/README.md` - Node building guide
- `/docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md` - ONEX architecture
- `/docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md` - Error handling
- `/CLAUDE.md` - Project conventions

### Validation Tools
- `scripts/validation/validate-union-usage.py` - Union validation script
- `/tmp/union_validation_full_report.json` - Full validation report
- `/tmp/invalid_unions_categorized.json` - Categorized analysis

### Key Models
- `src/omnibase_core/models/common/model_schema_value.py`
- `src/omnibase_core/models/common/model_flexible_value.py`
- `src/omnibase_core/models/common/model_typed_value.py`
- `src/omnibase_core/models/common/model_value_container.py`

---

## Appendix C: Contact & Support

### Project Team
- **Architecture Review**: ONEX Core Team
- **Security Review**: Security Team (for Phase 1 changes)
- **Code Review**: Senior Python Developers

### Questions & Issues
- **GitHub Issues**: https://github.com/OmniNode-ai/omnibase_core/issues
- **Discussion**: Project discussion channels
- **Documentation**: `/docs/research/UNION_REMEDIATION_PLAN.md` (this document)

---

**Document Status**: Draft
**Last Updated**: 2025-10-28
**Next Review**: After Phase 1 completion
**Approval Required**: Architecture Lead, Security Lead

---

**End of Remediation Plan**
