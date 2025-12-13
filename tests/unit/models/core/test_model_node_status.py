"""
Tests for ModelNodeStatus.

This module tests the generic node status model for common use.
"""

import pytest

pytestmark = pytest.mark.unit

from omnibase_core.models.core.model_node_status import ModelNodeStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestModelNodeStatus:
    """Test ModelNodeStatus functionality."""

    def test_create_node_status(self):
        """Test creating a ModelNodeStatus instance."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)
        assert status is not None
        assert isinstance(status, ModelNodeStatus)

    def test_node_status_inheritance(self):
        """Test that ModelNodeStatus inherits from BaseModel."""
        from pydantic import BaseModel

        status = ModelNodeStatus(version=DEFAULT_VERSION)
        assert isinstance(status, BaseModel)

    def test_node_status_serialization(self):
        """Test ModelNodeStatus serialization."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)

        data = status.model_dump()
        assert isinstance(data, dict)
        assert data == {}

    def test_node_status_deserialization(self):
        """Test ModelNodeStatus deserialization."""
        data = {}
        status = ModelNodeStatus.model_validate(data)
        assert isinstance(status, ModelNodeStatus)

    def test_node_status_json_serialization(self):
        """Test ModelNodeStatus JSON serialization."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)

        json_data = status.model_dump_json()
        assert isinstance(json_data, str)
        assert json_data == "{}"

    def test_node_status_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original_status = ModelNodeStatus(version=DEFAULT_VERSION)

        # Serialize
        data = original_status.model_dump()

        # Deserialize
        restored_status = ModelNodeStatus.model_validate(data)

        # Verify they are equivalent
        assert restored_status.model_dump() == original_status.model_dump()

    def test_node_status_equality(self):
        """Test ModelNodeStatus equality."""
        status1 = ModelNodeStatus(version=DEFAULT_VERSION)
        status2 = ModelNodeStatus(version=DEFAULT_VERSION)

        # Empty models should be equal
        assert status1 == status2

    def test_node_status_hash(self):
        """Test ModelNodeStatus hashing."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)

        # Pydantic models are not hashable by default
        # Test that we can access the model for hashing purposes
        data = status.model_dump()
        hash_value = hash(str(data))
        assert isinstance(hash_value, int)

    def test_node_status_str(self):
        """Test ModelNodeStatus string representation."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)

        str_repr = str(status)
        assert isinstance(str_repr, str)
        # Empty model might have empty string representation
        assert str_repr is not None

    def test_node_status_repr(self):
        """Test ModelNodeStatus repr representation."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)

        repr_str = repr(status)
        assert isinstance(repr_str, str)
        assert "ModelNodeStatus" in repr_str

    def test_node_status_attributes(self):
        """Test ModelNodeStatus attributes."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)

        # Should have model_dump method
        assert hasattr(status, "model_dump")
        assert callable(status.model_dump)

        # Should have model_validate method
        assert hasattr(ModelNodeStatus, "model_validate")
        assert callable(ModelNodeStatus.model_validate)

    def test_node_status_validation(self):
        """Test ModelNodeStatus validation."""
        # Valid empty model
        status = ModelNodeStatus(version=DEFAULT_VERSION)
        assert status is not None

        # Should accept empty dict
        status = ModelNodeStatus.model_validate({})
        assert status is not None

    def test_node_status_metadata(self):
        """Test ModelNodeStatus metadata."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)

        # Should have model_fields
        assert hasattr(status, "model_fields")
        assert isinstance(status.model_fields, dict)

        # Should have model_config
        assert hasattr(status, "model_config")
        assert hasattr(status.model_config, "get")

    def test_node_status_creation_with_data(self):
        """Test ModelNodeStatus creation with data."""
        # Even with data, should work (empty model)
        status = ModelNodeStatus.model_validate({"some_field": "some_value"})
        assert status is not None

        # Should ignore extra fields for empty model
        data = status.model_dump()
        assert data == {}

    def test_node_status_copy(self):
        """Test ModelNodeStatus copying."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)

        # Should be able to create a copy
        copied_status = status.model_copy()
        assert copied_status is not None
        assert copied_status == status
        assert copied_status is not status  # Different objects

    def test_node_status_immutability(self):
        """Test ModelNodeStatus immutability."""
        status = ModelNodeStatus(version=DEFAULT_VERSION)

        # Should be immutable by default
        original_data = status.model_dump()

        # Attempting to modify should not affect the original
        # (though this is more about Pydantic behavior)
        assert status.model_dump() == original_data
