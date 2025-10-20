# Import Migration Patterns - omnibase_core

**Status**: ✅ Available

## Overview

Guide for migrating import statements to new consolidated module structure.

## Import Restructuring

### Old Import Structure (Scattered)

```python
# Old scattered imports
from omnibase_core.nodes.effect.node_effect_service import NodeEffectService
from omnibase_core.nodes.compute.node_compute_service import NodeComputeService
from omnibase_core.nodes.reducer.node_reducer_service import NodeReducerService
from omnibase_core.nodes.orchestrator.node_orchestrator_service import NodeOrchestratorService
```

### New Import Structure (Consolidated)

```python
# New consolidated imports
from omnibase_core.core.infrastructure_service_bases import (
    NodeEffectService,
    NodeComputeService,
    NodeReducerService,
    NodeOrchestratorService
)
```

## Migration Patterns

### Pattern 1: Node Base Classes

**Before**:
```python
from omnibase_core.nodes.compute.node_compute_service import NodeComputeService
```

**After**:
```python
from omnibase_core.core.infrastructure_service_bases import NodeComputeService
```

### Pattern 2: Models

**Before**:
```python
from omnibase_core.models.event.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.health.model_health_status import ModelHealthStatus
```

**After**:
```python
from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_health_status import ModelHealthStatus
```

### Pattern 3: Enums

**Before**:
```python
from omnibase_core.enums.node.enum_node_type import EnumNodeType
from omnibase_core.enums.health.enum_health_status import EnumHealthStatus
```

**After**:
```python
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_health_status import EnumHealthStatus
```

### Pattern 4: Container

**Before**:
```python
from omnibase_core.container.onex_container import ONEXContainer
```

**After**:
```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
```

### Pattern 5: Exceptions

**Before**:
```python
from omnibase_core.exceptions.onex_error import OnexError
```

**After**:
```python
from omnibase_core.exceptions.base_onex_error import OnexError
```

## Automated Migration

### Using sed (Unix/Linux/Mac)

```bash
# Migrate node base class imports
sed -i 's/from omnibase_core\.nodes\..*/from omnibase_core.core.infrastructure_service_bases import/g' **/*.py

# Migrate container imports
sed -i 's/from omnibase_core\.container\.onex_container import ONEXContainer/from omnibase_core.models.container.model_onex_container import ModelONEXContainer/g' **/*.py
```

### Using Python Script

```python
import re
from pathlib import Path

def migrate_imports(file_path: Path) -> None:
    """Migrate imports in a Python file."""
    content = file_path.read_text()

    # Migration rules
    replacements = {
        r'from omnibase_core\.nodes\..*\.node_.*_service import':
            'from omnibase_core.core.infrastructure_service_bases import',
        r'from omnibase_core\.container\.onex_container import ONEXContainer':
            'from omnibase_core.models.container.model_onex_container import ModelONEXContainer',
    }

    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)

    file_path.write_text(content)

# Usage
for py_file in Path('src').rglob('*.py'):
    migrate_imports(py_file)
```

## Verification

### Check Import Validity

```bash
# Type check to verify imports
poetry run mypy src/

# Import check
poetry run python -c "from omnibase_core.core.infrastructure_service_bases import NodeComputeService; print('✅ Imports OK')"
```

## Common Issues

### Issue: Import Not Found

**Error**: `ModuleNotFoundError: No module named 'omnibase_core.nodes.compute'`

**Solution**: Update to consolidated imports.

### Issue: Circular Import

**Problem**: Circular dependencies after restructuring.

**Solution**: Use TYPE_CHECKING for forward references:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
```

## Next Steps

- [Migration Guide](MIGRATION_GUIDE.md) - Complete migration guide
- [TypedDict Consolidation](TYPEDDICT_CONSOLIDATION.md)
- [Type System](../architecture/type-system.md)

---

**Related Documentation**:
- [Development Workflow](../guides/development-workflow.md)
