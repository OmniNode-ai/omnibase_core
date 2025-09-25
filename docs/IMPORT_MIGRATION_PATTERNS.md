# Import Migration Patterns - Developer Reference

## Overview

This document provides developers with clear guidance on import patterns during the ONEX migration transition period. All patterns are enforced by automated pre-commit validation.

## 🚫 Blocked Import Patterns

### Critical - Archived Path Imports (Immediate Failures)

These imports will cause **immediate build failures** and are blocked by pre-commit hooks:

```python
# ❌ NEVER - Direct archived imports
from archived.some_module import SomeClass
from archive.old_module import OldFunction
import archived.utils
import archive.helpers

# ❌ NEVER - Archived source paths
from archived.src.omnibase_core.core.contracts.model_contract_base import ModelContractBase
from archived.src.omnibase_core.core.subcontracts.model_aggregation_subcontract import AggregationSubcontract
```

### High Priority - Old Migration Paths

These paths have been migrated and should use new locations:

```python
# ❌ OLD PATHS - Use new locations instead
from omnibase_core.core.contracts.model_contract_base import ModelContractBase
from omnibase_core.core.contracts.model_dependency import ModelDependency  
from omnibase_core.core.mixins.some_mixin import SomeMixin
from omnibase_core.core.subcontracts.model_aggregation_subcontract import AggregationSubcontract
```

## ✅ Correct Import Patterns

### Current Active Imports

```python
# ✅ CORRECT - Migrated subcontract models
from omnibase_core.models.contracts.subcontracts.model_aggregation_subcontract import (
    AggregationSubcontract,
    AggregationConfig,
    AggregationStrategy
)
from omnibase_core.models.contracts.subcontracts.model_caching_subcontract import CachingSubcontract
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import FsmSubcontract

# ✅ CORRECT - Core models and types  
from omnibase_core.models.base import BaseModel
from omnibase_core.types.common import CommonTypes
from omnibase_core.types.identifiers import UUID, CorrelationId

# ✅ CORRECT - Enums (migrated)
from omnibase_core.enums.enum_log_level import LogLevel
from omnibase_core.enums.enum_node_type import NodeType

# ✅ CORRECT - Utilities and exceptions
from omnibase_core.utils.validation import validate_model
from omnibase_core.exceptions import OnexValidationError
import omnibase_core.core.decorators
```

## 🗺️ Migration Path Reference

### Subcontract Models (✅ Completed)

| Old Path | New Path |
|----------|----------|
| `archived.src.omnibase_core.core.subcontracts.model_aggregation_subcontract` | `omnibase_core.models.contracts.subcontracts.model_aggregation_subcontract` |
| `archived.src.omnibase_core.core.subcontracts.model_caching_subcontract` | `omnibase_core.models.contracts.subcontracts.model_caching_subcontract` |
| `archived.src.omnibase_core.core.subcontracts.model_configuration_subcontract` | `omnibase_core.models.contracts.subcontracts.model_configuration_subcontract` |
| `archived.src.omnibase_core.core.subcontracts.model_event_type_subcontract` | `omnibase_core.models.contracts.subcontracts.model_event_type_subcontract` |
| `archived.src.omnibase_core.core.subcontracts.model_fsm_subcontract` | `omnibase_core.models.contracts.subcontracts.model_fsm_subcontract` |
| `archived.src.omnibase_core.core.subcontracts.model_routing_subcontract` | `omnibase_core.models.contracts.subcontracts.model_routing_subcontract` |
| `archived.src.omnibase_core.core.subcontracts.model_state_management_subcontract` | `omnibase_core.models.contracts.subcontracts.model_state_management_subcontract` |
| `archived.src.omnibase_core.core.subcontracts.model_workflow_coordination_subcontract` | `omnibase_core.models.contracts.subcontracts.model_workflow_coordination_subcontract` |

### Enums (✅ Completed)

| Old Path | New Path |
|----------|----------|
| `archived.src.omnibase_core.enums.enum_log_level` | `omnibase_core.enums.enum_log_level` |

### Contracts & Mixins (🚧 In Progress)

| Old Path | Likely New Path | Status |
|----------|-----------------|---------|
| `omnibase_core.core.contracts.*` | `omnibase_core.models.*` or `omnibase_core.types.*` | Migration planned |
| `omnibase_core.core.mixins.*` | `omnibase_core.models.*` or updated patterns | Migration planned |

## 🛡️ Pre-commit Validation

### Automatic Validation Hook

Every commit is automatically validated for proper import patterns:

```bash
# Runs automatically on commit
pre-commit run validate-archived-imports --all-files

# Manual validation  
python scripts/validation/validate-archived-imports.py src/
```

### Validation Output Example

```bash
🔍 ONEX Archived Import Validation Report
==================================================
Found 7 archived import violations:

🚨 CRITICAL (5 violations)
  📋 Direct Archived Import (1 files)
    📄 my_module.py:2
       Import: from archived.some_module import SomeClass
       Fix: Use the migrated path or current implementation

⚠️ HIGH (2 violations)  
  📋 Old Contract Path (1 files)
    📄 my_module.py:4
       Import: from omnibase_core.core.contracts.model_contract_base import ModelContractBase
       Fix: Use new contract paths: from omnibase_core.models.* or omnibase_core.types.*
```

## 🔧 Common Migration Scenarios

### Scenario 1: Migrating Subcontract Usage

**Before:**
```python
# ❌ OLD - Will be blocked
from omnibase_core.core.subcontracts.model_aggregation_subcontract import AggregationSubcontract
```

**After:**
```python  
# ✅ NEW - Correct path
from omnibase_core.models.contracts.subcontracts.model_aggregation_subcontract import AggregationSubcontract
```

### Scenario 2: Migrating Enum Usage

**Before:**
```python
# ❌ OLD - Will be blocked if importing from archived
from archived.src.omnibase_core.enums.enum_log_level import LogLevel
```

**After:**
```python
# ✅ NEW - Current path
from omnibase_core.enums.enum_log_level import LogLevel
```

### Scenario 3: Bulk Import Updates

For files with multiple old imports, use the validation script output to identify all necessary changes:

```bash
# Get comprehensive report with fix suggestions
python scripts/validation/validate-archived-imports.py src/ --max-violations 100
```

## 🚨 Troubleshooting

### Import Errors During Development

1. **ModuleNotFoundError**: Check if path uses old patterns
   ```bash
   # Validate your imports
   python scripts/validation/validate-archived-imports.py src/
   ```

2. **Pre-commit Hook Failures**: Review the validation output and fix blocked patterns
   ```bash
   # See what's blocking your commit
   pre-commit run validate-archived-imports --files your_file.py
   ```

3. **Uncertain About Correct Path**: Check migration mapping tables above or reference existing working imports in similar files

### Getting Help

1. **Check Migration Status**: Review [MIGRATION_TRACKING.md](../MIGRATION_TRACKING.md) for latest migration status
2. **Validate Pattern**: Use the validation script to check if your pattern is correct
3. **Reference Working Examples**: Look at recently migrated files for correct import patterns

## ⚡ Quick Commands

```bash
# Validate all source files
python scripts/validation/validate-archived-imports.py src/

# Run pre-commit hook manually
pre-commit run validate-archived-imports --all-files

# Check specific file
python scripts/validation/validate-archived-imports.py path/to/your/file.py

# Get verbose output for debugging
python scripts/validation/validate-archived-imports.py src/ --verbose --max-violations 50
```

---

**Last Updated**: 2025-09-25
**Related Documentation**:
- [MIGRATION_TRACKING.md](../MIGRATION_TRACKING.md) - Overall migration progress
- [.pre-commit-config.yaml](../.pre-commit-config.yaml) - Pre-commit hook configuration
- [scripts/validation/validate-archived-imports.py](../scripts/validation/validate-archived-imports.py) - Validation script source
