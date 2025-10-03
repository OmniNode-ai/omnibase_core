# Actionable Fixes - Quick Reference

This document provides specific, ready-to-implement fixes for the issues found in the model/enum analysis.

## CRITICAL Fixes (Do These First)

### 1. Extract Duplicate Enum: ModelComputationType

**Issue:** Same enum defined in two files
**Files:**
- `/root/repo/src/omnibase_core/models/operations/model_computation_input_data.py:54`
- `/root/repo/src/omnibase_core/models/operations/model_computation_output_data.py:21`

**Fix:**

1. Create `/root/repo/src/omnibase_core/enums/enum_computation_type.py`:
```python
"""Computation type enumeration."""
from enum import Enum

class EnumComputationType(str, Enum):
    """Types of computation operations."""

    NUMERIC = "numeric"
    TEXT = "text"
    BINARY = "binary"
    STRUCTURED = "structured"
```

2. Update both files to import:
```python
from omnibase_core.enums.enum_computation_type import EnumComputationType

# Remove the local ModelComputationType class definition
```

3. Update `__init__.py` in enums directory to export it

**Estimated Time:** 15 minutes

---

### 2. Fix HIGH Severity Any Type Usage

#### 2a. ModelResult - Add Generic Type Parameter

**File:** `/root/repo/src/omnibase_core/models/infrastructure/model_result.py:25`

**Current:**
```python
class ModelResult(BaseModel):
    value: Any
    error: Any
```

**Fix:**
```python
from typing import Generic, TypeVar

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

class ModelResult(BaseModel, Generic[T, E]):
    value: T | None = None
    error: E | None = None
```

**Estimated Time:** 30 minutes

#### 2b. ModelWorkflowCondition - Use Discriminated Union

**File:** `/root/repo/src/omnibase_core/models/contracts/model_workflow_condition.py:35`

**Current:**
```python
expected_value: ModelConditionValue[Any] | ModelConditionValueList
```

**Fix:** Create specific typed variants:
```python
# Define concrete types
ExpectedValueType = (
    ModelConditionValue[str] |
    ModelConditionValue[int] |
    ModelConditionValue[bool] |
    ModelConditionValue[float] |
    ModelConditionValueList
)

expected_value: ExpectedValueType
```

**Estimated Time:** 30 minutes

#### 2c. ModelConfigurationBase - Add Type Variants

**File:** `/root/repo/src/omnibase_core/models/core/model_configuration_base.py:29`

**Current:**
```python
config_data: Any
```

**Fix:** Use discriminated union or dict with proper types:
```python
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

config_data: dict[str, ModelSchemaValue] | None = None
```

**Estimated Time:** 30 minutes

---

## HIGH Priority Fixes (Use Existing Enums)

These fields have `str` type but corresponding enums ALREADY EXIST:

### 3. Quick Wins - Fields with Existing Enums

| File | Line | Field | Current | Fix | Enum Already Exists |
|------|------|-------|---------|-----|---------------------|
| `model_workflow_instance_metadata.py` | 36 | workflow_type | str | EnumWorkflowType | ✅ Yes |
| `model_event_metadata.py` | 36 | event_type | str | EnumEventType | ✅ Yes |
| `model_workflow_config.py` | 13 | execution_mode | str | EnumExecutionMode | ✅ Yes |
| `model_output_transformation_config.py` | 13 | format_type | str | EnumDataFormat | ✅ Yes |
| `model_event_descriptor.py` | 15 | criticality_level | str | EnumSeverityLevel | ✅ Yes |
| `model_message_payload.py` | 117 | data_type | str | EnumDataType | ✅ Yes |

**Fix Template:**

1. Add import at top of file:
```python
from omnibase_core.enums.enum_workflow_type import EnumWorkflowType
```

2. Change field type:
```python
# Before
workflow_type: str = Field(..., description="Type of workflow")

# After
workflow_type: EnumWorkflowType = Field(..., description="Type of workflow")
```

3. Update any tests or usages

**Estimated Time:** 15 minutes per field × 6 fields = 90 minutes

---

## MEDIUM Priority Fixes (Create New Enums)

### 4. Create Missing Enums for Common Patterns

#### 4a. Health Status Enum

**Usage:** Found in 3+ files
**Create:** `/root/repo/src/omnibase_core/enums/enum_health_status.py`

```python
"""Health status enumeration."""
from enum import Enum

class EnumHealthStatus(str, Enum):
    """System health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
```

**Apply to:**
- `model_system_metadata.py:50` - `health_status`

#### 4b. Validation Status Enum

**Create:** `/root/repo/src/omnibase_core/enums/enum_validation_status.py`

```python
"""Validation status enumeration."""
from enum import Enum

class EnumValidationStatus(str, Enum):
    """Validation status values."""

    VALID = "valid"
    INVALID = "invalid"
    PENDING = "pending"
    SKIPPED = "skipped"
    ERROR = "error"
```

**Apply to:**
- `model_computation_output_data.py:139` - `schema_validation_status`

#### 4c. Integrity Status Enum

**Create:** `/root/repo/src/omnibase_core/enums/enum_integrity_status.py`

```python
"""Data integrity status enumeration."""
from enum import Enum

class EnumIntegrityStatus(str, Enum):
    """Data integrity status values."""

    INTACT = "intact"
    CORRUPTED = "corrupted"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
```

**Apply to:**
- `model_computation_output_data.py:122` - `data_integrity_status`

**Estimated Time:** 20 minutes per enum × 3 = 60 minutes

---

## Model Naming Fixes

### 5. Rename Duplicate Model Names

#### 5a. Rename ModelGenericMetadata in results package

**File:** `/root/repo/src/omnibase_core/models/results/model_generic_metadata.py`

**Steps:**
1. Rename class to `ModelResultsMetadata` or `ModelTimestampedMetadata`
2. Update all imports in the same package
3. Update exports in `__init__.py`

**Estimated Time:** 30 minutes

#### 5b. Rename ModelRetryPolicy in event routing

**File:** `/root/repo/src/omnibase_core/models/contracts/subcontracts/model_event_routing.py`

**Steps:**
1. Rename class to `ModelEventRetryConfig`
2. Update usage in `ModelEventRouting` class (same file)
3. Search for any external usages and update

**Estimated Time:** 20 minutes

---

## Implementation Order

**Week 1 - Critical & High Impact:**
1. ✅ Extract duplicate enum (15 min)
2. ✅ Fix ModelResult generics (30 min)
3. ✅ Fix 6 fields using existing enums (90 min)
4. ✅ Rename duplicate models (50 min)

**Total Week 1:** ~3 hours

**Week 2 - Medium Impact:**
5. ✅ Create 3 new enums (60 min)
6. ✅ Fix ModelWorkflowCondition (30 min)
7. ✅ Fix ModelConfigurationBase (30 min)

**Total Week 2:** ~2 hours

**Week 3+ - Remaining Items:**
8. ⏭️ Address remaining 73 str→enum conversions as needed
9. ⏭️ Protocol implementation standardization
10. ⏭️ Enum consolidation review

---

## Testing Checklist

After each fix:

- [ ] Run mypy type checking: `mypy src/omnibase_core`
- [ ] Run unit tests: `pytest tests/`
- [ ] Check for import errors: `python -m omnibase_core`
- [ ] Verify no regressions in downstream code
- [ ] Update any affected documentation

---

## Validation Scripts

### Check for remaining Any usage:
```bash
grep -r ":\s*Any" src/omnibase_core/models --include="*.py" | wc -l
```

### Check for status: str patterns:
```bash
grep -r "status:\s*str" src/omnibase_core/models --include="*.py"
```

### Verify enum usage:
```bash
grep -r "from omnibase_core.enums" src/omnibase_core/models --include="*.py" | wc -l
```

---

## Quick Reference: Available Enums

Here are enums that already exist and should be used:

| Enum Name | Purpose | File |
|-----------|---------|------|
| EnumWorkflowType | Workflow types | enum_workflow_type.py |
| EnumEventType | Event types | enum_event_type.py |
| EnumExecutionMode | Execution modes | enum_execution_mode.py |
| EnumDataFormat | Data formats | enum_data_format.py |
| EnumSeverityLevel | Severity levels | enum_severity_level.py |
| EnumDataType | Data types | enum_data_type.py |
| EnumDeprecationStatus | Deprecation status | enum_deprecation_status.py |
| EnumMetadataNodeStatus | Metadata node status | enum_metadata_node_status.py |
| EnumOperationType | Operation types | enum_operation_type.py |
| EnumNodeType | Node types | enum_node_type.py |
| EnumStatus | Generic status | enum_status.py |
| EnumExecutionStatus | Execution status | enum_execution_status.py |

**Total Available:** 138 enums in `/root/repo/src/omnibase_core/enums/`

---

*This document provides specific, actionable fixes. Start with CRITICAL items and work down.*
