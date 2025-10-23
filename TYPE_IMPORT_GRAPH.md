# Type Import Graph Analysis

**Phase**: 0.3 - Type Import Mapping and Dependency Analysis
**Date**: 2025-10-22
**Project**: omnibase_core (Python 3.12+)
**Status**: Complete

## Executive Summary

This document provides a comprehensive analysis of type imports, dependency patterns, and circular dependency management in the omnibase_core project. The codebase demonstrates sophisticated import management with explicit circular dependency breaking through TYPE_CHECKING guards, lazy loading, and careful module organization.

### Key Statistics

| Metric | Value | Notes |
|--------|-------|-------|
| Total Python files | 1,848 | Across all modules |
| Type import statements | 1,625 | `from typing import` and `from...Type` |
| TYPE_CHECKING blocks | 210 | Used for circular dependency prevention |
| Future annotations usage | 441 files | Modern Python 3.10+ `from __future__ import annotations` |
| Old-style Union[] | 44 files | Legacy syntax, needs migration |
| New-style pipe unions | 147,915 lines | Modern PEP 604 `X \| Y` syntax |
| SPI protocol imports | 62 | External protocol dependencies |
| Package __init__ files | 54 | Module organization points |
| Files with __all__ exports | 489 | Explicit export control |
| Type definition files | 90 | In types/ directory |
| Enum definition files | 299 | In enums/ directory |

## Directory Structure

```
src/omnibase_core/
├── constants/          # Constants and configuration values
├── container/          # Dependency injection container
├── decorators/         # Function and class decorators
├── discovery/          # Service discovery mechanisms
├── enums/              # 299 enum definitions (isolated, no dependencies)
├── errors/             # Error handling and exception hierarchy
├── infrastructure/     # Infrastructure services and base classes
├── logging/            # Structured logging system
├── mixins/             # 48 reusable mixin classes
├── models/             # Domain models (39 subpackages)
│   ├── configuration/
│   ├── contracts/
│   ├── core/
│   ├── events/
│   ├── security/
│   └── ... (30+ more subpackages)
├── nodes/              # ONEX node implementations (29 files)
├── primitives/         # Primitive types (SemVer, etc.)
├── types/              # 90 TypedDict and type constraint definitions
├── utils/              # Utility functions and helpers
└── validation/         # Validation framework and utilities
```

## Import Pattern Analysis

### 1. Standard Library Imports

**Pattern**: Direct imports at module level
**Location**: Throughout codebase
**Risk**: None (no circular dependency risk)

**Common patterns**:
```python
import asyncio
import json
import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict
from uuid import UUID, uuid4
```

**Statistics**:
- `collections.abc` imports: Used for modern Callable type hints
- Standard library: Safe for direct import at module level

### 2. Typing Imports

**Primary sources**:
- `typing` module (standard library)
- `collections.abc` (modern Python 3.9+ collections)
- `omnibase_spi.protocols.types` (external SPI protocols)

**Modern typing patterns** (PEP 604):
```python
# ✅ PREFERRED - Modern pipe union syntax
result: str | int | None
values: list[str] | dict[str, Any]

# ❌ OLD STYLE - 44 files still using this
from typing import Union
result: Union[str, int, None]
```

**Recommendation**: Migrate remaining 44 files to modern pipe union syntax.

### 3. TYPE_CHECKING Pattern

**Purpose**: Break circular dependencies at import time while maintaining type safety
**Usage**: 210 files use TYPE_CHECKING blocks
**Pattern**:

```python
from typing import TYPE_CHECKING

# Runtime imports - available during execution
from omnibase_core.errors.error_codes import EnumCoreErrorCode

# Type-only imports - only available to type checkers (mypy, IDEs)
if TYPE_CHECKING:
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
    from omnibase_core.validation.validation_utils import ValidationResult

# Usage in type hints (works because TYPE_CHECKING is True for type checkers)
def handle_event(envelope: "ModelEventEnvelope") -> None:
    ...
```

**When to use TYPE_CHECKING**:
- Importing from modules that would create circular dependencies
- Forward references to classes not yet defined
- Type hints that are only needed for static analysis

### 4. Forward References (String Annotations)

**Pattern**: Type hints as strings to defer evaluation
**Purpose**: Avoid circular imports and reference types not yet defined

```python
# Forward reference using string annotation
def process_data(metadata: "ModelSemVer") -> "ValidationResult":
    ...

# Alternative: Use future annotations (Python 3.10+)
from __future__ import annotations

def process_data(metadata: ModelSemVer) -> ValidationResult:
    ...
```

**Status**: 441 files use `from __future__ import annotations`

### 5. Lazy Loading Pattern

**Pattern**: Defer imports using `__getattr__` to break circular dependencies
**Example**: `types/constraints.py` (lines 124-156)

```python
if TYPE_CHECKING:
    # Type checkers see these imports
    BaseCollection = ModelBaseCollection
    BaseFactory = ModelBaseFactory
else:
    # Runtime uses lazy loading
    def __getattr__(name: str) -> object:
        if name in ("ModelBaseCollection", "ModelBaseFactory"):
            from omnibase_core.models.base import ModelBaseCollection, ModelBaseFactory
            globals()["ModelBaseCollection"] = ModelBaseCollection
            globals()["ModelBaseFactory"] = ModelBaseFactory
            return globals()[name]
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

**Why this works**:
1. Type checkers see the TYPE_CHECKING imports for static analysis
2. At runtime, the imports are deferred until the attribute is first accessed
3. By that time, the circular dependency chain is already broken

### 6. Protocol Imports

**Source**: `omnibase_spi.protocols.types` (external SPI package)
**Count**: 62 imports
**Purpose**: Define structural typing contracts

```python
from omnibase_spi.protocols.types import (
    ProtocolConfigurable,
    ProtocolExecutable,
    ProtocolIdentifiable,
    ProtocolMetadataProvider,
    ProtocolNameable,
    ProtocolSerializable,
    ProtocolValidatable,
)
```

**Benefits**:
- Clear interface contracts
- Duck typing with type safety
- No runtime dependency (structural typing)

## Circular Dependency Analysis

### Critical Import Chain

The project has carefully managed circular dependencies through strategic use of TYPE_CHECKING and lazy loading. The primary chain:

```
1. types.core_types (minimal types, no external dependencies)
   ↓
2. errors.error_codes → imports types.core_types
   ↓
3. models.common.model_schema_value → imports errors.error_codes
   ↓
4. types.constraints → TYPE_CHECKING import of errors.error_codes
   ↓
5. models.* → imports types.constraints
   ↓
6. types.constraints → lazy __getattr__ import of models.base
```

### Documented Circular Dependency Breaking

Three critical modules explicitly document their import constraints:

#### 1. `types/constraints.py` (lines 7-34)

```python
"""
IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports:
- typing, pydantic (standard library)
- No imports from omnibase_core at module level (to break circular chain)

Type-Only Imports (Protected by TYPE_CHECKING):
- omnibase_core.errors.error_codes (used only for type hints)
- omnibase_core.models.base (lazy loaded via __getattr__)

Critical Rules:
- NEVER add runtime imports from errors.error_codes at module level
- NEVER add runtime imports from models.* at module level
- All imports from omnibase_core MUST be TYPE_CHECKING or lazy
"""
```

#### 2. `errors/error_codes.py` (lines 19-40)

```python
"""
IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================

Safe Runtime Imports (OK to import at module level):
- omnibase_core.enums.* (no dependencies on this module)
- omnibase_core.types.core_types (minimal types, no dependencies)
- Standard library modules

Type-Only Imports (MUST use TYPE_CHECKING guard):
- omnibase_core.models.* (imports from types.constraints, which references this module)
- Any module that directly/indirectly imports from types.constraints

Import Chain:
1. types.core_types (minimal types, no external deps)
2. THIS MODULE (errors.error_codes) → imports types.core_types
3. models.common.model_schema_value → imports THIS MODULE
4. types.constraints → TYPE_CHECKING import of THIS MODULE
5. models.* → imports types.constraints

Breaking this chain (e.g., adding runtime import from models.*) will cause circular import!
"""
```

#### 3. `errors/model_onex_error.py` (lines 16-36)

Similar constraints documented for the error base class.

### Circular Dependency Prevention Strategies

#### Strategy 1: TYPE_CHECKING Guards

**When**: Imports needed only for type hints
**Pattern**:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

def process_event(envelope: "ModelEventEnvelope") -> None:
    ...
```

**Files using this**: 210 files

#### Strategy 2: Lazy Loading (__getattr__)

**When**: Attributes accessed infrequently or late in initialization
**Pattern**:
```python
def __getattr__(name: str) -> object:
    if name == "LazyClass":
        from .module import LazyClass
        globals()["LazyClass"] = LazyClass
        return LazyClass
    raise AttributeError(...)
```

**Examples**:
- `types/constraints.py` (ModelBaseCollection, ModelBaseFactory)
- `types/__init__.py` (constraint exports)

#### Strategy 3: Minimal __init__.py

**When**: Package initialization should not trigger heavy imports
**Pattern**: `models/__init__.py`

```python
# Package init kept intentionally light to avoid circular imports
# Callers should import concrete symbols from their modules directly
__all__ = [
    "cli", "common", "config", ...  # Names only, no imports
]
```

**Benefits**:
- Prevents cascading imports during package initialization
- Explicit import paths (e.g., `from omnibase_core.models.core.model_node import ModelNode`)
- No hidden dependencies

#### Strategy 4: Future Annotations

**When**: All type hints should be strings (Python 3.10+)
**Pattern**:
```python
from __future__ import annotations

# No need for string quotes - all annotations are automatically stringified
def process_data(metadata: ModelSemVer) -> ValidationResult:
    ...
```

**Usage**: 441 files (24% of codebase)
**Recommendation**: Enable in remaining files for consistency

## Import Organization Standards

### Import Order (PEP 8 + isort)

```python
# 1. Future imports
from __future__ import annotations

# 2. Standard library
import asyncio
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

# 3. Third-party libraries
from pydantic import BaseModel, Field

# 4. External protocols (SPI)
from omnibase_spi.protocols.types import ProtocolExecutable

# 5. Internal imports - errors and types (safe, no circular deps)
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.types.core_types import TypedDictBasicErrorContext

# 6. Internal imports - other modules
from omnibase_core.models.core.model_node import ModelNode

# 7. TYPE_CHECKING imports (circular dependency breaking)
if TYPE_CHECKING:
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
```

### Module Dependency Hierarchy

**Safe to import anywhere** (no circular dependency risk):
1. `enums/` - 299 enum files, completely isolated
2. `types/core_types.py` - Minimal types, no dependencies
3. `primitives/` - Basic types (SemVer, UUID wrappers)
4. `constants/` - Configuration constants

**Safe with constraints** (document import chains):
5. `errors/` - Use TYPE_CHECKING for model imports
6. `types/constraints.py` - Use lazy loading for models
7. `types/__init__.py` - Use lazy loading for constraints

**Import from these carefully** (potential circular deps):
8. `models/` - Large hierarchy, imports from many modules
9. `mixins/` - Often imports from models
10. `nodes/` - Top-level implementations, imports everything

### Export Control (__all__)

**Usage**: 489 files (26% of codebase)
**Purpose**: Explicit API surface control

**Best practices**:
```python
# Explicit exports
__all__ = [
    "ModelNode",
    "NodeConfig",
    "create_node",
]

# Benefits:
# 1. Clear public API
# 2. Prevents accidental internal usage
# 3. Helps IDEs with auto-import
# 4. Documents intended usage
```

## TypedDict Usage Patterns

### TypedDict Files

**Location**: `types/` directory
**Count**: 90 files
**Pattern**: One TypedDict per file

**Naming convention**:
```
typed_dict_<name>.py → TypedDict<Name>

Examples:
- typed_dict_operation_result.py → TypedDictOperationResult
- typed_dict_node_core.py → TypedDictNodeCore
- typed_dict_metadata_dict.py → TypedDictMetadataDict
```

### Common TypedDict Patterns

#### 1. Simple TypedDict
```python
from typing import TypedDict

class TypedDictOperationResult(TypedDict):
    success: bool
    message: str
    data: dict[str, Any]
```

#### 2. Optional Fields (NotRequired)
```python
from typing import NotRequired, TypedDict

class TypedDictFeatureFlags(TypedDict, total=False):
    enable_caching: NotRequired[bool]
    max_retries: NotRequired[int]
```

#### 3. Forward References
```python
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.primitives.model_semver import ModelSemVer

class TypedDictMetadataDict(TypedDict, total=False):
    version: "ModelSemVer"  # Forward reference
```

### TypedDict Benefits

1. **Type safety**: Structured dictionaries with type checking
2. **No runtime overhead**: Unlike Pydantic models
3. **Clear contracts**: Explicit structure for dict interfaces
4. **IDE support**: Auto-completion and type hints

## Enum Usage Patterns

### Enum Organization

**Location**: `enums/` directory
**Count**: 299 files
**Isolation**: No dependencies on other omnibase_core modules

**Benefits**:
- No circular dependency risk
- Safe to import anywhere
- Clear value definitions

**Naming convention**:
```
enum_<name>.py → Enum<Name>

Examples:
- enum_node_type.py → EnumNodeType
- enum_onex_status.py → EnumOnexStatus
- enum_execution_status_v2.py → EnumExecutionStatusV2
```

## Best Practices Summary

### ✅ DO

1. **Use TYPE_CHECKING for circular imports**
   ```python
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from .heavy_module import HeavyClass
   ```

2. **Use modern pipe union syntax**
   ```python
   result: str | int | None
   ```

3. **Use future annotations**
   ```python
   from __future__ import annotations
   ```

4. **Document critical import chains**
   ```python
   """
   IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
   ...
   """
   ```

5. **Keep __init__.py minimal**
   ```python
   __all__ = ["name1", "name2"]  # Names only, no imports
   ```

6. **Use explicit __all__ exports**
   ```python
   __all__ = ["PublicClass", "public_function"]
   ```

7. **Import from specific modules**
   ```python
   from omnibase_core.models.core.model_node import ModelNode
   ```

8. **Use lazy loading for circular deps**
   ```python
   def __getattr__(name: str) -> object:
       if name == "LazyClass":
           from .module import LazyClass
           return LazyClass
   ```

### ❌ DON'T

1. **Don't import models in types/constraints.py at module level**
   ```python
   # ❌ BAD - Creates circular dependency
   from omnibase_core.models.base import ModelBaseCollection

   # ✅ GOOD - Use TYPE_CHECKING or lazy loading
   if TYPE_CHECKING:
       from omnibase_core.models.base import ModelBaseCollection
   ```

2. **Don't use old Union syntax**
   ```python
   # ❌ BAD - Old style
   from typing import Union
   result: Union[str, int]

   # ✅ GOOD - Modern style
   result: str | int
   ```

3. **Don't import * (star imports)**
   ```python
   # ❌ BAD - Implicit imports
   from omnibase_core.models import *

   # ✅ GOOD - Explicit imports
   from omnibase_core.models.core.model_node import ModelNode
   ```

4. **Don't break documented import chains**
   ```python
   # If a module documents "NEVER import from models.*"
   # DON'T add runtime imports from models
   ```

5. **Don't create heavy __init__.py files**
   ```python
   # ❌ BAD - Triggers cascading imports
   from .submodule1 import Class1
   from .submodule2 import Class2
   # ... 50 more imports

   # ✅ GOOD - Minimal __init__.py
   __all__ = ["submodule1", "submodule2"]
   ```

## Circular Dependency Inventory

### Identified Circular Dependencies

Based on analysis, the following circular dependencies are managed:

#### 1. types.constraints ↔ models.base
**Status**: ✅ Resolved via lazy loading
**Pattern**: __getattr__ in types/constraints.py
**Files**: types/constraints.py (lines 124-156)

#### 2. errors ↔ models
**Status**: ✅ Resolved via TYPE_CHECKING
**Pattern**: TYPE_CHECKING guards in error modules
**Files**: errors/error_codes.py, errors/model_onex_error.py

#### 3. types ↔ models
**Status**: ✅ Resolved via TYPE_CHECKING
**Pattern**: Forward references with TYPE_CHECKING
**Files**: Multiple TypedDict files in types/

#### 4. mixins ↔ models.events
**Status**: ✅ Resolved via TYPE_CHECKING
**Pattern**: Event envelope imports under TYPE_CHECKING
**Files**: Multiple mixin files

### No Circular Dependencies Found

The following module pairs do NOT have circular dependencies:

- ✅ enums ↔ anything (enums are isolated)
- ✅ primitives ↔ models (one-way dependency)
- ✅ constants ↔ anything (constants are leaf nodes)
- ✅ utils ↔ types (clean one-way dependency)

## Import Best Practices for Phases 1-4

### Phase 1: Type Cleanup

1. **Migrate remaining 44 files to pipe unions**
   - Search: `Union\[`
   - Replace: `X | Y` syntax
   - Verify: `poetry run mypy src/`

2. **Add future annotations to remaining files**
   - Add: `from __future__ import annotations`
   - Target: 1848 - 441 = 1407 files
   - Benefit: Cleaner type hints, reduced circular deps

3. **Standardize TYPE_CHECKING usage**
   - Review 210 TYPE_CHECKING blocks
   - Ensure consistent patterns
   - Document any new circular deps

### Phase 2: Import Organization

1. **Enforce isort compliance**
   ```bash
   poetry run isort src/ tests/
   ```

2. **Add __all__ to files without it**
   - Current: 489/1848 = 26%
   - Target: 80%+ for public modules
   - Tool: `poetry run python -m scripts.add_all_exports`

3. **Document additional import chains**
   - Find complex import relationships
   - Add docstrings like errors/error_codes.py
   - Create import chain diagrams

### Phase 3: Circular Dependency Elimination

1. **Audit remaining circular deps**
   ```bash
   # Use tools like pydeps or import-linter
   poetry run pydeps src/omnibase_core --show-cycles
   ```

2. **Refactor if necessary**
   - Extract interfaces to separate modules
   - Move shared types to core_types.py
   - Use dependency inversion

3. **Add CI checks**
   ```yaml
   - name: Check for circular imports
     run: poetry run import-linter --config .import-linter.ini
   ```

### Phase 4: Type System Hardening

1. **Enable strict mypy**
   ```toml
   [tool.mypy]
   strict = true
   warn_unused_ignores = true
   disallow_any_generics = true
   ```

2. **Add runtime type checking**
   - Consider: typeguard, beartype
   - Pattern: Validate at boundaries
   - Focus: External inputs, API responses

3. **Protocol usage expansion**
   - Convert ABCs to Protocols where appropriate
   - Reduce runtime coupling
   - Improve testability

## Import Anti-Patterns Found

### 1. Some Old Union Syntax (44 files)
**Issue**: `Union[X, Y]` instead of `X | Y`
**Fix**: Migrate to modern syntax
**Impact**: Low (works fine, but less readable)

### 2. Inconsistent future annotations usage
**Issue**: Only 24% of files use `from __future__ import annotations`
**Fix**: Add to remaining files
**Impact**: Medium (reduces circular import risk)

### 3. No automated circular dependency checks
**Issue**: Manual tracking of circular deps
**Fix**: Add import-linter to CI
**Impact**: High (prevents regressions)

## Recommendations for Type Import Management

### Short-term (Phase 1-2)

1. ✅ Migrate remaining 44 files from `Union[X, Y]` to `X | Y`
2. ✅ Add `from __future__ import annotations` to all files
3. ✅ Run `isort` and `black` on entire codebase
4. ✅ Add __all__ to public modules (target 80% coverage)

### Medium-term (Phase 3)

1. ✅ Add import-linter to CI for circular dependency checks
2. ✅ Create visual import dependency graphs
3. ✅ Document all critical import chains
4. ✅ Refactor any remaining problematic circular deps

### Long-term (Phase 4)

1. ✅ Enable strict mypy checking
2. ✅ Add runtime type validation at boundaries
3. ✅ Convert more ABCs to Protocols
4. ✅ Create import guidelines documentation

## Tools and Commands

### Analyzing Imports

```bash
# Count type imports
poetry run grep -r "from typing import" src/omnibase_core --include="*.py" | wc -l

# Find TYPE_CHECKING blocks
poetry run grep -r "if TYPE_CHECKING:" src/omnibase_core --include="*.py" -B 2 -A 5

# Find old Union syntax
poetry run grep -r "Union\[" src/omnibase_core --include="*.py"

# Find files without future annotations
poetry run grep -L "from __future__ import annotations" src/omnibase_core/**/*.py

# Check circular imports
poetry run pydeps src/omnibase_core --show-cycles

# Visualize import graph
poetry run pydeps src/omnibase_core --max-bacon=2 -o import_graph.svg
```

### Enforcing Standards

```bash
# Sort imports
poetry run isort src/ tests/

# Format code
poetry run black src/ tests/

# Type check
poetry run mypy src/omnibase_core

# Check import order and circular deps
poetry run import-linter --config .import-linter.ini
```

## Conclusion

The omnibase_core project demonstrates sophisticated circular dependency management through strategic use of TYPE_CHECKING guards, lazy loading, and minimal __init__.py files. The documented import chains in critical modules (types/constraints.py, errors/error_codes.py) provide clear guidance for maintaining the carefully constructed import hierarchy.

### Key Strengths

1. ✅ Explicit circular dependency documentation
2. ✅ Consistent TYPE_CHECKING usage (210 files)
3. ✅ Modern type hint syntax (147,915 pipe unions)
4. ✅ Isolated enums (no circular dependency risk)
5. ✅ Lazy loading pattern for breaking cycles
6. ✅ Minimal __init__.py files to prevent cascading imports

### Areas for Improvement

1. ⚠️ Migrate remaining 44 files from old Union syntax
2. ⚠️ Add future annotations to 1407 remaining files
3. ⚠️ Increase __all__ coverage from 26% to 80%+
4. ⚠️ Add automated circular dependency checks to CI
5. ⚠️ Create visual import dependency graphs

### Next Steps for Phases 1-4

**Phase 1 (Type Cleanup)**:
- Migrate Union[] to pipe unions
- Add future annotations
- Standardize TYPE_CHECKING patterns

**Phase 2 (Protocol Migration)**:
- Use import patterns as baseline
- Maintain TYPE_CHECKING usage
- Preserve circular dependency breaking

**Phase 3 (Validation)**:
- Test import changes don't break circular dependency management
- Verify TYPE_CHECKING still works
- Validate lazy loading patterns

**Phase 4 (Finalization)**:
- Document new import patterns
- Add CI checks for import standards
- Create import best practices guide

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-22
**Maintainers**: omnibase_core development team
