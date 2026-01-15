"""
Contract-Driven State Reducer Mixin

Provides contract-driven state management capability to nodes by interpreting
state_transitions from contracts/contract_state_transitions.yaml subcontracts.

This mixin eliminates the need for separate ToolStateReducer files by adding
state transition capability directly to nodes.
"""

from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.enums.enum_transition_type import EnumTransitionType
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.core.model_generic_contract import ModelGenericContract
from omnibase_core.models.core.model_state_transition import ModelStateTransition
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.typed_dict_default_output_state import (
    TypedDictDefaultOutputState,
)
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model


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

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize contract state reducer mixin."""
        super().__init__(*args, **kwargs)

        # State transitions loaded from contract
        self._state_transitions: list[ModelStateTransition] | None = None
        self._transitions_loaded = False

    def _load_state_transitions(self) -> list[ModelStateTransition]:
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
                    LogLevel.WARNING,
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
                    LogLevel.INFO,
                    f"No state transitions file found: {transitions_path}",
                    {"tool_name": tool_name},
                )
                self._transitions_loaded = True
                return []

            # Load and validate contract using safe YAML loader
            contract: ModelGenericContract = load_and_validate_yaml_model(
                transitions_path, ModelGenericContract
            )

            # Extract state_transitions section
            # Performance optimization: use model_dump(include=...) to only serialize
            # the state_transitions field, avoiding full contract serialization overhead
            contract_dict = contract.model_dump(include={"state_transitions"})
            transitions_data = contract_dict.get("state_transitions", [])

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
                            "updates",
                            {},
                        ),
                        description=transition_data.get("description"),
                    )
                elif transition_type == "tool_based":
                    tool_config = transition_data.get("tool_config", {})
                    # Get tool_id from config or generate from tool_name
                    from uuid import NAMESPACE_DNS, UUID, uuid5

                    tool_id = tool_config.get("tool_id")
                    if tool_id is None and tool_config.get("tool_name"):
                        # Generate deterministic UUID from tool_name
                        tool_id = uuid5(NAMESPACE_DNS, tool_config["tool_name"])
                    elif isinstance(tool_id, str):
                        tool_id = UUID(tool_id)

                    transition = ModelStateTransition.create_tool_based(
                        name=transition_data["name"],
                        triggers=transition_data.get("triggers", []),
                        tool_id=tool_id,
                        tool_display_name=tool_config.get("tool_name"),
                        tool_params=tool_config.get("tool_params"),
                        description=transition_data.get("description"),
                    )
                else:
                    # For complex types like conditional, create full object
                    transition = ModelStateTransition(**transition_data)

                transitions.append(transition)

            emit_log_event(
                LogLevel.INFO,
                f"Loaded {len(transitions)} state transitions from contract",
                {
                    "tool_name": tool_name,
                    "transitions_file": str(transitions_path),
                },
            )

            self._state_transitions = transitions
            self._transitions_loaded = True
            return transitions

        except (
            Exception
        ) as e:  # fallback-ok: resilient loading returns empty list on failure
            tool_name = getattr(self, "node_name", "unknown_tool")
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to load state transitions: {e!s}",
                {"tool_name": tool_name, "error": str(e)},
            )
            self._transitions_loaded = True
            return []

    def process_action_with_transitions(self, input_state: object) -> object:
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

            # Safely access action attribute - handle None input_state
            action: object | None = (
                getattr(input_state, "action", None)
                if input_state is not None
                else None
            )

            # Safely access action_name - handle None, missing attribute, or empty string
            # Note: Empty strings are intentionally treated as "unknown_action" since
            # action_name must be a non-empty string per FSM model validation rules
            action_name: str = "unknown_action"
            if action is not None:
                raw_action_name: object = getattr(action, "action_name", None)
                if isinstance(raw_action_name, str) and raw_action_name:
                    action_name = raw_action_name

            emit_log_event(
                LogLevel.INFO,
                f"Processing action with contract transitions: {action_name}",
                {
                    "tool_name": tool_name,
                    "action": action_name,
                },
            )

            # Load state transitions from contract
            transitions = self._load_state_transitions()

            # Find transitions triggered by this action
            # Safely handle potentially None triggers (defensive check)
            applicable_transitions = [
                t
                for t in transitions
                if getattr(t, "triggers", None) and action_name in t.triggers
            ]

            # Apply transitions in priority order
            # Use getattr for safe priority access with default of 0
            applicable_transitions.sort(
                key=lambda t: getattr(t, "priority", 0), reverse=True
            )

            for transition in applicable_transitions:
                self._apply_transition(transition, input_state)

            # Delegate to main processing logic
            if hasattr(self, "_process_main_logic"):
                return self._process_main_logic(input_state)

            # Fallback: create basic success response
            return self._create_default_output_state(input_state)

        except (AttributeError, RuntimeError, ValueError) as e:
            tool_name = getattr(self, "node_name", "unknown_tool")
            emit_log_event(
                LogLevel.ERROR,
                f"Error in contract state processing: {e!s}",
                {"tool_name": tool_name, "error": str(e)},
            )
            msg = f"Contract state processing error: {e!s}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
            ) from e

    def _apply_transition(
        self, transition: ModelStateTransition, input_state: object
    ) -> None:
        """
        Apply a single state transition.

        Args:
            transition: The transition to apply
            input_state: Current input state
        """
        tool_name = getattr(self, "node_name", "unknown_tool")
        # Defensive access to transition attributes to prevent AttributeError
        transition_name = getattr(transition, "name", "unknown_transition")
        transition_type = getattr(transition, "transition_type", None)

        try:
            if transition_type == EnumTransitionType.SIMPLE:
                self._apply_simple_transition(transition, input_state)
            elif transition_type == EnumTransitionType.TOOL_BASED:
                self._apply_tool_based_transition(transition, input_state)
            elif transition_type == EnumTransitionType.CONDITIONAL:
                self._apply_conditional_transition(transition, input_state)
            else:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Unsupported transition type: {transition_type}",
                    {
                        "tool_name": tool_name,
                        "transition_name": transition_name,
                    },
                )
        except (AttributeError, RuntimeError, ValueError) as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to apply transition {transition_name}: {e!s}",
                {
                    "tool_name": tool_name,
                    "transition_name": transition_name,
                    "error": str(e),
                },
            )

    def _apply_simple_transition(
        self,
        transition: ModelStateTransition,
        input_state: object,
    ) -> None:
        """Apply simple field update transition."""
        # Simple transitions update state fields using template expressions
        # For now, just log the transition (actual field updates would require state management)
        tool_name = getattr(self, "node_name", "unknown_tool")
        transition_name = getattr(transition, "name", "unknown_transition")

        emit_log_event(
            LogLevel.DEBUG,
            f"Applied simple transition: {transition_name}",
            {
                "tool_name": tool_name,
                "transition_name": transition_name,
                "transition_type": "simple",
            },
        )

    def _apply_tool_based_transition(
        self,
        transition: ModelStateTransition,
        input_state: object,
    ) -> None:
        """Apply tool-based transition by delegating to specified tool."""
        tool_name = getattr(self, "node_name", "unknown_tool")
        transition_name = getattr(transition, "name", "unknown_transition")

        # Defensive access to tool_config to prevent AttributeError
        tool_config = getattr(transition, "tool_config", None)
        if not tool_config:
            return

        # Safely extract tool identifiers with fallback defaults
        tool_display_name = getattr(tool_config, "tool_display_name", None)
        tool_id = getattr(tool_config, "tool_id", None)
        target_tool_name = tool_display_name or str(tool_id) if tool_id else "unknown"

        emit_log_event(
            LogLevel.DEBUG,
            f"Applied tool-based transition: {transition_name} -> {target_tool_name}",
            {
                "tool_name": tool_name,
                "transition_name": transition_name,
                "transition_type": "tool_based",
                "target_tool": target_tool_name,
            },
        )

    def _apply_conditional_transition(
        self,
        transition: ModelStateTransition,
        input_state: object,
    ) -> None:
        """Apply conditional transition based on state conditions."""
        tool_name = getattr(self, "node_name", "unknown_tool")
        transition_name = getattr(transition, "name", "unknown_transition")

        emit_log_event(
            LogLevel.DEBUG,
            f"Applied conditional transition: {transition_name}",
            {
                "tool_name": tool_name,
                "transition_name": transition_name,
                "transition_type": "conditional",
            },
        )

    def _create_default_output_state(
        self, input_state: object
    ) -> TypedDictDefaultOutputState:
        """Create a default output state when no main tool is available."""
        # This is a fallback - each tool should implement proper processing
        # Basic response structure
        # Use ModelSemVer for version field instead of string literal
        default_version = ModelSemVer(major=1, minor=0, patch=0)
        return {
            "status": EnumOnexStatus.SUCCESS,
            "message": "Processed action via contract transitions",
            "version": getattr(input_state, "version", default_version),
        }

    def get_state_transitions(self) -> list[ModelStateTransition]:
        """Get loaded state transitions for introspection."""
        return self._load_state_transitions()

    def has_state_transitions(self) -> bool:
        """Check if this node has state transitions defined."""
        transitions = self._load_state_transitions()
        return len(transitions) > 0
