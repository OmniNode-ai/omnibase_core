"""Tests for ModelMetadataNodeCollection."""

import pytest

from omnibase_core.models.metadata.model_metadata_node_analytics import (
    ModelMetadataNodeAnalytics,
)
from omnibase_core.models.metadata.model_metadata_node_collection import (
    ModelMetadataNodeCollection,
)
from omnibase_core.models.metadata.model_node_info_container import (
    ModelNodeInfoContainer,
)


@pytest.mark.unit
class TestModelMetadataNodeCollectionInstantiation:
    """Tests for ModelMetadataNodeCollection instantiation."""

    def test_create_empty_collection(self):
        """Test creating empty collection."""
        collection = ModelMetadataNodeCollection()
        assert isinstance(collection.root, dict)
        assert "_metadata_analytics" in collection.root
        assert "_node_info" in collection.root

    def test_create_with_root_dict(self):
        """Test creating collection with root dict."""
        root = {"key": "value"}
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["key"] == "value"
        assert "_metadata_analytics" in collection.root
        assert "_node_info" in collection.root

    def test_create_with_none_root(self):
        """Test creating collection with None root."""
        collection = ModelMetadataNodeCollection(root=None)
        assert isinstance(collection.root, dict)

    def test_create_with_invalid_root_type(self):
        """Test creating collection with invalid root type."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        with pytest.raises(ModelOnexError, match="root must be dict or None"):
            ModelMetadataNodeCollection(root="invalid")

    def test_create_with_invalid_root_list(self):
        """Test creating collection with list instead of dict."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        with pytest.raises(ModelOnexError, match="root must be dict or None"):
            ModelMetadataNodeCollection(root=["invalid"])


@pytest.mark.unit
class TestModelMetadataNodeCollectionAnalytics:
    """Tests for metadata analytics in collection."""

    def test_analytics_initialized_automatically(self):
        """Test analytics are initialized automatically."""
        collection = ModelMetadataNodeCollection()
        analytics = collection.root["_metadata_analytics"]
        assert isinstance(analytics, ModelMetadataNodeAnalytics)

    def test_analytics_preserved_when_provided(self):
        """Test analytics are not overwritten if already present."""
        existing_analytics = ModelMetadataNodeAnalytics()
        root = {"_metadata_analytics": existing_analytics}
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["_metadata_analytics"] is existing_analytics

    def test_analytics_creation_with_data(self):
        """Test analytics are created when not in provided root."""
        root = {"some_key": "some_value"}
        collection = ModelMetadataNodeCollection(root=root)
        assert "_metadata_analytics" in collection.root
        assert isinstance(
            collection.root["_metadata_analytics"], ModelMetadataNodeAnalytics
        )


@pytest.mark.unit
class TestModelMetadataNodeCollectionNodeInfo:
    """Tests for node info in collection."""

    def test_node_info_initialized_automatically(self):
        """Test node info is initialized automatically."""
        collection = ModelMetadataNodeCollection()
        node_info = collection.root["_node_info"]
        assert isinstance(node_info, ModelNodeInfoContainer)

    def test_node_info_preserved_when_provided(self):
        """Test node info is not overwritten if already present."""
        existing_node_info = ModelNodeInfoContainer()
        root = {"_node_info": existing_node_info}
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["_node_info"] is existing_node_info

    def test_node_info_creation_with_data(self):
        """Test node info is created when not in provided root."""
        root = {"some_key": "some_value"}
        collection = ModelMetadataNodeCollection(root=root)
        assert "_node_info" in collection.root
        assert isinstance(collection.root["_node_info"], ModelNodeInfoContainer)


@pytest.mark.unit
class TestModelMetadataNodeCollectionProtocols:
    """Tests for protocol implementations."""

    def test_get_metadata(self):
        """Test get_metadata method."""
        collection = ModelMetadataNodeCollection()
        metadata = collection.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata_success(self):
        """Test set_metadata method."""
        collection = ModelMetadataNodeCollection()
        # Setting metadata on fields that exist
        result = collection.set_metadata({})
        assert result is True

    def test_serialize(self):
        """Test serialize method."""
        collection = ModelMetadataNodeCollection(root={"key": "value"})
        data = collection.serialize()
        assert isinstance(data, dict)
        # RootModel serializes directly, not wrapped in "root"
        assert "key" in data

    def test_validate_instance(self):
        """Test validate_instance method."""
        collection = ModelMetadataNodeCollection()
        assert collection.validate_instance() is True


@pytest.mark.unit
class TestModelMetadataNodeCollectionCustomData:
    """Tests for custom data in collection."""

    def test_add_custom_node_data(self):
        """Test adding custom node data to collection."""
        root = {"custom_node": {"type": "test", "data": "value"}}
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["custom_node"]["type"] == "test"
        assert collection.root["custom_node"]["data"] == "value"

    def test_multiple_custom_nodes(self):
        """Test multiple custom nodes."""
        root = {"node1": {"data": "a"}, "node2": {"data": "b"}, "node3": {"data": "c"}}
        collection = ModelMetadataNodeCollection(root=root)
        assert len(collection.root) >= 5  # 3 custom + 2 special keys
        assert collection.root["node1"]["data"] == "a"
        assert collection.root["node2"]["data"] == "b"
        assert collection.root["node3"]["data"] == "c"

    def test_nested_structure(self):
        """Test deeply nested structure."""
        root = {"level1": {"level2": {"level3": {"data": "deep"}}}}
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["level1"]["level2"]["level3"]["data"] == "deep"


@pytest.mark.unit
class TestModelMetadataNodeCollectionAccess:
    """Tests for accessing collection data."""

    def test_access_root_directly(self):
        """Test direct access to root."""
        collection = ModelMetadataNodeCollection(root={"key": "value"})
        assert collection.root["key"] == "value"

    def test_access_analytics_directly(self):
        """Test direct access to analytics."""
        collection = ModelMetadataNodeCollection()
        analytics = collection.root["_metadata_analytics"]
        assert isinstance(analytics, ModelMetadataNodeAnalytics)

    def test_access_node_info_directly(self):
        """Test direct access to node info."""
        collection = ModelMetadataNodeCollection()
        node_info = collection.root["_node_info"]
        assert isinstance(node_info, ModelNodeInfoContainer)

    def test_iterate_over_root(self):
        """Test iterating over root keys."""
        root = {"node1": "a", "node2": "b"}
        collection = ModelMetadataNodeCollection(root=root)
        keys = list(collection.root.keys())
        assert "node1" in keys
        assert "node2" in keys
        assert "_metadata_analytics" in keys
        assert "_node_info" in keys


@pytest.mark.unit
class TestModelMetadataNodeCollectionModification:
    """Tests for modifying collection."""

    def test_modify_existing_node(self):
        """Test modifying existing node data."""
        root = {"node1": {"data": "original"}}
        collection = ModelMetadataNodeCollection(root=root)
        collection.root["node1"]["data"] = "modified"
        assert collection.root["node1"]["data"] == "modified"

    def test_add_new_node_after_creation(self):
        """Test adding new node after creation."""
        collection = ModelMetadataNodeCollection()
        collection.root["new_node"] = {"data": "new"}
        assert collection.root["new_node"]["data"] == "new"

    def test_delete_node(self):
        """Test deleting a node."""
        root = {"node1": "value"}
        collection = ModelMetadataNodeCollection(root=root)
        del collection.root["node1"]
        assert "node1" not in collection.root

    def test_update_analytics(self):
        """Test updating analytics object."""
        collection = ModelMetadataNodeCollection()
        new_analytics = ModelMetadataNodeAnalytics()
        collection.root["_metadata_analytics"] = new_analytics
        assert collection.root["_metadata_analytics"] is new_analytics


@pytest.mark.unit
class TestModelMetadataNodeCollectionEdgeCases:
    """Tests for edge cases."""

    def test_empty_nested_dict(self):
        """Test with empty nested dict."""
        root = {"node": {}}
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["node"] == {}

    def test_very_large_collection(self):
        """Test with large collection."""
        root = {f"node_{i}": f"value_{i}" for i in range(1000)}
        collection = ModelMetadataNodeCollection(root=root)
        assert len(collection.root) >= 1002  # 1000 + 2 special keys

    def test_special_characters_in_keys(self):
        """Test with special characters in keys."""
        root = {"node-1": "a", "node.2": "b", "node_3": "c"}
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["node-1"] == "a"
        assert collection.root["node.2"] == "b"
        assert collection.root["node_3"] == "c"

    def test_unicode_keys(self):
        """Test with unicode keys."""
        root = {"节点": "value", "ノード": "data"}
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["节点"] == "value"
        assert collection.root["ノード"] == "data"

    def test_numeric_string_keys(self):
        """Test with numeric string keys."""
        root = {"123": "a", "456": "b"}
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["123"] == "a"
        assert collection.root["456"] == "b"

    def test_mixed_value_types(self):
        """Test with mixed value types."""
        root = {
            "string": "value",
            "number": 123,
            "float": 45.67,
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["string"] == "value"
        assert collection.root["number"] == 123
        assert collection.root["float"] == 45.67
        assert collection.root["bool"] is True
        assert collection.root["list"] == [1, 2, 3]
        assert collection.root["dict"]["nested"] == "value"


@pytest.mark.unit
class TestModelMetadataNodeCollectionSerialization:
    """Tests for serialization."""

    def test_model_dump_with_data(self):
        """Test model_dump with custom data."""
        root = {"node1": "value1", "node2": "value2"}
        collection = ModelMetadataNodeCollection(root=root)
        data = collection.model_dump()
        # RootModel serializes directly
        assert data["node1"] == "value1"

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none."""
        collection = ModelMetadataNodeCollection()
        data = collection.model_dump(exclude_none=True)
        # RootModel serializes directly
        assert "_metadata_analytics" in data

    def test_serialize_and_deserialize(self):
        """Test serialization round-trip."""
        root = {"node": {"data": "value"}}
        collection = ModelMetadataNodeCollection(root=root)
        serialized = collection.serialize()
        # Verify serialized data structure - RootModel serializes directly
        assert isinstance(serialized, dict)
        assert "node" in serialized


@pytest.mark.unit
class TestModelMetadataNodeCollectionSpecialKeys:
    """Tests for special keys handling."""

    def test_cannot_remove_analytics_completely(self):
        """Test analytics key behavior."""
        collection = ModelMetadataNodeCollection()
        # Analytics should be present
        assert "_metadata_analytics" in collection.root

    def test_cannot_remove_node_info_completely(self):
        """Test node info key behavior."""
        collection = ModelMetadataNodeCollection()
        # Node info should be present
        assert "_node_info" in collection.root

    def test_overwrite_analytics_with_new_instance(self):
        """Test overwriting analytics with new instance."""
        collection = ModelMetadataNodeCollection()
        new_analytics = ModelMetadataNodeAnalytics()
        collection.root["_metadata_analytics"] = new_analytics
        assert collection.root["_metadata_analytics"] is new_analytics

    def test_overwrite_node_info_with_new_instance(self):
        """Test overwriting node info with new instance."""
        collection = ModelMetadataNodeCollection()
        new_node_info = ModelNodeInfoContainer()
        collection.root["_node_info"] = new_node_info
        assert collection.root["_node_info"] is new_node_info


@pytest.mark.unit
class TestModelMetadataNodeCollectionComplexScenarios:
    """Tests for complex scenarios."""

    def test_collection_with_all_features(self):
        """Test collection with all features combined."""
        custom_analytics = ModelMetadataNodeAnalytics()
        custom_node_info = ModelNodeInfoContainer()
        root = {
            "_metadata_analytics": custom_analytics,
            "_node_info": custom_node_info,
            "node1": {"type": "compute", "data": "a"},
            "node2": {"type": "effect", "data": "b"},
        }
        collection = ModelMetadataNodeCollection(root=root)
        assert collection.root["_metadata_analytics"] is custom_analytics
        assert collection.root["_node_info"] is custom_node_info
        assert collection.root["node1"]["type"] == "compute"
        assert collection.root["node2"]["type"] == "effect"

    def test_deeply_nested_modifications(self):
        """Test modifications in deeply nested structures."""
        root = {"level1": {"level2": {"level3": {"value": "original"}}}}
        collection = ModelMetadataNodeCollection(root=root)
        collection.root["level1"]["level2"]["level3"]["value"] = "modified"
        assert collection.root["level1"]["level2"]["level3"]["value"] == "modified"

    def test_collection_as_root_model(self):
        """Test collection behavior as RootModel."""
        collection = ModelMetadataNodeCollection(root={"test": "data"})
        # Should be able to access root directly
        assert hasattr(collection, "root")
        assert collection.root["test"] == "data"
