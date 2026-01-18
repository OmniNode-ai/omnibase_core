> **Navigation**: [Home](../index.md) > [Architecture](./overview.md) > Canonical Execution Shapes
> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# ONEX Canonical Execution Shapes

> **Version**: 1.0.0
> **Ticket**: OMN-933
> **Status**: Specification
> **Last Updated**: 2025-12-19

## Overview

This document defines the **canonical execution shapes** for the ONEX Four-Node Architecture. These shapes establish the architectural constraints that all ONEX components must follow to maintain predictable data flow, testability, and system integrity.

The ONEX architecture enforces **unidirectional data flow** through four specialized node types:

```text
EFFECT ──────> COMPUTE ──────> REDUCER ──────> ORCHESTRATOR
  │               │               │                │
  │               │               │                │
External I/O   Pure Transform   FSM State      Workflow
APIs, DB,      Validation,      Transitions,   Coordination,
Files          Algorithms       Intent Emit    Action Emit
```

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Allowed Execution Shapes](#allowed-execution-shapes)
3. [Forbidden Patterns](#forbidden-patterns)
4. [Why These Constraints Matter](#why-these-constraints-matter)
5. [Decision Matrix](#decision-matrix)
6. [Enforcement](#enforcement)
7. [Registration-Specific Execution Shapes](#registration-specific-execution-shapes)
8. [Related Documentation](#related-documentation)

---

## Core Principles

### The Four-Node Architecture

ONEX uses four specialized node types, each with distinct responsibilities:

| Node Type | Symbol | Purpose | Purity |
|-----------|--------|---------|--------|
| **EFFECT** | `[E]` | External I/O (APIs, databases, files) | Impure (side effects allowed) |
| **COMPUTE** | `[C]` | Data transformation and algorithms | Pure (deterministic) |
| **REDUCER** | `[R]` | FSM state management via Intent emission | Pure (no direct I/O) |
| **ORCHESTRATOR** | `[O]` | Workflow coordination via Action emission | Coordination layer |

### Unidirectional Data Flow

The ONEX pattern enforces left-to-right data flow:

```text
                    DATA FLOW DIRECTION
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶

    ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────────┐
    │ EFFECT  │────▶│ COMPUTE │────▶│ REDUCER │────▶│ORCHESTRATOR │
    │   [E]   │     │   [C]   │     │   [R]   │     │    [O]      │
    └─────────┘     └─────────┘     └─────────┘     └─────────────┘
         │                                                  │
         │                                                  │
    ┌────▼────┐                                    ┌────────▼────────┐
    │External │                                    │  Emits Actions  │
    │ World   │◀───────────────────────────────────│  to [E] nodes   │
    └─────────┘                                    └─────────────────┘

    Key: ────▶ Direct data flow
         ◀──── Action/Intent execution (via event bus, not direct call)
```

**Rules**:
- No backwards dependencies between adjacent nodes
- Cross-cutting coordination happens via Intents (Reducer) and Actions (Orchestrator)
- Effect nodes execute Intents and Actions from the event bus

---

## Allowed Execution Shapes

### Shape 1: Event to Orchestrator

**Purpose**: Workflow coordination triggered by external events

```text
    ┌─────────────────────────────────────────────────────────────┐
    │                    Event → Orchestrator                      │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐
    │   External   │          │  ORCHESTRATOR   │
    │    Event     │─────────▶│      [O]        │
    │              │          │                 │
    │ (Kafka,      │          │ Coordinates     │
    │  Webhook,    │          │ workflow via    │
    │  Timer)      │          │ ModelAction     │
    └──────────────┘          └────────┬────────┘
                                       │
                                       ▼
                              ┌────────────────┐
                              │ Emits Actions  │
                              │ to downstream  │
                              │ nodes via bus  │
                              └────────────────┘
```

**Use Cases**:
- Scheduled job triggers multi-step workflow
- Webhook initiates data processing pipeline
- Timer-based batch processing coordination

**Example**:
```python
# Event arrives from Kafka topic
@event_handler("order.created")
async def handle_order_created(event: OrderCreatedEvent):
    # Orchestrator coordinates the workflow
    orchestrator = NodeOrderProcessingOrchestrator(container)

    # Acquire lease for single-writer semantics
    lease = await orchestrator.acquire_lease(event.order_id)

    # Emit actions to downstream nodes
    action = ModelAction(
        action_type=EnumActionType.EFFECT,
        target_node_type="NodePaymentProcessorEffect",
        lease_id=lease.lease_id,
        epoch=lease.epoch,
        payload={"order_id": event.order_id}
    )
    await orchestrator.emit_action(action)
```

---

### Shape 2: Event to Reducer

**Purpose**: State transitions triggered by domain events

```text
    ┌─────────────────────────────────────────────────────────────┐
    │                     Event → Reducer                          │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐
    │   Domain     │          │    REDUCER      │
    │    Event     │─────────▶│      [R]        │
    │              │          │                 │
    │ (State       │          │ Pure FSM:       │
    │  change      │          │ delta(state,    │
    │  trigger)    │          │ event) →        │
    └──────────────┘          │ (new_state,     │
                              │  intents[])     │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌────────────────┐
                              │ Emits Intents  │
                              │ for side       │
                              │ effects        │
                              └────────────────┘
```

**Use Cases**:
- Order status updates (PLACED → PAID → SHIPPED)
- User account state changes
- Inventory level adjustments

**Example**:
```python
# Domain event triggers state transition
async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
    current_state = input_data.state
    event = input_data.event

    # Pure FSM transition
    transition_result = self._apply_fsm_transition(
        current_state,
        event.action,
        event.payload
    )

    # Emit intents for side effects (DB write, notification)
    intents = [
        ModelIntent(
            intent_type=EnumIntentType.DATABASE_WRITE,
            target="orders_table",
            payload={"data": transition_result.new_state}
        ),
        ModelIntent(
            intent_type=EnumIntentType.NOTIFICATION,
            target="email_service",
            payload={"template": "order_status_update"}
        )
    ]

    return ModelReducerOutput(
        result=transition_result.new_state,
        intents=intents
    )
```

---

### Shape 3: Intent to Effect

**Purpose**: Effect nodes execute Intents emitted by Reducers

```text
    ┌─────────────────────────────────────────────────────────────┐
    │                     Intent → Effect                          │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐          ┌──────────┐
    │  REDUCER     │          │    EFFECT       │          │ External │
    │    [R]       │─────────▶│      [E]        │─────────▶│ System   │
    │              │          │                 │          │          │
    │ Emits        │  Intent  │ Executes        │  I/O     │ Database │
    │ ModelIntent  │  Queue   │ the intent      │  Call    │ API, etc │
    └──────────────┘          └─────────────────┘          └──────────┘

    Intent Queue Flow:
    ┌─────────────────────────────────────────────────────────────┐
    │ [R] → emit(Intent) → Queue → [E] consumes → Execute → Done │
    └─────────────────────────────────────────────────────────────┘
```

**Pure FSM Pattern**:
```text
delta(state, action) → (new_state, intents[])

Where:
- Reducer describes WHAT should happen (Intent)
- Effect determines HOW to execute it
```

**Use Cases**:
- Database writes requested by Reducer
- Email notifications triggered by state changes
- API calls to external services
- Cache updates

**Example**:
```python
# Effect node processes Intents from queue
class NodeIntentExecutorEffect(NodeEffect):
    async def execute_intents(self, intents: list[ModelIntent]) -> list[IntentResult]:
        results = []

        # Sort by priority (higher first)
        sorted_intents = sorted(intents, key=lambda i: i.priority, reverse=True)

        for intent in sorted_intents:
            if intent.intent_type == EnumIntentType.DATABASE_WRITE:
                result = await self._execute_database_write(intent)
            elif intent.intent_type == EnumIntentType.NOTIFICATION:
                result = await self._execute_notification(intent)
            elif intent.intent_type == EnumIntentType.API_CALL:
                result = await self._execute_api_call(intent)

            results.append(IntentResult(intent_id=intent.intent_id, status="completed"))

        return results
```

---

### Shape 4: Command to Orchestrator

**Purpose**: External commands trigger workflow coordination

```text
    ┌─────────────────────────────────────────────────────────────┐
    │                  Command → Orchestrator                      │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐
    │   Command    │          │  ORCHESTRATOR   │
    │   (API,      │─────────▶│      [O]        │
    │    CLI,      │          │                 │
    │    Event)    │          │ Acquires lease  │
    └──────────────┘          │ Coordinates     │
                              │ multi-step      │
                              │ workflow        │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌────────────────────────────┐
                              │     Workflow Steps         │
                              │                            │
                              │  Action1 → [E] (fetch)     │
                              │      │                     │
                              │      ▼                     │
                              │  Action2 → [C] (transform) │
                              │      │                     │
                              │      ▼                     │
                              │  Action3 → [R] (reduce)    │
                              │      │                     │
                              │      ▼                     │
                              │  Action4 → [E] (persist)   │
                              └────────────────────────────┘
```

**Use Cases**:
- User initiates data import workflow
- Admin triggers batch processing
- Scheduled job starts ETL pipeline

**Example**:
```python
# Command triggers orchestrator
@api_endpoint("/api/import", methods=["POST"])
async def start_import(request: ImportRequest):
    orchestrator = NodeDataImportOrchestrator(container)

    # Acquire exclusive lease
    lease = await orchestrator.acquire_lease(
        workflow_id=uuid4(),
        lease_duration=timedelta(minutes=30)
    )

    # Define workflow steps with dependencies
    fetch_action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.EFFECT,
        target_node_type="NodeAPIFetcherEffect",
        lease_id=lease.lease_id,
        epoch=0
    )

    transform_action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.COMPUTE,
        target_node_type="NodeDataTransformerCompute",
        dependencies=[fetch_action.action_id],
        lease_id=lease.lease_id,
        epoch=1
    )

    # Execute workflow
    await orchestrator.execute_workflow([fetch_action, transform_action])
```

---

### Shape 5: Command to Effect

**Purpose**: Direct external operations without orchestration

```text
    ┌─────────────────────────────────────────────────────────────┐
    │                     Command → Effect                         │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐          ┌──────────┐
    │   Command    │          │    EFFECT       │          │ External │
    │              │─────────▶│      [E]        │─────────▶│ System   │
    │ (Simple      │          │                 │          │          │
    │  operation)  │          │ Single I/O      │          │ Database │
    └──────────────┘          │ operation       │          │ API, etc │
                              └─────────────────┘          └──────────┘
```

**Use Cases**:
- Simple CRUD operations
- Health checks
- Configuration reads
- Cache invalidation

**Example**:
```python
# Direct command to Effect node
@api_endpoint("/api/users/{user_id}", methods=["GET"])
async def get_user(user_id: UUID):
    effect = NodeUserFetcherEffect(container)

    result = await effect.process(
        ModelEffectInput(user_id=user_id)
    )

    return result.data
```

---

### Shape 6: Action to Effect (from Orchestrator)

**Purpose**: Orchestrator delegates I/O operations to Effect nodes

```text
    ┌─────────────────────────────────────────────────────────────┐
    │              Orchestrator Action → Effect                    │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐          ┌──────────┐
    │ ORCHESTRATOR │          │    EFFECT       │          │ External │
    │     [O]      │─────────▶│      [E]        │─────────▶│ System   │
    │              │          │                 │          │          │
    │ Emits        │  Action  │ Validates       │  I/O     │          │
    │ ModelAction  │  Queue   │ lease_id,       │  Call    │          │
    │              │          │ epoch then      │          │          │
    │              │          │ executes        │          │          │
    └──────────────┘          └─────────────────┘          └──────────┘

    Lease Validation:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. Verify lease_id matches workflow owner                    │
    │ 2. Verify epoch >= last_processed_epoch                      │
    │ 3. Execute action                                            │
    │ 4. Update last_processed_epoch                               │
    └─────────────────────────────────────────────────────────────┘
```

**Single-Writer Semantics**:
- Only the lease-holding Orchestrator can issue Actions
- Epoch versioning prevents stale action execution
- Actions are validated before execution

---

### Shape 7: Data Pipeline (Complete Flow)

**Purpose**: Full EFFECT → COMPUTE → REDUCER → ORCHESTRATOR pipeline

```text
    ┌─────────────────────────────────────────────────────────────┐
    │                   Complete Data Pipeline                     │
    └─────────────────────────────────────────────────────────────┘

    External                                           Coordinated
     Input                                               Output
       │                                                    ▲
       │                                                    │
       ▼                                                    │
    ┌──────┐     ┌──────┐     ┌──────┐     ┌────────────┐  │
    │ [E]  │────▶│ [C]  │────▶│ [R]  │────▶│    [O]     │──┘
    │      │     │      │     │      │     │            │
    │Fetch │     │Trans-│     │Aggre-│     │Coordinate  │
    │Data  │     │form  │     │gate  │     │Workflow    │
    └──────┘     └──────┘     └──────┘     └────────────┘
       │                         │               │
       │                         │               │
       ▼                         ▼               ▼
    External                  Intents         Actions
    Systems                   (to [E])        (to [E])

    Example: Order Processing Pipeline
    ┌────────────────────────────────────────────────────────────┐
    │ [E] Fetch order  →  [C] Validate  →  [R] Update state  →   │
    │        │                 │                  │               │
    │        ▼                 ▼                  ▼               │
    │    Raw order         Validated          New state +        │
    │    from API          order data         Intents for        │
    │                                         DB write           │
    │                                              │              │
    │                                              ▼              │
    │ [O] Coordinate payment → fulfillment → notification        │
    └────────────────────────────────────────────────────────────┘
```

---

## Forbidden Patterns

### Pattern 1: Command to Reducer (FORBIDDEN)

```text
    ┌─────────────────────────────────────────────────────────────┐
    │               FORBIDDEN: Command → Reducer                   │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐
    │   Command    │    ╳     │    REDUCER      │
    │              │────╳────▶│      [R]        │
    │              │    ╳     │                 │
    └──────────────┘          └─────────────────┘

    WHY FORBIDDEN:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. Bypasses orchestration layer                              │
    │ 2. No lease management = no single-writer guarantees         │
    │ 3. State changes without workflow context                    │
    │ 4. Inconsistent state across distributed system              │
    │ 5. No dependency tracking between operations                 │
    └─────────────────────────────────────────────────────────────┘
```

**Rationale**: Reducers manage FSM state transitions. Direct commands bypass the Orchestrator's lease-based coordination, leading to race conditions and inconsistent state.

**Correct Alternative**:
```text
    Command → [O] Orchestrator → (via Action) → [R] Reducer
```

---

### Pattern 2: Reducer to I/O (FORBIDDEN)

```text
    ┌─────────────────────────────────────────────────────────────┐
    │               FORBIDDEN: Reducer → I/O                       │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐
    │   REDUCER    │    ╳     │    External     │
    │     [R]      │────╳────▶│    System       │
    │              │    ╳     │   (DB, API)     │
    └──────────────┘          └─────────────────┘

    WHY FORBIDDEN:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. Reducers must be PURE (no side effects)                   │
    │ 2. Direct I/O breaks determinism                             │
    │ 3. I/O failures contaminate state logic                      │
    │ 4. Cannot test FSM transitions without mocking I/O           │
    │ 5. Violates: delta(state, action) → (new_state, intents[])  │
    └─────────────────────────────────────────────────────────────┘
```

**Rationale**: Reducers implement pure FSM logic. Direct I/O operations violate purity, making state transitions non-deterministic and difficult to test.

**Correct Alternative**:
```text
    [R] Reducer emits Intent → Queue → [E] Effect executes I/O
```

---

### Pattern 3: Effect to Reducer (FORBIDDEN)

```text
    ┌─────────────────────────────────────────────────────────────┐
    │               FORBIDDEN: Effect → Reducer                    │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐
    │   EFFECT     │    ╳     │    REDUCER      │
    │     [E]      │────╳────▶│      [R]        │
    │              │    ╳     │                 │
    └──────────────┘          └─────────────────┘

    WHY FORBIDDEN:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. Violates unidirectional data flow                         │
    │ 2. Effect nodes don't manage state                           │
    │ 3. Creates circular dependencies                             │
    │ 4. Bypasses Compute layer for data transformation            │
    │ 5. Makes data flow unpredictable                             │
    └─────────────────────────────────────────────────────────────┘
```

**Rationale**: Data flows left-to-right: EFFECT → COMPUTE → REDUCER. Effect nodes fetch/write data but don't directly update state machines.

**Correct Alternative**:
```text
    [E] Effect → [C] Compute (transform) → [R] Reducer (state transition)
```

---

### Pattern 4: Compute to External I/O (FORBIDDEN)

```text
    ┌─────────────────────────────────────────────────────────────┐
    │               FORBIDDEN: Compute → External I/O              │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐
    │   COMPUTE    │    ╳     │    External     │
    │     [C]      │────╳────▶│    System       │
    │              │    ╳     │   (DB, API)     │
    └──────────────┘          └─────────────────┘

    WHY FORBIDDEN:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. Compute nodes must be PURE (deterministic)                │
    │ 2. I/O makes transformations non-reproducible                │
    │ 3. Cannot cache computation results safely                   │
    │ 4. Parallel execution becomes unsafe                         │
    │ 5. Violates separation of concerns                           │
    └─────────────────────────────────────────────────────────────┘
```

**Rationale**: Compute nodes perform pure data transformations. I/O operations belong exclusively in Effect nodes.

**Correct Alternative**:
```text
    [E] Effect (fetch data) → [C] Compute (transform) → [E] Effect (persist)
```

---

### Pattern 5: Circular Dependencies (FORBIDDEN)

```text
    ┌─────────────────────────────────────────────────────────────┐
    │               FORBIDDEN: Circular Dependencies               │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────┐          ┌─────────────────┐
    │   Node A     │─────────▶│    Node B       │
    │              │          │                 │
    │              │◀─────────│                 │
    └──────────────┘    ╳     └─────────────────┘

    Example:
    [E] ◀──╳──▶ [C] ◀──╳──▶ [R] ◀──╳──▶ [O]
        ╳                              ╳
        └──────────────╳───────────────┘

    WHY FORBIDDEN:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. Deadlocks in distributed systems                          │
    │ 2. Infinite loops in workflow execution                      │
    │ 3. Unpredictable execution order                             │
    │ 4. Memory leaks from unbounded recursion                     │
    │ 5. Cannot reason about data flow                             │
    └─────────────────────────────────────────────────────────────┘
```

**Rationale**: ONEX enforces directed acyclic graph (DAG) execution. Circular dependencies create infinite loops and deadlocks.

**Correct Alternative**:
```text
    Use Orchestrator to coordinate multi-step workflows:
    [O] → [E] → [C] → [R] → (result back to [O] for next phase)
```

---

### Pattern 6: Orchestrator Direct I/O (FORBIDDEN)

```text
    ┌─────────────────────────────────────────────────────────────┐
    │               FORBIDDEN: Orchestrator → Direct I/O           │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────────┐          ┌─────────────────┐
    │   ORCHESTRATOR   │    ╳     │    External     │
    │       [O]        │────╳────▶│    System       │
    │                  │    ╳     │   (DB, API)     │
    └──────────────────┘          └─────────────────┘

    WHY FORBIDDEN:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. Orchestrators coordinate, they don't execute I/O          │
    │ 2. Violates single responsibility principle                  │
    │ 3. Makes workflows non-testable                              │
    │ 4. Bypasses Effect node retry/circuit breaker logic          │
    │ 5. Mixes coordination with execution                         │
    └─────────────────────────────────────────────────────────────┘
```

**Rationale**: Orchestrators emit Actions that Effect nodes execute. Direct I/O bypasses the Effect layer's retry logic, circuit breakers, and transaction management.

**Correct Alternative**:
```text
    [O] Orchestrator emits Action → Queue → [E] Effect executes I/O
```

---

### Pattern 7: Orchestrator Returns Result (FORBIDDEN)

```text
    ┌─────────────────────────────────────────────────────────────┐
    │          FORBIDDEN: Orchestrator → Typed Result              │
    └─────────────────────────────────────────────────────────────┘

    ┌──────────────────┐          ┌─────────────────┐
    │   ORCHESTRATOR   │    ╳     │   Return typed  │
    │       [O]        │────╳────▶│   result like   │
    │                  │    ╳     │   COMPUTE node  │
    └──────────────────┘          └─────────────────┘

    WHY FORBIDDEN:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. Orchestrators emit events/intents, not return results     │
    │ 2. Only COMPUTE nodes return typed results                   │
    │ 3. Violates separation of concerns (coordinate vs transform) │
    │ 4. Makes orchestrators stateful (aggregating results)        │
    │ 5. Breaks architectural clarity of 4-node pattern            │
    └─────────────────────────────────────────────────────────────┘
```

**Rationale**: The ONEX architecture enforces clear separation - **COMPUTE transforms data and returns results**, **ORCHESTRATOR coordinates workflows via events/intents**. Allowing Orchestrators to return results would blur this distinction.

**Validation Enforcement**:
```python
# This will raise ValueError at runtime
output = ModelHandlerOutput[dict](
    node_kind=EnumNodeKind.ORCHESTRATOR,
    result={"workflow_status": "completed"},  # ERROR!
)
# ValueError: ORCHESTRATOR cannot set result - use events[] and intents[] only.
# Only COMPUTE nodes return typed results.
```

**Correct Alternative**:
```text
    [O] Orchestrator emits events (workflow state) and intents (side effects)
    [C] COMPUTE node returns typed results when data transformation is needed
```

**Example**:
```python
# ✅ CORRECT - Orchestrator emits events and intents
return ModelHandlerOutput[None](
    node_kind=EnumNodeKind.ORCHESTRATOR,
    events=[
        ModelEventEnvelope(
            event_type="workflow.completed",
            payload={"workflow_id": workflow_id, "status": "success"}
        )
    ],
    intents=[
        ModelIntent(
            intent_type=EnumIntentType.NOTIFICATION,
            target="email_service",
            payload={"message": "Workflow completed"}
        )
    ],
    result=None,  # REQUIRED: Must be None
)
```

---

## Why These Constraints Matter

### 1. Predictable Data Flow

```text
    PREDICTABLE                         UNPREDICTABLE
    ┌─────────────────┐                 ┌─────────────────┐
    │ [E]→[C]→[R]→[O] │                 │ [E]↔[C]↔[R]↔[O] │
    │                 │                 │      ↕   ↕      │
    │ Clear path      │                 │ Circular deps   │
    │ Easy to trace   │                 │ Hard to debug   │
    │ Debuggable      │                 │ Race conditions │
    └─────────────────┘                 └─────────────────┘
```

**Benefits**:
- Trace any data item through the system
- Identify bottlenecks in the pipeline
- Debug failures with clear causality

### 2. Testability

```text
    PURE NODES (Compute, Reducer)       IMPURE NODES (Effect)
    ┌─────────────────────────────┐     ┌─────────────────────────────┐
    │ • No mocks needed           │     │ • Requires I/O mocking      │
    │ • Deterministic assertions  │     │ • Tests external contracts  │
    │ • Fast execution            │     │ • Integration test focus    │
    │ • Easy to verify            │     │ • Circuit breaker testing   │
    └─────────────────────────────┘     └─────────────────────────────┘

    Test Coverage Strategy:
    ┌───────────────────────────────────────────────────────────────┐
    │ COMPUTE: Unit tests (pure functions, no mocks)                │
    │ REDUCER: FSM transition tests (assert state + intents)        │
    │ EFFECT:  Integration tests (mock external systems)            │
    │ ORCHESTRATOR: Workflow tests (verify action sequencing)       │
    └───────────────────────────────────────────────────────────────┘
```

**Example - Testing Pure Reducer**:
```python
# No mocks needed - test pure FSM transition
def test_order_placed_transition():
    reducer = OrderReducer(container)
    initial_state = {"status": "IDLE", "order_id": None}
    action = "PLACE_ORDER"
    payload = {"items": [{"id": 1, "price": 100}]}

    result = reducer._apply_fsm_transition(initial_state, action, payload)

    # Assert on pure state transition
    assert result.new_state["status"] == "ORDER_PLACED"
    assert result.new_state["total"] == 100

    # Assert on emitted intents (not execution)
    assert len(result.intents) == 2
    assert result.intents[0].intent_type == EnumIntentType.DATABASE_WRITE
    assert result.intents[1].intent_type == EnumIntentType.NOTIFICATION
```

### 3. Clear Separation of Concerns

```text
    ┌─────────────────────────────────────────────────────────────┐
    │                   Separation of Concerns                     │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │  EFFECT [E]           COMPUTE [C]          REDUCER [R]      │
    │  ═════════════        ═════════════        ═════════════    │
    │  "Talk to the         "Transform the       "Manage the      │
    │   outside world"       data"                state machine"  │
    │                                                              │
    │  • API calls          • Validation         • FSM transitions │
    │  • DB operations      • Calculations       • State history   │
    │  • File I/O           • Filtering          • Intent emission │
    │  • Message queues     • Mapping            • Terminal states │
    │                                                              │
    │                     ORCHESTRATOR [O]                         │
    │                     ═════════════════                        │
    │                     "Coordinate the workflow"                │
    │                                                              │
    │                     • Lease management                       │
    │                     • Action emission                        │
    │                     • Dependency tracking                    │
    │                     • Error recovery                         │
    └─────────────────────────────────────────────────────────────┘
```

### 4. Debugging Simplicity

```text
    DEBUG FLOW (following canonical shapes):

    1. Find the error:
       ┌───────────────────────────────────────────────────────┐
       │ Error in NodeOrderReducer: Invalid state transition    │
       └───────────────────────────────────────────────────────┘
                                    │
    2. Trace backwards:             ▼
       ┌───────────────────────────────────────────────────────┐
       │ What COMPUTE node fed this Reducer?                    │
       │ → NodeOrderValidatorCompute                            │
       └───────────────────────────────────────────────────────┘
                                    │
    3. Find data source:            ▼
       ┌───────────────────────────────────────────────────────┐
       │ What EFFECT node provided the raw data?               │
       │ → NodeOrderFetcherEffect (API call failed silently)   │
       └───────────────────────────────────────────────────────┘
                                    │
    4. Root cause found:            ▼
       ┌───────────────────────────────────────────────────────┐
       │ External API returned malformed data                   │
       │ → Fix: Add validation in EFFECT or COMPUTE layer      │
       └───────────────────────────────────────────────────────┘
```

### 5. Scalability

```text
    HORIZONTAL SCALING (each node type scales independently):

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   EFFECT    │     │   COMPUTE   │     │   REDUCER   │
    │   Cluster   │     │   Cluster   │     │   Cluster   │
    ├─────────────┤     ├─────────────┤     ├─────────────┤
    │ [E] [E] [E] │────▶│ [C] [C] [C] │────▶│ [R] [R] [R] │
    │ [E] [E]     │     │ [C] [C]     │     │ [R]         │
    │ (I/O bound) │     │ (CPU bound) │     │ (State)     │
    └─────────────┘     └─────────────┘     └─────────────┘
         ▲                   ▲                    ▲
         │                   │                    │
    Scale based on:     Scale based on:     Scale based on:
    • API rate limits   • CPU utilization   • State partitions
    • DB connections    • Memory usage      • Event throughput
    • Network I/O       • Processing time
```

---

## Decision Matrix

Use this matrix to determine the correct execution shape:

| Trigger Source | Target | Shape | Valid? |
|---------------|--------|-------|--------|
| External Event | Orchestrator | Event → Orchestrator | Yes |
| External Event | Reducer | Event → Reducer | Yes |
| Intent (from Reducer) | Effect | Intent → Effect | Yes |
| Command | Orchestrator | Command → Orchestrator | Yes |
| Command | Effect | Command → Effect | Yes |
| Action (from Orchestrator) | Effect | Action → Effect | Yes |
| Command | Reducer | Command → Reducer | **No** |
| Reducer | External System | Reducer → I/O | **No** |
| Effect | Reducer | Effect → Reducer | **No** |
| Compute | External System | Compute → I/O | **No** |
| Any Node | Same Node Type | Circular | **No** |

---

## Enforcement

### Static Analysis

Purity checks are enforced via AST analysis:

```bash
# Check node purity (COMPUTE and REDUCER)
poetry run python scripts/check_node_purity.py

# Violations block CI/CD
poetry run python scripts/check_node_purity.py --strict
```

### Runtime Validation

- **Lease validation**: Actions must include valid `lease_id` and `epoch`
- **Intent routing**: Intents are validated before Effect execution
- **Workflow DAG**: Orchestrators detect circular dependencies

### Test Requirements

All nodes must include tests demonstrating:

1. **EFFECT**: I/O operation isolation and error handling
2. **COMPUTE**: Pure transformation with deterministic output
3. **REDUCER**: FSM transitions with correct Intent emission
4. **ORCHESTRATOR**: Workflow coordination with Action sequencing

---

## Registration-Specific Execution Shapes

Node registration in ONEX follows two distinct paths, each using a different canonical execution shape. This section documents how the registration domain applies the general execution shapes defined above.

### Canonical Registration (Event-Driven)

The **canonical registration path** uses automatic event-driven discovery:

| Aspect | Value |
|--------|-------|
| **Trigger** | `NodeIntrospected` EVENT (`NODE_INTROSPECTION_EVENT`) |
| **Shape** | Shape 1 - Event to Orchestrator |
| **Source** | `MixinIntrospectionPublisher` (automatic on node startup) |
| **Topic** | `onex.registration.events` |

```text
    ┌──────────────┐          ┌─────────────────┐
    │    Node      │          │  Registration   │
    │   Startup    │─────────▶│  Orchestrator   │
    │              │          │      [O]        │
    │ publishes    │  EVENT   │                 │
    │ NodeIntro-   │          │ Coordinates     │
    │ spected      │          │ workflow via    │
    │              │          │ ModelAction     │
    └──────────────┘          └────────┬────────┘
                                       │
                                       ▼
                              ┌────────────────────┐
                              │ Actions to Effect  │
                              │ nodes: Consul,     │
                              │ PostgreSQL, Events │
                              └────────────────────┘
```

**Use Cases**:
- Default path for automatic node registration on startup
- Zero-touch service discovery in production environments
- Integration testing with automatic node lifecycle

### Gated Registration (Command-Driven)

The **gated registration path** is reserved for administrative or exceptional registration flows:

| Aspect | Value |
|--------|-------|
| **Trigger** | `RegisterNodeRequested` COMMAND (planned) |
| **Shape** | Shape 4 - Command to Orchestrator |
| **Source** | Admin API, CLI, provisioning scripts (explicit) |
| **Topic** | `onex.registration.commands` |

```text
    ┌──────────────┐          ┌─────────────────┐
    │   Admin      │          │  Registration   │
    │   System     │─────────▶│  Orchestrator   │
    │              │          │      [O]        │
    │ sends        │ COMMAND  │                 │
    │ RegisterNode │          │ Validates auth, │
    │ Requested    │          │ applies policy, │
    │              │          │ coordinates     │
    └──────────────┘          └────────┬────────┘
                                       │
                              ┌────────┴────────┐
                              │                 │
                              ▼                 ▼
                      ┌──────────────┐  ┌──────────────┐
                      │ Gate PASS:   │  │ Gate FAIL:   │
                      │ Same workflow│  │ Emit         │
                      │ as canonical │  │ Rejection    │
                      └──────────────┘  └──────────────┘
```

**Use Cases**:
- Administrative/exceptional registration requiring explicit authorization
- Manual node onboarding in controlled environments
- Bulk provisioning with operator oversight
- Re-registration after infrastructure failures

### Registration Shape Summary

| Path | Trigger | Shape | Gate Required | Automation |
|------|---------|-------|---------------|------------|
| **Canonical** | `NodeIntrospected` EVENT | Shape 1 | No | Automatic |
| **Gated** | `RegisterNodeRequested` COMMAND | Shape 4 | Yes | Manual |

> **See Also**:
> - [Registration Trigger Design](REGISTRATION_TRIGGER_DESIGN.md) for detailed implementation, FSM states, and sequence diagrams
> - [ADR-004: Registration Trigger Architecture](decisions/ADR-004-registration-trigger-architecture.md) for architectural decision rationale

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [**Execution Shape Examples**](EXECUTION_SHAPE_EXAMPLES.md) | Practical code examples for each canonical shape |
| [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) | Complete architecture overview |
| [ModelIntent Architecture](MODEL_INTENT_ARCHITECTURE.md) | Intent pattern for Reducer → Effect |
| [ModelAction Architecture](MODEL_ACTION_ARCHITECTURE.md) | Action pattern for Orchestrator → nodes |
| [Node Purity Guarantees](NODE_PURITY_GUARANTEES.md) | Purity enforcement for COMPUTE/REDUCER |
| [Node Types Guide](../guides/node-building/02_NODE_TYPES.md) | When to use each node type |
| [Node Building Guide](../guides/node-building/README.md) | How to implement nodes |
| [Registration Trigger Design](REGISTRATION_TRIGGER_DESIGN.md) | Registration workflow implementation details |
| [ADR-004: Registration Trigger Architecture](decisions/ADR-004-registration-trigger-architecture.md) | Architectural decision for registration triggers |

### See Also

For practical, runnable code examples demonstrating each execution shape, see **[Execution Shape Examples](EXECUTION_SHAPE_EXAMPLES.md)**.

---

## Summary

### Allowed Execution Shapes

The following table shows all allowed message flow patterns. Shapes 1-5 are
**canonical message-category shapes** defined in `EnumExecutionShape` and
validated by `ModelExecutionShapeValidation`. Shapes 6-7 are **runtime
coordination patterns** that describe orchestrator behavior and pipeline flow.

| # | Shape | Purpose | Type |
|---|-------|---------|------|
| 1 | Event → Orchestrator | Workflow triggers | Canonical (enum) |
| 2 | Event → Reducer | State change triggers | Canonical (enum) |
| 3 | Intent → Effect | Reducer-requested I/O | Canonical (enum) |
| 4 | Command → Orchestrator | Workflow commands | Canonical (enum) |
| 5 | Command → Effect | Direct I/O operations | Canonical (enum) |
| 6 | Action → Effect | Orchestrator-delegated I/O | Runtime pattern |
| 7 | Full Pipeline | EFFECT → COMPUTE → REDUCER → ORCHESTRATOR | Composite pattern |

**Note**: Only shapes 1-5 have corresponding `EnumExecutionShape` values
(e.g., `event_to_orchestrator`, `intent_to_effect`). Shape 6 uses the
`ModelAction` pattern for orchestrator-to-node coordination. Shape 7 represents
the complete data pipeline, not a single message routing pattern.

### Forbidden Patterns

| # | Pattern | Why Forbidden |
|---|---------|---------------|
| 1 | Command → Reducer | Bypasses orchestration |
| 2 | Reducer → I/O | Violates purity |
| 3 | Effect → Reducer | Wrong data flow direction |
| 4 | Compute → I/O | Violates purity |
| 5 | Circular Dependencies | Creates infinite loops |
| 6 | Orchestrator → Direct I/O | Bypasses Effect layer |
| 7 | Orchestrator → Typed Result | Only COMPUTE returns results |

### Key Principles

1. **Unidirectional Flow**: Data flows EFFECT → COMPUTE → REDUCER → ORCHESTRATOR
2. **Purity**: COMPUTE and REDUCER nodes must be pure (no I/O)
3. **Intent/Action Separation**: Reducers emit Intents, Orchestrators emit Actions
4. **Single-Writer Semantics**: Leases ensure exclusive workflow ownership
5. **Testability**: Pure nodes are trivially testable without mocks

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-19
**Primary Maintainer**: ONEX Framework Team
