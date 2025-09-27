# Archive Migration Tracking

## Overview
This document tracks files migrated from `archived/` to `src/omnibase_core/` for future cleanup.

**Migration Strategy**:
- ✅ **MOVE + MODERNIZE** files to active codebase
- 📝 **TRACK** in this document for batch cleanup later
- 🚫 **NO immediate deletion** to avoid bloating PR sizes

## Current Migration Status

### ✅ Successfully Migrated Files

#### Subcontract Models (Target: `src/omnibase_core/models/contracts/subcontracts/`)
*Migration Date: 2025-09-25*

**Files Migrated**: 8/8 ✅ **COMPLETE**
- [✅] `archived/src/omnibase_core/core/subcontracts/model_aggregation_subcontract.py` → `src/omnibase_core/models/contracts/subcontracts/model_aggregation_subcontract.py` (2025-09-25)
- [✅] `archived/src/omnibase_core/core/subcontracts/model_caching_subcontract.py` → `src/omnibase_core/models/contracts/subcontracts/model_caching_subcontract.py` (2025-09-25)
- [✅] `archived/src/omnibase_core/core/subcontracts/model_configuration_subcontract.py` → `src/omnibase_core/models/contracts/subcontracts/model_configuration_subcontract.py` (2025-09-25)
- [✅] `archived/src/omnibase_core/core/subcontracts/model_event_type_subcontract.py` → `src/omnibase_core/models/contracts/subcontracts/model_event_type_subcontract.py` (2025-09-25)
- [✅] `archived/src/omnibase_core/core/subcontracts/model_fsm_subcontract.py` → `src/omnibase_core/models/contracts/subcontracts/model_fsm_subcontract.py` (2025-09-25)
- [✅] `archived/src/omnibase_core/core/subcontracts/model_routing_subcontract.py` → `src/omnibase_core/models/contracts/subcontracts/model_routing_subcontract.py` (2025-09-25)
- [✅] `archived/src/omnibase_core/core/subcontracts/model_state_management_subcontract.py` → `src/omnibase_core/models/contracts/subcontracts/model_state_management_subcontract.py` (2025-09-25)
- [✅] `archived/src/omnibase_core/core/subcontracts/model_workflow_coordination_subcontract.py` → `src/omnibase_core/models/contracts/subcontracts/model_workflow_coordination_subcontract.py` (2025-09-25)

#### Enum Dependencies (Target: `src/omnibase_core/enums/`)
*Migration Date: 2025-09-25*

**Files Migrated**: 1/1 ✅ **COMPLETE**
- [✅] `archived/src/omnibase_core/enums/enum_log_level.py` → `src/omnibase_core/enums/enum_log_level.py` (2025-09-25) - **DEPENDENCY RESOLUTION**

## 🗑️ Ready for Deletion Queue

### Subcontract Models - Migrated (2025-09-25)
- `archived/src/omnibase_core/core/subcontracts/model_aggregation_subcontract.py` ✅ **MIGRATED**
  - **Target**: `src/omnibase_core/models/contracts/subcontracts/model_aggregation_subcontract.py`
  - **Status**: Migration complete, ONEX compliant (modern type hints, Pydantic v2), structure validation passed, exports integrated
  - **Quality Metrics**: 7 classes migrated, zero tolerance Any types maintained, auto-integrated into __init__.py
  - **Ready for deletion**: Yes

- `archived/src/omnibase_core/core/subcontracts/model_caching_subcontract.py` ✅ **MIGRATED**
  - **Target**: `src/omnibase_core/models/contracts/subcontracts/model_caching_subcontract.py`
  - **Status**: Migration complete, validation passed, exports integrated
  - **Ready for deletion**: Yes

- `archived/src/omnibase_core/core/subcontracts/model_fsm_subcontract.py` ✅ **MIGRATED**
  - **Target**: `src/omnibase_core/models/contracts/subcontracts/model_fsm_subcontract.py`
  - **Status**: Migration complete, ONEX modernization applied (UUID correlation tracking), MyPy validation passed, exports integrated
  - **Ready for deletion**: Yes

- `archived/src/omnibase_core/core/subcontracts/model_event_type_subcontract.py` ✅ **MIGRATED**
  - **Target**: `src/omnibase_core/models/contracts/subcontracts/model_event_type_subcontract.py`
  - **Status**: Migration complete, ONEX compliant with strong typing, event handling patterns updated, MyPy validation passed, exports integrated
  - **Ready for deletion**: Yes

- `archived/src/omnibase_core/core/subcontracts/model_configuration_subcontract.py` ✅ **MIGRATED**
  - **Target**: `src/omnibase_core/models/contracts/subcontracts/model_configuration_subcontract.py`
  - **Status**: Migration complete, comprehensive ONEX modernization applied (UUID tracking, Path type integration, enhanced error context), MyPy validation passed, exports integrated
  - **Modernizations Applied**:
    - Added UUID correlation_id for configuration tracking
    - Added source_id UUID for configuration source tracking
    - Enhanced Path/str union type for source_path fields
    - Updated OnexError contexts with correlation tracking
    - Added UUID-based configuration source lookup methods
  - **Ready for deletion**: Yes

- `archived/src/omnibase_core/core/subcontracts/model_state_management_subcontract.py` ✅ **MIGRATED**
  - **Target**: `src/omnibase_core/models/contracts/subcontracts/model_state_management_subcontract.py`
  - **Status**: Migration complete, comprehensive ONEX modernization applied (Enum types, UUID correlation_id, Pydantic V2 ConfigDict), MyPy validation passed, exports integrated
  - **Modernizations Applied**:
    - Added 9 enum types for string constants (storage backends, consistency levels, etc.)
    - Added UUID correlation_id for operation tracing
    - Updated to Pydantic V2 model_config pattern
    - Enhanced type safety throughout
  - **Ready for deletion**: Yes

### Enum Dependencies - Migrated (2025-09-25)
- `archived/src/omnibase_core/enums/enum_log_level.py` ✅ **MIGRATED**
  - **Target**: `src/omnibase_core/enums/enum_log_level.py`
  - **Status**: Migration complete, dependency resolution successful, comprehensive import testing passed
  - **Migration Type**: DEPENDENCY RESOLUTION - resolved ModuleNotFoundError in model_configuration_subcontract.py
  - **Integration**: Added to src/omnibase_core/enums/__init__.py imports and __all__ list
  - **Validation**: All 8 subcontracts importing successfully via poetry run python
  - **Enum Values**: 9 levels (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, SUCCESS, UNKNOWN)
  - **Ready for deletion**: Yes

### Batch Cleanup Commands (Future)
```bash
# When ready for cleanup (separate PR)
rm archived/src/omnibase_core/core/subcontracts/model_*.py
rm archived/src/omnibase_core/enums/enum_log_level.py

# Update this document after cleanup
```

## Import Path Migration Guidelines

### 🚫 BLOCKED Import Patterns (Prevented by Pre-commit Hook)

During the migration transition, the following import patterns are **automatically blocked** by the `validate-archived-imports` pre-commit hook:

#### ❌ Critical - Archived Directory Imports
```python
# These will cause build failures
from archived.some_module import SomeClass
from archive.old_module import OldFunction
import archived.utils
import archive.helpers
```

#### ❌ High Priority - Old Migrated Paths
```python
# These paths have been migrated to new locations
from omnibase_core.core.contracts.model_contract_base import ModelContractBase
from omnibase_core.core.mixins.some_mixin import SomeMixin
from omnibase_core.core.subcontracts.model_aggregation_subcontract import AggregationSubcontract
```

### ✅ CORRECT Import Patterns

#### ✅ Current Active Paths
```python
# Use these paths for migrated content
from omnibase_core.models.contracts.subcontracts.model_aggregation_subcontract import AggregationSubcontract
from omnibase_core.models.base import BaseModel
from omnibase_core.types.common import CommonTypes
from omnibase_core.enums.enum_log_level import LogLevel
from omnibase_core.utils import UtilityFunction
import omnibase_core.exceptions
```

### 🔧 Migration Path Mapping

| Old Path (Blocked) | New Path (Current) | Status |
|-------------------|-------------------|---------|
| `from archived.src.omnibase_core.core.subcontracts.*` | `from omnibase_core.models.contracts.subcontracts.*` | ✅ Migrated |
| `from omnibase_core.core.contracts.*` | `from omnibase_core.models.*` or `omnibase_core.types.*` | 🚧 Migration in progress |
| `from omnibase_core.core.mixins.*` | `from omnibase_core.models.*` or updated patterns | 🚧 Migration in progress |
| `from archived.src.omnibase_core.enums.*` | `from omnibase_core.enums.*` | ✅ Migrated |

### 🛡️ Validation in Pre-commit Pipeline

The `validate-archived-imports` hook runs automatically on every commit to:
- **Prevent** accidental imports from `archived/` or `archive/` directories
- **Detect** usage of old migrated paths like `omnibase_core.core.contracts.*`  
- **Ensure** code follows current migration patterns
- **Provide** specific fix suggestions for each violation type

```yaml
# Enabled in .pre-commit-config.yaml
- id: validate-archived-imports
  name: ONEX Archived Path Import Prevention
  entry: poetry run python scripts/validation/validate-archived-imports.py
  args: ['src/']
  language: system
  pass_filenames: false
  files: ^.*\.py$
  exclude: ^(archived/|archive/|tests/fixtures/validation/).*$
  stages: [pre-commit]
```

### 📚 Quick Reference - Import Do's and Don'ts

#### ✅ DO
- Import from current active paths in `src/omnibase_core/`
- Use the pre-commit hook validation before committing
- Check migration mapping table above for correct paths
- Verify imports work with current codebase structure

#### ❌ DON'T  
- Import anything from `archived/` or `archive/` directories
- Use old `omnibase_core.core.contracts.*` paths
- Use old `omnibase_core.core.mixins.*` paths
- Skip the pre-commit validation

## Migration Guidelines

### ✅ File Successfully Migrated When:
1. File moved to correct `src/omnibase_core/` location
2. Imports modernized and MyPy compliant
3. ONEX naming/typing standards applied
4. Basic functionality validated
5. Added to project `__init__.py` exports
6. Checked into main branch

### 📋 Tracking Process:
1. **Before migration**: File listed as `[ ]` unchecked
2. **After migration**: File listed as `[✅]` with migration date
3. **Cleanup ready**: File moved to "Ready for Deletion Queue"
4. **Deleted**: File removed from tracking entirely

## Migration Statistics

- **Total Files Identified**: 1,854
- **Files Migrated**: 9 (8 subcontracts + 1 enum dependency)
- **Files Ready for Cleanup**: 9
- **Files Deleted**: 0
- **Migration Progress**: 0.49% (9/1854)
- **Dependency Resolution Success**: 100% (enum_log_level resolved)

## Next Migration Targets

1. **Subcontract Models** (8 files) - ✅ **COMPLETED**
2. **Enum Dependencies** (1 file) - ✅ **COMPLETED**
3. **Simple Utilities** (TBD)
4. **Configuration Models** (TBD)
5. **Complex Components** (See FUTURE_MIGRATION plans)

---
**Last Updated**: 2025-09-25
**Next Cleanup Planned**: After additional dependency migrations identified (if any)
