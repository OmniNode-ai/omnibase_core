# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test suite for MixinContractPublisher.

Tests contract registration, deregistration, and heartbeat publishing.
Validates ONEX standards for contract lifecycle events (OMN-1655).
"""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.events.enum_deregistration_reason import (
    EnumDeregistrationReason,
)
from omnibase_core.mixins.mixin_contract_publisher import MixinContractPublisher
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.contract_registration import (
    CONTRACT_DEREGISTERED_EVENT,
    CONTRACT_REGISTERED_EVENT,
    NODE_HEARTBEAT_EVENT,
    ModelContractDeregisteredEvent,
    ModelContractRegisteredEvent,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class MockNodeWithContractPublisher(MixinContractPublisher):
    """Mock node class that uses MixinContractPublisher."""

    mock_publisher_ref: AsyncMock  # Store reference to mock for test assertions

    def __init__(self, container: Any, publisher: AsyncMock | None = None) -> None:
        """Initialize mock node with contract publisher.

        Args:
            container: Mock container with services.
            publisher: Optional publisher instance.
        """
        self._init_contract_publisher(container, publisher=publisher)
        # Store mock reference for test assertions (avoids mypy issues with Protocol)
        if publisher is not None:
            self.mock_publisher_ref = publisher
        else:
            self.mock_publisher_ref = container.get_service("ProtocolEventBusPublisher")


@pytest.mark.unit
class TestMixinContractPublisher:
    """Test MixinContractPublisher functionality."""

    @pytest.fixture
    def mock_publisher(self) -> AsyncMock:
        """Create mock ProtocolEventBusPublisher."""
        publisher = AsyncMock()
        publisher.publish = AsyncMock()
        publisher.publish_envelope = AsyncMock()
        return publisher

    @pytest.fixture
    def mock_container(self, mock_publisher: AsyncMock) -> Mock:
        """Create mock container with publisher service."""
        container = Mock()
        container.get_service = Mock(return_value=mock_publisher)
        return container

    @pytest.fixture
    def contract_publisher(
        self, mock_container: Mock, mock_publisher: AsyncMock
    ) -> MockNodeWithContractPublisher:
        """Create MixinContractPublisher instance with mock publisher."""
        return MockNodeWithContractPublisher(mock_container, publisher=mock_publisher)

    @pytest.fixture
    def temp_contract_file(self, tmp_path: Path) -> Path:
        """Create temporary contract YAML file."""
        contract = tmp_path / "contract.yaml"
        contract.write_text(
            """name: test-node
version: 1.0.0
type: compute
description: A test node for unit testing
"""
        )
        return contract

    @pytest.fixture
    def temp_contract_file_complex(self, tmp_path: Path) -> Path:
        """Create temporary contract YAML file with complex structure."""
        contract = tmp_path / "contract_complex.yaml"
        contract.write_text(
            """name: complex-test-node
version: 2.5.3
type: orchestrator
description: A complex test node
metadata:
  author: Test Author
  license: MIT
capabilities:
  - compute
  - transform
"""
        )
        return contract

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_initialization_with_explicit_publisher(
        self, mock_container: Mock, mock_publisher: AsyncMock
    ) -> None:
        """Test successful initialization with explicitly provided publisher."""
        node = MockNodeWithContractPublisher(mock_container, publisher=mock_publisher)

        assert hasattr(node, "_contract_publisher")
        assert node._contract_publisher is mock_publisher
        assert node._heartbeat_task is None
        assert node._heartbeat_sequence == 0
        assert node._current_contract_hash is None
        assert node._current_node_name is None
        assert node._current_node_version is None

    def test_initialization_with_container_service(
        self, mock_container: Mock, mock_publisher: AsyncMock
    ) -> None:
        """Test initialization resolves publisher from container."""
        node = MockNodeWithContractPublisher(mock_container)

        mock_container.get_service.assert_called_with("ProtocolEventBusPublisher")
        assert node._contract_publisher is mock_publisher

    def test_initialization_missing_publisher_service(self) -> None:
        """Test initialization fails without publisher service."""
        container = Mock()
        container.get_service = Mock(return_value=None)

        with pytest.raises(ModelOnexError) as exc_info:
            MockNodeWithContractPublisher(container)

        assert "ProtocolEventBusPublisher" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.SERVICE_UNAVAILABLE

    # ========================================================================
    # publish_contract Tests
    # ========================================================================

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_success(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test successful contract publication."""
        result = await contract_publisher.publish_contract(temp_contract_file)

        # Verify result type and fields
        assert isinstance(result, ModelContractRegisteredEvent)
        assert result.node_name == "test-node"
        assert result.node_version == ModelSemVer(major=1, minor=0, patch=0)
        assert result.event_type == CONTRACT_REGISTERED_EVENT

        # Verify contract_yaml contains file content
        expected_content = temp_contract_file.read_text()
        assert result.contract_yaml == expected_content

        # Verify contract_hash is SHA256 of content
        expected_hash = hashlib.sha256(expected_content.encode("utf-8")).hexdigest()
        assert result.contract_hash == expected_hash

        # Verify publisher.publish() was called
        contract_publisher.mock_publisher_ref.publish.assert_called_once()
        call_kwargs = contract_publisher.mock_publisher_ref.publish.call_args.kwargs

        assert call_kwargs["topic"] == CONTRACT_REGISTERED_EVENT
        assert call_kwargs["key"] == b"test-node"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_complex_version(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file_complex: Path,
    ) -> None:
        """Test contract publication with complex semantic version."""
        result = await contract_publisher.publish_contract(temp_contract_file_complex)

        assert result.node_name == "complex-test-node"
        assert result.node_version == ModelSemVer(major=2, minor=5, patch=3)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_with_correlation_id(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test contract publication with provided correlation ID."""
        correlation_id = uuid4()

        result = await contract_publisher.publish_contract(
            temp_contract_file, correlation_id=correlation_id
        )

        assert result.correlation_id == correlation_id

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_with_source_node_id(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test contract publication with source node ID."""
        source_node_id = uuid4()

        result = await contract_publisher.publish_contract(
            temp_contract_file, source_node_id=source_node_id
        )

        assert result.source_node_id == source_node_id

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_file_not_found(
        self, contract_publisher: MockNodeWithContractPublisher
    ) -> None:
        """Test publish_contract raises error for non-existent file."""
        non_existent_path = Path("/non/existent/contract.yaml")

        with pytest.raises(ModelOnexError) as exc_info:
            await contract_publisher.publish_contract(non_existent_path)

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_invalid_yaml(
        self, contract_publisher: MockNodeWithContractPublisher, tmp_path: Path
    ) -> None:
        """Test publish_contract raises error for invalid YAML."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("name: [invalid yaml structure")

        with pytest.raises(ModelOnexError) as exc_info:
            await contract_publisher.publish_contract(invalid_yaml)

        assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_missing_name_field(
        self, contract_publisher: MockNodeWithContractPublisher, tmp_path: Path
    ) -> None:
        """Test publish_contract raises error for missing name field."""
        no_name_yaml = tmp_path / "no_name.yaml"
        no_name_yaml.write_text("version: 1.0.0\ntype: compute\n")

        with pytest.raises(ModelOnexError) as exc_info:
            await contract_publisher.publish_contract(no_name_yaml)

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        assert "name" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_non_dict_yaml(
        self, contract_publisher: MockNodeWithContractPublisher, tmp_path: Path
    ) -> None:
        """Test publish_contract raises error for non-dict YAML."""
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text("- item1\n- item2\n")

        with pytest.raises(ModelOnexError) as exc_info:
            await contract_publisher.publish_contract(list_yaml)

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        assert (
            "mapping" in str(exc_info.value).lower()
            or "dict" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_stores_state(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test publish_contract stores state for heartbeats and deregistration."""
        await contract_publisher.publish_contract(temp_contract_file)

        assert contract_publisher._current_node_name == "test-node"
        assert contract_publisher._current_node_version == ModelSemVer(
            major=1, minor=0, patch=0
        )
        assert contract_publisher._current_contract_hash is not None
        assert len(contract_publisher._current_contract_hash) == 64  # SHA256 hex length

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_default_version(
        self, contract_publisher: MockNodeWithContractPublisher, tmp_path: Path
    ) -> None:
        """Test publish_contract uses default version when not specified."""
        no_version_yaml = tmp_path / "no_version.yaml"
        no_version_yaml.write_text("name: test-node\ntype: compute\n")

        result = await contract_publisher.publish_contract(no_version_yaml)

        # Default version should be 0.0.0
        assert result.node_version == ModelSemVer(major=0, minor=0, patch=0)

    # ========================================================================
    # publish_deregistration Tests
    # ========================================================================

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_deregistration_success(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test successful deregistration event publication."""
        # First publish contract to set state
        await contract_publisher.publish_contract(temp_contract_file)

        # Reset mock to verify deregistration call
        contract_publisher.mock_publisher_ref.publish.reset_mock()

        # Publish deregistration
        result = await contract_publisher.publish_deregistration(
            reason=EnumDeregistrationReason.SHUTDOWN
        )

        # Verify result
        assert isinstance(result, ModelContractDeregisteredEvent)
        assert result.node_name == "test-node"
        assert result.reason == EnumDeregistrationReason.SHUTDOWN
        assert result.event_type == CONTRACT_DEREGISTERED_EVENT

        # Verify publisher was called
        contract_publisher.mock_publisher_ref.publish.assert_called_once()
        call_kwargs = contract_publisher.mock_publisher_ref.publish.call_args.kwargs
        assert call_kwargs["topic"] == CONTRACT_DEREGISTERED_EVENT

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_deregistration_custom_reason_upgrade(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test deregistration with UPGRADE reason."""
        await contract_publisher.publish_contract(temp_contract_file)

        result = await contract_publisher.publish_deregistration(
            reason=EnumDeregistrationReason.UPGRADE
        )

        assert result is not None
        assert result.reason == EnumDeregistrationReason.UPGRADE
        assert result.reason.is_planned()

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_deregistration_custom_reason_manual(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test deregistration with MANUAL reason."""
        await contract_publisher.publish_contract(temp_contract_file)

        result = await contract_publisher.publish_deregistration(
            reason=EnumDeregistrationReason.MANUAL
        )

        assert result is not None
        assert result.reason == EnumDeregistrationReason.MANUAL

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_deregistration_with_correlation_id(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test deregistration with correlation ID."""
        await contract_publisher.publish_contract(temp_contract_file)
        correlation_id = uuid4()

        result = await contract_publisher.publish_deregistration(
            reason=EnumDeregistrationReason.SHUTDOWN, correlation_id=correlation_id
        )

        assert result is not None
        assert result.correlation_id == correlation_id

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_deregistration_without_prior_registration(
        self, contract_publisher: MockNodeWithContractPublisher
    ) -> None:
        """Test deregistration returns None if no contract was registered."""
        result = await contract_publisher.publish_deregistration(
            reason=EnumDeregistrationReason.SHUTDOWN
        )

        assert result is None
        # Publisher should not have been called
        contract_publisher.mock_publisher_ref.publish.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_deregistration_default_reason(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test deregistration uses SHUTDOWN as default reason."""
        await contract_publisher.publish_contract(temp_contract_file)

        result = await contract_publisher.publish_deregistration()

        assert result is not None
        assert result.reason == EnumDeregistrationReason.SHUTDOWN

    # ========================================================================
    # Heartbeat Tests
    # ========================================================================

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_start_heartbeat(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test starting heartbeat publishes events."""
        await contract_publisher.publish_contract(temp_contract_file)
        contract_publisher.mock_publisher_ref.publish.reset_mock()

        # Start heartbeat with short interval
        await contract_publisher.start_heartbeat(interval_seconds=1)

        # Wait for at least one heartbeat
        await asyncio.sleep(1.5)

        # Stop heartbeat
        await contract_publisher.stop_heartbeat()

        # Verify heartbeat events were published
        assert contract_publisher.mock_publisher_ref.publish.call_count >= 1

        # Verify the call was to heartbeat topic
        call_kwargs = contract_publisher.mock_publisher_ref.publish.call_args.kwargs
        assert call_kwargs["topic"] == NODE_HEARTBEAT_EVENT

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_heartbeat_sequence_increments(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test heartbeat sequence number increments."""
        await contract_publisher.publish_contract(temp_contract_file)
        contract_publisher.mock_publisher_ref.publish.reset_mock()

        initial_sequence = contract_publisher._heartbeat_sequence
        assert initial_sequence == 0

        # Start heartbeat
        await contract_publisher.start_heartbeat(interval_seconds=1)

        # Wait for heartbeats
        await asyncio.sleep(2.5)

        # Stop heartbeat
        await contract_publisher.stop_heartbeat()

        # Sequence should have incremented
        assert contract_publisher._heartbeat_sequence > initial_sequence

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_heartbeat_cancellation(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test heartbeat can be cleanly cancelled."""
        await contract_publisher.publish_contract(temp_contract_file)

        # Start heartbeat
        await contract_publisher.start_heartbeat(interval_seconds=1)

        assert contract_publisher._heartbeat_task is not None
        assert not contract_publisher._heartbeat_task.done()

        # Cancel heartbeat
        await contract_publisher.stop_heartbeat()

        # Task should be cleaned up
        assert contract_publisher._heartbeat_task is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_heartbeat_already_running(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test starting heartbeat when already running is a no-op."""
        await contract_publisher.publish_contract(temp_contract_file)

        # Start heartbeat twice
        await contract_publisher.start_heartbeat(interval_seconds=1)
        first_task = contract_publisher._heartbeat_task

        await contract_publisher.start_heartbeat(interval_seconds=2)
        second_task = contract_publisher._heartbeat_task

        # Should be same task (no-op on second call)
        assert first_task is second_task

        # Cleanup
        await contract_publisher.stop_heartbeat()

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_heartbeat_interval_validation(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test heartbeat rejects invalid interval."""
        await contract_publisher.publish_contract(temp_contract_file)

        with pytest.raises(ModelOnexError) as exc_info:
            await contract_publisher.start_heartbeat(interval_seconds=0)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "at least 1 second" in exc_info.value.message

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_heartbeat_includes_contract_hash(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test heartbeat includes contract hash for drift detection."""
        await contract_publisher.publish_contract(temp_contract_file)

        # Store expected hash
        expected_hash = contract_publisher._current_contract_hash
        assert expected_hash is not None

        contract_publisher.mock_publisher_ref.publish.reset_mock()

        # Emit single heartbeat
        await contract_publisher._emit_heartbeat()

        # Verify heartbeat was published
        contract_publisher.mock_publisher_ref.publish.assert_called_once()

        # Parse the published event to verify hash
        call_kwargs = contract_publisher.mock_publisher_ref.publish.call_args.kwargs
        event_data = json.loads(call_kwargs["value"].decode("utf-8"))

        assert event_data["contract_hash"] == expected_hash

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_heartbeat_includes_uptime(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test heartbeat includes uptime seconds."""
        await contract_publisher.publish_contract(temp_contract_file)
        contract_publisher.mock_publisher_ref.publish.reset_mock()

        # Wait a bit to accumulate uptime
        await asyncio.sleep(0.5)

        # Emit heartbeat
        await contract_publisher._emit_heartbeat()

        # Parse the published event
        call_kwargs = contract_publisher.mock_publisher_ref.publish.call_args.kwargs
        event_data = json.loads(call_kwargs["value"].decode("utf-8"))

        # Uptime should be positive
        assert event_data["uptime_seconds"] > 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_stop_heartbeat_multiple_times(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test stop_heartbeat is safe to call multiple times."""
        await contract_publisher.publish_contract(temp_contract_file)

        await contract_publisher.start_heartbeat(interval_seconds=1)

        # Stop multiple times - should not raise
        await contract_publisher.stop_heartbeat()
        await contract_publisher.stop_heartbeat()
        await contract_publisher.stop_heartbeat()

        # Task should be None
        assert contract_publisher._heartbeat_task is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_stop_heartbeat_when_not_started(
        self, contract_publisher: MockNodeWithContractPublisher
    ) -> None:
        """Test stop_heartbeat is safe when heartbeat was never started."""
        # Should not raise
        await contract_publisher.stop_heartbeat()
        assert contract_publisher._heartbeat_task is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_heartbeat_without_prior_registration(
        self, contract_publisher: MockNodeWithContractPublisher
    ) -> None:
        """Test heartbeat emits nothing without prior registration."""
        # Emit heartbeat without registration
        await contract_publisher._emit_heartbeat()

        # Publisher should not have been called
        contract_publisher.mock_publisher_ref.publish.assert_not_called()

    # ========================================================================
    # Event Field Tests
    # ========================================================================

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_registration_event_fields(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test registration event has all required fields."""
        result = await contract_publisher.publish_contract(temp_contract_file)

        # Verify all required fields
        assert isinstance(result.event_id, UUID)
        assert isinstance(result.timestamp, datetime)
        assert result.event_type == CONTRACT_REGISTERED_EVENT
        assert isinstance(result.node_name, str)
        assert isinstance(result.node_version, ModelSemVer)
        assert isinstance(result.contract_hash, str)
        assert isinstance(result.contract_yaml, str)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_deregistration_event_fields(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test deregistration event has all required fields."""
        await contract_publisher.publish_contract(temp_contract_file)

        result = await contract_publisher.publish_deregistration(
            reason=EnumDeregistrationReason.SHUTDOWN
        )

        # Verify result is not None (contract was registered)
        assert result is not None

        # Verify all required fields
        assert isinstance(result.event_id, UUID)
        assert isinstance(result.timestamp, datetime)
        assert result.event_type == CONTRACT_DEREGISTERED_EVENT
        assert isinstance(result.node_name, str)
        assert isinstance(result.node_version, ModelSemVer)
        assert isinstance(result.reason, EnumDeregistrationReason)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_heartbeat_event_fields(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test heartbeat event has all required fields."""
        await contract_publisher.publish_contract(temp_contract_file)
        contract_publisher.mock_publisher_ref.publish.reset_mock()

        await contract_publisher._emit_heartbeat()

        # Parse the published event
        call_kwargs = contract_publisher.mock_publisher_ref.publish.call_args.kwargs
        event_data = json.loads(call_kwargs["value"].decode("utf-8"))

        # Verify required fields
        assert "event_id" in event_data
        assert "timestamp" in event_data
        assert event_data["event_type"] == NODE_HEARTBEAT_EVENT
        assert event_data["node_name"] == "test-node"
        assert "node_version" in event_data
        assert "sequence_number" in event_data
        assert "uptime_seconds" in event_data

    # ========================================================================
    # Edge Cases and Error Handling
    # ========================================================================

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_publish_contract_kafka_failure(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test error propagation when Kafka publish fails."""
        contract_publisher.mock_publisher_ref.publish.side_effect = RuntimeError(
            "Kafka connection failed"
        )

        with pytest.raises(RuntimeError) as exc_info:
            await contract_publisher.publish_contract(temp_contract_file)

        assert "Kafka connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_multiple_contract_publications(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
        temp_contract_file_complex: Path,
    ) -> None:
        """Test publishing multiple contracts updates state."""
        # First publication
        result1 = await contract_publisher.publish_contract(temp_contract_file)
        assert contract_publisher._current_node_name == "test-node"

        # Second publication
        result2 = await contract_publisher.publish_contract(temp_contract_file_complex)
        assert contract_publisher._current_node_name == "complex-test-node"

        # Events should have different hashes
        assert result1.contract_hash != result2.contract_hash

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_hash_consistency(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test contract hash is consistent for same content."""
        result1 = await contract_publisher.publish_contract(temp_contract_file)

        # Reset mock
        contract_publisher.mock_publisher_ref.publish.reset_mock()

        # Publish same contract again
        result2 = await contract_publisher.publish_contract(temp_contract_file)

        # Hashes should match
        assert result1.contract_hash == result2.contract_hash

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_timestamp_is_utc(
        self,
        contract_publisher: MockNodeWithContractPublisher,
        temp_contract_file: Path,
    ) -> None:
        """Test event timestamps are UTC timezone-aware."""
        before = datetime.now(UTC)

        result = await contract_publisher.publish_contract(temp_contract_file)

        after = datetime.now(UTC)

        # Timestamp should be between before and after
        assert before <= result.timestamp <= after

        # Timestamp should be timezone-aware
        assert result.timestamp.tzinfo is not None
