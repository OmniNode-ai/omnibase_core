"""Tests for ModelAnalyticsCore."""

from uuid import UUID, uuid4

import pytest

from omnibase_core.models.metadata.analytics.model_analytics_core import (
    ModelAnalyticsCore,
)


@pytest.mark.unit
class TestModelAnalyticsCoreInstantiation:
    """Tests for ModelAnalyticsCore instantiation."""

    def test_create_with_defaults(self):
        """Test creating analytics core with default values."""
        analytics = ModelAnalyticsCore()
        assert isinstance(analytics.collection_id, UUID)
        assert analytics.collection_display_name is None
        assert analytics.total_nodes == 0
        assert analytics.active_nodes == 0
        assert analytics.deprecated_nodes == 0
        assert analytics.disabled_nodes == 0

    def test_create_with_collection_info(self):
        """Test creating analytics core with collection info."""
        collection_id = uuid4()
        analytics = ModelAnalyticsCore(
            collection_id=collection_id,
            collection_display_name="Test Collection",
        )
        assert analytics.collection_id == collection_id
        assert analytics.collection_display_name == "Test Collection"

    def test_create_with_node_counts(self):
        """Test creating analytics core with node counts."""
        analytics = ModelAnalyticsCore(
            total_nodes=100,
            active_nodes=75,
            deprecated_nodes=15,
            disabled_nodes=10,
        )
        assert analytics.total_nodes == 100
        assert analytics.active_nodes == 75
        assert analytics.deprecated_nodes == 15
        assert analytics.disabled_nodes == 10

    def test_create_with_all_fields(self):
        """Test creating analytics core with all fields."""
        collection_id = uuid4()
        analytics = ModelAnalyticsCore(
            collection_id=collection_id,
            collection_display_name="Complete Collection",
            total_nodes=50,
            active_nodes=40,
            deprecated_nodes=5,
            disabled_nodes=5,
        )
        assert analytics.collection_id == collection_id
        assert analytics.collection_display_name == "Complete Collection"
        assert analytics.total_nodes == 50
        assert analytics.active_nodes == 40


@pytest.mark.unit
class TestModelAnalyticsCoreProperties:
    """Tests for ModelAnalyticsCore properties."""

    def test_collection_name_property(self):
        """Test collection_name property."""
        analytics = ModelAnalyticsCore(collection_display_name="Test Name")
        assert analytics.collection_name == "Test Name"

    def test_collection_name_property_none(self):
        """Test collection_name property when None."""
        analytics = ModelAnalyticsCore()
        assert analytics.collection_name is None

    def test_active_node_ratio_normal(self):
        """Test active_node_ratio with normal values."""
        analytics = ModelAnalyticsCore(total_nodes=100, active_nodes=75)
        assert analytics.active_node_ratio == 0.75

    def test_active_node_ratio_zero_total(self):
        """Test active_node_ratio when total_nodes is zero."""
        analytics = ModelAnalyticsCore(total_nodes=0, active_nodes=0)
        assert analytics.active_node_ratio == 0.0

    def test_active_node_ratio_all_active(self):
        """Test active_node_ratio when all nodes are active."""
        analytics = ModelAnalyticsCore(total_nodes=50, active_nodes=50)
        assert analytics.active_node_ratio == 1.0

    def test_deprecated_node_ratio_normal(self):
        """Test deprecated_node_ratio with normal values."""
        analytics = ModelAnalyticsCore(total_nodes=100, deprecated_nodes=20)
        assert analytics.deprecated_node_ratio == 0.2

    def test_deprecated_node_ratio_zero_total(self):
        """Test deprecated_node_ratio when total_nodes is zero."""
        analytics = ModelAnalyticsCore(total_nodes=0, deprecated_nodes=0)
        assert analytics.deprecated_node_ratio == 0.0

    def test_disabled_node_ratio_normal(self):
        """Test disabled_node_ratio with normal values."""
        analytics = ModelAnalyticsCore(total_nodes=100, disabled_nodes=10)
        assert analytics.disabled_node_ratio == 0.1

    def test_disabled_node_ratio_zero_total(self):
        """Test disabled_node_ratio when total_nodes is zero."""
        analytics = ModelAnalyticsCore(total_nodes=0, disabled_nodes=0)
        assert analytics.disabled_node_ratio == 0.0


@pytest.mark.unit
class TestModelAnalyticsCorePredicates:
    """Tests for ModelAnalyticsCore predicate methods."""

    def test_has_nodes_true(self):
        """Test has_nodes returns True when nodes exist."""
        analytics = ModelAnalyticsCore(total_nodes=10)
        assert analytics.has_nodes() is True

    def test_has_nodes_false(self):
        """Test has_nodes returns False when no nodes."""
        analytics = ModelAnalyticsCore(total_nodes=0)
        assert analytics.has_nodes() is False

    def test_has_active_nodes_true(self):
        """Test has_active_nodes returns True when active nodes exist."""
        analytics = ModelAnalyticsCore(active_nodes=5)
        assert analytics.has_active_nodes() is True

    def test_has_active_nodes_false(self):
        """Test has_active_nodes returns False when no active nodes."""
        analytics = ModelAnalyticsCore(active_nodes=0)
        assert analytics.has_active_nodes() is False

    def test_has_issues_with_deprecated(self):
        """Test has_issues returns True with deprecated nodes."""
        analytics = ModelAnalyticsCore(deprecated_nodes=5)
        assert analytics.has_issues() is True

    def test_has_issues_with_disabled(self):
        """Test has_issues returns True with disabled nodes."""
        analytics = ModelAnalyticsCore(disabled_nodes=3)
        assert analytics.has_issues() is True

    def test_has_issues_with_both(self):
        """Test has_issues returns True with both deprecated and disabled."""
        analytics = ModelAnalyticsCore(deprecated_nodes=2, disabled_nodes=3)
        assert analytics.has_issues() is True

    def test_has_issues_false(self):
        """Test has_issues returns False with no issues."""
        analytics = ModelAnalyticsCore(total_nodes=100, active_nodes=100)
        assert analytics.has_issues() is False


@pytest.mark.unit
class TestModelAnalyticsCoreUpdateMethods:
    """Tests for ModelAnalyticsCore update methods."""

    def test_update_node_counts(self):
        """Test update_node_counts method."""
        analytics = ModelAnalyticsCore()
        analytics.update_node_counts(
            total=100,
            active=75,
            deprecated=15,
            disabled=10,
        )
        assert analytics.total_nodes == 100
        assert analytics.active_nodes == 75
        assert analytics.deprecated_nodes == 15
        assert analytics.disabled_nodes == 10

    def test_update_node_counts_negative_values(self):
        """Test update_node_counts with negative values."""
        analytics = ModelAnalyticsCore()
        analytics.update_node_counts(
            total=-10,
            active=-5,
            deprecated=-3,
            disabled=-2,
        )
        # Negative values should be clamped to 0
        assert analytics.total_nodes == 0
        assert analytics.active_nodes == 0
        assert analytics.deprecated_nodes == 0
        assert analytics.disabled_nodes == 0

    def test_update_node_counts_replaces_existing(self):
        """Test update_node_counts replaces existing values."""
        analytics = ModelAnalyticsCore(
            total_nodes=50,
            active_nodes=40,
            deprecated_nodes=5,
            disabled_nodes=5,
        )
        analytics.update_node_counts(total=100, active=90, deprecated=5, disabled=5)
        assert analytics.total_nodes == 100
        assert analytics.active_nodes == 90

    def test_add_nodes_basic(self):
        """Test add_nodes method with basic values."""
        analytics = ModelAnalyticsCore(total_nodes=50, active_nodes=40)
        analytics.add_nodes(total=25, active=20)
        assert analytics.total_nodes == 75
        assert analytics.active_nodes == 60

    def test_add_nodes_all_types(self):
        """Test add_nodes method with all node types."""
        analytics = ModelAnalyticsCore(
            total_nodes=100,
            active_nodes=80,
            deprecated_nodes=10,
            disabled_nodes=10,
        )
        analytics.add_nodes(total=50, active=30, deprecated=10, disabled=10)
        assert analytics.total_nodes == 150
        assert analytics.active_nodes == 110
        assert analytics.deprecated_nodes == 20
        assert analytics.disabled_nodes == 20

    def test_add_nodes_negative_values(self):
        """Test add_nodes ignores negative values."""
        analytics = ModelAnalyticsCore(total_nodes=100)
        analytics.add_nodes(total=-50, active=-25)
        # Negative values should be treated as 0
        assert analytics.total_nodes == 100
        assert analytics.active_nodes == 0

    def test_add_nodes_zero_values(self):
        """Test add_nodes with zero values."""
        analytics = ModelAnalyticsCore(total_nodes=100)
        analytics.add_nodes(total=0, active=0)
        assert analytics.total_nodes == 100
        assert analytics.active_nodes == 0


@pytest.mark.unit
class TestModelAnalyticsCoreFactoryMethods:
    """Tests for ModelAnalyticsCore factory methods."""

    def test_create_for_collection(self):
        """Test create_for_collection factory method."""
        collection_id = uuid4()
        analytics = ModelAnalyticsCore.create_for_collection(
            collection_id=collection_id,
            collection_name="Test Collection",
        )
        assert analytics.collection_id == collection_id
        assert analytics.collection_display_name == "Test Collection"
        assert analytics.total_nodes == 0
        assert analytics.active_nodes == 0

    def test_create_with_counts(self):
        """Test create_with_counts factory method."""
        analytics = ModelAnalyticsCore.create_with_counts(
            collection_name="Test Collection",
            total_nodes=100,
            active_nodes=80,
            deprecated_nodes=10,
            disabled_nodes=10,
        )
        assert isinstance(analytics.collection_id, UUID)
        assert analytics.collection_display_name == "Test Collection"
        assert analytics.total_nodes == 100
        assert analytics.active_nodes == 80
        assert analytics.deprecated_nodes == 10
        assert analytics.disabled_nodes == 10

    def test_create_with_counts_minimal(self):
        """Test create_with_counts with minimal parameters."""
        analytics = ModelAnalyticsCore.create_with_counts(
            collection_name="Minimal",
            total_nodes=50,
            active_nodes=50,
        )
        assert analytics.collection_display_name == "Minimal"
        assert analytics.total_nodes == 50
        assert analytics.active_nodes == 50
        assert analytics.deprecated_nodes == 0
        assert analytics.disabled_nodes == 0

    def test_create_with_counts_deterministic_id(self):
        """Test create_with_counts generates deterministic ID."""
        analytics1 = ModelAnalyticsCore.create_with_counts(
            collection_name="Test",
            total_nodes=10,
            active_nodes=10,
        )
        analytics2 = ModelAnalyticsCore.create_with_counts(
            collection_name="Test",
            total_nodes=20,
            active_nodes=15,
        )
        # Same collection name should generate same ID
        assert analytics1.collection_id == analytics2.collection_id


@pytest.mark.unit
class TestModelAnalyticsCoreProtocols:
    """Tests for ModelAnalyticsCore protocol implementations."""

    def test_get_metadata(self):
        """Test get_metadata method."""
        analytics = ModelAnalyticsCore(collection_display_name="Test")
        metadata = analytics.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata(self):
        """Test set_metadata method."""
        analytics = ModelAnalyticsCore()
        result = analytics.set_metadata(
            {"collection_display_name": "Updated Collection"}
        )
        assert result is True
        assert analytics.collection_display_name == "Updated Collection"

    def test_set_metadata_with_exception(self):
        """Test set_metadata error handling."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        analytics = ModelAnalyticsCore()
        # Setting invalid type should raise ModelOnexError
        with pytest.raises(ModelOnexError):
            analytics.set_metadata({"total_nodes": "invalid"})

    def test_serialize(self):
        """Test serialize method."""
        analytics = ModelAnalyticsCore(
            collection_display_name="Test",
            total_nodes=100,
        )
        data = analytics.serialize()
        assert isinstance(data, dict)
        assert "collection_id" in data
        assert "collection_display_name" in data
        assert "total_nodes" in data

    def test_validate_instance(self):
        """Test validate_instance method."""
        analytics = ModelAnalyticsCore()
        assert analytics.validate_instance() is True


@pytest.mark.unit
class TestModelAnalyticsCoreSerialization:
    """Tests for ModelAnalyticsCore serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        collection_id = uuid4()
        analytics = ModelAnalyticsCore(
            collection_id=collection_id,
            collection_display_name="Test",
            total_nodes=100,
            active_nodes=80,
        )
        data = analytics.model_dump()
        assert data["collection_id"] == collection_id
        assert data["collection_display_name"] == "Test"
        assert data["total_nodes"] == 100
        assert data["active_nodes"] == 80

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none."""
        analytics = ModelAnalyticsCore(total_nodes=50)
        data = analytics.model_dump(exclude_none=True)
        assert "collection_display_name" not in data
        assert "total_nodes" in data


@pytest.mark.unit
class TestModelAnalyticsCoreEdgeCases:
    """Tests for ModelAnalyticsCore edge cases."""

    def test_very_large_node_counts(self):
        """Test analytics with very large node counts."""
        large_count = 1_000_000
        analytics = ModelAnalyticsCore(
            total_nodes=large_count,
            active_nodes=large_count - 1000,
        )
        assert analytics.total_nodes == large_count
        assert analytics.active_node_ratio > 0.99

    def test_ratios_with_rounding(self):
        """Test node ratios handle floating point precision."""
        analytics = ModelAnalyticsCore(total_nodes=3, active_nodes=1)
        ratio = analytics.active_node_ratio
        # 1/3 should be approximately 0.333...
        assert 0.333 < ratio < 0.334

    def test_empty_collection_name(self):
        """Test analytics with empty collection name."""
        analytics = ModelAnalyticsCore(collection_display_name="")
        assert analytics.collection_display_name == ""
        assert analytics.collection_name == ""

    def test_unicode_collection_name(self):
        """Test analytics with unicode collection name."""
        unicode_name = "Collection 世界 🌍"
        analytics = ModelAnalyticsCore(collection_display_name=unicode_name)
        assert analytics.collection_display_name == unicode_name

    def test_simultaneous_updates(self):
        """Test multiple updates don't conflict."""
        analytics = ModelAnalyticsCore()
        analytics.update_node_counts(total=100, active=80, deprecated=10, disabled=10)
        analytics.add_nodes(total=50, active=40, deprecated=5, disabled=5)
        assert analytics.total_nodes == 150
        assert analytics.active_nodes == 120
        assert analytics.deprecated_nodes == 15
        assert analytics.disabled_nodes == 15

    def test_all_nodes_deprecated(self):
        """Test analytics when all nodes are deprecated."""
        analytics = ModelAnalyticsCore(
            total_nodes=100,
            active_nodes=0,
            deprecated_nodes=100,
        )
        assert analytics.deprecated_node_ratio == 1.0
        assert analytics.active_node_ratio == 0.0
        assert analytics.has_issues() is True

    def test_counts_exceed_total(self):
        """Test when active+deprecated+disabled exceeds total."""
        # This shouldn't be allowed in reality but test the model handles it
        analytics = ModelAnalyticsCore(
            total_nodes=100,
            active_nodes=60,
            deprecated_nodes=30,
            disabled_nodes=30,  # Total: 120 > 100
        )
        # Model should still store the values
        assert analytics.total_nodes == 100
        assert analytics.active_nodes == 60
        assert analytics.deprecated_nodes == 30
        assert analytics.disabled_nodes == 30
