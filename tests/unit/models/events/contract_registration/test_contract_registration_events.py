# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for contract registration event models (OMN-1651).

Tests comprehensive model functionality including:
- ModelContractRegisteredEvent: Contract registration with full YAML for replay
- ModelContractDeregisteredEvent: Graceful contract deregistration
- ModelNodeHeartbeatEvent: Node liveness heartbeat

All models extend ModelRuntimeEventBase for consistency.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.events.contract_registration import (
    CONTRACT_DEREGISTERED_EVENT,
    CONTRACT_REGISTERED_EVENT,
    NODE_HEARTBEAT_EVENT,
    ModelContractDeregisteredEvent,
    ModelContractRegisteredEvent,
    ModelNodeHeartbeatEvent,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

pytestmark = pytest.mark.unit


# ============================================================================
# Test: Event Type Constants
# ============================================================================


class TestEventTypeConstants:
    """Tests for event type constants."""

    def test_contract_registered_event_value(self) -> None:
        """Test CONTRACT_REGISTERED_EVENT constant value."""
        assert CONTRACT_REGISTERED_EVENT == "onex.evt.contract-registered.v1"

    def test_contract_deregistered_event_value(self) -> None:
        """Test CONTRACT_DEREGISTERED_EVENT constant value."""
        assert CONTRACT_DEREGISTERED_EVENT == "onex.evt.contract-deregistered.v1"

    def test_node_heartbeat_event_value(self) -> None:
        """Test NODE_HEARTBEAT_EVENT constant value."""
        assert NODE_HEARTBEAT_EVENT == "onex.evt.node-heartbeat.v1"

    def test_event_type_constants_follow_naming_convention(self) -> None:
        """Test that event types follow onex.evt.*.v1 convention."""
        for event_type in [
            CONTRACT_REGISTERED_EVENT,
            CONTRACT_DEREGISTERED_EVENT,
            NODE_HEARTBEAT_EVENT,
        ]:
            assert event_type.startswith("onex.evt.")
            assert event_type.endswith(".v1")


# ============================================================================
# Test: ModelContractRegisteredEvent
# ============================================================================


class TestModelContractRegisteredEventRequiredFields:
    """Tests for required fields in ModelContractRegisteredEvent."""

    def test_create_with_required_fields(self) -> None:
        """Test creating model with required fields."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        event = ModelContractRegisteredEvent(
            node_name="compute-pipeline",
            node_version=version,
            contract_hash="abc123def456",
            contract_yaml="name: compute-pipeline\nversion: 1.2.3",
        )

        assert event.node_name == "compute-pipeline"
        assert event.node_version == version
        assert event.contract_hash == "abc123def456"
        assert event.contract_yaml == "name: compute-pipeline\nversion: 1.2.3"
        # Inherited defaults from ModelRuntimeEventBase
        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.event_type == CONTRACT_REGISTERED_EVENT

    def test_node_name_is_required(self) -> None:
        """Test that node_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractRegisteredEvent(
                node_version=ModelSemVer(major=1, minor=0, patch=0),
                contract_hash="abc123",
                contract_yaml="yaml content",
            )  # type: ignore[call-arg]

        assert "node_name" in str(exc_info.value)

    def test_node_version_is_required(self) -> None:
        """Test that node_version is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractRegisteredEvent(
                node_name="test-node",
                contract_hash="abc123",
                contract_yaml="yaml content",
            )  # type: ignore[call-arg]

        assert "node_version" in str(exc_info.value)

    def test_contract_hash_is_required(self) -> None:
        """Test that contract_hash is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractRegisteredEvent(
                node_name="test-node",
                node_version=ModelSemVer(major=1, minor=0, patch=0),
                contract_yaml="yaml content",
            )  # type: ignore[call-arg]

        assert "contract_hash" in str(exc_info.value)

    def test_contract_yaml_is_required(self) -> None:
        """Test that contract_yaml is required (critical for replay)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractRegisteredEvent(
                node_name="test-node",
                node_version=ModelSemVer(major=1, minor=0, patch=0),
                contract_hash="abc123",
            )  # type: ignore[call-arg]

        assert "contract_yaml" in str(exc_info.value)


class TestModelContractRegisteredEventContractYaml:
    """Tests for contract_yaml field (critical for replay capability)."""

    def test_contract_yaml_preserves_content_exactly(self) -> None:
        """Test that contract_yaml content is preserved exactly."""
        yaml_content = """name: my-node
version: 1.0.0
metadata:
  author: test
  tags:
    - compute
    - pipeline
subscriptions:
  - topic: "onex.runtime.events"
"""
        event = ModelContractRegisteredEvent(
            node_name="my-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            contract_hash="sha256:abc123",
            contract_yaml=yaml_content,
        )

        assert event.contract_yaml == yaml_content

    def test_contract_yaml_handles_multiline_strings(self) -> None:
        """Test contract_yaml with complex multiline YAML."""
        yaml_content = """description: |
  This is a multi-line
  description that spans
  several lines.
"""
        event = ModelContractRegisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            contract_hash="abc123",
            contract_yaml=yaml_content,
        )

        assert "multi-line" in event.contract_yaml


class TestModelContractRegisteredEventInheritedFields:
    """Tests for fields inherited from ModelRuntimeEventBase."""

    def test_event_id_auto_generated(self) -> None:
        """Test that event_id is auto-generated."""
        event1 = ModelContractRegisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            contract_hash="abc123",
            contract_yaml="yaml content",
        )
        event2 = ModelContractRegisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            contract_hash="abc123",
            contract_yaml="yaml content",
        )

        assert event1.event_id is not None
        assert event2.event_id is not None
        assert event1.event_id != event2.event_id

    def test_timestamp_auto_generated_utc(self) -> None:
        """Test that timestamp is auto-generated in UTC."""
        before = datetime.now(UTC)
        event = ModelContractRegisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            contract_hash="abc123",
            contract_yaml="yaml content",
        )
        after = datetime.now(UTC)

        assert before <= event.timestamp <= after

    def test_correlation_id_optional(self) -> None:
        """Test that correlation_id is optional."""
        correlation_id = uuid4()
        event = ModelContractRegisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            contract_hash="abc123",
            contract_yaml="yaml content",
            correlation_id=correlation_id,
        )

        assert event.correlation_id == correlation_id

    def test_source_node_id_optional(self) -> None:
        """Test that source_node_id is optional."""
        source_id = uuid4()
        event = ModelContractRegisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            contract_hash="abc123",
            contract_yaml="yaml content",
            source_node_id=source_id,
        )

        assert event.source_node_id == source_id


class TestModelContractRegisteredEventSerialization:
    """Tests for serialization round-trip."""

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round-trip."""
        original = ModelContractRegisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=2, minor=1, patch=0),
            contract_hash="sha256:def456",
            contract_yaml="name: test-node\nversion: 2.1.0",
            correlation_id=uuid4(),
        )

        json_str = original.model_dump_json()
        restored = ModelContractRegisteredEvent.model_validate_json(json_str)

        assert original.node_name == restored.node_name
        assert original.node_version == restored.node_version
        assert original.contract_hash == restored.contract_hash
        assert original.contract_yaml == restored.contract_yaml
        assert original.correlation_id == restored.correlation_id

    def test_json_parsing_with_string_version(self) -> None:
        """Test JSON parsing with version as dict."""
        json_data = {
            "node_name": "test-node",
            "node_version": {"major": 1, "minor": 0, "patch": 0},
            "contract_hash": "abc123",
            "contract_yaml": "yaml content",
        }

        event = ModelContractRegisteredEvent.model_validate(json_data)

        assert event.node_version.major == 1
        assert event.node_version.minor == 0
        assert event.node_version.patch == 0


# ============================================================================
# Test: ModelContractDeregisteredEvent
# ============================================================================


class TestModelContractDeregisteredEventRequiredFields:
    """Tests for required fields in ModelContractDeregisteredEvent."""

    def test_create_with_required_fields(self) -> None:
        """Test creating model with required fields."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        event = ModelContractDeregisteredEvent(
            node_name="compute-pipeline",
            node_version=version,
            reason="shutdown",
        )

        assert event.node_name == "compute-pipeline"
        assert event.node_version == version
        assert event.reason == "shutdown"
        assert event.event_type == CONTRACT_DEREGISTERED_EVENT

    def test_reason_is_required(self) -> None:
        """Test that reason is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractDeregisteredEvent(
                node_name="test-node",
                node_version=ModelSemVer(major=1, minor=0, patch=0),
            )  # type: ignore[call-arg]

        assert "reason" in str(exc_info.value)


class TestModelContractDeregisteredEventReasons:
    """Tests for different deregistration reasons."""

    def test_reason_shutdown(self) -> None:
        """Test deregistration with shutdown reason."""
        event = ModelContractDeregisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            reason="shutdown",
        )
        assert event.reason == "shutdown"

    def test_reason_upgrade(self) -> None:
        """Test deregistration with upgrade reason."""
        event = ModelContractDeregisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            reason="upgrade",
        )
        assert event.reason == "upgrade"

    def test_reason_manual(self) -> None:
        """Test deregistration with manual reason."""
        event = ModelContractDeregisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            reason="manual",
        )
        assert event.reason == "manual"

    def test_reason_custom_string_allowed(self) -> None:
        """Test that custom reason strings are allowed."""
        event = ModelContractDeregisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            reason="health_check_failure",
        )
        assert event.reason == "health_check_failure"


class TestModelContractDeregisteredEventSerialization:
    """Tests for serialization round-trip."""

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round-trip."""
        original = ModelContractDeregisteredEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=2, patch=3),
            reason="upgrade",
        )

        json_str = original.model_dump_json()
        restored = ModelContractDeregisteredEvent.model_validate_json(json_str)

        assert original.node_name == restored.node_name
        assert original.node_version == restored.node_version
        assert original.reason == restored.reason


# ============================================================================
# Test: ModelNodeHeartbeatEvent
# ============================================================================


class TestModelNodeHeartbeatEventRequiredFields:
    """Tests for required fields in ModelNodeHeartbeatEvent."""

    def test_create_with_required_fields(self) -> None:
        """Test creating model with required fields."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        event = ModelNodeHeartbeatEvent(
            node_name="compute-pipeline",
            node_version=version,
        )

        assert event.node_name == "compute-pipeline"
        assert event.node_version == version
        assert event.event_type == NODE_HEARTBEAT_EVENT
        assert event.timestamp is not None

    def test_node_name_is_required(self) -> None:
        """Test that node_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeHeartbeatEvent(
                node_version=ModelSemVer(major=1, minor=0, patch=0),
            )  # type: ignore[call-arg]

        assert "node_name" in str(exc_info.value)

    def test_node_version_is_required(self) -> None:
        """Test that node_version is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeHeartbeatEvent(
                node_name="test-node",
            )  # type: ignore[call-arg]

        assert "node_version" in str(exc_info.value)


class TestModelNodeHeartbeatEventSerialization:
    """Tests for serialization round-trip."""

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round-trip."""
        original = ModelNodeHeartbeatEvent(
            node_name="test-node",
            node_version=ModelSemVer(major=1, minor=0, patch=5),
        )

        json_str = original.model_dump_json()
        restored = ModelNodeHeartbeatEvent.model_validate_json(json_str)

        assert original.node_name == restored.node_name
        assert original.node_version == restored.node_version
        assert original.event_type == restored.event_type


# ============================================================================
# Test: Import from Package
# ============================================================================


class TestContractRegistrationEventsImport:
    """Tests for model imports from events package."""

    def test_import_from_contract_registration_module(self) -> None:
        """Test models can be imported from contract_registration module."""
        from omnibase_core.models.events.contract_registration import (
            ModelContractDeregisteredEvent as ImportedDeregistered,
        )
        from omnibase_core.models.events.contract_registration import (
            ModelContractRegisteredEvent as ImportedRegistered,
        )
        from omnibase_core.models.events.contract_registration import (
            ModelNodeHeartbeatEvent as ImportedHeartbeat,
        )

        assert ImportedRegistered is ModelContractRegisteredEvent
        assert ImportedDeregistered is ModelContractDeregisteredEvent
        assert ImportedHeartbeat is ModelNodeHeartbeatEvent

    def test_import_from_events_module(self) -> None:
        """Test models can be imported from events module."""
        from omnibase_core.models.events import (
            ModelContractDeregisteredEvent as ImportedDeregistered,
        )
        from omnibase_core.models.events import (
            ModelContractRegisteredEvent as ImportedRegistered,
        )
        from omnibase_core.models.events import (
            ModelNodeHeartbeatEvent as ImportedHeartbeat,
        )

        assert ImportedRegistered is ModelContractRegisteredEvent
        assert ImportedDeregistered is ModelContractDeregisteredEvent
        assert ImportedHeartbeat is ModelNodeHeartbeatEvent

    def test_event_constants_in_module_all(self) -> None:
        """Test that event constants are in __all__."""
        from omnibase_core.models.events import contract_registration

        assert "CONTRACT_REGISTERED_EVENT" in contract_registration.__all__
        assert "CONTRACT_DEREGISTERED_EVENT" in contract_registration.__all__
        assert "NODE_HEARTBEAT_EVENT" in contract_registration.__all__

    def test_models_in_module_all(self) -> None:
        """Test that models are in __all__."""
        from omnibase_core.models.events import contract_registration

        assert "ModelContractRegisteredEvent" in contract_registration.__all__
        assert "ModelContractDeregisteredEvent" in contract_registration.__all__
        assert "ModelNodeHeartbeatEvent" in contract_registration.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
