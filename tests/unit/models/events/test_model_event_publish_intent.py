# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelEventPublishIntent typed payload validation.

This module tests that ModelEventPublishIntent enforces typed-only payloads
as part of the OMN-1008 Core Payload Architecture improvements.

Test Coverage:
    - Typed payload acceptance (ModelEventPayloadUnion types)
    - Dict payload rejection
    - UTC-aware datetime handling
    - Forward reference resolution via utility
    - Subclass handling

Created: 2025-12-26
PR Coverage: OMN-1008 Core Payload Architecture
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_publish_intent import (
    ModelEventPublishIntent,
    _rebuild_model,
)
from omnibase_core.models.events.payloads import (
    ModelNodeRegisteredEvent,
)
from omnibase_core.models.infrastructure.model_retry_policy import ModelRetryPolicy

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_typed_payload() -> ModelNodeRegisteredEvent:
    """Create a sample typed payload for testing."""
    return ModelNodeRegisteredEvent(
        node_id=uuid4(),
        node_name="test-node",
        node_type=EnumNodeKind.COMPUTE,
    )


@pytest.fixture
def sample_correlation_id() -> UUID:
    """Create a sample correlation ID."""
    return uuid4()


# ============================================================================
# Tests for ModelEventPublishIntent Typed Payload Validation
# ============================================================================


@pytest.mark.unit
class TestModelEventPublishIntentTypedPayload:
    """Test ModelEventPublishIntent typed payload enforcement (OMN-1008).

    These tests verify that ModelEventPublishIntent only accepts typed payloads
    from ModelEventPayloadUnion and rejects raw dict payloads.
    """

    def test_typed_payload_accepted(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test that typed payloads implementing ModelEventPayloadUnion are accepted."""
        intent = ModelEventPublishIntent(
            correlation_id=sample_correlation_id,
            created_by="test_node_v1",
            target_topic="dev.omninode.test.events.v1",
            target_key="test-key-123",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
        )

        assert isinstance(intent.target_event_payload, ModelNodeRegisteredEvent)
        assert intent.target_event_payload.node_name == "test-node"
        assert intent.target_event_payload.node_type == EnumNodeKind.COMPUTE

    def test_dict_payload_rejected(self, sample_correlation_id: UUID) -> None:
        """Test that raw dict payloads are rejected.

        This test verifies the OMN-1008 requirement that dict payloads
        are no longer accepted - only typed payloads from ModelEventPayloadUnion.
        """
        dict_payload = {
            "node_id": str(uuid4()),
            "node_name": "dict-node",
            "node_type": "COMPUTE",
            "event_type": "onex.runtime.node.registered",
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelEventPublishIntent(
                correlation_id=sample_correlation_id,
                created_by="test_node_v1",
                target_topic="dev.omninode.test.events.v1",
                target_key="test-key-123",
                target_event_type="NODE_REGISTERED",
                target_event_payload=dict_payload,  # type: ignore[arg-type]
            )

        # Verify the error is about payload validation
        errors = exc_info.value.errors()
        assert any(
            "target_event_payload" in str(error.get("loc", [])) for error in errors
        )

    def test_none_payload_rejected(self, sample_correlation_id: UUID) -> None:
        """Test that None payload is rejected (required field)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventPublishIntent(
                correlation_id=sample_correlation_id,
                created_by="test_node_v1",
                target_topic="dev.omninode.test.events.v1",
                target_key="test-key-123",
                target_event_type="NODE_REGISTERED",
                target_event_payload=None,  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any(
            "target_event_payload" in str(error.get("loc", [])) for error in errors
        )

    def test_string_payload_rejected(self, sample_correlation_id: UUID) -> None:
        """Test that string payloads are rejected."""
        with pytest.raises(ValidationError):
            ModelEventPublishIntent(
                correlation_id=sample_correlation_id,
                created_by="test_node_v1",
                target_topic="dev.omninode.test.events.v1",
                target_key="test-key-123",
                target_event_type="NODE_REGISTERED",
                target_event_payload="invalid string payload",  # type: ignore[arg-type]
            )


# ============================================================================
# Tests for ModelEventPublishIntent UTC Datetime
# ============================================================================


@pytest.mark.unit
class TestModelEventPublishIntentUTCDatetime:
    """Test ModelEventPublishIntent UTC datetime handling (OMN-1008)."""

    def test_created_at_is_utc_aware(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test that created_at is timezone-aware with UTC timezone."""
        intent = ModelEventPublishIntent(
            correlation_id=sample_correlation_id,
            created_by="test_node_v1",
            target_topic="dev.omninode.test.events.v1",
            target_key="test-key-123",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
        )

        # Verify created_at is timezone-aware
        assert intent.created_at.tzinfo is not None
        # Verify it's UTC
        assert intent.created_at.tzinfo == UTC

    def test_explicit_utc_datetime_accepted(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test that explicitly providing UTC datetime works correctly."""
        explicit_time = datetime.now(UTC)

        intent = ModelEventPublishIntent(
            correlation_id=sample_correlation_id,
            created_by="test_node_v1",
            target_topic="dev.omninode.test.events.v1",
            target_key="test-key-123",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
            created_at=explicit_time,
        )

        assert intent.created_at == explicit_time
        assert intent.created_at.tzinfo == UTC


# ============================================================================
# Tests for ModelEventPublishIntent Basic Functionality
# ============================================================================


@pytest.mark.unit
class TestModelEventPublishIntentBasic:
    """Test ModelEventPublishIntent basic creation and validation."""

    def test_intent_creation_minimal(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test creating intent with minimal required fields."""
        intent = ModelEventPublishIntent(
            correlation_id=sample_correlation_id,
            created_by="test_reducer_v1_0_0",
            target_topic="dev.omninode.test.events.v1",
            target_key="test-key",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
        )

        # Verify required fields
        assert intent.correlation_id == sample_correlation_id
        assert intent.created_by == "test_reducer_v1_0_0"
        assert intent.target_topic == "dev.omninode.test.events.v1"
        assert intent.target_key == "test-key"
        assert intent.target_event_type == "NODE_REGISTERED"

        # Verify defaults
        assert isinstance(intent.intent_id, UUID)
        assert isinstance(intent.created_at, datetime)
        assert intent.priority == 5  # Default priority
        assert intent.retry_policy is None

    def test_intent_creation_all_fields(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test creating intent with all fields specified."""
        intent_id = uuid4()
        created_at = datetime.now(UTC)
        retry_policy = ModelRetryPolicy.create_simple(max_retries=3)

        intent = ModelEventPublishIntent(
            intent_id=intent_id,
            correlation_id=sample_correlation_id,
            created_at=created_at,
            created_by="full_test_node_v1_0_0",
            target_topic="dev.omninode.full.events.v1",
            target_key="full-key-456",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
            priority=3,
            retry_policy=retry_policy,
        )

        assert intent.intent_id == intent_id
        assert intent.correlation_id == sample_correlation_id
        assert intent.created_at == created_at
        assert intent.created_by == "full_test_node_v1_0_0"
        assert intent.target_topic == "dev.omninode.full.events.v1"
        assert intent.target_key == "full-key-456"
        assert intent.target_event_type == "NODE_REGISTERED"
        assert intent.priority == 3
        assert intent.retry_policy is not None
        assert intent.retry_policy.max_retries == 3

    def test_intent_priority_validation(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test that priority is validated (1-10 range)."""
        # Valid priority
        intent = ModelEventPublishIntent(
            correlation_id=sample_correlation_id,
            created_by="test_node_v1",
            target_topic="dev.omninode.test.events.v1",
            target_key="test-key",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
            priority=1,  # Highest priority
        )
        assert intent.priority == 1

        intent = ModelEventPublishIntent(
            correlation_id=sample_correlation_id,
            created_by="test_node_v1",
            target_topic="dev.omninode.test.events.v1",
            target_key="test-key",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
            priority=10,  # Lowest priority
        )
        assert intent.priority == 10

        # Invalid priority - too low
        with pytest.raises(ValidationError):
            ModelEventPublishIntent(
                correlation_id=sample_correlation_id,
                created_by="test_node_v1",
                target_topic="dev.omninode.test.events.v1",
                target_key="test-key",
                target_event_type="NODE_REGISTERED",
                target_event_payload=sample_typed_payload,
                priority=0,
            )

        # Invalid priority - too high
        with pytest.raises(ValidationError):
            ModelEventPublishIntent(
                correlation_id=sample_correlation_id,
                created_by="test_node_v1",
                target_topic="dev.omninode.test.events.v1",
                target_key="test-key",
                target_event_type="NODE_REGISTERED",
                target_event_payload=sample_typed_payload,
                priority=11,
            )

    def test_intent_extra_fields_forbidden(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test that extra fields are forbidden (strict schema)."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelEventPublishIntent(
                correlation_id=sample_correlation_id,
                created_by="test_node_v1",
                target_topic="dev.omninode.test.events.v1",
                target_key="test-key",
                target_event_type="NODE_REGISTERED",
                target_event_payload=sample_typed_payload,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )


# ============================================================================
# Tests for Forward Reference Resolution
# ============================================================================


@pytest.mark.unit
class TestModelEventPublishIntentForwardRefs:
    """Test forward reference resolution for ModelEventPublishIntent."""

    def test_rebuild_model_function_exists(self) -> None:
        """Test that _rebuild_model function is exported and callable."""
        assert callable(_rebuild_model)

    def test_rebuild_model_success(self) -> None:
        """Test that _rebuild_model can be called without error.

        This verifies the forward reference resolution mechanism works.
        """
        # Should not raise - model is already rebuilt on module load
        _rebuild_model()

    def test_model_works_after_rebuild(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test that model validates correctly after rebuild."""
        # Rebuild explicitly
        _rebuild_model()

        # Create instance
        intent = ModelEventPublishIntent(
            correlation_id=sample_correlation_id,
            created_by="post_rebuild_test",
            target_topic="dev.omninode.test.events.v1",
            target_key="test-key",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
        )

        assert intent.created_by == "post_rebuild_test"


# ============================================================================
# Tests for Serialization
# ============================================================================


@pytest.mark.unit
class TestModelEventPublishIntentSerialization:
    """Test ModelEventPublishIntent serialization."""

    def test_model_dump_includes_all_fields(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test that model_dump includes all fields."""
        intent = ModelEventPublishIntent(
            correlation_id=sample_correlation_id,
            created_by="serialization_test",
            target_topic="dev.omninode.test.events.v1",
            target_key="test-key",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
        )

        data = intent.model_dump()

        assert "intent_id" in data
        assert "correlation_id" in data
        assert "created_at" in data
        assert "created_by" in data
        assert "target_topic" in data
        assert "target_key" in data
        assert "target_event_type" in data
        assert "target_event_payload" in data
        assert "priority" in data
        assert "retry_policy" in data

    def test_model_dump_json_serializable(
        self,
        sample_typed_payload: ModelNodeRegisteredEvent,
        sample_correlation_id: UUID,
    ) -> None:
        """Test that model can be serialized to JSON."""
        intent = ModelEventPublishIntent(
            correlation_id=sample_correlation_id,
            created_by="json_test",
            target_topic="dev.omninode.test.events.v1",
            target_key="test-key",
            target_event_type="NODE_REGISTERED",
            target_event_payload=sample_typed_payload,
        )

        # Should not raise
        json_str = intent.model_dump_json()
        assert isinstance(json_str, str)
        assert "json_test" in json_str
