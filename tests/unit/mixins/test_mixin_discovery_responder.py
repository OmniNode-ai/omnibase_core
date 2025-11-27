"""
Comprehensive unit tests for MixinDiscoveryResponder.

Tests cover:
- Discovery responder initialization
- Event subscription and handling
- Filter criteria matching
- Capability reporting
- Health status reporting
- Statistics tracking
- Error scenarios
"""

import json
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder
from omnibase_core.models.core.model_discovery_request_response import (
    ModelDiscoveryRequestModelMetadata,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


# Helper class for testing - fully compliant node
class MockIntrospectionResponse(BaseModel):
    """Mock introspection response for testing."""

    node_id: UUID
    node_type: str
    capabilities: list[str]
    health_status: str


class MockEventChannels(BaseModel):
    """Mock event channels for testing."""

    subscribes_to: list[str]
    publishes_to: list[str]


class CompliantTestNode(MixinDiscoveryResponder):
    """Fully compliant test node with all required attributes and methods."""

    def __init__(self):
        super().__init__()
        self.node_id: UUID = uuid4()
        self.version: ModelSemVer = ModelSemVer(major=1, minor=0, patch=0)

    def get_introspection_response(self) -> MockIntrospectionResponse:
        """Return introspection response."""
        return MockIntrospectionResponse(
            node_id=self.node_id,
            node_type=self.__class__.__name__,
            capabilities=self.get_discovery_capabilities(),
            health_status=self.get_health_status(),
        )

    def get_event_channels(self) -> MockEventChannels:
        """Return event channels."""
        return MockEventChannels(
            subscribes_to=["onex.discovery.broadcast"],
            publishes_to=["onex.discovery.response"],
        )


class TestMixinDiscoveryResponderInitialization:
    """Test MixinDiscoveryResponder initialization."""

    def test_mixin_initialization(self):
        """Test MixinDiscoveryResponder initializes properly."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        assert isinstance(node, MixinDiscoveryResponder)
        assert hasattr(node, "_discovery_active")
        assert node._discovery_active is False
        assert node._last_response_time == 0.0
        assert node._response_throttle == 1.0
        assert isinstance(node._discovery_stats, dict)

    def test_initial_stats(self):
        """Test initial statistics are properly set."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        stats = node._discovery_stats

        assert stats["requests_received"] == 0
        assert stats["responses_sent"] == 0
        assert stats["throttled_requests"] == 0
        assert stats["last_request_time"] is None

    def test_mixin_in_multiple_inheritance(self):
        """Test MixinDiscoveryResponder works in multiple inheritance."""

        class BaseNode:
            def __init__(self):
                self.node_id = uuid4()

        class TestNode(MixinDiscoveryResponder, BaseNode):
            pass

        node = TestNode()
        assert isinstance(node, MixinDiscoveryResponder)
        assert isinstance(node, BaseNode)


class TestStartStopDiscoveryResponder:
    """Test start/stop discovery responder functionality."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_start_discovery_responder_success(self):
        """Test starting discovery responder successfully."""

        class TestNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.node_id = uuid4()

        node = TestNode()
        mock_event_bus = AsyncMock()
        mock_event_bus.subscribe = AsyncMock(return_value=AsyncMock())

        await node.start_discovery_responder(mock_event_bus)

        assert node._discovery_active is True
        assert node._discovery_event_bus is mock_event_bus
        mock_event_bus.subscribe.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_start_discovery_responder_custom_throttle(self):
        """Test starting discovery responder with custom throttle."""

        class TestNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.node_id = uuid4()

        node = TestNode()
        mock_event_bus = AsyncMock()
        mock_event_bus.subscribe = AsyncMock(return_value=AsyncMock())

        await node.start_discovery_responder(mock_event_bus, response_throttle=2.5)

        assert node._response_throttle == 2.5

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_start_discovery_responder_already_active(self):
        """Test starting discovery responder when already active."""

        class TestNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.node_id = uuid4()

        node = TestNode()
        mock_event_bus = AsyncMock()
        mock_event_bus.subscribe = AsyncMock(return_value=AsyncMock())

        await node.start_discovery_responder(mock_event_bus)
        call_count = mock_event_bus.subscribe.call_count

        # Try to start again
        await node.start_discovery_responder(mock_event_bus)

        # Should not subscribe again
        assert mock_event_bus.subscribe.call_count == call_count

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_start_discovery_responder_failure(self):
        """Test starting discovery responder with event bus failure."""

        class TestNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.node_id = uuid4()

        node = TestNode()
        mock_event_bus = AsyncMock()
        mock_event_bus.subscribe = AsyncMock(side_effect=Exception("Bus error"))

        with pytest.raises(ModelOnexError):
            await node.start_discovery_responder(mock_event_bus)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_stop_discovery_responder_when_active(self):
        """Test stopping active discovery responder."""

        class TestNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.node_id = uuid4()

        node = TestNode()
        mock_event_bus = AsyncMock()
        mock_unsubscribe = AsyncMock()
        mock_event_bus.subscribe = AsyncMock(return_value=mock_unsubscribe)

        await node.start_discovery_responder(mock_event_bus)
        await node.stop_discovery_responder()

        assert node._discovery_active is False
        mock_unsubscribe.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_stop_discovery_responder_when_inactive(self):
        """Test stopping inactive discovery responder."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        # Should not raise error
        await node.stop_discovery_responder()
        assert node._discovery_active is False


class TestDiscoveryMessageHandling:
    """Test discovery message handling."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_on_discovery_message_invalid_json(self):
        """Test processing message with invalid JSON."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()

        mock_message = Mock()
        mock_message.value = b"invalid json"
        mock_message.ack = AsyncMock()

        # Should not raise error, just silently handle
        await node._on_discovery_message(mock_message)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_on_discovery_message_malformed_envelope(self):
        """Test processing message with malformed envelope."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()

        mock_message = Mock()
        mock_message.value = json.dumps({"invalid": "envelope"}).encode("utf-8")
        mock_message.ack = AsyncMock()

        # Should not raise error, just silently handle
        await node._on_discovery_message(mock_message)


class TestDiscoveryCriteriaMatching:
    """Test discovery criteria matching."""

    def test_matches_criteria_no_filters(self):
        """Test matching with no filters (should match all)."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        request = ModelDiscoveryRequestModelMetadata(request_id=uuid4())

        assert node._matches_discovery_criteria(request) is True

    def test_matches_criteria_node_type_match(self):
        """Test matching with node type filter."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        request = ModelDiscoveryRequestModelMetadata(
            request_id=uuid4(), node_types=["TestNode"]
        )

        assert node._matches_discovery_criteria(request) is True

    def test_matches_criteria_node_type_no_match(self):
        """Test not matching with node type filter."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        request = ModelDiscoveryRequestModelMetadata(
            request_id=uuid4(), node_types=["OtherNode"]
        )

        assert node._matches_discovery_criteria(request) is False

    def test_matches_criteria_capability_match(self):
        """Test matching with capability filter."""

        class TestNode(MixinDiscoveryResponder):
            def get_discovery_capabilities(self):
                return ["discovery", "execution", "custom_capability"]

        node = TestNode()
        request = ModelDiscoveryRequestModelMetadata(
            request_id=uuid4(), requested_capabilities=["discovery"]
        )

        assert node._matches_discovery_criteria(request) is True

    def test_matches_criteria_capability_no_match(self):
        """Test not matching with capability filter."""

        class TestNode(MixinDiscoveryResponder):
            def get_discovery_capabilities(self):
                return ["discovery"]

        node = TestNode()
        request = ModelDiscoveryRequestModelMetadata(
            request_id=uuid4(), requested_capabilities=["missing_capability"]
        )

        assert node._matches_discovery_criteria(request) is False

    def test_matches_custom_criteria_default(self):
        """Test custom criteria matching with default implementation."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        # Default implementation accepts all
        assert node._matches_custom_criteria({"any": "criteria"}) is True

    def test_matches_custom_criteria_override(self):
        """Test custom criteria matching with override."""

        class TestNode(MixinDiscoveryResponder):
            def _matches_custom_criteria(self, filter_criteria):
                return filter_criteria.get("special_flag") == "yes"

        node = TestNode()

        assert node._matches_custom_criteria({"special_flag": "yes"}) is True
        assert node._matches_custom_criteria({"special_flag": "no"}) is False


class TestDiscoveryCapabilities:
    """Test discovery capabilities reporting."""

    def test_get_discovery_capabilities_default(self):
        """Test default capabilities."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        capabilities = node.get_discovery_capabilities()

        assert "discovery" in capabilities
        assert "introspection" in capabilities

    def test_get_discovery_capabilities_with_methods(self):
        """Test capabilities based on available methods."""

        class TestNode(MixinDiscoveryResponder):
            def run(self):
                pass

            def bind(self):
                pass

            def handle_event(self):
                pass

        node = TestNode()
        capabilities = node.get_discovery_capabilities()

        assert "execution" in capabilities
        assert "binding" in capabilities
        assert "event_handling" in capabilities

    def test_get_discovery_capabilities_override(self):
        """Test overriding capabilities."""

        class TestNode(MixinDiscoveryResponder):
            def get_discovery_capabilities(self):
                return ["custom1", "custom2", "custom3"]

        node = TestNode()
        capabilities = node.get_discovery_capabilities()

        assert capabilities == ["custom1", "custom2", "custom3"]


class TestHealthStatus:
    """Test health status reporting."""

    def test_get_health_status_default(self):
        """Test default health status."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        status = node.get_health_status()

        assert status == "healthy"

    def test_get_health_status_override(self):
        """Test overriding health status."""

        class TestNode(MixinDiscoveryResponder):
            def get_health_status(self):
                return "degraded"

        node = TestNode()
        status = node.get_health_status()

        assert status == "degraded"


class TestDiscoveryStatistics:
    """Test discovery statistics functionality."""

    def test_get_discovery_stats_initial(self):
        """Test getting initial statistics."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()
        stats = node.get_discovery_stats()

        assert stats["requests_received"] == 0
        assert stats["responses_sent"] == 0
        assert stats["throttled_requests"] == 0
        assert stats["active"] is False

    def test_reset_discovery_stats(self):
        """Test resetting statistics."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()

        # Modify stats
        node._discovery_stats["requests_received"] = 10
        node._discovery_stats["responses_sent"] = 8
        node._discovery_stats["throttled_requests"] = 2

        # Reset
        node.reset_discovery_stats()

        stats = node.get_discovery_stats()
        assert stats["requests_received"] == 0
        assert stats["responses_sent"] == 0
        assert stats["throttled_requests"] == 0


class TestNodeVersion:
    """Test node version retrieval."""

    def test_get_node_version_with_version_attr(self):
        """Test getting version from version attribute."""

        class TestNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.version = ModelSemVer(major=2, minor=5, patch=0)

        node = TestNode()
        version = node._get_node_version()

        assert isinstance(version, ModelSemVer)
        assert version.major == 2
        assert version.minor == 5
        assert version.patch == 0

    def test_get_node_version_with_node_version_attr(self):
        """Test getting version from node_version attribute."""

        class TestNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.node_version = ModelSemVer(major=3, minor=1, patch=4)

        node = TestNode()
        version = node._get_node_version()

        assert isinstance(version, ModelSemVer)
        assert version.major == 3
        assert version.minor == 1
        assert version.patch == 4

    def test_get_node_version_none(self):
        """Test getting version when not available now raises error."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()

        # BREAKING CHANGE: Now raises error instead of returning None
        with pytest.raises(ModelOnexError) as exc_info:
            node._get_node_version()

        assert "version" in str(exc_info.value).lower()


class TestEventChannels:
    """Test event channels retrieval."""

    def test_get_discovery_event_channels_missing_method(self):
        """Test that missing get_event_channels() method raises error."""

        class TestNode(MixinDiscoveryResponder):
            pass

        node = TestNode()

        # BREAKING CHANGE: Now raises error instead of fallback
        with pytest.raises(ModelOnexError) as exc_info:
            node._get_discovery_event_channels()

        assert "get_event_channels" in str(exc_info.value).lower()

    def test_get_discovery_event_channels_with_method(self):
        """Test event channels retrieval with proper method."""
        node = CompliantTestNode()
        channels = node._get_discovery_event_channels()

        assert isinstance(channels, dict)
        assert "subscribes_to" in channels
        assert "publishes_to" in channels
        assert "onex.discovery.broadcast" in channels["subscribes_to"]
        assert "onex.discovery.response" in channels["publishes_to"]


class TestIntegrationScenarios:
    """Integration tests for discovery responder."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_full_discovery_workflow(self):
        """Test complete discovery request-response workflow."""

        # Use CompliantTestNode which has all required attributes
        node = CompliantTestNode()
        mock_event_bus = AsyncMock()
        mock_event_bus.subscribe = AsyncMock(return_value=AsyncMock())
        mock_event_bus.publish = AsyncMock()

        # Start discovery responder
        await node.start_discovery_responder(mock_event_bus, response_throttle=0.1)

        assert node._discovery_active is True

        # Stop discovery responder
        await node.stop_discovery_responder()

        assert node._discovery_active is False

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_discovery_with_custom_capabilities(self):
        """Test discovery with custom capabilities."""

        class CustomNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.node_id = uuid4()

            def get_discovery_capabilities(self):
                return ["custom_cap1", "custom_cap2", "discovery"]

            def get_health_status(self):
                return "degraded"

        node = CustomNode()

        # Test capabilities
        capabilities = node.get_discovery_capabilities()
        assert "custom_cap1" in capabilities
        assert "custom_cap2" in capabilities

        # Test health status
        assert node.get_health_status() == "degraded"

        # Test criteria matching
        request = ModelDiscoveryRequestModelMetadata(
            request_id=uuid4(), requested_capabilities=["custom_cap1"]
        )
        assert node._matches_discovery_criteria(request) is True


class TestStrictTypeEnforcement:
    """Test strict type enforcement breaking changes."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_start_discovery_responder_missing_node_id(self):
        """Test that starting discovery fails if node_id is missing."""

        class InvalidNode(MixinDiscoveryResponder):
            pass

        node = InvalidNode()
        mock_event_bus = AsyncMock()

        with pytest.raises(ModelOnexError) as exc_info:
            await node.start_discovery_responder(mock_event_bus)

        # Error is wrapped in DISCOVERY_SETUP_FAILED
        assert exc_info.value.error_code == EnumCoreErrorCode.DISCOVERY_SETUP_FAILED

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_start_discovery_responder_wrong_node_id_type(self):
        """Test that starting discovery fails if node_id is not UUID."""

        class InvalidNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.node_id = "not-a-uuid"  # Wrong type

        node = InvalidNode()
        mock_event_bus = AsyncMock()

        with pytest.raises(ModelOnexError) as exc_info:
            await node.start_discovery_responder(mock_event_bus)

        # Error is wrapped in DISCOVERY_SETUP_FAILED
        assert exc_info.value.error_code == EnumCoreErrorCode.DISCOVERY_SETUP_FAILED

    def test_get_node_version_missing(self):
        """Test that _get_node_version fails if no version attribute."""

        class InvalidNode(MixinDiscoveryResponder):
            pass

        node = InvalidNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node._get_node_version()

        assert "version" in str(exc_info.value).lower()

    def test_get_node_version_wrong_type(self):
        """Test that _get_node_version fails if version is not ModelSemVer."""

        class InvalidNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.version = "1.0.0"  # Wrong type (string not ModelSemVer)

        node = InvalidNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node._get_node_version()

        assert "modelsemver" in str(exc_info.value).lower()

    def test_get_node_version_correct_type(self):
        """Test that _get_node_version succeeds with correct ModelSemVer type."""

        class ValidNode(MixinDiscoveryResponder):
            def __init__(self):
                super().__init__()
                self.version = ModelSemVer(major=2, minor=5, patch=3)

        node = ValidNode()
        version = node._get_node_version()

        assert isinstance(version, ModelSemVer)
        assert version.major == 2
        assert version.minor == 5
        assert version.patch == 3

    def test_get_discovery_introspection_missing_method(self):
        """Test that _get_discovery_introspection fails if method missing."""

        class InvalidNode(MixinDiscoveryResponder):
            pass

        node = InvalidNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node._get_discovery_introspection()

        assert "get_introspection_response" in str(exc_info.value).lower()

    def test_get_discovery_introspection_with_method(self):
        """Test that _get_discovery_introspection succeeds with proper method."""
        node = CompliantTestNode()
        introspection = node._get_discovery_introspection()

        assert isinstance(introspection, dict)
        assert "node_id" in introspection
        assert "node_type" in introspection

    def test_get_discovery_event_channels_missing_method(self):
        """Test that _get_discovery_event_channels fails if method missing."""

        class InvalidNode(MixinDiscoveryResponder):
            pass

        node = InvalidNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node._get_discovery_event_channels()

        assert "get_event_channels" in str(exc_info.value).lower()

    def test_get_discovery_event_channels_with_method(self):
        """Test that _get_discovery_event_channels succeeds with proper method."""
        node = CompliantTestNode()
        channels = node._get_discovery_event_channels()

        assert isinstance(channels, dict)
        assert "subscribes_to" in channels
        assert "publishes_to" in channels

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_compliant_node_full_workflow(self):
        """Test that fully compliant node works end-to-end."""
        node = CompliantTestNode()
        mock_event_bus = AsyncMock()
        mock_event_bus.subscribe = AsyncMock(return_value=AsyncMock())

        # Should not raise any errors
        await node.start_discovery_responder(mock_event_bus)

        assert node._discovery_active is True

        # Verify all required methods work
        assert isinstance(node._get_node_version(), ModelSemVer)
        assert isinstance(node._get_discovery_introspection(), dict)
        assert isinstance(node._get_discovery_event_channels(), dict)

        await node.stop_discovery_responder()

        assert node._discovery_active is False
