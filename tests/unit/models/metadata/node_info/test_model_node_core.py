# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelNodeCore."""

from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_conceptual_complexity import EnumConceptualComplexity
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.metadata.node_info.model_node_core import ModelNodeCore
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelNodeCoreInstantiation:
    """Tests for ModelNodeCore instantiation."""

    def test_create_with_defaults(self):
        """Test creating node core with default values."""
        node = ModelNodeCore()
        assert isinstance(node.node_id, UUID)
        assert node.node_display_name is None
        assert node.description is None
        assert node.node_type == EnumNodeType.UNKNOWN
        assert node.status == EnumMetadataNodeStatus.ACTIVE
        assert node.complexity == EnumConceptualComplexity.INTERMEDIATE
        assert isinstance(node.version, ModelSemVer)

    def test_create_with_node_info(self):
        """Test creating node core with basic node info."""
        node_id = uuid4()
        node = ModelNodeCore(
            node_id=node_id,
            node_display_name="Test Node",
            description="A test node",
        )
        assert node.node_id == node_id
        assert node.node_display_name == "Test Node"
        assert node.description == "A test node"

    def test_create_with_node_type(self):
        """Test creating node core with specific node type."""
        node = ModelNodeCore(node_type=EnumNodeType.COMPUTE_GENERIC)
        assert node.node_type == EnumNodeType.COMPUTE_GENERIC

    def test_create_with_status(self):
        """Test creating node core with specific status."""
        node = ModelNodeCore(status=EnumMetadataNodeStatus.DEPRECATED)
        assert node.status == EnumMetadataNodeStatus.DEPRECATED

    def test_create_with_complexity(self):
        """Test creating node core with specific complexity."""
        node = ModelNodeCore(complexity=EnumConceptualComplexity.ADVANCED)
        assert node.complexity == EnumConceptualComplexity.ADVANCED

    def test_create_with_version(self):
        """Test creating node core with specific version."""
        version = ModelSemVer(major=2, minor=3, patch=4)
        node = ModelNodeCore(version=version)
        assert node.version.major == 2
        assert node.version.minor == 3
        assert node.version.patch == 4


@pytest.mark.unit
class TestModelNodeCoreProperties:
    """Tests for ModelNodeCore properties."""

    def test_node_name_property(self):
        """Test node_name property."""
        node = ModelNodeCore(node_display_name="Test Name")
        assert node.node_name == "Test Name"

    def test_node_name_property_none(self):
        """Test node_name property when None."""
        node = ModelNodeCore()
        assert node.node_name is None

    def test_is_active_true(self):
        """Test is_active returns True for active status."""
        node = ModelNodeCore(status=EnumMetadataNodeStatus.ACTIVE)
        assert node.is_active is True

    def test_is_active_false(self):
        """Test is_active returns False for non-active status."""
        node = ModelNodeCore(status=EnumMetadataNodeStatus.DEPRECATED)
        assert node.is_active is False

    def test_is_deprecated_true(self):
        """Test is_deprecated returns True for deprecated status."""
        node = ModelNodeCore(status=EnumMetadataNodeStatus.DEPRECATED)
        assert node.is_deprecated is True

    def test_is_deprecated_false(self):
        """Test is_deprecated returns False for non-deprecated status."""
        node = ModelNodeCore(status=EnumMetadataNodeStatus.ACTIVE)
        assert node.is_deprecated is False

    def test_is_disabled_true(self):
        """Test is_disabled returns True for disabled status."""
        node = ModelNodeCore(status=EnumMetadataNodeStatus.DISABLED)
        assert node.is_disabled is True

    def test_is_disabled_false(self):
        """Test is_disabled returns False for non-disabled status."""
        node = ModelNodeCore(status=EnumMetadataNodeStatus.ACTIVE)
        assert node.is_disabled is False

    def test_is_simple_true(self):
        """Test is_simple returns True for trivial complexity."""
        node = ModelNodeCore(complexity=EnumConceptualComplexity.TRIVIAL)
        assert node.is_simple is True

    def test_is_simple_false(self):
        """Test is_simple returns False for non-trivial complexity."""
        node = ModelNodeCore(complexity=EnumConceptualComplexity.INTERMEDIATE)
        assert node.is_simple is False

    def test_is_complex_true_advanced(self):
        """Test is_complex returns True for advanced complexity."""
        node = ModelNodeCore(complexity=EnumConceptualComplexity.ADVANCED)
        assert node.is_complex is True

    def test_is_complex_true_expert(self):
        """Test is_complex returns True for expert complexity."""
        node = ModelNodeCore(complexity=EnumConceptualComplexity.EXPERT)
        assert node.is_complex is True

    def test_is_complex_false(self):
        """Test is_complex returns False for low complexity."""
        node = ModelNodeCore(complexity=EnumConceptualComplexity.BASIC)
        assert node.is_complex is False

    def test_version_string_property(self):
        """Test version_string property."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        node = ModelNodeCore(version=version)
        assert node.version_string == "1.2.3"


@pytest.mark.unit
class TestModelNodeCoreUpdateMethods:
    """Tests for ModelNodeCore update methods."""

    def test_update_status(self):
        """Test update_status method."""
        node = ModelNodeCore(status=EnumMetadataNodeStatus.ACTIVE)
        node.update_status(EnumMetadataNodeStatus.DEPRECATED)
        assert node.status == EnumMetadataNodeStatus.DEPRECATED

    def test_update_complexity(self):
        """Test update_complexity method."""
        node = ModelNodeCore(complexity=EnumConceptualComplexity.BASIC)
        node.update_complexity(EnumConceptualComplexity.ADVANCED)
        assert node.complexity == EnumConceptualComplexity.ADVANCED

    def test_update_version_all_components(self):
        """Test update_version with all components."""
        node = ModelNodeCore()
        node.update_version(major=2, minor=3, patch=4)
        assert node.version.major == 2
        assert node.version.minor == 3
        assert node.version.patch == 4

    def test_update_version_major_only(self):
        """Test update_version with major only."""
        node = ModelNodeCore(version=ModelSemVer(major=1, minor=2, patch=3))
        node.update_version(major=5)
        assert node.version.major == 5
        assert node.version.minor == 2
        assert node.version.patch == 3

    def test_update_version_minor_only(self):
        """Test update_version with minor only."""
        node = ModelNodeCore(version=ModelSemVer(major=1, minor=2, patch=3))
        node.update_version(minor=9)
        assert node.version.major == 1
        assert node.version.minor == 9
        assert node.version.patch == 3

    def test_update_version_patch_only(self):
        """Test update_version with patch only."""
        node = ModelNodeCore(version=ModelSemVer(major=1, minor=2, patch=3))
        node.update_version(patch=7)
        assert node.version.major == 1
        assert node.version.minor == 2
        assert node.version.patch == 7

    def test_increment_version_patch(self):
        """Test increment_version for patch level."""
        node = ModelNodeCore(version=ModelSemVer(major=1, minor=2, patch=3))
        node.increment_version("patch")
        assert node.version.major == 1
        assert node.version.minor == 2
        assert node.version.patch == 4

    def test_increment_version_minor(self):
        """Test increment_version for minor level."""
        node = ModelNodeCore(version=ModelSemVer(major=1, minor=2, patch=3))
        node.increment_version("minor")
        assert node.version.major == 1
        assert node.version.minor == 3
        assert node.version.patch == 0

    def test_increment_version_major(self):
        """Test increment_version for major level."""
        node = ModelNodeCore(version=ModelSemVer(major=1, minor=2, patch=3))
        node.increment_version("major")
        assert node.version.major == 2
        assert node.version.minor == 0
        assert node.version.patch == 0

    def test_increment_version_default(self):
        """Test increment_version with default (patch) level."""
        node = ModelNodeCore(version=ModelSemVer(major=1, minor=2, patch=3))
        node.increment_version()
        assert node.version.patch == 4


@pytest.mark.unit
class TestModelNodeCorePredicates:
    """Tests for ModelNodeCore predicate methods."""

    def test_has_description_true(self):
        """Test has_description returns True when description exists."""
        node = ModelNodeCore(description="Test description")
        assert node.has_description() is True

    def test_has_description_false_none(self):
        """Test has_description returns False when None."""
        node = ModelNodeCore(description=None)
        assert node.has_description() is False

    def test_has_description_false_empty(self):
        """Test has_description returns False when empty."""
        node = ModelNodeCore(description="")
        assert node.has_description() is False

    def test_has_description_false_whitespace(self):
        """Test has_description returns False for whitespace only."""
        node = ModelNodeCore(description="   ")
        assert node.has_description() is False

    def test_get_complexity_level(self):
        """Test get_complexity_level method."""
        node = ModelNodeCore(complexity=EnumConceptualComplexity.ADVANCED)
        level = node.get_complexity_level()
        assert level == EnumConceptualComplexity.ADVANCED.value


@pytest.mark.unit
class TestModelNodeCoreFactoryMethods:
    """Tests for ModelNodeCore factory methods."""

    def test_create_for_node(self):
        """Test create_for_node factory method."""
        node_id = uuid4()
        node = ModelNodeCore.create_for_node(
            node_id=node_id,
            node_name="Test Node",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            description="A test compute node",
        )
        assert node.node_id == node_id
        assert node.node_display_name == "Test Node"
        assert node.node_type == EnumNodeType.COMPUTE_GENERIC
        assert node.description == "A test compute node"

    def test_create_for_node_no_description(self):
        """Test create_for_node without description."""
        node_id = uuid4()
        node = ModelNodeCore.create_for_node(
            node_id=node_id,
            node_name="Minimal Node",
            node_type=EnumNodeType.EFFECT_GENERIC,
        )
        assert node.node_id == node_id
        assert node.node_display_name == "Minimal Node"
        assert node.node_type == EnumNodeType.EFFECT_GENERIC
        assert node.description is None

    def test_create_minimal_node(self):
        """Test create_minimal_node factory method."""
        node = ModelNodeCore.create_minimal_node(
            node_name="Minimal",
            node_type=EnumNodeType.REDUCER_GENERIC,
        )
        assert node.node_display_name == "Minimal"
        assert node.node_type == EnumNodeType.REDUCER_GENERIC
        assert node.description is None
        assert node.complexity == EnumConceptualComplexity.BASIC

    def test_create_minimal_node_default_type(self):
        """Test create_minimal_node with default type."""
        node = ModelNodeCore.create_minimal_node(node_name="Simple")
        assert node.node_display_name == "Simple"
        assert node.node_type == EnumNodeType.UNKNOWN
        assert node.complexity == EnumConceptualComplexity.BASIC

    def test_create_complex_node(self):
        """Test create_complex_node factory method."""
        node = ModelNodeCore.create_complex_node(
            node_name="Complex",
            node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
            description="A complex orchestrator node",
        )
        assert node.node_display_name == "Complex"
        assert node.node_type == EnumNodeType.ORCHESTRATOR_GENERIC
        assert node.description == "A complex orchestrator node"
        assert node.complexity == EnumConceptualComplexity.ADVANCED

    def test_create_minimal_node_deterministic_id(self):
        """Test create_minimal_node generates deterministic ID."""
        node1 = ModelNodeCore.create_minimal_node("Test")
        node2 = ModelNodeCore.create_minimal_node("Test")
        # Same name should generate same node_id
        assert node1.node_id == node2.node_id


@pytest.mark.unit
class TestModelNodeCoreProtocols:
    """Tests for ModelNodeCore protocol implementations."""

    def test_get_metadata(self):
        """Test get_metadata method."""
        node = ModelNodeCore(
            node_display_name="Test",
            description="Test description",
        )
        metadata = node.get_metadata()
        assert isinstance(metadata, dict)
        assert "description" in metadata

    def test_set_metadata(self):
        """Test set_metadata method."""
        node = ModelNodeCore()
        result = node.set_metadata({"description": "New description"})
        assert result is True
        assert node.description == "New description"

    def test_set_metadata_with_exception(self):
        """Test set_metadata error handling."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        node = ModelNodeCore()
        # Setting invalid enum should raise ModelOnexError
        with pytest.raises(ModelOnexError):
            node.set_metadata({"status": "invalid_status"})

    def test_serialize(self):
        """Test serialize method."""
        node = ModelNodeCore(
            node_display_name="Test",
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )
        data = node.serialize()
        assert isinstance(data, dict)
        assert "node_id" in data
        assert "node_display_name" in data
        assert "node_type" in data

    def test_validate_instance(self):
        """Test validate_instance method."""
        node = ModelNodeCore()
        assert node.validate_instance() is True


@pytest.mark.unit
class TestModelNodeCoreSerialization:
    """Tests for ModelNodeCore serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        node_id = uuid4()
        version = ModelSemVer(major=1, minor=2, patch=3)
        node = ModelNodeCore(
            node_id=node_id,
            node_display_name="Test",
            description="Test node",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            status=EnumMetadataNodeStatus.ACTIVE,
            complexity=EnumConceptualComplexity.INTERMEDIATE,
            version=version,
        )
        data = node.model_dump()
        assert data["node_id"] == node_id
        assert data["node_display_name"] == "Test"
        assert data["description"] == "Test node"

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none."""
        node = ModelNodeCore()
        data = node.model_dump(exclude_none=True)
        assert "node_display_name" not in data
        assert "description" not in data
        assert "node_id" in data  # Required field


@pytest.mark.unit
class TestModelNodeCoreEdgeCases:
    """Tests for ModelNodeCore edge cases."""

    def test_empty_node_display_name(self):
        """Test node with empty display name."""
        node = ModelNodeCore(node_display_name="")
        assert node.node_display_name == ""
        assert node.node_name == ""

    def test_unicode_node_name(self):
        """Test node with unicode display name."""
        unicode_name = "Node 世界 🌍"
        node = ModelNodeCore(node_display_name=unicode_name)
        assert node.node_display_name == unicode_name

    def test_very_long_description(self):
        """Test node with very long description."""
        long_desc = "A" * 10000
        node = ModelNodeCore(description=long_desc)
        assert len(node.description) == 10000

    def test_version_increment_multiple_times(self):
        """Test incrementing version multiple times."""
        node = ModelNodeCore(version=ModelSemVer(major=1, minor=0, patch=0))
        node.increment_version("patch")
        node.increment_version("patch")
        node.increment_version("patch")
        assert node.version.patch == 3

        node.increment_version("minor")
        assert node.version.minor == 1
        assert node.version.patch == 0

    def test_status_transitions(self):
        """Test multiple status transitions."""
        node = ModelNodeCore(status=EnumMetadataNodeStatus.ACTIVE)
        assert node.is_active is True

        node.update_status(EnumMetadataNodeStatus.DEPRECATED)
        assert node.is_deprecated is True
        assert node.is_active is False

        node.update_status(EnumMetadataNodeStatus.DISABLED)
        assert node.is_disabled is True
        assert node.is_deprecated is False

    def test_complexity_transitions(self):
        """Test multiple complexity transitions."""
        node = ModelNodeCore(complexity=EnumConceptualComplexity.BASIC)
        assert node.is_simple is False
        assert node.is_complex is False

        node.update_complexity(EnumConceptualComplexity.ADVANCED)
        assert node.is_complex is True
        assert node.is_simple is False

        node.update_complexity(EnumConceptualComplexity.TRIVIAL)
        assert node.is_simple is True
        assert node.is_complex is False

    def test_all_node_types(self):
        """Test creating nodes with all node types."""
        for node_type in EnumNodeType:
            node = ModelNodeCore(node_type=node_type)
            assert node.node_type == node_type

    def test_all_statuses(self):
        """Test creating nodes with all statuses."""
        for status in EnumMetadataNodeStatus:
            node = ModelNodeCore(status=status)
            assert node.status == status

    def test_all_complexities(self):
        """Test creating nodes with all complexities."""
        for complexity in EnumConceptualComplexity:
            node = ModelNodeCore(complexity=complexity)
            assert node.complexity == complexity

    def test_version_zero(self):
        """Test node with version 0.0.0."""
        version = ModelSemVer(major=0, minor=0, patch=0)
        node = ModelNodeCore(version=version)
        assert node.version.major == 0
        assert node.version.minor == 0
        assert node.version.patch == 0
