# Contract-Driven NodeReducer v1.0 Specification

> **Version**: 1.0.0
> **Date**: 2025-12-09
> **Status**: DRAFT - Ready for Implementation
> **Ticket**: [OMN-495](https://linear.app/omninode/issue/OMN-495)
> **Full Roadmap**: NODEREDUCER_VERSIONING_ROADMAP.md (to be created)

---

## Executive Summary

This document defines the **minimal v1.0 implementation** of contract-driven `NodeReducer`. The goal is a stable foundation for FSM-driven state management that can be shipped safely and extended incrementally.

**v1.0 Scope**: FSM-driven state transitions with pure function semantics, Intent emission for side effects, entry/exit actions, conditional transitions, and state persistence. No parallel transitions, no complex condition expressions, no distributed state coordination.

**Core Philosophy**: The Reducer is a pure function:

```text
delta(state, event) -> (new_state, intents[])
```

All side effects are emitted as Intents for Effect nodes to execute. This maintains Reducer purity and enables deterministic state transitions.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [v1.0 Scope](#v10-scope)
3. [Core Models](#core-models)
4. [Enums](#enums)
5. [FSM Subcontract Models](#fsm-subcontract-models)
6. [Execution Model](#execution-model)
7. [Intent Pattern](#intent-pattern)
8. [Error Model](#error-model-v10)
9. [NodeReducer Behavior](#v10-nodereducer-behavior)
10. [Example Contracts](#example-contracts)
11. [Implementation Plan](#implementation-plan)
12. [Acceptance Criteria](#acceptance-criteria)

---

## Design Principles

These principles apply to v1.0 and all future versions:

1. **Pure FSM Pattern**: Reducer produces `(new_state, intents[])` without executing side effects
2. **YAML-Driven**: State machines defined declaratively in contracts - zero custom Python code required
3. **Intent Emission**: Side effects declared as Intents for Effect nodes to execute
4. **Typed Boundaries**: All public surfaces use Pydantic models
5. **Deterministic**: Same state + event always produces same new state
6. **Entry/Exit Actions**: States can define actions triggered on entry/exit (emitted as Intents)

### Thread Safety and State Management

The FSM executor functions are designed to be **pure and stateless**:

- All FSM execution functions operate only on their input parameters
- Each `execute_transition()` invocation operates on its own data without shared state
- `ModelReducerInput` and `ModelReducerOutput` are immutable (`frozen=True`) after creation
- Safe for concurrent read access from multiple threads

**Known Limitation (v1.0)**: The `MixinFSMExecution` maintains internal state (`_fsm_state`) for tracking current FSM state. This state is instance-specific - do not share `NodeReducer` instances across threads.

**TODO(v1.1)**: Add thread-local FSM state or explicit state passing for thread-safe concurrent execution.

---

## v1.0 Scope

### What's IN v1.0

| Feature | Description |
|---------|-------------|
| **FSM State Transitions** | Declarative state machine with named transitions |
| **Entry/Exit Actions** | Actions executed on state entry/exit (emitted as Intents) |
| **Transition Actions** | Actions executed during transitions |
| **Conditional Transitions** | Expression-based conditions for transition guards |
| **Intent Emission** | Side effects declared as Intents |
| **State Persistence** | Persistence intents emitted when enabled |
| **Wildcard Transitions** | Global error handlers with `from_state: "*"` |
| **Terminal State Detection** | Identify when FSM has completed |
| **State History Tracking** | Track sequence of state transitions |
| **Transition Validation** | Contract validation at load time |

### What's NOT in v1.0

| Feature | Deferred To | Rationale |
|---------|-------------|-----------|
| **Parallel Transitions** | v1.1 | Merge semantics need careful design |
| **Complex Expressions** | v1.1 | Arithmetic and functions require expression language |
| **Distributed State** | v1.2 | Requires distributed coordination primitives |
| **Hierarchical States** | v1.2 | Parent-child state relationships add complexity |
| **State Timeouts** | v1.1 | Automatic transitions on timeout |
| **Transition Retries** | v1.1 | Fields defined but execution deferred |
| **Rollback Execution** | v1.2 | Rollback fields defined but execution deferred |
| **Custom Condition Evaluators** | v1.2 | Pluggable condition evaluation |
| **Real-time State Sync** | v1.3 | Multi-instance state synchronization |

---

## Core Models

### ModelReducerInput

```python
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)


class ModelReducerInput[T_Input](BaseModel):
    """
    Input model for NodeReducer operations.

    Strongly typed input wrapper for data reduction operations with
    comprehensive configuration for streaming modes, conflict resolution,
    and batch processing.

    Type Parameters:
        T_Input: The type of elements in the data list.

    Thread Safety:
        Immutable (frozen=True) after creation - thread-safe for
        concurrent read access.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    data: list[T_Input]
    reduction_type: EnumReductionType
    operation_id: UUID = Field(default_factory=uuid4)
    conflict_resolution: EnumConflictResolution = EnumConflictResolution.LAST_WINS
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batch_size: int = Field(default=1000, gt=0, le=10000)
    window_size_ms: int = Field(default=5000, ge=1000, le=60000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
```

### ModelReducerOutput

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.reducer.model_intent import ModelIntent


class ModelReducerOutput[T_Output](BaseModel):
    """
    Output model for NodeReducer operations.

    Strongly typed output wrapper with reduction statistics,
    conflict resolution metadata, and Intent emission list.

    Pure FSM Pattern:
        result: The new state after reduction
        intents: Side effects to be executed by Effect node

    Thread Safety:
        Immutable (frozen=True) after creation.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    result: T_Output
    operation_id: UUID
    reduction_type: EnumReductionType
    processing_time_ms: float
    items_processed: int
    conflicts_resolved: int = 0
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batches_processed: int = 1

    # Intent emission for pure FSM pattern
    intents: list[ModelIntent] = Field(
        default_factory=list,
        description="Side effect intents emitted during reduction (for Effect node)",
    )

    metadata: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
```

### ModelIntent

```python
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelIntent(BaseModel):
    """
    Intent declaration for side effects from pure Reducer FSM.

    The Reducer is a pure function: delta(state, action) -> (new_state, intents[])
    Instead of performing side effects directly, it emits Intents describing
    what side effects should occur. The Effect node consumes these Intents
    and executes them.

    Intent Types (Common Examples):
        - "log_event": Emit log message or metrics
        - "emit_event": Publish event to message bus
        - "persist_state": Write state to storage
        - "record_metric": Record metrics to monitoring service
        - "fsm_state_action": Execute FSM entry/exit action
        - "fsm_transition_action": Execute FSM transition action

    Thread Safety:
        Immutable (frozen=True) after creation. Note: shallow immutability -
        mutable nested data (dict/list contents) can still be modified.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
    )

    intent_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this intent",
    )

    intent_type: str = Field(
        ...,
        description="Type of intent (log_event, emit_event, persist_state, etc.)",
        min_length=1,
        max_length=100,
    )

    target: str = Field(
        ...,
        description="Target for the intent execution (service, channel, topic)",
        min_length=1,
        max_length=200,
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Intent payload data",
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    # Lease fields for single-writer semantics
    lease_id: UUID | None = Field(
        default=None,
        description="Optional lease ID if this intent relates to a leased workflow",
    )

    epoch: int | None = Field(
        default=None,
        description="Optional epoch if this intent relates to versioned state",
        ge=0,
    )
```

### ModelFSMTransitionResult

```python
from datetime import datetime
from typing import Any

from omnibase_core.models.reducer.model_intent import ModelIntent


class ModelFSMTransitionResult:
    """
    Result of FSM transition execution.

    Pure data structure containing transition outcome and intents for side effects.
    """

    def __init__(
        self,
        success: bool,
        new_state: str,
        old_state: str,
        transition_name: str | None,
        intents: list[ModelIntent],
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.new_state = new_state
        self.old_state = old_state
        self.transition_name = transition_name
        self.intents = intents
        self.metadata = metadata or {}
        self.error = error
        self.timestamp = datetime.now().isoformat()
```

### ModelFSMStateSnapshot

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelFSMStateSnapshot:
    """
    Current FSM state snapshot.

    Frozen dataclass preventing field reassignment.

    Warning: context (dict) and history (list) are mutable containers.
    Avoid modifying these after creation to maintain FSM purity.
    FSM executor creates new snapshots rather than mutating existing ones.
    """

    current_state: str
    context: dict[str, Any]
    history: list[str] = field(default_factory=list)
```

---

## Enums

### EnumReductionType

```python
from enum import Enum


class EnumReductionType(Enum):
    """Types of reduction operations supported."""

    FOLD = "fold"              # Reduce collection to single value
    ACCUMULATE = "accumulate"  # Build up result incrementally
    MERGE = "merge"            # Combine multiple datasets
    AGGREGATE = "aggregate"    # Statistical aggregation
    NORMALIZE = "normalize"    # Score normalization and ranking
    DEDUPLICATE = "deduplicate"  # Remove duplicates
    SORT = "sort"              # Sort and rank operations
    FILTER = "filter"          # Filter with conditions
    GROUP = "group"            # Group by criteria
    TRANSFORM = "transform"    # Data transformation
```

### EnumConflictResolution

```python
from enum import Enum


class EnumConflictResolution(Enum):
    """Strategies for resolving conflicts during reduction."""

    FIRST_WINS = "first_wins"  # Keep first encountered value
    LAST_WINS = "last_wins"    # Keep last encountered value
    MERGE = "merge"            # Attempt to merge values
    ERROR = "error"            # Raise error on conflict
    CUSTOM = "custom"          # Use custom resolution function
```

### EnumStreamingMode

```python
from enum import Enum


class EnumStreamingMode(Enum):
    """Streaming processing modes."""

    BATCH = "batch"            # Process all data at once
    INCREMENTAL = "incremental"  # Process data incrementally
    WINDOWED = "windowed"      # Process in time windows
    REAL_TIME = "real_time"    # Process as data arrives
```

---

## FSM Subcontract Models

### ModelFSMSubcontract

```python
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMSubcontract(BaseModel):
    """
    FSM (Finite State Machine) subcontract model.

    Comprehensive state machine subcontract providing state definitions,
    transitions, operations, validation, and recovery mechanisms.
    Designed for composition into node contracts requiring FSM functionality.

    VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core FSM identification
    state_machine_name: str = Field(
        default=...,
        description="Unique name for the state machine",
        min_length=1,
    )

    state_machine_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the state machine definition",
    )

    description: str = Field(
        default=...,
        description="Human-readable state machine description",
        min_length=1,
    )

    # ONEX correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for FSM instance tracking",
    )

    # State definitions
    states: list["ModelFSMStateDefinition"] = Field(
        default=...,
        description="All available states in the system",
        min_length=1,
    )

    initial_state: str = Field(
        default=...,
        description="Name of the initial state",
        min_length=1,
    )

    terminal_states: list[str] = Field(
        default_factory=list,
        description="Names of terminal/final states",
    )

    error_states: list[str] = Field(
        default_factory=list,
        description="Names of error/failure states",
    )

    # Transition specifications
    transitions: list["ModelFSMStateTransition"] = Field(
        default=...,
        description="All valid state transitions",
        min_length=1,
    )

    # Operation definitions
    operations: list["ModelFSMOperation"] = Field(
        default_factory=list,
        description="Available transition operations",
    )

    # FSM persistence and recovery
    persistence_enabled: bool = Field(
        default=True,
        description="Whether state persistence is enabled",
    )

    checkpoint_interval_ms: int = Field(
        default=30000,
        description="Interval for automatic checkpoints",
        ge=1000,
    )

    max_checkpoints: int = Field(
        default=10,
        description="Maximum number of checkpoints to retain",
        ge=1,
    )

    recovery_enabled: bool = Field(
        default=True,
        description="Whether automatic recovery is enabled",
    )

    rollback_enabled: bool = Field(
        default=True,
        description="Whether rollback operations are enabled",
    )

    # Conflict resolution
    conflict_resolution_strategy: str = Field(
        default="priority_based",
        description="Strategy for resolving transition conflicts",
    )

    concurrent_transitions_allowed: bool = Field(
        default=False,
        description="Whether concurrent transitions are allowed",
    )

    transition_timeout_ms: int = Field(
        default=5000,
        description="Default timeout for transitions",
        ge=1,
    )

    # Validation and monitoring
    strict_validation_enabled: bool = Field(
        default=True,
        description="Whether strict state validation is enabled",
    )

    state_monitoring_enabled: bool = Field(
        default=True,
        description="Whether state monitoring/metrics are enabled",
    )

    event_logging_enabled: bool = Field(
        default=True,
        description="Whether state transition events are logged",
    )

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,
        validate_assignment=True,
    )
```

### ModelFSMStateDefinition

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMStateDefinition(BaseModel):
    """
    State definition for FSM subcontract.

    Defines state properties, lifecycle management,
    and validation rules for FSM state handling.
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED
        description="Model version",
    )

    state_name: str = Field(
        default=...,
        description="Unique name for the state",
        min_length=1,
    )

    state_type: str = Field(
        default=...,
        description="Type classification (operational, snapshot, error, terminal)",
        min_length=1,
    )

    description: str = Field(
        default=...,
        description="Human-readable state description",
        min_length=1,
    )

    is_terminal: bool = Field(
        default=False,
        description="Whether this is a terminal/final state",
    )

    is_recoverable: bool = Field(
        default=True,
        description="Whether recovery is possible from this state",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Maximum time allowed in this state",
        ge=1,
    )

    entry_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute on state entry",
    )

    exit_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute on state exit",
    )

    required_data: list[str] = Field(
        default_factory=list,
        description="Required data fields for this state",
    )

    optional_data: list[str] = Field(
        default_factory=list,
        description="Optional data fields for this state",
    )

    validation_rules: list[str] = Field(
        default_factory=list,
        description="Validation rules for state data",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

### ModelFSMStateTransition

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMStateTransition(BaseModel):
    """
    State transition specification for FSM subcontract.

    Defines complete transition behavior including source/target states,
    triggers, conditions, actions, and rollback mechanisms.
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED
        description="Model version",
    )

    transition_name: str = Field(
        default=...,
        description="Unique name for the transition",
        min_length=1,
    )

    from_state: str = Field(
        default=...,
        description="Source state name (use '*' for wildcard)",
        min_length=1,
    )

    to_state: str = Field(
        default=...,
        description="Target state name",
        min_length=1,
    )

    trigger: str = Field(
        default=...,
        description="Event or condition that triggers transition",
        min_length=1,
    )

    priority: int = Field(
        default=1,
        description="Priority for conflict resolution",
        ge=1,
    )

    conditions: list["ModelFSMTransitionCondition"] = Field(
        default_factory=list,
        description="Conditions that must be met for transition",
    )

    actions: list["ModelFSMTransitionAction"] = Field(
        default_factory=list,
        description="Actions to execute during transition",
    )

    rollback_transitions: list[str] = Field(
        default_factory=list,
        description="Available rollback transition names",
    )

    is_atomic: bool = Field(
        default=True,
        description="Whether transition must complete atomically",
    )

    retry_enabled: bool = Field(
        default=False,
        description="Whether failed transitions can be retried",
    )

    max_retries: int = Field(
        default=0,
        description="Maximum number of retry attempts",
        ge=0,
    )

    retry_delay_ms: int = Field(
        default=1000,
        description="Delay between retry attempts",
        ge=0,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

### ModelFSMTransitionCondition

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMTransitionCondition(BaseModel):
    """
    Condition specification for FSM state transitions.

    Defines condition types, expressions, and validation logic
    for determining valid state transitions.
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED
        description="Subcontract version",
    )

    condition_name: str = Field(
        default=...,
        description="Unique name for the condition",
        min_length=1,
    )

    condition_type: str = Field(
        default=...,
        description="Type of condition (validation, state, processing, custom)",
        min_length=1,
    )

    expression: str = Field(
        default=...,
        description="Condition expression or rule",
        min_length=1,
    )

    required: bool = Field(
        default=True,
        description="Whether this condition is required for transition",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if condition fails",
    )

    retry_count: int = Field(
        default=0,
        description="Number of retries for failed conditions",
        ge=0,
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for condition evaluation",
        ge=1,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

### ModelFSMTransitionAction

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMTransitionAction(BaseModel):
    """
    Action specification for FSM state transitions.

    Defines actions to execute during state transitions,
    including logging, validation, and state modifications.
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED
        description="Subcontract version",
    )

    action_name: str = Field(
        default=...,
        description="Unique name for the action",
        min_length=1,
    )

    action_type: str = Field(
        default=...,
        description="Type of action (log, validate, modify, event, cleanup)",
        min_length=1,
    )

    action_config: list["ModelActionConfigParameter"] = Field(
        default_factory=list,
        description="Strongly-typed configuration parameters for the action",
    )

    execution_order: int = Field(
        default=1,
        description="Order of execution relative to other actions",
        ge=1,
    )

    is_critical: bool = Field(
        default=False,
        description="Whether action failure should abort transition",
    )

    rollback_action: str | None = Field(
        default=None,
        description="Action to execute if rollback is needed",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for action execution",
        ge=1,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

---

## Execution Model

### FSM Execution Flow

v1.0 uses **pure function FSM execution**:

```text
   Input Event
       │
       ▼
┌─────────────────┐
│ Validate State  │──▶ Error if invalid
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Find Transition │──▶ Error if none found
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Evaluate Guards  │──▶ Fail silently if conditions not met
└────────┬────────┘
         │ Conditions Met
         ▼
┌─────────────────┐
│  Exit Actions   │──▶ Emit Intents
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Trans. Actions   │──▶ Emit Intents
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Entry Actions  │──▶ Emit Intents
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Persistence   │──▶ Emit Intent (if enabled)
└────────┬────────┘
         │
         ▼
   FSMTransitionResult
   (new_state, intents[])
```

### Execution Rules

1. **Pure Function**: `execute_transition(fsm, state, trigger, context)` returns result and intents
2. **No Side Effects**: All side effects emitted as Intents
3. **Abort on Invalid State**: Invalid current state throws `ModelOnexError`
4. **Abort on No Transition**: No matching transition throws `ModelOnexError`
5. **Silent Fail on Conditions**: Unmet conditions return failed result (no exception)
6. **Action Order**: Exit actions -> Transition actions -> Entry actions

### Condition Evaluation

v1.0 uses a simple expression-based condition evaluation:

```yaml
conditions:
  - condition_name: has_data_sources
    condition_type: validation
    expression: "data_sources min_length 1"
    required: true
```

**v1.0 Expression Format**: `field_name operator expected_value`

**Supported Operators**:

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | String equality (type-coerced) | `status equals active` |
| `not_equals` | String inequality (type-coerced) | `status not_equals error` |
| `min_length` | Minimum collection length | `items min_length 1` |
| `max_length` | Maximum collection length | `items max_length 100` |
| `greater_than` | Numeric comparison | `count greater_than 0` |
| `less_than` | Numeric comparison | `count less_than 1000` |
| `exists` | Field exists in context | `user_id exists` |
| `not_exists` | Field does not exist | `error_code not_exists` |

**Type Coercion Behavior**:

The `equals` and `not_equals` operators perform **string-based comparison** by casting both sides to `str` before evaluation. This is intentional for YAML/JSON config compatibility.

```text
10 == "10"           -> True  (both become "10")
True == "True"       -> True  (both become "True")
None == "None"       -> True  (both become "None")
```

**Workarounds for strict typing**:
- Use `greater_than`/`less_than` for numeric comparison
- Preprocess context values before FSM execution

### Wildcard Transitions

Wildcard transitions (`from_state: "*"`) match from any state, useful for global error handlers:

```yaml
transitions:
  - transition_name: global_error_handler
    from_state: "*"
    to_state: error
    trigger: fatal_error
```

**Matching Priority**: Exact state match takes precedence over wildcard.

### State Persistence

When `persistence_enabled: true`, the executor emits a persistence Intent:

```python
ModelIntent(
    intent_type="persist_state",
    target="state_persistence",
    payload={
        "fsm_name": fsm.state_machine_name,
        "state": new_state,
        "previous_state": old_state,
        "context": context,
        "timestamp": datetime.now(UTC).isoformat(),
    },
    priority=1,  # High priority
)
```

---

## Intent Pattern

### Pure FSM Philosophy

The NodeReducer follows the pure FSM pattern:

```python
# Pure function signature
def delta(state: S, action: A) -> tuple[S, list[Intent]]:
    # Determine new state (pure logic)
    # Emit intents for side effects
    return (new_state, intents)
```

**Key Principle**: The Reducer never performs side effects directly. It only declares what should happen through Intents.

### Common Intent Types

| Intent Type | Target | Purpose |
|-------------|--------|---------|
| `persist_state` | `state_persistence` | Save FSM state to storage |
| `record_metric` | `metrics_service` | Record transition metrics |
| `log_event` | `logging_service` | Log state transitions |
| `fsm_state_action` | `action_executor` | Execute entry/exit action |
| `fsm_transition_action` | `action_executor` | Execute transition action |
| `emit_event` | Event topic | Publish domain event |

### Intent Flow

```text
┌─────────────┐
│  NodeReducer │  Emits Intents
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Intent[]   │  Pure declarations
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  NodeEffect │  Executes side effects
└─────────────┘
```

---

## Error Model (v1.0)

v1.0 uses **ModelOnexError** for FSM execution errors:

```python
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Invalid state error
raise ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message=f"Invalid current state: {current_state}",
    context={"fsm": fsm.state_machine_name, "state": current_state},
)

# No transition found error
raise ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message=f"No transition for trigger '{trigger}' from state '{current_state}'",
    context={
        "fsm": fsm.state_machine_name,
        "state": current_state,
        "trigger": trigger,
    },
)
```

### Error Handling Strategy

| Scenario | Behavior |
|----------|----------|
| Invalid current state | Raise `ModelOnexError` |
| No matching transition | Raise `ModelOnexError` |
| Conditions not met | Return failed result, emit log Intent |
| Action execution fails | Emit failure Intent (v1.0 actions are non-blocking) |
| Invalid target state | Raise `ModelOnexError` |

---

## v1.0 NodeReducer Behavior

### Startup Behavior

When a `NodeReducer` instance starts:

1. **Load Contract**: Read `state_transitions` from node contract
2. **Validate Structure**: Validate `ModelFSMSubcontract` with model validators
3. **Initialize FSM**: Set FSM state to `initial_state`
4. **Fail Fast**: If contract validation fails, node **must not start**

### Runtime Behavior

When `process(ModelReducerInput)` is called:

1. **Extract Trigger**: Get trigger from `input_data.metadata.get("trigger", "process")`
2. **Build Context**: Combine input data with metadata
3. **Execute Transition**: Call `execute_fsm_transition()`
4. **Build Output**: Create `ModelReducerOutput` with FSM result and intents
5. **Return**: Return typed output to caller

### Lifecycle

```text
┌─────────────────┐
│  Contract Load  │──▶ Validates FSM structure
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FSM Initialize │──▶ Sets initial state
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Node Ready    │──▶ Contract frozen, FSM initialized
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   process()     │──▶ Executes transition, returns result with intents
└─────────────────┘
```

### Usage

```python
from omnibase_core.nodes import NodeReducer


class NodeOrderStateMachine(NodeReducer):
    """Order state machine - all logic from contract."""
    pass


# Usage
node = NodeOrderStateMachine(container)

# Execute transition
input_data = ModelReducerInput(
    data=[{"order_id": "12345", "items": [...]}],
    reduction_type=EnumReductionType.TRANSFORM,
    metadata={
        "trigger": "submit_order",
        "customer_id": "cust_001",
    },
)

result = await node.process(input_data)

# Check result
print(f"New state: {result.metadata['fsm_state']}")
print(f"Intents to execute: {len(result.intents)}")

# Process intents via Effect node
for intent in result.intents:
    await effect_node.execute_intent(intent)
```

---

## Example Contracts

### Order Processing State Machine

```yaml
# examples/contracts/reducer/order_processor_fsm.yaml
node_type: REDUCER
node_name: order_processor
node_version: "1.0.0"

state_transitions:
  version:
    major: 1
    minor: 0
    patch: 0
  state_machine_name: order_processing_fsm
  state_machine_version:
    major: 1
    minor: 0
    patch: 0
  description: "Order processing state machine with payment and fulfillment"

  initial_state: pending
  terminal_states:
    - completed
    - cancelled
    - refunded
  error_states:
    - payment_failed
    - fulfillment_failed

  states:
    - version: { major: 1, minor: 0, patch: 0 }
      state_name: pending
      state_type: operational
      description: "Order submitted, awaiting payment"
      entry_actions:
        - create_order_record
        - send_order_confirmation
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: payment_processing
      state_type: operational
      description: "Payment is being processed"
      timeout_ms: 30000
      entry_actions:
        - initiate_payment
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: paid
      state_type: operational
      description: "Payment received, ready for fulfillment"
      entry_actions:
        - record_payment
        - notify_warehouse
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: fulfilling
      state_type: operational
      description: "Order is being fulfilled"
      entry_actions:
        - begin_fulfillment
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: shipped
      state_type: operational
      description: "Order has been shipped"
      entry_actions:
        - send_shipping_notification
      exit_actions:
        - log_state_transition

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: completed
      state_type: terminal
      description: "Order successfully completed"
      is_terminal: true
      entry_actions:
        - send_delivery_confirmation
        - update_customer_stats

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: cancelled
      state_type: terminal
      description: "Order was cancelled"
      is_terminal: true
      entry_actions:
        - process_cancellation
        - send_cancellation_notification

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: payment_failed
      state_type: error
      description: "Payment processing failed"
      is_recoverable: true
      entry_actions:
        - log_payment_failure
        - send_payment_failure_notification

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: fulfillment_failed
      state_type: error
      description: "Fulfillment failed"
      is_recoverable: true
      entry_actions:
        - log_fulfillment_failure
        - notify_support

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: refunded
      state_type: terminal
      description: "Order was refunded"
      is_terminal: true
      entry_actions:
        - process_refund
        - send_refund_notification

  transitions:
    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: start_payment
      from_state: pending
      to_state: payment_processing
      trigger: process_payment
      conditions:
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_items
          condition_type: validation
          expression: "items min_length 1"
          required: true
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_customer
          condition_type: validation
          expression: "customer_id exists"
          required: true
      actions:
        - version: { major: 1, minor: 0, patch: 0 }
          action_name: validate_inventory
          action_type: validate
          is_critical: true

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: payment_success
      from_state: payment_processing
      to_state: paid
      trigger: payment_completed
      conditions:
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_transaction_id
          condition_type: validation
          expression: "transaction_id exists"
          required: true

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: payment_failure
      from_state: payment_processing
      to_state: payment_failed
      trigger: payment_error

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: begin_fulfillment
      from_state: paid
      to_state: fulfilling
      trigger: start_fulfillment

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: ship_order
      from_state: fulfilling
      to_state: shipped
      trigger: order_shipped
      conditions:
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_tracking
          condition_type: validation
          expression: "tracking_number exists"
          required: true

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: deliver_order
      from_state: shipped
      to_state: completed
      trigger: order_delivered

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: cancel_order
      from_state: pending
      to_state: cancelled
      trigger: cancel
      priority: 2

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: retry_payment
      from_state: payment_failed
      to_state: payment_processing
      trigger: retry_payment

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: refund_order
      from_state: payment_failed
      to_state: refunded
      trigger: refund

    # Wildcard transition for global error handling
    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: global_cancel
      from_state: "*"
      to_state: cancelled
      trigger: force_cancel
      priority: 10

  persistence_enabled: true
  checkpoint_interval_ms: 30000
  max_checkpoints: 10
  recovery_enabled: true
  rollback_enabled: true
  transition_timeout_ms: 5000
  strict_validation_enabled: true
  state_monitoring_enabled: true
  event_logging_enabled: true
```

### Metrics Aggregation FSM

```yaml
# examples/contracts/reducer/metrics_aggregation_fsm.yaml
node_type: REDUCER
node_name: metrics_aggregator
node_version: "1.0.0"

state_transitions:
  version:
    major: 1
    minor: 0
    patch: 0
  state_machine_name: metrics_aggregation_fsm
  state_machine_version:
    major: 1
    minor: 0
    patch: 0
  description: "Metrics collection and aggregation state machine"

  initial_state: idle
  terminal_states:
    - completed
  error_states:
    - error

  states:
    - version: { major: 1, minor: 0, patch: 0 }
      state_name: idle
      state_type: operational
      description: "Waiting for data collection to start"
      entry_actions: []
      exit_actions: []

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: collecting
      state_type: operational
      description: "Collecting metrics from sources"
      entry_actions:
        - start_collection
      exit_actions:
        - finalize_collection

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: aggregating
      state_type: operational
      description: "Aggregating collected metrics"
      entry_actions:
        - begin_aggregation
      exit_actions: []

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: completed
      state_type: terminal
      description: "Aggregation complete"
      is_terminal: true
      entry_actions:
        - emit_aggregation_results

    - version: { major: 1, minor: 0, patch: 0 }
      state_name: error
      state_type: error
      description: "Error during processing"
      is_recoverable: true
      entry_actions:
        - log_error

  transitions:
    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: start_collecting
      from_state: idle
      to_state: collecting
      trigger: collect_metrics
      conditions:
        - version: { major: 1, minor: 0, patch: 0 }
          condition_name: has_data_sources
          condition_type: validation
          expression: "data_sources min_length 1"
          required: true
      actions:
        - version: { major: 1, minor: 0, patch: 0 }
          action_name: initialize_metrics
          action_type: setup

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: begin_aggregate
      from_state: collecting
      to_state: aggregating
      trigger: start_aggregation

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: finish
      from_state: aggregating
      to_state: completed
      trigger: complete

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: handle_error
      from_state: "*"
      to_state: error
      trigger: error_occurred

    - version: { major: 1, minor: 0, patch: 0 }
      transition_name: recover
      from_state: error
      to_state: idle
      trigger: reset

  persistence_enabled: true
  transition_timeout_ms: 5000
```

---

## Implementation Plan

### Phase 1: Core Models & Enums (~3 days)

| Task | File | Priority |
|------|------|----------|
| EnumReductionType | `enums/enum_reducer_types.py` | P0 |
| EnumConflictResolution | `enums/enum_reducer_types.py` | P0 |
| EnumStreamingMode | `enums/enum_reducer_types.py` | P0 |
| ModelIntent | `models/reducer/model_intent.py` | P0 |
| ModelReducerInput | `models/reducer/model_reducer_input.py` | P0 |
| ModelReducerOutput | `models/reducer/model_reducer_output.py` | P0 |
| ModelFSMStateSnapshot | `models/fsm/model_fsm_state_snapshot.py` | P0 |
| ModelFSMTransitionResult | `models/fsm/model_fsm_transition_result.py` | P0 |

### Phase 2: FSM Subcontract Models (~3 days)

| Task | File | Priority |
|------|------|----------|
| ModelFSMSubcontract | `models/contracts/subcontracts/model_fsm_subcontract.py` | P0 |
| ModelFSMStateDefinition | `models/contracts/subcontracts/model_fsm_state_definition.py` | P0 |
| ModelFSMStateTransition | `models/contracts/subcontracts/model_fsm_state_transition.py` | P0 |
| ModelFSMTransitionCondition | `models/contracts/subcontracts/model_fsm_transition_condition.py` | P0 |
| ModelFSMTransitionAction | `models/contracts/subcontracts/model_fsmtransitionaction.py` | P0 |
| ModelFSMOperation | `models/contracts/subcontracts/model_fsm_operation.py` | P0 |

### Phase 3: Execution & Node (~3 days)

| Task | File | Priority |
|------|------|----------|
| fsm_executor.py | `utils/fsm_executor.py` | P0 |
| MixinFSMExecution | `mixins/mixin_fsm_execution.py` | P0 |
| NodeReducer | `nodes/node_reducer.py` | P0 |

### Phase 4: Testing (~3 days)

| Task | File | Priority |
|------|------|----------|
| Unit tests for enums | `tests/unit/enums/test_reducer_types.py` | P0 |
| Unit tests for models | `tests/unit/models/reducer/test_*.py` | P0 |
| Unit tests for FSM models | `tests/unit/models/fsm/test_*.py` | P0 |
| Unit tests for executor | `tests/unit/utils/test_fsm_executor.py` | P0 |
| Integration tests | `tests/integration/test_reducer_fsm.py` | P0 |

### Total Estimate

- **Files**: ~20 files
- **Code**: ~1500 lines
- **Tests**: ~800 lines
- **Timeline**: 12 working days

---

## Acceptance Criteria

### Functional Requirements

- [ ] `ModelFSMSubcontract` validates contracts with model validators
- [ ] All FSM state definitions validated (initial, terminal, error states)
- [ ] All transitions validated (from_state, to_state must exist)
- [ ] FSM executes transitions using pure function semantics
- [ ] Entry/exit actions emit Intents (not executed directly)
- [ ] Transition actions emit Intents (not executed directly)
- [ ] Conditions evaluated using expression grammar
- [ ] Wildcard transitions (`from_state: "*"`) supported
- [ ] Persistence Intents emitted when enabled
- [ ] Terminal state detection working

### Type Safety Requirements

- [ ] All FSM models use `ConfigDict(extra="ignore")` for YAML compatibility
- [ ] All result models use `ConfigDict(frozen=True)` for immutability
- [ ] `ModelIntent` uses `ConfigDict(extra="forbid", frozen=True)`
- [ ] `ModelReducerInput`/`Output` are generic `[T_Input]`/`[T_Output]`
- [ ] mypy --strict passes with zero errors

### Testing Requirements

- [ ] Unit tests for each enum
- [ ] Unit tests for each model
- [ ] Unit tests for FSM executor functions
- [ ] Unit tests for condition evaluation
- [ ] Integration test with example FSM contract
- [ ] 90%+ code coverage

### Documentation Requirements

- [ ] Example contracts in `examples/contracts/reducer/`
- [ ] API documentation for public functions
- [ ] Migration guide from custom reducer implementations
- [ ] Intent pattern documentation

---

## References

- **Versioning Roadmap**: NODEREDUCER_VERSIONING_ROADMAP.md (to be created)
- **Example Contract**: order_processor_fsm.yaml (to be created in examples/contracts/reducer/)
- **Linear Issue**: [OMN-495](https://linear.app/omninode/issue/OMN-495)
- **NodeReducer Source**: [node_reducer.py](../../src/omnibase_core/nodes/node_reducer.py)
- **FSM Executor Source**: [fsm_executor.py](../../src/omnibase_core/utils/fsm_executor.py)
- **NodeCompute Pattern**: [CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md](./CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md)

---

**Last Updated**: 2025-12-09
**Version**: 1.0.0
**Status**: DRAFT - Ready for Implementation
