"""
Event Bus Service Implementation.

Centralized service for event bus operations extracted from ModelNodeBase
as part of NODEBASE-001 Phase 5 deconstruction.

This service handles:
- Event bus initialization and auto-resolution
- Node lifecycle event emission (START, SUCCESS, FAILURE)
- Introspection event publishing for service discovery
- Event pattern extraction and subscription management
- Event envelope creation and broadcasting
- Connection validation and error handling

Author: ONEX Framework Team
"""

import os
import time
from uuid import UUID

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus

from .models.model_event_bus_config import ModelEventBusConfig
from .protocols.protocol_event_bus_service import ProtocolEventBusService


class EventBusService(ProtocolEventBusService):
    """
    Event Bus Service for centralized event operations.

    Implements the ProtocolEventBusService interface to provide
    comprehensive event bus management extracted from ModelNodeBase.

    Phase 5: All event bus operations are now centralized in this service
    rather than being scattered throughout ModelNodeBase and mixins.
    """

    def __init__(self, config: ModelEventBusConfig | None = None):
        """
        Initialize EventBusService with configuration.

        Args:
            config: Optional configuration (uses defaults if not provided)
        """
        self.config = config or ModelEventBusConfig()
        self._event_bus: ProtocolEventBus | None = None
        self._event_cache = {}
        self._pattern_cache = {}

        emit_log_event(
            LogLevel.INFO,
            "Phase 5: EventBusService initialized",
            {
                "enable_lifecycle_events": self.config.enable_lifecycle_events,
                "enable_introspection_publishing": self.config.enable_introspection_publishing,
                "auto_resolve_event_bus": self.config.auto_resolve_event_bus,
                "connection_timeout": self.config.connection_timeout_seconds,
            },
        )

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

        Raises:
            OnexError: If event bus cannot be initialized and suppress_connection_errors is False
        """
        try:
            if event_bus:
                self._event_bus = event_bus
                emit_log_event(
                    LogLevel.INFO,
                    "EventBusService: Using provided event bus instance",
                    {
                        "event_bus_type": type(event_bus).__name__,
                        "auto_resolve": auto_resolve,
                    },
                )
                return event_bus

            if auto_resolve and self.config.auto_resolve_event_bus:
                resolved_bus = self.auto_resolve_event_bus_from_environment()
                if resolved_bus:
                    self._event_bus = resolved_bus
                    emit_log_event(
                        LogLevel.INFO,
                        "EventBusService: Successfully auto-resolved event bus",
                        {
                            "event_bus_type": type(resolved_bus).__name__,
                        },
                    )
                    return resolved_bus

            # No event bus available
            if not self.config.suppress_connection_errors:
                raise OnexError(
                    error_code=CoreErrorCode.RESOURCE_UNAVAILABLE,
                    message="Could not initialize event bus connection",
                    context={
                        "event_bus_provided": event_bus is not None,
                        "auto_resolve_enabled": auto_resolve
                        and self.config.auto_resolve_event_bus,
                        "suppress_errors": self.config.suppress_connection_errors,
                    },
                )
            emit_log_event(
                LogLevel.WARNING,
                "EventBusService: No event bus available, continuing in CLI-only mode",
                {
                    "suppress_connection_errors": self.config.suppress_connection_errors,
                },
            )
            self._event_bus = None
            return None

        except OnexError:
            raise
        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to initialize event bus: {e!s}",
                context={
                    "event_bus_provided": event_bus is not None,
                    "auto_resolve": auto_resolve,
                },
            ) from e

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
        if not self.config.enable_lifecycle_events:
            return False

        if not self._event_bus:
            emit_log_event(
                LogLevel.DEBUG,
                "EventBusService: No event bus available for NODE_START emission",
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "correlation_id": str(correlation_id),
                },
            )
            return False

        try:
            # Import proper event types
            from omnibase_core.core.constants.event_types import CoreEventTypes

            # Create NODE_START event
            start_event = ModelOnexEvent(
                event_type=CoreEventTypes.NODE_START,
                node_id=node_id,
                correlation_id=correlation_id,
                timestamp=time.time(),
                data={
                    "node_name": node_name,
                    "metadata": metadata,
                    **metadata,  # Flatten metadata into data
                },
            )

            # Create envelope and publish
            envelope = self.create_event_envelope(start_event, node_id, correlation_id)
            self._event_bus.publish(envelope)

            emit_log_event(
                LogLevel.INFO,
                f"EventBusService: Emitted NODE_START for {node_name}",
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "correlation_id": str(correlation_id),
                    "event_id": str(start_event.event_id),
                },
            )
            return True

        except Exception as e:
            if self.config.fail_fast_on_validation_errors:
                raise OnexError(
                    error_code=CoreErrorCode.OPERATION_FAILED,
                    message=f"Failed to emit NODE_START event: {e!s}",
                    context={
                        "node_id": node_id,
                        "node_name": node_name,
                        "correlation_id": str(correlation_id),
                    },
                ) from e
            emit_log_event(
                LogLevel.ERROR,
                f"EventBusService: Failed to emit NODE_START: {e!s}",
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "error_type": type(e).__name__,
                },
            )
            return False

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
        if not self.config.enable_lifecycle_events:
            return False

        if not self._event_bus:
            return False

        try:
            # Import proper event types
            from omnibase_core.core.constants.event_types import CoreEventTypes

            # Create NODE_SUCCESS event
            success_event = ModelOnexEvent(
                event_type=CoreEventTypes.NODE_SUCCESS,
                node_id=node_id,
                correlation_id=correlation_id,
                timestamp=time.time(),
                data={
                    "node_name": node_name,
                    "result_status": getattr(result, "status", "success"),
                    "metadata": {"has_result": result is not None, **metadata},
                },
            )

            # Create envelope and publish
            envelope = self.create_event_envelope(
                success_event,
                node_id,
                correlation_id,
            )
            self._event_bus.publish(envelope)

            emit_log_event(
                LogLevel.INFO,
                f"EventBusService: Emitted NODE_SUCCESS for {node_name}",
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "correlation_id": str(correlation_id),
                    "event_id": str(success_event.event_id),
                    "result_status": getattr(result, "status", "success"),
                },
            )
            return True

        except Exception as e:
            if self.config.fail_fast_on_validation_errors:
                raise OnexError(
                    error_code=CoreErrorCode.OPERATION_FAILED,
                    message=f"Failed to emit NODE_SUCCESS event: {e!s}",
                    context={
                        "node_id": node_id,
                        "node_name": node_name,
                        "correlation_id": str(correlation_id),
                    },
                ) from e
            emit_log_event(
                LogLevel.ERROR,
                f"EventBusService: Failed to emit NODE_SUCCESS: {e!s}",
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "error_type": type(e).__name__,
                },
            )
            return False

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
        if not self.config.enable_lifecycle_events:
            return False

        if not self._event_bus:
            return False

        try:
            # Import proper event types
            from omnibase_core.core.constants.event_types import CoreEventTypes

            # Create NODE_FAILURE event
            failure_event = ModelOnexEvent(
                event_type=CoreEventTypes.NODE_FAILURE,
                node_id=node_id,
                correlation_id=correlation_id,
                timestamp=time.time(),
                data={
                    "node_name": node_name,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "error_code": getattr(error, "error_code", None),
                    "metadata": metadata,
                },
            )

            # Create envelope and publish
            envelope = self.create_event_envelope(
                failure_event,
                node_id,
                correlation_id,
            )
            self._event_bus.publish(envelope)

            emit_log_event(
                LogLevel.ERROR,
                f"EventBusService: Emitted NODE_FAILURE for {node_name}",
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "correlation_id": str(correlation_id),
                    "event_id": str(failure_event.event_id),
                    "error_type": type(error).__name__,
                    "error_code": getattr(error, "error_code", None),
                },
            )
            return True

        except Exception as e:
            if self.config.fail_fast_on_validation_errors:
                raise OnexError(
                    error_code=CoreErrorCode.OPERATION_FAILED,
                    message=f"Failed to emit NODE_FAILURE event: {e!s}",
                    context={
                        "node_id": node_id,
                        "node_name": node_name,
                        "correlation_id": str(correlation_id),
                        "original_error": str(error),
                    },
                ) from e
            emit_log_event(
                LogLevel.ERROR,
                f"EventBusService: Failed to emit NODE_FAILURE: {e!s}",
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "original_error": str(error),
                    "emit_error_type": type(e).__name__,
                },
            )
            return False

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
        if not self.config.enable_introspection_publishing:
            return False

        if not self._event_bus:
            return False

        try:
            # Create introspection event
            from omnibase_core.models.core.model_semver import ModelSemVer
            from omnibase_core.models.discovery.model_node_introspection_event import (
                ModelNodeIntrospectionEvent,
            )

            # Parse version string to ModelSemVer
            try:
                version_parts = version.split(".")
                semver = ModelSemVer(
                    major=int(version_parts[0]) if len(version_parts) > 0 else 1,
                    minor=int(version_parts[1]) if len(version_parts) > 1 else 0,
                    patch=int(version_parts[2]) if len(version_parts) > 2 else 0,
                )
            except (ValueError, IndexError):
                semver = ModelSemVer(major=1, minor=0, patch=0)

            # Create introspection event
            introspection_event = ModelNodeIntrospectionEvent.create_from_node_info(
                node_id=node_id,
                node_name=node_name,
                version=semver,
                actions=actions,
                protocols=protocols,
                metadata=metadata,
                tags=["event_driven", "service"],
                health_endpoint=f"/health/{node_id}",
                correlation_id=correlation_id,
            )

            # Create envelope and publish with retry
            envelope = self.create_event_envelope(
                introspection_event,
                node_id,
                correlation_id,
            )

            if self.config.enable_event_retry:
                return self._publish_with_retry(
                    envelope,
                    self.config.max_retry_attempts,
                )
            self._event_bus.publish(envelope)

            emit_log_event(
                LogLevel.INFO,
                f"EventBusService: Published introspection event for {node_name}",
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "version": version,
                    "actions": actions,
                    "protocols": protocols,
                    "correlation_id": str(correlation_id),
                },
            )
            return True

        except Exception as e:
            if self.config.fail_fast_on_validation_errors:
                raise OnexError(
                    error_code=CoreErrorCode.OPERATION_FAILED,
                    message=f"Failed to publish introspection event: {e!s}",
                    context={
                        "node_id": node_id,
                        "node_name": node_name,
                        "version": version,
                    },
                ) from e
            emit_log_event(
                LogLevel.ERROR,
                f"EventBusService: Failed to publish introspection event: {e!s}",
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "error_type": type(e).__name__,
                },
            )
            return False

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
        patterns = []
        patterns_source = "default"

        try:
            # Check cache first
            cache_key = f"{node_name}_{id(contract_content)}"
            if self.config.enable_event_caching and cache_key in self._pattern_cache:
                cached_result = self._pattern_cache[cache_key]
                emit_log_event(
                    LogLevel.DEBUG,
                    f"EventBusService: Using cached event patterns for {node_name}",
                    {
                        "node_name": node_name,
                        "patterns": cached_result["patterns"],
                        "source": cached_result["source"],
                    },
                )
                return cached_result["patterns"]

            # Try to get patterns from contract first
            if self.config.use_contract_event_patterns and contract_content:
                try:
                    contract_dict = contract_content.__dict__
                    if "event_subscriptions" in contract_dict:
                        event_subs = contract_dict["event_subscriptions"]
                        if isinstance(event_subs, list):
                            for sub in event_subs:
                                if isinstance(sub, dict) and "event_type" in sub:
                                    patterns.append(sub["event_type"])
                            if patterns:
                                patterns_source = "contract"
                                emit_log_event(
                                    LogLevel.INFO,
                                    f"EventBusService: Found event patterns in contract for {node_name}",
                                    {
                                        "node_name": node_name,
                                        "patterns": patterns,
                                        "pattern_count": len(patterns),
                                    },
                                )
                except Exception as e:
                    emit_log_event(
                        LogLevel.WARNING,
                        f"EventBusService: Failed to parse contract event patterns: {e!s}",
                        {"node_name": node_name},
                    )

            # Fallback to node name-based patterns
            if not patterns and self.config.fallback_to_node_name_patterns:
                # Derive patterns from node name
                if node_name.startswith("tool_"):
                    # Convert tool_contract_validator -> contract.validate
                    tool_type = node_name.replace("tool_", "").replace("_", ".")

                    # Special mappings for known tools
                    event_mappings = {
                        "contract.validator": "contract.validate",
                        "ast.generator": "ast.generate",
                        "ast.renderer": "ast.render",
                        "scenario.generator": "scenario.generate",
                        "contract.driven.generator": "contract.generate",
                        "model.regenerator": "model.regenerate",
                    }

                    event_type = event_mappings.get(tool_type, tool_type)
                    patterns = [f"generation.{event_type}", f"*.{event_type}"]
                    patterns_source = "node_name"
                else:
                    # Generic node name pattern
                    patterns = [f"*.{node_name}", f"{node_name}.*"]
                    patterns_source = "node_name"

                emit_log_event(
                    LogLevel.INFO,
                    f"EventBusService: Generated event patterns from node name for {node_name}",
                    {
                        "node_name": node_name,
                        "patterns": patterns,
                        "pattern_source": patterns_source,
                    },
                )

            # Final fallback to default patterns
            if not patterns:
                patterns = self.config.default_event_patterns.copy()
                patterns_source = "default"
                emit_log_event(
                    LogLevel.WARNING,
                    f"EventBusService: Using default event patterns for {node_name}",
                    {
                        "node_name": node_name,
                        "patterns": patterns,
                    },
                )

            # Add discovery patterns for introspection
            discovery_patterns = ["core.discovery.introspection_request"]
            for pattern in discovery_patterns:
                if pattern not in patterns:
                    patterns.append(pattern)

            # Cache the result
            if self.config.enable_event_caching:
                if len(self._pattern_cache) >= self.config.cache_max_size:
                    # Simple cache eviction - remove first item
                    first_key = next(iter(self._pattern_cache))
                    del self._pattern_cache[first_key]

                self._pattern_cache[cache_key] = {
                    "patterns": patterns,
                    "source": patterns_source,
                }

            return patterns

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"EventBusService: Failed to get event patterns for {node_name}: {e!s}",
                {
                    "node_name": node_name,
                    "error_type": type(e).__name__,
                },
            )
            # Return default patterns as fallback
            return self.config.default_event_patterns.copy()

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
        try:
            if self.config.use_broadcast_envelopes:
                envelope = ModelEventEnvelope.create_broadcast(
                    payload=event,
                    source_node_id=source_node_id,
                    correlation_id=correlation_id,
                )

                emit_log_event(
                    LogLevel.DEBUG,
                    f"EventBusService: Created broadcast envelope for {event.event_type}",
                    {
                        "event_type": event.event_type,
                        "event_id": str(event.event_id),
                        "source_node_id": source_node_id,
                        "correlation_id": str(correlation_id),
                        "envelope_id": str(envelope.envelope_id),
                    },
                )
                return envelope
            # Create a simple envelope without broadcast metadata
            # Create proper route spec for direct routing
            # Generate a UUID-compatible destination for node addressing
            import hashlib

            from omnibase_core.models.core.model_route_spec import ModelRouteSpec

            if not source_node_id.startswith("node://"):
                # Generate a proper UUID from the source_node_id
                # Use a deterministic approach based on the node ID
                if len(source_node_id) >= 32 and "-" in source_node_id:
                    # Already looks like a UUID, use it directly
                    formatted_id = source_node_id
                else:
                    # Create a deterministic UUID from the node ID using MD5 hash
                    md5_hash = hashlib.md5(source_node_id.encode()).hexdigest()
                    # Format as UUID: 8-4-4-4-12
                    formatted_id = f"{md5_hash[:8]}-{md5_hash[8:12]}-{md5_hash[12:16]}-{md5_hash[16:20]}-{md5_hash[20:32]}"
                destination = f"node://{formatted_id}"
            else:
                destination = source_node_id
            route_spec = ModelRouteSpec.create_direct_route(destination)

            return ModelEventEnvelope(
                payload=event,
                source_node_id=source_node_id,
                correlation_id=correlation_id,
                route_spec=route_spec,
            )

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to create event envelope: {e!s}",
                context={
                    "event_type": event.event_type,
                    "source_node_id": source_node_id,
                    "correlation_id": str(correlation_id),
                },
            ) from e

    def auto_resolve_event_bus_from_environment(self) -> ProtocolEventBus | None:
        """
        Auto-resolve event bus adapter from environment configuration.

        Returns:
            Optional[ProtocolEventBus]: Event bus adapter if available
        """
        try:
            # Get event bus URL from config or environment
            event_bus_url = self.config.event_bus_url or os.getenv(
                "EVENT_BUS_URL",
                "http://localhost:8083",
            )

            emit_log_event(
                LogLevel.INFO,
                "EventBusService: Attempting to auto-resolve event bus from environment",
                {
                    "event_bus_url": event_bus_url,
                    "timeout_seconds": self.config.connection_timeout_seconds,
                },
            )

            # Try to create event bus adapter
            try:
                from omnibase_core.services.event_bus_adapter import EventBusAdapter

                adapter = EventBusAdapter(event_bus_url)

                # Test connection if validation is enabled
                if self.validate_event_bus_connection(adapter):
                    emit_log_event(
                        LogLevel.INFO,
                        "EventBusService: Successfully auto-resolved and validated event bus",
                        {
                            "event_bus_url": event_bus_url,
                            "adapter_type": type(adapter).__name__,
                        },
                    )
                    return adapter
                emit_log_event(
                    LogLevel.WARNING,
                    "EventBusService: Event bus connection validation failed",
                    {"event_bus_url": event_bus_url},
                )
                return None

            except ImportError:
                emit_log_event(
                    LogLevel.WARNING,
                    "EventBusService: EventBusAdapter not available for auto-resolution",
                    {"event_bus_url": event_bus_url},
                )
                return None

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"EventBusService: Failed to auto-resolve event bus: {e!s}",
                {
                    "error_type": type(e).__name__,
                    "event_bus_url": self.config.event_bus_url,
                },
            )
            return None

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
        try:
            success_count = 0

            for pattern in patterns:
                try:
                    event_bus.subscribe(event_handler, pattern)
                    success_count += 1
                    emit_log_event(
                        LogLevel.DEBUG,
                        f"EventBusService: Subscribed to pattern {pattern}",
                        {"pattern": pattern},
                    )
                except Exception as e:
                    emit_log_event(
                        LogLevel.ERROR,
                        f"EventBusService: Failed to subscribe to pattern {pattern}: {e!s}",
                        {
                            "pattern": pattern,
                            "error_type": type(e).__name__,
                        },
                    )

            emit_log_event(
                LogLevel.INFO,
                f"EventBusService: Set up {success_count}/{len(patterns)} event subscriptions",
                {
                    "success_count": success_count,
                    "total_patterns": len(patterns),
                    "patterns": patterns,
                },
            )

            return success_count > 0

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to setup event subscriptions: {e!s}",
                context={
                    "patterns": patterns,
                    "event_bus_type": type(event_bus).__name__,
                },
            ) from e

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
        try:
            success_count = 0

            for pattern in patterns:
                try:
                    event_bus.unsubscribe(pattern)
                    success_count += 1
                    emit_log_event(
                        LogLevel.DEBUG,
                        f"EventBusService: Unsubscribed from pattern {pattern}",
                        {"pattern": pattern},
                    )
                except Exception as e:
                    emit_log_event(
                        LogLevel.WARNING,
                        f"EventBusService: Failed to unsubscribe from pattern {pattern}: {e!s}",
                        {
                            "pattern": pattern,
                            "error_type": type(e).__name__,
                        },
                    )

            emit_log_event(
                LogLevel.INFO,
                f"EventBusService: Cleaned up {success_count}/{len(patterns)} event subscriptions",
                {
                    "success_count": success_count,
                    "total_patterns": len(patterns),
                    "patterns": patterns,
                },
            )

            return success_count == len(patterns)

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"EventBusService: Failed to cleanup event subscriptions: {e!s}",
                {
                    "patterns": patterns,
                    "error_type": type(e).__name__,
                },
            )
            return False

    def validate_event_bus_connection(self, event_bus: ProtocolEventBus) -> bool:
        """
        Validate that event bus connection is working properly.

        Args:
            event_bus: Event bus instance to validate

        Returns:
            bool: True if connection is healthy
        """
        try:
            # Check if event bus is None or not provided
            if not event_bus:
                return False

            # Basic validation - check if event bus has required methods
            required_methods = ["publish", "subscribe", "unsubscribe"]
            for method in required_methods:
                try:
                    # Handle potential exceptions when checking methods on broken event buses
                    if not hasattr(event_bus, method):
                        emit_log_event(
                            LogLevel.WARNING,
                            f"EventBusService: Event bus missing required method {method}",
                            {
                                "event_bus_type": type(event_bus).__name__,
                                "missing_method": method,
                            },
                        )
                        return False

                    # Try to access the method to ensure it's callable
                    method_obj = getattr(event_bus, method)
                    if not callable(method_obj):
                        emit_log_event(
                            LogLevel.WARNING,
                            f"EventBusService: Event bus method {method} is not callable",
                            {
                                "event_bus_type": type(event_bus).__name__,
                                "invalid_method": method,
                            },
                        )
                        return False

                except Exception:
                    # If hasattr, getattr, or callable check fails, the event bus is broken
                    return False

            # Additional validation could include ping/health checks
            # For now, basic method presence is sufficient

            emit_log_event(
                LogLevel.DEBUG,
                "EventBusService: Event bus connection validation passed",
                {
                    "event_bus_type": type(event_bus).__name__,
                    "validated_methods": required_methods,
                },
            )
            return True

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"EventBusService: Event bus validation failed: {e!s}",
                {
                    "event_bus_type": type(event_bus).__name__ if event_bus else None,
                    "error_type": type(e).__name__,
                },
            )
            return False

    def _publish_with_retry(
        self,
        envelope: ModelEventEnvelope,
        max_retries: int,
    ) -> bool:
        """
        Publish event envelope with retry logic.

        Args:
            envelope: Event envelope to publish
            max_retries: Maximum number of retry attempts

        Returns:
            bool: True if published successfully
        """
        if not self._event_bus:
            return False

        for attempt in range(max_retries):
            try:
                self._event_bus.publish(envelope)
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    emit_log_event(
                        LogLevel.ERROR,
                        f"EventBusService: Failed to publish event after {max_retries} attempts: {e!s}",
                        {
                            "envelope_id": str(envelope.envelope_id),
                            "max_retries": max_retries,
                            "error_type": type(e).__name__,
                        },
                    )
                    return False
                # Wait before retry
                time.sleep(self.config.retry_delay_seconds)

        return False
