> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > ModelAction Architecture

# ModelAction Architecture

> **See Also**: [ONEX Terminology Guide](../standards/onex_terminology.md) for canonical definitions. This document expands on the **Action** concept from the terminology guide.

## Overview

**ModelAction** represents an Orchestrator-issued command in the ONEX Four-Node Architecture. Actions are the primary mechanism for coordinating distributed workflows with guaranteed single-writer semantics through lease management.

### What is ModelAction?

ModelAction is a strongly-typed Pydantic model that encapsulates:
- **Command intent** via `action_type` (COMPUTE, EFFECT, REDUCE, ORCHESTRATE, CUSTOM)
- **Target routing** via `target_node_type` to specify which node should execute the action
- **Execution parameters** via `payload`, `dependencies`, `priority`, and `timeout_ms`
- **Ownership proof** via `lease_id` to ensure single-writer guarantees
- **Version control** via `epoch` for optimistic concurrency control

### Role in ONEX Four-Node Architecture

Actions flow from the **Orchestrator** node to downstream nodes (Compute, Effect, Reducer):

```
┌──────────────────┐
│  ORCHESTRATOR    │
│  (Coordinates)   │
└────────┬─────────┘
         │ Emits ModelAction
         ▼
┌────────────────────────────────────────┐
│  COMPUTE / EFFECT / REDUCER            │
│  (Validates lease_id & epoch)          │
│  (Executes action)                     │
└────────────────────────────────────────┘
```

**Key Characteristics:**
- **Unidirectional**: Actions flow from Orchestrator → downstream nodes
- **Stateless**: Actions carry all execution context in their payload
- **Versioned**: Epoch tracking prevents stale or out-of-order execution
- **Traceable**: UUID-based action_id enables distributed tracing

### Orchestrator-Issued Commands

Actions are **always issued by the Orchestrator**, never by downstream nodes. This enforces clear workflow coordination:

| Orchestrator Responsibility | Action Field |
|-----------------------------|--------------|
| Generate unique action ID | `action_id: UUID` |
| Specify target node type | `target_node_type: str` |
| Define action type | `action_type: EnumActionType` |
| Provide execution payload | `payload: dict[str, Any]` |
| Prove ownership | `lease_id: UUID` |
| Track version | `epoch: int` |
| Set priority | `priority: int (1-10)` |
| Define dependencies | `dependencies: list[UUID]` |

## Action vs Thunk

### Comparison Table

| Aspect | **Action** (Current) | **Thunk** (Legacy) |
|--------|---------------------|-------------------|
| **Purpose** | Orchestrator-issued command with explicit intent | Deferred computation wrapper |
| **Clarity** | Clear ownership and execution semantics | Ambiguous purpose (lazy evaluation?) |
| **Fields** | `action_id`, `action_type`, `lease_id`, `epoch` | `thunk_id`, `thunk_type` (no lease semantics) |
| **Lease Management** | ✅ Built-in via `lease_id` and `epoch` | ❌ No ownership guarantees |
| **Type Safety** | ✅ Pydantic validation with strong typing | ⚠️ Partial validation |
| **Naming Alignment** | ✅ Matches ONEX terminology (Actions emitted by Orchestrators) | ❌ Borrowed from functional programming (misleading) |
| **Documentation** | ✅ Clear role in Four-Node Architecture | ❌ Unclear semantics |

### Why the Rename: Clarity of Purpose

The rename from **Thunk** to **Action** reflects:

1. **Semantic Accuracy**: Actions represent commands issued by Orchestrators, not lazy evaluation wrappers
2. **ONEX Alignment**: "Action emission" is standard Orchestrator terminology across ONEX documentation
3. **Ownership Clarity**: Actions carry explicit ownership proof (`lease_id`), not present in generic thunk pattern
4. **Developer Experience**: "Action" is self-explanatory; "Thunk" requires functional programming background

**Example Naming Evolution:**
```
# Legacy naming (misleading)
thunk = ModelThunk(
    thunk_id=uuid4(),
    thunk_type=EnumActionType.COMPUTE,
    # No lease_id or epoch - missing ownership guarantees
)

# Current naming (clear intent)
action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.COMPUTE,
    lease_id=orchestrator.lease_id,  # Proves ownership
    epoch=orchestrator.current_epoch,  # Tracks version
)
```

### Migration Notes

**For Codebase Migration:**

1. **Search and Replace** (with validation):
   - `ModelThunk` → `ModelAction`
   - `thunk_id` → `action_id`
   - `thunk_type` → `action_type`
   - `emitted_thunks` → `emitted_actions`
   - `emit_thunk()` → `emit_action()`

2. **Add Lease Management** (critical):
   ```python
   # Before: No ownership guarantees
   thunk = ModelThunk(thunk_id=uuid4(), ...)

   # After: Single-writer semantics enforced
   action = ModelAction(
       action_id=uuid4(),
       lease_id=self.lease_id,  # ADD THIS
       epoch=self.current_epoch,  # ADD THIS
       ...
   )
   ```

3. **Update Tests**:
   - Replace `thunk` variable names with `action`
   - Add `lease_id` and `epoch` to test fixtures
   - Validate lease semantics in action processing tests

4. **Update Documentation**:
   - Replace "thunk" terminology with "action" in docstrings
   - Update workflow diagrams to show "Action Emission"
   - Link to Lease Management Pattern documentation

## Lease Management

Lease management provides **single-writer semantics** for distributed workflows, preventing concurrent modification conflicts.

### lease_id Field

**Type**: `UUID` (required)

**Purpose**: Proves Orchestrator ownership of a workflow instance.

**Key Properties**:
- Globally unique (UUID4)
- Immutable during workflow lifetime
- Must be included in all emitted actions
- Validated by all action processors before execution

**Single-Writer Semantics**:

The `lease_id` ensures that only **one Orchestrator** can control a workflow at any given time:

```
class NodeMyOrchestrator(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)

        # Claim ownership with unique lease
        self.lease_id = uuid4()  # Global ownership proof

    async def emit_action(self, action_type, target_node_type, payload):
        """Emit action with ownership proof."""
        action = ModelAction(
            action_id=uuid4(),
            action_type=action_type,
            target_node_type=target_node_type,
            payload=payload,
            lease_id=self.lease_id,  # Proves this orchestrator owns workflow
            epoch=self.current_epoch,
        )

        await self.event_bus.publish(action)
        self.current_epoch += 1  # Increment after emission
```

**Prevents Concurrent Modification**:

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Orchestrator A claims workflow
orchestrator_a.lease_id = UUID("a1a1a1a1-...")

# Orchestrator B attempts concurrent modification
orchestrator_b.lease_id = UUID("b2b2b2b2-...")

# Both emit actions for same workflow
action_a = ModelAction(lease_id=orchestrator_a.lease_id, ...)
action_b = ModelAction(lease_id=orchestrator_b.lease_id, ...)

# Downstream node validates: only ONE lease_id accepted per workflow
if action.lease_id != current_workflow_lease_id:
    raise ModelOnexError("Invalid lease_id: workflow owned by different orchestrator")
```

### epoch Field

**Type**: `int` (required, >= 0)

**Purpose**: Monotonically increasing version number for optimistic concurrency control.

**Key Properties**:
- Starts at 0 on workflow initialization
- Increments by 1 for each state change or action emission
- Never decrements (monotonic guarantee)
- Compared to detect stale or out-of-order actions

**Optimistic Concurrency Control**:

The `epoch` field enables detection of stale actions without distributed locks:

```
class NodeMyOrchestrator(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)
        self.lease_id = uuid4()
        self.current_epoch = 0  # Start at version 0

    async def execute_workflow_step(self, payload):
        """Execute workflow step with epoch tracking."""

        # Emit action with current epoch
        action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.COMPUTE,
            target_node_type="NodeDataProcessorCompute",
            payload=payload,
            lease_id=self.lease_id,
            epoch=self.current_epoch,  # Current version
        )

        await self.event_bus.publish(action)

        # Increment epoch AFTER emission
        self.current_epoch += 1  # Now at version 1, 2, 3, ...
```

**Epoch Validation Pattern**:

Downstream nodes validate epochs to reject stale actions:

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError

class NodeDataProcessorCompute(NodeCoreBase):
    async def process_action(self, action: ModelAction):
        """Process action with epoch validation."""

        # Validate lease_id first
        if action.lease_id != self.current_workflow_lease_id:
            raise ModelOnexError("Invalid lease_id")

        # Validate epoch to detect stale actions
        if action.epoch < self.last_processed_epoch:
            raise ModelOnexError(
                f"Stale action detected: epoch {action.epoch} < "
                f"last processed {self.last_processed_epoch}"
            )

        # Process action
        result = await self._execute_computation(action.payload)

        # Update last processed epoch
        self.last_processed_epoch = action.epoch

        return result
```

**Epoch Monotonicity Guarantee**:

```
Orchestrator State:      epoch=0 → emit → epoch=1 → emit → epoch=2 → emit → epoch=3
                                    │              │              │
                                    ▼              ▼              ▼
Actions Emitted:            Action(epoch=0)  Action(epoch=1)  Action(epoch=2)
                                    │              │              │
                                    ▼              ▼              ▼
Downstream Validation:      epoch >= 0       epoch >= 1       epoch >= 2
```

If actions arrive out-of-order, epochs detect the issue:
```
Received: Action(epoch=2) → OK, process and set last_processed_epoch=2
Received: Action(epoch=1) → REJECT, epoch < last_processed_epoch (stale!)
```

## ModelAction Fields

### Core Identification

```
action_id: UUID = Field(
    default_factory=uuid4,
    description="Unique action identifier (UUID)"
)
```

**Purpose**: Globally unique identifier for distributed tracing and action tracking.

**Usage**: Log correlation, error reporting, dependency resolution.

---

### Action Routing

```
action_type: EnumActionType = Field(
    ...,
    description="Type of action for routing"
)
```

**Values**:
- `EnumActionType.COMPUTE` - Pure computation/transformation
- `EnumActionType.EFFECT` - External I/O operations
- `EnumActionType.REDUCE` - Aggregation/persistence
- `EnumActionType.ORCHESTRATE` - Nested workflow coordination
- `EnumActionType.CUSTOM` - Domain-specific actions

**Purpose**: Routing hint for downstream nodes to understand action intent.

---

```
target_node_type: str = Field(
    ...,
    description="Target node type for execution"
)
```

**Purpose**: Specifies which node class should execute this action.

**Example Values**: `"NodeDataProcessorCompute"`, `"NodeDatabaseWriterEffect"`

---

### Execution Parameters

```
payload: dict[str, Any] = Field(
    default_factory=dict,
    description="Action payload data"
)
```

**Purpose**: Execution context and input data for action processing.

**Best Practice**: Use strongly-typed dictionaries with documented schemas.

---

```
dependencies: list[UUID] = Field(
    default_factory=list,
    description="List of dependency action IDs (UUIDs)"
)
```

**Purpose**: Declare action dependencies for execution ordering.

**Example**:
```
action_b = ModelAction(
    action_id=uuid4(),
    dependencies=[action_a.action_id],  # Wait for action_a to complete
    ...
)
```

---

```
priority: int = Field(
    default=1,
    description="Execution priority (higher = more urgent)"
)
```

**Range**: 1 (lowest) to 10 (highest)

**Purpose**: Priority queue ordering for action execution.

---

```
timeout_ms: int = Field(
    default=30000,
    description="Execution timeout in milliseconds"
)
```

**Default**: 30 seconds (30000ms)

**Purpose**: Maximum execution time before action is considered failed.

---

### Lease Management Fields

```
lease_id: UUID = Field(
    ...,
    description="Lease ID proving Orchestrator ownership"
)

epoch: int = Field(
    ...,
    description="Monotonically increasing version number"
)
```

**See**: [Lease Management](#lease-management) section above for detailed semantics.

---

### Retry and Metadata

```
retry_count: int = Field(
    default=0,
    description="Number of retry attempts"
)
```

**Purpose**: Track retry attempts for idempotency and circuit breaking.

---

```
metadata: dict[str, Any] = Field(
    default_factory=dict,
    description="Additional metadata"
)
```

**Purpose**: Extensible metadata for logging, tracing, or custom processing.

**Common Keys**:
- `"emitted_by"`: Orchestrator node ID
- `"emission_time"`: ISO 8601 timestamp
- `"workflow_id"`: Parent workflow UUID
- `"correlation_id"`: Cross-service tracing ID

---

```
created_at: datetime = Field(
    default_factory=datetime.now,
    description="Action creation timestamp"
)
```

**Purpose**: Audit trail and action lifecycle tracking.

## Usage Patterns

### Emitting Actions

**Basic Action Emission**:

```
from uuid import uuid4
from datetime import datetime
from omnibase_core.models.model_action import ModelAction
from omnibase_core.enums.enum_orchestrator_types import EnumActionType

class NodeWorkflowOrchestrator(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)
        self.lease_id = uuid4()  # Claim ownership
        self.current_epoch = 0   # Initialize version

    async def process_data_workflow(self, input_data: dict):
        """Orchestrate multi-step data processing workflow."""

        # Step 1: Emit COMPUTE action for data transformation
        compute_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.COMPUTE,
            target_node_type="NodeDataTransformerCompute",
            payload={
                "data": input_data,
                "transformation": "normalize",
            },
            lease_id=self.lease_id,  # Prove ownership
            epoch=self.current_epoch,  # Version 0
            priority=5,
            timeout_ms=10000,  # 10 second timeout
        )

        await self.event_bus.publish(compute_action)
        self.current_epoch += 1  # Increment to version 1

        # Step 2: Emit EFFECT action for database write
        effect_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.EFFECT,
            target_node_type="NodeDatabaseWriterEffect",
            payload={
                "table": "processed_data",
                "operation": "insert",
            },
            dependencies=[compute_action.action_id],  # Wait for compute
            lease_id=self.lease_id,
            epoch=self.current_epoch,  # Version 1
            priority=7,  # Higher priority
        )

        await self.event_bus.publish(effect_action)
        self.current_epoch += 1  # Increment to version 2
```

**Action with Metadata**:

```
action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.REDUCE,
    target_node_type="NodeAggregatorReducer",
    payload={"aggregation_key": "user_id"},
    lease_id=self.lease_id,
    epoch=self.current_epoch,
    metadata={
        "emitted_by": str(self.node_id),
        "emission_time": datetime.now().isoformat(),
        "workflow_id": str(self.workflow_id),
        "tenant_id": "tenant-123",
    },
)
```

**Conditional Action Emission**:

```
async def emit_conditional_action(self, condition: bool, payload: dict):
    """Emit action only if condition is met."""

    if not condition:
        self.logger.info("Condition not met, skipping action emission")
        return

    action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.CUSTOM,
        target_node_type="NodeCustomProcessorCompute",
        payload=payload,
        lease_id=self.lease_id,
        epoch=self.current_epoch,
        metadata={"conditional_emission": True},
    )

    await self.event_bus.publish(action)
    self.current_epoch += 1
```

### Validating Actions

**Lease Validation in Downstream Nodes**:

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError

class NodeDataTransformerCompute(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)
        self.active_leases: dict[UUID, int] = {}  # workflow_id -> last_epoch

    async def process_action(self, action: ModelAction):
        """Process action with comprehensive lease validation."""

        # Step 1: Validate lease_id (ownership proof)
        if not self._validate_lease_id(action):
            raise ModelOnexError(
                f"Invalid lease_id: {action.lease_id} not authorized "
                f"for workflow"
            )

        # Step 2: Validate epoch (stale action detection)
        if not self._validate_epoch(action):
            raise ModelOnexError(
                f"Stale action detected: epoch {action.epoch} < "
                f"last processed {self.active_leases.get(action.payload.get('workflow_id'), -1)}"
            )

        # Step 3: Execute action
        result = await self._execute_action(action)

        # Step 4: Update last processed epoch
        workflow_id = action.payload.get("workflow_id")
        if workflow_id:
            self.active_leases[workflow_id] = action.epoch

        return result

    def _validate_lease_id(self, action: ModelAction) -> bool:
        """Validate lease_id proves ownership."""
        # Implementation: Check against known active leases
        # For example, query distributed lease registry
        return True  # Simplified for example

    def _validate_epoch(self, action: ModelAction) -> bool:
        """Validate epoch is not stale."""
        workflow_id = action.payload.get("workflow_id")
        if not workflow_id:
            return True  # No epoch tracking without workflow_id

        last_epoch = self.active_leases.get(workflow_id, -1)
        return action.epoch >= last_epoch
```

**Stale Action Detection**:

```
from datetime import datetime
from uuid import UUID

class ActionValidator:
    """Utility class for action validation."""

    @staticmethod
    def is_stale_action(
        action: ModelAction,
        last_processed_epoch: int
    ) -> bool:
        """Check if action is stale based on epoch."""
        return action.epoch < last_processed_epoch

    @staticmethod
    def validate_action_timeout(action: ModelAction) -> bool:
        """Check if action has exceeded its timeout."""
        elapsed_ms = (datetime.now() - action.created_at).total_seconds() * 1000
        return elapsed_ms <= action.timeout_ms

    @staticmethod
    def validate_dependencies_met(
        action: ModelAction,
        completed_actions: set[UUID]
    ) -> bool:
        """Check if all action dependencies are satisfied."""
        return all(dep_id in completed_actions for dep_id in action.dependencies)
```

**Comprehensive Validation Pattern**:

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError

async def validate_and_process_action(
    action: ModelAction,
    last_processed_epoch: int,
    completed_actions: set[UUID],
) -> dict:
    """Validate action before processing."""

    # Validation 1: Lease ownership
    if action.lease_id != current_workflow_lease_id:
        raise ModelOnexError("Invalid lease_id: workflow owned by different orchestrator")

    # Validation 2: Epoch (stale detection)
    if ActionValidator.is_stale_action(action, last_processed_epoch):
        raise ModelOnexError(f"Stale action: epoch {action.epoch}")

    # Validation 3: Timeout
    if not ActionValidator.validate_action_timeout(action):
        raise ModelOnexError(f"Action timeout exceeded: {action.timeout_ms}ms")

    # Validation 4: Dependencies
    if not ActionValidator.validate_dependencies_met(action, completed_actions):
        raise ModelOnexError("Action dependencies not met")

    # All validations passed - safe to process
    return await execute_action(action)
```

## Best Practices

### Always Set lease_id in Orchestrator

**❌ WRONG - Missing lease_id**:
```
action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.COMPUTE,
    target_node_type="NodeProcessorCompute",
    # Missing lease_id and epoch!
)
```

**✅ CORRECT - Lease ownership guaranteed**:
```
class NodeMyOrchestrator(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)
        self.lease_id = uuid4()  # Claim ownership
        self.current_epoch = 0

    async def emit_action(self):
        action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.COMPUTE,
            target_node_type="NodeProcessorCompute",
            lease_id=self.lease_id,  # ✅ Proves ownership
            epoch=self.current_epoch,  # ✅ Tracks version
        )
        await self.publish(action)
        self.current_epoch += 1  # ✅ Increment after emission
```

---

### Increment Epoch on State Changes

**❌ WRONG - Epoch never increments**:
```
async def emit_multiple_actions(self):
    for i in range(10):
        action = ModelAction(
            action_id=uuid4(),
            lease_id=self.lease_id,
            epoch=self.current_epoch,  # ❌ Always epoch=0!
        )
        await self.publish(action)
    # self.current_epoch never incremented
```

**✅ CORRECT - Epoch tracks each state change**:
```
async def emit_multiple_actions(self):
    for i in range(10):
        action = ModelAction(
            action_id=uuid4(),
            lease_id=self.lease_id,
            epoch=self.current_epoch,  # ✅ Version: 0, 1, 2, ...
        )
        await self.publish(action)
        self.current_epoch += 1  # ✅ Increment after each emission
```

---

### Validate Lease Before Action Execution

**❌ WRONG - No lease validation**:
```
async def process_action(self, action: ModelAction):
    # ❌ Blindly execute without checking lease_id or epoch
    result = await self._execute(action.payload)
    return result
```

**✅ CORRECT - Comprehensive lease validation**:
```
from omnibase_core.models.errors.model_onex_error import ModelOnexError

async def process_action(self, action: ModelAction):
    # ✅ Step 1: Validate lease_id
    if action.lease_id != self.current_workflow_lease_id:
        raise ModelOnexError("Invalid lease_id")

    # ✅ Step 2: Validate epoch
    if action.epoch < self.last_processed_epoch:
        raise ModelOnexError("Stale action")

    # ✅ Step 3: Safe to execute
    result = await self._execute(action.payload)

    # ✅ Step 4: Update tracking
    self.last_processed_epoch = action.epoch

    return result
```

---

### Use Strong Typing for Payloads

**❌ WRONG - Untyped payload**:
```
action = ModelAction(
    action_type=EnumActionType.COMPUTE,
    payload={"data": some_data},  # ❌ What keys? What types?
)
```

**✅ CORRECT - Strongly-typed payload schema**:
```
from pydantic import BaseModel

class ComputePayload(BaseModel):
    """Strongly-typed payload for compute actions."""
    data: list[dict[str, Any]]
    transformation: str
    options: dict[str, bool] = {}

# Create typed payload
payload = ComputePayload(
    data=[{"id": 1, "value": 100}],
    transformation="normalize",
    options={"validate_schema": True},
)

action = ModelAction(
    action_type=EnumActionType.COMPUTE,
    payload=payload.model_dump(),  # ✅ Validated payload
)
```

---

### Track Action Dependencies for Ordering

**✅ Dependency Tracking Example**:
```
async def orchestrate_multi_step_workflow(self, input_data: dict):
    """Orchestrate workflow with dependency tracking."""

    # Step 1: Fetch data from API
    fetch_action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.EFFECT,
        target_node_type="NodeAPIFetcherEffect",
        payload={"url": "https://api.example.com/data"},
        lease_id=self.lease_id,
        epoch=self.current_epoch,
    )
    await self.publish(fetch_action)
    self.current_epoch += 1

    # Step 2: Transform fetched data (depends on Step 1)
    transform_action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.COMPUTE,
        target_node_type="NodeDataTransformerCompute",
        payload={"transformation": "normalize"},
        dependencies=[fetch_action.action_id],  # ✅ Wait for fetch
        lease_id=self.lease_id,
        epoch=self.current_epoch,
    )
    await self.publish(transform_action)
    self.current_epoch += 1

    # Step 3: Store results (depends on Step 2)
    store_action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.EFFECT,
        target_node_type="NodeDatabaseWriterEffect",
        payload={"table": "processed_data"},
        dependencies=[transform_action.action_id],  # ✅ Wait for transform
        lease_id=self.lease_id,
        epoch=self.current_epoch,
        priority=8,  # Higher priority for final step
    )
    await self.publish(store_action)
    self.current_epoch += 1
```

---

### Log Action Lifecycle Events

**✅ Comprehensive Action Logging**:
```
async def emit_action_with_logging(self, action_type, payload):
    """Emit action with full lifecycle logging."""

    action = ModelAction(
        action_id=uuid4(),
        action_type=action_type,
        target_node_type="NodeProcessorCompute",
        payload=payload,
        lease_id=self.lease_id,
        epoch=self.current_epoch,
        metadata={
            "emitted_by": str(self.node_id),
            "emission_time": datetime.now().isoformat(),
        },
    )

    # Log emission
    self.logger.info(
        "Action emitted",
        action_id=str(action.action_id),
        action_type=action_type.value,
        lease_id=str(action.lease_id),
        epoch=action.epoch,
    )

    await self.publish(action)
    self.current_epoch += 1

    # Log epoch increment
    self.logger.debug(
        "Epoch incremented",
        previous_epoch=self.current_epoch - 1,
        current_epoch=self.current_epoch,
    )
```

## Related Documentation

- **[ONEX Four-Node Architecture](./ONEX_FOUR_NODE_ARCHITECTURE.md)** - Node responsibilities and data flow
- **[Lease Management Pattern](../patterns/LEASE_MANAGEMENT_PATTERN.md)** - Single-writer semantics in detail
- **[Orchestrator Node Template](../guides/templates/ORCHESTRATOR_NODE_TEMPLATE.md)** - Implementation patterns
- **[Subcontract Architecture](./SUBCONTRACT_ARCHITECTURE.md)** - Workflow subcontracts
- **[Event-Driven Architecture](../patterns/EVENT_DRIVEN_ARCHITECTURE.md)** - Action publication patterns

## Summary

**ModelAction** provides the foundation for distributed workflow coordination in ONEX:

✅ **Clear Semantics**: "Action" accurately describes Orchestrator-issued commands
✅ **Single-Writer Guarantees**: `lease_id` prevents concurrent modification conflicts
✅ **Optimistic Concurrency**: `epoch` enables stale action detection without locks
✅ **Strong Typing**: Pydantic validation ensures type safety at runtime
✅ **Traceability**: UUID-based `action_id` enables distributed tracing
✅ **Dependency Management**: Explicit dependencies enable DAG-based execution

**Migration from Thunk**: Rename fields, add lease management, update tests and docs.

**Best Practice**: Always emit actions with `lease_id` and `epoch`, validate before execution, increment epoch after emission.
