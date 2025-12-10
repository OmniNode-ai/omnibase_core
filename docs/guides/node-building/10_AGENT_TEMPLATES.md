# Agent Templates for ONEX Node Development

> **Version**: v0.4.0
> **Status**: Complete
> **Purpose**: Structured, copy-paste-ready templates for node development
> **Format**: Machine-parseable with explicit parameters and validation checklists
> **Last Updated**: 2025-12-05

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [NodeCompute Template](#nodecompute-template)
3. [NodeEffect Template](#nodeeffect-template)
4. [NodeReducer Template](#nodereducer-template)
5. [NodeOrchestrator Template](#nodeorchestrator-template)
6. [Validation Checklists](#validation-checklists)
7. [Common Patterns](#common-patterns)
8. [Error Recovery](#error-recovery)

---

## Quick Reference

### Node Type Selection Matrix

```yaml
node_selection:
  COMPUTE:
    use_when:
      - "Pure data transformation"
      - "Business logic calculations"
      - "No external I/O required"
      - "Deterministic operations"
    never_use_when:
      - "API calls needed"
      - "Database operations"
      - "File system access"

  EFFECT:
    use_when:
      - "External API calls"
      - "Database read/write"
      - "File system operations"
      - "Message queue publishing"
    never_use_when:
      - "Pure calculations"
      - "State aggregation"
      - "Workflow coordination"

  REDUCER:
    use_when:
      - "State aggregation"
      - "FSM-driven state transitions"
      - "Event sourcing"
      - "Data accumulation"
    never_use_when:
      - "External I/O"
      - "Workflow orchestration"
      - "Simple transformations"

  ORCHESTRATOR:
    use_when:
      - "Multi-step workflows"
      - "Parallel task coordination"
      - "Dependency management"
      - "Cross-node orchestration"
    never_use_when:
      - "Single operations"
      - "Direct I/O"
      - "Simple state changes"
```

### Decision Tree for Agents

```yaml
agent_decision_tree:
  question_1:
    ask: "Does the node perform external I/O operations?"
    if_yes: "go_to_question_3"
    if_no: "go_to_question_2"

  question_2:
    ask: "Does it maintain state between calls or aggregate data?"
    if_yes: "USE REDUCER"
    if_no: "USE COMPUTE"

  question_3:
    ask: "Does it coordinate multiple other nodes?"
    if_yes: "USE ORCHESTRATOR"
    if_no: "USE EFFECT"
```

### Universal Import Block

```python
# v0.4.0 Primary Imports - USE THESE
from omnibase_core.nodes import (
    NodeCompute,
    NodeEffect,
    NodeReducer,
    NodeOrchestrator,
    ModelComputeInput,
    ModelComputeOutput,
    ModelEffectInput,
    ModelEffectOutput,
    ModelReducerInput,
    ModelReducerOutput,
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
```

---

## NodeCompute Template

### Parameters Schema

```yaml
template_id: "COMPUTE_NODE_V1"
parameters:
  NODE_NAME:
    type: string
    pattern: "Node[Domain][Purpose]Compute"
    example: "NodeDataTransformerCompute"
    required: true

  DOMAIN:
    type: string
    description: "Business domain (e.g., Payment, User, Order)"
    example: "Payment"
    required: true

  INPUT_MODEL:
    type: string
    description: "Pydantic model class for input"
    example: "PaymentRequest"
    required: true

  OUTPUT_MODEL:
    type: string
    description: "Pydantic model class for output"
    example: "PaymentResult"
    required: true

  COMPUTATION_DESCRIPTION:
    type: string
    description: "What this node computes"
    example: "Calculates payment fees and totals"
    required: true
```

### Generated Code Template

```python
"""
{NODE_NAME} - {COMPUTATION_DESCRIPTION}

Domain: {DOMAIN}
Type: COMPUTE (pure transformation, no I/O)
Version: v0.4.0
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.nodes import NodeCompute, ModelComputeInput, ModelComputeOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


# === INPUT/OUTPUT MODELS ===
# Replace these with your actual models

class {INPUT_MODEL}(BaseModel):
    """Input model for {NODE_NAME}."""
    # TODO: Define your input fields
    data: Any


class {OUTPUT_MODEL}(BaseModel):
    """Output model for {NODE_NAME}."""
    # TODO: Define your output fields
    result: Any


# === NODE IMPLEMENTATION ===

class {NODE_NAME}(NodeCompute[{INPUT_MODEL}, {OUTPUT_MODEL}]):
    """
    {COMPUTATION_DESCRIPTION}

    This is a COMPUTE node - pure transformation with no side effects.

    Attributes:
        container: ONEX dependency injection container

    Example:
        ```python
        container = ModelONEXContainer()
        node = {NODE_NAME}(container)

        input_data = ModelComputeInput(
            data={INPUT_MODEL}(data="example"),
            operation_id=uuid4(),
        )
        result = await node.process(input_data)
        ```
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize {NODE_NAME}.

        Args:
            container: ONEX container for dependency injection
        """
        super().__init__(container)  # MANDATORY - do not remove

        # Initialize any computation-specific configuration
        # Example: self.config = container.get_service("ConfigService")

    async def process(
        self,
        input_data: ModelComputeInput[{INPUT_MODEL}],
    ) -> ModelComputeOutput[{OUTPUT_MODEL}]:
        """
        Execute pure computation.

        Args:
            input_data: Compute input with {INPUT_MODEL} data

        Returns:
            Compute output with {OUTPUT_MODEL} result

        Raises:
            ModelOnexError: If computation fails
        """
        try:
            # Extract input
            data: {INPUT_MODEL} = input_data.data

            # === YOUR COMPUTATION LOGIC HERE ===
            # IMPORTANT: No I/O operations allowed
            # - No API calls
            # - No database queries
            # - No file operations

            result: {OUTPUT_MODEL} = self._compute(data)

            # Return result
            return ModelComputeOutput(
                result=result,
                operation_id=input_data.operation_id,
                metadata={
                    "node_type": "{NODE_NAME}",
                    "computation": "success",
                },
            )

        except Exception as e:
            raise ModelOnexError(
                message=f"{NODE_NAME} computation failed: {e}",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={"input": str(input_data.data)},
            ) from e

    def _compute(self, data: {INPUT_MODEL}) -> {OUTPUT_MODEL}:
        """
        Pure computation logic.

        Args:
            data: Input data to transform

        Returns:
            Transformed output data
        """
        # TODO: Implement your computation logic
        # Example:
        # return {OUTPUT_MODEL}(result=data.data.upper())
        raise NotImplementedError("Implement _compute method")


# === TEST TEMPLATE ===

"""
# Save as: tests/unit/nodes/test_{node_name_lower}.py

import pytest
from uuid import uuid4

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes import ModelComputeInput
from your_module import {NODE_NAME}, {INPUT_MODEL}


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer()


@pytest.fixture
def node(container: ModelONEXContainer) -> {NODE_NAME}:
    return {NODE_NAME}(container)


@pytest.mark.unit
class Test{NODE_NAME}:
    async def test_process_success(self, node: {NODE_NAME}) -> None:
        input_data = ModelComputeInput(
            data={INPUT_MODEL}(data="test"),
            operation_id=uuid4(),
        )
        result = await node.process(input_data)
        assert result is not None
        assert result.metadata["computation"] == "success"

    async def test_process_error_handling(self, node: {NODE_NAME}) -> None:
        # Test error cases
        pass
"""
```

### Validation Checklist

```yaml
checklist_id: "COMPUTE_VALIDATION_V1"
items:
  - id: "C001"
    check: "Class inherits from NodeCompute"
    severity: "CRITICAL"
    verify: "grep 'class.*NodeCompute' {file}"

  - id: "C002"
    check: "super().__init__(container) is called"
    severity: "CRITICAL"
    verify: "grep 'super().__init__(container)' {file}"

  - id: "C003"
    check: "No I/O operations in process() method"
    severity: "CRITICAL"
    verify: "Manual review - no httpx, requests, open(), db calls"

  - id: "C004"
    check: "Input/Output types match Generic parameters"
    severity: "HIGH"

  - id: "C005"
    check: "ModelOnexError used for error handling"
    severity: "HIGH"
    verify: "grep 'ModelOnexError' {file}"

  - id: "C006"
    check: "Docstrings present on class and methods"
    severity: "MEDIUM"

  - id: "C007"
    check: "Type hints on all parameters and returns"
    severity: "MEDIUM"
    verify: "poetry run mypy {file}"
```

---

## NodeEffect Template

### Parameters Schema

```yaml
template_id: "EFFECT_NODE_V1"
parameters:
  NODE_NAME:
    type: string
    pattern: "Node[Domain][Purpose]Effect"
    example: "NodePaymentGatewayEffect"
    required: true

  DOMAIN:
    type: string
    description: "Business domain"
    example: "Payment"
    required: true

  EFFECT_TYPE:
    type: enum
    values: ["API_CALL", "DATABASE", "FILE_SYSTEM", "MESSAGE_QUEUE", "EXTERNAL_SERVICE"]
    description: "Type of external effect"
    required: true

  INPUT_MODEL:
    type: string
    example: "PaymentRequest"
    required: true

  OUTPUT_MODEL:
    type: string
    example: "PaymentResponse"
    required: true

  EFFECT_DESCRIPTION:
    type: string
    example: "Calls external payment gateway API"
    required: true
```

### Generated Code Template

```python
"""
{NODE_NAME} - {EFFECT_DESCRIPTION}

Domain: {DOMAIN}
Type: EFFECT (external I/O operations)
Effect Type: {EFFECT_TYPE}
Version: v0.4.0
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.nodes import NodeEffect, ModelEffectInput, ModelEffectOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_types import EnumEffectType


# === INPUT/OUTPUT MODELS ===

class {INPUT_MODEL}(BaseModel):
    """Input model for {NODE_NAME}."""
    # TODO: Define your input fields
    data: Any


class {OUTPUT_MODEL}(BaseModel):
    """Output model for {NODE_NAME}."""
    # TODO: Define your output fields
    result: Any


# === NODE IMPLEMENTATION ===

class {NODE_NAME}(NodeEffect[{INPUT_MODEL}, {OUTPUT_MODEL}]):
    """
    {EFFECT_DESCRIPTION}

    This is an EFFECT node - handles external I/O operations.
    Effect Type: {EFFECT_TYPE}

    Attributes:
        container: ONEX dependency injection container

    Example:
        ```python
        container = ModelONEXContainer()
        node = {NODE_NAME}(container)

        input_data = ModelEffectInput(
            operation_data={INPUT_MODEL}(data="example"),
            effect_type=EnumEffectType.{EFFECT_TYPE},
            operation_id=uuid4(),
        )
        result = await node.process(input_data)
        ```
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize {NODE_NAME}.

        Args:
            container: ONEX container for dependency injection
        """
        super().__init__(container)  # MANDATORY - do not remove

        # Initialize effect-specific resources via DI
        # Example: self.http_client = container.get_service("HttpClient")
        # Example: self.db_pool = container.get_service("DatabasePool")

    async def process(
        self,
        input_data: ModelEffectInput[{INPUT_MODEL}],
    ) -> ModelEffectOutput[{OUTPUT_MODEL}]:
        """
        Execute external effect operation.

        Args:
            input_data: Effect input with operation data

        Returns:
            Effect output with operation result

        Raises:
            ModelOnexError: If effect execution fails
        """
        try:
            # Extract operation data
            data: {INPUT_MODEL} = input_data.operation_data

            # === YOUR EFFECT LOGIC HERE ===
            # This is where I/O operations happen:
            # - API calls
            # - Database queries
            # - File operations
            # - Message publishing

            result: {OUTPUT_MODEL} = await self._execute_effect(data)

            # Return result
            return ModelEffectOutput(
                result=result,
                operation_id=input_data.operation_id,
                effect_type=input_data.effect_type,
                success=True,
                metadata={
                    "node_type": "{NODE_NAME}",
                    "effect_type": "{EFFECT_TYPE}",
                },
            )

        except Exception as e:
            raise ModelOnexError(
                message=f"{NODE_NAME} effect failed: {e}",
                error_code=EnumCoreErrorCode.EXTERNAL_SERVICE_ERROR,
                context={
                    "effect_type": "{EFFECT_TYPE}",
                    "input": str(input_data.operation_data),
                },
            ) from e

    async def _execute_effect(self, data: {INPUT_MODEL}) -> {OUTPUT_MODEL}:
        """
        Execute the external effect.

        Args:
            data: Input data for the effect

        Returns:
            Result from external operation
        """
        # TODO: Implement your effect logic
        # Example API call:
        # response = await self.http_client.post(url, json=data.model_dump())
        # return {OUTPUT_MODEL}(result=response.json())
        raise NotImplementedError("Implement _execute_effect method")


# === TEST TEMPLATE ===

"""
# Save as: tests/unit/nodes/test_{node_name_lower}.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes import ModelEffectInput
from omnibase_core.enums.enum_effect_types import EnumEffectType
from your_module import {NODE_NAME}, {INPUT_MODEL}


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer()


@pytest.fixture
def node(container: ModelONEXContainer) -> {NODE_NAME}:
    return {NODE_NAME}(container)


@pytest.mark.unit
class Test{NODE_NAME}:
    async def test_process_success(self, node: {NODE_NAME}) -> None:
        # Mock the external service
        node._execute_effect = AsyncMock(return_value={OUTPUT_MODEL}(result="ok"))

        input_data = ModelEffectInput(
            operation_data={INPUT_MODEL}(data="test"),
            effect_type=EnumEffectType.{EFFECT_TYPE},
            operation_id=uuid4(),
        )
        result = await node.process(input_data)
        assert result.success is True

    async def test_process_handles_external_error(self, node: {NODE_NAME}) -> None:
        # Test error handling
        node._execute_effect = AsyncMock(side_effect=Exception("Service unavailable"))

        input_data = ModelEffectInput(
            operation_data={INPUT_MODEL}(data="test"),
            effect_type=EnumEffectType.{EFFECT_TYPE},
            operation_id=uuid4(),
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await node.process(input_data)
        assert "effect failed" in str(exc_info.value)
"""
```

### Validation Checklist

```yaml
checklist_id: "EFFECT_VALIDATION_V1"
items:
  - id: "E001"
    check: "Class inherits from NodeEffect"
    severity: "CRITICAL"

  - id: "E002"
    check: "super().__init__(container) is called"
    severity: "CRITICAL"

  - id: "E003"
    check: "Effect operations are async"
    severity: "HIGH"

  - id: "E004"
    check: "Error handling wraps external failures"
    severity: "HIGH"

  - id: "E005"
    check: "Resources obtained from container (DI)"
    severity: "HIGH"

  - id: "E006"
    check: "Effect type correctly specified"
    severity: "MEDIUM"
```

---

## NodeReducer Template

### Parameters Schema

```yaml
template_id: "REDUCER_NODE_V1"
parameters:
  NODE_NAME:
    type: string
    pattern: "Node[Domain][Purpose]Reducer"
    example: "NodeOrderStateReducer"
    required: true

  DOMAIN:
    type: string
    example: "Order"
    required: true

  FSM_STATES:
    type: array
    items: string
    example: ["idle", "processing", "completed", "failed"]
    required: true

  FSM_INITIAL_STATE:
    type: string
    example: "idle"
    required: true

  FSM_TERMINAL_STATES:
    type: array
    items: string
    example: ["completed", "failed"]
    required: true

  INPUT_MODEL:
    type: string
    example: "OrderEvent"
    required: true

  OUTPUT_MODEL:
    type: string
    example: "OrderState"
    required: true

  REDUCER_DESCRIPTION:
    type: string
    example: "Manages order lifecycle state transitions"
    required: true
```

### Generated Code Template

```python
"""
{NODE_NAME} - {REDUCER_DESCRIPTION}

Domain: {DOMAIN}
Type: REDUCER (FSM-driven state management)
Version: v0.4.0

FSM Configuration:
  States: {FSM_STATES}
  Initial: {FSM_INITIAL_STATE}
  Terminal: {FSM_TERMINAL_STATES}
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.nodes import NodeReducer, ModelReducerInput, ModelReducerOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_reducer_types import EnumReductionType


# === INPUT/OUTPUT MODELS ===

class {INPUT_MODEL}(BaseModel):
    """Input model for {NODE_NAME}."""
    trigger: str  # FSM trigger name
    data: Any


class {OUTPUT_MODEL}(BaseModel):
    """Output model for {NODE_NAME}."""
    current_state: str
    previous_state: str
    transition_success: bool


# === NODE IMPLEMENTATION ===

class {NODE_NAME}(NodeReducer[{INPUT_MODEL}, {OUTPUT_MODEL}], MixinFSMExecution):
    """
    {REDUCER_DESCRIPTION}

    This is a REDUCER node - FSM-driven state management.
    Uses MixinFSMExecution for declarative state transitions.

    FSM States: {FSM_STATES}
    Initial State: {FSM_INITIAL_STATE}
    Terminal States: {FSM_TERMINAL_STATES}

    Example:
        ```python
        container = ModelONEXContainer()
        node = {NODE_NAME}(container)

        # Set FSM contract
        node.fsm_contract = node.get_fsm_contract()

        input_data = ModelReducerInput(
            data={INPUT_MODEL}(trigger="start", data={}),
            reduction_type=EnumReductionType.AGGREGATE,
            metadata={{"trigger": "start"}},
        )
        result = await node.process(input_data)
        print(f"New state: {{result.metadata['fsm_state']}}")
        ```
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize {NODE_NAME}.

        Args:
            container: ONEX container for dependency injection
        """
        super().__init__(container)  # MANDATORY - do not remove

        # Set up FSM contract
        self.fsm_contract = self.get_fsm_contract()

    def get_fsm_contract(self) -> ModelFSMSubcontract:
        """
        Get FSM contract for this reducer.

        Returns:
            FSM subcontract defining states and transitions
        """
        return ModelFSMSubcontract(
            state_machine_name="{NODE_NAME}_FSM",
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    description="Initial idle state",
                ),
                ModelFSMStateDefinition(
                    state_name="processing",
                    description="Processing state",
                ),
                ModelFSMStateDefinition(
                    state_name="completed",
                    description="Successfully completed",
                ),
                ModelFSMStateDefinition(
                    state_name="failed",
                    description="Processing failed",
                ),
            ],
            initial_state="{FSM_INITIAL_STATE}",
            terminal_states={FSM_TERMINAL_STATES},
            error_states=["failed"],
            transitions=[
                ModelFSMStateTransition(
                    from_state="idle",
                    to_state="processing",
                    trigger="start",
                    description="Start processing",
                ),
                ModelFSMStateTransition(
                    from_state="processing",
                    to_state="completed",
                    trigger="complete",
                    description="Mark as completed",
                ),
                ModelFSMStateTransition(
                    from_state="processing",
                    to_state="failed",
                    trigger="fail",
                    description="Mark as failed",
                ),
                ModelFSMStateTransition(
                    from_state="failed",
                    to_state="idle",
                    trigger="reset",
                    description="Reset to retry",
                ),
            ],
            operations=[],
        )


# === FSM CONTRACT YAML ===

"""
# Save as: contracts/{domain}_reducer_contract.yaml

state_transitions:
  state_machine_name: "{NODE_NAME}_FSM"

  states:
    - state_name: "idle"
      description: "Initial idle state"
    - state_name: "processing"
      description: "Processing state"
    - state_name: "completed"
      description: "Successfully completed"
    - state_name: "failed"
      description: "Processing failed"

  initial_state: "{FSM_INITIAL_STATE}"
  terminal_states: {FSM_TERMINAL_STATES}
  error_states: ["failed"]

  transitions:
    - from_state: "idle"
      to_state: "processing"
      trigger: "start"
    - from_state: "processing"
      to_state: "completed"
      trigger: "complete"
    - from_state: "processing"
      to_state: "failed"
      trigger: "fail"
    - from_state: "failed"
      to_state: "idle"
      trigger: "reset"
"""


# === TEST TEMPLATE ===

"""
# Save as: tests/unit/nodes/test_{node_name_lower}.py

import pytest
from uuid import uuid4

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes import ModelReducerInput
from omnibase_core.enums.enum_reducer_types import EnumReductionType
from your_module import {NODE_NAME}, {INPUT_MODEL}


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer()


@pytest.fixture
def node(container: ModelONEXContainer) -> {NODE_NAME}:
    return {NODE_NAME}(container)


@pytest.mark.unit
class Test{NODE_NAME}:
    async def test_fsm_contract_loaded(self, node: {NODE_NAME}) -> None:
        assert node.fsm_contract is not None
        assert node.fsm_contract.initial_state == "{FSM_INITIAL_STATE}"

    async def test_state_transition(self, node: {NODE_NAME}) -> None:
        input_data = ModelReducerInput(
            data={INPUT_MODEL}(trigger="start", data={}),
            reduction_type=EnumReductionType.AGGREGATE,
            operation_id=uuid4(),
            metadata={{"trigger": "start"}},
        )
        result = await node.process(input_data)
        assert result.metadata["fsm_state"] == "processing"

    async def test_terminal_state(self, node: {NODE_NAME}) -> None:
        # Transition to terminal state
        pass
"""
```

### Validation Checklist

```yaml
checklist_id: "REDUCER_VALIDATION_V1"
items:
  - id: "R001"
    check: "Class inherits from NodeReducer"
    severity: "CRITICAL"

  - id: "R002"
    check: "MixinFSMExecution is included"
    severity: "CRITICAL"

  - id: "R003"
    check: "super().__init__(container) is called"
    severity: "CRITICAL"

  - id: "R004"
    check: "FSM contract defines all states"
    severity: "HIGH"

  - id: "R005"
    check: "Initial state is defined"
    severity: "HIGH"

  - id: "R006"
    check: "Terminal states are defined"
    severity: "HIGH"

  - id: "R007"
    check: "All transitions have from/to/trigger"
    severity: "HIGH"

  - id: "R008"
    check: "No direct I/O in reducer (use intents)"
    severity: "HIGH"
```

---

## NodeOrchestrator Template

### Parameters Schema

```yaml
template_id: "ORCHESTRATOR_NODE_V1"
parameters:
  NODE_NAME:
    type: string
    pattern: "Node[Domain][Purpose]Orchestrator"
    example: "NodeOrderFulfillmentOrchestrator"
    required: true

  DOMAIN:
    type: string
    example: "Order"
    required: true

  WORKFLOW_NAME:
    type: string
    example: "order_fulfillment_workflow"
    required: true

  EXECUTION_MODE:
    type: enum
    values: ["sequential", "parallel", "batch"]
    default: "sequential"
    required: true

  ORCHESTRATOR_DESCRIPTION:
    type: string
    example: "Coordinates order fulfillment workflow"
    required: true
```

### Generated Code Template

```python
"""
{NODE_NAME} - {ORCHESTRATOR_DESCRIPTION}

Domain: {DOMAIN}
Type: ORCHESTRATOR (workflow-driven coordination)
Version: v0.4.0

Workflow: {WORKFLOW_NAME}
Execution Mode: {EXECUTION_MODE}
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from omnibase_core.nodes import (
    NodeOrchestrator,
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.mixins.mixin_workflow_execution import MixinWorkflowExecution
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode


# === NODE IMPLEMENTATION ===

class {NODE_NAME}(NodeOrchestrator, MixinWorkflowExecution):
    """
    {ORCHESTRATOR_DESCRIPTION}

    This is an ORCHESTRATOR node - workflow-driven coordination.
    Uses MixinWorkflowExecution for declarative workflow management.

    Workflow: {WORKFLOW_NAME}
    Execution Mode: {EXECUTION_MODE}

    Example:
        ```python
        container = ModelONEXContainer()
        node = {NODE_NAME}(container)

        # Set workflow definition
        node.workflow_definition = node.get_workflow_definition()

        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            steps=[...],
        )
        result = await node.process(input_data)
        print(f"Status: {{result.execution_status}}")
        ```
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize {NODE_NAME}.

        Args:
            container: ONEX container for dependency injection
        """
        super().__init__(container)  # MANDATORY - do not remove

        # Set up workflow definition
        self.workflow_definition = self.get_workflow_definition()

    def get_workflow_definition(self) -> ModelWorkflowDefinition:
        """
        Get workflow definition for this orchestrator.

        Returns:
            Workflow definition with metadata and execution graph
        """
        from omnibase_core.models.contracts.subcontracts.model_execution_graph import (
            ModelExecutionGraph,
        )
        from omnibase_core.models.contracts.subcontracts.model_coordination_rules import (
            ModelCoordinationRules,
        )

        return ModelWorkflowDefinition(
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                workflow_name="{WORKFLOW_NAME}",
                description="{ORCHESTRATOR_DESCRIPTION}",
                execution_mode="{EXECUTION_MODE}",
                timeout_ms=60000,
                max_retries=3,
            ),
            execution_graph=ModelExecutionGraph(
                steps=[
                    # TODO: Define your workflow steps
                ],
            ),
            coordination_rules=ModelCoordinationRules(
                failure_recovery_strategy="retry_failed",
                max_parallel_steps=5,
                enable_checkpoints=True,
            ),
        )

    def create_workflow_steps(self) -> list[ModelWorkflowStep]:
        """
        Create workflow steps for execution.

        Returns:
            List of workflow steps
        """
        step_1_id = uuid4()
        step_2_id = uuid4()
        step_3_id = uuid4()

        return [
            ModelWorkflowStep(
                step_id=step_1_id,
                step_name="validate",
                step_type="compute",
                description="Validate input data",
                depends_on=[],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_2_id,
                step_name="process",
                step_type="effect",
                description="Process the request",
                depends_on=[step_1_id],
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step_3_id,
                step_name="notify",
                step_type="effect",
                description="Send notification",
                depends_on=[step_2_id],
                enabled=True,
            ),
        ]


# === WORKFLOW CONTRACT YAML ===

"""
# Save as: contracts/{domain}_orchestrator_contract.yaml

workflow_coordination:
  workflow_definition:
    workflow_metadata:
      workflow_name: "{WORKFLOW_NAME}"
      description: "{ORCHESTRATOR_DESCRIPTION}"
      execution_mode: "{EXECUTION_MODE}"
      timeout_ms: 60000
      max_retries: 3

    execution_graph:
      steps:
        - step_name: "validate"
          step_type: "compute"
          description: "Validate input data"
          depends_on: []
          timeout_ms: 5000

        - step_name: "process"
          step_type: "effect"
          description: "Process the request"
          depends_on: ["validate"]
          timeout_ms: 30000

        - step_name: "notify"
          step_type: "effect"
          description: "Send notification"
          depends_on: ["process"]
          timeout_ms: 10000

    coordination_rules:
      failure_recovery_strategy: "retry_failed"
      max_parallel_steps: 5
      enable_checkpoints: true
"""


# === TEST TEMPLATE ===

"""
# Save as: tests/unit/nodes/test_{node_name_lower}.py

import pytest
from uuid import uuid4

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes import ModelOrchestratorInput
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from your_module import {NODE_NAME}


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer()


@pytest.fixture
def node(container: ModelONEXContainer) -> {NODE_NAME}:
    return {NODE_NAME}(container)


@pytest.mark.unit
class Test{NODE_NAME}:
    async def test_workflow_definition_loaded(self, node: {NODE_NAME}) -> None:
        assert node.workflow_definition is not None
        assert node.workflow_definition.workflow_metadata.workflow_name == "{WORKFLOW_NAME}"

    async def test_create_workflow_steps(self, node: {NODE_NAME}) -> None:
        steps = node.create_workflow_steps()
        assert len(steps) > 0
        assert steps[0].step_name == "validate"

    async def test_process_workflow(self, node: {NODE_NAME}) -> None:
        steps = node.create_workflow_steps()
        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            steps=steps,
        )
        result = await node.process(input_data)
        assert result is not None
"""
```

### Validation Checklist

```yaml
checklist_id: "ORCHESTRATOR_VALIDATION_V1"
items:
  - id: "O001"
    check: "Class inherits from NodeOrchestrator"
    severity: "CRITICAL"

  - id: "O002"
    check: "MixinWorkflowExecution is included"
    severity: "CRITICAL"

  - id: "O003"
    check: "super().__init__(container) is called"
    severity: "CRITICAL"

  - id: "O004"
    check: "Workflow definition specifies execution_mode"
    severity: "HIGH"

  - id: "O005"
    check: "All steps have unique names"
    severity: "HIGH"

  - id: "O006"
    check: "Dependencies reference existing steps"
    severity: "HIGH"

  - id: "O007"
    check: "No circular dependencies in workflow"
    severity: "CRITICAL"

  - id: "O008"
    check: "Timeout values are reasonable"
    severity: "MEDIUM"
```

---

## Validation Checklists

### Universal Pre-Submission Checklist

```yaml
checklist_id: "UNIVERSAL_PRE_SUBMIT_V1"
items:
  - id: "U001"
    check: "File saved with correct name pattern"
    command: "ls -la src/*/nodes/"

  - id: "U002"
    check: "Imports resolve correctly"
    command: "poetry run python -c 'from {module} import {class}'"

  - id: "U003"
    check: "Type checking passes"
    command: "poetry run mypy {file_path}"

  - id: "U004"
    check: "Code formatting correct"
    command: "poetry run black --check {file_path}"

  - id: "U005"
    check: "Import sorting correct"
    command: "poetry run isort --check {file_path}"

  - id: "U006"
    check: "Unit tests pass"
    command: "poetry run pytest tests/unit/nodes/ -v"
```

### Quick Validation Commands

```bash
# Validate single node file
poetry run mypy src/path/to/node.py
poetry run black --check src/path/to/node.py
poetry run isort --check src/path/to/node.py

# Run node-specific tests
poetry run pytest tests/unit/nodes/test_your_node.py -v

# Full validation suite
poetry run pytest tests/unit/nodes/ --cov=src/omnibase_core/nodes
```

---

## Common Patterns

### Pattern 1: Container Service Injection

```python
def __init__(self, container: ModelONEXContainer) -> None:
    super().__init__(container)

    # Inject services from container
    self.logger = container.get_service("ProtocolLogger")
    self.config = container.get_service("ProtocolConfig")
    self.metrics = container.get_service("ProtocolMetrics")
```

### Pattern 2: Error Handling with Context

```python
try:
    result = await self._execute_operation(data)
except SpecificError as e:
    raise ModelOnexError(
        message=f"Operation failed: {e}",
        error_code=EnumCoreErrorCode.OPERATION_FAILED,
        context={
            "operation": "specific_operation",
            "input_id": str(data.id),
            "original_error": str(e),
        },
    ) from e
```

### Pattern 3: Metadata Propagation

```python
return ModelComputeOutput(
    result=result,
    operation_id=input_data.operation_id,
    metadata={
        **input_data.metadata,  # Propagate input metadata
        "node_type": self.__class__.__name__,
        "processing_time_ms": processing_time,
        "version": "v0.4.0",
    },
)
```

### Pattern 4: Async Factory for Validation

```python
@classmethod
async def create(
    cls,
    container: ModelONEXContainer,
    contract: ModelContract,
) -> "NodeMyType":
    """Async factory with validation."""
    instance = cls(container)
    instance.contract = contract

    # Validate contract
    errors = await instance.validate_contract()
    if errors:
        raise ModelOnexError(
            message=f"Contract validation failed: {errors}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    return instance
```

---

## Error Recovery

### Common Errors and Solutions

```yaml
errors:
  - error: "TypeError: __init__() missing 1 required positional argument: 'container'"
    cause: "Node instantiated without container"
    solution: "Always pass ModelONEXContainer to node constructor"
    example: "node = MyNode(ModelONEXContainer())"

  - error: "AttributeError: 'NoneType' object has no attribute 'xxx'"
    cause: "super().__init__(container) not called"
    solution: "Add super().__init__(container) as first line of __init__"

  - error: "ModelOnexError: FSM contract not loaded"
    cause: "Reducer used without FSM contract"
    solution: "Set node.fsm_contract before calling process()"

  - error: "ModelOnexError: Workflow definition not loaded"
    cause: "Orchestrator used without workflow definition"
    solution: "Set node.workflow_definition before calling process()"

  - error: "ImportError: cannot import name 'NodeXxx' from 'omnibase_core.nodes'"
    cause: "Using old import path"
    solution: "Use v0.4.0 imports: from omnibase_core.nodes import NodeXxx"
```

### Debug Commands

```bash
# Check if node can be imported
poetry run python -c "from omnibase_core.nodes import NodeCompute; print('OK')"

# Check if your node can be imported
poetry run python -c "from your_module import YourNode; print('OK')"

# Run with verbose logging
ONEX_LOG_LEVEL=DEBUG poetry run pytest tests/unit/nodes/test_your_node.py -v

# Check mypy errors in detail
poetry run mypy src/your_module/your_node.py --show-error-codes
```

---

## Related Documentation

- [What is a Node?](01_WHAT_IS_A_NODE.md)
- [Node Types](02_NODE_TYPES.md)
- [COMPUTE Node Tutorial](03_COMPUTE_NODE_TUTORIAL.md)
- [EFFECT Node Tutorial](04_EFFECT_NODE_TUTORIAL.md)
- [REDUCER Node Tutorial](05_REDUCER_NODE_TUTORIAL.md)
- [ORCHESTRATOR Node Tutorial](06_ORCHESTRATOR_NODE_TUTORIAL.md)
- [Patterns Catalog](07_PATTERNS_CATALOG.md)

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-05
**Status**: Complete
