"""Unit tests for ModelEnvelope canonical message envelope.

This module tests the ModelEnvelope model which provides:
- Unique message identification (message_id)
- Request correlation tracking (correlation_id)
- Causation chain support (causation_id)
- Entity association (entity_id)
- Automatic timestamp generation (emitted_at)

The ModelEnvelope is designed for strict validation with extra="forbid"
to ensure only defined fields are accepted.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_envelope import ModelEnvelope


class TestModelEnvelopeCreation:
    """Tests for ModelEnvelope creation and defaults."""

    def test_envelope_creation_with_required_fields(self) -> None:
        """Test envelope can be created with only required fields."""
        correlation_id = uuid4()
        entity_id = "node-123"

        envelope = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id=entity_id,
        )

        assert envelope.correlation_id == correlation_id
        assert envelope.entity_id == entity_id
        assert isinstance(envelope.message_id, UUID)
        assert isinstance(envelope.emitted_at, datetime)
        assert envelope.causation_id is None

    def test_envelope_creation_with_all_fields(self) -> None:
        """Test envelope can be created with all fields explicitly set."""
        message_id = uuid4()
        correlation_id = uuid4()
        causation_id = uuid4()
        entity_id = "service-abc"
        emitted_at = datetime.now(UTC)

        envelope = ModelEnvelope(
            message_id=message_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            entity_id=entity_id,
            emitted_at=emitted_at,
        )

        assert envelope.message_id == message_id
        assert envelope.correlation_id == correlation_id
        assert envelope.causation_id == causation_id
        assert envelope.entity_id == entity_id
        assert envelope.emitted_at == emitted_at

    def test_envelope_default_values(self) -> None:
        """Test that message_id and emitted_at have sensible defaults."""
        correlation_id = uuid4()
        entity_id = "node-456"
        before = datetime.now(UTC)

        envelope = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id=entity_id,
        )

        after = datetime.now(UTC)

        # message_id should be auto-generated UUID
        assert isinstance(envelope.message_id, UUID)
        assert envelope.message_id != UUID(int=0)  # Not a null UUID

        # emitted_at should be set to approximately now
        assert isinstance(envelope.emitted_at, datetime)
        assert before <= envelope.emitted_at <= after

        # causation_id should default to None
        assert envelope.causation_id is None

    def test_envelope_message_ids_are_unique(self) -> None:
        """Test that each envelope gets a unique message_id by default."""
        correlation_id = uuid4()
        entity_id = "node-789"

        envelope1 = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id=entity_id,
        )
        envelope2 = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id=entity_id,
        )

        # Each envelope should have a different message_id
        assert envelope1.message_id != envelope2.message_id


class TestModelEnvelopeValidation:
    """Tests for ModelEnvelope field validation."""

    def test_envelope_rejects_missing_correlation_id(self) -> None:
        """Test that missing correlation_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnvelope(entity_id="node-123")  # type: ignore[call-arg]

        # Verify the error mentions correlation_id
        error_str = str(exc_info.value)
        assert "correlation_id" in error_str

    def test_envelope_rejects_missing_entity_id(self) -> None:
        """Test that missing entity_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnvelope(correlation_id=uuid4())  # type: ignore[call-arg]

        # Verify the error mentions entity_id
        error_str = str(exc_info.value)
        assert "entity_id" in error_str

    def test_envelope_accepts_null_causation_id(self) -> None:
        """Test that causation_id=None is valid (root messages have no parent)."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
            causation_id=None,
        )

        assert envelope.causation_id is None

    def test_envelope_rejects_empty_entity_id(self) -> None:
        """Test that empty string entity_id is rejected."""
        from omnibase_core.errors import ModelOnexError

        # ModelEnvelope uses ModelOnexError for empty/whitespace validation
        with pytest.raises((ValidationError, ModelOnexError)) as exc_info:
            ModelEnvelope(
                correlation_id=uuid4(),
                entity_id="",  # Empty string should fail
            )

        error_str = str(exc_info.value)
        assert "entity_id" in error_str or "empty" in error_str.lower()

    def test_envelope_rejects_whitespace_only_entity_id(self) -> None:
        """Test that whitespace-only entity_id is rejected."""
        from omnibase_core.errors import ModelOnexError

        # ModelEnvelope uses ModelOnexError for empty/whitespace validation
        with pytest.raises((ValidationError, ModelOnexError)) as exc_info:
            ModelEnvelope(
                correlation_id=uuid4(),
                entity_id="   ",  # Whitespace only should fail
            )

        error_str = str(exc_info.value)
        assert "entity_id" in error_str or "whitespace" in error_str.lower()


class TestModelEnvelopeExtraFieldRejection:
    """Tests for strict model behavior (extra='forbid')."""

    def test_envelope_rejects_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnvelope(
                correlation_id=uuid4(),
                entity_id="node-123",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value).lower()
        # The error should indicate extra field is not allowed
        assert "extra" in error_str or "unknown_field" in error_str

    def test_envelope_rejects_multiple_extra_fields(self) -> None:
        """Test that multiple extra fields are all rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnvelope(
                correlation_id=uuid4(),
                entity_id="node-123",
                extra_field_1="value1",  # type: ignore[call-arg]
                extra_field_2="value2",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "extra_field" in error_str

    def test_envelope_strict_model(self) -> None:
        """Test that the model is configured with extra='forbid'."""
        # This test ensures the model has the correct ConfigDict setting
        # by attempting to use model_construct which bypasses validation
        valid_envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
        )

        # model_config should have extra="forbid"
        config = valid_envelope.model_config
        assert config.get("extra") == "forbid"

    def test_envelope_rejects_payload_field(self) -> None:
        """Test that adding a 'payload' field is rejected (reserved for parent class)."""
        with pytest.raises(ValidationError):
            ModelEnvelope(
                correlation_id=uuid4(),
                entity_id="node-123",
                payload={"data": "value"},  # type: ignore[call-arg]
            )


class TestModelEnvelopeTypeValidation:
    """Tests for ModelEnvelope field type validation."""

    def test_envelope_message_id_is_uuid(self) -> None:
        """Test that message_id is a UUID type."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
        )

        assert isinstance(envelope.message_id, UUID)

    def test_envelope_correlation_id_is_uuid(self) -> None:
        """Test that correlation_id is a UUID type."""
        correlation_id = uuid4()
        envelope = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id="node-123",
        )

        assert isinstance(envelope.correlation_id, UUID)
        assert envelope.correlation_id == correlation_id

    def test_envelope_causation_id_is_uuid_or_none(self) -> None:
        """Test that causation_id is a UUID when set, or None when not."""
        causation_id = uuid4()

        # With causation_id set
        envelope_with_causation = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
            causation_id=causation_id,
        )
        assert isinstance(envelope_with_causation.causation_id, UUID)
        assert envelope_with_causation.causation_id == causation_id

        # Without causation_id
        envelope_without_causation = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-456",
        )
        assert envelope_without_causation.causation_id is None

    def test_envelope_emitted_at_is_datetime(self) -> None:
        """Test that emitted_at is a datetime type."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
        )

        assert isinstance(envelope.emitted_at, datetime)

    def test_envelope_entity_id_is_string(self) -> None:
        """Test that entity_id is a string type."""
        entity_id = "my-service-node-123"
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id=entity_id,
        )

        assert isinstance(envelope.entity_id, str)
        assert envelope.entity_id == entity_id

    def test_envelope_rejects_invalid_uuid_for_correlation_id(self) -> None:
        """Test that invalid UUID strings for correlation_id are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnvelope(
                correlation_id="not-a-uuid",  # type: ignore[arg-type]
                entity_id="node-123",
            )

        error_str = str(exc_info.value)
        assert "correlation_id" in error_str or "uuid" in error_str.lower()

    def test_envelope_rejects_invalid_uuid_for_causation_id(self) -> None:
        """Test that invalid UUID strings for causation_id are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnvelope(
                correlation_id=uuid4(),
                entity_id="node-123",
                causation_id="not-a-uuid",  # type: ignore[arg-type]
            )

        error_str = str(exc_info.value)
        assert "causation_id" in error_str or "uuid" in error_str.lower()


class TestModelEnvelopeSelfReferenceValidation:
    """Tests for self-reference validation."""

    def test_envelope_rejects_self_reference(self) -> None:
        """Test that causation_id cannot equal message_id."""
        from omnibase_core.errors import ModelOnexError

        message_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            ModelEnvelope(
                message_id=message_id,
                correlation_id=uuid4(),
                entity_id="node-123",
                causation_id=message_id,  # Same as message_id - self-reference
            )

        assert "self-reference" in str(exc_info.value).lower()


class TestModelEnvelopeCausationChain:
    """Tests for causation chain relationships."""

    def test_envelope_causation_id_references_parent(self) -> None:
        """Test that child's causation_id correctly references parent's message_id."""
        correlation_id = uuid4()

        # Create parent (root) message
        parent = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id="parent-node",
        )

        # Create child message with causation_id pointing to parent
        child = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id="child-node",
            causation_id=parent.message_id,
        )

        # Verify the chain
        assert child.causation_id == parent.message_id
        assert child.correlation_id == parent.correlation_id

    def test_envelope_causation_chain_integrity(self) -> None:
        """Test that a chain of messages maintains integrity."""
        correlation_id = uuid4()

        # Create a chain: root -> middle -> leaf
        root = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id="root-node",
            causation_id=None,  # Root has no parent
        )

        middle = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id="middle-node",
            causation_id=root.message_id,
        )

        leaf = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id="leaf-node",
            causation_id=middle.message_id,
        )

        # Verify the entire chain
        assert root.causation_id is None
        assert middle.causation_id == root.message_id
        assert leaf.causation_id == middle.message_id

        # All share the same correlation_id
        assert root.correlation_id == correlation_id
        assert middle.correlation_id == correlation_id
        assert leaf.correlation_id == correlation_id

        # All have unique message_ids
        assert len({root.message_id, middle.message_id, leaf.message_id}) == 3

    def test_envelope_parallel_children_share_parent(self) -> None:
        """Test that multiple children can share the same parent causation."""
        correlation_id = uuid4()

        parent = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id="parent-node",
        )

        # Create multiple children from the same parent
        child1 = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id="child-1",
            causation_id=parent.message_id,
        )

        child2 = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id="child-2",
            causation_id=parent.message_id,
        )

        # Both children reference the same parent
        assert child1.causation_id == parent.message_id
        assert child2.causation_id == parent.message_id

        # Children have unique message_ids
        assert child1.message_id != child2.message_id


class TestModelEnvelopeUtilityMethods:
    """Tests for utility methods (is_root, has_same_workflow, is_caused_by)."""

    def test_is_root_returns_true_for_root(self) -> None:
        """Test that is_root returns True for root messages."""
        root = ModelEnvelope.create_root(uuid4(), "node-123")

        assert root.is_root() is True

    def test_is_root_returns_false_for_child(self) -> None:
        """Test that is_root returns False for child messages."""
        root = ModelEnvelope.create_root(uuid4(), "node-123")
        child = root.create_child()

        assert child.is_root() is False

    def test_has_same_workflow_returns_true(self) -> None:
        """Test that has_same_workflow returns True for same correlation."""
        correlation_id = uuid4()

        env1 = ModelEnvelope.create_root(correlation_id, "node-1")
        env2 = ModelEnvelope.create_root(correlation_id, "node-2")

        assert env1.has_same_workflow(env2) is True
        assert env2.has_same_workflow(env1) is True

    def test_has_same_workflow_returns_false(self) -> None:
        """Test that has_same_workflow returns False for different correlations."""
        env1 = ModelEnvelope.create_root(uuid4(), "node-1")
        env2 = ModelEnvelope.create_root(uuid4(), "node-2")

        assert env1.has_same_workflow(env2) is False
        assert env2.has_same_workflow(env1) is False

    def test_is_caused_by_returns_true(self) -> None:
        """Test that is_caused_by returns True for direct parent."""
        root = ModelEnvelope.create_root(uuid4(), "node-123")
        child = root.create_child()

        assert child.is_caused_by(root) is True

    def test_is_caused_by_returns_false_for_unrelated(self) -> None:
        """Test that is_caused_by returns False for unrelated envelopes."""
        root1 = ModelEnvelope.create_root(uuid4(), "node-1")
        root2 = ModelEnvelope.create_root(uuid4(), "node-2")

        assert root1.is_caused_by(root2) is False
        assert root2.is_caused_by(root1) is False

    def test_is_caused_by_returns_false_for_grandparent(self) -> None:
        """Test that is_caused_by returns False for indirect (grandparent) relationship."""
        root = ModelEnvelope.create_root(uuid4(), "node-123")
        child = root.create_child()
        grandchild = child.create_child()

        # Grandchild is NOT directly caused by root
        assert grandchild.is_caused_by(root) is False
        # Grandchild IS directly caused by child
        assert grandchild.is_caused_by(child) is True


class TestModelEnvelopeImmutability:
    """Tests for envelope immutability (frozen=True)."""

    def test_envelope_is_frozen(self) -> None:
        """Test that the envelope is immutable after creation."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
        )

        # Verify frozen=True in config
        config = envelope.model_config
        assert config.get("frozen") is True

        # Attempting to modify should raise an error
        with pytest.raises(ValidationError):
            envelope.entity_id = "new-entity"  # type: ignore[misc]

    def test_envelope_cannot_modify_correlation_id(self) -> None:
        """Test that correlation_id cannot be modified."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
        )

        with pytest.raises(ValidationError):
            envelope.correlation_id = uuid4()  # type: ignore[misc]

    def test_envelope_cannot_modify_message_id(self) -> None:
        """Test that message_id cannot be modified."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
        )

        with pytest.raises(ValidationError):
            envelope.message_id = uuid4()  # type: ignore[misc]

    def test_envelope_cannot_modify_causation_id(self) -> None:
        """Test that causation_id cannot be modified."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
            causation_id=None,
        )

        with pytest.raises(ValidationError):
            envelope.causation_id = uuid4()  # type: ignore[misc]


class TestModelEnvelopeFactoryMethods:
    """Tests for factory methods."""

    def test_create_root_envelope(self) -> None:
        """Test creating a root envelope without causation via class method."""
        correlation_id = uuid4()
        entity_id = "root-service"

        root = ModelEnvelope.create_root(
            correlation_id=correlation_id,
            entity_id=entity_id,
        )

        assert root.correlation_id == correlation_id
        assert root.entity_id == entity_id
        assert root.causation_id is None  # Root has no parent
        assert isinstance(root.message_id, UUID)
        assert isinstance(root.emitted_at, datetime)

    def test_create_child_envelope_inherits_entity_id(self) -> None:
        """Test that create_child inherits entity_id from parent by default."""
        correlation_id = uuid4()
        entity_id = "parent-service"

        parent = ModelEnvelope.create_root(
            correlation_id=correlation_id,
            entity_id=entity_id,
        )

        child = parent.create_child()

        assert child.correlation_id == parent.correlation_id
        assert child.causation_id == parent.message_id
        assert child.entity_id == parent.entity_id  # Inherited
        assert isinstance(child.message_id, UUID)
        assert child.message_id != parent.message_id

    def test_create_child_envelope_with_custom_entity_id(self) -> None:
        """Test that create_child can override entity_id."""
        correlation_id = uuid4()

        parent = ModelEnvelope.create_root(
            correlation_id=correlation_id,
            entity_id="parent-service",
        )

        child = parent.create_child(entity_id="child-service")

        assert child.correlation_id == parent.correlation_id
        assert child.causation_id == parent.message_id
        assert child.entity_id == "child-service"  # Overridden

    def test_create_child_chain(self) -> None:
        """Test creating a chain of children via factory method."""
        correlation_id = uuid4()

        root = ModelEnvelope.create_root(
            correlation_id=correlation_id,
            entity_id="root",
        )

        child1 = root.create_child()
        child2 = child1.create_child()
        child3 = child2.create_child()

        # Verify chain structure
        assert root.causation_id is None
        assert child1.causation_id == root.message_id
        assert child2.causation_id == child1.message_id
        assert child3.causation_id == child2.message_id

        # All share same correlation
        assert child1.correlation_id == correlation_id
        assert child2.correlation_id == correlation_id
        assert child3.correlation_id == correlation_id


class TestModelEnvelopeValidationHelpers:
    """Tests for validation helper functions."""

    def test_validate_envelope_fields_success(self) -> None:
        """Test that valid envelope data passes validation."""
        from omnibase_core.models.common.model_envelope import validate_envelope_fields

        valid_data = {
            "correlation_id": uuid4(),
            "entity_id": "node-123",
        }

        result = validate_envelope_fields(valid_data)
        assert not result.has_errors()

    def test_validate_envelope_fields_missing_correlation_id(self) -> None:
        """Test that missing correlation_id is detected."""
        from omnibase_core.models.common.model_envelope import validate_envelope_fields

        invalid_data: dict[str, object] = {
            "entity_id": "node-123",
        }

        result = validate_envelope_fields(invalid_data)
        assert result.has_errors()
        # Check that correlation_id is mentioned in errors
        error_messages = [str(e) for e in result.errors]
        assert any("correlation_id" in msg for msg in error_messages)

    def test_validate_envelope_fields_missing_entity_id(self) -> None:
        """Test that missing entity_id is detected."""
        from omnibase_core.models.common.model_envelope import validate_envelope_fields

        invalid_data = {
            "correlation_id": uuid4(),
        }

        result = validate_envelope_fields(invalid_data)
        assert result.has_errors()
        error_messages = [str(e) for e in result.errors]
        assert any("entity_id" in msg for msg in error_messages)

    def test_validate_envelope_fields_empty_entity_id(self) -> None:
        """Test that empty entity_id is detected."""
        from omnibase_core.models.common.model_envelope import validate_envelope_fields

        invalid_data = {
            "correlation_id": uuid4(),
            "entity_id": "",
        }

        result = validate_envelope_fields(invalid_data)
        assert result.has_errors()

    def test_validate_envelope_fields_invalid_uuid_format(self) -> None:
        """Test that invalid UUID format is detected."""
        from omnibase_core.models.common.model_envelope import validate_envelope_fields

        invalid_data = {
            "correlation_id": "not-a-uuid",
            "entity_id": "node-123",
        }

        result = validate_envelope_fields(invalid_data)
        assert result.has_errors()

    def test_validate_envelope_fields_self_reference(self) -> None:
        """Test that self-reference (message_id == causation_id) is detected."""
        from omnibase_core.models.common.model_envelope import validate_envelope_fields

        message_id = uuid4()
        invalid_data = {
            "correlation_id": uuid4(),
            "entity_id": "node-123",
            "message_id": message_id,
            "causation_id": message_id,  # Same as message_id
        }

        result = validate_envelope_fields(invalid_data)
        assert result.has_errors()

    def test_validate_envelope_fields_entity_id_too_long(self) -> None:
        """Test that entity_id exceeding max length is detected."""
        from omnibase_core.models.common.model_envelope import validate_envelope_fields

        long_entity_id = "x" * 513  # Exceeds 512 char limit
        invalid_data = {
            "correlation_id": uuid4(),
            "entity_id": long_entity_id,
        }

        result = validate_envelope_fields(invalid_data)
        assert result.has_errors()
        # Verify error mentions length
        error_messages = [str(e) for e in result.errors]
        assert any("length" in msg.lower() or "512" in msg for msg in error_messages)


class TestValidateCausationChain:
    """Tests for the validate_causation_chain helper function."""

    def test_validate_causation_chain_valid(self) -> None:
        """Test that a valid causation chain passes validation."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child = root.create_child()

        result = validate_causation_chain([root, child])
        assert result is True

    def test_validate_causation_chain_empty_list(self) -> None:
        """Test that empty list is valid."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        result = validate_causation_chain([])
        assert result is True

    def test_validate_causation_chain_single_root(self) -> None:
        """Test that single root envelope is valid."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        root = ModelEnvelope.create_root(uuid4(), "node-1")

        result = validate_causation_chain([root])
        assert result is True

    def test_validate_causation_chain_missing_parent(self) -> None:
        """Test that missing parent in chain is detected."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child = root.create_child()

        # Only include child, not root - child's causation_id references missing message
        result = validate_causation_chain([child])
        assert result is False

    def test_validate_causation_chain_different_correlations(self) -> None:
        """Test that envelopes with different correlation_ids are detected."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        env1 = ModelEnvelope.create_root(uuid4(), "node-1")
        env2 = ModelEnvelope.create_root(uuid4(), "node-2")  # Different correlation

        result = validate_causation_chain([env1, env2])
        assert result is False

    def test_validate_causation_chain_long_chain(self) -> None:
        """Test validation of a longer causation chain."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child1 = root.create_child()
        child2 = child1.create_child()
        child3 = child2.create_child()

        result = validate_causation_chain([root, child1, child2, child3])
        assert result is True

    def test_validate_causation_chain_with_max_depth_none_backwards_compatible(
        self,
    ) -> None:
        """Test that max_chain_depth=None preserves backwards compatible behavior."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child1 = root.create_child()
        child2 = child1.create_child()
        child3 = child2.create_child()
        child4 = child3.create_child()

        # Long chain should pass with max_chain_depth=None (default)
        result = validate_causation_chain([root, child1, child2, child3, child4])
        assert result is True

        result_explicit_none = validate_causation_chain(
            [root, child1, child2, child3, child4], max_chain_depth=None
        )
        assert result_explicit_none is True

    def test_validate_causation_chain_max_depth_pass(self) -> None:
        """Test that chain within max_chain_depth passes."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child = root.create_child()

        # Chain depth is 1 (root -> child), should pass with max_chain_depth=1
        result = validate_causation_chain([root, child], max_chain_depth=1)
        assert result is True

        # Should also pass with higher limit
        result_higher = validate_causation_chain([root, child], max_chain_depth=5)
        assert result_higher is True

    def test_validate_causation_chain_max_depth_fail(self) -> None:
        """Test that chain exceeding max_chain_depth fails."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child = root.create_child()

        # Chain depth is 1 (root -> child), should fail with max_chain_depth=0
        result = validate_causation_chain([root, child], max_chain_depth=0)
        assert result is False

    def test_validate_causation_chain_max_depth_exact_boundary(self) -> None:
        """Test max_chain_depth at exact boundary."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child1 = root.create_child()
        child2 = child1.create_child()

        # Chain depth is 2 (root -> child1 -> child2)
        # Should pass at exactly max_chain_depth=2
        result_pass = validate_causation_chain(
            [root, child1, child2], max_chain_depth=2
        )
        assert result_pass is True

        # Should fail at max_chain_depth=1
        result_fail = validate_causation_chain(
            [root, child1, child2], max_chain_depth=1
        )
        assert result_fail is False

    def test_validate_causation_chain_max_depth_empty_list(self) -> None:
        """Test that empty list passes with any max_chain_depth."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        result = validate_causation_chain([], max_chain_depth=0)
        assert result is True

        result_higher = validate_causation_chain([], max_chain_depth=10)
        assert result_higher is True

    def test_validate_causation_chain_max_depth_single_root(self) -> None:
        """Test that single root (depth=0) passes with max_chain_depth=0."""
        from omnibase_core.models.common.model_envelope import validate_causation_chain

        root = ModelEnvelope.create_root(uuid4(), "node-1")

        result = validate_causation_chain([root], max_chain_depth=0)
        assert result is True


class TestGetChainDepth:
    """Tests for the get_chain_depth helper function."""

    def test_get_chain_depth_empty_list(self) -> None:
        """Test that empty list returns depth 0."""
        from omnibase_core.models.common.model_envelope import get_chain_depth

        result = get_chain_depth([])
        assert result == 0

    def test_get_chain_depth_single_root(self) -> None:
        """Test that single root envelope returns depth 0."""
        from omnibase_core.models.common.model_envelope import get_chain_depth

        root = ModelEnvelope.create_root(uuid4(), "node-1")

        result = get_chain_depth([root])
        assert result == 0

    def test_get_chain_depth_chain_of_two(self) -> None:
        """Test chain of 2 envelopes (root -> child) returns depth 1."""
        from omnibase_core.models.common.model_envelope import get_chain_depth

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child = root.create_child()

        result = get_chain_depth([root, child])
        assert result == 1

    def test_get_chain_depth_chain_of_five(self) -> None:
        """Test chain of 5 envelopes returns depth 4."""
        from omnibase_core.models.common.model_envelope import get_chain_depth

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child1 = root.create_child()
        child2 = child1.create_child()
        child3 = child2.create_child()
        child4 = child3.create_child()

        result = get_chain_depth([root, child1, child2, child3, child4])
        assert result == 4

    def test_get_chain_depth_order_independent(self) -> None:
        """Test that chain depth calculation is order-independent."""
        from omnibase_core.models.common.model_envelope import get_chain_depth

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child1 = root.create_child()
        child2 = child1.create_child()

        # Different orderings should produce same depth
        result_ordered = get_chain_depth([root, child1, child2])
        result_reversed = get_chain_depth([child2, child1, root])
        result_shuffled = get_chain_depth([child1, root, child2])

        assert result_ordered == 2
        assert result_reversed == 2
        assert result_shuffled == 2

    def test_get_chain_depth_branching_chains(self) -> None:
        """Test depth calculation with branching (multiple children from one parent)."""
        from omnibase_core.models.common.model_envelope import get_chain_depth

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")

        # Two children from root (parallel branches)
        child_a = root.create_child(entity_id="child-a")
        child_b = root.create_child(entity_id="child-b")

        # Branch A continues deeper
        grandchild_a = child_a.create_child()

        # The deepest path is: root -> child_a -> grandchild_a (depth 2)
        result = get_chain_depth([root, child_a, child_b, grandchild_a])
        assert result == 2

    def test_get_chain_depth_multiple_roots(self) -> None:
        """Test depth with multiple root envelopes (same correlation_id)."""
        from omnibase_core.models.common.model_envelope import get_chain_depth

        correlation_id = uuid4()
        root1 = ModelEnvelope.create_root(correlation_id, "root-1")
        root2 = ModelEnvelope.create_root(correlation_id, "root-2")

        child1 = root1.create_child()
        child2 = child1.create_child()

        # root1 -> child1 -> child2 (depth 2)
        # root2 has no children (depth 0 from root2)
        # Max depth should be 2
        result = get_chain_depth([root1, root2, child1, child2])
        assert result == 2

    def test_get_chain_depth_orphan_envelope(self) -> None:
        """Test depth with orphan envelope (missing parent in list)."""
        from omnibase_core.models.common.model_envelope import get_chain_depth

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child = root.create_child()

        # Only include child (orphan - parent not in list)
        # The child has no children, so depth from it is 0
        result = get_chain_depth([child])
        assert result == 0

    def test_get_chain_depth_orphan_with_descendants(self) -> None:
        """Test depth with orphan that has its own descendants."""
        from omnibase_core.models.common.model_envelope import get_chain_depth

        correlation_id = uuid4()
        root = ModelEnvelope.create_root(correlation_id, "node-1")
        child = root.create_child()
        grandchild = child.create_child()

        # Exclude root - child becomes orphan but has grandchild
        # child -> grandchild (depth 1)
        result = get_chain_depth([child, grandchild])
        assert result == 1

    def test_get_chain_depth_exported_in_all(self) -> None:
        """Test that get_chain_depth is exported in __all__."""
        from omnibase_core.models.common import model_envelope

        assert "get_chain_depth" in model_envelope.__all__


class TestModelEnvelopeSerialization:
    """Tests for serialization and deserialization."""

    def test_envelope_model_dump(self) -> None:
        """Test that envelope can be dumped to dict."""
        correlation_id = uuid4()
        entity_id = "node-123"

        envelope = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id=entity_id,
        )

        data = envelope.model_dump()

        assert data["correlation_id"] == correlation_id
        assert data["entity_id"] == entity_id
        assert "message_id" in data
        assert "emitted_at" in data
        assert "causation_id" in data

    def test_envelope_model_dump_json(self) -> None:
        """Test that envelope can be serialized to JSON."""
        correlation_id = uuid4()
        entity_id = "node-123"

        envelope = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id=entity_id,
        )

        json_str = envelope.model_dump_json()

        assert isinstance(json_str, str)
        assert str(correlation_id) in json_str
        assert entity_id in json_str

    def test_envelope_round_trip_serialization(self) -> None:
        """Test that envelope can be serialized and deserialized."""
        correlation_id = uuid4()
        causation_id = uuid4()
        entity_id = "node-123"
        emitted_at = datetime.now(UTC)

        original = ModelEnvelope(
            correlation_id=correlation_id,
            causation_id=causation_id,
            entity_id=entity_id,
            emitted_at=emitted_at,
        )

        # Round-trip through JSON
        json_str = original.model_dump_json()
        restored = ModelEnvelope.model_validate_json(json_str)

        assert restored.correlation_id == original.correlation_id
        assert restored.causation_id == original.causation_id
        assert restored.entity_id == original.entity_id
        assert restored.message_id == original.message_id

    def test_envelope_model_validate_from_dict(self) -> None:
        """Test that envelope can be created from dict via model_validate."""
        message_id = uuid4()
        correlation_id = uuid4()
        entity_id = "node-123"
        emitted_at = datetime.now(UTC)

        data = {
            "message_id": message_id,
            "correlation_id": correlation_id,
            "entity_id": entity_id,
            "emitted_at": emitted_at,
            "causation_id": None,
        }

        envelope = ModelEnvelope.model_validate(data)

        assert envelope.message_id == message_id
        assert envelope.correlation_id == correlation_id
        assert envelope.entity_id == entity_id


class TestModelEnvelopeEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_envelope_with_unicode_entity_id(self) -> None:
        """Test that unicode characters in entity_id are handled."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-\u4e2d\u6587-123",  # Contains Chinese characters
        )

        assert envelope.entity_id == "node-\u4e2d\u6587-123"

    def test_envelope_with_long_entity_id(self) -> None:
        """Test that entity_id exceeding max_length=512 is rejected."""
        long_entity_id = "x" * 513  # Exceeds 512 char limit

        with pytest.raises(ValidationError) as exc_info:
            ModelEnvelope(
                correlation_id=uuid4(),
                entity_id=long_entity_id,
            )

        # Verify error mentions the constraint
        error_str = str(exc_info.value).lower()
        assert (
            "512" in error_str or "string_too_long" in error_str or "max" in error_str
        )

    def test_envelope_with_special_characters_in_entity_id(self) -> None:
        """Test that special characters in entity_id are handled."""
        special_entity_id = "node/with:special@chars#123"

        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id=special_entity_id,
        )

        assert envelope.entity_id == special_entity_id

    def test_envelope_emitted_at_is_timezone_aware(self) -> None:
        """Test that emitted_at is timezone-aware by default."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-123",
        )

        # The datetime should have timezone info
        assert envelope.emitted_at.tzinfo is not None

    def test_envelope_rejects_naive_datetime_for_emitted_at(self) -> None:
        """Test that naive datetime (no timezone) is rejected for emitted_at."""
        from omnibase_core.errors import ModelOnexError

        naive_dt = datetime(2024, 1, 15, 10, 30, 0)  # No timezone

        with pytest.raises(ModelOnexError) as exc_info:
            ModelEnvelope(
                correlation_id=uuid4(),
                entity_id="node-123",
                emitted_at=naive_dt,
            )

        assert "timezone" in str(exc_info.value).lower()


class TestModelEnvelopeRepr:
    """Tests for __repr__ method."""

    def test_repr_includes_all_fields(self) -> None:
        """Test that __repr__ includes all key envelope fields."""
        correlation_id = uuid4()
        entity_id = "node-123"

        envelope = ModelEnvelope(
            correlation_id=correlation_id,
            entity_id=entity_id,
        )

        repr_str = repr(envelope)

        # Should include class name
        assert "ModelEnvelope(" in repr_str

        # Should include all key fields
        assert "message_id=" in repr_str
        assert "correlation_id=" in repr_str
        assert "causation_id=" in repr_str
        assert "entity_id=" in repr_str
        assert "emitted_at=" in repr_str

        # Should include actual values
        assert str(correlation_id) in repr_str
        assert entity_id in repr_str

    def test_repr_is_readable(self) -> None:
        """Test that __repr__ produces human-readable output."""
        envelope = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="test-node",
        )

        repr_str = repr(envelope)

        # Should be a single-line representation suitable for debugging
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0


class TestModelEnvelopeEquality:
    """Tests for equality and comparison."""

    def test_envelope_equality_same_message_id(self) -> None:
        """Test that envelopes with same message_id are equal."""
        message_id = uuid4()
        correlation_id = uuid4()
        entity_id = "node-123"
        emitted_at = datetime.now(UTC)

        envelope1 = ModelEnvelope(
            message_id=message_id,
            correlation_id=correlation_id,
            entity_id=entity_id,
            emitted_at=emitted_at,
        )

        envelope2 = ModelEnvelope(
            message_id=message_id,
            correlation_id=correlation_id,
            entity_id=entity_id,
            emitted_at=emitted_at,
        )

        assert envelope1 == envelope2

    def test_envelope_inequality_different_message_id(self) -> None:
        """Test that envelopes with different message_id are not equal."""
        correlation_id = uuid4()
        entity_id = "node-123"
        emitted_at = datetime.now(UTC)

        envelope1 = ModelEnvelope(
            message_id=uuid4(),
            correlation_id=correlation_id,
            entity_id=entity_id,
            emitted_at=emitted_at,
        )

        envelope2 = ModelEnvelope(
            message_id=uuid4(),
            correlation_id=correlation_id,
            entity_id=entity_id,
            emitted_at=emitted_at,
        )

        assert envelope1 != envelope2

    def test_envelope_hash_for_set_membership(self) -> None:
        """Test that envelopes can be used in sets (if hashable)."""
        envelope1 = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-1",
        )

        envelope2 = ModelEnvelope(
            correlation_id=uuid4(),
            entity_id="node-2",
        )

        # If the model is hashable (frozen=True), this should work
        try:
            envelope_set = {envelope1, envelope2}
            assert len(envelope_set) == 2
        except TypeError:
            # If not hashable (frozen=False), that's expected
            pass
