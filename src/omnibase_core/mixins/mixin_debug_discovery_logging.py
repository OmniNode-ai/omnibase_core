"""
ONEX Debug Discovery Logging Mixin.

Provides standardized debug logging capabilities for nodes that need
to monitor and debug service discovery interactions.
"""

import logging
from collections.abc import Mapping

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.types.model_onex_common_types import EnvValue

logger = logging.getLogger(__name__)


class MixinDebugDiscoveryLogging:
    """
    Mixin providing standardized debug logging for service discovery events.

    This mixin provides consistent debug logging patterns for nodes that need
    to monitor and troubleshoot service discovery interactions, reducing code
    duplication while maintaining comprehensive debugging capabilities.
    """

    def setup_discovery_debug_logging(
        self,
        node_name: str,
        additional_context: Mapping[str, EnvValue] | None = None,
    ) -> None:
        """
        Setup comprehensive discovery event debug logging.

        Args:
            node_name: Name of the node for logging context
            additional_context: Additional context fields to include in logs
        """

        context = {
            "node_name": node_name,
            "container_available": hasattr(self, "container"),
            "event_bus_available": hasattr(self, "event_bus"),
            "service_registry_enabled": hasattr(self, "start_service_registry"),
        }

        if additional_context:
            context.update(additional_context)

        emit_log_event(
            LogLevel.DEBUG,
            f"🔍 {node_name.upper()} DEBUG: Setting up discovery event monitoring",
        )

        # Override the introspection handler to add debug logging
        if hasattr(self, "_handle_introspection_request"):
            # Store original handler
            self._original_handle_introspection_request = (
                self._handle_introspection_request  # type: ignore[has-type]  # Dynamic attribute access for debug wrapper
            )

            # Replace with debug version (explicit type for MyPy)
            def debug_handler(envelope_or_event: object) -> None:
                return self._debug_handle_introspection_request(
                    envelope_or_event, node_name
                )

            self._handle_introspection_request = debug_handler

            emit_log_event(
                LogLevel.DEBUG,
                f"🔍 {node_name.upper()} DEBUG: Wrapped introspection handler with debug logging",
                {"node_name": node_name},
            )

    def _debug_handle_introspection_request(
        self, envelope_or_event: object, node_name: str
    ) -> None:
        """
        Debug wrapper for introspection request handling.

        Args:
            envelope_or_event: Event envelope or direct event
            node_name: Name of the node for logging context
        """
        from omnibase_core.constants.constants_event_types import (
            REQUEST_REAL_TIME_INTROSPECTION,
        )

        # Extract event from envelope if needed
        if hasattr(envelope_or_event, "payload"):
            event = envelope_or_event.payload
            envelope_id = getattr(envelope_or_event, "envelope_id", "unknown")
        else:
            event = envelope_or_event
            envelope_id = "direct_event"

        emit_log_event(
            LogLevel.DEBUG,
            f"🔍 {node_name.upper()} DEBUG: Received discovery event",
            {
                "node_name": node_name,
                "event_type": getattr(event, "event_type", "unknown"),
                "correlation_id": str(getattr(event, "correlation_id", "unknown")),
                "envelope_id": str(envelope_id),
                "envelope_type": type(envelope_or_event).__name__,
                "payload_type": type(event).__name__,
                "expected_event_type": REQUEST_REAL_TIME_INTROSPECTION,
                "event_matches_expected": getattr(event, "event_type", None)
                == REQUEST_REAL_TIME_INTROSPECTION,
            },
        )

        # Call original handler
        try:
            result: None = self._original_handle_introspection_request(
                envelope_or_event
            )

            emit_log_event(
                LogLevel.DEBUG,
                f"🔍 {node_name.upper()} DEBUG: Introspection handler completed successfully",
                {
                    "node_name": node_name,
                    "correlation_id": str(getattr(event, "correlation_id", "unknown")),
                    "result": str(result) if result is not None else "None",
                },
            )

            return result

        except Exception as e:  # catch-all-ok: introspection handler can raise anything during node inspection
            emit_log_event(
                LogLevel.ERROR,
                f"🔍 {node_name.upper()} DEBUG: Introspection handler failed",
                {
                    "node_name": node_name,
                    "correlation_id": str(getattr(event, "correlation_id", "unknown")),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
