"""
NodeReducerDeclarative - Declarative reducer node for FSM-driven state management.

Enables reducer nodes to operate entirely from YAML contracts using FSM subcontracts.
Zero custom Python code required - all state transitions defined declaratively.

ZERO TOLERANCE: No Any types allowed in implementation.

Author: ONEX Framework Team
"""

from typing import Any, Generic, cast

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.model_reducer_input import ModelReducerInput, T_Input
from omnibase_core.models.model_reducer_output import ModelReducerOutput, T_Output

# Error messages
_ERR_FSM_CONTRACT_NOT_LOADED = "FSM contract not loaded"


class NodeReducerDeclarative(
    NodeCoreBase, MixinFSMExecution, Generic[T_Input, T_Output]
):
    """
    Declarative reducer node for FSM-driven state management.

    Generic type parameters:
        T_Input: Type of input data items (flows from ModelReducerInput[T_Input])
        T_Output: Type of output result (flows to ModelReducerOutput[T_Output])

    Type flow:
        Input data (list[T_Input]) → FSM processing → Output result (T_Output)
        In declarative mode, T_Output is typically the same as list[T_Input] or a transformation thereof.

    Enables creating reducer nodes entirely from YAML contracts without custom Python code.
    State transitions, conditions, and actions are all defined in FSM subcontracts.

    Pattern:
        class NodeMyReducer(NodeReducerDeclarative):
            # No custom code needed - driven entirely by YAML contract
            pass

    Example YAML Contract:
        ```yaml
        state_transitions:
          state_machine_name: metrics_aggregation_fsm
          initial_state: idle
          states:
            - state_name: idle
              entry_actions: []
              exit_actions: []
            - state_name: collecting
              entry_actions: ["start_collection"]
              exit_actions: ["finalize_collection"]
            - state_name: aggregating
              entry_actions: ["begin_aggregation"]
              exit_actions: []
            - state_name: completed
              is_terminal: true
          transitions:
            - from_state: idle
              to_state: collecting
              trigger: collect_metrics
              conditions:
                - expression: "data_sources min_length 1"
                  required: true
              actions:
                - action_name: "initialize_metrics"
                  action_type: "setup"
            - from_state: collecting
              to_state: aggregating
              trigger: start_aggregation
            - from_state: aggregating
              to_state: completed
              trigger: complete
          persistence_enabled: true
        ```

    Usage:
        ```python
        # Create node from container
        node = NodeMyReducer(container)

        # Initialize FSM state
        node.initialize_fsm_state(
            node.contract.state_transitions,
            context={"batch_size": 1000}
        )

        # Execute transition via process method
        result = await node.process(input_data)

        # Check current state
        current = node.get_current_fsm_state()
        ```

    Key Features:
        - Pure FSM pattern: (state, event) → (new_state, intents[])
        - All side effects emitted as intents for Effect nodes
        - Complete Pydantic validation for contracts
        - Zero custom code - entirely YAML-driven
        - State persistence when enabled
        - Entry/exit actions for states
        - Conditional transitions with expression evaluation
        - Wildcard transitions for error handling
        - Terminal state detection
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize declarative reducer node.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Load FSM contract from node contract
        # This assumes the node contract has a state_transitions field
        # If not present, FSM capabilities are not active
        self.fsm_contract: ModelFSMSubcontract | None = None

        # Try to load FSM contract if available in node contract
        if hasattr(self, "contract") and hasattr(self.contract, "state_transitions"):
            self.fsm_contract = self.contract.state_transitions

            # Auto-initialize FSM state if contract is present
            self.initialize_fsm_state(self.fsm_contract, context={})

    async def process(
        self,
        input_data: ModelReducerInput[T_Input],
    ) -> ModelReducerOutput[T_Output]:
        """
        Process input using FSM-driven state transitions.

        Pure FSM pattern: Executes transition, emits intents for side effects.

        Args:
            input_data: Reducer input with trigger and context

        Returns:
            Reducer output with new state and intents

        Raises:
            ModelOnexError: If FSM contract not loaded or transition fails

        Example:
            ```python
            input_data = ModelReducerInput(
                data=[...],
                reduction_type=EnumReductionType.AGGREGATE,
                metadata={
                    "trigger": "collect_metrics",
                    "data_sources": ["db1", "db2", "api"],
                }
            )

            result = await node.process(input_data)
            print(f"New state: {result.metadata['fsm_state']}")
            print(f"Intents emitted: {len(result.intents)}")
            ```
        """
        if not self.fsm_contract:
            raise ModelOnexError(
                message=_ERR_FSM_CONTRACT_NOT_LOADED,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Extract trigger from metadata (default to generic 'process' trigger)
        trigger = input_data.metadata.get("trigger", "process")

        # Build context from input data
        context: dict[str, Any] = {
            "input_data": input_data.data,
            "reduction_type": input_data.reduction_type.value,
            "operation_id": str(input_data.operation_id),
            **input_data.metadata,
        }

        # Execute FSM transition
        fsm_result = await self.execute_fsm_transition(
            self.fsm_contract,
            trigger=trigger,
            context=context,
        )

        # Create reducer output with FSM result
        output: ModelReducerOutput[T_Output] = ModelReducerOutput(
            result=cast(
                T_Output, input_data.data
            ),  # Cast to T_Output for declarative passthrough
            operation_id=input_data.operation_id,
            reduction_type=input_data.reduction_type,
            processing_time_ms=0,  # Computed by caller if needed
            items_processed=(
                len(input_data.data) if hasattr(input_data.data, "__len__") else 0
            ),
            conflicts_resolved=0,
            streaming_mode=input_data.streaming_mode,
            batches_processed=1,
            intents=fsm_result.intents,  # Emit FSM intents
            metadata={
                "fsm_state": fsm_result.new_state,
                "fsm_transition": fsm_result.transition_name or "none",
                "fsm_success": str(fsm_result.success),
                **input_data.metadata,
            },
        )

        return output

    async def validate_contract(self) -> list[str]:
        """
        Validate FSM contract for correctness.

        Returns:
            List of validation errors (empty if valid)

        Example:
            ```python
            errors = await node.validate_contract()
            if errors:
                print(f"Contract validation failed: {errors}")
            else:
                print("Contract is valid!")
            ```
        """
        if not self.fsm_contract:
            return ["FSM contract not loaded"]

        return await self.validate_fsm_contract(self.fsm_contract)

    def get_current_state(self) -> str | None:
        """
        Get current FSM state name.

        Returns:
            Current state name, or None if FSM not initialized

        Example:
            ```python
            state = node.get_current_state()
            if state == "completed":
                print("FSM has reached completion")
            ```
        """
        return self.get_current_fsm_state()

    def get_state_history(self) -> list[str]:
        """
        Get FSM state transition history.

        Returns:
            List of previous state names in chronological order

        Example:
            ```python
            history = node.get_state_history()
            print(f"State progression: {' -> '.join(history)}")
            ```
        """
        return self.get_fsm_state_history()

    def is_complete(self) -> bool:
        """
        Check if FSM has reached a terminal state.

        Returns:
            True if current state is terminal, False otherwise

        Example:
            ```python
            if node.is_complete():
                print("Workflow completed - no more transitions possible")
            ```
        """
        if not self.fsm_contract:
            return False
        return self.is_terminal_state(self.fsm_contract)
