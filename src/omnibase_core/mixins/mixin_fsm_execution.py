"""
Mixin for FSM execution from YAML contracts.

Enables nodes to execute state machines declaratively from ModelFSMSubcontract.

Typing: Strongly typed with strategic object usage for mixin kwargs and runtime context.
"""

from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.types.type_fsm_context import FSMContextType
from omnibase_core.utils.util_fsm_executor import (
    FSMState,
    FSMTransitionResult,
    execute_transition,
    get_initial_state,
    validate_fsm_contract,
)


class MixinFSMExecution:
    """
    Mixin providing FSM execution capabilities from YAML contracts.

    Enables reducer nodes to execute state machines declaratively without
    custom code. State transitions are driven entirely by FSM subcontract.

    Usage:
        class NodeMyReducer(NodeReducer, MixinFSMExecution):
            # No custom FSM code needed - driven by YAML contract
            pass

    Pattern:
        This mixin maintains minimal state (current FSM state only).
        All transition logic is delegated to pure functions in utils/util_fsm_executor.py.
        Intents are emitted for all side effects (pure FSM pattern).
    """

    def __init__(self, **kwargs: object) -> None:
        """
        Initialize FSM execution mixin.

        Args:
            **kwargs: Passed to super().__init__()
        """
        super().__init__(**kwargs)

        # Minimal state: current FSM state snapshot
        # This is the ONLY mutable state in the mixin
        self._fsm_state: FSMState | None = None

    async def execute_fsm_transition(
        self,
        fsm_contract: ModelFSMSubcontract,
        trigger: str,
        context: FSMContextType,
    ) -> FSMTransitionResult:
        """
        Execute FSM transition from YAML contract.

        Pure function delegation: delegates to utils/util_fsm_executor.execute_transition()
        which returns (new_state, intents) without side effects.

        Args:
            fsm_contract: FSM subcontract from node contract
            trigger: Event triggering the transition
            context: Execution context data

        Returns:
            FSMTransitionResult with new state and intents

        Example:
            result = await self.execute_fsm_transition(
                self.contract.state_machine,
                trigger="collect_metrics",
                context={"data_sources": [...]},
            )

            # Check result
            if result.success:
                print(f"Transitioned to: {result.new_state}")
                # Process intents (emitted to Effect node)
                for intent in result.intents:
                    print(f"Intent: {intent.intent_type}")
        """
        # Get current state (or use initial state)
        current_state = (
            self._fsm_state.current_state
            if self._fsm_state
            else fsm_contract.initial_state
        )

        # Execute transition using pure function from utils
        result = await execute_transition(
            fsm_contract,
            current_state,
            trigger,
            context,
        )

        # Update internal state if successful
        if result.success:
            # Create new FSMState with updated current state and history
            # Use list spread to maintain immutability by creating new list
            previous_history = self._fsm_state.history if self._fsm_state else []
            new_history = [*previous_history, result.old_state]
            self._fsm_state = FSMState(
                current_state=result.new_state,
                context=context,
                history=new_history,
            )

        return result

    async def validate_fsm_contract(
        self, fsm_contract: ModelFSMSubcontract
    ) -> list[str]:
        """
        Validate FSM contract for correctness.

        Pure function delegation: delegates to utils/util_fsm_executor.validate_fsm_contract()

        Args:
            fsm_contract: FSM subcontract to validate

        Returns:
            List of validation errors (empty if valid)

        Example:
            errors = await self.validate_fsm_contract(
                self.contract.state_machine
            )

            if errors:
                print(f"FSM validation failed: {errors}")
            else:
                print("FSM contract is valid!")
        """
        return await validate_fsm_contract(fsm_contract)

    def get_current_fsm_state(self) -> str | None:
        """
        Get current FSM state name.

        Returns:
            Current state name, or None if FSM not initialized

        Example:
            state = self.get_current_fsm_state()
            if state == "collecting":
                print("FSM is collecting data")
        """
        return self._fsm_state.current_state if self._fsm_state else None

    def get_fsm_state_history(self) -> list[str]:
        """
        Get FSM state transition history.

        Returns:
            List of previous state names in chronological order

        Example:
            history = self.get_fsm_state_history()
            print(f"State history: {' -> '.join(history)}")
        """
        return self._fsm_state.history if self._fsm_state else []

    def reset_fsm_state(self, fsm_contract: ModelFSMSubcontract) -> None:
        """
        Reset FSM to initial state.

        Args:
            fsm_contract: FSM subcontract defining initial state

        Example:
            # Reset to clean initial state
            self.reset_fsm_state(self.contract.state_machine)
            assert self.get_current_fsm_state() == "idle"
        """
        self._fsm_state = get_initial_state(fsm_contract)

    def initialize_fsm_state(
        self, fsm_contract: ModelFSMSubcontract, context: FSMContextType | None = None
    ) -> None:
        """
        Initialize FSM state with optional context.

        Args:
            fsm_contract: FSM subcontract defining initial state
            context: Optional initial context data

        Example:
            # Initialize with context
            self.initialize_fsm_state(
                self.contract.state_machine,
                context={"batch_size": 1000}
            )
        """
        self._fsm_state = FSMState(
            current_state=fsm_contract.initial_state,
            context=context or {},
            history=[],
        )

    def is_terminal_state(self, fsm_contract: ModelFSMSubcontract) -> bool:
        """
        Check if current state is a terminal state.

        Args:
            fsm_contract: FSM subcontract with terminal state definitions

        Returns:
            True if current state is terminal, False otherwise

        Example:
            if self.is_terminal_state(self.contract.state_machine):
                print("FSM has reached terminal state")
                # No more transitions possible
        """
        if not self._fsm_state:
            return False

        current_state = self._fsm_state.current_state

        # Check if current state is in terminal_states list
        if current_state in fsm_contract.terminal_states:
            return True

        # Check state definition for is_terminal flag
        for state in fsm_contract.states:
            if state.state_name == current_state:
                return state.is_terminal

        return False
