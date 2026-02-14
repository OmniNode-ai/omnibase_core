> **Navigation**: [Home](../INDEX.md) > Conventions > File Headers

# File Header Conventions

This document defines the canonical file header format for all Python files in the omnibase_core codebase. Consistent headers improve readability, enable automated tooling, and ensure compliance with Python standards.

---

## Table of Contents

1. [Overview](#overview)
2. [Canonical Format](#canonical-format)
3. [Key Rules](#key-rules)
4. [Examples by File Type](#examples-by-file-type)
5. [Validation](#validation)

---

## Overview

File headers in omnibase_core follow a strict ordering to ensure:

- **PEP 257 compliance**: Module docstrings appear first for documentation tools
- **Future-proof typing**: `from __future__ import annotations` enables PEP 604 union syntax everywhere
- **Consistent import order**: Standard library, third-party, then local imports (enforced by ruff I001/I002)
- **Automated validation**: Pre-commit hooks detect violations automatically

---

## Canonical Format

Every Python file in `src/omnibase_core/` MUST follow this structure:

```python
"""
Module docstring (PEP 257 format).

Additional description if needed. Keep concise (3-6 lines for simple modules).
"""

from __future__ import annotations

# Standard library imports
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

# Third-party imports
from pydantic import BaseModel, ConfigDict, Field

# Conditional imports for type checking only
if TYPE_CHECKING:
    from some_module import SomeType

# Local imports
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class MyClass:
    """Class docstring."""
    pass


__all__ = ["MyClass"]
```

---

## Key Rules

### 1. Module Docstring Comes First

The module docstring MUST be the very first statement in the file (before any imports).

```python
# CORRECT
"""Module description."""

from __future__ import annotations

# WRONG - Import before docstring
from __future__ import annotations

"""Module description."""  # This becomes a string literal, not a docstring
```

### 2. `from __future__ import annotations` Must Follow Docstring

This import MUST appear immediately after the module docstring. It enables:

- PEP 604 union syntax (`str | None` instead of `Optional[str]`)
- Forward references without quotes
- Consistent typing behavior across the codebase

```python
"""Module docstring."""

from __future__ import annotations  # MUST be here, right after docstring

from typing import TYPE_CHECKING  # Other imports follow
```

### 3. Import Order (Enforced by Ruff)

Imports MUST be ordered in these groups, separated by blank lines:

| Order | Group | Examples |
|-------|-------|----------|
| 1 | Standard library | `from collections.abc import Callable`, `from datetime import datetime` |
| 2 | Third-party | `from pydantic import BaseModel`, `from fastapi import FastAPI` |
| 3 | TYPE_CHECKING block | `if TYPE_CHECKING:` with conditional imports |
| 4 | Local/first-party | `from omnibase_core.enums import EnumNodeKind` |

**Note**: The `TYPE_CHECKING` block can appear within the third-party or local sections depending on what it imports.

### 4. Explicit Exports

Files SHOULD end with an `__all__` list for explicit public API declaration:

```python
__all__ = ["MyClass", "my_function"]
```

---

## Examples by File Type

### Enum Files

```python
"""
Node Kind Enum.

High-level architectural classification for ONEX nodes.

Defines 5 values: 4 core types (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR) plus
RUNTIME_HOST for infrastructure. The "four-node architecture" refers to the
core processing pipeline: EFFECT -> COMPUTE -> REDUCER -> ORCHESTRATOR.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeKind(StrValueHelper, str, Enum):
    """High-level architectural classification for ONEX four-node architecture."""

    EFFECT = "effect"
    COMPUTE = "compute"
    REDUCER = "reducer"
    ORCHESTRATOR = "orchestrator"
    RUNTIME_HOST = "runtime_host"


__all__ = ["EnumNodeKind"]
```

### Model Files

```python
"""
Generic container pattern for single-value models with metadata.

This module provides a reusable generic container that can replace
specialized single-value containers across the codebase, reducing
repetitive patterns while maintaining type safety.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelContainer[T](BaseModel):
    """Generic container for single values with metadata and validation."""

    value: T = Field(description="The contained value")

    model_config = ConfigDict(extra="ignore", validate_assignment=True)


__all__ = ["ModelContainer"]
```

### TypedDict Files

```python
"""
TypedDict for event information.
"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID


class TypedDictEventInfo(TypedDict):
    event_id: UUID
    event_type: str
    timestamp: datetime
    source: str
    correlation_id: NotRequired[UUID]
    sequence_number: NotRequired[int]


__all__ = ["TypedDictEventInfo"]
```

### Decorator Files

```python
"""
Standard error handling decorators for ONEX framework.

This module provides decorators that eliminate error handling boilerplate
and ensure consistent error patterns across all tools, especially important
for agent-generated tools.

All decorators in this module follow the ONEX exception handling contract:
- Cancellation/exit signals (SystemExit, KeyboardInterrupt, GeneratorExit,
  asyncio.CancelledError) ALWAYS propagate - they are never caught.
- ModelOnexError is always re-raised as-is to preserve error context.
- Other exceptions are wrapped in ModelOnexError with appropriate error codes.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


def standard_error_handling(operation_name: str) -> Callable[..., Any]:
    """Decorator that provides standard error handling for operations."""
    # Implementation...
    pass


__all__ = ["standard_error_handling"]
```

---

## Validation

### Pre-commit Hooks

File header conventions are enforced automatically by:

- **ruff I001**: Import block organization (sorting within groups)
- **ruff I002**: Missing required imports
- **ruff D100**: Missing module docstring (if docstring rules enabled)

### Manual Validation

Run the following to check compliance:

```bash
# Check import ordering
poetry run ruff check src/omnibase_core/ --select=I

# Auto-fix import issues
poetry run ruff check src/omnibase_core/ --select=I --fix

# Run all pre-commit hooks
pre-commit run --all-files
```

### Common Violations

| Violation | Fix |
|-----------|-----|
| Import before docstring | Move docstring to line 1 |
| Missing `from __future__ import annotations` | Add after docstring |
| Unsorted imports | Run `ruff check --fix` |
| Missing blank line between import groups | Run `ruff check --fix` |

---

## Related Documentation

- [Docstring Guidelines](../../CLAUDE.md#docstring-guidelines) - When and how to write docstrings
- [Import Policy](../../CLAUDE.md#import-policy) - Absolute vs relative imports
- [File Naming Conventions](../../CLAUDE.md#file-naming-conventions) - Directory-specific prefixes

---

**Last Updated**: 2026-01-14 | **Related PR**: #398 (Unified file headers across 225+ files)
