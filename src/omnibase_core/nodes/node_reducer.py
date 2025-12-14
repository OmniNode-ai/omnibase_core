"""
NodeReducer - FSM-driven reducer node for state management.

Primary reducer implementation using FSM subcontracts for state transitions.
Zero custom Python code required - all state transitions defined declaratively.
"""

import time

# ONEX_EXCLUDE: any - Base node class requires Any for generic type parameters [OMN-203]
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput

# Error messages
_ERR_FSM_CONTRACT_NOT_LOADED = "FSM contract not loaded"


class NodeReducer[T_Input, T_Output](NodeCoreBase, MixinFSMExecution):
    """
    FSM-driven reducer node for state management.

    Generic type parameters:
        T_Input: Type of input data items (flows from ModelReducerInput[T_Input])
        T_Output: Type of output result (flows to ModelReducerOutput[T_Output])

    Type flow:
        Input data (list[T_Input]) -> FSM processing -> Output result (T_Output)
        T_Output is typically the same as list[T_Input] or a transformation thereof.

    Enables creating reducer nodes entirely from YAML contracts without custom Python code.
    State transitions, conditions, and actions are all defined in FSM subcontracts.

    Thread Safety:
        **MVP Design Decision**: NodeReducer uses mutable FSM state intentionally for
        the MVP phase to enable stateful workflow processing with minimal complexity.
        This is a documented trade-off.

        **Mutable State Components**:
        - `fsm_contract`: Loaded FSM subcontract reference
        - FSM execution state (via MixinFSMExecution):
          - Current state tracking
          - State transition history
          - Context accumulation

        **Current Limitations**:
        NodeReducer instances are NOT thread-safe. Concurrent access will corrupt
        FSM state.

        **Production Path**: Future versions will support stateless FSM execution
        with external state stores. See docs/architecture/MUTABLE_STATE_STRATEGY.md
        for the production improvement roadmap.

        **Mitigation**: Each thread should have its own NodeReducer instance.
        See docs/guides/THREADING.md for thread-local instance patterns.

    Pattern:
        class NodeMyReducer(NodeReducer):
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
            node.contract.state_machine,
            context={"batch_size": 1000}
        )

        # Execute transition via process method
        result = await node.process(input_data)

        # Check current state
        current = node.get_current_fsm_state()
        ```

    Key Features:
        - Pure FSM pattern: (state, event) -> (new_state, intents[])
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
        Initialize reducer node.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Load FSM contract from node contract
        # This assumes the node contract has a state_machine field
        # If not present, FSM capabilities are not active
        self.fsm_contract: ModelFSMSubcontract | None = None

        # Try to load FSM contract if available in node contract
        if hasattr(self, "contract") and hasattr(self.contract, "state_machine"):
            self.fsm_contract = self.contract.state_machine

            # Auto-initialize FSM state if contract is present
            if self.fsm_contract is not None:
                self.initialize_fsm_state(self.fsm_contract, context={})
        else:
            # FSM capabilities inactive - no state_machine in contract
            emit_log_event(
                LogLevel.DEBUG,
                f"FSM capabilities inactive for {self.__class__.__name__}: "
                "no state_machine found in contract",
                {"node_id": str(self.node_id), "node_type": self.__class__.__name__},
            )

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
            import logging

            from omnibase_core.models.reducer import ModelReducerInput
            from omnibase_core.enums.enum_reduction_type import EnumReductionType

            logger = logging.getLogger(__name__)

            input_data = ModelReducerInput(
                data=[...],
                reduction_type=EnumReductionType.AGGREGATE,
                metadata={
                    "trigger": "collect_metrics",
                    "data_sources": ["db1", "db2", "api"],
                }
            )

            result = await node.process(input_data)
            logger.debug("New state: %s", result.metadata['fsm_state'])
            logger.debug("Intents emitted: %d", len(result.intents))
            ```
        """
        if not self.fsm_contract:
            raise ModelOnexError(
                message=_ERR_FSM_CONTRACT_NOT_LOADED,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Extract trigger from metadata (default to generic 'process' trigger)
        trigger = input_data.metadata.get("trigger", "process")

        # Build context from input data - context contains serializable values
        context: SerializedDict = {
            "input_data": input_data.data,
            "reduction_type": input_data.reduction_type.value,
            "operation_id": str(input_data.operation_id),
            **input_data.metadata,
        }

        # Execute FSM transition with timing measurement
        start_time = time.perf_counter()
        fsm_result = await self.execute_fsm_transition(
            self.fsm_contract,
            trigger=trigger,
            context=context,
        )
        processing_time_ms = (time.perf_counter() - start_time) * 1000

        # Create reducer output with FSM result
        output: ModelReducerOutput[T_Output] = ModelReducerOutput(
            result=cast(
                "T_Output", input_data.data
            ),  # Cast to T_Output for passthrough
            operation_id=input_data.operation_id,
            reduction_type=input_data.reduction_type,
            processing_time_ms=processing_time_ms,
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
            import logging

            logger = logging.getLogger(__name__)

            errors = await node.validate_contract()
            if errors:
                logger.warning("Contract validation failed: %s", errors)
            else:
                logger.info("Contract is valid!")
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
            import logging

            logger = logging.getLogger(__name__)

            state = node.get_current_state()
            if state == "completed":
                logger.info("FSM has reached completion")
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
            import logging

            logger = logging.getLogger(__name__)

            history = node.get_state_history()
            logger.debug("State progression: %s", ' -> '.join(history))
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
            import logging

            logger = logging.getLogger(__name__)

            if node.is_complete():
                logger.info("Workflow completed - no more transitions possible")
            ```
        """
        if not self.fsm_contract:
            return False
        return self.is_terminal_state(self.fsm_contract)
