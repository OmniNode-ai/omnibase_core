# === OmniNode:Metadata ===
# author: OmniNode Team
# description: Discovery responder mixin for ONEX nodes to respond to discovery broadcasts
# === /OmniNode:Metadata ===

import json
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.core.model_discovery_request_response import (
    ModelDiscoveryRequestModelMetadata,
    ModelDiscoveryResponseModelMetadata,
)
from omnibase_core.models.core.model_event_type import (
    create_event_type_from_registry,
    is_event_equal,
)
from omnibase_core.models.core.model_onex_event import ModelOnexEvent as OnexEvent
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.protocols import ProtocolEventBus
from omnibase_core.types.typed_dict_discovery_stats import TypedDictDiscoveryStats

# TypeAdapter for duck-typing validation of discovery request metadata
_DISCOVERY_REQUEST_ADAPTER: TypeAdapter[ModelDiscoveryRequestModelMetadata] = (
    TypeAdapter(ModelDiscoveryRequestModelMetadata)
)

# TypeAdapter for duck-typing validation of OnexEvent payloads
_ONEX_EVENT_ADAPTER: TypeAdapter[OnexEvent] = TypeAdapter(OnexEvent)

# Lazy initialization of introspection adapter to avoid import cycle
_INTROSPECTION_ADAPTER: TypeAdapter[object] | None = None


def _get_introspection_adapter() -> TypeAdapter[object]:
    """Get or create the introspection data TypeAdapter (lazy init to avoid cycles)."""
    global _INTROSPECTION_ADAPTER
    if _INTROSPECTION_ADAPTER is None:
        from omnibase_core.models.core.model_introspection_data import (
            ModelIntrospectionData,
        )

        _INTROSPECTION_ADAPTER = TypeAdapter(ModelIntrospectionData)
    return _INTROSPECTION_ADAPTER


if TYPE_CHECKING:
    from omnibase_core.models.core.model_introspection_data import (
        ModelIntrospectionData,
    )
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
    from omnibase_core.protocols import ProtocolEventMessage
    from omnibase_core.types.typed_dict_mixin_types import (
        TypedDictDiscoveryExtendedStats,
        TypedDictFilterCriteria,
    )


class MixinDiscoveryResponder:
    """
    Mixin for ONEX nodes to respond to discovery broadcasts.

    DISCOVERY RESPONDER PATTERN:
    - All nodes listen to 'onex.discovery.broadcast' channel
    - Respond to NODE_DISCOVERY_REQUEST events with introspection data
    - Include health status, capabilities, and full introspection
    - Rate limiting prevents discovery spam

    USAGE:
    - Mix into any ONEX node class that should participate in discovery
    - Call start_discovery_responder() during node initialization
    - Override get_discovery_capabilities() to customize capabilities
    - Override get_health_status() to provide current health

    RESPONSE CONTENT:
    - Full introspection data from node (ModelIntrospectionData)
    - Current health status and capabilities
    - Event channels and version information
    - Response time metrics

    TYPE SAFETY:
    - Uses TypeAdapter for duck-typing validation of event payloads and metadata
    - No isinstance checks for protocol/duck-typing validation
    - Basic type validation (UUID, ModelSemVer) uses isinstance where appropriate
    - Consistent with ONEX patterns

    THREAD SAFETY:
    Warning: This mixin is NOT thread-safe by default:
    - Instance state (_discovery_stats, _last_response_time) can be corrupted
    - Concurrent access requires external synchronization (threading.Lock)
    - Each thread should use its own instance, or wrap access with locks
    - See docs/guides/THREADING.md for comprehensive threading guidelines
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._discovery_active = False
        self._last_response_time: float = 0.0
        self._response_throttle = 1.0  # Minimum seconds between responses
        self._discovery_stats: TypedDictDiscoveryStats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "filtered_requests": 0,
            "last_request_time": None,
            "error_level_count": 0,
        }
        self._discovery_event_bus: ProtocolEventBus | None = None
        self._discovery_unsubscribe: Callable[[], Awaitable[None]] | None = None

    async def start_discovery_responder(
        self,
        event_bus: ProtocolEventBus,
        response_throttle: float = 1.0,
    ) -> None:
        """
        Start responding to discovery broadcasts.

        Args:
            event_bus: Event bus to listen on
            response_throttle: Minimum seconds between responses (rate limiting)
        """
        if self._discovery_active:
            emit_log_event(
                LogLevel.INFO,
                "Discovery responder already active",
                {"component": "DiscoveryResponder"},
            )
            return

        self._response_throttle = response_throttle
        self._discovery_event_bus = event_bus

        try:
            # Get node_id for group_id - STRICT: Must have node_id attribute
            if not hasattr(self, "node_id"):
                raise ModelOnexError(
                    message="Node must have 'node_id' attribute to participate in discovery",
                    error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                    node_type=self.__class__.__name__,
                )
            node_id = self.node_id
            if not isinstance(node_id, UUID):
                raise ModelOnexError(
                    message="node_id must be UUID type",
                    error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                    node_type=self.__class__.__name__,
                    actual_type=type(node_id).__name__,
                )
            group_id = f"discovery-{node_id}"

            # Subscribe to discovery broadcast channel
            # Create wrapper for protocol message -> envelope conversion
            self._discovery_unsubscribe = await event_bus.subscribe(
                topic="onex.discovery.broadcast",
                group_id=group_id,
                on_message=self._on_discovery_message,
            )

            self._discovery_active = True

            emit_log_event(
                LogLevel.INFO,
                f"Started discovery responder with {response_throttle}s throttle",
                {
                    "component": "DiscoveryResponder",
                    "node_id": node_id,
                    "response_throttle": response_throttle,
                },
            )

        except ModelOnexError:
            # Re-raise ONEX errors directly (already structured)
            raise
        except Exception as e:  # fallback-ok: convert generic exceptions to ONEX errors
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to start discovery responder: {e!s}",
                {"component": "DiscoveryResponder", "error": str(e)},
            )
            raise ModelOnexError(
                message=f"Failed to start discovery responder: {e!s}",
                error_code=EnumCoreErrorCode.DISCOVERY_SETUP_FAILED,
            ) from e

    async def stop_discovery_responder(self) -> None:
        """
        Stop responding to discovery broadcasts.
        """
        if not self._discovery_active:
            return

        self._discovery_active = False

        # Unsubscribe from event bus
        if self._discovery_unsubscribe:
            try:
                await self._discovery_unsubscribe()
            except Exception:
                # cleanup-resilience-ok: cleanup errors during shutdown are non-critical
                pass

        emit_log_event(
            LogLevel.INFO,
            "Stopped discovery responder",
            {"component": "DiscoveryResponder", "stats": self._discovery_stats},
        )

    async def _on_discovery_message(self, message: "ProtocolEventMessage") -> None:
        """
        Adapter method to convert ProtocolEventMessage to ModelEventEnvelope.

        Args:
            message: Low-level protocol message from event bus
        """
        try:
            # Import here to avoid circular dependencies
            from omnibase_core.models.events.model_event_envelope import (
                ModelEventEnvelope,
            )

            # Deserialize the envelope from message value
            # IMPORTANT: Keep raw dict for discovery metadata extraction
            # (ModelEventData loses discovery-specific fields during validation)
            envelope_dict = json.loads(message.value.decode("utf-8"))
            envelope: ModelEventEnvelope[object] = ModelEventEnvelope(**envelope_dict)

            # Pass raw dict for metadata extraction (see _extract_discovery_request_metadata)
            await self._handle_discovery_request(envelope, envelope_dict)

            # Acknowledge message receipt only after successful handling
            await message.ack()

        except (ModelOnexError, RuntimeError, ValueError) as e:
            # Log non-fatal discovery errors for observability
            from omnibase_core.logging.logging_structured import (
                emit_log_event_sync as emit_log_event,
            )

            emit_log_event(
                LogLevel.WARNING,
                "Discovery message processing failed (non-fatal)",
                {
                    "component": "DiscoveryResponder",
                    "error": str(e),
                    "operation": "_on_discovery_message",
                },
            )
            # Track error metrics
            self._discovery_stats["error_level_count"] += 1

            # Acknowledge message even on error to prevent infinite redelivery
            # Discovery failures are non-fatal and should not block the system
            try:
                await message.ack()
            except (RuntimeError, ValueError) as ack_error:
                emit_log_event(
                    LogLevel.ERROR,
                    "Failed to acknowledge discovery message after error",
                    {
                        "component": "DiscoveryResponder",
                        "error": str(ack_error),
                        "operation": "_on_discovery_message",
                    },
                )

    async def _handle_discovery_request(
        self,
        envelope: "ModelEventEnvelope[object]",
        raw_envelope_dict: dict[str, object] | None = None,
    ) -> None:
        """
        Handle incoming discovery requests.

        Discovery Protocol:
        - Events with type "NODE_DISCOVERY_REQUEST" are handled
        - Request metadata is extracted from the raw envelope dict (not Pydantic models)
        - TypeAdapter is used for duck-typing validation (no isinstance checks)

        Args:
            envelope: Event envelope containing the discovery request
            raw_envelope_dict: Raw envelope dict for metadata extraction (bypasses
                ModelEventData validation which loses discovery-specific fields)
        """
        try:
            # STRICT: Envelope must have payload attribute
            if not hasattr(envelope, "payload"):
                raise ModelOnexError(
                    message="Envelope missing required 'payload' attribute",
                    error_code=EnumCoreErrorCode.DISCOVERY_INVALID_REQUEST,
                    envelope_type=type(envelope).__name__,
                )

            # Extract and validate event using TypeAdapter for duck-typing validation
            # (Per ONEX conventions: use TypeAdapter, not isinstance checks)
            # TypeAdapter.validate_python() accepts any Python object (dict, Pydantic model,
            # dataclass, etc.) and validates/coerces it to the target type
            event = envelope.payload

            # Validate event structure using TypeAdapter (duck typing)
            # TypeAdapter handles all input types - no isinstance checks needed
            try:
                onex_event = _ONEX_EVENT_ADAPTER.validate_python(event)
            except ValidationError as e:
                emit_log_event(
                    LogLevel.WARNING,
                    "Event payload validation failed",
                    {
                        "component": "DiscoveryResponder",
                        "validation_error": str(e),
                        "payload_type": type(event).__name__,
                        "operation": "_handle_discovery_request",
                    },
                )
                raise ModelOnexError(
                    message="Event payload does not conform to OnexEvent schema",
                    error_code=EnumCoreErrorCode.DISCOVERY_INVALID_REQUEST,
                    validation_errors=str(e),
                ) from e

            # Check for discovery request event type
            is_discovery_request = is_event_equal(
                onex_event.event_type, "NODE_DISCOVERY_REQUEST"
            )

            if not is_discovery_request:
                return  # Not a discovery request

            # TypedDict ensures correct types at initialization
            self._discovery_stats["requests_received"] += 1
            self._discovery_stats["last_request_time"] = time.time()

            # Check rate limiting
            current_time = time.time()
            if current_time - self._last_response_time < self._response_throttle:
                self._discovery_stats["throttled_requests"] += 1
                return  # Throttled

            # Extract request metadata from raw envelope dict using TypeAdapter
            # Discovery protocol puts metadata in the event's data field (dict format)
            # We use raw_envelope_dict because ModelEventData validation loses discovery fields
            request_metadata = self._extract_discovery_request_metadata(
                raw_envelope_dict
            )
            if request_metadata is None:
                return  # Invalid request format

            # Check if we match filter criteria
            if not self._matches_discovery_criteria(request_metadata):
                self._discovery_stats["filtered_requests"] += 1
                return  # Doesn't match criteria

            # Generate discovery response (updates metrics on success)
            await self._send_discovery_response(onex_event, request_metadata)

        except (ModelOnexError, RuntimeError, ValueError) as e:
            # Log non-fatal discovery errors for observability
            emit_log_event(
                LogLevel.WARNING,
                "Discovery request handling failed (non-fatal)",
                {
                    "component": "DiscoveryResponder",
                    "error": str(e),
                    "operation": "_handle_discovery_request",
                },
            )
            # Track error metrics
            self._discovery_stats["error_level_count"] += 1

    def _extract_discovery_request_metadata(
        self, raw_envelope_dict: dict[str, object] | None
    ) -> ModelDiscoveryRequestModelMetadata | None:
        """
        Extract discovery request metadata from raw envelope dict using TypeAdapter.

        Discovery protocol places metadata in the event's `data` field.
        We extract from raw dict because Pydantic's ModelEventData validation
        loses discovery-specific fields (ModelEventData has different schema).
        This method uses TypeAdapter for duck-typing validation.

        Args:
            raw_envelope_dict: Raw envelope dict before Pydantic validation

        Returns:
            Validated ModelDiscoveryRequestModelMetadata or None if invalid
        """
        if raw_envelope_dict is None:
            return None

        # Navigate to payload.data in raw envelope dict
        # Structure: envelope -> payload -> data
        payload = raw_envelope_dict.get("payload")
        # Note: isinstance check is appropriate here - we're navigating JSON-parsed dict
        # structure, not validating duck-typed protocols
        if not isinstance(payload, dict):
            return None

        data = payload.get("data")
        if data is None:
            return None

        # Use TypeAdapter for duck-typing validation (no isinstance checks needed)
        # TypeAdapter.validate_python() handles dict, Pydantic model, dataclass, etc.
        try:
            return _DISCOVERY_REQUEST_ADAPTER.validate_python(data)
        except ValidationError as e:
            # Log validation failure for observability (DEBUG level - expected noise from untrusted sources)
            emit_log_event(
                LogLevel.DEBUG,
                "Discovery request metadata validation failed",
                {
                    "component": "DiscoveryResponder",
                    "validation_error": str(e),
                    "data_type": type(data).__name__,
                    "operation": "_extract_discovery_request_metadata",
                },
            )
            return None

    def _matches_discovery_criteria(
        self, request: ModelDiscoveryRequestModelMetadata
    ) -> bool:
        """
        Check if this node matches the discovery criteria.

        Args:
            request: Discovery request metadata

        Returns:
            bool: True if node matches criteria, False otherwise
        """
        # Check node type filter
        if request.node_types:
            # Use canonical node_type from get_node_type() if available,
            # otherwise use class name as default
            node_type = (
                self.get_node_type()
                if hasattr(self, "get_node_type")
                else self.__class__.__name__
            )
            if node_type not in request.node_types:
                return False

        # Check capability filter
        if request.requested_capabilities:
            node_capabilities = self.get_discovery_capabilities()
            for required_capability in request.requested_capabilities:
                if required_capability not in node_capabilities:
                    return False

        # Check custom filter criteria
        if request.filter_criteria:
            if not self._matches_custom_criteria(request.filter_criteria):
                return False

        return True

    def _matches_custom_criteria(
        self, filter_criteria: "TypedDictFilterCriteria"
    ) -> bool:
        """
        Check custom filter criteria.

        Override this method in subclasses for custom filtering logic.

        Args:
            filter_criteria: Custom filter criteria (TypedDictFilterCriteria with optional fields)

        Returns:
            bool: True if node matches criteria, False otherwise
        """
        # Default implementation accepts all
        return True

    async def _send_discovery_response(
        self,
        original_event: OnexEvent,
        request: ModelDiscoveryRequestModelMetadata,
    ) -> None:
        """
        Send discovery response back to requester.

        Args:
            original_event: Original discovery request event
            request: Request metadata
        """
        try:
            response_start = time.time()

            # Get node introspection data
            introspection_data = self._get_discovery_introspection()

            # Create discovery response
            # STRICT: Node must have node_id attribute of type UUID
            if not hasattr(self, "node_id"):
                raise ModelOnexError(
                    message="Node must have 'node_id' attribute to send discovery response",
                    error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                    node_type=self.__class__.__name__,
                )

            node_id_value = self.node_id
            if not isinstance(node_id_value, UUID):
                raise ModelOnexError(
                    message="node_id must be UUID type, not string or other type",
                    error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                    node_type=self.__class__.__name__,
                    actual_type=type(node_id_value).__name__,
                    value=str(node_id_value),
                )

            # STRICT: Get version as ModelSemVer - no silent conversions
            version_semver = self._get_node_version()
            if not isinstance(version_semver, ModelSemVer):
                raise ModelOnexError(
                    message="Node version must be ModelSemVer type",
                    error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                    node_type=self.__class__.__name__,
                    actual_type=(
                        type(version_semver).__name__ if version_semver else "None"
                    ),
                )

            # Get event channels as list
            channels_dict = self._get_discovery_event_channels()
            # Flatten the dict to a list of channel names
            event_channels_list: list[str] = []
            if channels_dict:
                for _key, values in channels_dict.items():
                    if isinstance(values, list):
                        event_channels_list.extend(values)

            # Determine node type from method or introspection data
            node_type_value: str
            if hasattr(self, "get_node_type"):
                node_type_value = self.get_node_type()
            elif hasattr(introspection_data, "node_type"):
                node_type_value = introspection_data.node_type
            else:
                node_type_value = self.__class__.__name__

            response_metadata = ModelDiscoveryResponseModelMetadata(
                request_id=request.request_id,
                node_id=node_id_value,
                introspection=introspection_data,
                health_status=self.get_health_status(),
                capabilities=self.get_discovery_capabilities(),
                node_type=node_type_value,
                version=version_semver,
                event_channels=event_channels_list,
                response_time_ms=(time.time() - response_start) * 1000,
            )

            # Discovery Protocol Design Note:
            # The OnexEvent.data field is typed as ModelEventData | None, but discovery
            # protocol requires placing ModelDiscoveryResponseModelMetadata in this field.
            # This is a known protocol limitation - discovery metadata structure does not
            # fit ModelEventData's rigid schema. The receiving end deserializes the dict
            # directly to ModelDiscoveryResponseModelMetadata.
            response_event = OnexEvent(
                event_type=create_event_type_from_registry("DISCOVERY_RESPONSE"),
                node_id=node_id_value,
                correlation_id=original_event.correlation_id,
                data=response_metadata.model_dump(),  # type: ignore[arg-type]  # Discovery protocol places metadata dict in data field; receiver deserializes directly
            )

            # Publish response (assuming we have access to event bus)
            if self._discovery_event_bus:
                # Local import to avoid circular dependency
                from omnibase_core.models.events.model_event_envelope import (
                    ModelEventEnvelope,
                )

                # Wrap in envelope before publishing
                # Note: node_id_value already validated above as UUID type
                envelope = ModelEventEnvelope.create_broadcast(
                    payload=response_event,
                    source_node_id=node_id_value,
                    correlation_id=original_event.correlation_id,
                )

                # Serialize envelope to bytes for protocol event bus
                envelope_bytes = json.dumps(envelope.model_dump()).encode("utf-8")

                # Publish to event bus (protocol requires topic, key, value, headers)
                await self._discovery_event_bus.publish(
                    topic="onex.discovery.response",
                    key=None,
                    value=envelope_bytes,
                )

                # Update metrics only after successful publish
                self._last_response_time = (
                    time.time()
                )  # Use actual publish time, not request time
                self._discovery_stats["responses_sent"] += 1

        except (ModelOnexError, RuntimeError, ValueError) as e:
            # Log discovery errors for observability
            emit_log_event(
                LogLevel.WARNING,
                "Discovery response sending failed",
                {
                    "component": "DiscoveryResponder",
                    "error": str(e),
                    "operation": "_send_discovery_response",
                },
            )
            # Note: error_level_count is incremented by the caller (_handle_discovery_request)
            # to avoid double-counting when exception is re-raised

            # Re-raise to signal failure to caller
            raise ModelOnexError(
                message="Failed to send discovery response",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
            ) from e

    def _get_discovery_introspection(self) -> "ModelIntrospectionData":
        """
        Get introspection data for discovery response.

        STRICT: Node must implement get_introspection_response() method.
        Uses TypeAdapter for duck-typing validation of the response.

        Returns:
            ModelIntrospectionData: Validated node introspection data

        Raises:
            ModelOnexError: If get_introspection_response() method is missing
                or returns incompatible data
        """
        if not hasattr(self, "get_introspection_response"):
            raise ModelOnexError(
                message="Node must implement 'get_introspection_response()' method for discovery",
                error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                node_type=self.__class__.__name__,
            )

        introspection_response = self.get_introspection_response()

        # Use TypeAdapter for duck-typing validation (no isinstance checks needed)
        # TypeAdapter.validate_python() handles Pydantic models, dicts, dataclasses, etc.
        adapter = _get_introspection_adapter()
        try:
            result = adapter.validate_python(introspection_response)
            return cast("ModelIntrospectionData", result)
        except ValidationError as e:
            emit_log_event(
                LogLevel.WARNING,
                "Introspection response validation failed",
                {
                    "component": "DiscoveryResponder",
                    "validation_error": str(e),
                    "response_type": type(introspection_response).__name__,
                    "operation": "_get_discovery_introspection",
                },
            )
            raise ModelOnexError(
                message="Introspection response does not match ModelIntrospectionData schema",
                error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                node_type=self.__class__.__name__,
                validation_errors=str(e),
            ) from e

    def get_discovery_capabilities(self) -> list[str]:
        """
        Get capabilities supported by this node for discovery.

        Override this method in subclasses to provide specific capabilities.

        Returns:
            list[str]: List of capabilities supported by the node
        """
        capabilities = ["discovery", "introspection"]

        # Add capabilities based on available methods
        if hasattr(self, "run"):
            capabilities.append("execution")
        if hasattr(self, "bind"):
            capabilities.append("binding")
        if hasattr(self, "get_introspection_response"):
            capabilities.append("full_introspection")
        if hasattr(self, "handle_event"):
            capabilities.append("event_handling")

        return capabilities

    def get_health_status(self) -> str:
        """
        Get current health status of the node.

        Override this method in subclasses to provide specific health checks.

        Returns:
            str: Health status ('healthy', 'degraded', 'unhealthy')
        """
        # Default implementation - always healthy
        # Subclasses should implement actual health checks
        return "healthy"

    def _get_node_version(self) -> ModelSemVer:
        """
        Get version of the node.

        STRICT: Returns ModelSemVer type only - no string conversions or fallbacks.

        Returns:
            ModelSemVer: Node version

        Raises:
            ModelOnexError: If version attribute is missing or wrong type
        """
        # Check for version attribute first
        if hasattr(self, "version"):
            version = self.version
            if not isinstance(version, ModelSemVer):
                raise ModelOnexError(
                    message="Node 'version' attribute must be ModelSemVer type",
                    error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                    node_type=self.__class__.__name__,
                    actual_type=type(version).__name__,
                )
            return version

        # Check for node_version attribute as fallback
        if hasattr(self, "node_version"):
            node_version = self.node_version
            if not isinstance(node_version, ModelSemVer):
                raise ModelOnexError(
                    message="Node 'node_version' attribute must be ModelSemVer type",
                    error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                    node_type=self.__class__.__name__,
                    actual_type=type(node_version).__name__,
                )
            return node_version

        # No version attribute found
        raise ModelOnexError(
            message="Node must have 'version' or 'node_version' attribute of type ModelSemVer",
            error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
            node_type=self.__class__.__name__,
        )

    def _get_discovery_event_channels(self) -> dict[str, list[str]]:
        """
        Get event channels for discovery response.

        STRICT: Node must implement get_event_channels() method.

        Returns:
            dict[str, list[str]]: Event channels (subscribes_to, publishes_to)

        Raises:
            ModelOnexError: If get_event_channels() method is missing
        """
        if not hasattr(self, "get_event_channels"):
            raise ModelOnexError(
                message="Node must implement 'get_event_channels()' method for discovery",
                error_code=EnumCoreErrorCode.DISCOVERY_INVALID_NODE,
                node_type=self.__class__.__name__,
            )

        channels = self.get_event_channels()
        result: dict[str, list[str]] = channels.model_dump()
        return result

    def get_discovery_stats(self) -> "TypedDictDiscoveryExtendedStats":
        """
        Get discovery responder statistics.

        Returns:
            TypedDictDiscoveryExtendedStats: Discovery statistics with extended status
        """
        from omnibase_core.types.typed_dict_mixin_types import (
            TypedDictDiscoveryExtendedStats,
        )

        return TypedDictDiscoveryExtendedStats(
            requests_received=self._discovery_stats["requests_received"],
            responses_sent=self._discovery_stats["responses_sent"],
            throttled_requests=self._discovery_stats["throttled_requests"],
            filtered_requests=self._discovery_stats["filtered_requests"],
            last_request_time=self._discovery_stats["last_request_time"],
            error_level_count=self._discovery_stats["error_level_count"],
            active=self._discovery_active,
            throttle_seconds=self._response_throttle,
            last_response_time=self._last_response_time,
        )

    def reset_discovery_stats(self) -> None:
        """
        Reset discovery responder statistics.
        """
        self._discovery_stats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "filtered_requests": 0,
            "last_request_time": None,
            "error_level_count": 0,
        }
