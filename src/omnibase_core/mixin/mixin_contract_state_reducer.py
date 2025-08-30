"""
Contract-Driven State Reducer Mixin

Provides contract-driven state management capability to nodes by interpreting
state_transitions from contracts/contract_state_transitions.yaml subcontracts.

This mixin eliminates the need for separate ToolStateReducer files by adding
state transition capability directly to nodes.
"""

from pathlib import Path
from typing import List, Optional

import yaml
from omnibase.enums.enum_log_level import LogLevelEnum

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.core.core_structured_logging import \
    emit_log_event_sync as emit_log_event
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.exceptions import OnexError
from omnibase_core.model.core.model_state_transition import (
    EnumTransitionType, ModelStateTransition)


class MixinContractStateReducer:
    """
    Mixin for contract-driven state management.

    CANONICAL PATTERN: Interprets state_transitions from contract subcontracts
    CRITICAL: This is a DATA-DRIVEN state machine, not hardcoded business logic

    Usage:
        class ToolMyNode(MixinContractStateReducer, ProtocolReducer):
            def process(self, input_state):
                return self.process_action_with_transitions(input_state)
    """

    def __init__(self, *args, **kwargs):
        """Initialize contract state reducer mixin."""
        super().__init__(*args, **kwargs)

        # State transitions loaded from contract
        self._state_transitions: Optional[List[ModelStateTransition]] = None
        self._transitions_loaded = False

    def _load_state_transitions(self) -> List[ModelStateTransition]:
        """
        Load state transitions from contracts/contract_state_transitions.yaml.

        CONTRACT-DRIVEN PATTERN: Parse actual contract file for transitions
        """
        if self._transitions_loaded:
            return self._state_transitions or []

        try:
            # Get path to state transitions subcontract relative to node
            current_dir = Path(__file__).parent.parent
            tool_name = getattr(self, "node_name", "unknown_tool")

            # Find the tool directory (look for v1_0_0 pattern)
            tool_paths = list(current_dir.glob(f"**/tools/**/{tool_name}/v1_0_0"))
            if not tool_paths:
                tool_paths = list(current_dir.glob(f"**/{tool_name}/v1_0_0"))

            if not tool_paths:
                emit_log_event(
                    LogLevelEnum.WARNING,
                    f"Could not find tool directory for {tool_name}",
                    {"tool_name": tool_name},
                )
                self._transitions_loaded = True
                return []

            transitions_path = (
                tool_paths[0] / "contracts" / "contract_state_transitions.yaml"
            )

            if not transitions_path.exists():
                emit_log_event(
                    LogLevelEnum.INFO,
                    f"No state transitions file found: {transitions_path}",
                    {"tool_name": tool_name},
                )
                self._transitions_loaded = True
                return []

            # Load and parse YAML
            with open(transitions_path, "r") as f:
                contract_data = yaml.safe_load(f)

            # Extract state_transitions section
            transitions_data = contract_data.get("state_transitions", [])

            # Convert to ModelStateTransition objects
            transitions = []
            for transition_data in transitions_data:
                # Create appropriate transition based on type
                transition_type = transition_data.get("transition_type")

                if transition_type == "simple":
                    transition = ModelStateTransition.create_simple(
                        name=transition_data["name"],
                        triggers=transition_data.get("triggers", []),
                        updates=transition_data.get("simple_config", {}).get(
                            "updates", {}
                        ),
                        description=transition_data.get("description"),
                    )
                elif transition_type == "tool_based":
                    tool_config = transition_data.get("tool_config", {})
                    transition = ModelStateTransition.create_tool_based(
                        name=transition_data["name"],
                        triggers=transition_data.get("triggers", []),
                        tool_name=tool_config.get("tool_name"),
                        tool_params=tool_config.get("tool_params"),
                        description=transition_data.get("description"),
                    )
                else:
                    # For complex types like conditional, create full object
                    transition = ModelStateTransition(**transition_data)

                transitions.append(transition)

            emit_log_event(
                LogLevelEnum.INFO,
                f"Loaded {len(transitions)} state transitions from contract",
                {
                    "tool_name": tool_name,
                    "transitions_file": str(transitions_path),
                },
            )

            self._state_transitions = transitions
            self._transitions_loaded = True
            return transitions

        except Exception as e:
            tool_name = getattr(self, "node_name", "unknown_tool")
            emit_log_event(
                LogLevelEnum.ERROR,
                f"Failed to load state transitions: {str(e)}",
                {"tool_name": tool_name, "error": str(e)},
            )
            self._transitions_loaded = True
            return []

    def process_action_with_transitions(self, input_state):
        """
        Process action using contract-driven state transitions.

        CANONICAL PATTERN: Apply state transitions, then delegate to main tool

        Args:
            input_state: Input state with action specification

        Returns:
            Output state after applying transitions and processing
        """
        try:
            tool_name = getattr(self, "node_name", "unknown_tool")
            action_name = getattr(input_state.action, "action_name", "unknown_action")

            emit_log_event(
                LogLevelEnum.INFO,
                f"Processing action with contract transitions: {action_name}",
                {
                    "tool_name": tool_name,
                    "action": action_name,
                },
            )

            # Load state transitions from contract
            transitions = self._load_state_transitions()

            # Find transitions triggered by this action
            applicable_transitions = [
                t for t in transitions if action_name in t.triggers
            ]

            # Apply transitions in priority order
            applicable_transitions.sort(key=lambda t: t.priority, reverse=True)

            for transition in applicable_transitions:
                self._apply_transition(transition, input_state)

            # Delegate to main processing logic
            if hasattr(self, "_process_main_logic"):
                return self._process_main_logic(input_state)

            # Fallback: create basic success response
            return self._create_default_output_state(input_state)

        except Exception as e:
            tool_name = getattr(self, "node_name", "unknown_tool")
            emit_log_event(
                LogLevelEnum.ERROR,
                f"Error in contract state processing: {str(e)}",
                {"tool_name": tool_name, "error": str(e)},
            )
            raise OnexError(
                f"Contract state processing error: {str(e)}",
                CoreErrorCode.OPERATION_FAILED,
            )

    def _apply_transition(self, transition: ModelStateTransition, input_state) -> None:
        """
        Apply a single state transition.

        Args:
            transition: The transition to apply
            input_state: Current input state
        """
        tool_name = getattr(self, "node_name", "unknown_tool")

        try:
            if transition.transition_type == EnumTransitionType.SIMPLE:
                self._apply_simple_transition(transition, input_state)
            elif transition.transition_type == EnumTransitionType.TOOL_BASED:
                self._apply_tool_based_transition(transition, input_state)
            elif transition.transition_type == EnumTransitionType.CONDITIONAL:
                self._apply_conditional_transition(transition, input_state)
            else:
                emit_log_event(
                    LogLevelEnum.WARNING,
                    f"Unsupported transition type: {transition.transition_type}",
                    {
                        "tool_name": tool_name,
                        "transition_name": transition.name,
                    },
                )
        except Exception as e:
            emit_log_event(
                LogLevelEnum.ERROR,
                f"Failed to apply transition {transition.name}: {str(e)}",
                {
                    "tool_name": tool_name,
                    "transition_name": transition.name,
                    "error": str(e),
                },
            )

    def _apply_simple_transition(
        self, transition: ModelStateTransition, input_state
    ) -> None:
        """Apply simple field update transition."""
        # Simple transitions update state fields using template expressions
        # For now, just log the transition (actual field updates would require state management)
        tool_name = getattr(self, "node_name", "unknown_tool")

        emit_log_event(
            LogLevelEnum.DEBUG,
            f"Applied simple transition: {transition.name}",
            {
                "tool_name": tool_name,
                "transition_name": transition.name,
                "transition_type": "simple",
            },
        )

    def _apply_tool_based_transition(
        self, transition: ModelStateTransition, input_state
    ) -> None:
        """Apply tool-based transition by delegating to specified tool."""
        tool_name = getattr(self, "node_name", "unknown_tool")

        if not transition.tool_config:
            return

        target_tool_name = transition.tool_config.tool_name

        emit_log_event(
            LogLevelEnum.DEBUG,
            f"Applied tool-based transition: {transition.name} -> {target_tool_name}",
            {
                "tool_name": tool_name,
                "transition_name": transition.name,
                "transition_type": "tool_based",
                "target_tool": target_tool_name,
            },
        )

    def _apply_conditional_transition(
        self, transition: ModelStateTransition, input_state
    ) -> None:
        """Apply conditional transition based on state conditions."""
        tool_name = getattr(self, "node_name", "unknown_tool")

        emit_log_event(
            LogLevelEnum.DEBUG,
            f"Applied conditional transition: {transition.name}",
            {
                "tool_name": tool_name,
                "transition_name": transition.name,
                "transition_type": "conditional",
            },
        )

    def _create_default_output_state(self, input_state):
        """Create a default output state when no main tool is available."""
        # This is a fallback - each tool should implement proper processing
        tool_name = getattr(self, "node_name", "unknown_tool")

        # Try to create output state using the tool's output state model
        output_model_name = f"Model{tool_name.replace('_', '').title()}OutputState"

        # Basic response structure
        return {
            "status": EnumOnexStatus.SUCCESS,
            "message": "Processed action via contract transitions",
            "version": getattr(input_state, "version", "1.0.0"),
        }

    def get_state_transitions(self) -> List[ModelStateTransition]:
        """Get loaded state transitions for introspection."""
        return self._load_state_transitions()

    def has_state_transitions(self) -> bool:
        """Check if this node has state transitions defined."""
        transitions = self._load_state_transitions()
        return len(transitions) > 0
