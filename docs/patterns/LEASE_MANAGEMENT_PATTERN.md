# Lease Management Pattern

## Overview

The lease management pattern provides **single-writer semantics** for distributed workflows in the ONEX architecture. It prevents concurrent modification conflicts through two core primitives:

- **lease_id**: Unique UUID proving Orchestrator ownership of a workflow
- **epoch**: Monotonically increasing version number for optimistic concurrency control

This pattern ensures that only one Orchestrator can control a workflow at any given time, while allowing multiple Compute/Effect/Reducer nodes to process actions safely.

## Core Concepts

### lease_id (UUID)

The `lease_id` is a unique identifier that proves an Orchestrator's ownership of a workflow:

- **Issued**: When an Orchestrator claims a workflow instance
- **Validated**: Before any action execution by downstream nodes
- **Purpose**: Prevents multiple Orchestrators from modifying the same workflow concurrently

**Key Properties:**
- Globally unique (UUID4)
- Immutable during workflow lifetime
- Must be included in all emitted actions
- Validated by all action processors

### epoch (int)

The `epoch` is a monotonically increasing version number that tracks workflow state changes:

- **Increments**: On each state transition or action emission
- **Enables**: Optimistic concurrency control
- **Detects**: Stale or out-of-order actions

**Key Properties:**
- Starts at 0 on workflow initialization
- Increments by 1 for each state change
- Never decrements
- Compared to detect stale actions

## Lease Lifecycle

### 1. Lease Acquisition

When an Orchestrator initializes, it claims ownership by generating a unique lease_id:

```python
from uuid import uuid4
from omnibase_core.onex.node_core_base import NodeCoreBase

class NodeMyOrchestrator(NodeCoreBase):
    """Orchestrator with lease management."""

    def __init__(self, container):
        super().__init__(container)

        # Claim ownership with unique lease
        self.lease_id = uuid4()

        # Initialize epoch counter
        self.current_epoch = 0

        # Track workflow state
        self.workflow_state = "initialized"
```python

### 2. Action Emission with Lease

All actions emitted by the Orchestrator must include the lease_id and current epoch:

```python
from omnibase_core.models.model_action import ModelAction
from omnibase_core.enums.enum_action_type import EnumActionType

class NodeMyOrchestrator(NodeCoreBase):
    async def execute_workflow_step(self, payload: dict):
        """Emit action with lease metadata."""

        action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.EXECUTE_WORKFLOW,
            target_node_type="NodeDataProcessorCompute",
            payload=payload,
            lease_id=self.lease_id,  # Prove ownership
            epoch=self.current_epoch,  # Current version
            priority=5,
        )

        # Publish action to event bus
        await self.event_bus.publish(action)

        # Increment epoch after emitting action
        self.current_epoch += 1
```python

### 3. Lease Validation

Downstream nodes (Compute, Effect, Reducer) validate the lease before processing:

```python
from omnibase_core.errors.model_onex_error import ModelOnexError

class NodeDataProcessorCompute(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)

        # Expected lease_id (set during workflow initialization)
        self.expected_lease_id: UUID | None = None

        # Track last processed epoch
        self.last_processed_epoch = -1

    def validate_action(self, action: ModelAction) -> bool:
        """Validate action lease and epoch."""

        # Check lease ownership
        if action.lease_id != self.expected_lease_id:
            raise ModelOnexError(
                message=f"Invalid lease_id: {action.lease_id}",
                error_code="LEASE_VIOLATION",
                context={
                    "expected_lease": str(self.expected_lease_id),
                    "received_lease": str(action.lease_id),
                }
            )

        # Check for stale actions
        if action.epoch < self.last_processed_epoch:
            raise ModelOnexError(
                message=f"Stale action: epoch {action.epoch} < {self.last_processed_epoch}",
                error_code="STALE_EPOCH",
                context={
                    "action_epoch": action.epoch,
                    "current_epoch": self.last_processed_epoch,
                }
            )

        return True

    async def process(self, action: ModelAction):
        """Process action after validation."""

        # Validate lease and epoch
        self.validate_action(action)

        # Process the action
        result = await self._execute_computation(action.payload)

        # Update last processed epoch
        self.last_processed_epoch = action.epoch

        return result
```python

### 4. Epoch Increment

The Orchestrator increments the epoch on every state change:

```python
class NodeMyOrchestrator(NodeCoreBase):
    async def update_workflow_state(self, new_state: str):
        """Update workflow state and increment epoch."""

        # Update state
        self.workflow_state = new_state

        # Increment epoch (version control)
        self.current_epoch += 1

        # Log state transition
        self.logger.info(
            f"Workflow state changed to {new_state} (epoch {self.current_epoch})"
        )

    async def handle_result(self, result: ModelResult):
        """Process result and update state."""

        if result.success:
            await self.update_workflow_state("step_completed")
        else:
            await self.update_workflow_state("step_failed")
```python

## Lease Patterns

### Single-Writer Orchestrator

The primary pattern: one Orchestrator owns and controls a workflow instance.

```python
class NodeWorkflowOrchestrator(NodeCoreBase):
    """Single-writer Orchestrator with lease management."""

    def __init__(self, container):
        super().__init__(container)

        # Claim ownership
        self.lease_id = uuid4()
        self.current_epoch = 0

        # Workflow metadata
        self.workflow_id = uuid4()
        self.workflow_state = "initialized"

    async def emit_action(self, action_type: EnumActionType, payload: dict):
        """Emit action with lease metadata."""

        action = ModelAction(
            action_id=uuid4(),
            action_type=action_type,
            payload=payload,
            lease_id=self.lease_id,  # Ownership proof
            epoch=self.current_epoch,  # Version control
            priority=5,
        )

        # Publish to event bus
        await self.event_bus.publish(action)

        # Increment epoch
        self.current_epoch += 1

        self.logger.debug(
            f"Emitted action {action_type.value} with lease {self.lease_id} "
            f"at epoch {self.current_epoch - 1}"
        )

    async def execute_workflow(self):
        """Execute multi-step workflow."""

        # Step 1: Data validation
        await self.emit_action(
            EnumActionType.VALIDATE_DATA,
            {"data": self.input_data}
        )

        # Step 2: Data processing
        await self.emit_action(
            EnumActionType.PROCESS_DATA,
            {"validated_data": self.validated_data}
        )

        # Step 3: Store results
        await self.emit_action(
            EnumActionType.STORE_RESULTS,
            {"processed_data": self.processed_data}
        )
```python

### Lease Validation in Compute/Effect

Compute and Effect nodes validate leases before executing work:

```python
class NodeMyCompute(NodeCoreBase):
    """Compute node with lease validation."""

    def __init__(self, container):
        super().__init__(container)

        # Lease metadata
        self.expected_lease_id: UUID | None = None
        self.last_processed_epoch = -1

    def set_lease(self, lease_id: UUID):
        """Set expected lease_id for validation."""
        self.expected_lease_id = lease_id
        self.logger.info(f"Lease set to {lease_id}")

    async def process(self, input_data: dict):
        """Process input with lease validation."""

        action = input_data.get("action")

        # Validate lease ownership
        if action.lease_id != self.expected_lease_id:
            raise ModelOnexError(
                message="Invalid lease_id - action from wrong Orchestrator",
                error_code="LEASE_VIOLATION",
                context={
                    "expected": str(self.expected_lease_id),
                    "received": str(action.lease_id),
                }
            )

        # Validate epoch (detect stale actions)
        if action.epoch < self.last_processed_epoch:
            raise ModelOnexError(
                message="Stale action detected (old epoch)",
                error_code="STALE_EPOCH",
                context={
                    "action_epoch": action.epoch,
                    "current_epoch": self.last_processed_epoch,
                }
            )

        # Process action
        result = self._execute(action.payload)

        # Update last processed epoch
        self.last_processed_epoch = action.epoch

        return result
```python

## Optimistic Concurrency Control

### Scenario: Concurrent State Updates

The epoch mechanism prevents race conditions when multiple actions are in flight:

1. **Orchestrator A**: epoch=5, emits action X
2. **Orchestrator B**: epoch=5, emits action Y (conflict!)
3. **Compute node**: Accepts first action, rejects second (epoch conflict)

### Epoch Conflict Resolution

```python
class NodeMyCompute(NodeCoreBase):
    def handle_epoch_conflict(self, action: ModelAction):
        """Handle epoch-based conflicts."""

        if action.epoch < self.current_epoch:
            # Stale action - reject immediately
            raise ModelOnexError(
                message=f"Stale action: epoch {action.epoch} < {self.current_epoch}",
                error_code="STALE_EPOCH",
                context={
                    "action_epoch": action.epoch,
                    "current_epoch": self.current_epoch,
                    "recommendation": "Orchestrator should refresh state"
                }
            )

        elif action.epoch > self.current_epoch:
            # Future action - may indicate missed updates
            raise ModelOnexError(
                message=f"Future action: epoch {action.epoch} > {self.current_epoch}",
                error_code="FUTURE_EPOCH",
                context={
                    "action_epoch": action.epoch,
                    "current_epoch": self.current_epoch,
                    "recommendation": "Check for missed state updates"
                }
            )

        else:
            # Current epoch - process action normally
            self._process_action(action)
```python

### Multi-Orchestrator Coordination

When multiple Orchestrators need to coordinate (rare), use lease handoff:

```python
class NodePrimaryOrchestrator(NodeCoreBase):
    async def handoff_lease(self, secondary_orchestrator: "NodeSecondaryOrchestrator"):
        """Transfer lease to another Orchestrator."""

        # Create new lease for secondary
        new_lease_id = uuid4()

        # Emit lease transfer action
        transfer_action = ModelAction(
            action_type=EnumActionType.LEASE_TRANSFER,
            payload={
                "old_lease_id": str(self.lease_id),
                "new_lease_id": str(new_lease_id),
                "transfer_epoch": self.current_epoch,
            },
            lease_id=self.lease_id,  # Still using old lease
            epoch=self.current_epoch,
        )

        await self.event_bus.publish(transfer_action)

        # Invalidate own lease
        self.lease_id = None

        # Secondary claims new lease
        secondary_orchestrator.claim_lease(new_lease_id, self.current_epoch + 1)
```python

## Lease Expiration

### Time-Based Expiration

Leases can expire after a TTL to prevent orphaned workflows:

```python
from datetime import datetime, timedelta
from pydantic import BaseModel

class ModelLeaseMetadata(BaseModel):
    """Lease metadata with expiration tracking."""

    lease_id: UUID
    acquired_at: datetime
    ttl_seconds: int = 300  # 5 minute default

    def is_expired(self) -> bool:
        """Check if lease has expired."""
        elapsed = (datetime.now() - self.acquired_at).total_seconds()
        return elapsed > self.ttl_seconds

    def remaining_ttl(self) -> float:
        """Get remaining TTL in seconds."""
        elapsed = (datetime.now() - self.acquired_at).total_seconds()
        return max(0, self.ttl_seconds - elapsed)

class NodeMyOrchestrator(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)

        self.lease_id = uuid4()
        self.lease_metadata = ModelLeaseMetadata(
            lease_id=self.lease_id,
            acquired_at=datetime.now(),
            ttl_seconds=300,  # 5 minutes
        )

    def check_lease_validity(self):
        """Check if lease is still valid."""
        if self.lease_metadata.is_expired():
            raise ModelOnexError(
                message="Lease has expired",
                error_code="LEASE_EXPIRED",
                context={
                    "lease_id": str(self.lease_id),
                    "acquired_at": self.lease_metadata.acquired_at.isoformat(),
                    "ttl_seconds": self.lease_metadata.ttl_seconds,
                }
            )
```python

### Lease Renewal

Orchestrators can renew leases before expiration:

```python
class NodeMyOrchestrator(NodeCoreBase):
    async def renew_lease(self):
        """Renew lease before expiration."""

        if self.lease_metadata.remaining_ttl() < 60:  # Less than 1 minute remaining
            self.logger.info("Renewing lease")

            # Update acquisition time
            self.lease_metadata = ModelLeaseMetadata(
                lease_id=self.lease_id,  # Keep same lease_id
                acquired_at=datetime.now(),  # Reset timer
                ttl_seconds=self.lease_metadata.ttl_seconds,
            )

    async def execute_long_workflow(self):
        """Execute workflow with automatic lease renewal."""

        for step in self.workflow_steps:
            # Check and renew lease if needed
            await self.renew_lease()

            # Execute step
            await self.execute_step(step)
```python

### Lease Revocation

The system can revoke leases for failed Orchestrators:

```python
class NodeLeaseManager(NodeCoreBase):
    """Centralized lease management."""

    def __init__(self, container):
        super().__init__(container)
        self.active_leases: dict[UUID, ModelLeaseMetadata] = {}

    async def revoke_lease(self, lease_id: UUID, reason: str):
        """Revoke a lease (e.g., Orchestrator failure)."""

        if lease_id not in self.active_leases:
            raise ModelOnexError(
                message=f"Lease {lease_id} not found",
                error_code="LEASE_NOT_FOUND",
            )

        # Remove lease
        del self.active_leases[lease_id]

        # Emit revocation event
        revocation_event = ModelEvent(
            event_type=EnumEventType.LEASE_REVOKED,
            payload={
                "lease_id": str(lease_id),
                "reason": reason,
                "revoked_at": datetime.now().isoformat(),
            }
        )

        await self.event_bus.publish(revocation_event)

        self.logger.warning(f"Revoked lease {lease_id}: {reason}")
```python

## Best Practices

### 1. Always Set lease_id in Orchestrators

Every Orchestrator must generate and maintain a unique lease_id:

```python
class NodeMyOrchestrator(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)
        self.lease_id = uuid4()  # ✅ REQUIRED
        self.current_epoch = 0
```python

### 2. Validate lease_id Before Action Execution

All action processors must validate the lease:

```python
async def process(self, action: ModelAction):
    # ✅ REQUIRED: Validate lease before processing
    if action.lease_id != self.expected_lease_id:
        raise ModelOnexError("Invalid lease_id")

    # Now safe to process
    result = await self._execute(action)
```python

### 3. Increment Epoch on Every State Change

Maintain strict epoch discipline:

```python
async def update_state(self, new_state: str):
    self.workflow_state = new_state
    self.current_epoch += 1  # ✅ REQUIRED
```python

### 4. Reject Stale Actions (Old Epoch)

Never process actions from the past:

```python
if action.epoch < self.last_processed_epoch:
    raise ModelOnexError("Stale action")  # ✅ REQUIRED
```python

### 5. Use TTL for Lease Expiration

Set reasonable TTLs to prevent orphaned workflows:

```python
self.lease_metadata = ModelLeaseMetadata(
    lease_id=self.lease_id,
    acquired_at=datetime.now(),
    ttl_seconds=300,  # ✅ RECOMMENDED: 5 minutes
)
```python

### 6. Log Lease Violations for Debugging

Comprehensive logging helps diagnose issues:

```python
except ModelOnexError as e:
    self.logger.error(
        f"Lease violation: {e.message}",
        extra={
            "expected_lease": str(self.expected_lease_id),
            "received_lease": str(action.lease_id),
            "action_epoch": action.epoch,
            "current_epoch": self.current_epoch,
        }
    )
    raise
```text

## Anti-Patterns

### ❌ Sharing lease_id Across Orchestrators

**Wrong:**
```python
# BAD: Multiple Orchestrators sharing same lease
orchestrator_a.lease_id = shared_lease
orchestrator_b.lease_id = shared_lease  # Violates single-writer semantics
```text

**Right:**
```python
# GOOD: Each Orchestrator has unique lease
orchestrator_a.lease_id = uuid4()
orchestrator_b.lease_id = uuid4()
```python

### ❌ Skipping Epoch Validation

**Wrong:**
```python
async def process(self, action: ModelAction):
    # BAD: No epoch validation
    return await self._execute(action)
```python

**Right:**
```python
async def process(self, action: ModelAction):
    # GOOD: Validate epoch
    if action.epoch < self.last_processed_epoch:
        raise ModelOnexError("Stale action")
    return await self._execute(action)
```python

### ❌ Not Incrementing Epoch on State Changes

**Wrong:**
```python
async def update_state(self, new_state: str):
    # BAD: State changed but epoch not incremented
    self.workflow_state = new_state
```python

**Right:**
```python
async def update_state(self, new_state: str):
    # GOOD: Increment epoch with state change
    self.workflow_state = new_state
    self.current_epoch += 1
```python

### ❌ Reusing Expired Leases

**Wrong:**
```python
if self.lease_metadata.is_expired():
    # BAD: Continue using expired lease
    await self.emit_action(action_type, payload)
```python

**Right:**
```python
if self.lease_metadata.is_expired():
    # GOOD: Renew or re-acquire lease
    await self.renew_lease()
    await self.emit_action(action_type, payload)
```text

### ❌ Allowing Actions Without lease_id

**Wrong:**
```python
action = ModelAction(
    action_type=EnumActionType.EXECUTE,
    payload={"data": value},
    # BAD: No lease_id
)
```python

**Right:**
```python
action = ModelAction(
    action_type=EnumActionType.EXECUTE,
    payload={"data": value},
    lease_id=self.lease_id,  # GOOD: Include lease
    epoch=self.current_epoch,
)
```python

## Testing Lease Management

### Unit Tests

```python
import pytest
from uuid import uuid4
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.model_action import ModelAction

def test_lease_validation_success():
    """Test successful lease validation."""
    orchestrator = NodeMyOrchestrator(container)

    valid_action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.EXECUTE,
        lease_id=orchestrator.lease_id,  # Correct lease
        epoch=orchestrator.current_epoch,  # Current epoch
    )

    assert orchestrator.validate_action(valid_action) is True

def test_lease_validation_wrong_lease():
    """Test rejection of wrong lease_id."""
    orchestrator = NodeMyOrchestrator(container)

    invalid_action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.EXECUTE,
        lease_id=uuid4(),  # Wrong lease
        epoch=0,
    )

    with pytest.raises(ModelOnexError) as exc_info:
        orchestrator.validate_action(invalid_action)

    assert "LEASE_VIOLATION" in str(exc_info.value.error_code)

def test_epoch_validation_stale_action():
    """Test rejection of stale actions."""
    compute = NodeMyCompute(container)
    compute.expected_lease_id = uuid4()
    compute.last_processed_epoch = 5

    stale_action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.EXECUTE,
        lease_id=compute.expected_lease_id,
        epoch=3,  # Stale (< 5)
    )

    with pytest.raises(ModelOnexError) as exc_info:
        compute.validate_action(stale_action)

    assert "STALE_EPOCH" in str(exc_info.value.error_code)

def test_epoch_increment_on_state_change():
    """Test epoch increments on state changes."""
    orchestrator = NodeMyOrchestrator(container)
    initial_epoch = orchestrator.current_epoch

    orchestrator.update_workflow_state("processing")

    assert orchestrator.current_epoch == initial_epoch + 1
```python

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_workflow_with_lease():
    """Test complete workflow with lease management."""

    # Setup
    orchestrator = NodeWorkflowOrchestrator(container)
    compute = NodeMyCompute(container)
    compute.set_lease(orchestrator.lease_id)

    # Execute workflow
    await orchestrator.emit_action(
        EnumActionType.PROCESS_DATA,
        {"data": [1, 2, 3]}
    )

    # Simulate action processing
    action = await event_bus.receive()

    # Validate lease
    assert action.lease_id == orchestrator.lease_id
    assert action.epoch == 0

    # Process action
    result = await compute.process(action)

    # Verify epoch updated
    assert orchestrator.current_epoch == 1

@pytest.mark.asyncio
async def test_lease_expiration():
    """Test lease expiration handling."""

    orchestrator = NodeMyOrchestrator(container)
    orchestrator.lease_metadata.ttl_seconds = 1  # 1 second TTL

    # Wait for expiration
    await asyncio.sleep(2)

    # Verify lease expired
    assert orchestrator.lease_metadata.is_expired() is True

    # Verify cannot emit actions with expired lease
    with pytest.raises(ModelOnexError):
        orchestrator.check_lease_validity()
```text

## Summary

The lease management pattern provides robust single-writer semantics through:

- **lease_id**: Unique ownership proof for Orchestrators
- **epoch**: Version control for optimistic concurrency
- **Validation**: Strict lease and epoch checking before action execution
- **Expiration**: TTL-based lease lifecycle management

**Key Takeaways:**
1. Every Orchestrator must have a unique lease_id
2. All actions must include lease_id and epoch
3. All processors must validate lease and epoch
4. Epoch increments on every state change
5. Stale actions (old epoch) must be rejected
6. Leases should have reasonable TTLs

This pattern is essential for coordinating distributed ONEX workflows while maintaining consistency and preventing race conditions.
