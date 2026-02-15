> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Protocol Architecture

# Protocol Architecture Analysis
**Phase 0.2: Protocol Architecture Audit**
**Generated**: 2025-10-22
**Updated**: 2025-12-18
**Project**: omnibase_core (ONEX Framework)
**Codebase Size**: 1,848+ Python files

---

> **Note (v0.4.0 - Dependency Inversion)**: This document was originally written when
> `omnibase_core` depended on `omnibase_spi` for protocol definitions. As of v0.3.6, the
> dependency was **inverted** - SPI now depends on Core, not the reverse.
> **Current Architecture (v0.3.6+)**:
> - **omnibase_core.protocols** now defines Core-native protocol interfaces
> - **omnibase_spi** depends on Core and may extend protocols for cross-service use
> - **omnibase_infra** implements SPI protocols using transport libraries
> Historical references to "importing from omnibase_spi" should be understood as now
> importing from `omnibase_core.protocols`. See the [Import Compatibility Matrix](IMPORT_COMPATIBILITY_MATRIX.md)
> for the current import paths.

---

## Executive Summary

The omnibase_core project follows a **protocol-driven architecture** where:
- **omnibase_core.protocols** defines Core-native protocol interfaces (v0.3.6+)
- **omnibase_core** defines internal protocols for domain-specific needs
- Protocol-based dependency injection is used extensively (420+ method implementations)
- Strong typing with runtime-checkable protocols for structural subtyping

### Key Findings
✅ **Clean separation**: Core protocols now native to omnibase_core
✅ **Type safety**: Runtime-checkable protocols with type guards
✅ **Zero external dependencies**: Core protocols are self-contained
✅ **Dependency inversion**: SPI depends on Core (not reverse)
⚠️ **Limited documentation**: Protocol usage patterns not well documented
⚠️ **Discovery challenge**: Protocol implementations scattered across codebase

---

## Protocol Inventory

### 1. Internal Protocols (omnibase_core)

Total: **3 protocols**

#### 1.1 ProtocolPatternChecker
**Location**: `src/omnibase_core/validation/patterns.py:28`

```python
class ProtocolPatternChecker(Protocol):
    """Protocol for pattern checkers with issues tracking."""

    issues: list[str]

    def visit(self, node: ast.AST) -> None:
        """Visit an AST node."""
        ...
```

**Purpose**: Structural subtyping for AST validation checkers
**Pattern**: Visitor pattern protocol
**Usage**: Pattern validation system (3 concrete implementations)
**Implementations**:
- `PydanticPatternChecker`
- `NamingConventionChecker`
- `GenericPatternChecker`

**Design Notes**:
- Uses Protocol for polymorphic checker composition
- Enables extensible validation without inheritance
- Issues tracked as mutable state (list[str])

---

#### 1.2 MixinSerializable
**Location**: `src/omnibase_core/mixins/mixin_serializable.py:30`

```python
class MixinSerializable(Protocol):
    """
    Protocol for models that support recursive, protocol-driven serialization
    for ONEX/OmniNode file/block I/O.
    """

    def to_serializable_dict(self: T) -> dict[str, Any]: ...

    @classmethod
    def from_serializable_dict(cls: type[T], data: dict[str, Any]) -> T: ...
```

**Purpose**: Recursive serialization for ONEX models
**Pattern**: Two-way transformation protocol
**Usage**: 19 occurrences across 8 files
**Key Implementations**:
- `ModelNodeMetadataBlock`
- `ModelProjectMetadataBlock`
- `ModelGitHubActionsWorkflow`
- `ModelFunctionTool`

**Design Notes**:
- Generic type variable `T` for self-referential types
- Supports nested model serialization
- Recursive handling of lists, dicts, and enums
- Foundation for canonical I/O operations

---

#### 1.3 EnumStatusProtocol
**Location**: `src/omnibase_core/models/core/model_status_protocol.py:17`

```python
class EnumStatusProtocol(Protocol):
    """Protocol for status enums that can be migrated and converted to base status."""

    value: str

    def to_base_status(self) -> EnumBaseStatus:
        """Convert this status to its base status equivalent."""
        ...
```

**Purpose**: Enum migration and status normalization
**Pattern**: Adapter protocol for enum interoperability
**Usage**: 18 occurrences across 7 files
**Key Implementations**:
- `EnumScenarioStatusV2`
- `EnumGeneralStatus`
- `EnumFunctionLifecycleStatus`
- `EnumExecutionStatus`

**Design Notes**:
- Enables polymorphic status handling
- Used by `ModelStatusMigrator` for version migrations
- Supports migration path from domain-specific to base statuses
- TYPE_CHECKING guard prevents circular imports

---

### 2. Core-Native Protocols (omnibase_core.protocols)

> **Note (v0.3.6+)**: These protocols are now defined in `omnibase_core.protocols`.
> The section header and location references below have been updated from the original
> `omnibase_spi` paths. See [Import Compatibility Matrix](IMPORT_COMPATIBILITY_MATRIX.md)
> for current import paths.

Total: **100+ protocols** across 20+ domains

#### 2.1 Core Type Protocols
**Location**: `omnibase_core.protocols` (formerly `omnibase_spi.protocols.types`)

**Structural Protocols** (behavioral contracts):
```python
ProtocolSerializable       # model_dump() method
ProtocolIdentifiable       # id property
ProtocolNameable          # get_name(), set_name() methods
ProtocolConfigurable      # configure() method
ProtocolExecutable        # execute() method
ProtocolValidatable       # validate_instance() method
ProtocolMetadataProvider  # metadata property
```

**Data Protocols** (shape contracts):
```python
ProtocolContextValue       # Union[primitive | list | dict]
ProtocolSchemaValue        # Schema-validated values
ProtocolHealthCheck        # Health check result structure
ProtocolLogEntry           # Structured logging data
ProtocolMetadata           # Generic metadata structure
ProtocolSemVer            # Semantic version structure
```

**Usage in omnibase_core**:
```python
# From types/constraints.py (v0.3.6+ - Core-native imports)
from omnibase_core.protocols import (
    ProtocolConfigurable as Configurable,
    ProtocolExecutable as Executable,
    ProtocolIdentifiable as Identifiable,
    ProtocolSerializable as Serializable,
    ProtocolValidatable,
    ProtocolMetadataProvider,
)
```

---

#### 2.2 Event Bus Protocols
**Location**: `omnibase_core.protocols` (formerly `omnibase_spi.protocols.event_bus`)

```python
ProtocolEventBus              # Event bus interface
ProtocolEventPublisher        # Event publishing
ProtocolEventSubscription     # Subscription management
ProtocolEventEnvelope         # Event wrapper protocol
ProtocolEventOrchestrator     # Multi-event coordination
```

**Key Pattern**: Pub/Sub with protocol-based contracts
**Usage**: `MixinEventDrivenNode` uses `ProtocolEventBus` extensively

---

#### 2.3 File Handling Protocols
**Location**: `omnibase_core.protocols` (formerly `omnibase_spi.protocols.file_handling`)

```python
ProtocolFileReader            # File reading interface
ProtocolFileWriter            # File writing interface
ProtocolFileTypeHandler       # MIME type handling
ProtocolDirectoryTraverser    # Directory navigation
ProtocolFileProcessing        # Processing pipeline
```

**Key Pattern**: Strategy pattern for file operations

---

#### 2.4 Schema & Validation Protocols
**Location**: `omnibase_core.protocols` (formerly `omnibase_spi.protocols.schema`)

```python
ProtocolSchemaLoader          # Schema loading interface
ProtocolValidationResult      # Validation output
ProtocolModelValidatable      # Model validation
```

**Usage**: `MixinEventDrivenNode` injects `ProtocolSchemaLoader`

---

#### 2.5 MCP (Model Context Protocol)
**Location**: `omnibase_core.protocols` (formerly `omnibase_spi.protocols.mcp`)

```python
ProtocolTool                  # MCP tool interface
ProtocolMCPRegistry           # Tool registry
ProtocolMCPDiscovery          # Tool discovery
ProtocolMCPValidator          # Tool validation
```

**Key Pattern**: Plugin architecture with protocol contracts

---

#### 2.6 Workflow Orchestration Protocols
**Location**: `omnibase_core.protocols` (formerly `omnibase_spi.protocols.workflow_orchestration`)

```python
ProtocolWorkflowDefinition    # Workflow structure
ProtocolWorkflowContext       # Execution context
ProtocolWorkflowEvent         # Event-driven workflow
ProtocolTaskConfiguration     # Task config
```

**Key Pattern**: Event-driven workflow with FSM support

---

## Protocol Usage Patterns

### Pattern 1: Structural Subtyping (Duck Typing)
**Use Case**: Polymorphic behavior without inheritance

```python
# Protocol definition (omnibase_core.protocols - v0.3.6+)
class ProtocolSerializable(Protocol):
    def model_dump(self) -> dict[str, Any]: ...

# Implementation (omnibase_core) - NO explicit inheritance
class ModelBase(BaseModel):
    # Pydantic models automatically satisfy this protocol
    def model_dump(self) -> dict[str, Any]:
        return super().model_dump()

# Usage with type hints
def serialize_model(obj: ProtocolSerializable) -> dict[str, Any]:
    return obj.model_dump()  # Type-safe!
```

**Benefits**:
- No tight coupling to concrete types
- Easier testing (mock any compatible object)
- Gradual typing support

---

### Pattern 2: Dependency Injection
**Use Case**: Constructor injection with protocol contracts

```python
class MixinEventDrivenNode:
    def __init__(
        self,
        event_bus: ProtocolEventBus,
        metadata_loader: ProtocolSchemaLoader,
        **kwargs: object,
    ) -> None:
        # Protocol contracts enforce interface compliance
        if not event_bus:
            raise ModelOnexError(
                EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER,
                "ProtocolEventBus is mandatory"
            )

        self.event_bus = event_bus
        self.metadata_loader = metadata_loader
```

**Benefits**:
- Clear interface boundaries
- Mockable dependencies
- Runtime validation via type checking

**Usage Count**: 100+ constructor injections across codebase

---

### Pattern 3: Runtime Type Checking
**Use Case**: Dynamic validation with type guards

```python
# Type guards in types/constraints.py
def is_serializable(obj: object) -> bool:
    """Check if object implements Serializable protocol."""
    return hasattr(obj, "model_dump") and callable(obj.model_dump)

def is_identifiable(obj: object) -> bool:
    """Check if object implements Identifiable protocol."""
    return hasattr(obj, "id")

# Usage
if is_serializable(unknown_obj):
    result = unknown_obj.model_dump()  # Type-narrowed!
```

**Type Guards Available**:
- `is_serializable()`
- `is_identifiable()`
- `is_nameable()`
- `is_validatable()`
- `is_configurable()`
- `is_executable()`
- `is_metadata_provider()`
- `is_primitive_value()`
- `is_context_value()`

---

### Pattern 4: Protocol Composition
**Use Case**: Multiple protocol constraints

```python
# TypeVars with protocol bounds
SerializableType = TypeVar("SerializableType", bound=Serializable)
IdentifiableType = TypeVar("IdentifiableType", bound=Identifiable)

# Intersection types via multiple bounds
def process_entity(
    entity: Serializable & Identifiable
) -> dict[str, Any]:
    return {
        "id": entity.id,
        "data": entity.model_dump(),
    }
```

---

### Pattern 5: Protocol Aliasing
**Use Case**: Avoiding naming conflicts

```python
# From types/constraints.py (v0.3.6+ - Core-native imports)
from omnibase_core.protocols import (
    ProtocolConfigurable as Configurable,
    ProtocolExecutable as Executable,
    ProtocolIdentifiable as Identifiable,
)

# Shorter aliases for common use
ConfigurableType = TypeVar("ConfigurableType", bound=Configurable)
ExecutableType = TypeVar("ExecutableType", bound=Executable)
```

**Rationale**: Cleaner code, avoid Protocol prefix repetition

---

### Pattern 6: Lazy Protocol Imports
**Use Case**: Breaking circular dependencies

```python
# From types/constraints.py
if TYPE_CHECKING:
    # Type hints only, not runtime
    BaseCollection = ModelBaseCollection
    BaseFactory = ModelBaseFactory
else:
    # Lazy runtime import via __getattr__
    def __getattr__(name: str) -> object:
        if name in ("ModelBaseCollection", "BaseCollection"):
            from omnibase_core.models.base import ModelBaseCollection
            globals()["ModelBaseCollection"] = ModelBaseCollection
            return globals()[name]
        raise AttributeError(f"module has no attribute {name!r}")
```

**Critical Pattern**: Used to break `models.* → types.constraints → models.base` cycle

---

## Protocol Dependency Graph

### High-Level Architecture

> **Note (v0.3.6+)**: The diagram below has been updated to reflect the dependency
> inversion where omnibase_core is now the source of truth for protocols.

```text
┌─────────────────────────────────────────────────────────────┐
│                      omnibase_core                           │
│  (Protocol Definitions - Source of Truth)                   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ protocols/                                          │   │
│  │  ├── container/ (DI protocols)                     │   │
│  │  ├── event_bus/ (Event bus protocols)              │   │
│  │  ├── types/ (Core type protocols)                  │   │
│  │  ├── validation/ (Validation protocols)            │   │
│  │  └── ...                                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ models/* (1,800+ files)                            │   │
│  │  - BaseModel classes                               │   │
│  │  - Implicit protocol satisfaction                  │   │
│  │  - Constructor DI with protocols                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Internal Protocols                                  │   │
│  │  ├── validation/patterns.py::ProtocolPatternChecker       │   │
│  │  ├── mixins/mixin_serializable.py::MixinSerializable│  │
│  │  └── models/core/model_status_protocol.py::EnumStatusProtocol │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ imports (depends on)
                              │
┌─────────────────────────────────────────────────────────────┐
│                      omnibase_spi                            │
│  (Service Provider Interface - extends Core protocols)      │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Extends Core protocols for cross-service contracts │   │
│  │  - May add SPI-specific protocol extensions       │   │
│  │  - References Core models and types               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ imports (depends on)
                              │
┌─────────────────────────────────────────────────────────────┐
│                      omnibase_infra                          │
│  (Protocol Implementations - Transport Libraries)           │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Implements protocols using transport libraries     │   │
│  │  - Kafka for event bus                            │   │
│  │  - PostgreSQL for persistence                      │   │
│  │  - Redis for caching                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

### Critical Import Chains

#### Chain 1: Type Constraints (Circular Dependency Resolution)
```text
1. types/core_types.py               (no external deps)
2. errors/error_codes.py             → types/core_types
3. models/common/model_schema_value  → errors/error_codes
4. types/constraints.py              → TYPE_CHECKING(errors/error_codes)
5. models/*                          → types/constraints (runtime)
6. types/constraints.__getattr__()   → models/base (lazy)
```

**Key**: Step 4 uses `TYPE_CHECKING` to avoid runtime import, breaking the cycle.

#### Chain 2: Event Bus Integration
```text
omnibase_core.protocols (Core-native - v0.3.6+)
  → ProtocolEventBus
    → omnibase_core.mixins.mixin_event_driven_node
      → Constructor injection: event_bus: ProtocolEventBus
        → Runtime validation + event handlers
```

#### Chain 3: Metadata Loading
```text
omnibase_core.protocols (Core-native - v0.3.6+)
  → ProtocolSchemaLoader
    → omnibase_core.mixins.mixin_event_driven_node
      → DI: metadata_loader: ProtocolSchemaLoader | None
        → Fallback via registry lookup
```

---

## Protocol Violations Analysis

### Violation Type 1: Missing Protocol Methods ❌
**Status**: NOT FOUND in audit

**What to look for**:
```python
# VIOLATION: Claims to satisfy protocol but missing method
class BadImplementation:
    def model_dump(self) -> dict[str, Any]:
        return {"data": "ok"}
    # Missing: serialize() method required by ProtocolSerializable

# Usage
def process(obj: ProtocolSerializable):
    obj.serialize()  # Runtime AttributeError!
```

**Mitigation**: Use `runtime_checkable` + type guards

---

### Violation Type 2: Incorrect Method Signatures ❌
**Status**: NOT FOUND in audit

**What to look for**:
```python
# VIOLATION: Wrong return type
class BadSerializer:
    def model_dump(self) -> str:  # Should be dict[str, Any]
        return "not a dict"
```

**Detection**: Mypy type checking

---

### Violation Type 3: Protocol Used Where Concrete Type Needed ⚠️
**Status**: POTENTIAL ISSUE

**Example**:
```python
# From constraints.py - uses object instead of protocol
PrimitiveValueType = object  # Runtime validation required
ContextValueType = object    # Runtime validation required

# Better approach
@runtime_checkable
class ProtocolPrimitiveValue(Protocol):
    """Represents str | int | float | bool"""
    pass

PrimitiveValueType = TypeVar("PrimitiveValueType", str, int, float, bool)
```

**Recommendation**: Replace `object` with proper TypeVar or Union

---

### Violation Type 4: Mutable Protocol State ⚠️
**Status**: FOUND in `ProtocolPatternChecker`

```python
class ProtocolPatternChecker(Protocol):
    issues: list[str]  # ⚠️ Mutable state in protocol
```

**Issue**: Protocols with mutable state can cause shared-state bugs

**Recommendation**:
- Use `@dataclass` with `frozen=True` for immutable protocols
- Or return issues instead of storing them

```python
# Better design
class ProtocolPatternChecker(Protocol):
    def visit(self, node: ast.AST) -> None: ...
    def get_issues(self) -> list[str]: ...  # Getter instead of property
```

---

### Violation Type 5: Missing Runtime Checkable ⚠️
**Status**: FOUND in internal protocols

**Example**:
```python
# Current: Not runtime checkable
class ProtocolPatternChecker(Protocol):
    issues: list[str]
    def visit(self, node: ast.AST) -> None: ...

# Better: Runtime checkable
@runtime_checkable
class ProtocolPatternChecker(Protocol):
    issues: list[str]
    def visit(self, node: ast.AST) -> None: ...

# Enables runtime checks
if isinstance(obj, ProtocolPatternChecker):
    obj.visit(ast_node)
```

**Recommendation**: Add `@runtime_checkable` to all protocols for isinstance() support

---

## Design Recommendations

### Recommendation 1: Add @runtime_checkable to Internal Protocols
**Priority**: HIGH

```python
# Before
class ProtocolPatternChecker(Protocol):
    issues: list[str]
    def visit(self, node: ast.AST) -> None: ...

# After
from typing import Protocol, runtime_checkable

@runtime_checkable
class ProtocolPatternChecker(Protocol):
    issues: list[str]
    def visit(self, node: ast.AST) -> None: ...
```

**Benefits**:
- Enable isinstance() checks
- Better runtime validation
- Consistent with omnibase_core.protocols patterns

---

### Recommendation 2: Replace object with Proper Type Constraints
**Priority**: MEDIUM

```python
# Before (from constraints.py)
PrimitiveValueType = object  # Runtime validation required
ContextValueType = object    # Runtime validation required

# After
PrimitiveValueType = TypeVar("PrimitiveValueType", str, int, float, bool)

# Or use Union for flexibility
ContextValueType = str | int | float | bool | list[Any] | dict[str, Any]
```

**Benefits**:
- Better type safety
- IDE autocomplete support
- Mypy validation

---

### Recommendation 3: Document Protocol Usage Patterns
**Priority**: HIGH

Create `docs/PROTOCOL_PATTERNS.md` with:
- When to use protocols vs abstract base classes
- Protocol composition patterns
- Testing strategies for protocol-based code
- Migration guide from ABC to Protocol

---

### Recommendation 4: Extract Common Protocol Patterns
**Priority**: MEDIUM

```python
# Create common/protocol_patterns.py
from typing import Protocol, runtime_checkable, TypeVar

T = TypeVar("T")

@runtime_checkable
class ProtocolTwoWaySerializer(Protocol[T]):
    """Standard pattern for serialization protocols."""
    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> T: ...

# Use in MixinSerializable
class MixinSerializable(ProtocolTwoWaySerializer[T]):
    def to_dict(self) -> dict[str, Any]:
        return self.to_serializable_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> T:
        return cls.from_serializable_dict(data)
```

---

### Recommendation 5: Add Protocol Tests
**Priority**: HIGH

```python
# tests/protocols/test_pattern_checker_protocol.py
import pytest
from typing import get_type_hints

def test_pattern_checker_protocol_compliance():
    """Test that all checker implementations satisfy ProtocolPatternChecker protocol."""
    from omnibase_core.validation.validator_patterns import ProtocolPatternChecker
    from omnibase_core.validation.checker_pydantic_pattern import PydanticPatternChecker

    checker = PydanticPatternChecker("test.py")

    # Runtime check
    assert isinstance(checker, ProtocolPatternChecker)

    # Interface check
    assert hasattr(checker, "issues")
    assert hasattr(checker, "visit")
    assert callable(checker.visit)

def test_serializable_mixin_protocol():
    """Test MixinSerializable protocol compliance."""
    from omnibase_core.mixins.mixin_serializable import MixinSerializable
    from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock

    # Check type hints
    hints = get_type_hints(ModelNodeMetadataBlock)
    assert "to_serializable_dict" in dir(ModelNodeMetadataBlock)
    assert "from_serializable_dict" in dir(ModelNodeMetadataBlock)
```

**Testing Strategy**:
- Runtime isinstance() checks
- Interface presence tests
- Type hint validation
- Integration tests with mocks

---

### Recommendation 6: Protocol Naming Conventions
**Priority**: LOW (already consistent)

**Current Convention** (GOOD):
- Core protocols: `Protocol<Name>` (e.g., `ProtocolSerializable`)
- Internal protocols: Descriptive names (e.g., `ProtocolPatternChecker`, `MixinSerializable`)
- Aliases: Short names (e.g., `Serializable`, `Configurable`)

**Keep this pattern** - it's clear and consistent.

---

### Recommendation 7: Protocol Documentation
**Priority**: HIGH

Add docstrings to all protocols explaining:
1. **Purpose**: What contract does this define?
2. **Usage**: When should you use this protocol?
3. **Implementation**: What must implementers provide?
4. **Examples**: Show concrete usage

```python
@runtime_checkable
class ProtocolPatternChecker(Protocol):
    """
    Protocol for AST pattern validation checkers.

    Purpose:
        Defines the contract for objects that traverse AST nodes and collect
        validation issues. Enables polymorphic checker composition without
        inheritance coupling.

    Usage:
        Use this protocol when:
        - Creating custom pattern validators
        - Type-hinting checker arguments
        - Testing with mock checkers

    Implementation Requirements:
        - Must provide an `issues` attribute (list[str])
        - Must implement `visit(node: ast.AST) -> None`
        - Should accumulate issues during traversal

    Example:
        class MyChecker:
            def __init__(self):
                self.issues = []

            def visit(self, node: ast.AST) -> None:
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("test_"):
                        self.issues.append("Function must start with test_")

        checker: ProtocolPatternChecker = MyChecker()  # Type-safe!
    """

    issues: list[str]

    def visit(self, node: ast.AST) -> None:
        """Visit an AST node and collect validation issues."""
        ...
```

---

## Protocol Hierarchy

### Core Type Protocols
```text
ProtocolSerializable (SPI)
  ↓
MixinSerializable (omnibase_core)
  ↓ (implicit implementations)
ModelNodeMetadataBlock
ModelProjectMetadataBlock
ModelGitHubActionsWorkflow
```

### Status Protocols
```text
EnumStatusProtocol (omnibase_core)
  ↓ (implementations)
EnumScenarioStatusV2
EnumGeneralStatus
EnumFunctionLifecycleStatus
EnumExecutionStatus
```

### Validation Protocols
```text
ProtocolPatternChecker (omnibase_core)
  ↓ (implementations)
PydanticPatternChecker
NamingConventionChecker
GenericPatternChecker
```

---

## Best Practices for Phases 1-4

### Phase 1: Fix Existing Issues
1. ✅ Add `@runtime_checkable` to all internal protocols
2. ✅ Replace `object` types with proper TypeVars
3. ✅ Add comprehensive protocol tests
4. ✅ Document all protocols with examples

### Phase 2: Protocol Consolidation
1. ✅ Audit all protocol usage in models/*
2. ✅ Identify redundant type hints
3. ✅ Create protocol composition patterns
4. ✅ Standardize DI patterns

### Phase 3: Migration & Cleanup
1. ✅ Migrate ABC to Protocol where appropriate
2. ✅ Remove unused protocol imports
3. ✅ Consolidate protocol type guards
4. ✅ Update CI to enforce protocol compliance

### Phase 4: Documentation & Tooling
1. ✅ Create protocol catalog
2. ✅ Add protocol migration guide
3. ✅ Build protocol discovery tool
4. ✅ Create protocol validation CLI

---

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Protocol with Concrete Implementation
```python
# BAD: Protocol with default implementation
class BadProtocol(Protocol):
    def method(self) -> str:
        return "default"  # Protocols should not have implementations
```

**Reason**: Protocols define contracts, not implementations. Use abstract base classes for default behavior.

---

### ❌ Anti-Pattern 2: Over-Specific Protocols
```python
# BAD: Protocol that's too specific
class ProtocolUserManagerWithDatabaseAndCacheAndLogging(Protocol):
    def get_user_from_database_with_cache_and_logging(self, id: int) -> User: ...
```

**Reason**: Protocols should be small, composable interfaces.

**Better**:
```python
class ProtocolUserRepository(Protocol):
    def get_user(self, id: int) -> User: ...

class ProtocolCacheable(Protocol):
    def cache_get(self, key: str) -> Any: ...
```

---

### ❌ Anti-Pattern 3: Protocol Soup
```python
# BAD: Every class uses different protocols
def process(
    a: Protocol1,
    b: Protocol2,
    c: Protocol3,
    d: Protocol4,
    e: Protocol5,
): ...
```

**Reason**: Too many protocols = cognitive overload

**Better**: Use protocol composition or domain-specific protocols

---

### ❌ Anti-Pattern 4: Ignoring Type Checkers
```python
# BAD: Ignoring mypy errors
obj: ProtocolSerializable = some_object  # type: ignore
```

**Reason**: Type ignores hide protocol violations

**Better**: Fix the underlying issue or use proper type guards

---

## Tools & Validation

### Static Type Checking
```bash
# Run mypy with protocol checks
uv run mypy src/omnibase_core --strict-optional --check-untyped-defs

# Protocol-specific checks
uv run mypy src/omnibase_core --warn-redundant-casts --warn-unreachable
```

### Runtime Validation
```python
# Use type guards
from omnibase_core.types.type_constraints import is_serializable

if is_serializable(obj):
    data = obj.model_dump()  # Type-safe!
else:
    raise TypeError(f"{obj} does not implement Serializable protocol")
```

### Protocol Discovery
```bash
# Find all protocol definitions
grep -r "class.*Protocol" src/omnibase_core --include="*.py"

# Find protocol usage
grep -r ": Protocol" src/omnibase_core --include="*.py"

# Count protocol implementations
grep -r "def model_dump\|def serialize\|def get_name" src/omnibase_core --include="*.py" | wc -l
```

---

## References

### Internal Documentation
- `types/constraints.py` - Type constraints and protocol aliases
- `validation/patterns.py` - Pattern validation protocols
- `mixins/mixin_serializable.py` - Serialization protocol
- `models/core/model_status_protocol.py` - Status migration protocol
- `protocols/` - Core-native protocol definitions (v0.3.6+)

### External Resources
- PEP 544 - Protocols: Structural subtyping (static duck typing)
- Python typing module documentation
- [Import Compatibility Matrix](IMPORT_COMPATIBILITY_MATRIX.md) - Current import paths

---

## Appendix: Complete Protocol Catalog

### omnibase_core Internal Protocols (3)
1. **ProtocolPatternChecker** - AST validation contract
2. **MixinSerializable** - Recursive serialization
3. **EnumStatusProtocol** - Status migration

### omnibase_core.protocols Categories (100+)
1. **Core Types** (50+) - Basic interfaces (Serializable, Identifiable, etc.)
2. **Event Bus** (15+) - Pub/sub messaging
3. **File Handling** (12+) - File I/O operations
4. **MCP** (18+) - Model Context Protocol
5. **Workflow Orchestration** (15+) - Event-driven workflows
6. **Container** (12+) - Dependency injection
7. **Discovery** (7+) - Service discovery
8. **Schema** (11+) - Schema validation
9. **Storage** (6+) - Storage backends
10. **Validation** (8+) - Data validation

---

## Metrics Summary

| Metric | Count |
|--------|-------|
| Total Python files | 1,848 |
| Internal protocols | 3 |
| External protocols (SPI) | 100+ |
| Protocol method implementations | 420+ |
| Files using protocols | 224 |
| Serialization implementations | 19 |
| Status migration implementations | 18 |
| Pattern checker implementations | 3 |

---

**Document Version**: 1.1
**Last Updated**: 2025-12-18
**Audit Scope**: Complete omnibase_core codebase
**Change History**:
- v1.1 (2025-12-18): Updated for v0.3.6 dependency inversion - protocols now Core-native
- v1.0 (2025-10-22): Initial audit
