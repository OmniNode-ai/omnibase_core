"""Tests for get_metadata() implementations across models.

This module tests the fixed get_metadata() implementations to verify:
1. Each get_metadata() returns a properly typed TypedDictMetadataDict
2. The returned dict contains actual model field values (not empty/incorrect data)
3. The proper field mappings work (node_name -> name, node_version -> version, etc.)

Coverage includes models from different categories:
- node_metadata: ModelNodeCoreInfoSummary, ModelFunctionNode
- metadata/node_info: ModelNodeCore
- metadata: ModelInputState, ModelFieldIdentity
- analytics: ModelAnalyticsCore
"""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_conceptual_complexity import EnumConceptualComplexity
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_status import EnumStatus
from omnibase_core.models.metadata.analytics.model_analytics_core import (
    ModelAnalyticsCore,
)
from omnibase_core.models.metadata.model_field_identity import ModelFieldIdentity
from omnibase_core.models.metadata.model_input_state_class import ModelInputState
from omnibase_core.models.metadata.node_info.model_node_core import ModelNodeCore
from omnibase_core.models.node_metadata.model_function_node import ModelFunctionNode
from omnibase_core.models.node_metadata.model_node_core_info_summary import (
    ModelNodeCoreInfoSummary,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestGetMetadataImplementations:
    """Tests for get_metadata() implementations across models."""

    # =========================================================================
    # ModelNodeCoreInfoSummary Tests (node_metadata category)
    # =========================================================================

    def test_model_node_core_info_summary_get_metadata_returns_typed_dict(self) -> None:
        """Test ModelNodeCoreInfoSummary.get_metadata() returns TypedDictMetadataDict."""
        model = ModelNodeCoreInfoSummary(
            node_id=uuid4(),
            node_name="test-node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            status=EnumStatus.ACTIVE,
            health=EnumNodeHealthStatus.HEALTHY,
            is_active=True,
            is_healthy=True,
            has_description=True,
            has_author=True,
        )

        metadata = model.get_metadata()

        # Verify it's a dict (TypedDict is a dict at runtime)
        assert isinstance(metadata, dict)
        # Verify expected keys exist
        assert "name" in metadata
        assert "version" in metadata
        assert "metadata" in metadata

    def test_model_node_core_info_summary_get_metadata_name_mapping(self) -> None:
        """Test ModelNodeCoreInfoSummary maps node_name to name correctly."""
        expected_name = "my-custom-node"
        model = ModelNodeCoreInfoSummary(
            node_id=uuid4(),
            node_name=expected_name,
            node_type=EnumMetadataNodeType.METHOD,
            node_version=ModelSemVer(major=2, minor=1, patch=0),
            status=EnumStatus.ACTIVE,
            health=EnumNodeHealthStatus.HEALTHY,
            is_active=True,
            is_healthy=True,
            has_description=False,
            has_author=False,
        )

        metadata = model.get_metadata()

        assert metadata["name"] == expected_name

    def test_model_node_core_info_summary_get_metadata_version_mapping(self) -> None:
        """Test ModelNodeCoreInfoSummary maps node_version to version correctly."""
        expected_version = ModelSemVer(major=3, minor=2, patch=1)
        model = ModelNodeCoreInfoSummary(
            node_id=uuid4(),
            node_name="version-test-node",
            node_type=EnumMetadataNodeType.CLASS,
            node_version=expected_version,
            status=EnumStatus.COMPLETED,
            health=EnumNodeHealthStatus.DEGRADED,
            is_active=False,
            is_healthy=False,
            has_description=True,
            has_author=True,
        )

        metadata = model.get_metadata()

        assert metadata["version"] == expected_version
        # Verify actual version values
        assert metadata["version"].major == 3
        assert metadata["version"].minor == 2
        assert metadata["version"].patch == 1

    def test_model_node_core_info_summary_get_metadata_enums_serialized(self) -> None:
        """Test ModelNodeCoreInfoSummary serializes enums to .value in metadata dict."""
        node_id = uuid4()
        model = ModelNodeCoreInfoSummary(
            node_id=node_id,
            node_name="enum-test",
            node_type=EnumMetadataNodeType.MODULE,
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            status=EnumStatus.PENDING,
            health=EnumNodeHealthStatus.CRITICAL,
            is_active=False,
            is_healthy=False,
            has_description=True,
            has_author=False,
        )

        metadata = model.get_metadata()

        # Verify nested metadata contains enum values as strings
        inner_metadata = metadata["metadata"]
        assert inner_metadata["node_type"] == "module"
        assert inner_metadata["status"] == "pending"
        assert inner_metadata["health"] == "critical"
        assert inner_metadata["node_id"] == str(node_id)
        assert inner_metadata["is_active"] is False
        assert inner_metadata["is_healthy"] is False

    # =========================================================================
    # ModelNodeCore Tests (metadata/node_info category)
    # =========================================================================

    def test_model_node_core_get_metadata_returns_typed_dict(self) -> None:
        """Test ModelNodeCore.get_metadata() returns TypedDictMetadataDict."""
        model = ModelNodeCore(
            node_id=uuid4(),
            node_display_name="core-node",
            description="A test node core",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            status=EnumMetadataNodeStatus.ACTIVE,
            complexity=EnumConceptualComplexity.INTERMEDIATE,
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        metadata = model.get_metadata()

        assert isinstance(metadata, dict)

    def test_model_node_core_get_metadata_name_mapping(self) -> None:
        """Test ModelNodeCore maps node_display_name to name correctly."""
        expected_name = "my-display-name"
        model = ModelNodeCore(
            node_id=uuid4(),
            node_display_name=expected_name,
            description="Test description",
            node_type=EnumNodeType.TRANSFORMER,
            status=EnumMetadataNodeStatus.ACTIVE,
            version=ModelSemVer(major=1, minor=2, patch=3),
        )

        metadata = model.get_metadata()

        assert metadata["name"] == expected_name

    def test_model_node_core_get_metadata_description_mapping(self) -> None:
        """Test ModelNodeCore maps description correctly."""
        expected_description = "This is a detailed description of the node"
        model = ModelNodeCore(
            node_id=uuid4(),
            node_display_name="desc-test",
            description=expected_description,
            node_type=EnumNodeType.AGGREGATOR,
        )

        metadata = model.get_metadata()

        assert metadata["description"] == expected_description

    def test_model_node_core_get_metadata_version_direct(self) -> None:
        """Test ModelNodeCore maps version directly (not node_version)."""
        expected_version = ModelSemVer(major=5, minor=4, patch=3)
        model = ModelNodeCore(
            node_id=uuid4(),
            node_display_name="version-test",
            version=expected_version,
        )

        metadata = model.get_metadata()

        assert metadata["version"] == expected_version
        assert metadata["version"].major == 5
        assert metadata["version"].minor == 4
        assert metadata["version"].patch == 3

    def test_model_node_core_get_metadata_inner_metadata(self) -> None:
        """Test ModelNodeCore includes proper inner metadata with serialized values."""
        node_id = uuid4()
        model = ModelNodeCore(
            node_id=node_id,
            node_display_name="inner-meta-test",
            description="For testing inner metadata",
            node_type=EnumNodeType.GATEWAY,
            status=EnumMetadataNodeStatus.DEPRECATED,
            complexity=EnumConceptualComplexity.ADVANCED,
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        metadata = model.get_metadata()

        inner_metadata = metadata["metadata"]
        assert inner_metadata["node_id"] == str(node_id)
        assert inner_metadata["node_type"] == "GATEWAY"
        assert inner_metadata["status"] == "deprecated"
        assert inner_metadata["complexity"] == "advanced"
        assert inner_metadata["is_active"] is False  # deprecated != active
        assert inner_metadata["is_deprecated"] is True

    def test_model_node_core_get_metadata_no_name_when_none(self) -> None:
        """Test ModelNodeCore does not include name key when node_display_name is None."""
        model = ModelNodeCore(
            node_id=uuid4(),
            node_display_name=None,
            description="No display name",
        )

        metadata = model.get_metadata()

        assert "name" not in metadata

    # =========================================================================
    # ModelInputState Tests (metadata category)
    # =========================================================================

    def test_model_input_state_get_metadata_returns_typed_dict(self) -> None:
        """Test ModelInputState.get_metadata() returns TypedDictMetadataDict."""
        model = ModelInputState(
            version=ModelSemVer(major=1, minor=0, patch=0),
            additional_fields={"key": "value"},
        )

        metadata = model.get_metadata()

        assert isinstance(metadata, dict)

    def test_model_input_state_get_metadata_version_mapping(self) -> None:
        """Test ModelInputState maps version correctly."""
        expected_version = ModelSemVer(major=2, minor=3, patch=4)
        model = ModelInputState(
            version=expected_version,
        )

        metadata = model.get_metadata()

        assert "version" in metadata
        assert metadata["version"] == expected_version
        assert metadata["version"].major == 2
        assert metadata["version"].minor == 3
        assert metadata["version"].patch == 4

    def test_model_input_state_get_metadata_additional_fields_in_metadata(self) -> None:
        """Test ModelInputState includes additional_fields in metadata dict."""
        additional = {"custom_key": "custom_value", "count": 42}
        model = ModelInputState(
            version=ModelSemVer(major=1, minor=0, patch=0),
            additional_fields=additional,
        )

        metadata = model.get_metadata()

        assert "metadata" in metadata
        assert metadata["metadata"]["custom_key"] == "custom_value"
        assert metadata["metadata"]["count"] == 42

    def test_model_input_state_get_metadata_no_version_when_none(self) -> None:
        """Test ModelInputState does not include version key when version is None."""
        model = ModelInputState(
            version=None,
            additional_fields={},
        )

        metadata = model.get_metadata()

        assert "version" not in metadata

    def test_model_input_state_get_metadata_empty_additional_fields(self) -> None:
        """Test ModelInputState with empty additional_fields."""
        model = ModelInputState(
            version=ModelSemVer(major=1, minor=0, patch=0),
            additional_fields={},
        )

        metadata = model.get_metadata()

        # Empty additional_fields should not create metadata key
        assert "metadata" not in metadata or metadata.get("metadata") == {}

    # =========================================================================
    # ModelAnalyticsCore Tests (analytics category)
    # =========================================================================

    def test_model_analytics_core_get_metadata_returns_typed_dict(self) -> None:
        """Test ModelAnalyticsCore.get_metadata() returns TypedDictMetadataDict."""
        model = ModelAnalyticsCore(
            collection_id=uuid4(),
            collection_display_name="analytics-collection",
            total_nodes=100,
            active_nodes=80,
            deprecated_nodes=15,
            disabled_nodes=5,
        )

        metadata = model.get_metadata()

        assert isinstance(metadata, dict)

    def test_model_analytics_core_get_metadata_name_mapping(self) -> None:
        """Test ModelAnalyticsCore maps collection_display_name to name correctly."""
        expected_name = "my-analytics-collection"
        model = ModelAnalyticsCore(
            collection_id=uuid4(),
            collection_display_name=expected_name,
            total_nodes=50,
            active_nodes=40,
        )

        metadata = model.get_metadata()

        assert metadata["name"] == expected_name

    def test_model_analytics_core_get_metadata_inner_metadata(self) -> None:
        """Test ModelAnalyticsCore includes proper analytics data in inner metadata."""
        collection_id = uuid4()
        model = ModelAnalyticsCore(
            collection_id=collection_id,
            collection_display_name="test-collection",
            total_nodes=100,
            active_nodes=75,
            deprecated_nodes=20,
            disabled_nodes=5,
        )

        metadata = model.get_metadata()

        inner_metadata = metadata["metadata"]
        assert inner_metadata["collection_id"] == str(collection_id)
        assert inner_metadata["collection_display_name"] == "test-collection"
        assert inner_metadata["total_nodes"] == 100
        assert inner_metadata["active_nodes"] == 75
        assert inner_metadata["deprecated_nodes"] == 20
        assert inner_metadata["disabled_nodes"] == 5
        assert inner_metadata["active_node_ratio"] == 0.75

    def test_model_analytics_core_get_metadata_no_name_when_none(self) -> None:
        """Test ModelAnalyticsCore does not include name when collection_display_name is None."""
        model = ModelAnalyticsCore(
            collection_id=uuid4(),
            collection_display_name=None,
            total_nodes=10,
        )

        metadata = model.get_metadata()

        assert "name" not in metadata

    def test_model_analytics_core_get_metadata_zero_ratio(self) -> None:
        """Test ModelAnalyticsCore handles zero total_nodes for ratio calculations."""
        model = ModelAnalyticsCore(
            collection_id=uuid4(),
            collection_display_name="empty-collection",
            total_nodes=0,
            active_nodes=0,
        )

        metadata = model.get_metadata()

        inner_metadata = metadata["metadata"]
        # Ratio should be 0.0 when total_nodes is 0
        assert inner_metadata["active_node_ratio"] == 0.0

    # =========================================================================
    # ModelFunctionNode Tests (node_metadata category - composition pattern)
    # =========================================================================

    def test_model_function_node_get_metadata_returns_typed_dict(self) -> None:
        """Test ModelFunctionNode.get_metadata() returns TypedDictMetadataDict."""
        model = ModelFunctionNode.create_simple(
            name="test_function",
            description="A test function",
        )

        metadata = model.get_metadata()

        assert isinstance(metadata, dict)

    def test_model_function_node_get_metadata_name_mapping(self) -> None:
        """Test ModelFunctionNode maps name correctly via delegated property."""
        expected_name = "my_custom_function"
        model = ModelFunctionNode.create_simple(
            name=expected_name,
            description="Custom function",
        )

        metadata = model.get_metadata()

        assert metadata["name"] == expected_name

    def test_model_function_node_get_metadata_description_mapping(self) -> None:
        """Test ModelFunctionNode maps description correctly via delegated property."""
        expected_description = "This function does something important"
        model = ModelFunctionNode.create_simple(
            name="desc_function",
            description=expected_description,
        )

        metadata = model.get_metadata()

        assert metadata["description"] == expected_description

    def test_model_function_node_get_metadata_tags_mapping(self) -> None:
        """Test ModelFunctionNode maps tags correctly."""
        model = ModelFunctionNode.create_simple(
            name="tagged_function",
            description="A tagged function",
        )
        model.add_tag("important")
        model.add_tag("v1")

        metadata = model.get_metadata()

        assert "tags" in metadata
        assert "important" in metadata["tags"]
        assert "v1" in metadata["tags"]

    def test_model_function_node_get_metadata_inner_metadata(self) -> None:
        """Test ModelFunctionNode includes proper data in inner metadata."""
        model = ModelFunctionNode.create_from_signature(
            name="signature_function",
            parameters=["param1", "param2", "param3"],
            description="Function with signature",
        )

        metadata = model.get_metadata()

        inner_metadata = metadata["metadata"]
        assert "function_id" in inner_metadata
        assert inner_metadata["status"] == "active"  # default status
        assert inner_metadata["parameters"] == ["param1", "param2", "param3"]
        assert inner_metadata["parameter_count"] == 3
        assert "is_active" in inner_metadata
        assert "has_documentation" in inner_metadata
        assert "has_examples" in inner_metadata
        assert "has_type_annotations" in inner_metadata

    # =========================================================================
    # ModelFieldIdentity Tests (metadata category - simple field mapping)
    # =========================================================================

    def test_model_field_identity_get_metadata_returns_typed_dict(self) -> None:
        """Test ModelFieldIdentity.get_metadata() returns TypedDictMetadataDict."""
        model = ModelFieldIdentity(
            identity_id=uuid4(),
            identity_display_name="FIELD_NAME",
            field_id=uuid4(),
            field_display_name="field_name",
            description="A test field",
        )

        metadata = model.get_metadata()

        assert isinstance(metadata, dict)

    def test_model_field_identity_get_metadata_name_mapping(self) -> None:
        """Test ModelFieldIdentity maps field_display_name to name correctly."""
        expected_name = "my_field_name"
        model = ModelFieldIdentity(
            identity_id=uuid4(),
            identity_display_name="MY_FIELD_NAME",
            field_id=uuid4(),
            field_display_name=expected_name,
            description="Test field",
        )

        metadata = model.get_metadata()

        assert metadata["name"] == expected_name

    def test_model_field_identity_get_metadata_description_mapping(self) -> None:
        """Test ModelFieldIdentity maps description correctly."""
        expected_description = "This is a detailed field description"
        model = ModelFieldIdentity(
            identity_id=uuid4(),
            identity_display_name="DESCRIBED_FIELD",
            field_id=uuid4(),
            field_display_name="described_field",
            description=expected_description,
        )

        metadata = model.get_metadata()

        assert metadata["description"] == expected_description

    def test_model_field_identity_get_metadata_no_name_when_none(self) -> None:
        """Test ModelFieldIdentity does not include name when field_display_name is None."""
        model = ModelFieldIdentity(
            identity_id=uuid4(),
            identity_display_name="NO_FIELD_NAME",
            field_id=uuid4(),
            field_display_name=None,
            description="Field without display name",
        )

        metadata = model.get_metadata()

        assert "name" not in metadata

    def test_model_field_identity_get_metadata_no_description_when_empty(self) -> None:
        """Test ModelFieldIdentity does not include description when empty."""
        model = ModelFieldIdentity(
            identity_id=uuid4(),
            identity_display_name="EMPTY_DESC",
            field_id=uuid4(),
            field_display_name="empty_desc",
            description="",
        )

        metadata = model.get_metadata()

        # Empty description should not be included
        assert "description" not in metadata


@pytest.mark.unit
class TestGetMetadataTypeConsistency:
    """Tests verifying type consistency across all get_metadata() implementations."""

    def test_all_models_return_dict_compatible(self) -> None:
        """Verify all tested models return dict-compatible structures."""
        models = [
            ModelNodeCoreInfoSummary(
                node_id=uuid4(),
                node_name="test",
                node_type=EnumMetadataNodeType.FUNCTION,
                node_version=ModelSemVer(major=1, minor=0, patch=0),
                status=EnumStatus.ACTIVE,
                health=EnumNodeHealthStatus.HEALTHY,
                is_active=True,
                is_healthy=True,
                has_description=True,
                has_author=True,
            ),
            ModelNodeCore(
                node_id=uuid4(),
                node_display_name="test",
            ),
            ModelInputState(
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelAnalyticsCore(
                collection_id=uuid4(),
                collection_display_name="test",
            ),
            ModelFunctionNode.create_simple(name="test", description="test"),
            ModelFieldIdentity(
                identity_id=uuid4(),
                identity_display_name="TEST",
                field_id=uuid4(),
                field_display_name="test",
                description="test",
            ),
        ]

        for model in models:
            metadata = model.get_metadata()
            assert isinstance(metadata, dict), (
                f"{type(model).__name__}.get_metadata() did not return dict"
            )
            # Verify keys are strings
            for key in metadata:
                assert isinstance(key, str), (
                    f"{type(model).__name__} has non-string key: {key}"
                )

    def test_version_field_is_model_semver_when_present(self) -> None:
        """Verify version field is ModelSemVer when present."""
        models_with_version = [
            ModelNodeCoreInfoSummary(
                node_id=uuid4(),
                node_name="test",
                node_type=EnumMetadataNodeType.FUNCTION,
                node_version=ModelSemVer(major=1, minor=0, patch=0),
                status=EnumStatus.ACTIVE,
                health=EnumNodeHealthStatus.HEALTHY,
                is_active=True,
                is_healthy=True,
                has_description=True,
                has_author=True,
            ),
            ModelNodeCore(
                node_id=uuid4(),
                node_display_name="test",
                version=ModelSemVer(major=2, minor=0, patch=0),
            ),
            ModelInputState(
                version=ModelSemVer(major=3, minor=0, patch=0),
            ),
        ]

        for model in models_with_version:
            metadata = model.get_metadata()
            if "version" in metadata:
                assert isinstance(metadata["version"], ModelSemVer), (
                    f"{type(model).__name__} version is not ModelSemVer"
                )

    def test_metadata_dict_values_are_serializable(self) -> None:
        """Verify inner metadata dict values are serializable (no raw enums)."""
        model = ModelNodeCoreInfoSummary(
            node_id=uuid4(),
            node_name="serialization-test",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            status=EnumStatus.ACTIVE,
            health=EnumNodeHealthStatus.HEALTHY,
            is_active=True,
            is_healthy=True,
            has_description=True,
            has_author=True,
        )

        metadata = model.get_metadata()
        inner_metadata = metadata.get("metadata", {})

        for key, value in inner_metadata.items():
            # Values should be primitive types, not enum instances
            assert not isinstance(value, EnumMetadataNodeType), (
                f"Inner metadata contains raw enum: {key}={value}"
            )
            assert not isinstance(value, EnumStatus), (
                f"Inner metadata contains raw enum: {key}={value}"
            )
            assert not isinstance(value, EnumNodeHealthStatus), (
                f"Inner metadata contains raw enum: {key}={value}"
            )


@pytest.mark.unit
class TestGetMetadataEdgeCases:
    """Tests for edge cases in get_metadata() implementations."""

    def test_model_with_all_optional_fields_none(self) -> None:
        """Test models handle all optional fields being None gracefully."""
        model = ModelNodeCore(
            node_id=uuid4(),
            node_display_name=None,
            description=None,
        )

        metadata = model.get_metadata()

        # Should not raise and should return valid dict
        assert isinstance(metadata, dict)
        # name and description should not be present
        assert "name" not in metadata
        assert "description" not in metadata
        # But version should still be present (has default)
        assert "version" in metadata

    def test_model_with_empty_string_values(self) -> None:
        """Test models handle empty string values correctly."""
        model = ModelFieldIdentity(
            identity_id=uuid4(),
            identity_display_name="EMPTY_TEST",
            field_id=uuid4(),
            field_display_name="",  # Empty string
            description="",  # Empty string
        )

        metadata = model.get_metadata()

        # Empty strings should not create keys (per implementation)
        assert isinstance(metadata, dict)
        # Implementation checks for truthiness, so empty strings are excluded
        assert "name" not in metadata
        assert "description" not in metadata

    def test_model_with_special_characters_in_name(self) -> None:
        """Test models handle special characters in name fields."""
        special_name = "test-node_with.special:chars"
        model = ModelNodeCore(
            node_id=uuid4(),
            node_display_name=special_name,
            description="Node with special chars in name",
        )

        metadata = model.get_metadata()

        assert metadata["name"] == special_name

    def test_model_with_unicode_characters(self) -> None:
        """Test models handle unicode characters correctly."""
        unicode_description = "Description with unicode: \u00e9\u00e8\u00ea \u4e2d\u6587 \u0410\u0411\u0412"
        model = ModelNodeCore(
            node_id=uuid4(),
            node_display_name="unicode-test",
            description=unicode_description,
        )

        metadata = model.get_metadata()

        assert metadata["description"] == unicode_description

    def test_analytics_core_with_large_node_counts(self) -> None:
        """Test ModelAnalyticsCore handles large node counts correctly."""
        model = ModelAnalyticsCore(
            collection_id=uuid4(),
            collection_display_name="large-collection",
            total_nodes=1000000,
            active_nodes=999000,
            deprecated_nodes=900,
            disabled_nodes=100,
        )

        metadata = model.get_metadata()

        inner_metadata = metadata["metadata"]
        assert inner_metadata["total_nodes"] == 1000000
        assert inner_metadata["active_nodes"] == 999000
        # Verify ratio calculation is correct
        assert inner_metadata["active_node_ratio"] == 0.999
