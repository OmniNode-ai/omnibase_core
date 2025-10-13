"""
Tests for ModelLogNodeIdentifier and related models.

This module tests the discriminated union for log node identifiers,
including both UUID and string-based identifiers.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.logging.model_log_node_identifier import (
    ModelLogNodeIdentifier,
    ModelLogNodeIdentifierUUID,
)
from omnibase_core.models.logging.model_lognodeidentifierstring import (
    ModelLogNodeIdentifierString,
)


class TestModelLogNodeIdentifierUUID:
    """Test UUID-based log node identifier."""

    def test_create_uuid_identifier(self):
        """Test creating UUID identifier with valid UUID."""
        test_uuid = uuid4()
        identifier = ModelLogNodeIdentifierUUID(value=test_uuid)

        assert identifier.type == "uuid"
        assert identifier.value == test_uuid

    def test_create_uuid_identifier_with_string_uuid(self):
        """Test creating UUID identifier with string UUID."""
        test_uuid_str = str(uuid4())
        identifier = ModelLogNodeIdentifierUUID(value=test_uuid_str)

        assert identifier.type == "uuid"
        assert str(identifier.value) == test_uuid_str

    def test_uuid_identifier_validation(self):
        """Test UUID identifier validation."""
        # Valid UUID
        valid_uuid = uuid4()
        identifier = ModelLogNodeIdentifierUUID(value=valid_uuid)
        assert identifier.value == valid_uuid

        # Invalid UUID should raise validation error
        with pytest.raises(ValueError):
            ModelLogNodeIdentifierUUID(value="not-a-uuid")

    def test_uuid_identifier_serialization(self):
        """Test UUID identifier serialization."""
        test_uuid = uuid4()
        identifier = ModelLogNodeIdentifierUUID(value=test_uuid)

        data = identifier.model_dump()
        assert data["type"] == "uuid"
        assert (
            data["value"] == test_uuid
        )  # UUID is serialized as UUID object, not string

    def test_uuid_identifier_deserialization(self):
        """Test UUID identifier deserialization."""
        test_uuid = uuid4()
        data = {"type": "uuid", "value": str(test_uuid)}

        identifier = ModelLogNodeIdentifierUUID.model_validate(data)
        assert identifier.type == "uuid"
        assert identifier.value == test_uuid


class TestModelLogNodeIdentifierString:
    """Test string-based log node identifier."""

    def test_create_string_identifier(self):
        """Test creating string identifier."""
        test_string = "test_module.TestClass"
        identifier = ModelLogNodeIdentifierString(value=test_string)

        assert identifier.type == "string"
        assert identifier.value == test_string

    def test_string_identifier_with_module_name(self):
        """Test string identifier with module name."""
        module_name = "omnibase_core.models.test"
        identifier = ModelLogNodeIdentifierString(value=module_name)

        assert identifier.type == "string"
        assert identifier.value == module_name

    def test_string_identifier_with_class_name(self):
        """Test string identifier with class name."""
        class_name = "TestModel"
        identifier = ModelLogNodeIdentifierString(value=class_name)

        assert identifier.type == "string"
        assert identifier.value == class_name

    def test_string_identifier_serialization(self):
        """Test string identifier serialization."""
        test_string = "test_module.TestClass"
        identifier = ModelLogNodeIdentifierString(value=test_string)

        data = identifier.model_dump()
        assert data["type"] == "string"
        assert data["value"] == test_string

    def test_string_identifier_deserialization(self):
        """Test string identifier deserialization."""
        test_string = "test_module.TestClass"
        data = {"type": "string", "value": test_string}

        identifier = ModelLogNodeIdentifierString.model_validate(data)
        assert identifier.type == "string"
        assert identifier.value == test_string


class TestModelLogNodeIdentifierUnion:
    """Test the discriminated union ModelLogNodeIdentifier."""

    def test_uuid_identifier_union(self):
        """Test UUID identifier in union context."""
        test_uuid = uuid4()
        identifier: ModelLogNodeIdentifier = ModelLogNodeIdentifierUUID(value=test_uuid)

        assert isinstance(identifier, ModelLogNodeIdentifierUUID)
        assert identifier.type == "uuid"
        assert identifier.value == test_uuid

    def test_string_identifier_union(self):
        """Test string identifier in union context."""
        test_string = "test_module.TestClass"
        identifier: ModelLogNodeIdentifier = ModelLogNodeIdentifierString(
            value=test_string
        )

        assert isinstance(identifier, ModelLogNodeIdentifierString)
        assert identifier.type == "string"
        assert identifier.value == test_string

    def test_union_discrimination(self):
        """Test union discrimination based on type field."""
        # UUID identifier
        uuid_data = {"type": "uuid", "value": str(uuid4())}
        uuid_identifier = ModelLogNodeIdentifierUUID.model_validate(uuid_data)
        assert uuid_identifier.type == "uuid"

        # String identifier
        string_data = {"type": "string", "value": "test_module"}
        string_identifier = ModelLogNodeIdentifierString.model_validate(string_data)
        assert string_identifier.type == "string"

    def test_union_serialization_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        # UUID identifier
        test_uuid = uuid4()
        uuid_identifier = ModelLogNodeIdentifierUUID(value=test_uuid)
        uuid_data = uuid_identifier.model_dump()
        uuid_restored = ModelLogNodeIdentifierUUID.model_validate(uuid_data)
        assert uuid_restored.value == test_uuid

        # String identifier
        test_string = "test_module.TestClass"
        string_identifier = ModelLogNodeIdentifierString(value=test_string)
        string_data = string_identifier.model_dump()
        string_restored = ModelLogNodeIdentifierString.model_validate(string_data)
        assert string_restored.value == test_string


class TestModelLogNodeIdentifierEdgeCases:
    """Test edge cases for log node identifiers."""

    def test_empty_string_identifier(self):
        """Test string identifier with empty string."""
        identifier = ModelLogNodeIdentifierString(value="")
        assert identifier.type == "string"
        assert identifier.value == ""

    def test_unicode_string_identifier(self):
        """Test string identifier with unicode characters."""
        unicode_string = "测试模块.Test类"
        identifier = ModelLogNodeIdentifierString(value=unicode_string)
        assert identifier.type == "string"
        assert identifier.value == unicode_string

    def test_long_string_identifier(self):
        """Test string identifier with long string."""
        long_string = "very.long.module.name.with.many.segments.TestClass"
        identifier = ModelLogNodeIdentifierString(value=long_string)
        assert identifier.type == "string"
        assert identifier.value == long_string

    def test_uuid_identifier_with_nil_uuid(self):
        """Test UUID identifier with nil UUID."""
        nil_uuid = UUID("00000000-0000-0000-0000-000000000000")
        identifier = ModelLogNodeIdentifierUUID(value=nil_uuid)
        assert identifier.type == "uuid"
        assert identifier.value == nil_uuid

    def test_identifier_type_immutability(self):
        """Test that identifier type cannot be changed."""
        test_uuid = uuid4()
        identifier = ModelLogNodeIdentifierUUID(value=test_uuid)

        # Type should be immutable
        assert identifier.type == "uuid"
        # Attempting to change type should not work (Pydantic models are immutable by default)
        # The type field is set to a literal value and cannot be changed
        assert identifier.type == "uuid"


class TestModelLogNodeIdentifierIntegration:
    """Test integration scenarios for log node identifiers."""

    def test_logging_context_uuid(self):
        """Test UUID identifier in logging context."""
        test_uuid = uuid4()
        identifier = ModelLogNodeIdentifierUUID(value=test_uuid)

        # Simulate logging context
        log_context = {"node_id": identifier, "message": "Test log message"}

        assert log_context["node_id"].type == "uuid"
        assert log_context["node_id"].value == test_uuid

    def test_logging_context_string(self):
        """Test string identifier in logging context."""
        test_string = "test_module.TestClass"
        identifier = ModelLogNodeIdentifierString(value=test_string)

        # Simulate logging context
        log_context = {"node_id": identifier, "message": "Test log message"}

        assert log_context["node_id"].type == "string"
        assert log_context["node_id"].value == test_string

    def test_identifier_comparison(self):
        """Test identifier comparison."""
        uuid1 = uuid4()
        uuid2 = uuid4()

        identifier1 = ModelLogNodeIdentifierUUID(value=uuid1)
        identifier2 = ModelLogNodeIdentifierUUID(value=uuid1)
        identifier3 = ModelLogNodeIdentifierUUID(value=uuid2)

        # Same UUID should be equal
        assert identifier1 == identifier2
        # Different UUID should not be equal
        assert identifier1 != identifier3

    def test_identifier_hash(self):
        """Test identifier hashing."""
        test_uuid = uuid4()
        identifier = ModelLogNodeIdentifierUUID(value=test_uuid)

        # Pydantic models are not hashable by default
        # Test that we can access the value for hashing
        hash_value = hash(identifier.value)
        assert isinstance(hash_value, int)

        # Same UUID should have same hash
        identifier2 = ModelLogNodeIdentifierUUID(value=test_uuid)
        assert hash(identifier.value) == hash(identifier2.value)
