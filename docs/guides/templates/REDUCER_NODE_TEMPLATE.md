> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > Templates > REDUCER Node

# REDUCER Node Template

## Overview

This template provides the unified architecture pattern for ONEX REDUCER nodes. REDUCER nodes are FSM-driven state management components responsible for aggregating and reducing data while maintaining pure state transitions.

**v0.4.0 Architecture**: `NodeReducer` is the PRIMARY implementation (not a "declarative" variant). All state transitions are defined declaratively via YAML FSM contracts.

## Key Characteristics

- **FSM-Driven State Management**: All state transitions defined in YAML contracts
- **Pure State Transitions**: No direct side effects - emits `ModelIntent` for Effect nodes
- **Data Aggregation**: Reduce, merge, fold, and transform data collections
- **Intent-Based Architecture**: `delta(state, action) -> (new_state, intents[])`
- **Type Safety**: Full Pydantic validation with generic typing
- **Zero Custom Code**: Entirely YAML-driven state machine behavior

## Directory Structure

```
{REPOSITORY_NAME}/
├── src/
│   └── {REPOSITORY_NAME}/
│       └── nodes/
│           └── node_{DOMAIN}_{MICROSERVICE_NAME}_reducer/
│               └── v1_0_0/
│                   ├── __init__.py
│                   ├── node.py
│                   ├── config.py
│                   ├── contracts/
│                   │   ├── __init__.py
│                   │   ├── reducer_contract.py
│                   │   └── subcontracts/
│                   │       ├── __init__.py
│                   │       ├── fsm_subcontract.yaml
│                   │       ├── input_subcontract.yaml
│                   │       ├── output_subcontract.yaml
│                   │       └── config_subcontract.yaml
│                   ├── models/
│                   │   ├── __init__.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_input.py
│                   │   └── model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_output.py
│                   ├── enums/
│                   │   ├── __init__.py
│                   │   └── enum_{DOMAIN}_{MICROSERVICE_NAME}_state.py
│                   └── manifest.yaml
└── tests/
    └── {REPOSITORY_NAME}/
        └── nodes/
            └── node_{DOMAIN}_{MICROSERVICE_NAME}_reducer/
                └── v1_0_0/
                    ├── test_node.py
                    ├── test_fsm_transitions.py
                    ├── test_contracts.py
                    └── test_intents.py
```

## Template Files

### 1. Node Implementation (`node.py`)

```python
"""ONEX REDUCER node for {DOMAIN} {MICROSERVICE_NAME} state management."""

from typing import Any
from uuid import UUID
import time

# v0.4.0 unified node imports
from omnibase_core.nodes import (
    NodeReducer,
    ModelReducerInput,
    ModelReducerOutput,
    EnumReductionType,
    EnumConflictResolution,
    EnumStreamingMode,
)
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

from .enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_state import Enum{DomainCamelCase}{MicroserviceCamelCase}State


class Node{DomainCamelCase}{MicroserviceCamelCase}Reducer(
    NodeReducer[
        dict[str, Any],  # T_Input: Type of input data items
        dict[str, Any],  # T_Output: Type of output result
    ]
):
    """REDUCER node for {DOMAIN} {MICROSERVICE_NAME} FSM-driven state management.

    This node provides pure FSM-based state aggregation for {DOMAIN} domain
    operations, focusing on {MICROSERVICE_NAME} state transitions and data reduction.

    Architecture Pattern:
        - Pure FSM: delta(state, action) -> (new_state, intents[])
        - No direct side effects - all effects emitted as ModelIntent
        - Effect nodes consume and execute intents

    Key Features:
        - FSM-driven state transitions via YAML contract
        - Type-safe input/output validation
        - Conflict resolution strategies
        - Streaming mode support (BATCH, WINDOWED, CONTINUOUS)
        - Intent emission for downstream Effect nodes

    Thread Safety:
        NodeReducer instances are NOT thread-safe due to mutable FSM state.
        Each thread should have its own instance. See docs/guides/THREADING.md.

    Example:
        ```python
        node = Node{DomainCamelCase}{MicroserviceCamelCase}Reducer(container)

        # Initialize FSM state
        node.initialize_fsm_state(
            node.contract.state_machine,
            context={"batch_size": 1000}
        )

        # Execute reduction with FSM transition
        result = await node.process(input_data)

        # Check FSM state and emitted intents
        print(f"New state: {result.metadata['fsm_state']}")
        print(f"Intents emitted: {len(result.intents)}")
        ```
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the REDUCER node with container.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Node-specific initialization (non-FSM components)
        # FSM contract is automatically loaded by base class

        # Performance tracking
        self._reduction_metrics: list[dict[str, Any]] = []
        self._state_transition_count: int = 0

    async def process(
        self,
        input_data: ModelReducerInput[dict[str, Any]],
    ) -> ModelReducerOutput[dict[str, Any]]:
        """Process input using FSM-driven state transitions.

        Pure FSM pattern: Executes transition, emits intents for side effects.
        The base class handles FSM contract execution; override only for
        custom pre/post processing.

        Args:
            input_data: Reducer input with data, reduction type, and metadata

        Returns:
            Reducer output with reduced result, FSM state, and intents

        Raises:
            ModelOnexError: If FSM contract not loaded or transition fails

        Example:
            ```python
            input_data = ModelReducerInput(
                data=[{"user": "alice", "score": 100}, {"user": "bob", "score": 85}],
                reduction_type=EnumReductionType.AGGREGATE,
                metadata={
                    "trigger": "aggregate_scores",
                    "group_by": "user",
                }
            )

            result = await node.process(input_data)
            print(f"Aggregated result: {result.result}")
            print(f"Items processed: {result.items_processed}")
            ```
        """
        start_time = time.perf_counter()

        # Execute base FSM-driven processing
        result = await super().process(input_data)

        # Track metrics
        processing_time_ms = (time.perf_counter() - start_time) * 1000
        self._reduction_metrics.append({
            "reduction_type": input_data.reduction_type.value,
            "items_processed": result.items_processed,
            "processing_time_ms": processing_time_ms,
            "timestamp": time.time(),
        })
        self._state_transition_count += 1

        return result

    def emit_intent(
        self,
        intent_type: str,
        target: str,
        payload: dict[str, Any],
        priority: int = 1,
    ) -> ModelIntent:
        """Create an intent for side effect execution by Effect nodes.

        Reducer nodes are pure - they don't execute side effects directly.
        Instead, they emit intents describing what should happen.

        Args:
            intent_type: Type of intent (log, emit_event, write, notify)
            target: Target for intent execution (service, channel, topic)
            payload: Intent payload data
            priority: Execution priority (1-10, higher = more urgent)

        Returns:
            ModelIntent ready for emission

        Example:
            ```python
            # Intent to emit an event
            intent = self.emit_intent(
                intent_type="emit_event",
                target="user.score_updated",
                payload={"user_id": "123", "new_score": 250},
                priority=5,
            )
            ```
        """
        return ModelIntent(
            intent_type=intent_type,
            target=target,
            payload=payload,
            priority=priority,
        )

    async def get_reduction_metrics(self) -> dict[str, Any]:
        """Get current reduction performance metrics.

        Returns:
            Dictionary with performance statistics
        """
        if not self._reduction_metrics:
            return {
                "total_reductions": 0,
                "average_processing_time_ms": 0.0,
                "state_transitions": 0,
                "current_state": self.get_current_state(),
            }

        total_reductions = len(self._reduction_metrics)
        average_time = sum(
            m["processing_time_ms"] for m in self._reduction_metrics
        ) / total_reductions

        return {
            "total_reductions": total_reductions,
            "average_processing_time_ms": round(average_time, 2),
            "max_processing_time_ms": max(
                m["processing_time_ms"] for m in self._reduction_metrics
            ),
            "total_items_processed": sum(
                m["items_processed"] for m in self._reduction_metrics
            ),
            "state_transitions": self._state_transition_count,
            "current_state": self.get_current_state(),
            "state_history": list(self.get_state_history()),
            "is_terminal": self.is_complete(),
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Health status information
        """
        try:
            # Validate FSM contract
            contract_errors = await self.validate_contract()

            # Get recent metrics
            recent_metrics = [
                m for m in self._reduction_metrics
                if time.time() - m["timestamp"] < 300  # Last 5 minutes
            ]

            avg_processing_time = (
                sum(m["processing_time_ms"] for m in recent_metrics) / len(recent_metrics)
                if recent_metrics else 0.0
            )

            return {
                "status": "healthy" if not contract_errors else "degraded",
                "fsm": {
                    "current_state": self.get_current_state(),
                    "is_terminal": self.is_complete(),
                    "contract_valid": len(contract_errors) == 0,
                    "contract_errors": contract_errors,
                },
                "performance": {
                    "average_processing_time_ms": round(avg_processing_time, 2),
                    "recent_reductions": len(recent_metrics),
                    "total_state_transitions": self._state_transition_count,
                },
                "timestamp": time.time(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time(),
            }
```

### 2. FSM State Enum (`enum_{DOMAIN}_{MICROSERVICE_NAME}_state.py`)

```python
"""FSM state enumeration for {DOMAIN} {MICROSERVICE_NAME} REDUCER operations."""

from enum import Enum


class Enum{DomainCamelCase}{MicroserviceCamelCase}State(str, Enum):
    """Enumeration of FSM states for {DOMAIN} {MICROSERVICE_NAME} reducer.

    States follow the FSM pattern where each state has defined
    entry/exit actions and allowed transitions.
    """

    # Initial state - ready to receive data
    IDLE = "idle"
    """Initial state, waiting for input data."""

    # Active processing states
    COLLECTING = "collecting"
    """Actively collecting and buffering input data."""

    VALIDATING = "validating"
    """Validating collected data before reduction."""

    REDUCING = "reducing"
    """Executing reduction operation on validated data."""

    AGGREGATING = "aggregating"
    """Aggregating reduced results from multiple sources."""

    # Terminal states
    COMPLETED = "completed"
    """Successfully completed reduction workflow."""

    FAILED = "failed"
    """Reduction failed - terminal error state."""

    CANCELLED = "cancelled"
    """Reduction was cancelled by user/system."""

    @classmethod
    def get_active_states(cls) -> list["Enum{DomainCamelCase}{MicroserviceCamelCase}State"]:
        """Get states that indicate active processing."""
        return [
            cls.COLLECTING,
            cls.VALIDATING,
            cls.REDUCING,
            cls.AGGREGATING,
        ]

    @classmethod
    def get_terminal_states(cls) -> list["Enum{DomainCamelCase}{MicroserviceCamelCase}State"]:
        """Get terminal states (no further transitions allowed)."""
        return [
            cls.COMPLETED,
            cls.FAILED,
            cls.CANCELLED,
        ]

    def is_active(self) -> bool:
        """Check if this state indicates active processing."""
        return self in self.get_active_states()

    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in self.get_terminal_states()

    def can_transition_to(self, target: "Enum{DomainCamelCase}{MicroserviceCamelCase}State") -> bool:
        """Check if transition to target state is allowed.

        Note: This is a simplified check. Full validation is done by FSM contract.
        """
        # Terminal states cannot transition
        if self.is_terminal():
            return False

        # Define allowed transitions
        allowed_transitions: dict[
            "Enum{DomainCamelCase}{MicroserviceCamelCase}State",
            list["Enum{DomainCamelCase}{MicroserviceCamelCase}State"],
        ] = {
            type(self).IDLE: [type(self).COLLECTING, type(self).CANCELLED],
            type(self).COLLECTING: [type(self).VALIDATING, type(self).FAILED, type(self).CANCELLED],
            type(self).VALIDATING: [type(self).REDUCING, type(self).FAILED, type(self).CANCELLED],
            type(self).REDUCING: [type(self).AGGREGATING, type(self).COMPLETED, type(self).FAILED],
            type(self).AGGREGATING: [type(self).COMPLETED, type(self).FAILED],
        }

        return target in allowed_transitions.get(self, [])
```

### 3. FSM Subcontract (`subcontracts/fsm_subcontract.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} REDUCER FSM Subcontract
# Defines FSM state machine for reducer state transitions

api_version: "v1.0.0"
kind: "FSMSubcontract"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-reducer-fsm"
  description: "FSM contract for {DOMAIN} {MICROSERVICE_NAME} reduction state management"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "REDUCER"

state_transitions:
  state_machine_name: "{DOMAIN}_{MICROSERVICE_NAME}_reduction_fsm"
  initial_state: idle

  states:
    - state_name: idle
      description: "Initial state, waiting for input data"
      entry_actions: []
      exit_actions: []

    - state_name: collecting
      description: "Actively collecting and buffering input data"
      entry_actions:
        - action_name: "initialize_buffer"
          action_type: "setup"
      exit_actions:
        - action_name: "finalize_buffer"
          action_type: "cleanup"

    - state_name: validating
      description: "Validating collected data before reduction"
      entry_actions:
        - action_name: "start_validation"
          action_type: "validate"
      exit_actions: []

    - state_name: reducing
      description: "Executing reduction operation on validated data"
      entry_actions:
        - action_name: "begin_reduction"
          action_type: "process"
      exit_actions:
        - action_name: "emit_reduction_metrics"
          action_type: "log"

    - state_name: aggregating
      description: "Aggregating reduced results from multiple sources"
      entry_actions:
        - action_name: "begin_aggregation"
          action_type: "aggregate"
      exit_actions: []

    - state_name: completed
      description: "Successfully completed reduction workflow"
      is_terminal: true
      entry_actions:
        - action_name: "emit_completion_event"
          action_type: "emit_event"
      exit_actions: []

    - state_name: failed
      description: "Reduction failed - terminal error state"
      is_terminal: true
      entry_actions:
        - action_name: "emit_failure_event"
          action_type: "emit_event"
        - action_name: "log_failure"
          action_type: "log"
      exit_actions: []

    - state_name: cancelled
      description: "Reduction was cancelled by user/system"
      is_terminal: true
      entry_actions:
        - action_name: "emit_cancellation_event"
          action_type: "emit_event"
      exit_actions: []

  transitions:
    # From idle state
    - from_state: idle
      to_state: collecting
      trigger: start_collection
      conditions:
        - expression: "data_sources min_length 1"
          required: true
      actions:
        - action_name: "log_collection_start"
          action_type: "log"

    - from_state: idle
      to_state: cancelled
      trigger: cancel
      conditions: []
      actions: []

    # From collecting state
    - from_state: collecting
      to_state: validating
      trigger: validate
      conditions:
        - expression: "buffer_size gt 0"
          required: true
      actions:
        - action_name: "log_validation_start"
          action_type: "log"

    - from_state: collecting
      to_state: failed
      trigger: collection_error
      conditions: []
      actions:
        - action_name: "log_collection_error"
          action_type: "log"

    - from_state: collecting
      to_state: cancelled
      trigger: cancel
      conditions: []
      actions: []

    # From validating state
    - from_state: validating
      to_state: reducing
      trigger: start_reduction
      conditions:
        - expression: "validation_passed eq true"
          required: true
      actions:
        - action_name: "log_reduction_start"
          action_type: "log"

    - from_state: validating
      to_state: failed
      trigger: validation_error
      conditions: []
      actions:
        - action_name: "log_validation_error"
          action_type: "log"

    - from_state: validating
      to_state: cancelled
      trigger: cancel
      conditions: []
      actions: []

    # From reducing state
    - from_state: reducing
      to_state: aggregating
      trigger: aggregate
      conditions:
        - expression: "partial_results min_length 1"
          required: true
      actions: []

    - from_state: reducing
      to_state: completed
      trigger: complete
      conditions:
        - expression: "reduction_complete eq true"
          required: true
      actions:
        - action_name: "emit_result"
          action_type: "emit_event"

    - from_state: reducing
      to_state: failed
      trigger: reduction_error
      conditions: []
      actions:
        - action_name: "log_reduction_error"
          action_type: "log"

    # From aggregating state
    - from_state: aggregating
      to_state: completed
      trigger: complete
      conditions:
        - expression: "aggregation_complete eq true"
          required: true
      actions:
        - action_name: "emit_aggregated_result"
          action_type: "emit_event"

    - from_state: aggregating
      to_state: failed
      trigger: aggregation_error
      conditions: []
      actions:
        - action_name: "log_aggregation_error"
          action_type: "log"

    # Wildcard error transition (any active state to failed)
    - from_state: "*"
      to_state: failed
      trigger: fatal_error
      conditions: []
      actions:
        - action_name: "log_fatal_error"
          action_type: "log"

  persistence_enabled: true
  persistence_config:
    backend: "memory"  # Can be "redis", "postgresql", etc.
    ttl_seconds: 3600
    checkpoint_interval_events: 10
```

### 4. Input Model (`model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_input.py`)

```python
"""Input model for {DOMAIN} {MICROSERVICE_NAME} REDUCER operations."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)


class Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput(BaseModel):
    """Input model for {DOMAIN} {MICROSERVICE_NAME} reduction operations.

    Strongly typed input wrapper for FSM-driven data reduction with
    support for streaming modes, conflict resolution, and FSM triggers.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    # Core data fields
    data: list[dict[str, Any]] = Field(
        description="List of data items to reduce"
    )

    reduction_type: EnumReductionType = Field(
        description="Type of reduction operation to perform"
    )

    operation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for tracking this operation"
    )

    # FSM trigger (determines state transition)
    trigger: str = Field(
        default="process",
        min_length=1,
        max_length=100,
        description="FSM trigger to execute (e.g., 'start_collection', 'validate', 'complete')"
    )

    # Conflict resolution
    conflict_resolution: EnumConflictResolution = Field(
        default=EnumConflictResolution.LAST_WINS,
        description="Strategy for resolving conflicts during reduction"
    )

    # Streaming configuration
    streaming_mode: EnumStreamingMode = Field(
        default=EnumStreamingMode.BATCH,
        description="Mode for processing data (BATCH, WINDOWED, CONTINUOUS)"
    )

    batch_size: int = Field(
        default=1000,
        gt=0,
        le=10000,
        description="Maximum number of elements to process in each batch"
    )

    window_size_ms: int = Field(
        default=5000,
        ge=1000,
        le=60000,
        description="Window duration in milliseconds for WINDOWED mode"
    )

    # Reduction-specific parameters
    group_by: list[str] | None = Field(
        default=None,
        description="Fields to group by for GROUP reduction type"
    )

    aggregation_fields: list[str] | None = Field(
        default=None,
        description="Fields to aggregate for AGGREGATE reduction type"
    )

    sort_by: str | None = Field(
        default=None,
        description="Field to sort by for SORT reduction type"
    )

    sort_descending: bool = Field(
        default=False,
        description="Sort in descending order"
    )

    # Context and metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context metadata and FSM context data"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this input was created"
    )

    @field_validator('data')
    @classmethod
    def validate_data_not_empty(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate that data list is not empty."""
        if not v:
            raise ValueError("Data list cannot be empty for reduction")
        return v

    @field_validator('group_by')
    @classmethod
    def validate_group_by(cls, v: list[str] | None, info) -> list[str] | None:
        """Validate group_by is provided for GROUP reduction."""
        reduction_type = info.data.get('reduction_type')
        if reduction_type == EnumReductionType.GROUP and not v:
            raise ValueError("group_by must be specified for GROUP reduction")
        return v

    @field_validator('aggregation_fields')
    @classmethod
    def validate_aggregation_fields(cls, v: list[str] | None, info) -> list[str] | None:
        """Validate aggregation_fields is provided for AGGREGATE reduction."""
        reduction_type = info.data.get('reduction_type')
        if reduction_type == EnumReductionType.AGGREGATE and not v:
            raise ValueError("aggregation_fields must be specified for AGGREGATE reduction")
        return v
```

### 5. Output Model (`model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_output.py`)

```python
"""Output model for {DOMAIN} {MICROSERVICE_NAME} REDUCER operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.reducer.model_intent import ModelIntent


class Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(BaseModel):
    """Output model for {DOMAIN} {MICROSERVICE_NAME} reduction operations.

    Strongly typed output wrapper with reduction statistics,
    FSM state information, and Intent emission list.

    Pure FSM Pattern:
        result: The new state after reduction
        intents: Side effects to be executed by Effect node
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    # Core result fields
    result: dict[str, Any] | list[dict[str, Any]] = Field(
        description="Reduced result data"
    )

    operation_id: UUID = Field(
        description="Operation ID from input for correlation"
    )

    reduction_type: EnumReductionType = Field(
        description="Type of reduction that was performed"
    )

    # Processing statistics
    processing_time_ms: float = Field(
        ge=0,
        description="Total reduction processing time in milliseconds"
    )

    items_processed: int = Field(
        ge=0,
        description="Number of input items processed"
    )

    items_output: int = Field(
        ge=0,
        description="Number of items in output result"
    )

    conflicts_resolved: int = Field(
        default=0,
        ge=0,
        description="Number of conflicts resolved during reduction"
    )

    # Streaming information
    streaming_mode: EnumStreamingMode = Field(
        default=EnumStreamingMode.BATCH,
        description="Mode used for processing"
    )

    batches_processed: int = Field(
        default=1,
        ge=1,
        description="Number of batches processed"
    )

    # FSM state information
    fsm_state: str = Field(
        description="Current FSM state after transition"
    )

    fsm_previous_state: str | None = Field(
        default=None,
        description="Previous FSM state before transition"
    )

    fsm_transition: str | None = Field(
        default=None,
        description="Name of FSM transition that was executed"
    )

    fsm_is_terminal: bool = Field(
        default=False,
        description="Whether current FSM state is terminal"
    )

    # Intent emission for pure FSM pattern
    intents: tuple[ModelIntent, ...] = Field(
        default=(),
        description="Side effect intents emitted during reduction (for Effect node)"
    )

    # Metadata and timestamp
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional result metadata"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this output was created"
    )
```

### 6. Input Subcontract (`subcontracts/input_subcontract.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} REDUCER Input Subcontract
# Defines the expected input structure for reduction operations

api_version: "v1.0.0"
kind: "InputSubcontract"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-reducer-input"
  description: "Input contract for {DOMAIN} {MICROSERVICE_NAME} reduction operations"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "REDUCER"

schema:
  type: "object"
  required:
    - "data"
    - "reduction_type"

  properties:
    data:
      type: "array"
      minItems: 1
      description: "List of data items to reduce"
      items:
        type: "object"
        additionalProperties: true

    reduction_type:
      type: "string"
      enum:
        - "fold"
        - "accumulate"
        - "merge"
        - "aggregate"
        - "normalize"
        - "deduplicate"
        - "sort"
        - "filter"
        - "group"
        - "transform"
      description: "Type of reduction operation to perform"

    operation_id:
      type: "string"
      format: "uuid"
      description: "Unique identifier for tracking this operation"

    trigger:
      type: "string"
      minLength: 1
      maxLength: 100
      default: "process"
      description: "FSM trigger to execute"

    conflict_resolution:
      type: "string"
      enum:
        - "first_wins"
        - "last_wins"
        - "merge"
        - "error"
        - "custom"
      default: "last_wins"
      description: "Strategy for resolving conflicts during reduction"

    streaming_mode:
      type: "string"
      enum:
        - "batch"
        - "incremental"
        - "windowed"
        - "real_time"
      default: "batch"
      description: "Mode for processing data"

    batch_size:
      type: "integer"
      minimum: 1
      maximum: 10000
      default: 1000
      description: "Maximum batch size"

    window_size_ms:
      type: "integer"
      minimum: 1000
      maximum: 60000
      default: 5000
      description: "Window duration in milliseconds"

    group_by:
      type: ["array", "null"]
      items:
        type: "string"
      description: "Fields to group by for GROUP reduction"

    aggregation_fields:
      type: ["array", "null"]
      items:
        type: "string"
      description: "Fields to aggregate for AGGREGATE reduction"

    sort_by:
      type: ["string", "null"]
      description: "Field to sort by"

    sort_descending:
      type: "boolean"
      default: false
      description: "Sort in descending order"

    metadata:
      type: "object"
      additionalProperties: true
      description: "Additional context metadata and FSM context"

    timestamp:
      type: "string"
      format: "date-time"
      description: "When input was created"

validation_rules:
  - name: "group_reduction_requires_group_by"
    description: "GROUP reduction type requires group_by field"
    rule: |
      if reduction_type == "group":
        assert group_by is not None
        assert len(group_by) > 0

  - name: "aggregate_requires_fields"
    description: "AGGREGATE reduction type requires aggregation_fields"
    rule: |
      if reduction_type == "aggregate":
        assert aggregation_fields is not None
        assert len(aggregation_fields) > 0

  - name: "sort_requires_sort_by"
    description: "SORT reduction type requires sort_by field"
    rule: |
      if reduction_type == "sort":
        assert sort_by is not None

examples:
  - name: "group_reduction"
    description: "Group reduction by user"
    data:
      data:
        - {"user": "alice", "score": 100}
        - {"user": "bob", "score": 85}
        - {"user": "alice", "score": 95}
      reduction_type: "group"
      trigger: "start_collection"
      group_by: ["user"]
      conflict_resolution: "merge"
      metadata:
        source: "game_scores"

  - name: "aggregate_reduction"
    description: "Aggregate metrics"
    data:
      data:
        - {"metric": "cpu", "value": 45.2}
        - {"metric": "cpu", "value": 52.1}
        - {"metric": "memory", "value": 78.5}
      reduction_type: "aggregate"
      trigger: "start_collection"
      aggregation_fields: ["value"]
      group_by: ["metric"]
```

### 7. Output Subcontract (`subcontracts/output_subcontract.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} REDUCER Output Subcontract
# Defines the expected output structure for reduction operations

api_version: "v1.0.0"
kind: "OutputSubcontract"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-reducer-output"
  description: "Output contract for {DOMAIN} {MICROSERVICE_NAME} reduction operations"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "REDUCER"

schema:
  type: "object"
  required:
    - "result"
    - "operation_id"
    - "reduction_type"
    - "processing_time_ms"
    - "items_processed"
    - "fsm_state"

  properties:
    result:
      description: "Reduced result data (object or array)"
      oneOf:
        - type: "object"
        - type: "array"

    operation_id:
      type: "string"
      format: "uuid"
      description: "Operation ID from input for correlation"

    reduction_type:
      type: "string"
      enum:
        - "fold"
        - "accumulate"
        - "merge"
        - "aggregate"
        - "normalize"
        - "deduplicate"
        - "sort"
        - "filter"
        - "group"
        - "transform"
      description: "Type of reduction performed"

    processing_time_ms:
      type: "number"
      minimum: 0
      description: "Processing time in milliseconds"

    items_processed:
      type: "integer"
      minimum: 0
      description: "Number of input items processed"

    items_output:
      type: "integer"
      minimum: 0
      description: "Number of items in output"

    conflicts_resolved:
      type: "integer"
      minimum: 0
      default: 0
      description: "Number of conflicts resolved"

    streaming_mode:
      type: "string"
      enum:
        - "batch"
        - "incremental"
        - "windowed"
        - "real_time"
      description: "Processing mode used"

    batches_processed:
      type: "integer"
      minimum: 1
      default: 1
      description: "Number of batches processed"

    fsm_state:
      type: "string"
      description: "Current FSM state after transition"

    fsm_previous_state:
      type: ["string", "null"]
      description: "Previous FSM state"

    fsm_transition:
      type: ["string", "null"]
      description: "FSM transition executed"

    fsm_is_terminal:
      type: "boolean"
      default: false
      description: "Whether FSM reached terminal state"

    intents:
      type: "array"
      description: "Side effect intents for Effect node"
      items:
        type: "object"
        required:
          - "intent_type"
          - "target"
        properties:
          intent_id:
            type: "string"
            format: "uuid"
          intent_type:
            type: "string"
          target:
            type: "string"
          payload:
            type: "object"
          priority:
            type: "integer"
            minimum: 1
            maximum: 10

    metadata:
      type: "object"
      description: "Additional result metadata"

    timestamp:
      type: "string"
      format: "date-time"
      description: "When output was created"

validation_rules:
  - name: "terminal_state_intents"
    description: "Terminal states should emit completion/failure intents"
    rule: |
      if fsm_is_terminal == true:
        assert len(intents) > 0

  - name: "processing_consistency"
    description: "Output items should not exceed input items for most reductions"
    rule: |
      # For most reductions, output <= input
      # GROUP and TRANSFORM may have different output sizes
      if reduction_type not in ["group", "transform"]:
        assert items_output <= items_processed

examples:
  - name: "successful_group_reduction"
    description: "Successful group reduction result"
    data:
      result:
        alice:
          scores: [100, 95]
          total: 195
          count: 2
        bob:
          scores: [85]
          total: 85
          count: 1
      operation_id: "550e8400-e29b-41d4-a716-446655440000"
      reduction_type: "group"
      processing_time_ms: 12.5
      items_processed: 3
      items_output: 2
      conflicts_resolved: 1
      streaming_mode: "batch"
      batches_processed: 1
      fsm_state: "completed"
      fsm_previous_state: "reducing"
      fsm_transition: "complete"
      fsm_is_terminal: true
      intents:
        - intent_id: "660e8400-e29b-41d4-a716-446655440001"
          intent_type: "emit_event"
          target: "reduction.completed"
          payload:
            operation_id: "550e8400-e29b-41d4-a716-446655440000"
            groups_created: 2
          priority: 5
      metadata:
        source: "game_scores"
        reduction_algorithm: "group_by_key"
```

### 8. Manifest (`manifest.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} REDUCER Node Manifest
# Defines metadata, dependencies, and deployment specifications

api_version: "v1.0.0"
kind: "NodeManifest"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-reducer"
  description: "REDUCER node for {DOMAIN} {MICROSERVICE_NAME} FSM-driven state management"
  version: "1.0.0"
  domain: "{DOMAIN}"
  microservice_name: "{MICROSERVICE_NAME}"
  node_type: "REDUCER"
  created_at: "2024-01-15T10:00:00Z"
  updated_at: "2024-01-15T10:00:00Z"
  maintainers:
    - "team@{DOMAIN}.com"
  tags:
    - "reducer"
    - "fsm"
    - "state-management"
    - "aggregation"
    - "{DOMAIN}"
    - "onex-v4"

specification:
  # Node classification
  node_class: "REDUCER"
  processing_type: "synchronous"
  stateful: true  # FSM maintains state

  # FSM characteristics
  fsm:
    enabled: true
    persistence: true
    initial_state: "idle"
    terminal_states:
      - "completed"
      - "failed"
      - "cancelled"

  # Performance characteristics
  performance:
    expected_latency_ms: 50
    max_latency_ms: 1000
    throughput_ops_per_second: 5000
    memory_requirement_mb: 128
    cpu_requirement_cores: 0.5
    scaling_factor: "horizontal"

  # Operational requirements
  reliability:
    availability_target: "99.9%"
    error_rate_target: "0.1%"
    recovery_time_target_seconds: 10
    fsm_state_recovery: true
    retry_policy: "exponential_backoff"

  # Resource management
  resources:
    memory:
      min_mb: 64
      max_mb: 512
      typical_mb: 128
    cpu:
      min_cores: 0.25
      max_cores: 2.0
      typical_cores: 0.5
    storage:
      fsm_state_mb: 10
      cache_space_mb: 50

  # Security requirements
  security:
    input_validation: "strict"
    output_sanitization: "enabled"
    audit_logging: "enabled"
    fsm_state_encryption: "optional"

# Dependency specifications
dependencies:
  runtime:
    python: ">=3.12,<4.0"
    pydantic: ">=2.0.0"
    asyncio: "builtin"

  internal:
    omnibase_core:
      version: ">=0.4.0"
      components:
        - "nodes.node_reducer"
        - "models.reducer.model_reducer_input"
        - "models.reducer.model_reducer_output"
        - "models.reducer.model_intent"
        - "models.errors.model_onex_error"
        - "enums.enum_reducer_types"

  external: {}

  optional:
    redis: ">=4.0.0"  # For FSM state persistence
    prometheus_client: ">=0.16.0"  # For metrics

# Interface contracts
contracts:
  fsm:
    contract_file: "subcontracts/fsm_subcontract.yaml"
    validation_level: "strict"

  input:
    contract_file: "subcontracts/input_subcontract.yaml"
    validation_level: "strict"

  output:
    contract_file: "subcontracts/output_subcontract.yaml"
    validation_level: "strict"

  config:
    contract_file: "subcontracts/config_subcontract.yaml"
    validation_level: "strict"

# API specification
api:
  endpoints:
    reduce:
      path: "/api/v1/reduce"
      method: "POST"
      input_model: "Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput"
      output_model: "Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput"
      timeout_ms: 10000
      rate_limit: "5000/minute"

    state:
      path: "/api/v1/reduce/state"
      method: "GET"
      description: "Get current FSM state"
      timeout_ms: 1000
      rate_limit: "100/minute"

    health:
      path: "/health"
      method: "GET"
      timeout_ms: 5000
      rate_limit: "100/minute"

# Testing requirements
testing:
  unit_tests:
    coverage_minimum: 90
    test_files:
      - "test_node.py"
      - "test_fsm_transitions.py"
      - "test_contracts.py"
      - "test_intents.py"

  integration_tests:
    required: true
    test_scenarios:
      - "basic_reduction"
      - "fsm_state_transitions"
      - "intent_emission"
      - "error_handling"
      - "conflict_resolution"

  fsm_tests:
    required: true
    test_scenarios:
      - "all_valid_transitions"
      - "invalid_transition_rejection"
      - "terminal_state_behavior"
      - "state_persistence"
      - "recovery_from_failure"

# Deployment configuration
deployment:
  container:
    base_image: "python:3.12-slim"
    entrypoint: "python -m {REPOSITORY_NAME}.nodes.node_{DOMAIN}_{MICROSERVICE_NAME}_reducer.v1_0_0.node"
    healthcheck:
      endpoint: "/health"
      interval_seconds: 30
      timeout_seconds: 5
      retries: 3

  scaling:
    min_replicas: 1
    max_replicas: 10
    target_cpu_utilization: 60
    target_memory_utilization: 70

  environment_variables:
    required:
      - "ONEX_ENVIRONMENT"
      - "NODE_CONFIG_PATH"
    optional:
      - "REDIS_URL"
      - "FSM_PERSISTENCE_BACKEND"
      - "METRICS_ENDPOINT"
      - "LOG_LEVEL"

# Monitoring and observability
monitoring:
  metrics:
    - name: "reduction_duration_seconds"
      type: "histogram"
      description: "Time spent on reduction operations"
      labels: ["reduction_type", "streaming_mode"]

    - name: "fsm_transitions_total"
      type: "counter"
      description: "Total FSM state transitions"
      labels: ["from_state", "to_state", "trigger"]

    - name: "intents_emitted_total"
      type: "counter"
      description: "Total intents emitted"
      labels: ["intent_type", "target"]

    - name: "conflicts_resolved_total"
      type: "counter"
      description: "Total conflicts resolved"
      labels: ["conflict_resolution"]

    - name: "fsm_current_state"
      type: "gauge"
      description: "Current FSM state (encoded as integer)"

  logging:
    level: "INFO"
    format: "structured_json"
    fields:
      - "timestamp"
      - "level"
      - "correlation_id"
      - "operation_id"
      - "fsm_state"
      - "reduction_type"
      - "items_processed"

  alerts:
    - name: "high_error_rate"
      condition: "error_rate > 5%"
      severity: "warning"
      notification: "team_channel"

    - name: "fsm_stuck_in_state"
      condition: "fsm_state_duration > 5m"
      severity: "warning"
      notification: "team_channel"

    - name: "high_conflict_rate"
      condition: "conflict_rate > 20%"
      severity: "info"
      notification: "team_channel"

# Documentation
documentation:
  readme: "README.md"
  api_docs: "docs/api.md"
  fsm_docs: "docs/fsm.md"
  deployment_guide: "docs/deployment.md"
  troubleshooting: "docs/troubleshooting.md"
  examples: "examples/"

# Lifecycle management
lifecycle:
  deprecation_policy: "6_months_notice"
  upgrade_path: "rolling_deployment"
  backward_compatibility: "1_major_version"
  support_window: "24_months"

# Integration points
integrations:
  upstream_nodes:
    - node_type: "COMPUTE"
      interface: "onex_standard"
      data_flow: "request_response"
    - node_type: "ORCHESTRATOR"
      interface: "onex_standard"
      data_flow: "request_response"

  downstream_nodes:
    - node_type: "EFFECT"
      interface: "intent_based"
      data_flow: "intent_emission"
      description: "Effect nodes consume and execute emitted intents"

  external_services:
    - service_type: "state_store"
      protocol: "redis"
      optional: true
      description: "FSM state persistence"
    - service_type: "metrics"
      protocol: "prometheus"
      optional: true
```

## Usage Instructions

### Template Customization

Replace the following placeholders throughout all files:

- `{REPOSITORY_NAME}`: Target repository name (e.g., "omniplan")
- `{DOMAIN}`: Business domain (e.g., "rsd", "finance", "analytics")
- `{MICROSERVICE_NAME}`: Specific microservice name (e.g., "metrics_aggregator")
- `{DomainCamelCase}`: Domain in CamelCase (e.g., "RSD", "Finance")
- `{MicroserviceCamelCase}`: Microservice in CamelCase (e.g., "MetricsAggregator")

### Key Architectural Features

1. **Pure FSM Pattern**: `delta(state, action) -> (new_state, intents[])`
2. **Intent-Based Side Effects**: No direct I/O - all effects emitted as `ModelIntent`
3. **YAML-Driven Configuration**: Zero custom Python for state transitions
4. **Type-Safe I/O**: Full Pydantic validation with generic typing
5. **State Persistence**: Optional checkpoint-based recovery
6. **Conflict Resolution**: Configurable strategies for data conflicts
7. **Streaming Support**: BATCH, WINDOWED, and CONTINUOUS modes

### FSM Design Principles

1. **States are immutable** - Transitions produce new state, never modify existing
2. **Intents describe effects** - Reducer declares "what should happen", Effect executes
3. **Conditions guard transitions** - Explicit conditions prevent invalid state changes
4. **Entry/Exit actions are logged** - All state changes are observable
5. **Terminal states are final** - No transitions allowed from terminal states

### Implementation Checklist

- [ ] Replace all template placeholders
- [ ] Define all FSM states in enum and YAML contract
- [ ] Define all valid transitions in FSM subcontract
- [ ] Implement entry/exit actions for each state
- [ ] Define intent types for side effects
- [ ] Configure conflict resolution strategy
- [ ] Set up state persistence if needed
- [ ] Write comprehensive FSM transition tests
- [ ] Update manifest with accurate characteristics
- [ ] Validate contract compliance
- [ ] Set up monitoring and alerting

### Example: Creating a Metrics Aggregator Reducer

```python
from omnibase_core.nodes import (
    NodeReducer,
    ModelReducerInput,
    ModelReducerOutput,
    EnumReductionType,
)
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeMetricsAggregatorReducer(NodeReducer[dict, dict]):
    """Reducer for aggregating system metrics.

    FSM States:
        idle -> collecting -> validating -> aggregating -> completed

    Intents Emitted:
        - emit_event: Publish aggregated metrics
        - write: Persist metrics to storage
        - notify: Alert on threshold breaches
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

    async def process(
        self,
        input_data: ModelReducerInput[dict],
    ) -> ModelReducerOutput[dict]:
        """Process metrics with FSM-driven aggregation."""
        # Base class handles FSM transitions
        result = await super().process(input_data)

        # Add domain-specific intents
        if result.metadata.get("fsm_state") == "completed":
            # Emit notification if aggregated value exceeds threshold
            aggregated_value = result.result.get("total", 0)
            if aggregated_value > 1000:
                # Intent for notification - Effect node will execute
                notify_intent = ModelIntent(
                    intent_type="notify",
                    target="alerts.metrics_threshold",
                    payload={
                        "metric": "aggregated_total",
                        "value": aggregated_value,
                        "threshold": 1000,
                    },
                    priority=8,
                )
                # Add intent to result (immutable, so create new tuple)
                result = result.model_copy(
                    update={"intents": result.intents + (notify_intent,)}
                )

        return result


# Usage
container = ModelONEXContainer(...)
node = NodeMetricsAggregatorReducer(container)

# Initialize FSM
node.initialize_fsm_state(node.contract.state_machine, context={})

# Process input
input_data = ModelReducerInput(
    data=[
        {"metric": "cpu", "value": 45.2},
        {"metric": "cpu", "value": 52.1},
        {"metric": "memory", "value": 78.5},
    ],
    reduction_type=EnumReductionType.AGGREGATE,
    metadata={"trigger": "start_collection"},
)

result = await node.process(input_data)
print(f"FSM State: {result.metadata['fsm_state']}")
print(f"Intents: {len(result.intents)}")
```

This template ensures all REDUCER nodes follow the unified ONEX architecture while maintaining FSM-driven state management with pure intent-based side effect emission.
