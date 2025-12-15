"""
NodeReducer - FSM-driven reducer node for state management.

Primary reducer implementation using FSM subcontracts for state transitions.
Zero custom Python code required - all state transitions defined declaratively.
"""

import time
from datetime import UTC, datetime

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
from omnibase_core.models.fsm import ModelFSMStateSnapshot
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput

# Error messages
_ERR_FSM_CONTRACT_NOT_LOADED = "FSM contract not loaded"
_ERR_INVALID_SNAPSHOT_STATE = (
    "Invalid FSM snapshot: state '{state}' is not defined in FSM contract"
)
_ERR_INVALID_HISTORY_STATE = (
    "Invalid FSM snapshot: history contains invalid state '{state}'"
)
_ERR_FUTURE_TIMESTAMP = (
    "Invalid FSM snapshot: timestamp {snapshot_time} is in the future "
    "(current: {current_time}, difference: {difference_seconds:.3f}s)"
)


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
        NodeReducer instances are NOT thread-safe due to mutable FSM state:
        - Current state tracking
        - State transition history
        - Context accumulation

        Each thread should have its own NodeReducer instance, or implement
        explicit synchronization. See docs/guides/THREADING.md for patterns.

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

    def snapshot_state(self) -> ModelFSMStateSnapshot | None:
        """
        Return current FSM state as a strongly-typed snapshot model.

        Returns the current FSM state as an immutable ``ModelFSMStateSnapshot``
        that can be serialized and restored later. This enables FSM replay,
        debugging, and state persistence with full type safety.

        For JSON serialization use cases where a plain dict is preferred,
        use ``get_state_snapshot()`` instead.

        Returns:
            ModelFSMStateSnapshot if FSM is initialized, None otherwise.

        Example:
            ```python
            import logging

            logger = logging.getLogger(__name__)

            snapshot = node.snapshot_state()
            if snapshot:
                logger.info("Current state: %s", snapshot.current_state)
                logger.debug("Context: %s", snapshot.context)
                logger.debug("History: %s", snapshot.history)

                # Can be restored later
                node.restore_state(snapshot)
            else:
                logger.warning("FSM not initialized")
            ```

        See Also:
            get_state_snapshot: Returns dict[str, object] for JSON serialization.
            restore_state: Restores state from a ModelFSMStateSnapshot.
        """
        return self._fsm_state

    def _validate_fsm_snapshot(
        self,
        snapshot: ModelFSMStateSnapshot,
        contract: ModelFSMSubcontract,
    ) -> None:
        """
        Validate FSM snapshot against the loaded contract.

        Ensures the restored snapshot represents a valid FSM state:
        - Current state must exist in contract state definitions
        - All history states must exist in contract state definitions
        - Timestamp sanity check (not in the future)

        Args:
            snapshot: FSM state snapshot to validate
            contract: FSM contract defining valid states

        Raises:
            ModelOnexError: If snapshot state is invalid or not in contract

        Note:
            This validation prevents injection of impossible states during
            restore operations, ensuring FSM consistency and integrity.
        """
        # Build set of valid state names from contract
        valid_states: set[str] = {state.state_name for state in contract.states}

        # Validate current state exists in contract
        if snapshot.current_state not in valid_states:
            raise ModelOnexError(
                message=_ERR_INVALID_SNAPSHOT_STATE.format(
                    state=snapshot.current_state
                ),
                error_code=EnumCoreErrorCode.INVALID_STATE,
                context={
                    "snapshot_state": snapshot.current_state,
                    "valid_states": sorted(valid_states),
                    "fsm_name": contract.state_machine_name,
                },
            )

        # Validate all history states exist in contract
        for history_state in snapshot.history:
            if history_state not in valid_states:
                raise ModelOnexError(
                    message=_ERR_INVALID_HISTORY_STATE.format(state=history_state),
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                    context={
                        "invalid_history_state": history_state,
                        "valid_states": sorted(valid_states),
                        "fsm_name": contract.state_machine_name,
                    },
                )

        # Timestamp sanity check: snapshot context may contain a timestamp
        # Check if context has a 'created_at' or 'timestamp' field
        timestamp_keys = ["created_at", "timestamp", "snapshot_time"]
        for key in timestamp_keys:
            if key in snapshot.context:
                timestamp_value = snapshot.context[key]
                # Handle both datetime objects and ISO strings
                if isinstance(timestamp_value, datetime):
                    snapshot_time = timestamp_value
                elif isinstance(timestamp_value, str):
                    try:
                        snapshot_time = datetime.fromisoformat(
                            timestamp_value.replace("Z", "+00:00")
                        )
                    except ValueError:
                        # Skip validation if timestamp format is unrecognized
                        continue
                else:
                    continue

                # Ensure timezone-aware comparison
                now = datetime.now(UTC)
                if snapshot_time.tzinfo is None:
                    snapshot_time = snapshot_time.replace(tzinfo=UTC)

                if snapshot_time > now:
                    difference_seconds = (snapshot_time - now).total_seconds()
                    raise ModelOnexError(
                        message=_ERR_FUTURE_TIMESTAMP.format(
                            snapshot_time=snapshot_time.isoformat(),
                            current_time=now.isoformat(),
                            difference_seconds=difference_seconds,
                        ),
                        error_code=EnumCoreErrorCode.INVALID_STATE,
                        context={
                            "snapshot_timestamp": snapshot_time.isoformat(),
                            "current_time": now.isoformat(),
                            "difference_seconds": difference_seconds,
                            "fsm_name": contract.state_machine_name,
                        },
                    )

    def restore_state(self, snapshot: ModelFSMStateSnapshot) -> None:
        """
        Restore FSM state from a snapshot.

        Replaces the current FSM state with the provided snapshot after
        validating that the snapshot represents a valid FSM state according
        to the loaded contract. Useful for resuming workflows from persisted
        state or implementing checkpoint/recovery patterns.

        Validation performed:
            - Current state exists in FSM contract state definitions
            - All history states exist in FSM contract state definitions
            - Timestamp is not in the future (sanity check)

        Args:
            snapshot: FSM state snapshot to restore

        Raises:
            ModelOnexError: If FSM contract not loaded or snapshot state invalid

        Example:
            ```python
            import logging

            logger = logging.getLogger(__name__)

            # Save state before risky operation
            saved_snapshot = node.snapshot_state()

            try:
                result = await node.process(input_data)
            except Exception:
                # Restore to previous state on failure
                if saved_snapshot:
                    node.restore_state(saved_snapshot)
                    logger.info("Restored FSM state to: %s", saved_snapshot.current_state)
                raise
            ```
        """
        if not self.fsm_contract:
            raise ModelOnexError(
                message=_ERR_FSM_CONTRACT_NOT_LOADED,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Validate snapshot against contract before restoring
        self._validate_fsm_snapshot(snapshot, self.fsm_contract)

        self._fsm_state = snapshot

    def get_state_snapshot(self) -> dict[str, object] | None:
        """
        Return FSM state as a JSON-serializable dictionary.

        Converts the current FSM state snapshot to a plain dictionary
        suitable for JSON serialization, API responses, or external storage
        systems that require dict format.

        For strongly-typed access to FSM state, use ``snapshot_state()``
        instead, which returns the ``ModelFSMStateSnapshot`` model directly.

        Returns:
            dict[str, object] with FSM state data that can be serialized
            to JSON, or None if FSM not initialized.

        Example:
            ```python
            import json
            import logging

            logger = logging.getLogger(__name__)

            snapshot_dict = node.get_state_snapshot()
            if snapshot_dict:
                # Direct JSON serialization
                json_str = json.dumps(snapshot_dict, default=str)
                logger.debug("FSM state JSON: %s", json_str)

                # Access fields as dict keys
                logger.info("Current state: %s", snapshot_dict["current_state"])
                logger.info("History: %d transitions", len(snapshot_dict["history"]))

                # For restoration, use snapshot_state() to get the model
            ```

        See Also:
            snapshot_state: Returns strongly-typed ModelFSMStateSnapshot.
            restore_state: Restores state from a ModelFSMStateSnapshot.
        """
        if self._fsm_state is None:
            return None
        return self._fsm_state.model_dump()
