# ADR-001: Protocol-Based Dependency Injection Architecture

**Status**: Accepted ✅
**Date**: 2025-10-30
**Deciders**: ONEX Framework Team
**Related**: REGISTRY_AUDIT_REPORT.md (2025-10-30)

---

## Context

The omnibase_core framework requires a robust dependency injection (DI) system that supports:

1. **Protocol-driven interfaces** (omnibase_spi protocols)
2. **Type-safe service resolution**
3. **Multiple service lifecycles** (singleton, transient, scoped)
4. **Observable service management** (health monitoring, performance tracking)
5. **Pydantic validation** for all configurations and contracts

### The "Registry" Terminology Problem

The term "registry" appears in three distinct architectural contexts within omnibase_core, leading to confusion:

1. **ServiceRegistry** - Dependency injection container (compile-time resolution)
2. **Business Registries** - CLI/event discovery systems (contract-time discovery)
3. **MixinServiceRegistry** - Runtime tool discovery (event-time discovery)

This ADR clarifies these distinctions and establishes the protocol-based DI pattern as the canonical approach.

---

## Decision

We adopt **Protocol-Based Dependency Injection** via `ServiceRegistry` as the exclusive DI mechanism for omnibase_core.

### Core Principles

1. **Protocol Interfaces Only**: All services resolved by protocol interface, never by concrete class
2. **Pydantic Validation**: All configuration/registration models are Pydantic BaseModel subclasses
3. **Type-Safe Resolution**: Generic type parameters ensure compile-time type safety
4. **Observable Lifecycle**: All registrations tracked with health monitoring and performance metrics
5. **Clear Separation**: Business domain registries serve distinct purposes from DI container

---

## Architectural Components

### 1. ServiceRegistry (DI Container)

**Purpose**: Protocol-based dependency injection and service lifecycle management

**Key Classes**:
- `ServiceRegistry` - Main DI container (implements `ProtocolServiceRegistry`)
- `ModelServiceRegistryConfig` - Configuration (Pydantic BaseModel)
- `ModelServiceRegistryStatus` - Health/status reporting (Pydantic BaseModel)
- `ModelServiceRegistration` - Service registration metadata (Pydantic BaseModel)

**Usage Pattern**:
```python
# Initialize registry
config = create_default_registry_config()
registry = ServiceRegistry(config)

# Register service by protocol interface
await registry.register_instance(
    interface=ProtocolLogger,
    instance=logger_instance,
    scope="global"
)

# Resolve service by protocol
logger = await registry.resolve_service(ProtocolLogger)
```

**Integration with Container**:
```python
# ModelONEXContainer integration (lines 125-149)
self._service_registry = ServiceRegistry(registry_config)

# Service resolution with fallback
service = await self.get_service_async(ProtocolLogger)
```

**Files**:
- `src/omnibase_core/container/service_registry.py` (896 lines)
- `src/omnibase_core/models/container/model_registry_config.py`
- `src/omnibase_core/models/container/model_registry_status.py`

### 2. Business Domain Registries (Separate Concern)

**Purpose**: Dynamic discovery of CLI actions, events, and commands from node contracts

These are **NOT dependency injection registries** - they serve business logic purposes:

#### ModelActionRegistry
- **Purpose**: Discover CLI actions from node contracts
- **Pattern**: Loads `contract.yaml` → validates with `ModelGenericYaml` (Pydantic) → registers `ModelCliAction`
- **Usage**: CLI command routing and action discovery

#### ModelEventTypeRegistry
- **Purpose**: Discover event types from node contracts
- **Pattern**: Loads `contract.yaml` → validates with `ModelGenericYaml` (Pydantic) → registers `ModelEventType`
- **Usage**: Event type validation and namespace management

#### ModelCliCommandRegistry
- **Purpose**: CLI command routing and discovery
- **Pattern**: IS a Pydantic BaseModel, stores `ModelCliCommandDefinition` instances
- **Usage**: CLI command parsing and execution routing

**Key Distinction**: These registries discover **business logic** (actions, events) from contracts, not **service dependencies**.

**Files**:
- `src/omnibase_core/models/core/model_action_registry.py`
- `src/omnibase_core/models/core/model_event_type_registry.py`
- `src/omnibase_core/models/core/model_cli_command_registry.py`

### 3. MixinServiceRegistry (Runtime Discovery)

**Purpose**: Event-driven tool discovery and lifecycle management

**Pattern**:
- Subscribes to event bus (`core.node.start`, `core.node.stop`)
- Maintains live catalog of available tools
- Tracks service health via `MixinServiceRegistryEntry` (Pydantic)

**Key Distinction**: This handles **runtime discovery** of tools that come online/offline dynamically, not compile-time dependency resolution.

**Files**:
- `src/omnibase_core/mixins/mixin_service_registry.py`
- `src/omnibase_core/mixins/model_service_registry_entry.py`

---

## Resolution Flow

### Dependency Injection (ServiceRegistry)

```text
User Code
    │
    ▼
container.get_service(ProtocolLogger)
    │
    ▼
ServiceRegistry.resolve_service(ProtocolLogger)
    │
    ├─→ Check interface_map for ProtocolLogger
    │
    ├─→ Get registration metadata (Pydantic validated)
    │
    ├─→ Resolve by lifecycle (singleton/transient)
    │
    └─→ Return typed instance: logger (type: ProtocolLogger)
```python

### Business Registry (Action Discovery)

```text
Node Contract (contract.yaml)
    │
    ▼
load_and_validate_yaml_model(file, ModelGenericYaml)  # Pydantic validation
    │
    ▼
Extract CLI interface section
    │
    ▼
ModelCliAction.from_contract_action(...)  # Pydantic model
    │
    ▼
ModelActionRegistry.register_action(action)
    │
    └─→ Stored in _actions dict for CLI routing
```python

### Runtime Discovery (MixinServiceRegistry)

```python
Tool Node Starts
    │
    ▼
Event: core.node.start published to event bus
    │
    ▼
MixinServiceRegistry._handle_node_start(event)
    │
    ▼
Create MixinServiceRegistryEntry (Pydantic)
    │
    ▼
Store in self.service_registry[tool_id]
    │
    └─→ Tool available in live catalog
```python

---

## Pydantic Validation Compliance

### Validation Requirements (100% Compliant)

**All Configuration Models**:
- ✅ `ModelServiceRegistryConfig` - Field validators, constraints, defaults
- ✅ `ModelServiceRegistryStatus` - Enum validation, datetime handling
- ✅ `ModelServiceRegistration` - Lifecycle validation, health checks
- ✅ `ModelCliCommandRegistry` - BaseModel with nested model validation

**Contract Loading**:
- ✅ All YAML loaded via `load_and_validate_yaml_model(file, ModelGenericYaml)`
- ✅ Pydantic validation occurs BEFORE business logic
- ✅ Validation errors raise `ModelOnexError` with structured context

**Zero Manual Validation**:
- ❌ No `isinstance(x, dict)` checks in container/registry code
- ❌ No `type(x) == dict` patterns
- ❌ No manual dict key validation

**Evidence**: See REGISTRY_AUDIT_REPORT.md (2025-10-30) for comprehensive analysis.

---

## Service Lifecycle Patterns

### Singleton (Default)

```python
# Register singleton
await registry.register_instance(
    interface=ProtocolLogger,
    instance=logger,
    scope="global"
)

# All resolutions return same instance
logger1 = await registry.resolve_service(ProtocolLogger)
logger2 = await registry.resolve_service(ProtocolLogger)
assert logger1 is logger2  # Same instance
```text

### Transient (Planned v2.0)

```python
# Register transient (requires factory support)
await registry.register_factory(
    interface=ProtocolConnectionPool,
    factory=ConnectionPoolFactory(),
    lifecycle="transient"
)

# Each resolution creates new instance
pool1 = await registry.resolve_service(ProtocolConnectionPool)
pool2 = await registry.resolve_service(ProtocolConnectionPool)
assert pool1 is not pool2  # Different instances
```text

### Scoped (Planned v2.0)

```python
# Register scoped service
await registry.register_service(
    interface=ProtocolRequestContext,
    implementation=RequestContext,
    lifecycle="scoped",
    scope="request"
)

# Same instance within scope, different across scopes
async with registry.create_scope("request") as scope:
    ctx1 = await scope.resolve_service(ProtocolRequestContext)
    ctx2 = await scope.resolve_service(ProtocolRequestContext)
    assert ctx1 is ctx2  # Same within scope
```python

---

## Integration with ModelONEXContainer

### Dual Resolution Strategy

The container supports both ServiceRegistry (new) and legacy fallback:

```python
async def get_service_async(
    self,
    protocol_type: type[T],
    service_name: str | None = None,
) -> T:
    # 1. Try ServiceRegistry first (new DI)
    if self._enable_service_registry and self._service_registry:
        try:
            return await self._service_registry.resolve_service(protocol_type)
        except Exception:
            pass  # Fall through to legacy

    # 2. Fallback to legacy resolution
    provider_map = {
        "ProtocolLogger": "enhanced_logger",
    }
    provider_name = provider_map.get(protocol_type.__name__)
    return getattr(self._base_container, provider_name)()
```python

**Migration Path**: v1.0 uses fallback, v2.0 will be ServiceRegistry-only.

---

## Consequences

### Positive

✅ **Type Safety**: Generic type parameters ensure compile-time correctness
✅ **Testability**: Easy to mock protocol interfaces in tests
✅ **Observability**: Built-in health monitoring and performance tracking
✅ **Flexibility**: Multiple lifecycles (singleton, transient, scoped)
✅ **Validation**: Pydantic ensures configuration correctness
✅ **Consistency**: Single pattern for all dependency management
✅ **Future-Proof**: Protocol-based design supports omnibase_spi evolution

### Neutral

⚠️ **Learning Curve**: Developers must understand protocol vs concrete class distinction
⚠️ **Terminology**: "Registry" used in three contexts requires clear documentation

### Negative

❌ **Performance Overhead**: Protocol resolution adds ~1-2ms per resolution (acceptable for non-hot-path)
❌ **v1.0 Limitations**: Factory and scoped lifecycle not yet implemented
❌ **Fallback Complexity**: Dual resolution strategy adds maintenance burden (temporary)

---

## Alternatives Considered

### Alternative 1: Concrete Class DI

**Pattern**:
```python
# Register by concrete class
registry.register(LoggerImpl, singleton=True)

# Resolve by concrete class
logger = registry.resolve(LoggerImpl)
```text

**Rejected Because**:
- ❌ Tight coupling to implementation
- ❌ Hard to mock in tests
- ❌ Doesn't support omnibase_spi protocol architecture
- ❌ Violates Dependency Inversion Principle

### Alternative 2: String-Based Resolution

**Pattern**:
```python
# Register by string name
registry.register("logger", logger_instance)

# Resolve by string
logger = registry.resolve("logger")
```python

**Rejected Because**:
- ❌ No type safety (returns `Any`)
- ❌ Typos cause runtime errors
- ❌ No IDE autocomplete support
- ❌ Difficult to refactor

### Alternative 3: Decorator-Based DI

**Pattern**:
```python
@injectable(ProtocolLogger)
class MyService:
    def __init__(self, logger: ProtocolLogger):
        self.logger = logger
```python

**Rejected Because**:
- ❌ Requires complex decorator machinery
- ❌ Hard to debug when injection fails
- ❌ Less explicit than constructor injection
- ❌ Adds "magic" behavior

---

## Implementation Notes

### Current Status (v0.2.0)

**Implemented**:
- ✅ ServiceRegistry with protocol-based resolution
- ✅ Singleton lifecycle support
- ✅ Pydantic validation for all models
- ✅ Health monitoring and status reporting
- ✅ Integration with ModelONEXContainer
- ✅ Business registry systems (action, event, command)
- ✅ MixinServiceRegistry for runtime discovery

**Planned for v2.0**:
- ⏳ Factory-based registration (line 289-315 in service_registry.py)
- ⏳ Transient lifecycle implementation
- ⏳ Scoped lifecycle with scope creation
- ⏳ Circular dependency detection (currently returns empty list)
- ⏳ Auto-wiring via constructor inspection
- ⏳ Protocol service resolver for external dependencies

### Migration Path

**Phase 1 (v0.1.x)**: Dual resolution
- ServiceRegistry available but optional
- Fallback to legacy resolution if ServiceRegistry fails
- Gradual migration of services to ServiceRegistry

**Phase 2 (v1.0.x)**: ServiceRegistry primary
- ServiceRegistry becomes default resolution path
- Legacy resolution only for explicitly configured services
- Deprecation warnings for legacy patterns

**Phase 3 (v2.0.x)**: ServiceRegistry only
- Remove all legacy fallback logic
- ServiceRegistry is exclusive DI mechanism
- Complete factory and scoped lifecycle support

---

## TODO Clarifications

The codebase contains TODO comments that are often misinterpreted as "legacy registry removal" tasks. These are actually **future protocol integration** placeholders:

### model_onex_container.py Lines 58-61

**Current**:
```python
# TODO: These imports require omnibase-spi protocols that may not be available yet
```bash

**Clarified**:
```python
# FUTURE (v2.0): Protocol integrations pending omnibase-spi v0.2.0
# These protocols will enable external service discovery and database pooling.
# Tracking: https://github.com/OmniNode-ai/omnibase_spi/issues/42
```python

### model_onex_container.py Lines 304-305

**Current**:
```python
# TODO: Ready to implement using ProtocolServiceResolver from omnibase_spi.protocols.container
# Note: ProtocolServiceResolver added in omnibase_spi v0.1.2
```python

**Status**:
ProtocolServiceResolver is now available in omnibase_spi v0.1.2 and ready for implementation.
This will enable automatic service discovery for ProtocolDatabaseConnection,
ProtocolServiceDiscovery, and other external dependencies.

### model_onex_container.py Lines 531-560

**Current**:
```python
# TODO: Ready to implement using ProtocolServiceResolver from omnibase_spi.protocols.container
# Note: ProtocolServiceResolver added in omnibase_spi v0.1.2
```python

**Status**:
ProtocolServiceResolver is now available for implementation of external service health checks.
Current behavior: Returns "unavailable" status message (graceful degradation).
Implementation ready to proceed using omnibase_spi v0.1.2.
```markdown

---

## References

### Related Documentation

- [ONEX Four-Node Architecture](../ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Protocol-Driven DI Guide](../../guides/PROTOCOL_DRIVEN_DI.md) (to be created)
- [Registry Audit Report](../../../REGISTRY_AUDIT_REPORT.md)

### External References

- [Dependency Inversion Principle (SOLID)](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Protocol-Oriented Programming](https://developer.apple.com/videos/play/wwdc2015/408/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Code References

**Primary Implementation**:
- `src/omnibase_core/container/service_registry.py` (Lines 39-896)
- `src/omnibase_core/models/container/model_onex_container.py` (Lines 74-730)

**Protocol Definitions** (omnibase_spi):
- `omnibase_spi.protocols.container.ProtocolServiceRegistry`
- `omnibase_spi.protocols.container.LiteralServiceLifecycle`
- `omnibase_spi.protocols.container.LiteralInjectionScope`

**Business Registries**:
- `src/omnibase_core/models/core/model_action_registry.py`
- `src/omnibase_core/models/core/model_event_type_registry.py`
- `src/omnibase_core/models/core/model_cli_command_registry.py`

---

## Approval

**Approved By**: ONEX Framework Team
**Date**: 2025-10-30
**Version**: 1.0

**Sign-offs**:
- Architecture: ✅ Approved (protocol-based approach aligns with omnibase_spi)
- Implementation: ✅ Approved (100% Pydantic validation, type-safe)
- Testing: ✅ Approved (12,000+ tests cover framework functionality)
- Documentation: ✅ Approved (comprehensive audit report + ADR)

---

## Changelog

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-30 | Initial ADR following comprehensive registry audit | ONEX Team |

---

**Next Review**: 2026-01-30 (or upon omnibase-spi v0.2.0 release)
