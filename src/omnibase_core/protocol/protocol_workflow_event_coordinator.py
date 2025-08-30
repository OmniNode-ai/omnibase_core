"""
Protocol interface for Workflow event coordinator tools.

This protocol defines the interface for tools that coordinate event-driven
workflow execution within Workflow scenarios.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol

from omnibase_core.model.core.model_onex_result import ModelOnexResult
from omnibase_core.model.workflow.model_workflow_event import \
    ModelWorkflowEvent

if TYPE_CHECKING:
    from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus
    from omnibase_core.protocol.protocol_node_registry import \
        ProtocolNodeRegistry


class ProtocolWorkflowEventCoordinator(Protocol):
    """
    Protocol for Workflow event coordinator tools that manage event-driven
    workflow coordination.

    These tools handle the coordination of events, triggers, and state
    transitions within Workflow execution workflows.
    """

    def set_registry(self, registry: "ProtocolNodeRegistry") -> None:
        """
        Set the registry for accessing other tools.

        Args:
            registry: The registry containing other tools and dependencies
        """
        ...

    def set_event_bus(self, event_bus: "ProtocolEventBus") -> None:
        """
        Set the event bus for publishing and subscribing to events.

        Args:
            event_bus: The event bus instance
        """
        ...

    def run(self, input_state: Dict[str, Any]) -> ModelOnexResult:
        """
        Run the Workflow event coordinator with the provided input state.

        Args:
            input_state: Input state containing action and parameters

        Returns:
            Result of event coordination
        """
        ...

    def coordinate_events(
        self,
        workflow_events: List[ModelWorkflowEvent],
        scenario_id: str,
        correlation_id: str,
    ) -> ModelOnexResult:
        """
        Coordinate a list of Workflow events.

        Args:
            workflow_events: List of Workflow events to coordinate
            scenario_id: ID of the scenario
            correlation_id: Correlation ID for tracking

        Returns:
            Result of event coordination
        """
        ...

    def publish_workflow_event(
        self, event: ModelWorkflowEvent, correlation_id: str
    ) -> ModelOnexResult:
        """
        Publish a Workflow event to the event bus.

        Args:
            event: Workflow event to publish
            correlation_id: Correlation ID for tracking

        Returns:
            Result of event publishing
        """
        ...

    def subscribe_to_events(
        self, event_types: List[str], callback: callable, correlation_id: str
    ) -> ModelOnexResult:
        """
        Subscribe to specific event types.

        Args:
            event_types: List of event types to subscribe to
            callback: Callback function to handle events
            correlation_id: Correlation ID for tracking

        Returns:
            Result of event subscription
        """
        ...

    def get_event_status(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a specific event.

        Args:
            event_id: ID of the event

        Returns:
            Event status information or None if not found
        """
        ...

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for the Workflow event coordinator.

        Returns:
            Health check result with status and capabilities
        """
        ...
