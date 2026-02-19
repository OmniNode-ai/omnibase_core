# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelCheckpointMetadata validators and edge cases.

These tests focus on the validator logic introduced in PR #251:
- parent_checkpoint_id UUID coercion (string to UUID)
- checkpoint_type enum normalization
- trigger_event enum normalization
- Security-focused tests for malicious inputs

Related tests in test_context_models.py cover basic instantiation,
defaults, immutability, and from_attributes behavior.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumCheckpointType, EnumTriggerEvent
from omnibase_core.models.context import ModelCheckpointMetadata

# =============================================================================
# UUID COERCION TESTS
# =============================================================================


@pytest.mark.unit
class TestModelCheckpointMetadataUUIDCoercion:
    """Tests for parent_checkpoint_id UUID coercion validator."""

    def test_parent_checkpoint_id_accepts_uuid_directly(self) -> None:
        """Test that parent_checkpoint_id accepts UUID objects directly."""
        test_uuid = uuid4()
        metadata = ModelCheckpointMetadata(parent_checkpoint_id=test_uuid)
        assert metadata.parent_checkpoint_id == test_uuid
        assert isinstance(metadata.parent_checkpoint_id, UUID)

    def test_parent_checkpoint_id_coerces_valid_string_to_uuid(self) -> None:
        """Test that valid UUID string is coerced to UUID type."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        metadata = ModelCheckpointMetadata(parent_checkpoint_id=uuid_str)  # type: ignore[arg-type]
        assert metadata.parent_checkpoint_id == UUID(uuid_str)
        assert isinstance(metadata.parent_checkpoint_id, UUID)

    def test_parent_checkpoint_id_coerces_uppercase_uuid_string(self) -> None:
        """Test that uppercase UUID string is coerced to UUID type."""
        uuid_str = "550E8400-E29B-41D4-A716-446655440000"
        metadata = ModelCheckpointMetadata(parent_checkpoint_id=uuid_str)  # type: ignore[arg-type]
        assert isinstance(metadata.parent_checkpoint_id, UUID)

    def test_parent_checkpoint_id_coerces_uuid_without_hyphens(self) -> None:
        """Test that UUID string without hyphens is coerced to UUID type."""
        uuid_str = "550e8400e29b41d4a716446655440000"
        metadata = ModelCheckpointMetadata(parent_checkpoint_id=uuid_str)  # type: ignore[arg-type]
        assert isinstance(metadata.parent_checkpoint_id, UUID)

    def test_parent_checkpoint_id_rejects_invalid_string(self) -> None:
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCheckpointMetadata(parent_checkpoint_id="not-a-valid-uuid")  # type: ignore[arg-type]
        error_message = str(exc_info.value).lower()
        assert "parent_checkpoint_id" in error_message or "uuid" in error_message

    def test_parent_checkpoint_id_rejects_empty_string(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValidationError):
            ModelCheckpointMetadata(parent_checkpoint_id="")  # type: ignore[arg-type]

    def test_parent_checkpoint_id_rejects_partial_uuid(self) -> None:
        """Test that partial UUID raises ValueError."""
        with pytest.raises(ValidationError):
            ModelCheckpointMetadata(parent_checkpoint_id="550e8400-e29b")  # type: ignore[arg-type]

    def test_parent_checkpoint_id_accepts_none(self) -> None:
        """Test that parent_checkpoint_id accepts None."""
        metadata = ModelCheckpointMetadata(parent_checkpoint_id=None)
        assert metadata.parent_checkpoint_id is None

    def test_parent_checkpoint_id_rejects_integer(self) -> None:
        """Test that parent_checkpoint_id rejects integer input."""
        with pytest.raises(ValidationError):
            ModelCheckpointMetadata(parent_checkpoint_id=12345)  # type: ignore[arg-type]

    def test_parent_checkpoint_id_rejects_dict(self) -> None:
        """Test that parent_checkpoint_id rejects dict input."""
        with pytest.raises(ValidationError):
            ModelCheckpointMetadata(parent_checkpoint_id={"uuid": "test"})  # type: ignore[arg-type]

    def test_parent_checkpoint_id_rejects_list(self) -> None:
        """Test that parent_checkpoint_id rejects list input."""
        with pytest.raises(ValidationError):
            ModelCheckpointMetadata(
                parent_checkpoint_id=["550e8400-e29b-41d4-a716-446655440000"]
            )  # type: ignore[arg-type]


# =============================================================================
# ENUM NORMALIZATION TESTS
# =============================================================================


@pytest.mark.unit
class TestModelCheckpointMetadataEnumNormalization:
    """Tests for checkpoint_type and trigger_event enum normalization."""

    # checkpoint_type tests
    def test_checkpoint_type_accepts_enum_directly(self) -> None:
        """Test that checkpoint_type accepts EnumCheckpointType directly."""
        metadata = ModelCheckpointMetadata(checkpoint_type=EnumCheckpointType.AUTOMATIC)
        assert metadata.checkpoint_type == EnumCheckpointType.AUTOMATIC
        assert isinstance(metadata.checkpoint_type, EnumCheckpointType)

    def test_checkpoint_type_normalizes_lowercase_string(self) -> None:
        """Test that lowercase string is normalized to enum."""
        metadata = ModelCheckpointMetadata(checkpoint_type="automatic")
        assert metadata.checkpoint_type == EnumCheckpointType.AUTOMATIC

    def test_checkpoint_type_normalizes_uppercase_string(self) -> None:
        """Test that uppercase string is normalized to enum."""
        metadata = ModelCheckpointMetadata(checkpoint_type="AUTOMATIC")
        assert metadata.checkpoint_type == EnumCheckpointType.AUTOMATIC

    def test_checkpoint_type_normalizes_mixed_case_string(self) -> None:
        """Test that mixed case string is normalized to enum."""
        metadata = ModelCheckpointMetadata(checkpoint_type="Automatic")
        assert metadata.checkpoint_type == EnumCheckpointType.AUTOMATIC

    def test_checkpoint_type_keeps_unknown_string(self) -> None:
        """Test that unknown strings are kept as-is for extensibility."""
        metadata = ModelCheckpointMetadata(checkpoint_type="custom_checkpoint_type")
        assert metadata.checkpoint_type == "custom_checkpoint_type"
        assert isinstance(metadata.checkpoint_type, str)

    # trigger_event tests
    def test_trigger_event_accepts_enum_directly(self) -> None:
        """Test that trigger_event accepts EnumTriggerEvent directly."""
        metadata = ModelCheckpointMetadata(
            trigger_event=EnumTriggerEvent.STAGE_COMPLETE
        )
        assert metadata.trigger_event == EnumTriggerEvent.STAGE_COMPLETE
        assert isinstance(metadata.trigger_event, EnumTriggerEvent)

    def test_trigger_event_normalizes_lowercase_string(self) -> None:
        """Test that lowercase string is normalized to enum."""
        metadata = ModelCheckpointMetadata(trigger_event="stage_complete")
        assert metadata.trigger_event == EnumTriggerEvent.STAGE_COMPLETE

    def test_trigger_event_normalizes_uppercase_string(self) -> None:
        """Test that uppercase string is normalized to enum."""
        metadata = ModelCheckpointMetadata(trigger_event="ERROR")
        assert metadata.trigger_event == EnumTriggerEvent.ERROR

    def test_trigger_event_keeps_unknown_string(self) -> None:
        """Test that unknown strings are kept as-is for extensibility."""
        metadata = ModelCheckpointMetadata(trigger_event="custom_trigger")
        assert metadata.trigger_event == "custom_trigger"
        assert isinstance(metadata.trigger_event, str)

    def test_both_enums_accept_none(self) -> None:
        """Test that both enum fields accept None."""
        metadata = ModelCheckpointMetadata(checkpoint_type=None, trigger_event=None)
        assert metadata.checkpoint_type is None
        assert metadata.trigger_event is None


# =============================================================================
# SECURITY TESTS
# =============================================================================


@pytest.mark.unit
class TestModelCheckpointMetadataSecurity:
    """Security-focused tests for ModelCheckpointMetadata."""

    def test_parent_checkpoint_id_rejects_sql_injection(self) -> None:
        """Test that SQL injection in parent_checkpoint_id is rejected."""
        with pytest.raises(ValidationError):
            ModelCheckpointMetadata(
                parent_checkpoint_id="'; DROP TABLE checkpoints; --"
            )  # type: ignore[arg-type]

    def test_parent_checkpoint_id_rejects_script_injection(self) -> None:
        """Test that script injection in parent_checkpoint_id is rejected."""
        with pytest.raises(ValidationError):
            ModelCheckpointMetadata(
                parent_checkpoint_id="<script>alert('xss')</script>"
            )  # type: ignore[arg-type]

    def test_parent_checkpoint_id_rejects_path_traversal(self) -> None:
        """Test that path traversal in parent_checkpoint_id is rejected."""
        with pytest.raises(ValidationError):
            ModelCheckpointMetadata(parent_checkpoint_id="../../etc/passwd")  # type: ignore[arg-type]

    def test_parent_checkpoint_id_rejects_null_byte_injection(self) -> None:
        """Test that null byte in parent_checkpoint_id is rejected."""
        with pytest.raises(ValidationError):
            ModelCheckpointMetadata(
                parent_checkpoint_id="550e8400-e29b-41d4-a716-446655440000\x00malicious"
            )  # type: ignore[arg-type]

    def test_source_node_handles_special_characters(self) -> None:
        """Test that source_node handles special characters safely."""
        # Since source_node is just a string field, it should accept special chars
        # but they shouldn't cause issues
        metadata = ModelCheckpointMetadata(
            source_node="node_compute_test<>\"&'",
        )
        assert metadata.source_node == "node_compute_test<>\"&'"

    def test_workflow_stage_handles_unicode(self) -> None:
        """Test that workflow_stage handles unicode safely."""
        metadata = ModelCheckpointMetadata(workflow_stage="processing_日本語_stage")
        assert "日本語" in metadata.workflow_stage  # type: ignore[operator]

    def test_error_message_does_not_leak_sensitive_data(self) -> None:
        """Test that error messages don't expose sensitive internal details."""
        try:
            ModelCheckpointMetadata(parent_checkpoint_id="invalid-secret-checkpoint-id")  # type: ignore[arg-type]
        except ValidationError as e:
            error_str = str(e)
            # Should not contain full stack traces
            assert "Traceback" not in error_str
            # Should mention the field name for user guidance
            assert (
                "parent_checkpoint_id" in error_str.lower()
                or "uuid" in error_str.lower()
            )


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.unit
class TestModelCheckpointMetadataEdgeCases:
    """Edge case tests for ModelCheckpointMetadata."""

    def test_all_fields_none(self) -> None:
        """Test creating metadata with all fields as None."""
        metadata = ModelCheckpointMetadata()
        assert metadata.checkpoint_type is None
        assert metadata.source_node is None
        assert metadata.trigger_event is None
        assert metadata.workflow_stage is None
        assert metadata.parent_checkpoint_id is None

    def test_all_fields_populated(self) -> None:
        """Test creating metadata with all fields populated."""
        parent_uuid = uuid4()
        metadata = ModelCheckpointMetadata(
            checkpoint_type="automatic",
            source_node="node_compute_transform",
            trigger_event="stage_complete",
            workflow_stage="processing",
            parent_checkpoint_id=parent_uuid,
        )
        assert metadata.checkpoint_type == EnumCheckpointType.AUTOMATIC
        assert metadata.source_node == "node_compute_transform"
        assert metadata.trigger_event == EnumTriggerEvent.STAGE_COMPLETE
        assert metadata.workflow_stage == "processing"
        assert metadata.parent_checkpoint_id == parent_uuid

    def test_model_dump_round_trip(self) -> None:
        """Test that model can be serialized and deserialized."""
        parent_uuid = uuid4()
        original = ModelCheckpointMetadata(
            checkpoint_type="automatic",
            source_node="test_node",
            trigger_event="stage_complete",
            workflow_stage="validation",
            parent_checkpoint_id=parent_uuid,
        )

        dumped = original.model_dump()
        restored = ModelCheckpointMetadata.model_validate(dumped)

        # Note: enum may be stored as enum or string depending on dump mode
        assert restored.source_node == original.source_node
        assert restored.workflow_stage == original.workflow_stage
        assert restored.parent_checkpoint_id == original.parent_checkpoint_id

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round trip."""
        import json

        parent_uuid = uuid4()
        original = ModelCheckpointMetadata(
            checkpoint_type="manual",
            source_node="test_node",
            parent_checkpoint_id=parent_uuid,
        )

        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        restored = ModelCheckpointMetadata.model_validate(parsed)

        assert restored.source_node == original.source_node
        assert restored.parent_checkpoint_id == original.parent_checkpoint_id

    def test_hashable_for_frozen_model(self) -> None:
        """Test that frozen model is hashable."""
        uuid1 = UUID("550e8400-e29b-41d4-a716-446655440000")
        metadata1 = ModelCheckpointMetadata(
            checkpoint_type="automatic",
            parent_checkpoint_id=uuid1,
        )
        metadata2 = ModelCheckpointMetadata(
            checkpoint_type="automatic",
            parent_checkpoint_id=uuid1,
        )

        assert hash(metadata1) == hash(metadata2)
        assert metadata1 == metadata2

        # Can be used in set
        metadata_set = {metadata1, metadata2}
        assert len(metadata_set) == 1

    def test_unicode_in_string_fields(self) -> None:
        """Test unicode handling in string fields.

        Tests: Japanese (日本語), Russian (Кириллица), Greek (Ελληνικά)
        """
        metadata = ModelCheckpointMetadata(
            source_node="node_日本語_test",
            workflow_stage="Кириллица_stage_Ελληνικά",
        )
        assert "日本語" in metadata.source_node  # type: ignore[operator]
        assert "Кириллица" in metadata.workflow_stage  # type: ignore[operator]
        assert "Ελληνικά" in metadata.workflow_stage  # type: ignore[operator]

    def test_backward_compatible_with_string_checkpoint_id(self) -> None:
        """Test backward compatibility: string checkpoint ID is coerced."""
        # This is the pattern that might exist in legacy serialized data
        uuid_str = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        metadata = ModelCheckpointMetadata(
            parent_checkpoint_id=uuid_str  # type: ignore[arg-type]
        )
        assert isinstance(metadata.parent_checkpoint_id, UUID)
        assert str(metadata.parent_checkpoint_id) == uuid_str
