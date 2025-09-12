"""
Protocol for Event Bus Service Operations.

This protocol defines the interface for centralized event bus operations
extracted from ModelNodeBase as part of NODEBASE-001 Phase 5 deconstruction.

Author: ONEX Framework Team
"""

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus


@runtime_checkable
class ProtocolEventBusService(Protocol):
    """
    Protocol for Event Bus Service operations.

    This protocol ensures duck typing compatibility for event bus management,
    event emission, pattern handling, and introspection publishing.

    Following ONEX protocol patterns for service abstraction and dependency injection.
    """

    def initialize_event_bus(
        self,
        event_bus: ProtocolEventBus | None = None,
        auto_resolve: bool = True,
    ) -> ProtocolEventBus:
        """
        Initialize or auto-resolve event bus connection.

        Args:
            event_bus: Optional pre-configured event bus instance
            auto_resolve: Whether to auto-resolve from environment if none provided

        Returns:
            ProtocolEventBus: Initialized event bus instance
        """
        ...

    def emit_node_start(
        self,
        node_id: str,
        node_name: str,
        correlation_id: UUID,
        metadata: dict,
    ) -> bool:
        """
        Emit NODE_START event for operation lifecycle tracking.

        Args:
            node_id: Node identifier
            node_name: Human-readable node name
            correlation_id: Operation correlation ID
            metadata: Additional event metadata

        Returns:
            bool: True if event was emitted successfully
        """
        ...

    def emit_node_success(
        self,
        node_id: str,
        node_name: str,
        correlation_id: UUID,
        result: object,
        metadata: dict,
    ) -> bool:
        """
        Emit NODE_SUCCESS event for successful operation completion.

        Args:
            node_id: Node identifier
            node_name: Human-readable node name
            correlation_id: Operation correlation ID
            result: Operation result object
            metadata: Additional event metadata

        Returns:
            bool: True if event was emitted successfully
        """
        ...

    def emit_node_failure(
        self,
        node_id: str,
        node_name: str,
        correlation_id: UUID,
        error: Exception,
        metadata: dict,
    ) -> bool:
        """
        Emit NODE_FAILURE event for operation failure tracking.

        Args:
            node_id: Node identifier
            node_name: Human-readable node name
            correlation_id: Operation correlation ID
            error: Exception that caused the failure
            metadata: Additional event metadata

        Returns:
            bool: True if event was emitted successfully
        """
        ...

    def publish_introspection_event(
        self,
        node_id: str,
        node_name: str,
        version: str,
        actions: list[str],
        protocols: list[str],
        metadata: dict,
        correlation_id: UUID,
    ) -> bool:
        """
        Publish introspection event for service discovery.

        Args:
            node_id: Node identifier
            node_name: Human-readable node name
            version: Node version
            actions: Supported actions/capabilities
            protocols: Supported protocols
            metadata: Node metadata
            correlation_id: Operation correlation ID

        Returns:
            bool: True if event was published successfully
        """
        ...

    def get_event_patterns_from_contract(
        self,
        contract_content: object,
        node_name: str,
    ) -> list[str]:
        """
        Extract event patterns from contract or derive from node name.

        Args:
            contract_content: Contract object with event subscriptions
            node_name: Node name for pattern derivation fallback

        Returns:
            List[str]: Event patterns this node should subscribe to
        """
        ...

    def create_event_envelope(
        self,
        event: ModelOnexEvent,
        source_node_id: str,
        correlation_id: UUID,
    ) -> ModelEventEnvelope:
        """
        Create properly formatted event envelope for broadcasting.

        Args:
            event: ONEX event to wrap
            source_node_id: Source node identifier
            correlation_id: Correlation ID for tracking

        Returns:
            ModelEventEnvelope: Formatted envelope ready for publishing
        """
        ...

    def auto_resolve_event_bus_from_environment(self) -> ProtocolEventBus | None:
        """
        Auto-resolve event bus adapter from environment configuration.

        Returns:
            Optional[ProtocolEventBus]: Event bus adapter if available
        """
        ...

    def setup_event_subscriptions(
        self,
        event_bus: ProtocolEventBus,
        patterns: list[str],
        event_handler: callable,
    ) -> bool:
        """
        Set up event subscriptions for specified patterns.

        Args:
            event_bus: Event bus instance
            patterns: Event patterns to subscribe to
            event_handler: Handler function for incoming events

        Returns:
            bool: True if subscriptions were set up successfully
        """
        ...

    def cleanup_event_subscriptions(
        self,
        event_bus: ProtocolEventBus,
        patterns: list[str],
    ) -> bool:
        """
        Clean up event subscriptions for specified patterns.

        Args:
            event_bus: Event bus instance
            patterns: Event patterns to unsubscribe from

        Returns:
            bool: True if cleanup was successful
        """
        ...

    def validate_event_bus_connection(self, event_bus: ProtocolEventBus) -> bool:
        """
        Validate that event bus connection is working properly.

        Args:
            event_bus: Event bus instance to validate

        Returns:
            bool: True if connection is healthy
        """
        ...
