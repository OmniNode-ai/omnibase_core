"""
Test suite for ModelGenericCollectionSummary.

Tests the strongly-typed summary for generic collections.
"""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_generic_collection_summary import (
    ModelGenericCollectionSummary,
)


class TestModelGenericCollectionSummary:
    """Test cases for ModelGenericCollectionSummary."""

    def test_initialization_with_required_fields(self):
        """Test initialization with all required fields."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=100,
            enabled_items=80,
            valid_items=90,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        assert summary.total_items == 100
        assert summary.enabled_items == 80
        assert summary.valid_items == 90
        assert summary.created_at == now
        assert summary.updated_at == now
        assert summary.has_items is True

    def test_initialization_with_optional_fields(self):
        """Test initialization with optional fields."""
        now = datetime.now()
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")

        summary = ModelGenericCollectionSummary(
            collection_id=test_uuid,
            collection_display_name="Test Collection",
            total_items=50,
            enabled_items=40,
            valid_items=45,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        assert summary.collection_id == test_uuid
        assert summary.collection_display_name == "Test Collection"
        assert summary.total_items == 50
        assert summary.enabled_items == 40
        assert summary.valid_items == 45

    def test_default_collection_id_generated(self):
        """Test that default collection_id is generated."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        assert isinstance(summary.collection_id, UUID)

    def test_default_collection_display_name(self):
        """Test default collection display name."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        assert summary.collection_display_name == ""

    def test_empty_collection_summary(self):
        """Test summary for an empty collection."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=0,
            enabled_items=0,
            valid_items=0,
            created_at=now,
            updated_at=now,
            has_items=False,
        )

        assert summary.total_items == 0
        assert summary.enabled_items == 0
        assert summary.valid_items == 0
        assert summary.has_items is False

    def test_configure_protocol_method(self):
        """Test configure method (Configurable protocol)."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        result = summary.configure(
            collection_display_name="Updated Name",
            total_items=20,
        )

        assert result is True
        assert summary.collection_display_name == "Updated Name"
        assert summary.total_items == 20

    def test_configure_with_invalid_fields(self):
        """Test configure with non-existent fields."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        result = summary.configure(
            collection_display_name="Valid",
            nonexistent_field="Invalid",
        )

        assert result is True
        assert summary.collection_display_name == "Valid"

    def test_configure_with_exception(self):
        """Test configure handles exceptions gracefully."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        # Try to set invalid type
        result = summary.configure(total_items="not_an_int")

        assert result is False

    def test_serialize_protocol_method(self):
        """Test serialize method (Serializable protocol)."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            collection_display_name="Test",
            total_items=100,
            enabled_items=80,
            valid_items=90,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        serialized = summary.serialize()

        assert isinstance(serialized, dict)
        assert serialized["collection_display_name"] == "Test"
        assert serialized["total_items"] == 100
        assert serialized["enabled_items"] == 80
        assert serialized["valid_items"] == 90
        assert serialized["has_items"] is True

    def test_serialize_includes_all_fields(self):
        """Test serialize includes all fields."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        serialized = summary.serialize()

        required_fields = [
            "collection_id",
            "collection_display_name",
            "total_items",
            "enabled_items",
            "valid_items",
            "created_at",
            "updated_at",
            "has_items",
        ]
        for field in required_fields:
            assert field in serialized, f"Field {field} missing from serialized output"

    def test_validate_instance_protocol_method(self):
        """Test validate_instance method (Validatable protocol)."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        result = summary.validate_instance()

        assert result is True

    def test_get_name_protocol_method(self):
        """Test get_name method (Nameable protocol)."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        name = summary.get_name()

        assert isinstance(name, str)
        assert "ModelGenericCollectionSummary" in name

    def test_get_name_with_display_name(self):
        """Test get_name when display name is set."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            collection_display_name="My Collection",
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        name = summary.get_name()

        # Verify name is a non-empty string
        assert isinstance(name, str)
        assert len(name) > 0

    def test_set_name_protocol_method(self):
        """Test set_name method (Nameable protocol)."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        # Set name and verify it was applied
        summary.set_name("New Collection Name")
        # Verify set_name completed without raising exception
        assert isinstance(summary, ModelGenericCollectionSummary)

    def test_model_config_extra_ignore(self):
        """Test that extra fields are ignored per model_config."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
            extra_field="should be ignored",
        )

        assert summary.total_items == 10
        # Verify extra field was not added to the model
        with pytest.raises(AttributeError):
            _ = summary.extra_field

    def test_model_config_validate_assignment(self):
        """Test that assignment validation works per model_config."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        # Should be able to update with valid type
        summary.total_items = 20
        assert summary.total_items == 20

        # Should raise validation error with invalid type
        with pytest.raises(ValidationError) as exc_info:
            summary.total_items = "not_an_int"
        assert "total_items" in str(exc_info.value)

    def test_statistics_consistency(self):
        """Test that statistics are consistent."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=100,
            enabled_items=80,
            valid_items=90,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        # Enabled items should be <= total items
        assert summary.enabled_items <= summary.total_items
        # Valid items should be <= total items
        assert summary.valid_items <= summary.total_items

    def test_has_items_flag_consistency(self):
        """Test has_items flag consistency with total_items."""
        now = datetime.now()

        # Collection with items
        summary1 = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        assert summary1.has_items is True
        assert summary1.total_items > 0

        # Empty collection
        summary2 = ModelGenericCollectionSummary(
            total_items=0,
            enabled_items=0,
            valid_items=0,
            created_at=now,
            updated_at=now,
            has_items=False,
        )

        assert summary2.has_items is False
        assert summary2.total_items == 0

    def test_timestamp_handling(self):
        """Test timestamp fields handle datetime correctly."""
        created = datetime(2024, 1, 1, 12, 0, 0)
        updated = datetime(2024, 1, 2, 12, 0, 0)

        summary = ModelGenericCollectionSummary(
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=created,
            updated_at=updated,
            has_items=True,
        )

        assert isinstance(summary.created_at, datetime)
        assert isinstance(summary.updated_at, datetime)
        assert summary.created_at == created
        assert summary.updated_at == updated
        # Updated should be after or equal to created
        assert summary.updated_at >= summary.created_at

    def test_multiple_summaries_independence(self):
        """Test that multiple instances are independent."""
        now = datetime.now()

        summary1 = ModelGenericCollectionSummary(
            collection_display_name="Collection 1",
            total_items=10,
            enabled_items=5,
            valid_items=8,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        summary2 = ModelGenericCollectionSummary(
            collection_display_name="Collection 2",
            total_items=20,
            enabled_items=15,
            valid_items=18,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        assert summary1.collection_display_name == "Collection 1"
        assert summary2.collection_display_name == "Collection 2"
        assert summary1.total_items == 10
        assert summary2.total_items == 20
        assert summary1.collection_id != summary2.collection_id

    def test_complex_real_world_scenario(self):
        """Test complex real-world collection summary scenario."""
        created = datetime(2024, 1, 1, 0, 0, 0)
        updated = datetime(2024, 1, 15, 12, 30, 0)

        # Large production collection summary
        summary = ModelGenericCollectionSummary(
            collection_display_name="Production User Database",
            total_items=50000,
            enabled_items=48500,
            valid_items=49800,
            created_at=created,
            updated_at=updated,
            has_items=True,
        )

        # Verify all properties
        assert summary.collection_display_name == "Production User Database"
        assert summary.total_items == 50000
        assert summary.enabled_items == 48500
        assert summary.valid_items == 49800
        assert summary.has_items is True

        # Calculate percentages
        enabled_percentage = (summary.enabled_items / summary.total_items) * 100
        valid_percentage = (summary.valid_items / summary.total_items) * 100

        assert enabled_percentage == 97.0
        assert valid_percentage == 99.6

        # Test protocols work
        assert summary.validate_instance() is True
        serialized = summary.serialize()
        assert isinstance(serialized, dict)

    def test_edge_case_all_disabled(self):
        """Test edge case where all items are disabled."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=100,
            enabled_items=0,
            valid_items=100,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        assert summary.total_items == 100
        assert summary.enabled_items == 0
        assert summary.valid_items == 100
        assert summary.has_items is True

    def test_edge_case_all_invalid(self):
        """Test edge case where all items are invalid."""
        now = datetime.now()

        summary = ModelGenericCollectionSummary(
            total_items=100,
            enabled_items=100,
            valid_items=0,
            created_at=now,
            updated_at=now,
            has_items=True,
        )

        assert summary.total_items == 100
        assert summary.enabled_items == 100
        assert summary.valid_items == 0
        assert summary.has_items is True
