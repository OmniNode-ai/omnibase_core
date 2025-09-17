"""
Node Shutdown Event Model

Event published by nodes when they are shutting down to enable
graceful deregistration from the service registry.
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from omnibase_core.core.constants.event_types import CoreEventTypes
from omnibase_core.models.core.model_onex_event import ModelOnexEvent


class ModelNodeShutdownEvent(ModelOnexEvent):
    """
    Event published by nodes when shutting down for graceful deregistration.

    This event allows nodes to cleanly remove themselves from the service
    registry and notify other services of their unavailability.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=CoreEventTypes.NODE_SHUTDOWN_EVENT,
        description="Event type identifier",
    )

    # Node identification
    node_name: str = Field(..., description="Name of the node shutting down")

    # Shutdown information
    shutdown_reason: str = Field(
        ...,
        description="Reason for shutdown (graceful, error, forced, maintenance)",
    )
    shutdown_initiated_at: datetime = Field(
        default_factory=datetime.now,
        description="When the shutdown was initiated",
    )

    # Operational details
    final_status: str = Field(
        default="stopping",
        description="Final status of the node (stopping, stopped, error)",
    )
    uptime_seconds: int | None = Field(
        None,
        description="Total uptime of the node in seconds",
    )
    requests_processed: int | None = Field(
        None,
        description="Total requests processed during node lifetime",
    )

    # Cleanup information
    cleanup_actions: list[str] = Field(
        default_factory=list,
        description="List of cleanup actions performed during shutdown",
    )
    cleanup_errors: list[str] = Field(
        default_factory=list,
        description="Any errors encountered during cleanup",
    )

    # Restart information
    restart_expected: bool = Field(
        False,
        description="Whether the node is expected to restart",
    )
    restart_delay_seconds: int | None = Field(
        None,
        description="Expected delay before restart in seconds",
    )
    replacement_node_id: str | None = Field(
        None,
        description="ID of replacement node if applicable",
    )

    # Consul compatibility
    service_id: str | None = Field(
        None,
        description="Service ID for Consul deregistration",
    )

    # Final metrics
    final_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Final performance metrics before shutdown",
    )

    @classmethod
    def create_graceful_shutdown(
        cls,
        node_id: str,
        node_name: str,
        uptime_seconds: int | None = None,
        requests_processed: int | None = None,
        **kwargs,
    ) -> "ModelNodeShutdownEvent":
        """
        Factory method to create a graceful shutdown event.

        Args:
            node_id: Unique node identifier
            node_name: Node name
            uptime_seconds: Total uptime
            requests_processed: Total requests processed
            **kwargs: Additional fields

        Returns:
            ModelNodeShutdownEvent for graceful shutdown
        """
        return cls(
            node_id=node_id,
            node_name=node_name,
            shutdown_reason="graceful",
            final_status="stopping",
            uptime_seconds=uptime_seconds,
            requests_processed=requests_processed,
            cleanup_actions=[
                "closing_connections",
                "saving_state",
                "cleanup_resources",
            ],
            **kwargs,
        )

    @classmethod
    def create_error_shutdown(
        cls,
        node_id: str,
        node_name: str,
        error_message: str,
        uptime_seconds: int | None = None,
        **kwargs,
    ) -> "ModelNodeShutdownEvent":
        """
        Factory method to create an error shutdown event.

        Args:
            node_id: Unique node identifier
            node_name: Node name
            error_message: Error that caused shutdown
            uptime_seconds: Uptime before error
            **kwargs: Additional fields

        Returns:
            ModelNodeShutdownEvent for error shutdown
        """
        return cls(
            node_id=node_id,
            node_name=node_name,
            shutdown_reason="error",
            final_status="error",
            uptime_seconds=uptime_seconds,
            cleanup_errors=[error_message],
            final_metrics={"error_message": error_message},
            **kwargs,
        )

    @classmethod
    def create_maintenance_shutdown(
        cls,
        node_id: str,
        node_name: str,
        maintenance_reason: str,
        restart_delay_seconds: int | None = None,
        replacement_node_id: str | None = None,
        **kwargs,
    ) -> "ModelNodeShutdownEvent":
        """
        Factory method to create a maintenance shutdown event.

        Args:
            node_id: Unique node identifier
            node_name: Node name
            maintenance_reason: Reason for maintenance
            restart_delay_seconds: Expected restart delay
            replacement_node_id: Replacement node if any
            **kwargs: Additional fields

        Returns:
            ModelNodeShutdownEvent for maintenance shutdown
        """
        return cls(
            node_id=node_id,
            node_name=node_name,
            shutdown_reason="maintenance",
            final_status="stopping",
            restart_expected=True,
            restart_delay_seconds=restart_delay_seconds,
            replacement_node_id=replacement_node_id,
            cleanup_actions=["maintenance_prep", "state_backup"],
            final_metrics={"maintenance_reason": maintenance_reason},
            **kwargs,
        )

    @classmethod
    def create_forced_shutdown(
        cls,
        node_id: str,
        node_name: str,
        force_reason: str,
        **kwargs,
    ) -> "ModelNodeShutdownEvent":
        """
        Factory method to create a forced shutdown event.

        Args:
            node_id: Unique node identifier
            node_name: Node name
            force_reason: Reason for forced shutdown
            **kwargs: Additional fields

        Returns:
            ModelNodeShutdownEvent for forced shutdown
        """
        return cls(
            node_id=node_id,
            node_name=node_name,
            shutdown_reason="forced",
            final_status="stopped",
            cleanup_actions=["emergency_cleanup"],
            final_metrics={"force_reason": force_reason},
            **kwargs,
        )

    def is_graceful(self) -> bool:
        """Check if this was a graceful shutdown"""
        return self.shutdown_reason == "graceful"

    def has_cleanup_errors(self) -> bool:
        """Check if there were cleanup errors"""
        return len(self.cleanup_errors) > 0

    def will_restart(self) -> bool:
        """Check if the node is expected to restart"""
        return self.restart_expected
