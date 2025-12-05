# Declarative Implementation Plan - ONEX Architecture

> **Version**: 2.0.0
> **Date**: 2025-12-05
> **Status**: ✅ **ALL PHASES COMPLETE** - Declarative nodes are now PRIMARY implementations
> **Correlation ID**: `impl-plan-declarative-onex-2025-11-16`

> **UPDATE (v0.4.0)**: `NodeReducer` and `NodeOrchestrator` are now the **PRIMARY declarative implementations**. The "Declarative" suffix has been removed because these ARE the standard. Legacy imperative implementations have been moved to `nodes/legacy/`.

---

## 🎯 Current Implementation Status (2025-11-16)

| Phase | Status | Completion | Commit | Files |
|-------|--------|-----------|--------|-------|
| **Phase 1: FSM Execution** | ✅ **COMPLETE** | 100% | `7bbb4a8` | fsm_executor.py, mixin_fsm_execution.py, tests |
| **Phase 2: Workflow Execution** | ✅ **COMPLETE** | 100% | `58a3972` | workflow_executor.py, mixin_workflow_execution.py, tests |
| **Phase 3: Declarative Nodes** | ✅ **COMPLETE** | 100% | `588529f` | `node_reducer.py`, `node_orchestrator.py` (now primary) |
| **Phase 4: Migration and Examples** | ✅ **COMPLETE** | 100% | `5cac29c` | Example YAMLs, migration guide |
| **Phase 5: Naming Cleanup** | ✅ **COMPLETE** | 100% | v0.4.0 | Removed "Declarative" suffix, moved legacy to `nodes/legacy/` |

**Total Implementation**: 5,000+ lines of production code, 2,300+ lines of tests, 900+ lines of documentation.

**Developer Impact**: Reducer/orchestrator nodes can now be created with **99% less code** (1 line vs 200-300 lines).

---

## Executive Summary

This document provides a complete implementation plan for closing the gap between ONEX's **complete YAML contract infrastructure** and the **runtime execution** needed to make orchestrator/reducer nodes truly declarative.

**Key Principle**: ONEX does NOT use "services" - we use **mixins**, **utility modules**, and **node-based architecture**.

---

## 🎯 Current Implementation Status (2025-11-16)

| Phase | Status | Completion | PR | Description |
|-------|--------|-----------|-----|-------------|
| **Phase 1: FSM Execution** | ✅ **Complete** | 100% | #83 | FSM execution infrastructure (utils, mixins, tests) |
| **Phase 2: Workflow Execution** | 🚧 Planned | 0% | TBD | Workflow execution infrastructure |
| **Phase 3: Examples & Patterns** | ⏳ Planned | 0% | TBD | Example contracts and usage patterns |
| **Phase 4: Migration and Examples** | ⏳ Planned | 0% | TBD | Examples, docs, migration guides |

**✅ What's Available Now** (Phase 1):
- `src/omnibase_core/utils/fsm_executor.py` - FSM execution utilities (548 lines)
- `src/omnibase_core/mixins/mixin_fsm_execution.py` - FSM execution mixin (237 lines)
- Comprehensive test coverage (18 test cases, 610+ test lines)
- Mixin metadata documentation (589 lines)

**🚧 What's Coming Next**:
- Phase 2: Workflow execution utilities and mixins
- Phase 3: Example YAML contracts showing mixin composition patterns
- Phase 4: Migration guides and best practices documentation

---

## Table of Contents

1. [Architecture Alignment](#architecture-alignment)
2. [Implementation Components](#implementation-components)
3. [Phase 1: FSM Execution Infrastructure](#phase-1-fsm-execution-infrastructure)
4. [Phase 2: Workflow Execution Infrastructure](#phase-2-workflow-execution-infrastructure)
5. [Phase 3: Example Contracts & Usage Patterns](#phase-3-example-contracts--usage-patterns)
6. [Phase 4: Migration and Examples](#phase-4-migration-and-examples)
7. [Testing Strategy](#testing-strategy)
8. [Success Metrics](#success-metrics)

---

## Architecture Alignment

### ✅ ONEX Patterns We Use

| Pattern | Usage | Example |
|---------|-------|---------|
| **Mixins** | Cross-cutting concerns | `MixinRetry`, `MixinCaching`, `MixinHealthCheck` |
| **Utility Modules** | Pure functions, algorithms | `utils/validation.py`, `utils/serialization.py` |
| **Protocol-Driven DI** | Interface-based injection | `container.get_service("ProtocolLogger")` |
| **Base Classes** | Shared functionality | `NodeCoreBase` with `process()` method |
| **Pydantic Models** | Data validation | All contracts, inputs, outputs |
| **Four-Node Types** | EFFECT, COMPUTE, REDUCER, ORCHESTRATOR | Core architecture |

### ❌ Patterns We DON'T Use

- ❌ "Service" classes (ServiceFSMExecutor, ServiceWorkflowExecutor)
- ❌ Separate runtime layers
- ❌ External orchestration engines

### ✅ Correct Pattern: Execution via Mixins + Utilities

```
# ✅ CORRECT - Mixin-based execution
class MixinFSMExecution:
    """Mixin providing FSM execution from YAML contracts."""

    async def execute_fsm_transition(
        self,
        fsm_contract: ModelFSMSubcontract,
        current_state: str,
        trigger: str,
        context: dict[str, Any]
    ) -> FSMTransitionResult:
        """Execute FSM transition declaratively."""
        # Delegate to utility module for pure logic
        from omnibase_core.utils.fsm_executor import execute_transition
        return await execute_transition(fsm_contract, current_state, trigger, context)

# ✅ CORRECT - Utility module with pure functions
# src/omnibase_core/utils/fsm_executor.py
async def execute_transition(
    fsm: ModelFSMSubcontract,
    current_state: str,
    trigger: str,
    context: dict[str, Any]
) -> FSMTransitionResult:
    """Pure function: execute FSM transition."""
    # Validation, execution logic here
    pass
```

---

## Implementation Components

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   YAML Contracts (✅ Complete)               │
│  ModelFSMSubcontract, ModelWorkflowCoordinationSubcontract  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          Execution Mixins (Phase 1 ✅, Phase 2 🚧)          │
│      MixinFSMExecution, MixinWorkflowExecution              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Utility Modules (Phase 1 ✅, Phase 2 🚧)            │
│   utils/fsm_executor.py, utils/workflow_executor.py         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│        Node Composition via Mixins (No special base!)       │
│   class MyNode(NodeCoreBase, MixinFSMExecution): ...        │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: FSM Execution Infrastructure

**Timeline**: Sprint 1 (Week 1-2)
**Goal**: Enable YAML-driven FSM execution for reducer nodes

### 1.1 FSM Utility Module

**File**: `src/omnibase_core/utils/fsm_executor.py`

```
"""
FSM execution utilities for declarative state machines.

Pure functions for executing FSM transitions from ModelFSMSubcontract.
No side effects - returns results and intents.
"""

from typing import Any
from uuid import UUID, uuid4
from datetime import datetime

from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.model_intent import ModelIntent
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class FSMTransitionResult:
    """Result of FSM transition execution."""

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


class FSMState:
    """Current FSM state snapshot."""

    def __init__(
        self,
        current_state: str,
        context: dict[str, Any],
        history: list[str] | None = None,
    ):
        self.current_state = current_state
        self.context = context
        self.history = history or []


async def execute_transition(
    fsm: ModelFSMSubcontract,
    current_state: str,
    trigger: str,
    context: dict[str, Any],
) -> FSMTransitionResult:
    """
    Execute FSM transition declaratively from YAML contract.

    Pure function: (fsm_contract, state, trigger, context) → (result, intents)

    Args:
        fsm: FSM subcontract definition (from YAML)
        current_state: Current state name
        trigger: Trigger event name
        context: Execution context data

    Returns:
        FSMTransitionResult with new state and intents for side effects

    Raises:
        ModelOnexError: If transition is invalid or execution fails
    """
    intents: list[ModelIntent] = []

    # 1. Validate current state exists
    state_def = _get_state_definition(fsm, current_state)
    if not state_def:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid current state: {current_state}",
            context={"fsm": fsm.state_machine_name, "state": current_state},
        )

    # 2. Find valid transition
    transition = _find_transition(fsm, current_state, trigger)
    if not transition:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"No transition for trigger '{trigger}' from state '{current_state}'",
            context={
                "fsm": fsm.state_machine_name,
                "state": current_state,
                "trigger": trigger,
            },
        )

    # 3. Evaluate transition conditions
    conditions_met = await _evaluate_conditions(transition, context)
    if not conditions_met:
        # Create intent to log condition failure
        intents.append(
            ModelIntent(
                intent_type="log_event",
                target="logging_service",
                payload={
                    "level": "WARNING",
                    "message": f"FSM transition conditions not met: {transition.transition_name}",
                    "context": {
                        "fsm": fsm.state_machine_name,
                        "from_state": current_state,
                        "to_state": transition.to_state,
                    },
                },
                priority=3,
            )
        )

        return FSMTransitionResult(
            success=False,
            new_state=current_state,  # Stay in current state
            old_state=current_state,
            transition_name=transition.transition_name,
            intents=intents,
            error="Transition conditions not met",
        )

    # 4. Execute exit actions from current state
    exit_intents = await _execute_state_actions(
        fsm, state_def, "exit", context
    )
    intents.extend(exit_intents)

    # 5. Execute transition actions
    transition_intents = await _execute_transition_actions(transition, context)
    intents.extend(transition_intents)

    # 6. Get target state definition
    target_state_def = _get_state_definition(fsm, transition.to_state)
    if not target_state_def:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid target state: {transition.to_state}",
            context={"fsm": fsm.state_machine_name, "state": transition.to_state},
        )

    # 7. Execute entry actions for new state
    entry_intents = await _execute_state_actions(
        fsm, target_state_def, "entry", context
    )
    intents.extend(entry_intents)

    # 8. Create persistence intent if enabled
    if fsm.persistence_enabled:
        intents.append(
            ModelIntent(
                intent_type="persist_state",
                target="state_persistence",
                payload={
                    "fsm_name": fsm.state_machine_name,
                    "state": transition.to_state,
                    "previous_state": current_state,
                    "context": context,
                    "timestamp": datetime.now().isoformat(),
                },
                priority=1,  # High priority for persistence
            )
        )

    # 9. Create monitoring intent
    intents.append(
        ModelIntent(
            intent_type="record_metric",
            target="metrics_service",
            payload={
                "metric_name": "fsm_transition",
                "tags": {
                    "fsm": fsm.state_machine_name,
                    "from_state": current_state,
                    "to_state": transition.to_state,
                    "trigger": trigger,
                },
                "value": 1,
            },
            priority=3,
        )
    )

    return FSMTransitionResult(
        success=True,
        new_state=transition.to_state,
        old_state=current_state,
        transition_name=transition.transition_name,
        intents=intents,
        metadata={
            "conditions_evaluated": len(transition.conditions),
            "actions_executed": len(transition.actions),
        },
    )


async def validate_fsm_contract(fsm: ModelFSMSubcontract) -> list[str]:
    """
    Validate FSM contract for correctness.

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[str] = []

    # Check initial state exists
    if not _get_state_definition(fsm, fsm.initial_state):
        errors.append(f"Initial state not defined: {fsm.initial_state}")

    # Check all transitions reference valid states
    for transition in fsm.transitions:
        if not _get_state_definition(fsm, transition.from_state):
            errors.append(
                f"Transition '{transition.transition_name}' references invalid from_state: {transition.from_state}"
            )
        if not _get_state_definition(fsm, transition.to_state):
            errors.append(
                f"Transition '{transition.transition_name}' references invalid to_state: {transition.to_state}"
            )

    # Check for unreachable states
    reachable_states = _find_reachable_states(fsm)
    all_states = {state.state_name for state in fsm.states}
    unreachable = all_states - reachable_states
    if unreachable:
        errors.append(f"Unreachable states: {', '.join(unreachable)}")

    # Check terminal states have no outgoing transitions
    terminal_states = {state.state_name for state in fsm.states if state.is_terminal}
    for transition in fsm.transitions:
        if transition.from_state in terminal_states:
            errors.append(
                f"Terminal state '{transition.from_state}' has outgoing transition: {transition.transition_name}"
            )

    return errors


# Private helper functions

def _get_state_definition(
    fsm: ModelFSMSubcontract, state_name: str
) -> ModelFSMStateDefinition | None:
    """Find state definition by name."""
    for state in fsm.states:
        if state.state_name == state_name:
            return state
    return None


def _find_transition(
    fsm: ModelFSMSubcontract, from_state: str, trigger: str
) -> ModelFSMStateTransition | None:
    """Find transition matching from_state and trigger."""
    for transition in fsm.transitions:
        if transition.from_state == from_state and transition.trigger == trigger:
            return transition
        # Support wildcard transitions
        if transition.from_state == "*" and transition.trigger == trigger:
            return transition
    return None


async def _evaluate_conditions(
    transition: ModelFSMStateTransition,
    context: dict[str, Any],
) -> bool:
    """Evaluate all transition conditions.

    NOTE: Actual implementation in fsm_executor.py uses STRING-BASED comparison
    for 'equals' and 'not_equals' operators (both values cast to str).
    See fsm_executor.py:_evaluate_single_condition() for complete documentation
    on type coercion behavior.
    """
    if not transition.conditions:
        return True

    for condition in transition.conditions:
        # Evaluate condition based on type
        if condition.condition_type == "field_check":
            field_value = context.get(condition.field)

            if condition.operator == "equals":
                # ACTUAL IMPLEMENTATION: str(field_value) == str(condition.value)
                # This pseudocode simplified for planning purposes
                if field_value != condition.value:
                    return False
            elif condition.operator == "not_equals":
                # ACTUAL IMPLEMENTATION: str(field_value) != str(condition.value)
                # This pseudocode simplified for planning purposes
                if field_value == condition.value:
                    return False
            elif condition.operator == "min_length":
                if not field_value or len(field_value) < int(condition.value):
                    return False
            elif condition.operator == "max_length":
                if field_value and len(field_value) > int(condition.value):
                    return False
            elif condition.operator == "greater_than":
                if not field_value or field_value <= condition.value:
                    return False
            elif condition.operator == "less_than":
                if not field_value or field_value >= condition.value:
                    return False

    return True


async def _execute_state_actions(
    fsm: ModelFSMSubcontract,
    state: ModelFSMStateDefinition,
    action_type: str,  # "entry" or "exit"
    context: dict[str, Any],
) -> list[ModelIntent]:
    """Execute state entry/exit actions, returning intents."""
    intents: list[ModelIntent] = []

    actions = state.entry_actions if action_type == "entry" else state.exit_actions

    for action_name in actions:
        # Create intent for each action
        intents.append(
            ModelIntent(
                intent_type=f"fsm_state_action",
                target="action_executor",
                payload={
                    "action_name": action_name,
                    "action_type": action_type,
                    "state": state.state_name,
                    "fsm": fsm.state_machine_name,
                    "context": context,
                },
                priority=2,
            )
        )

    return intents


async def _execute_transition_actions(
    transition: ModelFSMStateTransition,
    context: dict[str, Any],
) -> list[ModelIntent]:
    """Execute transition actions, returning intents."""
    intents: list[ModelIntent] = []

    for action in transition.actions:
        intents.append(
            ModelIntent(
                intent_type="fsm_transition_action",
                target="action_executor",
                payload={
                    "action_name": action.action_name,
                    "action_type": action.action_type,
                    "transition": transition.transition_name,
                    "context": context,
                },
                priority=2,
            )
        )

    return intents


def _find_reachable_states(fsm: ModelFSMSubcontract) -> set[str]:
    """Find all states reachable from initial state."""
    reachable = {fsm.initial_state}
    queue = [fsm.initial_state]

    while queue:
        current = queue.pop(0)

        for transition in fsm.transitions:
            if transition.from_state == current and transition.to_state not in reachable:
                reachable.add(transition.to_state)
                queue.append(transition.to_state)

    return reachable
```

### 1.2 FSM Execution Mixin

**File**: `src/omnibase_core/mixins/mixin_fsm_execution.py`

```
"""
Mixin for FSM execution from YAML contracts.

Enables nodes to execute state machines declaratively from ModelFSMSubcontract.
"""

from typing import Any

from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.utils.fsm_executor import (
    FSMState,
    FSMTransitionResult,
    execute_transition,
    validate_fsm_contract,
)


class MixinFSMExecution:
    """
    Mixin providing FSM execution capabilities from YAML contracts.

    Enables reducer nodes to execute state machines declaratively without
    custom code. State transitions are driven entirely by FSM subcontract.

    Usage:
        class NodeMyReducer(NodeCoreBase, MixinFSMExecution):
            # No custom FSM code needed - driven by YAML contract
            pass
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize FSM execution mixin."""
        super().__init__(**kwargs)
        self._fsm_state: FSMState | None = None

    async def execute_fsm_transition(
        self,
        fsm_contract: ModelFSMSubcontract,
        trigger: str,
        context: dict[str, Any],
    ) -> FSMTransitionResult:
        """
        Execute FSM transition from YAML contract.

        Args:
            fsm_contract: FSM subcontract from node contract
            trigger: Event triggering the transition
            context: Execution context data

        Returns:
            FSMTransitionResult with new state and intents
        """
        # Get current state (or use initial state)
        current_state = (
            self._fsm_state.current_state
            if self._fsm_state
            else fsm_contract.initial_state
        )

        # Execute transition using utility function
        result = await execute_transition(
            fsm_contract,
            current_state,
            trigger,
            context,
        )

        # Update internal state if successful
        if result.success:
            self._fsm_state = FSMState(
                current_state=result.new_state,
                context=context,
                history=(self._fsm_state.history if self._fsm_state else [])
                + [result.old_state],
            )

        return result

    async def validate_fsm_contract(
        self, fsm_contract: ModelFSMSubcontract
    ) -> list[str]:
        """
        Validate FSM contract for correctness.

        Args:
            fsm_contract: FSM subcontract to validate

        Returns:
            List of validation errors (empty if valid)
        """
        return await validate_fsm_contract(fsm_contract)

    def get_current_fsm_state(self) -> str | None:
        """Get current FSM state name."""
        return self._fsm_state.current_state if self._fsm_state else None

    def reset_fsm_state(self, fsm_contract: ModelFSMSubcontract) -> None:
        """Reset FSM to initial state."""
        self._fsm_state = FSMState(
            current_state=fsm_contract.initial_state,
            context={},
            history=[],
        )
```

### 1.3 Update mixin_metadata.yaml

**File**: `src/omnibase_core/mixins/mixin_metadata.yaml`

Add new entry:

```
mixins:
  # ... existing mixins ...

  - name: MixinFSMExecution
    version: 1.0.0
    description: |
      Declarative FSM execution from YAML contracts.
      Enables state machines without custom code.

    module: omnibase_core.mixins.mixin_fsm_execution
    class: MixinFSMExecution

    categories:
      - fsm
      - declarative
      - state_management

    node_types:
      - REDUCER
      - ORCHESTRATOR

    capabilities:
      - name: execute_fsm_transition
        description: Execute state transition from FSM contract
        returns: FSMTransitionResult with new state and intents

      - name: validate_fsm_contract
        description: Validate FSM contract structure
        returns: List of validation errors

      - name: get_current_fsm_state
        description: Get current FSM state name
        returns: State name or None

    configuration_schema:
      type: object
      properties:
        auto_validate:
          type: boolean
          default: true
          description: Automatically validate FSM contract on initialization

        strict_mode:
          type: boolean
          default: true
          description: Fail on validation errors (vs. warnings)

    integration_patterns:
      reducer_node:
        pattern: |
          class NodeMetricsReducer(NodeCoreBase, MixinFSMExecution):
              async def process(self, input_data):
                  # FSM-driven processing
                  result = await self.execute_fsm_transition(
                      self.contract.state_transitions,
                      trigger=input_data.trigger,
                      context={"data": input_data.data}
                  )

                  return ModelReducerOutput(
                      result=result.new_state,
                      intents=result.intents
                  )

    examples:
      - title: Metrics Aggregation FSM
        description: State machine for metrics aggregation lifecycle
        code: |
          # No custom Python code needed!
          # FSM defined entirely in YAML contract

          # contracts/reducer_metrics.yaml
          state_transitions:
            state_machine_name: metrics_aggregation
            states:
              - state_name: idle
              - state_name: collecting
              - state_name: aggregating
              - state_name: completed
            transitions:
              - from_state: idle
                to_state: collecting
                trigger: start_collection
```

---

## Phase 2: Workflow Execution Infrastructure

> ⚠️ **NOT YET IMPLEMENTED**
> **Status**: 🚧 Planned for Sprint 2
> **Estimated**: TBD
> The components described below are **not yet available**. This section documents the planned implementation.

**Timeline**: Sprint 2 (Week 3-4)
**Goal**: Enable YAML-driven workflow execution for orchestrator nodes

### 2.1 Workflow Utility Module

**File**: `src/omnibase_core/utils/workflow_executor.py`

```
"""
Workflow execution utilities for declarative orchestration.

Pure functions for executing workflows from ModelWorkflowDefinition.
No side effects - returns results and actions.
"""

from typing import Any
from uuid import UUID, uuid4
from datetime import datetime

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import (
    EnumActionType,
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.orchestrator.model_action import ModelAction


class WorkflowExecutionResult:
    """
    Result of workflow execution.

    Pure data structure containing workflow outcome and emitted actions.
    """

    def __init__(
        self,
        workflow_id: UUID,
        execution_status: EnumWorkflowState,
        completed_steps: list[str],
        failed_steps: list[str],
        actions_emitted: list[ModelAction],
        execution_time_ms: int,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize workflow execution result.

        Args:
            workflow_id: Unique workflow execution ID
            execution_status: Final workflow status
            completed_steps: List of completed step IDs
            failed_steps: List of failed step IDs
            actions_emitted: List of actions emitted during execution
            execution_time_ms: Execution time in milliseconds
            metadata: Optional execution metadata
        """
        self.workflow_id = workflow_id
        self.execution_status = execution_status
        self.completed_steps = completed_steps
        self.failed_steps = failed_steps
        self.actions_emitted = actions_emitted
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()


class WorkflowStepExecutionContext:
    """Context for a single step execution."""

    def __init__(
        self,
        step: ModelWorkflowStep,
        workflow_id: UUID,
        completed_steps: set[UUID],
    ):
        """
        Initialize step execution context.

        Args:
            step: Step to execute
            workflow_id: Parent workflow ID
            completed_steps: Set of completed step IDs
        """
        self.step = step
        self.workflow_id = workflow_id
        self.completed_steps = completed_steps
        self.started_at = datetime.now()
        self.completed_at: datetime | None = None
        self.error: str | None = None


async def execute_workflow(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
    workflow_id: UUID,
    execution_mode: EnumExecutionMode | None = None,
) -> WorkflowExecutionResult:
    """
    Execute workflow declaratively from YAML contract.

    Pure function: (workflow_def, steps) → (result, actions)

    Args:
        workflow_definition: Workflow definition from YAML contract
        workflow_steps: List of workflow steps to execute
        workflow_id: Unique workflow execution ID
        execution_mode: Optional execution mode override

    Returns:
        WorkflowExecutionResult with emitted actions

    Raises:
        ModelOnexError: If workflow execution fails
    """
    start_time = datetime.now()

    # Validate workflow
    validation_errors = await validate_workflow_definition(
        workflow_definition, workflow_steps
    )
    if validation_errors:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Workflow validation failed: {', '.join(validation_errors)}",
            context={"workflow_id": str(workflow_id), "errors": validation_errors},
        )

    # Determine execution mode
    mode = execution_mode or _get_execution_mode(workflow_definition)

    # Execute based on mode
    if mode == EnumExecutionMode.SEQUENTIAL:
        result = await _execute_sequential(
            workflow_definition, workflow_steps, workflow_id
        )
    elif mode == EnumExecutionMode.PARALLEL:
        result = await _execute_parallel(
            workflow_definition, workflow_steps, workflow_id
        )
    elif mode == EnumExecutionMode.BATCH:
        result = await _execute_batch(workflow_definition, workflow_steps, workflow_id)
    else:
        # Default to sequential
        result = await _execute_sequential(
            workflow_definition, workflow_steps, workflow_id
        )

    # Calculate execution time
    end_time = datetime.now()
    execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
    result.execution_time_ms = execution_time_ms

    return result


async def validate_workflow_definition(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
) -> list[str]:
    """
    Validate workflow definition and steps for correctness.

    Pure validation function - no side effects.

    Args:
        workflow_definition: Workflow definition to validate
        workflow_steps: Workflow steps to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[str] = []

    # Check workflow has steps
    if not workflow_steps:
        errors.append("Workflow has no steps defined")
        return errors

    # Check for dependency cycles
    if _has_dependency_cycles(workflow_steps):
        errors.append("Workflow contains dependency cycles")

    # Validate each step
    step_ids = {step.step_id for step in workflow_steps}
    for step in workflow_steps:
        # Check step name
        if not step.step_name:
            errors.append(f"Step {step.step_id} missing name")

        # Check dependencies reference valid steps
        for dep_id in step.depends_on:
            if dep_id not in step_ids:
                errors.append(
                    f"Step '{step.step_name}' depends on non-existent step: {dep_id}"
                )

    return errors


def get_execution_order(
    workflow_steps: list[ModelWorkflowStep],
) -> list[UUID]:
    """
    Get topological execution order for workflow steps.

    Args:
        workflow_steps: Workflow steps to order

    Returns:
        List of step IDs in execution order

    Raises:
        ModelOnexError: If workflow contains cycles
    """
    if _has_dependency_cycles(workflow_steps):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Cannot compute execution order: workflow contains cycles",
            context={},
        )

    return _get_topological_order(workflow_steps)


# Private helper functions


def _get_execution_mode(
    workflow_definition: ModelWorkflowDefinition,
) -> EnumExecutionMode:
    """Extract execution mode from workflow metadata."""
    mode_str = workflow_definition.workflow_metadata.execution_mode
    if mode_str == "sequential":
        return EnumExecutionMode.SEQUENTIAL
    elif mode_str == "parallel":
        return EnumExecutionMode.PARALLEL
    elif mode_str == "batch":
        return EnumExecutionMode.BATCH
    return EnumExecutionMode.SEQUENTIAL


async def _execute_sequential(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
    workflow_id: UUID,
) -> WorkflowExecutionResult:
    """Execute workflow steps sequentially."""
    completed_steps: list[str] = []
    failed_steps: list[str] = []
    all_actions: list[ModelAction] = []
    completed_step_ids: set[UUID] = set()

    # Get topological order for dependency-aware execution
    execution_order = _get_topological_order(workflow_steps)

    # Create step lookup
    steps_by_id = {step.step_id: step for step in workflow_steps}

    for step_id in execution_order:
        step = steps_by_id.get(step_id)
        if not step:
            continue

        # Check if step should be skipped
        if not step.enabled:
            continue

        # Check dependencies are met
        if not _dependencies_met(step, completed_step_ids):
            failed_steps.append(str(step.step_id))
            continue

        try:
            # Create context
            context = WorkflowStepExecutionContext(
                step, workflow_id, completed_step_ids
            )

            # Emit action for this step
            action = _create_action_for_step(step, workflow_id)
            all_actions.append(action)

            # Mark step as completed
            context.completed_at = datetime.now()
            completed_steps.append(str(step.step_id))
            completed_step_ids.add(step.step_id)

        except Exception as e:
            failed_steps.append(str(step.step_id))

            # Handle based on error action
            if step.error_action == "stop":
                break
            elif step.error_action == "continue":
                continue
            # For other error actions, continue for now

    # Determine final status
    status = (
        EnumWorkflowState.COMPLETED
        if not failed_steps
        else EnumWorkflowState.FAILED
    )

    return WorkflowExecutionResult(
        workflow_id=workflow_id,
        execution_status=status,
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        actions_emitted=all_actions,
        execution_time_ms=0,  # Will be set by caller
        metadata={"execution_mode": "sequential"},
    )


async def _execute_parallel(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
    workflow_id: UUID,
) -> WorkflowExecutionResult:
    """Execute workflow steps in parallel (respecting dependencies)."""
    completed_steps: list[str] = []
    failed_steps: list[str] = []
    all_actions: list[ModelAction] = []
    completed_step_ids: set[UUID] = set()

    # For parallel execution, we execute in waves based on dependencies
    remaining_steps = list(workflow_steps)

    while remaining_steps:
        # Find steps with met dependencies
        ready_steps = [
            step
            for step in remaining_steps
            if step.enabled and _dependencies_met(step, completed_step_ids)
        ]

        if not ready_steps:
            # No progress can be made - remaining steps have unmet dependencies
            for step in remaining_steps:
                failed_steps.append(str(step.step_id))
            break

        # Execute ready steps (in parallel conceptually, but we emit actions)
        for step in ready_steps:
            try:
                # Emit action for this step
                action = _create_action_for_step(step, workflow_id)
                all_actions.append(action)

                # Mark as completed
                completed_steps.append(str(step.step_id))
                completed_step_ids.add(step.step_id)

            except Exception as e:
                failed_steps.append(str(step.step_id))

                if step.error_action == "stop":
                    # Stop entire workflow
                    remaining_steps = []
                    break

        # Remove processed steps
        remaining_steps = [s for s in remaining_steps if s not in ready_steps]

    status = (
        EnumWorkflowState.COMPLETED
        if not failed_steps
        else EnumWorkflowState.FAILED
    )

    return WorkflowExecutionResult(
        workflow_id=workflow_id,
        execution_status=status,
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        actions_emitted=all_actions,
        execution_time_ms=0,
        metadata={"execution_mode": "parallel"},
    )


async def _execute_batch(
    workflow_definition: ModelWorkflowDefinition,
    workflow_steps: list[ModelWorkflowStep],
    workflow_id: UUID,
) -> WorkflowExecutionResult:
    """Execute workflow with batching."""
    # For batch mode, use sequential execution with batching metadata
    result = await _execute_sequential(workflow_definition, workflow_steps, workflow_id)
    result.metadata["execution_mode"] = "batch"
    result.metadata["batch_size"] = len(workflow_steps)
    return result


def _create_action_for_step(
    step: ModelWorkflowStep,
    workflow_id: UUID,
) -> ModelAction:
    """
    Create action for workflow step.

    Args:
        step: Workflow step to create action for
        workflow_id: Parent workflow ID

    Returns:
        ModelAction for step execution
    """
    # Map step type to action type
    action_type_map = {
        "compute": EnumActionType.COMPUTE,
        "effect": EnumActionType.EFFECT,
        "reducer": EnumActionType.REDUCE,
        "orchestrator": EnumActionType.ORCHESTRATE,
        "custom": EnumActionType.CUSTOM,
    }

    action_type = action_type_map.get(step.step_type, EnumActionType.CUSTOM)

    # Determine target node type from step type
    target_node_type_map = {
        "compute": "NodeCompute",
        "effect": "NodeEffect",
        "reducer": "NodeReducer",
        "orchestrator": "NodeOrchestrator",
        "custom": "NodeCustom",
    }
    target_node_type = target_node_type_map.get(step.step_type, "NodeCustom")

    return ModelAction(
        action_id=uuid4(),
        action_type=action_type,
        target_node_type=target_node_type,
        payload={
            "workflow_id": str(workflow_id),
            "step_id": str(step.step_id),
            "step_name": step.step_name,
        },
        dependencies=step.depends_on,
        priority=step.priority,
        timeout_ms=step.timeout_ms,
        lease_id=uuid4(),
        epoch=0,
        retry_count=step.retry_count,
        metadata={
            "step_name": step.step_name,
            "correlation_id": str(step.correlation_id),
        },
        created_at=datetime.now(),
    )


def _dependencies_met(
    step: ModelWorkflowStep,
    completed_step_ids: set[UUID],
) -> bool:
    """Check if all step dependencies are met."""
    return all(dep_id in completed_step_ids for dep_id in step.depends_on)


def _get_topological_order(
    workflow_steps: list[ModelWorkflowStep],
) -> list[UUID]:
    """
    Get topological ordering of steps based on dependencies.

    Uses Kahn's algorithm for topological sorting.

    Args:
        workflow_steps: Workflow steps to order

    Returns:
        List of step IDs in topological order
    """
    # Build adjacency list and in-degree map
    step_ids = {step.step_id for step in workflow_steps}
    edges: dict[UUID, list[UUID]] = {step_id: [] for step_id in step_ids}
    in_degree: dict[UUID, int] = {step_id: 0 for step_id in step_ids}

    for step in workflow_steps:
        for dep_id in step.depends_on:
            if dep_id in step_ids:
                edges[dep_id].append(step.step_id)
                in_degree[step.step_id] += 1

    # Kahn's algorithm
    queue = [step_id for step_id, degree in in_degree.items() if degree == 0]
    result: list[UUID] = []

    while queue:
        node = queue.pop(0)
        result.append(node)

        for neighbor in edges.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result


def _has_dependency_cycles(
    workflow_steps: list[ModelWorkflowStep],
) -> bool:
    """
    Check if workflow contains dependency cycles.

    Uses DFS-based cycle detection.

    Args:
        workflow_steps: Workflow steps to check

    Returns:
        True if cycles detected, False otherwise
    """
    # Build adjacency list
    step_ids = {step.step_id for step in workflow_steps}
    edges: dict[UUID, list[UUID]] = {step_id: [] for step_id in step_ids}

    for step in workflow_steps:
        for dep_id in step.depends_on:
            if dep_id in step_ids:
                # Note: dependency is reversed - we go FROM dependent TO dependency
                edges[step.step_id].append(dep_id)

    # DFS-based cycle detection
    visited: set[UUID] = set()
    rec_stack: set[UUID] = set()

    def has_cycle_dfs(node: UUID) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in edges.get(node, []):
            if neighbor not in visited:
                if has_cycle_dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for step_id in step_ids:
        if step_id not in visited:
            if has_cycle_dfs(step_id):
                return True

    return False
```

### 2.2 Workflow Execution Mixin

**File**: `src/omnibase_core/mixins/mixin_workflow_execution.py`

```
"""
Mixin for workflow execution from YAML contracts.

Enables orchestrator nodes to execute workflows declaratively.
"""

from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.utils.workflow_executor import (
    WorkflowExecutionResult,
    execute_workflow,
    get_execution_order,
    validate_workflow_definition,
)


class MixinWorkflowExecution:
    """
    Mixin providing workflow execution capabilities from YAML contracts.

    Enables orchestrator nodes to execute workflows declaratively without
    custom code. Workflow coordination is driven entirely by contract.

    Usage:
        class NodeMyOrchestrator(NodeCoreBase, MixinWorkflowExecution):
            # No custom workflow code needed - driven by YAML contract
            pass
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize workflow execution mixin."""
        super().__init__(**kwargs)

    async def execute_workflow_from_contract(
        self,
        workflow_definition: ModelWorkflowDefinition,
        workflow_steps: list[ModelWorkflowStep],
        workflow_id: UUID,
        execution_mode: EnumExecutionMode | None = None,
    ) -> WorkflowExecutionResult:
        """
        Execute workflow from YAML contract.

        Args:
            workflow_definition: Workflow definition from node contract
            workflow_steps: List of workflow steps to execute
            workflow_id: Unique workflow execution ID
            execution_mode: Optional execution mode override

        Returns:
            WorkflowExecutionResult with emitted actions
        """
        return await execute_workflow(
            workflow_definition, workflow_steps, workflow_id, execution_mode
        )

    async def validate_workflow_contract(
        self,
        workflow_definition: ModelWorkflowDefinition,
        workflow_steps: list[ModelWorkflowStep],
    ) -> list[str]:
        """
        Validate workflow contract for correctness.

        Args:
            workflow_definition: Workflow definition to validate
            workflow_steps: Workflow steps to validate

        Returns:
            List of validation errors (empty if valid)
        """
        return await validate_workflow_definition(workflow_definition, workflow_steps)

    def get_workflow_execution_order(
        self,
        workflow_steps: list[ModelWorkflowStep],
    ) -> list[UUID]:
        """
        Get topological execution order for workflow steps.

        Args:
            workflow_steps: Workflow steps to order

        Returns:
            List of step IDs in execution order

        Raises:
            ModelOnexError: If workflow contains cycles
        """
        return get_execution_order(workflow_steps)
```

---

## Phase 3: Example Contracts & Usage Patterns

> ⚠️ **NOT YET IMPLEMENTED**
> **Status**: ⏳ Planned for Sprint 3
> **Estimated**: TBD
> The components described below are **not yet available**. This section documents the planned implementation.

**Timeline**: Sprint 3 (Week 5-6)
**Goal**: Comprehensive examples showing mixin composition patterns

### Key Insight: Declarative Nodes ARE Now the Primary Implementation (v0.4.0)

**UPDATE (v0.4.0)**: `NodeReducer` and `NodeOrchestrator` are now the **PRIMARY declarative implementations**. The "Declarative" suffix was removed because these ARE the standard.

```python
# ✅ CORRECT (v0.4.0) - Use the primary declarative base classes
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator

class NodeMetricsReducer(NodeReducer):
    """Reducer with FSM-driven execution by default - just inherit!"""
    pass  # All logic from YAML contract

class NodePipelineOrchestrator(NodeOrchestrator):
    """Orchestrator with workflow-driven execution by default!"""
    pass  # All logic from YAML contract

# Legacy imports (for backwards compatibility only)
from omnibase_core.nodes.legacy.node_reducer_legacy import NodeReducerLegacy
from omnibase_core.nodes.legacy.node_orchestrator_legacy import NodeOrchestratorLegacy
```

**Or compose with additional mixins:**
```python
class NodeMetricsReducer(NodeReducer, MixinEventBus):
    """Reducer with FSM (built-in) + Event bus (additional)."""
    pass
```

### 3.1 Example YAML Contracts

Create comprehensive example contracts demonstrating common patterns:

#### Pattern 1: FSM-Driven Reducer with Events

**File**: `examples/contracts/reducer_with_fsm_and_events.yaml`

```
node_type: REDUCER
node_name: metrics_aggregator_with_events
node_version: 1.0.0
description: Metrics reducer with FSM and event publishing

# FSM subcontract drives state transitions
state_transitions:
  state_machine_name: metrics_fsm
  initial_state: idle
  states:
    - state_name: idle
      entry_actions: [log_ready]
    - state_name: collecting
      entry_actions: [start_timer]
      exit_actions: [stop_timer]
    - state_name: completed
      is_terminal: true
  transitions:
    - from_state: idle
      to_state: collecting
      trigger: start_collection
    - from_state: collecting
      to_state: completed
      trigger: data_ready

# Event bus configuration for publishing state changes
event_coordination:
  event_types:
    - StateChanged
    - CollectionCompleted
```

**Usage**:
```
class NodeMetricsReducer(NodeCoreBase, MixinFSMExecution, MixinEventBus):
    # No custom FSM code - driven by YAML!
    # MixinFSMExecution provides execute_fsm_transition()
    # MixinEventBus provides publish_event()
    pass
```

#### Pattern 2: Workflow Orchestrator with Parallel Execution

**File**: `examples/contracts/orchestrator_parallel_workflow.yaml`

```
node_type: ORCHESTRATOR
node_name: parallel_data_pipeline
node_version: 1.0.0

workflow_coordination:
  execution_mode: parallel
  max_parallel_branches: 4

  workflow_definition:
    execution_graph:
      steps:
        - step_id: fetch_data
          step_type: effect
          actions:
            - action_type: EFFECT
              target_node_type: NodeDataFetcher

        - step_id: validate_data
          dependencies: [fetch_data]
          actions:
            - action_type: COMPUTE
              target_node_type: NodeValidator
```

**Usage**:
```
class NodePipelineOrchestrator(NodeCoreBase, MixinWorkflowExecution):
    # No custom workflow code - driven by YAML!
    # MixinWorkflowExecution provides execute_workflow_from_contract()
    pass
```

#### Pattern 3: Complex Multi-State Workflow with Error Handling

**File**: `examples/contracts/orchestrator_with_error_recovery.yaml`

```
node_type: ORCHESTRATOR
workflow_coordination:
  execution_mode: sequential
  recovery_enabled: true
  rollback_enabled: true

  coordination_rules:
    failure_strategy: retry_with_backoff
    max_retries: 3
    retry_delay_ms: 1000
```

### 3.2 Usage Pattern Documentation

**File**: `docs/guides/DECLARATIVE_PATTERNS.md`

#### Pattern: Reducer with FSM

**When to use**: State-driven aggregation, lifecycle management

```
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
from omnibase_core.mixins.mixin_event_bus import MixinEventBus

class NodeMyReducer(NodeCoreBase, MixinFSMExecution, MixinEventBus):
    """
    Reducer with FSM-driven state transitions and event publishing.

    Mixins provide:
    - MixinFSMExecution: execute_fsm_transition(), validate_fsm_contract()
    - MixinEventBus: publish_event(), subscribe_to_event()
    """

    async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
        # 1. Execute FSM transition from YAML contract
        fsm_result = await self.execute_fsm_transition(
            fsm_contract=self.contract.state_transitions,
            trigger=input_data.metadata.get("trigger", "process"),
            context={"input": input_data.data}
        )

        # 2. Publish state change event
        await self.publish_event(StateChangedEvent(
            old_state=fsm_result.old_state,
            new_state=fsm_result.new_state,
            timestamp=datetime.now()
        ))

        # 3. Return result with intents
        return ModelReducerOutput(
            result=fsm_result.new_state,
            intents=fsm_result.intents,
            metadata={"fsm_state": fsm_result.new_state}
        )
```

#### Pattern: Orchestrator with Workflow Execution

**When to use**: Multi-step workflows, parallel coordination

```
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_workflow_execution import MixinWorkflowExecution

class NodeMyOrchestrator(NodeCoreBase, MixinWorkflowExecution):
    """
    Orchestrator with workflow execution from YAML contract.

    Mixins provide:
    - MixinWorkflowExecution: execute_workflow_from_contract()
    """

    async def process(self, input_data: ModelOrchestratorInput) -> ModelOrchestratorOutput:
        # Execute workflow declaratively from YAML
        result = await self.execute_workflow_from_contract(
            workflow_contract=self.contract.workflow_coordination.workflow_definition,
            workflow_id=input_data.workflow_id,
            context=input_data.metadata or {}
        )

        return ModelOrchestratorOutput(
            execution_status=result.execution_status,
            completed_steps=result.completed_steps,
            actions_emitted=result.actions_emitted
        )
```

### 3.3 Best Practices Documentation

**File**: `docs/best-practices/MIXIN_COMPOSITION.md`

#### Composing Multiple Mixins

```
# ✅ GOOD - Clear, declarative composition
class NodeAdvancedReducer(
    NodeCoreBase,           # Always first
    MixinFSMExecution,      # FSM capabilities
    MixinEventBus,          # Event publishing
    MixinCaching,           # Result caching
    MixinHealthCheck        # Health monitoring
):
    """
    Advanced reducer with multiple cross-cutting concerns.

    Each mixin provides specific capabilities:
    - FSM execution from YAML
    - Event publishing/subscription
    - Result caching with TTL
    - Health check endpoints
    """
    pass
```

#### Avoiding Common Pitfalls

```
# ❌ BAD - Don't create unnecessary base classes
class NodeReducerDeclarative(NodeCoreBase, MixinFSMExecution):
    """This is redundant - just use mixins directly!"""
    pass

# ✅ GOOD - Compose mixins directly on your node
class NodeMyReducer(NodeCoreBase, MixinFSMExecution):
    """Clear, direct composition."""
    pass
```

---

## Phase 4: Migration and Examples

> ⚠️ **NOT YET IMPLEMENTED**
> **Status**: ⏳ Planned for Sprint 4
> **Estimated**: TBD
> The components described below are **not yet available**. This section documents the planned implementation.

**Timeline**: Sprint 4 (Week 7-8)
**Goal**: Examples, documentation, migration guides

### 4.1 Example Contracts Directory

Create `examples/contracts/` with:

#### FSM Example: Metrics Aggregator

**File**: `examples/contracts/reducer_metrics_aggregator.yaml`

```
node_type: REDUCER
node_name: metrics_aggregator_declarative
node_version: 1.0.0

state_transitions:
  state_machine_name: metrics_aggregation_fsm
  state_machine_version: 1.0.0
  description: Metrics aggregation lifecycle state machine

  initial_state: idle

  states:
    - state_name: idle
      state_type: operational
      is_terminal: false
      entry_actions:
        - log_fsm_ready
      exit_actions: []
      validation_rules: []

    - state_name: collecting
      state_type: operational
      is_terminal: false
      entry_actions:
        - start_collection_timer
        - initialize_collection_buffer
      exit_actions:
        - stop_collection_timer
      validation_rules:
        - validate_data_sources_not_empty

    - state_name: aggregating
      state_type: operational
      is_terminal: false
      entry_actions:
        - initialize_aggregation_context
      exit_actions: []
      validation_rules:
        - validate_aggregation_strategy

    - state_name: completed
      state_type: terminal
      is_terminal: true
      entry_actions:
        - emit_completion_event
        - publish_aggregated_metrics
      exit_actions: []
      validation_rules: []

    - state_name: error
      state_type: error
      is_terminal: true
      entry_actions:
        - log_error_state
        - emit_error_event
      exit_actions: []
      validation_rules: []

  transitions:
    - transition_name: start_collection
      from_state: idle
      to_state: collecting
      trigger: collect_metrics
      conditions:
        - condition_type: field_check
          field: data_sources
          operator: min_length
          value: 1
      actions:
        - action_name: log_collection_start
          action_type: logging
      is_atomic: true
      retry_enabled: true
      max_retries: 3
      retry_delay_ms: 1000

    - transition_name: begin_aggregation
      from_state: collecting
      to_state: aggregating
      trigger: data_ready
      conditions: []
      actions:
        - action_name: log_aggregation_start
          action_type: logging
      is_atomic: true
      retry_enabled: false

    - transition_name: complete_aggregation
      from_state: aggregating
      to_state: completed
      trigger: aggregation_done
      conditions: []
      actions:
        - action_name: finalize_aggregation
          action_type: computation
      is_atomic: true
      retry_enabled: false

    - transition_name: handle_error
      from_state: "*"
      to_state: error
      trigger: error_occurred
      conditions: []
      actions:
        - action_name: capture_error_context
          action_type: logging
      is_atomic: false
      retry_enabled: false

  persistence_enabled: true
  recovery_enabled: true
  rollback_enabled: true
  checkpoint_interval_ms: 30000
  max_checkpoints: 10
  conflict_resolution_strategy: priority_based
  concurrent_transitions_allowed: false
  transition_timeout_ms: 5000
  strict_validation_enabled: true
  state_monitoring_enabled: true
  event_logging_enabled: true
```

#### Workflow Example: Data Pipeline

**File**: `examples/contracts/orchestrator_data_pipeline.yaml`

```
node_type: ORCHESTRATOR
node_name: data_pipeline_orchestrator
node_version: 1.0.0

workflow_coordination:
  execution_mode: sequential
  max_parallel_branches: 4
  checkpoint_enabled: true
  state_persistence_enabled: true
  rollback_enabled: true
  recovery_enabled: true

  workflow_definition:
    workflow_metadata:
      workflow_name: data_processing_pipeline
      workflow_version: 1.0.0
      description: End-to-end data processing workflow
      execution_mode: sequential

    execution_graph:
      steps:
        - step_id: fetch_raw_data
          step_name: Fetch Raw Data from Sources
          step_type: effect
          actions:
            - action_type: EFFECT
              target_node_type: NodeDataFetcher
              payload:
                source: database
                query: SELECT * FROM raw_data
              priority: 1
          timeout_ms: 10000
          retry_enabled: true
          max_retries: 3

        - step_id: validate_data_quality
          step_name: Validate Data Quality
          step_type: compute
          actions:
            - action_type: COMPUTE
              target_node_type: NodeDataValidator
              payload:
                validation_rules:
                  - check_nulls
                  - check_schema
                  - check_ranges
              priority: 1
          dependencies:
            - fetch_raw_data
          timeout_ms: 5000
          retry_enabled: true
          max_retries: 2

        - step_id: transform_data
          step_name: Transform and Enrich Data
          step_type: compute
          actions:
            - action_type: COMPUTE
              target_node_type: NodeDataTransformer
              payload:
                transformations:
                  - normalize_values
                  - enrich_metadata
                  - compute_derived_fields
              priority: 1
          dependencies:
            - validate_data_quality
          timeout_ms: 15000
          retry_enabled: true
          max_retries: 2

        - step_id: aggregate_metrics
          step_name: Aggregate Metrics
          step_type: reduce
          actions:
            - action_type: REDUCE
              target_node_type: NodeMetricsAggregator
              payload:
                aggregation_strategy: sum
                group_by_fields:
                  - category
                  - timestamp_hour
              priority: 2
          dependencies:
            - transform_data
          timeout_ms: 8000
          retry_enabled: true
          max_retries: 2

        - step_id: persist_results
          step_name: Persist Aggregated Results
          step_type: effect
          actions:
            - action_type: EFFECT
              target_node_type: NodeDatabaseWriter
              payload:
                target_table: aggregated_metrics
                write_mode: upsert
              priority: 1
          dependencies:
            - aggregate_metrics
          timeout_ms: 10000
          retry_enabled: true
          max_retries: 3

    coordination_rules:
      failure_strategy: rollback
      partial_success_handling: continue
      timeout_handling: retry_with_backoff
      dependency_resolution: strict
```

### 4.2 Migration Guide

**File**: `docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md`

#### Before: Imperative Pattern

```
class NodeMyReducer(NodeReducer):
    def __init__(self, container):
        super().__init__(container)
        # Custom FSM state
        self.current_state = "idle"
        self.state_handlers = {
            "idle": self._handle_idle,
            "processing": self._handle_processing,
        }

    async def process(self, input_data):
        # Custom state machine logic
        handler = self.state_handlers[self.current_state]
        result = await handler(input_data)
        # ... 50+ lines of FSM code ...
```

#### After: Declarative Pattern with Mixins

```
# 1. Create YAML contract (one time)
# contracts/my_reducer.yaml
node_type: REDUCER
state_transitions:
  state_machine_name: my_fsm
  states: [idle, processing, completed]
  transitions: [...]

# 2. Use NodeCoreBase + MixinFSMExecution (no custom FSM code!)
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer

class NodeMyReducer(NodeCoreBase, MixinFSMExecution):
    """Reducer driven by FSM contract - no custom state machine code!"""

    async def process(self, input_data):
        # Execute FSM transition declaratively
        result = await self.execute_fsm_transition(
            self.contract.state_transitions,
            trigger=input_data.metadata.get("trigger"),
            context={"data": input_data.data}
        )
        return ModelReducerOutput(
            result=result.new_state,
            intents=result.intents
        )

# Instantiate - DONE!
contract = ModelContractReducer.from_yaml("contracts/my_reducer.yaml")
node = NodeMyReducer(container, contract)
```

#### Migration Steps

1. **Analyze current FSM** - Map states, transitions, actions
2. **Create YAML contract** - Define FSM declaratively
3. **Validate contract** - Use validation utilities
4. **Add mixin to node class** - Inherit from MixinFSMExecution
5. **Use mixin methods** - Call execute_fsm_transition() in process()
6. **Test** - Verify behavior matches
7. **Remove custom FSM code** - Delete old state machine implementation

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/utils/test_fsm_executor.py`

```
"""Tests for FSM execution utilities."""

import pytest
from omnibase_core.utils.fsm_executor import execute_transition, validate_fsm_contract
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)

@pytest.mark.asyncio
async def test_fsm_transition_success():
    """Test successful FSM transition."""
    fsm = ModelFSMSubcontract(
        state_machine_name="test_fsm",
        states=[
            ModelFSMStateDefinition(state_name="idle", state_type="operational"),
            ModelFSMStateDefinition(state_name="running", state_type="operational"),
        ],
        initial_state="idle",
        transitions=[
            ModelFSMStateTransition(
                transition_name="start",
                from_state="idle",
                to_state="running",
                trigger="start_event",
            )
        ],
    )

    result = await execute_transition(fsm, "idle", "start_event", {})

    assert result.success
    assert result.new_state == "running"
    assert result.old_state == "idle"
    assert len(result.intents) > 0  # Should emit intents

# ... more tests ...
```

### Integration Tests

**File**: `tests/integration/test_fsm_mixin_integration.py`

```
"""Integration tests for FSM execution mixin."""

import pytest
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer

class TestReducerWithFSM(NodeCoreBase, MixinFSMExecution):
    """Test reducer using FSM mixin."""

    async def process(self, input_data):
        result = await self.execute_fsm_transition(
            self.contract.state_transitions,
            trigger=input_data.metadata.get("trigger"),
            context={"data": input_data.data}
        )
        return ModelReducerOutput(
            result=result.new_state,
            intents=result.intents,
            metadata={"fsm_state": result.new_state}
        )

@pytest.mark.asyncio
async def test_reducer_with_fsm_mixin(container):
    """Test reducer driven by FSM mixin and YAML contract."""
    # Load contract from YAML
    contract = ModelContractReducer.from_yaml(
        "examples/contracts/reducer_metrics_aggregator.yaml"
    )

    # Create node with FSM mixin
    node = TestReducerWithFSM(container, contract)

    # Process input
    input_data = ModelReducerInput(
        data=[{"metric": "cpu", "value": 50}],
        reduction_type=EnumReductionType.AGGREGATE,
        metadata={"trigger": "collect_metrics"},
    )

    result = await node.process(input_data)

    # Verify FSM executed via mixin
    assert result.metadata["fsm_state"] == "collecting"
    assert len(result.intents) > 0  # Should emit intents
```

---

## Success Metrics

### Phase 1 Success Criteria

- [ ] FSM utility module complete with 90%+ test coverage
- [ ] MixinFSMExecution functional and tested
- [ ] Example FSM YAML contract validates successfully
- [ ] FSM transitions execute without errors
- [ ] Intents emitted correctly for all state actions

### Phase 2 Success Criteria

- [ ] Workflow utility module complete with 90%+ test coverage
- [ ] MixinWorkflowExecution functional and tested
- [ ] Example workflow YAML contract validates successfully
- [ ] Sequential workflow execution working
- [ ] Actions emitted correctly for all steps

### Phase 3 Success Criteria

- [ ] 5+ example YAML contracts covering common patterns
- [ ] Example contracts validate successfully
- [ ] Usage pattern documentation complete with before/after examples
- [ ] Best practices guide for mixin composition
- [ ] All examples demonstrate mixin-based composition (no declarative base classes)

### Phase 4 Success Criteria

- [ ] 5+ example YAML contracts covering common patterns
- [ ] Migration guide complete with before/after examples
- [ ] Documentation updated across all tutorials
- [ ] 3+ teams successfully migrated to declarative pattern
- [ ] Developer feedback: "faster to write declarative contracts than code"

---

## Timeline Summary

| Phase | Duration | Deliverable | Team |
|-------|----------|-------------|------|
| Phase 1 | Week 1-2 | FSM execution infrastructure | Core Team |
| Phase 2 | Week 3-4 | Workflow execution infrastructure | Core Team |
| Phase 3 | Week 5-6 | Example contracts and usage patterns | Core Team |
| Phase 4 | Week 7-8 | Migration guides and best practices | Core + DevRel |

**Total**: 8 weeks to complete declarative architecture

---

## Next Steps

1. **Review this plan** - Team feedback and approval
2. **Create GitHub issues** - One issue per component
3. **Assign Phase 1** - Start with FSM execution
4. **Set up CI/CD** - Add tests for new components
5. **Kickoff Sprint 1** - Begin implementation

---

**Last Updated**: 2025-12-05
**Status**: ✅ COMPLETE - All phases implemented, declarative nodes are now primary
**Note**: See v0.4.0 release notes for naming convention changes

---

## Appendix: Key Files (v0.4.0 Updated)

```
Primary Node Classes (v0.4.0):
├── src/omnibase_core/nodes/
│   ├── node_reducer.py              # PRIMARY FSM-driven reducer (was NodeReducerDeclarative)
│   ├── node_orchestrator.py         # PRIMARY workflow-driven orchestrator (was NodeOrchestratorDeclarative)
│   ├── node_compute.py              # Primary compute node
│   ├── node_effect.py               # Primary effect node
│   └── legacy/                      # Backwards compatibility
│       ├── node_reducer_legacy.py   # Legacy imperative reducer
│       └── node_orchestrator_legacy.py # Legacy imperative orchestrator

Implementation Components:
├── src/omnibase_core/
│   ├── utils/
│   │   ├── fsm_executor.py           # FSM execution logic (✅ Complete)
│   │   └── workflow_executor.py      # Workflow execution logic (✅ Complete)
│   └── mixins/
│       ├── mixin_fsm_execution.py    # FSM execution mixin (✅ Complete)
│       └── mixin_workflow_execution.py # Workflow execution mixin (✅ Complete)

Example Contracts:
├── examples/contracts/
│   ├── reducer_with_fsm_and_events.yaml     # FSM + Events example
│   ├── orchestrator_parallel_workflow.yaml  # Parallel workflow example
│   └── orchestrator_with_error_recovery.yaml # Error handling example

Tests:
├── tests/
│   ├── unit/utils/
│   │   ├── test_fsm_executor.py       # FSM utility tests (✅ Complete)
│   │   └── test_workflow_executor.py  # Workflow utility tests (✅ Complete)
│   └── integration/
│       ├── test_fsm_mixin_integration.py
│       └── test_workflow_mixin_integration.py

Documentation:
├── docs/guides/
│   ├── DECLARATIVE_PATTERNS.md              # Usage patterns
│   └── MIGRATING_TO_DECLARATIVE_NODES.md    # Migration guide
└── docs/best-practices/
    └── MIXIN_COMPOSITION.md                 # Composition best practices
```

**Key Change (v0.4.0)**: `NodeReducer` and `NodeOrchestrator` ARE now the declarative implementations. No "Declarative" suffix needed - these ARE the standard.
