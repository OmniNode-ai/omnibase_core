# Dict[str, Any] Prevention Guide

**Last Updated**: 2025-12-24
**Status**: Active Enforcement
**Error Code**: `[explicit-any]`

## Overview

This document describes the mypy configuration for preventing new usage of `dict[str, Any]` in the codebase. The goal is to improve type safety by encouraging developers to use more specific types.

## What is Enforced

The mypy option `disallow_any_explicit = True` is enabled globally. This catches:

1. **Explicit `Any` in type annotations**:
   ```python
   # ERROR: Explicit "Any" is not allowed [explicit-any]
   def process(data: dict[str, Any]) -> dict[str, Any]:
       ...
   ```

2. **`Any` as a return type**:
   ```python
   # ERROR: Explicit "Any" is not allowed [explicit-any]
   def get_value() -> Any:
       ...
   ```

3. **`Any` in class attributes**:
   ```python
   class MyClass:
       # ERROR: Explicit "Any" is not allowed [explicit-any]
       data: dict[str, Any]
   ```

## How to Fix Violations

### Option 1: Use Specific Types (Preferred)

Replace `dict[str, Any]` with a more specific type:

```python
# Instead of dict[str, Any], use:

# 1. TypedDict for known structure
from typing import TypedDict

class UserData(TypedDict):
    name: str
    age: int
    email: str

def process_user(data: UserData) -> UserData:
    ...

# 2. Specific dict types
def process_config(data: dict[str, str | int | bool]) -> dict[str, str]:
    ...

# 3. Pydantic models
from pydantic import BaseModel

class Config(BaseModel):
    setting: str
    value: int

def apply_config(config: Config) -> None:
    ...
```

### Option 2: Use SchemaDict or ModelSchemaValue (ONEX Standard)

For schema-related data, use the ONEX type aliases:

```python
# For dict[str, Any] replacement in schema contexts
from omnibase_core.types.type_schema_aliases import SchemaDict

def process_schema(data: SchemaDict) -> SchemaDict:
    ...

# For individual typed values
from omnibase_core.models.common import ModelSchemaValue

value: ModelSchemaValue = ModelSchemaValue.create_string("example")
```

### Option 3: Use @allow_dict_any Decorator (Last Resort)

If `dict[str, Any]` is truly unavoidable, document the justification:

```python
from omnibase_core.decorators import allow_dict_any

@allow_dict_any(reason="External API returns untyped JSON that varies by endpoint")
def fetch(self, endpoint: str) -> dict[str, Any]:  # type: ignore[explicit-any]
    ...
```

**Note**: Even with the decorator, you still need `# type: ignore[explicit-any]` for mypy. The decorator is for documentation and validation scripts.

## Legacy Code Exemptions

The following modules have legacy exemptions and are NOT checked for `explicit-any`:

| Module | Error Count | Notes |
|--------|-------------|-------|
| `omnibase_core.models.*` | ~1685 | Primary tech debt area |
| `omnibase_core.mixins.*` | ~114 | Mixin implementations |
| `omnibase_core.utils.*` | ~52 | Utility functions |
| `omnibase_core.logging.*` | ~23 | Logging infrastructure |
| `omnibase_core.decorators.*` | ~21 | Decorator implementations |
| `omnibase_core.infrastructure.*` | ~12 | Node infrastructure |
| `omnibase_core.errors.*` | ~12 | Error handling |
| `omnibase_core.types.*` | ~11 | Type definitions |
| `omnibase_core.runtime.*` | ~11 | Runtime components |
| `omnibase_core.protocols.*` | ~10 | Protocol definitions |
| `omnibase_core.nodes.*` | ~10 | Node implementations |
| `omnibase_core.container.*` | ~9 | DI container |
| `omnibase_core.services.*` | ~5 | Service layer |
| `omnibase_core.validation.*` | Various | Validation logic |
| `omnibase_core.tools.*` | Various | Development tools |
| `tests.*` | N/A | Test code |
| `scripts.*` | N/A | Build scripts |

### Rules for Legacy Exemptions

1. **DO NOT add new modules** to the exemption list
2. When modifying files in exempted modules, **migrate away from dict[str, Any]** where possible
3. New code in exempted modules should still avoid `dict[str, Any]` (honor the intent)
4. Remove modules from exemptions once fully migrated

## Configuration Details

### mypy.ini Settings

```ini
[mypy]
# Global enforcement
disallow_any_explicit = True

# Per-module exemptions for legacy code
[mypy-omnibase_core.models.*]
disallow_any_explicit = False

# ... (see mypy.ini for full list)
```

### pyproject.toml Settings

```toml
[tool.mypy]
disallow_any_explicit = true
```

## Migration Priority

When addressing tech debt, prioritize by impact:

1. **models/** (85% of violations) - Highest ROI
2. **mixins/** (6% of violations)
3. **utils/** (3% of violations)
4. **Other modules** (6% combined)

## Related Documentation

- [Type System Architecture](./TYPE_SYSTEM.md)
- [ModelSchemaValue Type Definition](../../src/omnibase_core/types/type_schema_aliases.py)
- [ONEX Terminology](../standards/onex_terminology.md)

## Verification

To verify the configuration is working:

```bash
# Check that legacy modules are exempted
poetry run mypy src/omnibase_core/models/ --show-error-codes 2>&1 | grep explicit-any
# Should show: (no output or very few errors)

# Check that new code is caught
echo 'from typing import Any
def test(x: dict[str, Any]) -> Any:
    pass' > /tmp/test_any.py
poetry run mypy /tmp/test_any.py --show-error-codes
# Should show: Explicit "Any" is not allowed [explicit-any]
```

## Changelog

- **2025-12-24**: Initial implementation
  - Enabled `disallow_any_explicit = True` globally
  - Added per-module exemptions for ~1972 legacy violations across ~1351 files
  - Created documentation
