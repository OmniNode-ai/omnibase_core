# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelSubjectRef.

Tests comprehensive subject reference functionality including:
- Model instantiation with UUID and string IDs
- Immutability (frozen model)
- Optional field handling (namespace, subject_key)
- Field type validation
- Serialization and deserialization
- extra="forbid" behavior
- from_attributes=True behavior
"""

from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_subject_type import EnumSubjectType
from omnibase_core.models.omnimemory.model_subject_ref import ModelSubjectRef

pytestmark = pytest.mark.unit

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_ref_data_uuid() -> dict[str, Any]:
    """Minimal required data for creating a subject ref with UUID."""
    return {
        "subject_type": EnumSubjectType.AGENT,
        "subject_id": uuid4(),
    }


@pytest.fixture
def minimal_ref_data_string() -> dict[str, Any]:
    """Minimal required data for creating a subject ref with string ID."""
    return {
        "subject_type": EnumSubjectType.USER,
        "subject_id": "user-12345",
    }


@pytest.fixture
def full_ref_data() -> dict[str, Any]:
    """Complete data including all optional fields."""
    return {
        "subject_type": EnumSubjectType.WORKFLOW,
        "subject_id": uuid4(),
        "namespace": "production",
        "subject_key": "data-processor-v2",
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelSubjectRefInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_uuid_id(self, minimal_ref_data_uuid: dict[str, Any]) -> None:
        """Test creating ref with UUID subject_id."""
        ref = ModelSubjectRef(**minimal_ref_data_uuid)

        assert ref.subject_type == EnumSubjectType.AGENT
        assert isinstance(ref.subject_id, UUID)
        assert ref.namespace is None
        assert ref.subject_key is None

    def test_create_with_string_id(
        self, minimal_ref_data_string: dict[str, Any]
    ) -> None:
        """Test creating ref with string subject_id."""
        ref = ModelSubjectRef(**minimal_ref_data_string)

        assert ref.subject_type == EnumSubjectType.USER
        assert ref.subject_id == "user-12345"
        assert isinstance(ref.subject_id, str)

    def test_create_with_full_data(self, full_ref_data: dict[str, Any]) -> None:
        """Test creating ref with all fields explicitly set."""
        ref = ModelSubjectRef(**full_ref_data)

        assert ref.subject_type == EnumSubjectType.WORKFLOW
        assert ref.subject_id == full_ref_data["subject_id"]
        assert ref.namespace == "production"
        assert ref.subject_key == "data-processor-v2"

    def test_create_with_namespace_only(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test creating ref with namespace but no subject_key."""
        minimal_ref_data_uuid["namespace"] = "staging"
        ref = ModelSubjectRef(**minimal_ref_data_uuid)

        assert ref.namespace == "staging"
        assert ref.subject_key is None

    def test_create_with_subject_key_only(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test creating ref with subject_key but no namespace."""
        minimal_ref_data_uuid["subject_key"] = "my-agent"
        ref = ModelSubjectRef(**minimal_ref_data_uuid)

        assert ref.namespace is None
        assert ref.subject_key == "my-agent"

    def test_various_subject_types(self) -> None:
        """Test all subject types can be used."""
        subject_types = [
            EnumSubjectType.AGENT,
            EnumSubjectType.USER,
            EnumSubjectType.WORKFLOW,
            EnumSubjectType.PROJECT,
            EnumSubjectType.SERVICE,
            EnumSubjectType.ORG,
            EnumSubjectType.TASK,
            EnumSubjectType.CORPUS,
            EnumSubjectType.SESSION,
            EnumSubjectType.CUSTOM,
        ]
        for subject_type in subject_types:
            ref = ModelSubjectRef(
                subject_type=subject_type,
                subject_id="test-id",
            )
            assert ref.subject_type == subject_type

    def test_subject_type_from_string(self) -> None:
        """Test that subject_type can be provided as string."""
        # NOTE: Intentionally testing Pydantic coercion - mypy correctly flags string where enum expected
        ref = ModelSubjectRef(
            subject_type="agent",  # type: ignore[arg-type]
            subject_id="test-id",
        )
        assert ref.subject_type == EnumSubjectType.AGENT


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelSubjectRefImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_ref_data_uuid: dict[str, Any]) -> None:
        """Test that the model is immutable."""
        ref = ModelSubjectRef(**minimal_ref_data_uuid)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ref.subject_type = EnumSubjectType.USER  # type: ignore[misc]

    def test_cannot_modify_subject_id(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test that subject_id cannot be modified."""
        ref = ModelSubjectRef(**minimal_ref_data_uuid)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ref.subject_id = uuid4()  # type: ignore[misc]

    def test_cannot_modify_namespace(self, full_ref_data: dict[str, Any]) -> None:
        """Test that namespace cannot be modified."""
        ref = ModelSubjectRef(**full_ref_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ref.namespace = "different-namespace"  # type: ignore[misc]

    def test_cannot_modify_subject_key(self, full_ref_data: dict[str, Any]) -> None:
        """Test that subject_key cannot be modified."""
        ref = ModelSubjectRef(**full_ref_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ref.subject_key = "different-key"  # type: ignore[misc]


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelSubjectRefValidation:
    """Tests for field validation constraints."""

    def test_missing_required_field_subject_type(self) -> None:
        """Test that missing subject_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE: Intentionally testing Pydantic validation - mypy correctly flags missing required arg
            ModelSubjectRef(subject_id="test-id")  # type: ignore[call-arg]

        assert "subject_type" in str(exc_info.value)

    def test_missing_required_field_subject_id(self) -> None:
        """Test that missing subject_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE: Intentionally testing Pydantic validation - mypy correctly flags missing required arg
            ModelSubjectRef(subject_type=EnumSubjectType.AGENT)  # type: ignore[call-arg]

        assert "subject_id" in str(exc_info.value)

    def test_invalid_subject_type_rejected(self) -> None:
        """Test that invalid subject_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE: Intentionally testing Pydantic validation - mypy correctly flags wrong type
            ModelSubjectRef(
                subject_type="invalid_type",  # type: ignore[arg-type]
                subject_id="test-id",
            )

        assert "subject_type" in str(exc_info.value)

    def test_uuid_id_preserved(self) -> None:
        """Test that UUID subject_id type is preserved."""
        test_uuid = uuid4()
        ref = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
        )

        assert ref.subject_id == test_uuid
        assert isinstance(ref.subject_id, UUID)

    def test_string_id_preserved(self) -> None:
        """Test that string subject_id type is preserved."""
        ref = ModelSubjectRef(
            subject_type=EnumSubjectType.USER,
            subject_id="my-string-id-123",
        )

        assert ref.subject_id == "my-string-id-123"
        assert isinstance(ref.subject_id, str)


# ============================================================================
# Test: extra="forbid" Behavior
# ============================================================================


class TestModelSubjectRefExtraForbid:
    """Tests for extra='forbid' behavior."""

    def test_extra_fields_rejected(self, minimal_ref_data_uuid: dict[str, Any]) -> None:
        """Test that extra fields are rejected."""
        minimal_ref_data_uuid["unexpected_field"] = "should_fail"

        with pytest.raises(ValidationError) as exc_info:
            ModelSubjectRef(**minimal_ref_data_uuid)

        assert "unexpected_field" in str(exc_info.value) or "extra" in str(
            exc_info.value
        )

    def test_multiple_extra_fields_rejected(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test that multiple extra fields are rejected."""
        minimal_ref_data_uuid["extra1"] = "value1"
        minimal_ref_data_uuid["extra2"] = "value2"

        with pytest.raises(ValidationError):
            ModelSubjectRef(**minimal_ref_data_uuid)


# ============================================================================
# Test: from_attributes=True Behavior
# ============================================================================


class TestModelSubjectRefFromAttributes:
    """Tests for from_attributes=True behavior."""

    def test_create_from_object_with_attributes(self) -> None:
        """Test creating model from object with matching attributes."""

        class SubjectRefLike:
            """Object with subject ref attributes."""

            def __init__(self) -> None:
                self.subject_type = EnumSubjectType.AGENT
                self.subject_id = uuid4()
                self.namespace = "test-ns"
                self.subject_key = "test-key"

        source = SubjectRefLike()
        ref = ModelSubjectRef.model_validate(source)

        assert ref.subject_type == source.subject_type
        assert ref.subject_id == source.subject_id
        assert ref.namespace == source.namespace
        assert ref.subject_key == source.subject_key

    def test_create_from_object_minimal_attributes(self) -> None:
        """Test creating model from object with only required attributes."""

        class MinimalSubjectRef:
            """Object with minimal required attributes."""

            def __init__(self) -> None:
                self.subject_type = EnumSubjectType.USER
                self.subject_id = "user-abc"

        source = MinimalSubjectRef()
        ref = ModelSubjectRef.model_validate(source)

        assert ref.subject_type == source.subject_type
        assert ref.subject_id == source.subject_id
        assert ref.namespace is None
        assert ref.subject_key is None


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelSubjectRefSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_ref_data_uuid: dict[str, Any]) -> None:
        """Test serialization to dictionary."""
        ref = ModelSubjectRef(**minimal_ref_data_uuid)
        data = ref.model_dump()

        assert "subject_type" in data
        assert "subject_id" in data
        assert "namespace" in data
        assert "subject_key" in data
        assert data["subject_type"] == EnumSubjectType.AGENT

    def test_model_dump_json(self, full_ref_data: dict[str, Any]) -> None:
        """Test serialization to JSON string."""
        ref = ModelSubjectRef(**full_ref_data)
        json_str = ref.model_dump_json()

        assert isinstance(json_str, str)
        assert "workflow" in json_str
        assert "production" in json_str
        assert "data-processor-v2" in json_str

    def test_round_trip_serialization_uuid(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test that model survives serialization round-trip with UUID."""
        original = ModelSubjectRef(**minimal_ref_data_uuid)
        data = original.model_dump()
        restored = ModelSubjectRef(**data)

        assert original.subject_type == restored.subject_type
        assert original.subject_id == restored.subject_id
        assert original.namespace == restored.namespace
        assert original.subject_key == restored.subject_key

    def test_round_trip_serialization_string(
        self, minimal_ref_data_string: dict[str, Any]
    ) -> None:
        """Test that model survives serialization round-trip with string ID."""
        original = ModelSubjectRef(**minimal_ref_data_string)
        data = original.model_dump()
        restored = ModelSubjectRef(**data)

        assert original.subject_type == restored.subject_type
        assert original.subject_id == restored.subject_id

    def test_json_round_trip_serialization(self, full_ref_data: dict[str, Any]) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelSubjectRef(**full_ref_data)

        json_str = original.model_dump_json()
        restored = ModelSubjectRef.model_validate_json(json_str)

        assert original.subject_type == restored.subject_type
        assert original.subject_id == restored.subject_id
        assert original.namespace == restored.namespace
        assert original.subject_key == restored.subject_key

    def test_model_dump_contains_all_fields(
        self, full_ref_data: dict[str, Any]
    ) -> None:
        """Test model_dump contains all expected fields."""
        ref = ModelSubjectRef(**full_ref_data)
        data = ref.model_dump()

        expected_fields = [
            "subject_type",
            "subject_id",
            "namespace",
            "subject_key",
        ]
        for field in expected_fields:
            assert field in data

    def test_model_validate_from_dict(self, full_ref_data: dict[str, Any]) -> None:
        """Test model validation from dictionary."""
        ref = ModelSubjectRef.model_validate(full_ref_data)

        assert ref.subject_type == full_ref_data["subject_type"]
        assert ref.subject_id == full_ref_data["subject_id"]
        assert ref.namespace == full_ref_data["namespace"]
        assert ref.subject_key == full_ref_data["subject_key"]


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelSubjectRefEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_string_id_rejected(self) -> None:
        """Test that empty string ID is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSubjectRef(
                subject_type=EnumSubjectType.AGENT,
                subject_id="",
            )
        assert "subject_id" in str(exc_info.value)

    def test_empty_namespace_string_rejected(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test that empty string namespace is rejected."""
        minimal_ref_data_uuid["namespace"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ModelSubjectRef(**minimal_ref_data_uuid)
        assert "namespace" in str(exc_info.value)

    def test_whitespace_namespace_string_rejected(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test that whitespace-only namespace is rejected."""
        minimal_ref_data_uuid["namespace"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            ModelSubjectRef(**minimal_ref_data_uuid)
        assert "namespace" in str(exc_info.value)

    def test_empty_subject_key_string_rejected(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test that empty string subject_key is rejected."""
        minimal_ref_data_uuid["subject_key"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ModelSubjectRef(**minimal_ref_data_uuid)
        assert "subject_key" in str(exc_info.value)

    def test_whitespace_subject_key_string_rejected(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test that whitespace-only subject_key is rejected."""
        minimal_ref_data_uuid["subject_key"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            ModelSubjectRef(**minimal_ref_data_uuid)
        assert "subject_key" in str(exc_info.value)

    def test_whitespace_subject_id_string_rejected(self) -> None:
        """Test that whitespace-only subject_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSubjectRef(
                subject_type=EnumSubjectType.AGENT,
                subject_id="   ",
            )
        assert "subject_id" in str(exc_info.value)

    def test_long_string_id(self) -> None:
        """Test handling of long string ID."""
        long_id = "x" * 1000
        ref = ModelSubjectRef(
            subject_type=EnumSubjectType.USER,
            subject_id=long_id,
        )
        assert ref.subject_id == long_id

    def test_special_characters_in_string_id(self) -> None:
        """Test string ID with special characters."""
        special_ids = [
            "user-123",
            "user_456",
            "user.789",
            "user:abc",
            "user/def",
            "user@example.com",
        ]
        for sid in special_ids:
            ref = ModelSubjectRef(
                subject_type=EnumSubjectType.USER,
                subject_id=sid,
            )
            assert ref.subject_id == sid

    def test_special_characters_in_namespace(
        self, minimal_ref_data_uuid: dict[str, Any]
    ) -> None:
        """Test namespace with special characters."""
        special_namespaces = [
            "prod-us-east",
            "staging_v2",
            "env.test",
            "org:team",
        ]
        for ns in special_namespaces:
            minimal_ref_data_uuid["namespace"] = ns
            ref = ModelSubjectRef(**minimal_ref_data_uuid)
            assert ref.namespace == ns

    def test_model_equality_same_data(self) -> None:
        """Test model equality comparison with same data."""
        test_uuid = uuid4()
        ref1 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
            namespace="prod",
            subject_key="key1",
        )
        ref2 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
            namespace="prod",
            subject_key="key1",
        )

        assert ref1 == ref2

    def test_model_inequality_different_subject_type(self) -> None:
        """Test model inequality when subject_type differs."""
        test_uuid = uuid4()
        ref1 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
        )
        ref2 = ModelSubjectRef(
            subject_type=EnumSubjectType.USER,
            subject_id=test_uuid,
        )

        assert ref1 != ref2

    def test_model_inequality_different_subject_id(self) -> None:
        """Test model inequality when subject_id differs."""
        ref1 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=uuid4(),
        )
        ref2 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=uuid4(),
        )

        assert ref1 != ref2

    def test_model_inequality_different_namespace(self) -> None:
        """Test model inequality when namespace differs."""
        test_uuid = uuid4()
        ref1 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
            namespace="prod",
        )
        ref2 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
            namespace="staging",
        )

        assert ref1 != ref2

    def test_str_representation(self, minimal_ref_data_uuid: dict[str, Any]) -> None:
        """Test __str__ method returns formatted string."""
        ref = ModelSubjectRef(**minimal_ref_data_uuid)
        str_repr = str(ref)

        assert isinstance(str_repr, str)
        assert "agent" in str_repr

    def test_str_representation_with_namespace(
        self, full_ref_data: dict[str, Any]
    ) -> None:
        """Test __str__ includes namespace when present."""
        ref = ModelSubjectRef(**full_ref_data)
        str_repr = str(ref)

        assert isinstance(str_repr, str)
        assert "production" in str_repr
        assert "workflow" in str_repr

    def test_repr_representation(self, minimal_ref_data_uuid: dict[str, Any]) -> None:
        """Test __repr__ method returns string with class name."""
        ref = ModelSubjectRef(**minimal_ref_data_uuid)
        repr_str = repr(ref)

        assert isinstance(repr_str, str)
        assert "ModelSubjectRef" in repr_str

    def test_hash_consistency_for_same_data(self) -> None:
        """Test that frozen model is hashable and consistent."""
        test_uuid = uuid4()
        ref1 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
            namespace="prod",
        )
        ref2 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
            namespace="prod",
        )

        # Frozen models should be hashable
        assert hash(ref1) == hash(ref2)

    def test_can_use_as_dict_key(self, minimal_ref_data_uuid: dict[str, Any]) -> None:
        """Test that frozen model can be used as dictionary key."""
        ref = ModelSubjectRef(**minimal_ref_data_uuid)

        # Should be usable as dict key
        test_dict = {ref: "value"}
        assert test_dict[ref] == "value"

    def test_can_add_to_set(self) -> None:
        """Test that frozen model can be added to set."""
        test_uuid = uuid4()
        ref1 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
        )
        ref2 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=test_uuid,
        )

        # Should be usable in sets
        test_set = {ref1, ref2}
        assert len(test_set) == 1  # Same data, same hash


# ============================================================================
# Test: Integration with EnumSubjectType
# ============================================================================


class TestModelSubjectRefEnumIntegration:
    """Tests for integration with EnumSubjectType methods."""

    def test_entity_type_subject(self) -> None:
        """Test that entity-type subjects work correctly."""
        for subject_type in [
            EnumSubjectType.AGENT,
            EnumSubjectType.USER,
            EnumSubjectType.SERVICE,
        ]:
            ref = ModelSubjectRef(
                subject_type=subject_type,
                subject_id="test-id",
            )
            assert ref.subject_type.is_entity_type()

    def test_scope_type_subject(self) -> None:
        """Test that scope-type subjects work correctly."""
        for subject_type in [
            EnumSubjectType.WORKFLOW,
            EnumSubjectType.PROJECT,
            EnumSubjectType.ORG,
            EnumSubjectType.TASK,
            EnumSubjectType.CORPUS,
            EnumSubjectType.SESSION,
        ]:
            ref = ModelSubjectRef(
                subject_type=subject_type,
                subject_id="test-id",
            )
            assert ref.subject_type.is_scope_type()

    def test_persistent_subject(self) -> None:
        """Test that persistent/non-persistent subjects work correctly."""
        # Non-persistent
        session_ref = ModelSubjectRef(
            subject_type=EnumSubjectType.SESSION,
            subject_id="session-123",
        )
        assert not session_ref.subject_type.is_persistent()

        # Persistent
        agent_ref = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id="agent-123",
        )
        assert agent_ref.subject_type.is_persistent()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
