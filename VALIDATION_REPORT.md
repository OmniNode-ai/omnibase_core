# Validation Report - Domain Reorganization ONEX 2.0

**Date**: 2025-10-02
**Branch**: refactor/domain-reorganization-onex-2.0
**Status**: ❌ CRITICAL ISSUES FOUND

## Executive Summary

The migration has introduced several critical issues that prevent the codebase from functioning:

1. **CRITICAL**: Recursive type definition causing infinite recursion in Pydantic
2. **CRITICAL**: Duplicate error files causing import confusion
3. **HIGH**: Circular import dependencies
4. **MEDIUM**: 131 naming convention violations
5. **MEDIUM**: 41 invalid union patterns
6. **LOW**: 3 NotImplementedError compliance issues (intentional stubs)

## Critical Issues

### 1. Infinite Recursion in Type Definitions

**Severity**: CRITICAL
**Status**: ❌ BLOCKING

**Problem**:
- The TypeAlias definitions for JsonSerializable, ValidationValue, and ResultValue are causing infinite recursion in Pydantic schema generation
- Affects: `src/omnibase_core/models/types/model_onex_common_types.py`
- Stack trace shows recursion in ModelGenericMetadata when processing recursive Union[list[...], dict[str, ...]] types

**Root Cause**:
```python
# This pattern causes infinite recursion in Pydantic:
JsonSerializable: TypeAlias = (
    str | int | float | bool
    | list["JsonSerializable"]  # Recursive without bound
    | dict[str, "JsonSerializable"]  # Recursive without bound
    | None
)
```

**Impact**: Cannot import any error modules or models

**Recommendation**:
- Replace recursive TypeAlias with bounded Pydantic models or use explicit depth limits
- Or use Any with runtime validation instead of recursive types

### 2. Duplicate/Inconsistent Error Files

**Severity**: CRITICAL
**Status**: ❌ BLOCKING

**Problem**:
- Inconsistent error file naming:
  - Git shows: `core_errors.py`, `document_freshness_errors.py`
  - Actual files: `error_codes.py`, `error_document_freshness.py`
  - Additional: `error_onex.py`, `onex_error.py`
- Imports reference non-existent files

**Files Affected**:
- `src/omnibase_core/__init__.py` imports from `error_onex`
- `src/omnibase_core/errors/error_document_freshness.py` imports from `error_onex`
- Validation scripts expect old names

**Recommendation**:
- Determine canonical file names
- Update git index to match actual files
- Update all imports consistently

### 3. Circular Import Dependencies

**Severity**: HIGH
**Status**: ⚠️  PARTIALLY FIXED

**Problem**:
- Circular dependency chain:
  1. `omnibase_core.errors.error_codes` → `omnibase_core.models.common.model_schema_value`
  2. `omnibase_core.models` → `omnibase_core.types.constraints`
  3. `omnibase_core.types.constraints` → `omnibase_core.errors.error_codes`

**Fix Applied**:
- Added TYPE_CHECKING guard and lazy imports in `types/constraints.py`

**Remaining Risk**:
- Fragile - any new direct imports will break
- Need architectural refactoring

## Medium Priority Issues

### 4. Naming Convention Violations

**Severity**: MEDIUM
**Status**: ⚠️  131 violations

**Categories**:
- 117 violations in archived/test files (acceptable)
- 14 violations in active codebase (need fixing)

**Active Violations**:
- Node* classes in `infrastructure/` should be in `nodes/` (warnings, not errors)
- Test models not following Model* prefix

### 5. Invalid Union Patterns

**Severity**: MEDIUM  
**Status**: ⚠️  41 patterns flagged

**Issues**:
- Some false positives (`correlation_id: str | UUID | None` is acceptable)
- Genuine primitive soup needs ModelSchemaValue

## Low Priority Issues

### 6. NotImplementedError Compliance

**Severity**: LOW
**Status**: ✅ ACCEPTABLE

- Lines 117, 122, 127 in `error_codes.py`
- All have `# stub-ok: abstract method` markers
- Validation script should respect these markers

## Passed Validations

✅ **Archived Imports**: No violations
✅ **Syntax**: PEP 695 → TypeAlias conversion successful
✅ **Import Patterns**: Ruff checks pass

## Action Plan

### Immediate (Blocking)

1. **Fix Recursive Types**: Replace with bounded models or Any
2. **Consolidate Error Files**: Resolve naming inconsistencies
3. **Test Imports**: Verify all modules import successfully

### Short Term

4. **Fix Active Naming**: 14 violations in infrastructure/
5. **Review Unions**: Validate primitive soup patterns

### Medium Term

6. **Refactor Dependencies**: Break error ↔ model ↔ type cycle

## Files Modified

- ✅ `model_onex_common_types.py` - Fixed PEP 695 syntax
- ✅ `constraints.py` - Fixed circular import
- ✅ `errors/__init__.py` - Added exports
- ❌ Recursive type issue unresolved
- ❌ File naming inconsistencies unresolved
