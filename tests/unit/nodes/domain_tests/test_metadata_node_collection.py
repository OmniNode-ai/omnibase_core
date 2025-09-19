"""
Test Metadata Node Collection functionality.

Validates that the ModelMetadataNodeCollection works correctly with
node management, analytics, and enterprise features.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from omnibase_core.models.nodes import ModelMetadataNodeCollection
from omnibase_core.models.core.model_function_node import ModelFunctionNode


class TestMetadataNodeCollection:
    """Test ModelMetadataNodeCollection functionality."""

    def test_empty_collection_creation(self):
        """Test creating an empty metadata node collection."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        assert collection.node_count == 0
        assert collection.collection_id is not None
        assert collection.health_score == 100.0
        assert collection.analytics is not None

    def test_collection_with_dict_initialization(self):
        """Test collection initialization with dictionary."""
        initial_data = {
            "test_node": {"name": "test_node", "description": "Test node"}
        }

        collection = ModelMetadataNodeCollection(initial_data)
        assert collection.node_count == 1
        assert collection.get_node("test_node") is not None

    def test_add_node_with_dict_data(self):
        """Test adding a node with dictionary data."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        node_data = {
            "name": "test_function",
            "description": "Test function description",
            "parameters": [],
            "return_type": "str",
        }

        success = collection.add_node("test_function", node_data)
        assert success
        assert collection.node_count == 1

        retrieved_node = collection.get_node("test_function")
        assert retrieved_node is not None

    def test_add_node_with_function_node(self):
        """Test adding a node with ModelFunctionNode."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        function_node = ModelFunctionNode(
            name="test_function",
            description="Test function",
            parameters=[],
            return_type="str",
        )

        success = collection.add_node("test_function", function_node)
        assert success
        assert collection.node_count == 1

    def test_add_node_with_invalid_name(self):
        """Test adding node with invalid name fails."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Invalid Python identifier
        success = collection.add_node("123invalid", {"name": "test"})
        assert not success
        assert collection.node_count == 0

    def test_remove_node(self):
        """Test removing a node from collection."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Add node
        node_data = {"name": "test_node", "description": "Test"}
        collection.add_node("test_node", node_data)
        assert collection.node_count == 1

        # Remove node
        success = collection.remove_node("test_node")
        assert success
        assert collection.node_count == 0
        assert collection.get_node("test_node") is None

    def test_remove_nonexistent_node(self):
        """Test removing non-existent node."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        success = collection.remove_node("nonexistent")
        assert not success

    def test_get_node_info(self):
        """Test getting node information."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Add node
        node_data = {"name": "test_node", "description": "Test"}
        collection.add_node("test_node", node_data)

        # Get node info
        node_info = collection.get_node_info("test_node")
        assert node_info is not None
        assert node_info.name == "test_node"

    def test_update_node_info(self):
        """Test updating node information."""
        from omnibase_core.models.nodes.model_metadata_node_info import ModelMetadataNodeInfo

        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Add node
        node_data = {"name": "test_node", "description": "Test"}
        collection.add_node("test_node", node_data)

        # Update node info
        updated_info = ModelMetadataNodeInfo(
            name="test_node",
            description="Updated description",
        )
        success = collection.update_node_info("test_node", updated_info)
        assert success

        # Verify update
        retrieved_info = collection.get_node_info("test_node")
        assert retrieved_info.description == "Updated description"

    def test_update_node_info_nonexistent(self):
        """Test updating info for non-existent node."""
        from omnibase_core.models.nodes.model_metadata_node_info import ModelMetadataNodeInfo

        collection = ModelMetadataNodeCollection.create_empty_collection()

        updated_info = ModelMetadataNodeInfo(name="nonexistent")
        success = collection.update_node_info("nonexistent", updated_info)
        assert not success

    def test_collection_id_generation(self):
        """Test collection ID generation."""
        collection1 = ModelMetadataNodeCollection.create_empty_collection()
        collection2 = ModelMetadataNodeCollection.create_empty_collection()

        # Empty collections should have same ID
        assert collection1.collection_id == collection2.collection_id

        # Adding different nodes should create different IDs
        collection1.add_node("node1", {"name": "node1"})
        collection2.add_node("node2", {"name": "node2"})

        assert collection1.collection_id != collection2.collection_id

    def test_analytics_tracking(self):
        """Test analytics tracking functionality."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Initial analytics
        analytics = collection.analytics
        assert analytics.total_nodes == 0

        # Add some nodes
        collection.add_node("node1", {"name": "node1"})
        collection.add_node("node2", {"name": "node2"})

        # Analytics should update
        updated_analytics = collection.analytics
        assert updated_analytics.total_nodes == 2

    def test_health_score_calculation(self):
        """Test health score calculation."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Empty collection should have perfect health
        assert collection.health_score == 100.0

        # Add healthy nodes
        collection.add_node("healthy_node", {"name": "healthy_node"})
        assert collection.health_score > 0

    def test_create_from_function_nodes(self):
        """Test creating collection from existing function nodes."""
        function_nodes = {
            "func1": ModelFunctionNode(
                name="func1",
                description="Function 1",
                parameters=[],
                return_type="str",
            ),
            "func2": ModelFunctionNode(
                name="func2",
                description="Function 2",
                parameters=[],
                return_type="int",
            ),
        }

        collection = ModelMetadataNodeCollection.create_from_function_nodes(
            function_nodes
        )

        assert collection.node_count == 2
        assert collection.get_node("func1") is not None
        assert collection.get_node("func2") is not None

    def test_create_documentation_collection(self):
        """Test creating documentation-focused collection."""
        collection = ModelMetadataNodeCollection.create_documentation_collection(
            "test_docs"
        )

        assert collection.node_count == 0
        analytics = collection.analytics
        # Should have documentation-specific analytics
        assert analytics is not None

    def test_metadata_analytics_fields(self):
        """Test metadata analytics structure."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Add node to populate analytics
        collection.add_node("test_node", {"name": "test_node"})

        analytics = collection.analytics
        assert hasattr(analytics, 'total_nodes')
        assert hasattr(analytics, 'last_modified')
        assert analytics.total_nodes == 1

    def test_node_validation_on_creation(self):
        """Test node validation during creation."""
        # Valid function name
        collection = ModelMetadataNodeCollection({
            "valid_function_name": {"name": "valid"}
        })
        assert collection.node_count == 1

        # Invalid function name should raise error
        with pytest.raises(ValueError, match="Invalid function name"):
            ModelMetadataNodeCollection({
                "123invalid": {"name": "invalid"}
            })

    def test_model_serialization(self):
        """Test model serialization and deserialization."""
        collection = ModelMetadataNodeCollection.create_empty_collection()
        collection.add_node("test_node", {"name": "test_node"})

        # Serialize
        serialized = collection.model_dump()
        assert isinstance(serialized, dict)

        # Deserialize
        restored = ModelMetadataNodeCollection.model_validate(serialized)
        assert restored.node_count == collection.node_count

    def test_enterprise_metadata_fields(self):
        """Test enterprise metadata fields are preserved."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Should have enterprise fields
        assert "_metadata_analytics" in collection.root
        assert "_node_info" in collection.root

        # Adding nodes shouldn't remove enterprise fields
        collection.add_node("test_node", {"name": "test_node"})
        assert "_metadata_analytics" in collection.root
        assert "_node_info" in collection.root

    def test_coerce_node_values_functionality(self):
        """Test node value coercion during initialization."""
        # Test with ModelFunctionNode dict that should be coerced
        data_with_coercible_node = {
            "test_function": {
                "name": "test_function",
                "description": "Test",
                "parameters": [],
                "return_type": "str",
            }
        }

        collection = ModelMetadataNodeCollection(data_with_coercible_node)
        node = collection.get_node("test_function")
        assert isinstance(node, ModelFunctionNode)

    def test_node_count_computed_field(self):
        """Test node_count computed field excludes metadata."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Initially empty
        assert collection.node_count == 0

        # Add regular nodes
        collection.add_node("node1", {"name": "node1"})
        collection.add_node("node2", {"name": "node2"})
        assert collection.node_count == 2

        # Enterprise metadata fields shouldn't count
        assert "_metadata_analytics" in collection.root
        assert "_node_info" in collection.root
        assert collection.node_count == 2  # Still 2, not 4

    def test_analytics_auto_update(self):
        """Test that analytics automatically update when nodes change."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        initial_analytics = collection.analytics
        initial_modified = initial_analytics.last_modified

        # Add node and check analytics update
        collection.add_node("test_node", {"name": "test_node"})

        updated_analytics = collection.analytics
        updated_modified = updated_analytics.last_modified

        # Should have different modification time
        assert updated_modified != initial_modified
        assert updated_analytics.total_nodes == 1

    def test_invalid_function_names_rejected(self):
        """Test that invalid function names are rejected."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        invalid_names = [
            "123starts_with_number",
            "contains-hyphen",
            "contains space",
            "contains.dot",
            "",
        ]

        for invalid_name in invalid_names:
            success = collection.add_node(invalid_name, {"name": "test"})
            assert not success, f"Should reject invalid name: {invalid_name}"

        assert collection.node_count == 0

    def test_collection_from_existing_collection(self):
        """Test creating collection from existing collection."""
        original = ModelMetadataNodeCollection.create_empty_collection()
        original.add_node("test_node", {"name": "test_node"})

        # Create new collection from existing
        new_collection = ModelMetadataNodeCollection(original)
        assert new_collection.node_count == 1
        assert new_collection.get_node("test_node") is not None

    def test_performance_with_many_nodes(self):
        """Test performance with many nodes."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Add many nodes
        num_nodes = 100
        for i in range(num_nodes):
            node_name = f"node_{i}"
            collection.add_node(node_name, {"name": node_name})

        assert collection.node_count == num_nodes

        # Analytics should handle many nodes
        analytics = collection.analytics
        assert analytics.total_nodes == num_nodes

        # Collection ID should be stable
        collection_id = collection.collection_id
        assert len(collection_id) == 16  # SHA256 hash truncated to 16 chars

    @pytest.mark.parametrize("node_count", [0, 1, 5, 10])
    def test_health_score_with_different_node_counts(self, node_count):
        """Test health score calculation with different node counts."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Add nodes
        for i in range(node_count):
            collection.add_node(f"node_{i}", {"name": f"node_{i}"})

        health_score = collection.health_score
        assert 0 <= health_score <= 100

        if node_count == 0:
            assert health_score == 100.0

    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling."""
        collection = ModelMetadataNodeCollection.create_empty_collection()

        # Test adding None data
        success = collection.add_node("test_node", None)
        assert not success

        # Test getting non-existent node
        node = collection.get_node("nonexistent")
        assert node is None

        # Test removing non-existent node
        success = collection.remove_node("nonexistent")
        assert not success

        # Test getting info for non-existent node
        info = collection.get_node_info("nonexistent")
        assert info is None