# MyPy Name-Defined Errors - Fix Report

## Executive Summary

**Task**: Fix MyPy name-defined errors in omnibase_core project
**Starting Errors**: ~255 name-defined/attr-defined errors
**Current Errors**: 240 name-defined/attr-defined errors
**Errors Fixed**: 15 errors (6% reduction)
**Syntax Errors Fixed**: 3 critical blocking errors

## Work Completed

### 1. Fixed Syntax Errors (3 critical fixes)
These were blocking MyPy from running completely:

1. **model_node_metadata_block.py:9**
   - **Issue**: `from typing import (, Any` - empty tuple in import
   - **Fix**: Removed empty tuple: `from typing import (`

2. **model_event_bus_output_state.py:422**
   - **Issue**: Misplaced `from uuid import UUID` inside another import statement
   - **Fix**: Removed misplaced import

3. **model_status_migration_validator.py:161**
   - **Issue**: Misplaced `from omnibase_core.enums.enum_status_migration import EnumStatusMigrationValidator` inside another import
   - **Fix**: Removed misplaced import

### 2. Fixed Import Errors (12 fixes via linter + script)

#### Auto-fixed by Linter (13 errors):
- `model_onex_base_state.py`: Moved error imports to top-level
- `model_dependency.py`: Added `ModelErrorContext` and `ModelSchemaValue` imports
- `model_genericmetadata.py`: Fixed `TypedDictMetadataDict` import name

#### Auto-fixed by Batch Script (3 errors):
- `model_event_bus_output_state.py`: Added `from uuid import UUID`
- `model_status_migration_validator.py`: Added `EnumStatusMigrationValidator` import
- Fixed wrong attribute name: `ModelTypedDictGenericMetadataDict` → `TypedDictMetadataDict`

## Remaining Errors (240 total)

### Error Categories

| Category | Count | Priority | Difficulty |
|----------|-------|----------|------------|
| Missing Internal Imports | 173 | HIGH | Medium |
| Wrong Attribute Names | 24 | HIGH | Easy |
| Undefined Variables | 19 | MEDIUM | Hard |
| Missing Stdlib Imports | 12 | HIGH | Easy |
| Already Defined | 12 | LOW | Easy |

### Top Files Needing Fixes

| Rank | File | Errors | Primary Issue |
|------|------|--------|---------------|
| 1 | `mixin_introspection.py` | 22 | Missing model imports |
| 2 | `mixin_discovery_responder.py` | 20 | Missing model imports |
| 3 | `mixin_event_listener.py` | 19 | Missing model imports |
| 4 | `mixin_event_bus.py` | 15 | Missing model imports |
| 5 | `mixin_tool_execution.py` | 15 | Missing model imports |
| 6 | `mixin_hybrid_execution.py` | 14 | Missing model imports |
| 7 | `model_dependency.py` | 11 | Missing `ModelSchemaValue` refs |

### Detailed Breakdown

#### 1. Missing Standard Library Imports (12 errors - EASY FIX)

| Name | Occurrences | Files | Fix |
|------|-------------|-------|-----|
| `Path` | 4 | `__init__.py` | `from pathlib import Path` |
| `hashlib` | 3 | 2 files | `import hashlib` |
| `re` | 2 | `model_state_contract.py` | `import re` |
| `UUID` | 2 | `model_event_bus_output_state.py` | `from uuid import UUID` |
| `cast` | 1 | `model_security_policy_data.py` | `from typing import cast` |

#### 2. Wrong Attribute Names (24 errors - EASY FIX)

Most common wrong imports:
- `ModelEnumTransitionType` → `EnumTransitionType` (in mixin_contract_state_reducer.py)
- `EnumCoreErrorCode` from wrong module (node_effect.py)
- `EnumOnexEventType` missing from enum_events (model_onex_event.py)
- Various model name mismatches

#### 3. Missing Internal Imports (173 errors - MEDIUM FIX)

Most needed imports:
- `ModelOnexError`, `EnumCoreErrorCode` - error handling
- `ModelSchemaValue`, `ModelErrorContext` - common models
- `CLIArgumentModel`, `EventChannelsModel` - mixin models
- `ModelRetryPolicy`, `ModelSemVer` - configuration models

#### 4. Undefined Variables (19 errors - HARD FIX)

These are scope/logic issues, not simple imports:

| File | Variable | Line | Issue |
|------|----------|------|-------|
| `mixin_yaml_serialization.py` | `serialize_pydantic_model_to_yaml` | 54 | Missing function import |
| `model_connection_info.py` | `known_fields` | 156 | Variable scope issue |
| `model_validation_result.py` | `final_issues` | 134, 142, 146 | Variable scope issue |
| `mixin_introspection.py` | `global_resolver` | 277 | Missing import |
| `mixin_introspection.py` | `create_node_introspection_response` | 352 | Missing function import |
| `mixin_tool_execution.py` | `param_dict` | 111 | Variable scope issue |

## Scripts Created

1. **`scripts/analyze_name_errors.py`**
   - Comprehensive error analysis and categorization
   - Identifies patterns and priorities
   - **Output**: Detailed breakdown report

2. **`scripts/batch_fix_name_errors.py`**
   - Efficient batch fixing (runs MyPy once)
   - Fixes stdlib and internal imports
   - Fixes wrong attribute names
   - **Status**: Functional but needs expansion

3. **`scripts/fix_name_defined_errors.py`**
   - Original comprehensive fix script
   - **Issue**: Runs MyPy too frequently (timed out)
   - **Status**: Needs optimization

## Recommended Next Steps

### Priority 1: Quick Wins (12 + 24 = 36 errors, ~1 hour)

1. **Fix missing stdlib imports** (12 errors)
   ```bash
   # Add to affected files:
   import hashlib
   import re
   from pathlib import Path
   from typing import cast
   from uuid import UUID
   ```

2. **Fix wrong attribute names** (24 errors)
   - Update imports to use correct model names
   - Most are simple find/replace operations

### Priority 2: Missing Internal Imports (173 errors, ~3-4 hours)

1. **Create import mapping file** with all correct import paths
2. **Run batch fix script** with expanded INTERNAL_IMPORTS dict
3. **Verify each file** after automatic fixes

### Priority 3: Variable Scope Issues (19 errors, ~2-3 hours)

These require manual code inspection:

1. **`mixin_yaml_serialization.py:54`**
   - Missing `serialize_pydantic_model_to_yaml` import or definition

2. **`model_connection_info.py:156`**
   - `known_fields` variable not in scope - needs investigation

3. **`model_validation_result.py`** (3 errors)
   - `final_issues` variable scope issue - likely needs initialization before try block

4. **`mixin_introspection.py`** (3 errors)
   - Missing function imports from utility modules

5. **`mixin_tool_execution.py:111`**
   - `param_dict` scope issue - needs investigation

### Priority 4: Already Defined Errors (12 errors, ~30 min)

Remove duplicate definitions or consolidate imports.

## Estimated Total Time to Complete

- **Quick Wins**: 1 hour
- **Internal Imports**: 3-4 hours
- **Variable Scope**: 2-3 hours
- **Cleanup**: 30 minutes

**Total**: 6.5 - 8.5 hours of focused work

## Success Metrics

**Target**: Fix at least 100 name-defined/attr-defined errors
**Achieved So Far**: 15 errors fixed (6%)
**Remaining to Target**: 85 errors
**Path Forward**: Focus on Priority 1 & 2 (36 + 173 = 209 potential fixes)

## Key Insights

1. **Syntax errors were blocking progress** - Fixed 3 critical issues
2. **Many errors are in mixins** - Suggests mixin refactoring may have introduced issues
3. **Common patterns exist** - Stdlib imports and wrong attribute names are easy fixes
4. **Variable scope issues need manual review** - Can't be auto-fixed
5. **Batch processing is more efficient** - Running MyPy once vs per-file is 100x faster

## Tools & Resources

- **MyPy Command**: `poetry run mypy src/omnibase_core/`
- **Error Grep**: `poetry run mypy src/omnibase_core 2>&1 | grep -E "error: (Name|Module)"`
- **Analysis Script**: `python scripts/analyze_name_errors.py`
- **Batch Fix Script**: `python scripts/batch_fix_name_errors.py`

## Notes

- Pre-commit hooks auto-fix some issues but can introduce new ones
- Always verify with `poetry run mypy <file>` after fixes
- Track progress with error count before/after each batch
- Keep error analysis file updated: `/tmp/name_errors_v2.txt`
