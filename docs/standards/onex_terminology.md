# ONEX Core Terminology

> **Version**: 1.0.0
> **Last Updated**: 2025-12-19
> **Status**: Canonical Reference
> **Purpose**: Single authoritative document defining all core ONEX concepts

---

## Table of Contents

1. [Overview](#overview)
2. [Architectural Diagram](#architectural-diagram)
3. [Core Concepts](#core-concepts)
   - [1. EVENT](#1-event)
   - [2. ACTION](#2-action)
   - [3. INTENT](#3-intent)
   - [4. REDUCER](#4-reducer)
   - [5. ORCHESTRATOR](#5-orchestrator)
   - [6. EFFECT](#6-effect)
   - [7. HANDLER](#7-handler)
   - [8. PROJECTION](#8-projection)
   - [9. RUNTIME](#9-runtime)
4. [Quick Reference Table](#quick-reference-table)
5. [When to Use Each Node Type](#when-to-use-each-node-type)
6. [Concept Relationships](#concept-relationships)
7. [Disambiguation Guide](#disambiguation-guide)
8. [Related Documentation](#related-documentation)

---

## Overview

The ONEX (Open Node Execution) framework defines a structured vocabulary for building distributed, event-driven systems. This document provides canonical definitions for the 9 core concepts that form the foundation of the ONEX architecture.

**Core Design Principles**:
- **Unidirectional Data Flow**: EFFECT -> COMPUTE -> REDUCER -> ORCHESTRATOR
- **Separation of Concerns**: Each node type has a single, well-defined responsibility
- **Declarative Configuration**: YAML contracts define behavior without custom code
- **Purity Preservation**: Reducers emit Intents instead of performing side effects

> **Python Version**: 3.12+ required. Code examples use modern Python features including `datetime.UTC` and PEP 604 union syntax (`X | None`).

---

## Architectural Diagram

```text
                          ONEX Four-Node Architecture

    +-----------+     +-----------+     +-----------+     +---------------+
    |  EFFECT   |---->|  COMPUTE  |---->|  REDUCER  |---->| ORCHESTRATOR  |
    | External  |     |   Pure    |     | FSM State |     |   Workflow    |
    |    I/O    |     | Transform |     | + Intents |     | + Actions     |
    +-----------+     +-----------+     +-----------+     +---------------+
          |                                   |                   |
          |                                   v                   v
          |                            +-----------+       +-----------+
          |                            |  INTENT   |       |  ACTION   |
          |                            | (emitted) |       | (emitted) |
          +<---------------------------+-----------+       +-----------+
                   (executed by Effect)

    +---------------------------------------------------------------------------+
    |                              RUNTIME HOST                                  |
    |  +-------------+  +-------------+  +---------------+  +-----------------+ |
    |  |  Handler    |  |  Handler    |  |   Envelope    |  |    Projection   | |
    |  |  (HTTP)     |  |  (Kafka)    |  |    Router     |  |      Store      | |
    |  +-------------+  +-------------+  +---------------+  +-----------------+ |
    +---------------------------------------------------------------------------+

    +--------------------+           +--------------------+
    |  ModelEventEnvelope|           |  ModelOnexEnvelope |
    |  (Inter-service)   |           |  (Handler I/O)     |
    +--------------------+           +--------------------+
```

---

## Core Concepts

### 1. EVENT

**Formal Definition**: A structured message wrapped in `ModelEventEnvelope` for inter-service communication, providing standardized metadata, correlation tracking, security context, QoS features, and distributed tracing.

**Key Model**: `ModelEventEnvelope[T]`

**File Location**: `src/omnibase_core/models/events/model_event_envelope.py`

**Role in Architecture**: Events are the primary communication mechanism between services. They carry payloads between nodes while maintaining correlation context and security information.

**Key Features**:
- Generic payload support (`ModelEventEnvelope[T]`)
- Correlation ID tracking for request tracing
- Distributed tracing (trace_id, span_id, request_id)
- Quality of Service (priority 1-10, timeout, retry count)
- Security context
- ONEX version compliance

**Code Example**:

```python
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from uuid import uuid4

# Create a broadcast envelope
envelope = ModelEventEnvelope.create_broadcast(
    payload={"order_id": "12345", "status": "created"},
    source_node_id=uuid4(),
    correlation_id=uuid4(),
    priority=7,
)

# Check envelope state
if envelope.is_correlated():
    print(f"Correlation ID: {envelope.correlation_id}")

if envelope.is_high_priority():  # priority >= 8
    print("Processing high-priority event")
```

**Disambiguation**:

| Context | Meaning | Model |
|---------|---------|-------|
| **Event (Envelope)** | Inter-service message wrapper | `ModelEventEnvelope[T]` |
| **Event (FSM trigger)** | State machine transition trigger | String trigger in FSM contract |
| **Event (messaging)** | Generic message on event bus | Payload inside envelope |

---

### 2. ACTION

**Formal Definition**: An Orchestrator-issued command with lease-based ownership for coordinating distributed workflows with single-writer semantics.

**Key Model**: `ModelAction`

**File Location**: `src/omnibase_core/models/orchestrator/model_action.py`

**Role in Architecture**: Actions are emitted exclusively by Orchestrator nodes to coordinate work across downstream nodes (COMPUTE, EFFECT, REDUCER). They enforce single-writer semantics through lease management.

**Key Features**:
- Lease-based ownership (`lease_id` proves Orchestrator authority)
- Epoch-based optimistic concurrency control
- Dependency tracking for execution ordering
- Priority-based execution scheduling
- Timeout enforcement

**Code Example**:

```python
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.enums.enum_orchestrator_types import EnumActionType
from uuid import uuid4
from datetime import datetime, UTC

# Orchestrator emits action with lease proof
action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.COMPUTE,
    target_node_type="NodeDataTransformerCompute",
    payload={"transformation": "normalize"},
    lease_id=orchestrator_lease_id,  # Proves ownership
    epoch=current_epoch,              # Version tracking
    priority=5,
    timeout_ms=10000,
)
```

**Important Clarification**: "Command" is NOT a formal ONEX concept. Use "Action" for Orchestrator-issued commands. The term "command" may appear in documentation as an English noun describing what Actions represent, but `ModelAction` is the canonical model.

> **Note**: `ModelAction` is primarily used internally by Orchestrator nodes. Application code typically interacts with Actions indirectly through workflow definitions in YAML contracts.

---

### 3. INTENT

**Formal Definition**: A declarative side effect specification emitted by a pure Reducer, to be executed by an Effect node. Intents maintain Reducer purity by separating the decision of "what should happen" from the execution of "how it happens."

**Key Models**:
- `ModelIntent` (Extension): Open set for plugins and experiments
- `ModelCoreIntent` (Core): Discriminated union for core infrastructure

**File Location**: `src/omnibase_core/models/reducer/model_intent.py`

**Role in Architecture**: Intents implement the Pure FSM pattern where Reducers describe side effects without executing them:

```text
delta(state, action) -> (new_state, intents[])
```

**Two-Tier Intent System**:

| Tier | Model | Purpose | Use When |
|------|-------|---------|----------|
| **Core Intents** | `ModelCoreIntent` | Discriminated union with compile-time safety | Registration, persistence, lifecycle |
| **Extension Intents** | `ModelIntent` | Open set with runtime validation | Plugins, experiments, third-party integrations |

**Code Example**:

```python
from omnibase_core.models.reducer.model_intent import ModelIntent
from uuid import uuid4

# Reducer emits intent for database write (does NOT execute it)
intent = ModelIntent(
    intent_id=uuid4(),
    intent_type="database_write",
    target="orders_table",
    payload={
        "operation": "insert",
        "data": {"order_id": "12345", "status": "pending"},
    },
    priority=5,
    lease_id=workflow_lease_id,  # Optional workflow tracking
    epoch=current_epoch,          # Optional version tracking
)

# Return from Reducer (pure - no side effects executed)
return ModelReducerOutput(
    result=new_state,
    intents=[intent],  # Effect node will execute these
)
```

---

### 4. REDUCER

**Formal Definition**: An FSM-driven node for pure state management that processes inputs and emits state transitions plus Intents for side effects, without performing I/O directly.

**Key Class**: `NodeReducer`

**File Location**: `src/omnibase_core/nodes/node_reducer.py`

**Role in Architecture**: Third node in the pipeline (EFFECT -> COMPUTE -> REDUCER -> ORCHESTRATOR). Implements pure finite state machine logic.

**Key Features**:
- Pure FSM pattern: `delta(state, action) -> (new_state, intents[])`
- YAML-driven state machine definitions
- No direct side effects (all I/O delegated via Intents)
- State history tracking
- Terminal state detection

**Code Example**:

```python
from omnibase_core.nodes import NodeReducer, ModelReducerInput, ModelReducerOutput
from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeOrderProcessingReducer(NodeReducer):
    """
    FSM-driven reducer for order state management.

    States defined in YAML contract:
    - pending -> processing (trigger: start_processing)
    - processing -> completed (trigger: complete)
    - processing -> failed (trigger: fail)
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        # FSM contract auto-loaded from node contract
        # No additional initialization needed

# Usage
node = NodeOrderProcessingReducer(container)
input_data = ModelReducerInput(
    data=[{"order_id": "12345"}],
    reduction_type=EnumReductionType.AGGREGATE,
    metadata={"trigger": "start_processing"},
)

result = await node.process(input_data)
print(f"New state: {result.metadata['fsm_state']}")
print(f"Intents emitted: {len(result.intents)}")
```

---

### 5. ORCHESTRATOR

**Formal Definition**: A workflow-driven node for coordinating multi-step workflows across distributed nodes, using Actions with lease-based single-writer semantics.

**Key Class**: `NodeOrchestrator`

**File Location**: `src/omnibase_core/nodes/node_orchestrator.py`

**Role in Architecture**: Fourth (final) node in the pipeline. Coordinates workflow execution across EFFECT, COMPUTE, and REDUCER nodes.

**Key Features**:
- YAML-driven workflow definitions
- Action emission for deferred execution
- Dependency-aware topological ordering
- Sequential, parallel, and batch execution modes
- Lease-based single-writer semantics
- Cycle detection in workflow graphs

**Code Example**:

```python
from omnibase_core.nodes import (
    NodeOrchestrator,
    ModelOrchestratorInput,
    EnumExecutionMode,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from uuid import uuid4

class NodeDataPipelineOrchestrator(NodeOrchestrator):
    """
    Workflow-driven orchestrator for data processing pipeline.

    Workflow defined in YAML contract:
    1. fetch_data (EFFECT) -> 2. validate (COMPUTE) -> 3. store (EFFECT)
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        # Workflow definition auto-loaded from contract

# Usage
node = NodeDataPipelineOrchestrator(container)
input_data = ModelOrchestratorInput(
    workflow_id=uuid4(),
    steps=[
        {"step_id": uuid4(), "step_name": "Fetch", "step_type": "effect"},
        {"step_id": uuid4(), "step_name": "Validate", "step_type": "compute"},
    ],
    execution_mode=EnumExecutionMode.PARALLEL,
)

result = await node.process(input_data)
print(f"Status: {result.execution_status}")
print(f"Actions emitted: {len(result.actions_emitted)}")
```

---

### 6. EFFECT

**Formal Definition**: A contract-driven node for executing external I/O operations including database access, API calls, file operations, and event emission.

**Key Class**: `NodeEffect`

**File Location**: `src/omnibase_core/nodes/node_effect.py`

**Role in Architecture**: First node in the pipeline (EFFECT -> COMPUTE -> REDUCER -> ORCHESTRATOR). Handles all external system interactions.

**Key Features**:
- External I/O execution (database, HTTP, files, message queues)
- Transaction support with rollback capabilities
- Retry policies with exponential backoff
- Circuit breaker integration
- Intent execution (consumes Intents emitted by Reducers)

**Code Example**:

```python
from omnibase_core.nodes import NodeEffect, ModelEffectInput, ModelEffectOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeDatabaseWriterEffect(NodeEffect):
    """
    EFFECT node for database write operations.

    Handles:
    - Intent execution from Reducers
    - Transaction management
    - Retry logic with circuit breaker
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.db_pool = container.get_service("ProtocolDatabasePool")

    async def execute_effect(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """Execute database write with transaction support."""
        async with self.transaction_context() as tx:
            result = await self.db_pool.execute(
                input_data.operation_config.query,
                input_data.operation_config.parameters,
            )
            tx.add_operation(
                "write",
                input_data.operation_config,
                rollback_fn=lambda: self.db_pool.rollback(),
            )

        return ModelEffectOutput(
            correlation_id=input_data.correlation_id,
            operation_result=result,
            success=True,
        )
```

---

### 7. HANDLER

**Formal Definition**: An execution unit that processes operations by type, implementing the `ProtocolHandler` interface for runtime routing.

**Key Protocol**: `ProtocolHandler`

**File Location**: `src/omnibase_core/protocols/runtime/protocol_handler.py`

**Role in Architecture**: Handlers are execution units within the Runtime that process `ModelOnexEnvelope` instances. The `EnvelopeRouter` routes envelopes to handlers based on `handler_type`.

**Three Handler Sub-Patterns**:

| Pattern | Description | Example |
|---------|-------------|---------|
| **Protocol Handler** | I/O execution (implements `ProtocolHandler`) | HTTP, Database, Kafka handlers |
| **Event Handler** | Pub/sub event handling (via `MixinEventHandler`) | Subscription-based event processing |
| **CLI Handler** | Command-line interface (via `MixinCLIHandler`) | CLI command processing |

**Code Example**:

```python
from omnibase_core.protocols.runtime import ProtocolHandler
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.types.typed_dict_handler_metadata import TypedDictHandlerMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer

class HttpHandler:
    """HTTP handler implementation."""

    @property
    def handler_type(self) -> EnumHandlerType:
        return EnumHandlerType.HTTP

    async def execute(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
        """Execute HTTP request based on envelope payload."""
        url = envelope.payload.get("url")
        method = envelope.payload.get("method", "GET")

        response = await self._http_client.request(method, url)

        return ModelOnexEnvelope.create_response(
            request=envelope,
            payload={"status": response.status, "body": response.body},
            success=response.status < 400,
        )

    def describe(self) -> TypedDictHandlerMetadata:
        return {
            "name": "http_handler",
            "version": ModelSemVer(major=1, minor=0, patch=0),
            "description": "HTTP request handler",
            "capabilities": ["GET", "POST", "PUT", "DELETE"],
        }

# Verify protocol compliance
handler: ProtocolHandler = HttpHandler()
assert isinstance(handler, ProtocolHandler)  # True with @runtime_checkable
```

---

### 8. PROJECTION

**Formal Definition**: Read-optimized materialized views for CQRS patterns, providing eventual consistency via watermark tracking and version gating.

**Key Model**: `ModelProjectionBase`

**File Location**: `src/omnibase_core/models/projection/model_projection_base.py`

**Role in Architecture**: Projections are materialized views of canonical state, optimized for read operations. They support eventual consistency through version tracking.

**Key Features**:
- Key-version mapping to canonical state
- Watermark tracking for consistency
- Version gating for read operations
- Fallback to canonical state when projection lags

**Code Example**:

```python
from omnibase_core.models.projection.model_projection_base import ModelProjectionBase
from pydantic import Field
from datetime import datetime, UTC
from typing import Any

class ModelWorkflowProjection(ModelProjectionBase):
    """
    Projection for workflow state, optimized for queries.

    Indexed fields enable fast lookups by status and namespace.
    """

    tag: str = Field(
        ...,
        description="Workflow status (PENDING, PROCESSING, COMPLETED)",
    )
    namespace: str = Field(
        ...,
        description="Multi-tenant isolation namespace",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )
    indices: dict[str, Any] | None = Field(
        default=None,
        description="Custom query indices",
    )

# Usage in projection store
projection = await proj_store.get_state(
    key=workflow_key,
    required_version=5,  # Wait until projection reaches v5
    max_wait_ms=100,
)

if projection is None:
    # Projection lagging, fallback to canonical
    canonical = await canonical_store.get_state(key=workflow_key)
```

**Note**: There is no explicit "Projector" class in omnibase_core. Projection materialization is handled by application-level components that subscribe to state change events.

---

### 9. RUNTIME

**Formal Definition**: The execution environment that hosts ONEX nodes, managing envelope routing, handler registration, and service lifecycle.

**Node Kind**: `RUNTIME_HOST` (infrastructure type, not a core pipeline node)

**Key Components**:

| Component | Description | Location |
|-----------|-------------|----------|
| `EnvelopeRouter` | Transport-agnostic orchestrator | `src/omnibase_core/runtime/envelope_router.py` |
| `RuntimeNodeInstance` | Node instance wrapper | `src/omnibase_core/runtime/` |
| `ModelONEXContainer` | DI container for services | `src/omnibase_core/models/container/model_onex_container.py` |

**Disambiguation**:

| Type | Description | Characteristics |
|------|-------------|-----------------|
| **NodeRuntime** (Core) | Pure runtime logic | No event loop, deterministic |
| **RuntimeHostProcess** (Infrastructure) | Process with event loop | Manages lifecycle, I/O multiplexing |

**Code Example**:

```python
from omnibase_core.runtime.envelope_router import EnvelopeRouter
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Initialize DI container
container = ModelONEXContainer()
container.register_service("ProtocolLogger", logger_instance)
container.register_service("ProtocolEventBus", event_bus_instance)

# Create envelope router
router = EnvelopeRouter(container)

# Register handlers
router.register_handler(HttpHandler())
router.register_handler(DatabaseHandler())
router.register_handler(KafkaHandler())

# Route envelope to appropriate handler
response = await router.route(incoming_envelope)
```

---

## Quick Reference Table

| Concept | Model/Class | File Location | Pipeline Position |
|---------|-------------|---------------|-------------------|
| **EVENT** | `ModelEventEnvelope[T]` | `models/events/model_event_envelope.py` | Transport layer |
| **ACTION** | `ModelAction` | `models/orchestrator/model_action.py` | Emitted by ORCHESTRATOR |
| **INTENT** | `ModelIntent` | `models/reducer/model_intent.py` | Emitted by REDUCER |
| **REDUCER** | `NodeReducer` | `nodes/node_reducer.py` | Position 3 |
| **ORCHESTRATOR** | `NodeOrchestrator` | `nodes/node_orchestrator.py` | Position 4 (final) |
| **EFFECT** | `NodeEffect` | `nodes/node_effect.py` | Position 1 |
| **HANDLER** | `ProtocolHandler` | `protocols/runtime/protocol_handler.py` | Runtime layer |
| **PROJECTION** | `ModelProjectionBase` | `models/projection/model_projection_base.py` | CQRS read side |
| **RUNTIME** | `EnvelopeRouter` | `runtime/envelope_router.py` | Infrastructure |

---

## When to Use Each Node Type

Use this decision guide to select the appropriate node type for your use case:

| If you need to... | Use | Example |
|-------------------|-----|---------|
| Read/write external data (DB, API, files) | **EFFECT** | Database queries, HTTP calls, file I/O |
| Transform data without side effects | **COMPUTE** | Data validation, format conversion, calculations |
| Manage state with FSM transitions | **REDUCER** | Order status workflow, user session state |
| Coordinate multi-step workflows | **ORCHESTRATOR** | ETL pipelines, saga patterns, batch processing |

### Decision Flowchart

```text
Start
  |
  +-- Does it involve external I/O? --Yes--> EFFECT
  |
  +-- Is it pure data transformation? --Yes--> COMPUTE
  |
  +-- Does it manage state transitions? --Yes--> REDUCER
  |
  +-- Does it coordinate multiple nodes? --Yes--> ORCHESTRATOR
```

### Common Patterns

| Pattern | Node Combination | Description |
|---------|------------------|-------------|
| **Read-Transform-Write** | EFFECT -> COMPUTE -> EFFECT | Fetch data, transform, persist |
| **Event-Sourced State** | EFFECT -> REDUCER | Event ingestion with FSM state |
| **Orchestrated Pipeline** | ORCHESTRATOR -> (EFFECT, COMPUTE, REDUCER) | Workflow-driven processing |
| **Pure Transformation** | COMPUTE only | Stateless data processing |

---

## Concept Relationships

```text
                     Emits Actions
    +---------------+--------------->+---------------+
    | ORCHESTRATOR  |                |    Action     |
    | (Coordinates) |                | (lease_id,    |
    +-------^-------+                |  epoch)       |
            |                        +---------------+
            | Pipeline flow                  |
            |                                v
    +-------+-------+                Target nodes
    |    REDUCER    |                (COMPUTE, EFFECT,
    | (Pure FSM)    |                 REDUCER)
    +-------+-------+
            |
            | Emits Intents
            v
    +---------------+
    |    Intent     |
    | (side effect  |
    |  declaration) |
    +-------+-------+
            |
            | Executed by
            v
    +---------------+
    |    EFFECT     |
    | (External I/O)|
    +---------------+
            |
            | Wraps in
            v
    +---------------+
    | EventEnvelope |
    | (Transport)   |
    +-------+-------+
            |
            | Routed by
            v
    +---------------+
    |   RUNTIME     |
    | (EnvelopeRouter|
    |  + Handlers)  |
    +---------------+
            |
            | Materialize to
            v
    +---------------+
    |  PROJECTION   |
    | (Read views)  |
    +---------------+
```

---

## Disambiguation Guide

### Event Variations

| Term | Context | Meaning |
|------|---------|---------|
| `ModelEventEnvelope` | Inter-service transport | Wrapper with metadata, correlation, QoS |
| FSM Event/Trigger | Reducer state machine | String trigger for state transitions |
| Domain Event | Business logic | Application-specific event payload |

### Command vs Action

| Term | Status | Use |
|------|--------|-----|
| **Action** | Canonical | Formal ONEX concept (`ModelAction`) |
| **Command** | Informal | English noun describing Actions |

**Rule**: Always use "Action" in code and formal documentation.

### Handler Variations

| Type | Interface | Purpose |
|------|-----------|---------|
| **Protocol Handler** | `ProtocolHandler` | I/O execution (HTTP, DB, Kafka) |
| **Event Handler** | `MixinEventHandler` | Pub/sub event processing |
| **CLI Handler** | `MixinCLIHandler` | Command-line processing |

### Runtime Variations

| Type | Characteristics | Use Case |
|------|-----------------|----------|
| **NodeRuntime** (Core) | Pure, no event loop | Logic testing, deterministic execution |
| **RuntimeHostProcess** (Infra) | Event loop, lifecycle | Production deployment |

---

## Related Documentation

| Topic | Document |
|-------|----------|
| Four-Node Architecture | `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md` |
| Intent Architecture | `docs/architecture/MODEL_INTENT_ARCHITECTURE.md` |
| Action Architecture | `docs/architecture/MODEL_ACTION_ARCHITECTURE.md` |
| Terminology Guide | `docs/conventions/TERMINOLOGY_GUIDE.md` |
| Node Building Guide | `docs/guides/node-building/README.md` |
| Pure FSM Pattern | `docs/patterns/PURE_FSM_REDUCER_PATTERN.md` |
| Lease Management | `docs/patterns/LEASE_MANAGEMENT_PATTERN.md` |
| Threading Guide | `docs/guides/THREADING.md` |
| Declarative Nodes Migration | `docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md` |
| EnumNodeKind Migration | `docs/guides/ENUM_NODE_KIND_MIGRATION.md` |

---

**Document Version**: 1.0.0
**Created**: 2025-12-19
**Author**: ONEX Framework Team
**Linear Ticket**: OMN-931

**Changelog**:
- 1.0.0 (2025-12-19): Initial canonical terminology document
