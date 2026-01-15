"""
Request-Response Introspection Mixin.

Enables nodes to respond to REQUEST_INTROSPECTION events with real-time status information.
Provides the "request-response" half of the hybrid discovery system.
"""

import contextlib
import time
from datetime import UTC
from typing import TYPE_CHECKING
from uuid import uuid4

from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.models.core.model_onex_event import ModelOnexEvent as OnexEvent
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

from omnibase_core.constants.constants_event_types import (
    REQUEST_REAL_TIME_INTROSPECTION,
)
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_node_current_status import EnumNodeCurrentStatus
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.discovery.model_current_tool_availability import (
    ModelCurrentToolAvailability,
)
from omnibase_core.models.discovery.model_discovery_performance_metrics import (
    ModelPerformanceMetrics,
)
from omnibase_core.models.discovery.model_introspection_additional_info import (
    ModelIntrospectionAdditionalInfo,
)
from omnibase_core.models.discovery.model_introspection_filters import (
    ModelIntrospectionFilters,
)
from omnibase_core.models.discovery.model_introspection_response_event import (
    ModelIntrospectionResponseEvent,
)
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
)
from omnibase_core.models.discovery.model_request_introspection_event import (
    ModelRequestIntrospectionEvent,
)
from omnibase_core.models.discovery.model_resource_usage import ModelResourceUsage


class MixinRequestResponseIntrospection:
    """
    Mixin providing request-response introspection capabilities for nodes.

    This mixin enables nodes to:
    - Listen for REQUEST_REAL_TIME_INTROSPECTION events
    - Filter requests based on node characteristics
    - Gather real-time node status and capabilities
    - Respond with REAL_TIME_INTROSPECTION_RESPONSE events

    Works alongside MixinIntrospectionPublisher to provide a hybrid discovery system:
    - Auto-publish introspection for bootstrap/registration
    - Request-response introspection for real-time "who's available now" discovery
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._introspection_request_subscription = None
        self._startup_time: float = time.time()

    def _setup_request_response_introspection(self) -> None:
        """Set up subscription to REQUEST_REAL_TIME_INTROSPECTION events."""
        if not hasattr(self, "_event_bus") or self._event_bus is None:
            emit_log_event_sync(
                LogLevel.WARNING,
                "🔍 INTROSPECTION DEBUG: No event bus available for subscription",
                {
                    "node_name": getattr(self, "node_name", "unknown"),
                    "has_event_bus_attr": hasattr(self, "_event_bus"),
                    "event_bus_is_none": getattr(self, "_event_bus", None) is None,
                },
            )
            return

        try:
            # Subscribe to introspection request events
            # Note: CLI sends "core.discovery.realtime_request"
            self._event_bus.subscribe(
                self._handle_introspection_request,
            )

            emit_log_event_sync(
                LogLevel.INFO,
                f"🔍 INTROSPECTION: Subscribed to {REQUEST_REAL_TIME_INTROSPECTION}",
                {
                    "node_name": getattr(self, "node_name", "unknown"),
                    "event_type": REQUEST_REAL_TIME_INTROSPECTION,
                    "event_bus_type": type(self._event_bus).__name__,
                    "event_bus_connected": getattr(
                        self._event_bus,
                        "is_connected",
                        lambda: "unknown",
                    )(),
                },
            )

        except (AttributeError, KeyError, RuntimeError, ValueError) as e:
            emit_log_event_sync(
                LogLevel.ERROR,
                f"🔍 INTROSPECTION DEBUG: Failed to set up request-response introspection: {e}",
                {
                    "node_name": getattr(self, "node_name", "unknown"),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            if hasattr(self, "_logger") and self._logger:
                self._logger.exception(
                    f"Failed to set up request-response introspection: {e}",
                )

    def _teardown_request_response_introspection(self) -> None:
        """Clean up introspection request subscription."""
        try:
            if hasattr(self, "_event_bus") and self._event_bus:
                self._event_bus.unsubscribe(self._handle_introspection_request)
        except (AttributeError, KeyError, RuntimeError, ValueError) as e:
            if hasattr(self, "_logger") and self._logger:
                self._logger.exception(
                    f"Failed to teardown request-response introspection: {e}",
                )

    def _handle_introspection_request(
        self, envelope: "ModelEventEnvelope[OnexEvent] | OnexEvent"
    ) -> None:
        """
        Handle incoming REQUEST_REAL_TIME_INTROSPECTION events.

        Args:
            envelope: The envelope or event to handle
        """

        # Extract event from envelope if needed
        if hasattr(envelope, "payload"):
            event = envelope.payload
        else:
            event = envelope

        emit_log_event_sync(
            LogLevel.INFO,
            "🔍 INTROSPECTION: Received introspection request",
            {
                "event_type": getattr(event, "event_type", "unknown"),
                "correlation_id": str(getattr(event, "correlation_id", "unknown")),
                "node_name": getattr(self, "node_name", "unknown"),
                "envelope_type": type(envelope).__name__,
                "payload_type": type(event).__name__,
                "expected_event_type": REQUEST_REAL_TIME_INTROSPECTION,
                "event_bus_available": hasattr(self, "_event_bus")
                and self._event_bus is not None,
            },
        )

        # DEBUG: Event type constant verification
        emit_log_event_sync(
            LogLevel.DEBUG,
            "🔍 INTROSPECTION DEBUG: Event type verification",
            {
                "received_event_type": getattr(event, "event_type", "unknown"),
                "expected_constant": REQUEST_REAL_TIME_INTROSPECTION,
                "constants_match": getattr(event, "event_type", None)
                == REQUEST_REAL_TIME_INTROSPECTION,
                "event_type_from_constants": REQUEST_REAL_TIME_INTROSPECTION,
                "correlation_id": str(getattr(event, "correlation_id", "unknown")),
                "node_name": getattr(self, "node_name", "unknown"),
            },
        )

        # Filter for REQUEST_REAL_TIME_INTROSPECTION events only
        if event.event_type != REQUEST_REAL_TIME_INTROSPECTION:
            emit_log_event_sync(
                LogLevel.DEBUG,
                "🔍 INTROSPECTION: Ignoring non-introspection event",
                {
                    "event_type": event.event_type,
                    "expected_type": REQUEST_REAL_TIME_INTROSPECTION,
                    "node_name": getattr(self, "node_name", "unknown"),
                },
            )
            return

        # Reconstruct ModelRequestIntrospectionEvent from event data
        # The event bus delivers events as dictionaries, so we need to reconstruct the typed object
        try:
            if isinstance(event, ModelRequestIntrospectionEvent):
                request_event = event
            elif hasattr(event, "__dict__"):
                # Convert object to dict for reconstruction
                event_dict = event.__dict__ if hasattr(event, "__dict__") else event
                # Dict unpacking to reconstruct typed event; structure validated by Pydantic at runtime
                request_event = ModelRequestIntrospectionEvent(**event_dict)  # type: ignore[arg-type]  # Dict unpacking for event reconstruction
            elif isinstance(event, dict):
                # Event bus delivers as dictionary - reconstruct typed object
                request_event = ModelRequestIntrospectionEvent(**event)
            else:
                emit_log_event_sync(
                    LogLevel.WARNING,
                    "🔍 INTROSPECTION: Cannot reconstruct ModelRequestIntrospectionEvent from event",
                    {
                        "event_class": type(event).__name__,
                        "event_data": str(event)[:200],
                    },
                )
                return
        except Exception as e:  # fallback-ok: event handler returns early with logging, malformed events shouldn't crash node
            emit_log_event_sync(
                LogLevel.WARNING,
                "🔍 INTROSPECTION: Failed to reconstruct ModelRequestIntrospectionEvent",
                {"error": str(e), "event_class": type(event).__name__},
            )
            return

        start_time = time.time()

        try:
            # Check if this request matches our node characteristics
            if not self._matches_introspection_filters(request_event.filters):
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    "🔍 INTROSPECTION: Node does not match filters",
                    {
                        "node_name": getattr(self, "node_name", "unknown"),
                        "filters": (
                            str(request_event.filters)
                            if request_event.filters
                            else "None"
                        ),
                    },
                )
                return

            emit_log_event_sync(
                LogLevel.INFO,
                "🔍 INTROSPECTION: Node matches filters, preparing response",
                {
                    "node_name": getattr(self, "node_name", "unknown"),
                    "correlation_id": str(request_event.correlation_id),
                    "include_resource_usage": request_event.include_resource_usage,
                    "include_performance_metrics": request_event.include_performance_metrics,
                },
            )

            # Gather current node status
            current_status = self._get_current_node_status()
            capabilities = self._get_current_capabilities()
            tools = self._get_current_tool_availability()

            # Optional detailed information
            resource_usage = None
            performance_metrics = None

            if request_event.include_resource_usage:
                resource_usage = self._get_current_resource_usage()

            if request_event.include_performance_metrics:
                performance_metrics = self._get_current_performance_metrics()

            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000

            # Create and publish response
            response = ModelIntrospectionResponseEvent.create_response(
                correlation_id=request_event.correlation_id,
                node_id=getattr(self, "node_id", uuid4()),
                node_name=getattr(self, "node_name", "unknown_node"),
                version=getattr(
                    self, "version", ModelSemVer(major=1, minor=0, patch=0)
                ),
                current_status=current_status,
                capabilities=capabilities,
                response_time_ms=response_time_ms,
                tools=tools,
                resource_usage=resource_usage,
                performance_metrics=performance_metrics,
                tags=getattr(self, "tags", []),
                health_endpoint=getattr(self, "health_endpoint", None),
                additional_info=self._get_additional_introspection_info(),
            )

            # DEBUG: Response creation logging
            emit_log_event_sync(
                LogLevel.INFO,
                "🔍 INTROSPECTION DEBUG: Response object created",
                {
                    "correlation_id": str(request_event.correlation_id),
                    "response_event_type": response.event_type,
                    "response_type": type(response).__name__,
                    "node_id": response.node_id,
                    "node_name": response.node_name,
                    "current_status": (
                        response.current_status.value
                        if response.current_status
                        else "None"
                    ),
                    "response_time_ms": response.response_time_ms,
                    "tools_count": len(response.tools) if response.tools else 0,
                    "capabilities_actions": (
                        len(response.capabilities.actions)
                        if response.capabilities
                        else 0
                    ),
                    "has_resource_usage": response.resource_usage is not None,
                    "has_performance_metrics": response.performance_metrics is not None,
                    "creating_node": getattr(self, "node_name", "unknown"),
                },
            )

            # Publish response
            if hasattr(self, "_event_bus") and self._event_bus:
                emit_log_event_sync(
                    LogLevel.INFO,
                    "🔍 INTROSPECTION: Publishing response",
                    {
                        "node_name": getattr(self, "node_name", "unknown"),
                        "correlation_id": str(request_event.correlation_id),
                        "response_event_type": response.event_type,
                    },
                )

                # Create envelope for the response
                from omnibase_core.models.events.model_event_envelope import (
                    ModelEventEnvelope,
                )

                response_envelope = ModelEventEnvelope.create_broadcast(
                    payload=response,
                    source_node_id=getattr(self, "node_id", uuid4()),
                    correlation_id=getattr(event, "correlation_id", None),
                )

                # DEBUG: Pre-publication logging
                emit_log_event_sync(
                    LogLevel.INFO,
                    "🔍 INTROSPECTION DEBUG: About to publish response envelope",
                    {
                        "correlation_id": str(request_event.correlation_id),
                        "envelope_id": str(response_envelope.envelope_id),
                        "source_tool": response_envelope.source_tool,
                        "target_tool": response_envelope.target_tool,
                        "event_type": response_envelope.payload.event_type,
                        "response_type": type(response).__name__,
                        "envelope_correlation_id": str(
                            response_envelope.correlation_id,
                        ),
                        "node_name": getattr(self, "node_name", "unknown"),
                        "event_bus_type": type(self._event_bus).__name__,
                        "event_bus_connected": getattr(
                            self._event_bus,
                            "is_connected",
                            lambda: "unknown",
                        )(),
                    },
                )

                # Publish the response
                publication_result = self._event_bus.publish(response_envelope)

                # DEBUG: Post-publication logging
                emit_log_event_sync(
                    LogLevel.INFO,
                    "🔍 INTROSPECTION DEBUG: Response envelope published",
                    {
                        "correlation_id": str(request_event.correlation_id),
                        "envelope_id": str(response_envelope.envelope_id),
                        "publication_result": (
                            str(publication_result)
                            if publication_result is not None
                            else "None"
                        ),
                        "publication_result_type": (
                            type(publication_result).__name__
                            if publication_result is not None
                            else "NoneType"
                        ),
                        "node_name": getattr(self, "node_name", "unknown"),
                        "event_type": response_envelope.payload.event_type,
                        "response_type": type(response).__name__,
                    },
                )
                emit_log_event_sync(
                    LogLevel.INFO,
                    "✅ INTROSPECTION: Response published successfully",
                    {"node_name": getattr(self, "node_name", "unknown")},
                )
            else:
                emit_log_event_sync(
                    LogLevel.ERROR,
                    "❌ INTROSPECTION: No event bus available to publish response",
                    {"node_name": getattr(self, "node_name", "unknown")},
                )

        except Exception as e:  # catch-all-ok: request handling errors should be caught and reported via error response
            emit_log_event_sync(
                LogLevel.ERROR,
                f"❌ INTROSPECTION: Error handling request: {e!s}",
                {
                    "node_name": getattr(self, "node_name", "unknown"),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            # Send error response
            try:
                response_time_ms = (time.time() - start_time) * 1000
                event_correlation_id = getattr(event, "correlation_id", None) or uuid4()
                error_response = ModelIntrospectionResponseEvent.create_error_response(
                    correlation_id=event_correlation_id,
                    node_id=getattr(self, "node_id", uuid4()),
                    node_name=getattr(self, "node_name", "unknown_node"),
                    version=getattr(
                        self, "version", ModelSemVer(major=1, minor=0, patch=0)
                    ),
                    error_message=str(e),
                    response_time_ms=response_time_ms,
                )

                if hasattr(self, "_event_bus") and self._event_bus:
                    # Create envelope for the error response
                    from omnibase_core.models.events.model_event_envelope import (
                        ModelEventEnvelope,
                    )

                    error_envelope = ModelEventEnvelope.create_broadcast(
                        payload=error_response,
                        source_node_id=getattr(self, "node_id", uuid4()),
                        correlation_id=event_correlation_id,
                    )

                    # DEBUG: Error response publication logging
                    emit_log_event_sync(
                        LogLevel.DEBUG,
                        "🔍 INTROSPECTION DEBUG: Publishing error response envelope",
                        {
                            "correlation_id": str(request_event.correlation_id),
                            "envelope_id": str(error_envelope.envelope_id),
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                            "node_name": getattr(self, "node_name", "unknown"),
                            "event_type": error_envelope.payload.event_type,
                        },
                    )

                    error_publication_result = self._event_bus.publish(error_envelope)

                    # DEBUG: Error response publication result
                    emit_log_event_sync(
                        LogLevel.DEBUG,
                        "🔍 INTROSPECTION DEBUG: Error response envelope published",
                        {
                            "correlation_id": str(request_event.correlation_id),
                            "envelope_id": str(error_envelope.envelope_id),
                            "publication_result": (
                                str(error_publication_result)
                                if error_publication_result is not None
                                else "None"
                            ),
                            "node_name": getattr(self, "node_name", "unknown"),
                        },
                    )

            except (
                Exception
            ) as nested_e:  # catch-all-ok: error response sending is best-effort
                if hasattr(self, "_logger") and self._logger:
                    self._logger.exception(f"Failed to send error response: {nested_e}")

    def _matches_introspection_filters(
        self,
        filters: ModelIntrospectionFilters | None,
    ) -> bool:
        """
        Check if this node matches the introspection request filters.

        Args:
            filters: Optional filters from the request

        Returns:
            True if node matches filters (or no filters provided)
        """
        if not filters:
            return True

        # Check node_type filter
        if filters.node_type:
            node_type = getattr(self, "node_type", None)
            if node_type and node_type not in filters.node_type:
                return False

        # Check node_names filter
        if filters.node_names:
            node_name = getattr(self, "node_name", None)
            if node_name and node_name not in filters.node_names:
                return False

        # Check capabilities filter
        if filters.capabilities:
            current_capabilities = self._get_current_capabilities()
            node_actions = set(current_capabilities.actions)
            required_capabilities = set(filters.capabilities)
            if not required_capabilities.issubset(node_actions):
                return False

        # Check protocols filter
        if filters.protocols:
            current_capabilities = self._get_current_capabilities()
            node_protocols = set(current_capabilities.protocols)
            required_protocols = set(filters.protocols)
            if not required_protocols.issubset(node_protocols):
                return False

        # Check tags filter
        if filters.tags:
            node_tags = set(getattr(self, "tags", []))
            required_tags = set(filters.tags)
            if not required_tags.issubset(node_tags):
                return False

        # Check status filter
        if filters.status:
            current_status = self._get_current_node_status()
            if current_status.value not in filters.status:
                return False

        return True

    def _get_current_node_status(self) -> EnumNodeCurrentStatus:
        """
        Get the current operational status of the node.

        Returns:
            Current node status
        """
        # Default implementation - subclasses can override for more sophisticated logic
        if hasattr(self, "_is_shutting_down") and self._is_shutting_down:
            return EnumNodeCurrentStatus.STOPPING

        if hasattr(self, "_is_starting") and self._is_starting:
            return EnumNodeCurrentStatus.STARTING

        # Check if node appears healthy
        try:
            if (
                hasattr(self, "_event_bus")
                and self._event_bus
                and hasattr(self._event_bus, "is_connected")
            ) and not self._event_bus.is_connected():
                return EnumNodeCurrentStatus.DEGRADED
        except Exception:  # fallback-ok: catches non-fatal exceptions, returns DEGRADED for health reporting
            return EnumNodeCurrentStatus.DEGRADED

        return EnumNodeCurrentStatus.READY

    def _get_current_capabilities(self) -> ModelNodeCapabilities:
        """
        Get current node capabilities.

        Returns:
            Current capabilities (fallback to introspection if available)
        """
        # Try to use cached introspection data if available
        if hasattr(self, "_cached_introspection"):
            cached = self._cached_introspection
            if hasattr(cached, "capabilities"):
                capabilities: ModelNodeCapabilities = cached.capabilities
                return capabilities

        # Fallback to basic capabilities
        actions = []
        if hasattr(self, "get_supported_actions"):
            with contextlib.suppress(Exception):
                actions = self.get_supported_actions()

        protocols = ["event_bus"]
        if hasattr(self, "get_supported_protocols"):
            with contextlib.suppress(Exception):
                protocols = self.get_supported_protocols()

        metadata = {}
        if hasattr(self, "get_metadata"):
            with contextlib.suppress(Exception):
                metadata = self.get_metadata()

        # Dict metadata passed where typed model expected; Pydantic validates at runtime
        return ModelNodeCapabilities(
            actions=actions,
            protocols=protocols,
            metadata=metadata,  # type: ignore[arg-type]  # Dict passed for metadata; Pydantic validates at runtime
        )

    def _get_current_tool_availability(self) -> list[ModelCurrentToolAvailability]:
        """
        Get current tool availability information.

        Returns:
            List of tool availability status
        """
        tools = []

        # Try to get tool information from registry if available
        if hasattr(self, "_registry") and self._registry:
            try:
                available_tools = self._registry.get_available_tools()
                for tool_name in available_tools:
                    tools.append(
                        ModelCurrentToolAvailability(
                            tool_name=tool_name,
                            status=EnumNodeCurrentStatus.READY,
                            execution_count=0,  # Could be enhanced with actual metrics
                        ),
                    )
            except (
                Exception
            ) as e:  # fallback-ok: tool availability optional, returns partial results
                # Registry tool enumeration failed - log for debugging but continue
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    f"Failed to get tool availability from registry: {e}",
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "node_name": getattr(self, "node_name", "unknown"),
                    },
                )

        return tools

    def _get_current_resource_usage(self) -> ModelResourceUsage | None:
        """
        Get current resource usage information.

        Returns:
            Resource usage information if available
        """
        try:
            import psutil

            process = psutil.Process()

            return ModelResourceUsage(
                cpu_percent=process.cpu_percent(),
                memory_mb=process.memory_info().rss / 1024 / 1024,
                memory_percent=process.memory_percent(),
                open_files=process.num_fds() if hasattr(process, "num_fds") else None,
                active_connections=(
                    len(process.connections())
                    if hasattr(process, "connections")
                    else None
                ),
            )
        except ImportError:
            # psutil not available
            return None
        except (
            Exception
        ):  # fallback-ok: resource metrics optional, returns None if unavailable
            # Error getting resource usage
            return None

    def _get_current_performance_metrics(self) -> ModelPerformanceMetrics | None:
        """
        Get current performance metrics.

        Returns:
            Performance metrics if available
        """
        try:
            uptime_seconds = time.time() - self._startup_time

            # Basic metrics - could be enhanced with actual monitoring
            return ModelPerformanceMetrics(
                uptime_seconds=uptime_seconds,
                requests_per_minute=0.0,  # Would need request tracking
                average_response_time_ms=0.0,  # Would need response time tracking
                error_rate_percent=0.0,  # Would need error tracking
                queue_depth=0,  # Would need queue monitoring
            )
        except (
            Exception
        ):  # fallback-ok: performance metrics optional, returns None if unavailable
            return None

    def _get_additional_introspection_info(
        self,
    ) -> ModelIntrospectionAdditionalInfo | None:
        """
        Get additional node-specific introspection information.

        Returns:
            ModelIntrospectionAdditionalInfo with additional information
        """
        # Create the additional info model
        # Convert startup_time from float timestamp to datetime
        from datetime import datetime

        startup_datetime = datetime.fromtimestamp(self._startup_time, tz=UTC)
        additional_info = ModelIntrospectionAdditionalInfo(
            startup_time=startup_datetime,
        )

        # Add any node-specific information
        if hasattr(self, "get_additional_info"):
            try:
                additional = self.get_additional_info()
                if isinstance(additional, dict):
                    # Update the model with additional fields
                    for key, value in additional.items():
                        setattr(additional_info, key, value)
            except (
                Exception
            ) as e:  # fallback-ok: additional info optional, returns partial results
                # Additional info gathering failed - log for debugging but continue
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    f"Failed to gather additional introspection info: {e}",
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "node_name": getattr(self, "node_name", "unknown"),
                    },
                )

        return additional_info
