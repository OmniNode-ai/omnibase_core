# Mixin Migration Plan: From Inheritance to Runtime-Host Model

> **Version**: 1.1.0
> **Status**: Active Planning
> **Last Updated**: 2025-12-03
> **Related Documents**:
> - [DEPENDENCY_REFACTORING_PLAN.md](./DEPENDENCY_REFACTORING_PLAN.md)
> - [MINIMAL_RUNTIME_PHASED_PLAN.md](./MINIMAL_RUNTIME_PHASED_PLAN.md)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [The R/H/D Classification System](#the-rhd-classification-system)
3. [Complete Mixin Audit Table](#complete-mixin-audit-table)
4. [Migration Paths by Category](#migration-paths-by-category)
5. [Special Handling: Reducer/Orchestrator Domain Logic](#special-handling-reducerorchestrator-domain-logic)
6. [Handler Protocol Interfaces (SPI)](#handler-protocol-interfaces-spi)
7. [Seven-Step Migration Process](#seven-step-migration-process)
8. [Phase Alignment](#phase-alignment)
9. [Risk Assessment](#risk-assessment)
10. [Success Criteria](#success-criteria)

---

## Executive Summary

The omnibase_core project currently uses **40 mixins** to add cross-cutting behavior to nodes through multiple inheritance. This approach has led to:

- **Diamond inheritance problems** requiring careful MRO management
- **Tight coupling** between infrastructure and domain logic
- **Testing complexity** due to interdependent behaviors
- **Hidden dependencies** via `getattr()` patterns

This migration plan replaces mixin inheritance with a **runtime-host model** where:

1. **Runtime behaviors (R)** are injected into `NodeRuntime`/`NodeInstance` as first-class services
2. **Handler behaviors (H)** become explicit handler implementations (Vault, Consul, DB, HTTP, LLM)
3. **Domain libraries (D)** become pure functions/classes with no runtime dependencies

**Goal**: Eliminate all 40 mixins by Phase 4, replacing them with composable, testable, protocol-driven components.

### Core I/O Invariant

**Critical Rule**: No code in `omnibase_core` may initiate network I/O, database I/O, file I/O, or external process execution.

This means:
- **R (Runtime)** mixins become pure algorithms in `omnibase_core/runtime/`
- **H (Handler)** mixins become I/O implementations in **`omnibase_infra`** (not Core!)
- **D (Domain)** mixins become pure libraries in `omnibase_core/lib/` or `omnibase_core/domain/`

### R/H/D Classification Destination Summary

| Classification | Destination Package | Destination Path |
|----------------|---------------------|------------------|
| **R** (Runtime) | `omnibase_core` | `omnibase_core/runtime/` |
| **H** (Handler) | `omnibase_infra` | `omnibase_infra/handlers/` |
| **D** (Domain) | `omnibase_core` | `omnibase_core/lib/` or `omnibase_core/domain/` |

---

## The R/H/D Classification System

### Runtime-Level Behavior (R)

**Definition**: Cross-cutting concerns that every node needs but shouldn't implement.

**Characteristics**:
- Applied consistently across all node types
- Manages node lifecycle, identity, and infrastructure
- Provides observability (metrics, logging, health)
- Handles event bus integration

**Migration Target**: `NodeRuntime` / `NodeInstance` classes

**Examples**:
- Node lifecycle (start, stop, register, deregister)
- Health monitoring and reporting
- Metrics collection and emission
- Event bus connection management
- Correlation ID propagation

### Handler-Level Behavior (H)

**Definition**: External service integrations that vary by deployment.

**Characteristics**:
- Specific to external systems (Vault, Consul, databases, HTTP APIs)
- Configured via environment/deployment
- May have multiple implementations (e.g., mock vs. production)
- Implements SPI protocols
- **Performs I/O operations** (network, database, file system, external processes)

**Migration Target**: Handler implementations in **`omnibase_infra/handlers/`** (NOT core!)

> **Critical**: Handlers perform I/O and therefore belong in `omnibase_infra`, not `omnibase_core`. The Core I/O Invariant prohibits any I/O-initiating code in core.

**Correct Destinations**:
- `VaultHandler` -> `omnibase_infra/handlers/vault_handler.py`
- `ConsulHandler` -> `omnibase_infra/handlers/consul_handler.py`
- `DbHandler` -> `omnibase_infra/handlers/postgres_handler.py`
- `HttpHandler` -> `omnibase_infra/handlers/http_rest_handler.py`
- `LlmHandler` -> `omnibase_infra/handlers/llm_handler.py`
- `ServiceRegistryHandler` -> `omnibase_infra/handlers/service_registry_handler.py`
- `DiscoveryHandler` -> `omnibase_infra/handlers/discovery_handler.py`
- `CLIHandler` -> `omnibase_infra/handlers/cli_handler.py`

**Examples**:
- Secret fetching (Vault handler)
- Service discovery (Consul handler)
- Database operations (PostgreSQL handler)
- HTTP client operations (HTTP handler)
- LLM integrations (LLM handler)

### Domain Libraries (D)

**Definition**: Pure computation with no side effects or runtime dependencies.

**Characteristics**:
- No I/O, no event bus, no external calls
- Stateless or explicitly state-passing
- Easily unit testable in isolation
- Framework-agnostic

**Migration Target**: `omnibase_core/utils/` or `omnibase_core/domain/`

**Examples**:
- Hash computation algorithms
- YAML serialization/canonicalization
- Data redaction logic
- Lazy evaluation utilities
- Type conversion helpers

---

## Complete Mixin Audit Table

| # | Mixin Name | Current Purpose | Class | Target | Phase |
|---|-----------|-----------------|-------|--------|-------|
| 1 | `MixinCaching` | In-memory caching for node operations | R | `NodeRuntime.cache_service` | 2 |
| 2 | `MixinCompletionData` | Tracks completion status/progress | R | `NodeRuntime.completion_tracker` | 2 |
| 3 | `MixinLazyValue` | Lazy evaluation wrapper class | D | `utils/lazy.py` | 1 |
| 4 | `MixinMetrics` | Prometheus-style metrics collection | R | `NodeRuntime.metrics_service` | 2 |
| 5 | `MixinNodeSetup` | Standard node initialization | R | `NodeRuntime.__init__()` | 1 |
| 6 | `MixinDiscovery` | Service discovery client | H | `omnibase_infra/handlers/discovery_handler.py` | 3 |
| 7 | `MixinFSMExecution` | Finite state machine execution | D | `domain/fsm/executor.py` | 2 |
| 8 | `MixinIntentPublisher` | Publishes ModelIntent events | R | `NodeRuntime.intent_emitter` | 3 |
| 9 | `MixinSerializable` | Basic serialization interface | D | `utils/serialization.py` | 1 |
| 10 | `MixinCanonicalSerialization` | Canonical YAML serialization | D | `utils/canonical_yaml.py` | 1 |
| 11 | `MixinCLIHandler` | CLI argument parsing/handling | H | `omnibase_infra/handlers/cli_handler.py` | 2 |
| 12 | `MixinContractMetadata` | Contract metadata extraction | D | `utils/contract_metadata.py` | 1 |
| 13 | `MixinContractStateReducer` | Contract-driven state reduction | D | `domain/fsm/contract_reducer.py` | 2 |
| 14 | `MixinDebugDiscoveryLogging` | Debug logging for discovery | R | `NodeRuntime.logger` (debug mode) | 1 |
| 15 | `MixinDiscoveryResponder` | Responds to discovery requests | R | `NodeRuntime.discovery_responder` | 2 |
| 16 | `MixinEventBus` | Event bus connection management | R | `NodeRuntime.event_bus` | 1 |
| 17 | `MixinEventDrivenNode` | Base event-driven node behavior | R | `NodeRuntime` (core) | 1 |
| 18 | `MixinEventHandler` | Event handler registration | R | `NodeRuntime.event_handlers` | 1 |
| 19 | `MixinEventListener` | Event subscription management | R | `NodeRuntime.subscriptions` | 1 |
| 20 | `MixinFailFast` | Fail-fast validation patterns | D | `utils/fail_fast.py` | 1 |
| 21 | `MixinHashComputation` | SHA256 hash for metadata blocks | D | `utils/hash.py` | 1 |
| 22 | `MixinHealthCheck` | Health check implementation | R | `NodeRuntime.health_service` | 1 |
| 23 | `MixinHybridExecution` | Direct/workflow/orchestrated modes | R | `NodeRuntime.execution_mode_resolver` | 3 |
| 24 | `MixinIntrospectFromContract` | Load introspection from contract | D | `utils/contract_introspection.py` | 1 |
| 25 | `MixinIntrospection` | Node introspection response | R | `NodeRuntime.introspection_service` | 2 |
| 26 | `MixinIntrospectionPublisher` | Publish introspection events | R | `NodeRuntime.introspection_publisher` | 2 |
| 27 | `MixinLazyEvaluation` | Lazy evaluation patterns | D | `utils/lazy.py` | 1 |
| 28 | `MixinLogData` | Structured log data model | D | `models/logging/` (already a model) | 0 |
| 29 | `MixinNodeExecutor` | Persistent executor mode | R | `NodeRuntime.executor_service` | 3 |
| 30 | `MixinNodeIdFromContract` | Load node ID from contract | D | `utils/node_id.py` | 1 |
| 31 | `MixinNodeIntrospectionData` | Introspection data container | D | `models/introspection/` (already a model) | 0 |
| 32 | `MixinNodeLifecycle` | Node lifecycle events | R | `NodeRuntime.lifecycle_manager` | 1 |
| 33 | `MixinNodeService` | Service interface for nodes | R | `NodeRuntime.service_interface` | 2 |
| 34 | `MixinRedaction` | Sensitive field redaction | D | `utils/redaction.py` | 1 |
| 35 | `MixinRequestResponseIntrospection` | Real-time introspection | R | `NodeRuntime.realtime_introspection` | 3 |
| 36 | `MixinServiceRegistry` | Service registry maintenance | H | `omnibase_infra/handlers/service_registry_handler.py` | 3 |
| 37 | `MixinToolExecution` | Tool execution event handling | R | `NodeRuntime.tool_executor` | 2 |
| 38 | `MixinUtils` | Utility functions (canonicalize) | D | `utils/mixin_utils.py` -> `utils/canonical.py` | 1 |
| 39 | `MixinWorkflowExecution` | Workflow execution from contracts | R | `NodeRuntime.workflow_executor` | 3 |
| 40 | `MixinYAMLSerialization` | YAML serialization with comments | D | `utils/yaml_serialization.py` | 1 |

### Summary by Classification

| Classification | Count | Percentage |
|---------------|-------|------------|
| **Runtime (R)** | 22 | 55% |
| **Handler (H)** | 4 | 10% |
| **Domain (D)** | 14 | 35% |
| **Total** | 40 | 100% |

### Summary by Phase

| Phase | Count | Description |
|-------|-------|-------------|
| **Phase 0** | 2 | Already models, no migration needed |
| **Phase 1** | 14 | Domain libraries (no dependencies) |
| **Phase 2** | 12 | Core runtime services |
| **Phase 3** | 12 | Advanced runtime + handlers |
| **Phase 4** | 0 | Cleanup and removal |

---

## Migration Paths by Category

### Domain Libraries (D) - Phase 1

**Target Structure**:
```
omnibase_core/
├── utils/
│   ├── lazy.py                    # MixinLazyValue + MixinLazyEvaluation
│   ├── serialization.py           # MixinSerializable
│   ├── canonical_yaml.py          # MixinCanonicalSerialization
│   ├── contract_metadata.py       # MixinContractMetadata
│   ├── contract_introspection.py  # MixinIntrospectFromContract
│   ├── fail_fast.py               # MixinFailFast
│   ├── hash.py                    # MixinHashComputation
│   ├── node_id.py                 # MixinNodeIdFromContract
│   ├── redaction.py               # MixinRedaction
│   ├── yaml_serialization.py      # MixinYAMLSerialization
│   └── canonical.py               # MixinUtils
├── domain/
│   └── fsm/
│       ├── executor.py            # MixinFSMExecution
│       └── contract_reducer.py    # MixinContractStateReducer
```

**Migration Pattern for D**:
```python
# BEFORE (mixin)
class MixinHashComputation:
    def compute_hash(self, body: str, volatile_fields: tuple) -> str:
        ...

class MyNode(MixinHashComputation, NodeBase):
    def process(self):
        hash_val = self.compute_hash(body, fields)

# AFTER (pure function)
# utils/hash.py
def compute_metadata_hash(
    metadata_block: dict[str, Any],
    body: str,
    volatile_fields: tuple[str, ...] = ("hash", "last_modified_at"),
    placeholder: str = "<PLACEHOLDER>",
) -> str:
    """Compute SHA256 hash for metadata block."""
    ...

# node usage
from omnibase_core.utils.hash import compute_metadata_hash

class MyNode(NodeBase):
    def process(self):
        hash_val = compute_metadata_hash(self.metadata, body, fields)
```

### Runtime Services (R) - Phases 1-3

**Target Structure**:
```
omnibase_core/
├── runtime/
│   ├── node_runtime.py           # Main runtime orchestrator
│   ├── services/
│   │   ├── cache_service.py      # MixinCaching
│   │   ├── completion_tracker.py # MixinCompletionData
│   │   ├── metrics_service.py    # MixinMetrics
│   │   ├── health_service.py     # MixinHealthCheck
│   │   ├── lifecycle_manager.py  # MixinNodeLifecycle
│   │   ├── event_manager.py      # MixinEventBus + MixinEventHandler + MixinEventListener
│   │   ├── discovery_responder.py # MixinDiscoveryResponder
│   │   ├── introspection_service.py # MixinIntrospection + MixinIntrospectionPublisher
│   │   ├── intent_emitter.py     # MixinIntentPublisher
│   │   ├── tool_executor.py      # MixinToolExecution
│   │   ├── executor_service.py   # MixinNodeExecutor
│   │   ├── workflow_executor.py  # MixinWorkflowExecution
│   │   └── execution_mode_resolver.py # MixinHybridExecution
│   └── protocols/
│       ├── protocol_cache.py
│       ├── protocol_metrics.py
│       ├── protocol_health.py
│       └── ...
```

**Migration Pattern for R**:
```python
# BEFORE (mixin)
class MixinHealthCheck:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def health_check(self) -> ModelHealthStatus:
        ...

class MyNode(MixinHealthCheck, MixinMetrics, NodeBase):
    ...

# AFTER (runtime service)
# runtime/services/health_service.py
class HealthService:
    """Health check service injected by NodeRuntime."""

    def __init__(self, runtime: "NodeRuntime"):
        self._runtime = runtime
        self._custom_checks: list[Callable] = []

    def health_check(self) -> ModelHealthStatus:
        ...

    def add_check(self, check: Callable) -> None:
        self._custom_checks.append(check)

# runtime/node_runtime.py
class NodeRuntime:
    def __init__(self, config: RuntimeConfig):
        self.health = HealthService(self)
        self.metrics = MetricsService(self)
        self.lifecycle = LifecycleManager(self)
        self.event_bus = EventManager(self)
        ...

# node usage
class MyNode(NodeBase):
    def __init__(self, runtime: NodeRuntime):
        self._runtime = runtime
        self._runtime.health.add_check(self._check_database)

    def get_health(self) -> ModelHealthStatus:
        return self._runtime.health.health_check()
```

### Handler Implementations (H) - Phase 3

> **Critical**: All handlers belong in `omnibase_infra`, NOT `omnibase_core`. Handlers perform I/O operations which violates the Core I/O Invariant.

**Target Structure**:
```
omnibase_infra/                           # <- NOT omnibase_core!
├── handlers/
│   ├── discovery_handler.py              # MixinDiscovery -> Consul/static discovery
│   ├── service_registry_handler.py       # MixinServiceRegistry
│   ├── cli_handler.py                    # MixinCLIHandler
│   ├── vault_handler.py                  # Secret fetching
│   ├── postgres_handler.py               # Database operations
│   ├── http_rest_handler.py              # HTTP client operations
│   ├── llm_handler.py                    # LLM integrations
│   └── health_handler.py                 # Health check I/O
├── handlers_testing/                     # Testing implementations
│   ├── mock_discovery_handler.py         # Mock/static for testing
│   ├── in_memory_registry_handler.py     # In-memory registry
│   └── mock_vault_handler.py             # Mock secrets
```

**Protocols remain in `omnibase_spi`**:
```
omnibase_spi/
├── protocols/
│   └── handlers/
│       ├── protocol_discovery.py
│       ├── protocol_registry.py
│       ├── protocol_cli.py
│       ├── protocol_vault.py
│       ├── protocol_db.py
│       └── protocol_health.py
```

**Migration Pattern for H**:
```python
# BEFORE (mixin in omnibase_core)
class MixinServiceRegistry:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_registry: dict[str, ServiceEntry] = {}

    def start_service_registry(self, domain_filter: str | None = None) -> None:
        ...

# AFTER (handler in omnibase_infra)
# omnibase_infra/handlers/service_registry_handler.py
class ServiceRegistryHandler(ProtocolServiceRegistry):
    """Handler for service registry operations. Lives in omnibase_infra."""

    def __init__(
        self,
        event_bus: ProtocolEventBus,
        config: RegistryConfig,
    ):
        self._event_bus = event_bus
        self._config = config
        self._registry: dict[str, ServiceEntry] = {}

    def start(self, domain_filter: str | None = None) -> None:
        # I/O: connects to Consul, publishes events, etc.
        ...

    def stop(self) -> None:
        # I/O: deregisters from Consul, closes connections
        ...

# SPI protocol (in omnibase_spi, no I/O)
# omnibase_spi/protocols/handlers/registry.py
class ProtocolServiceRegistry(Protocol):
    def start(self, domain_filter: str | None = None) -> None: ...
    def stop(self) -> None: ...
    def get_services(self) -> list[ServiceEntry]: ...

# Runtime injection (core gets handler via DI, doesn't import infra directly)
class NodeRuntime:
    def __init__(self, config: RuntimeConfig, registry: ProtocolServiceRegistry):
        # Handler injected at runtime, not imported from infra
        self.registry = registry
```

---

## Special Handling: Reducer/Orchestrator Domain Logic

### FSM Execution (Reducers)

The `MixinFSMExecution` and `MixinContractStateReducer` contain **domain logic** for finite state machines that must remain pure.

**Migration Strategy**:

```python
# domain/fsm/executor.py
class FSMExecutor:
    """Pure FSM execution engine."""

    def __init__(self, fsm_definition: ModelFSMDefinition):
        self._definition = fsm_definition
        self._transitions = self._build_transition_table()

    def execute_transition(
        self,
        current_state: str,
        intent: ModelIntent,
    ) -> FSMTransitionResult:
        """Execute a state transition. Pure function, no side effects."""
        ...

# domain/fsm/contract_reducer.py
def reduce_state_from_contract(
    contract: ModelContract,
    current_state: ModelState,
    event: ModelEvent,
) -> tuple[ModelState, list[ModelIntent]]:
    """Pure state reduction based on contract definition."""
    ...
```

**Reducer Node Pattern**:
```python
class NodeMyReducer(NodeReducerDeclarative):
    """Reducer node using pure FSM domain logic."""

    def __init__(self, runtime: NodeRuntime, contract: ModelContract):
        super().__init__(runtime, contract)
        self._fsm = FSMExecutor(contract.fsm_definition)

    async def reduce(
        self,
        current_state: ModelState,
        event: ModelEvent,
    ) -> ReducerResult:
        # Use pure domain function
        new_state, intents = reduce_state_from_contract(
            self._contract,
            current_state,
            event,
        )

        # Emit intents through runtime (side effect)
        for intent in intents:
            await self._runtime.intent_emitter.emit(intent)

        return ReducerResult(state=new_state, intents=intents)
```

### Workflow Execution (Orchestrators)

The `MixinWorkflowExecution` contains **coordination logic** that becomes a runtime service.

**Migration Strategy**:

```python
# runtime/services/workflow_executor.py
class WorkflowExecutor:
    """Runtime service for workflow execution."""

    def __init__(self, runtime: "NodeRuntime"):
        self._runtime = runtime

    async def execute_workflow(
        self,
        definition: ModelWorkflowDefinition,
        steps: list[ModelWorkflowStep],
        workflow_id: UUID,
    ) -> WorkflowExecutionResult:
        """Execute workflow with runtime context."""
        # Validate workflow
        errors = await validate_workflow_definition(definition, steps)
        if errors:
            raise WorkflowValidationError(errors)

        # Get execution order (pure function)
        order = get_execution_order(steps)

        # Execute steps through runtime
        for step_id in order:
            step = self._get_step(steps, step_id)
            await self._execute_step(step)

        return WorkflowExecutionResult(...)
```

---

## Handler Protocol Interfaces (SPI)

### Protocol/Implementation Split

The handler architecture follows a strict separation:

**Protocols (interfaces)** live in `omnibase_spi`:
- `ProtocolVaultHandler` -> `omnibase_spi/protocols/handlers/vault.py`
- `ProtocolDbHandler` -> `omnibase_spi/protocols/handlers/db.py`
- `ProtocolDiscoveryService` -> `omnibase_spi/protocols/handlers/discovery.py`
- `ProtocolServiceRegistry` -> `omnibase_spi/protocols/handlers/registry.py`
- `ProtocolCLIHandler` -> `omnibase_spi/protocols/handlers/cli.py`
- `ProtocolHealthService` -> `omnibase_spi/protocols/handlers/health.py`

**Implementations** live in `omnibase_infra`:
- `VaultHandler(ProtocolVaultHandler)` -> `omnibase_infra/handlers/vault_handler.py`
- `PostgresHandler(ProtocolDbHandler)` -> `omnibase_infra/handlers/postgres_handler.py`
- `ConsulHandler(ProtocolDiscoveryService)` -> `omnibase_infra/handlers/consul_handler.py`
- `ServiceRegistryHandler(ProtocolServiceRegistry)` -> `omnibase_infra/handlers/service_registry_handler.py`
- `CLIHandler(ProtocolCLIHandler)` -> `omnibase_infra/handlers/cli_handler.py`
- `HealthHandler(ProtocolHealthService)` -> `omnibase_infra/handlers/health_handler.py`

> **Why this split?** Protocols define contracts without I/O. Implementations perform actual I/O operations (network calls, database queries, file access). The Core I/O Invariant requires all I/O to be in `omnibase_infra`.

The following protocols need to be added to `omnibase_spi`:

### ProtocolDiscoveryService

```python
# omnibase_spi/protocols/protocol_discovery_service.py
from typing import Protocol

class ProtocolDiscoveryService(Protocol):
    """Protocol for service discovery handlers."""

    def register_service(
        self,
        service_id: str,
        metadata: dict[str, Any],
    ) -> None:
        """Register a service with the discovery system."""
        ...

    def deregister_service(self, service_id: str) -> None:
        """Deregister a service."""
        ...

    def discover_services(
        self,
        service_type: str | None = None,
        tags: list[str] | None = None,
    ) -> list[ServiceEntry]:
        """Discover available services."""
        ...
```

### ProtocolServiceRegistry

```python
# omnibase_spi/protocols/protocol_service_registry.py
class ProtocolServiceRegistry(Protocol):
    """Protocol for service registry maintenance."""

    def start(self, domain_filter: str | None = None) -> None:
        """Start the registry."""
        ...

    def stop(self) -> None:
        """Stop the registry."""
        ...

    def get_registered_services(
        self,
        status_filter: str | None = None,
    ) -> list[ServiceRegistryEntry]:
        """Get registered services."""
        ...

    def get_service_by_name(
        self,
        service_name: str,
    ) -> ServiceRegistryEntry | None:
        """Get a specific service by name."""
        ...
```

### ProtocolCLIHandler

```python
# omnibase_spi/protocols/protocol_cli_handler.py
class ProtocolCLIHandler(Protocol):
    """Protocol for CLI handling."""

    def parse_args(self, args: list[str]) -> dict[str, Any]:
        """Parse command line arguments."""
        ...

    def handle_introspect(self) -> None:
        """Handle --introspect flag."""
        ...

    def handle_help(self) -> None:
        """Handle --help flag."""
        ...
```

### ProtocolHealthService

```python
# omnibase_spi/protocols/protocol_health_service.py
class ProtocolHealthService(Protocol):
    """Protocol for health check services."""

    def health_check(self) -> ModelHealthStatus:
        """Perform synchronous health check."""
        ...

    async def health_check_async(self) -> ModelHealthStatus:
        """Perform asynchronous health check."""
        ...

    def add_check(
        self,
        check: Callable[[], ModelHealthStatus],
    ) -> None:
        """Add a custom health check."""
        ...
```

---

## Seven-Step Migration Process

For each mixin, follow this process:

### Step 1: Analyze Dependencies

```bash
# Find all usages of the mixin
poetry run grep -r "MixinName" src/ tests/

# Check inheritance chains
poetry run grep -r "class.*MixinName" src/
```

### Step 2: Extract Pure Logic

- Identify pure functions that can be extracted
- Create target module in `utils/` or `domain/`
- Write unit tests for extracted functions

### Step 3: Create Protocol (if H/R)

- For Handler (H): Create SPI protocol
- For Runtime (R): Create service interface
- Add to `omnibase_spi` if cross-package

### Step 4: Implement Target

- **D**: Implement pure functions in target module
- **H**: Implement handler class with protocol
- **R**: Implement runtime service

### Step 5: Add Adapter Layer

Create temporary adapter that:
- Inherits from old mixin
- Delegates to new implementation
- Allows gradual migration

```python
# adapters/mixin_health_check_adapter.py
class MixinHealthCheckAdapter(MixinHealthCheck):
    """Adapter for gradual migration."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._health_service = HealthService(self)

    def health_check(self) -> ModelHealthStatus:
        return self._health_service.health_check()
```

### Step 6: Migrate Consumers

- Update nodes to use new implementation
- Remove mixin from inheritance chain
- Update tests

### Step 7: Delete Mixin

- Remove adapter
- Delete original mixin file
- Update `__init__.py` exports
- Run full test suite

---

## Phase Alignment

This plan aligns with [MINIMAL_RUNTIME_PHASED_PLAN.md](./MINIMAL_RUNTIME_PHASED_PLAN.md):

### Phase 0: Foundation (Already Complete)

- `MixinLogData` and `MixinNodeIntrospectionData` are already Pydantic models
- No migration needed

### Phase 1: Domain Libraries

**Duration**: 2-3 weeks

**Mixins to Migrate** (14 total):
- MixinLazyValue, MixinLazyEvaluation
- MixinSerializable, MixinCanonicalSerialization, MixinYAMLSerialization
- MixinContractMetadata, MixinIntrospectFromContract
- MixinFailFast, MixinHashComputation, MixinRedaction
- MixinNodeIdFromContract, MixinUtils
- MixinDebugDiscoveryLogging (merge into logger)

**Deliverables**:
- All D-class functions extracted to `utils/`
- Unit tests for all extracted functions
- No breaking changes to existing code

### Phase 2: Core Runtime Services

**Duration**: 3-4 weeks

**Mixins to Migrate** (12 total):
- MixinCaching, MixinCompletionData, MixinMetrics
- MixinHealthCheck, MixinNodeSetup
- MixinEventBus, MixinEventDrivenNode
- MixinEventHandler, MixinEventListener
- MixinNodeLifecycle, MixinNodeService
- MixinDiscoveryResponder

**Deliverables**:
- `NodeRuntime` class with injected services
- Protocol definitions for each service
- Integration tests for runtime

### Phase 3: Advanced Runtime + Handlers

**Duration**: 3-4 weeks

**Mixins to Migrate** (12 total):
- MixinIntrospection, MixinIntrospectionPublisher
- MixinRequestResponseIntrospection
- MixinIntentPublisher, MixinToolExecution
- MixinNodeExecutor, MixinWorkflowExecution
- MixinHybridExecution
- MixinFSMExecution, MixinContractStateReducer
- MixinDiscovery, MixinServiceRegistry, MixinCLIHandler

**Deliverables**:
- All handler implementations **in `omnibase_infra/handlers/`** (NOT core!)
- Handler protocols in `omnibase_spi/protocols/handlers/`
- Domain FSM/workflow modules in `omnibase_core/domain/`
- End-to-end tests

> **Note**: Handler implementations (MixinDiscovery, MixinServiceRegistry, MixinCLIHandler) migrate to `omnibase_infra`, not `omnibase_core`, per the Core I/O Invariant.

### Phase 4: Cleanup and Removal

**Duration**: 1-2 weeks

**Activities**:
- Remove all adapter classes
- Delete mixin files
- Update documentation
- Final test validation

---

## Risk Assessment

### High Risk Mixins

| Mixin | Risk | Mitigation |
|-------|------|------------|
| `MixinEventDrivenNode` | Foundation for many nodes | Extensive adapter period |
| `MixinNodeLifecycle` | Critical for node startup/shutdown | Parallel implementation |
| `MixinNodeExecutor` | Used in production executors | Staged rollout |

### Medium Risk Mixins

| Mixin | Risk | Mitigation |
|-------|------|------------|
| `MixinHealthCheck` | Health endpoints in production | Feature flag for new impl |
| `MixinServiceRegistry` | Service discovery critical path | Shadow mode testing |

### Low Risk Mixins

| Mixin | Risk | Mitigation |
|-------|------|------------|
| `MixinHashComputation` | Pure function, no side effects | Simple extraction |
| `MixinRedaction` | Stateless utility | Direct replacement |

---

## Success Criteria

### Phase 1 Complete

- [ ] All 14 D-class functions extracted
- [ ] 100% unit test coverage for extracted functions
- [ ] No import errors from existing code
- [ ] CI pipeline passing

### Phase 2 Complete

- [ ] `NodeRuntime` class operational
- [ ] All 12 core services implemented
- [ ] Existing nodes can use either pattern
- [ ] Performance benchmarks maintained

### Phase 3 Complete

- [ ] All handlers implemented with protocols
- [ ] FSM/workflow domain modules tested
- [ ] All 40 mixins have migration path

### Phase 4 Complete

- [ ] All mixin files deleted
- [ ] No mixin imports in codebase
- [ ] Documentation updated
- [ ] Performance maintained or improved

---

## Appendix: Mixin File Locations

```
src/omnibase_core/mixins/
├── __init__.py
├── mixin_caching.py
├── mixin_canonical_serialization.py
├── mixin_cli_handler.py
├── mixin_completion_data.py
├── mixin_contract_metadata.py
├── mixin_contract_state_reducer.py
├── mixin_debug_discovery_logging.py
├── mixin_discovery.py
├── mixin_discovery_responder.py
├── mixin_event_bus.py
├── mixin_event_driven_node.py
├── mixin_event_handler.py
├── mixin_event_listener.py
├── mixin_fail_fast.py
├── mixin_fsm_execution.py
├── mixin_hash_computation.py
├── mixin_health_check.py
├── mixin_hybrid_execution.py
├── mixin_intent_publisher.py
├── mixin_introspect_from_contract.py
├── mixin_introspection.py
├── mixin_introspection_publisher.py
├── mixin_lazy_evaluation.py
├── mixin_lazy_value.py
├── mixin_log_data.py
├── mixin_metrics.py
├── mixin_node_executor.py
├── mixin_node_id_from_contract.py
├── mixin_node_introspection_data.py
├── mixin_node_lifecycle.py
├── mixin_node_service.py
├── mixin_node_setup.py
├── mixin_redaction.py
├── mixin_request_response_introspection.py
├── mixin_serializable.py
├── mixin_service_registry.py
├── mixin_tool_execution.py
├── mixin_utils.py
├── mixin_workflow_execution.py
└── mixin_yaml_serialization.py
```

---

**Document Owner**: OmniNode Architecture Team
**Review Cycle**: Weekly during migration
**Next Review**: Phase 1 kickoff
