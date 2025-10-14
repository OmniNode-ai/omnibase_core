"""
Unit tests for MixinDiscovery API.

Tests mixin discovery, compatibility checking, dependency resolution,
and validation for autonomous code generation.
"""

from pathlib import Path

import pytest

from omnibase_core.discovery.mixin_discovery import MixinDiscovery
from omnibase_core.discovery.model_mixin_info import ModelMixinInfo
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.primitives.model_semver import ModelSemVer


class TestModelMixinInfo:
    """Tests for ModelMixinInfo model."""

    def test_mixin_info_creation_with_required_fields(self) -> None:
        """Test ModelMixinInfo creation with required fields."""
        mixin = ModelMixinInfo(
            name="MixinTest",
            description="Test mixin",
            version=ModelSemVer(major=1, minor=0, patch=0),
            category="testing",
        )

        assert mixin.name == "MixinTest"
        assert mixin.description == "Test mixin"
        assert mixin.version.major == 1
        assert mixin.version.minor == 0
        assert mixin.version.patch == 0
        assert mixin.category == "testing"
        assert mixin.requires == []
        assert mixin.compatible_with == []
        assert mixin.incompatible_with == []
        assert mixin.config_schema == {}
        assert mixin.usage_examples == []

    def test_mixin_info_creation_with_all_fields(self) -> None:
        """Test ModelMixinInfo creation with all fields."""
        mixin = ModelMixinInfo(
            name="MixinRetry",
            description="Retry logic with exponential backoff",
            version=ModelSemVer(major=1, minor=0, patch=0),
            category="flow_control",
            requires=["omnibase_core.models.infrastructure", "pydantic"],
            compatible_with=["MixinEventBus", "MixinLogging"],
            incompatible_with=["MixinSynchronous"],
            config_schema={
                "max_retries": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "default": 3,
                }
            },
            usage_examples=["HTTP API retries", "Database connection retries"],
        )

        assert mixin.name == "MixinRetry"
        assert len(mixin.requires) == 2
        assert len(mixin.compatible_with) == 2
        assert len(mixin.incompatible_with) == 1
        assert "max_retries" in mixin.config_schema
        assert len(mixin.usage_examples) == 2


class TestMixinDiscovery:
    """Tests for MixinDiscovery class."""

    def test_mixin_discovery_initialization_default_path(self) -> None:
        """Test MixinDiscovery initialization with default path."""
        discovery = MixinDiscovery()

        assert discovery.mixins_path.name == "mixins"
        assert discovery.metadata_path.name == "mixin_metadata.yaml"

    def test_mixin_discovery_initialization_custom_path(self) -> None:
        """Test MixinDiscovery initialization with custom path."""
        custom_path = Path("/custom/mixins")
        discovery = MixinDiscovery(mixins_path=custom_path)

        assert discovery.mixins_path == custom_path
        assert discovery.metadata_path == custom_path / "mixin_metadata.yaml"

    def test_get_all_mixins(self) -> None:
        """Test retrieving all available mixins."""
        discovery = MixinDiscovery()
        mixins = discovery.get_all_mixins()

        assert isinstance(mixins, list)
        assert len(mixins) > 0
        assert all(isinstance(m, ModelMixinInfo) for m in mixins)

        # Check that MixinRetry is present
        retry_mixin = next((m for m in mixins if m.name == "MixinRetry"), None)
        assert retry_mixin is not None
        assert retry_mixin.category == "flow_control"
        assert retry_mixin.version.major == 1
        assert retry_mixin.version.minor == 0
        assert retry_mixin.version.patch == 0

    def test_get_mixins_by_category(self) -> None:
        """Test filtering mixins by category."""
        discovery = MixinDiscovery()

        # Get flow_control mixins
        flow_control_mixins = discovery.get_mixins_by_category("flow_control")

        assert isinstance(flow_control_mixins, list)
        assert all(m.category == "flow_control" for m in flow_control_mixins)

        # Verify MixinRetry is in the list
        retry_found = any(m.name == "MixinRetry" for m in flow_control_mixins)
        assert retry_found

    def test_get_mixins_by_nonexistent_category(self) -> None:
        """Test filtering by nonexistent category returns empty list."""
        discovery = MixinDiscovery()
        mixins = discovery.get_mixins_by_category("nonexistent_category")

        assert isinstance(mixins, list)
        assert len(mixins) == 0

    def test_get_mixin_by_name(self) -> None:
        """Test retrieving a specific mixin by name."""
        discovery = MixinDiscovery()
        retry_mixin = discovery.get_mixin("MixinRetry")

        assert retry_mixin.name == "MixinRetry"
        assert retry_mixin.description
        assert retry_mixin.category == "flow_control"

    def test_get_mixin_nonexistent_name(self) -> None:
        """Test retrieving nonexistent mixin raises error."""
        discovery = MixinDiscovery()

        with pytest.raises(ModelOnexError) as exc_info:
            discovery.get_mixin("NonexistentMixin")

        assert "not found" in str(exc_info.value.message).lower()

    def test_get_categories(self) -> None:
        """Test retrieving all unique categories."""
        discovery = MixinDiscovery()
        categories = discovery.get_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "flow_control" in categories
        assert categories == sorted(categories)  # Should be sorted

    def test_find_compatible_mixins(self) -> None:
        """Test finding mixins compatible with base mixins."""
        discovery = MixinDiscovery()

        # Find mixins compatible with MixinRetry
        compatible = discovery.find_compatible_mixins(["MixinRetry"])

        assert isinstance(compatible, list)

        # Should not include MixinRetry itself
        assert not any(m.name == "MixinRetry" for m in compatible)

        # Should not include any incompatible mixins
        retry_mixin = discovery.get_mixin("MixinRetry")
        for mixin in compatible:
            assert mixin.name not in retry_mixin.incompatible_with

    def test_find_compatible_mixins_with_multiple_base(self) -> None:
        """Test finding compatible mixins with multiple base mixins."""
        discovery = MixinDiscovery()

        # If MixinEventBus exists in metadata, test with it
        all_mixins = discovery.get_all_mixins()
        if len(all_mixins) > 1:
            base_mixins = [all_mixins[0].name]
            compatible = discovery.find_compatible_mixins(base_mixins)

            # Should not include base mixins
            for mixin in compatible:
                assert mixin.name not in base_mixins

    def test_find_compatible_mixins_empty_base(self) -> None:
        """Test finding compatible mixins with empty base returns all."""
        discovery = MixinDiscovery()
        all_mixins = discovery.get_all_mixins()
        compatible = discovery.find_compatible_mixins([])

        # Empty base should return all mixins
        assert len(compatible) == len(all_mixins)

    def test_get_mixin_dependencies(self) -> None:
        """Test retrieving mixin dependencies."""
        discovery = MixinDiscovery()

        deps = discovery.get_mixin_dependencies("MixinRetry")

        assert isinstance(deps, list)
        # MixinRetry has dependencies
        assert len(deps) > 0

        # Check some expected dependencies
        assert any("omnibase_core" in dep for dep in deps)

    def test_get_mixin_dependencies_nonexistent(self) -> None:
        """Test getting dependencies for nonexistent mixin raises error."""
        discovery = MixinDiscovery()

        with pytest.raises(ModelOnexError) as exc_info:
            discovery.get_mixin_dependencies("NonexistentMixin")

        assert "not found" in str(exc_info.value.message).lower()

    def test_validate_composition_valid(self) -> None:
        """Test validating a valid mixin composition."""
        discovery = MixinDiscovery()

        # Single mixin is always valid
        is_valid, errors = discovery.validate_composition(["MixinRetry"])

        assert is_valid
        assert len(errors) == 0

    def test_validate_composition_with_unknown_mixin(self) -> None:
        """Test validating composition with unknown mixin."""
        discovery = MixinDiscovery()

        is_valid, errors = discovery.validate_composition(
            ["MixinRetry", "UnknownMixin"]
        )

        assert not is_valid
        assert len(errors) > 0
        assert any("unknown" in err.lower() for err in errors)

    def test_validate_composition_empty_list(self) -> None:
        """Test validating empty composition."""
        discovery = MixinDiscovery()

        is_valid, errors = discovery.validate_composition([])

        assert is_valid
        assert len(errors) == 0

    def test_caching_behavior(self) -> None:
        """Test that mixin data is cached after first load."""
        discovery = MixinDiscovery()

        # First call loads data
        mixins1 = discovery.get_all_mixins()

        # Second call should use cache
        mixins2 = discovery.get_all_mixins()

        assert mixins1 == mixins2
        assert discovery._mixins_cache is not None

    def test_metadata_file_not_found(self) -> None:
        """Test error handling when metadata file doesn't exist."""
        # Use a path that definitely doesn't exist
        nonexistent_path = Path("/nonexistent/path/to/mixins")
        discovery = MixinDiscovery(mixins_path=nonexistent_path)

        with pytest.raises(ModelOnexError) as exc_info:
            discovery.get_all_mixins()

        assert "not found" in str(exc_info.value.message).lower()


class TestMixinDiscoveryIntegration:
    """Integration tests for MixinDiscovery workflows."""

    def test_complete_discovery_workflow(self) -> None:
        """Test complete workflow from discovery to composition validation."""
        discovery = MixinDiscovery()

        # 1. Discover all mixins
        all_mixins = discovery.get_all_mixins()
        assert len(all_mixins) > 0

        # 2. Get categories
        categories = discovery.get_categories()
        assert len(categories) > 0

        # 3. Get mixins by category
        for category in categories:
            category_mixins = discovery.get_mixins_by_category(category)
            assert len(category_mixins) > 0

        # 4. Check compatibility
        if len(all_mixins) > 0:
            base_mixin = all_mixins[0]
            compatible = discovery.find_compatible_mixins([base_mixin.name])
            assert isinstance(compatible, list)

        # 5. Validate composition
        if len(all_mixins) > 0:
            composition = [all_mixins[0].name]
            is_valid, errors = discovery.validate_composition(composition)
            assert is_valid

    def test_mixin_recommendation_workflow(self) -> None:
        """Test workflow for recommending mixins based on requirements."""
        discovery = MixinDiscovery()

        # Get a base mixin
        all_mixins = discovery.get_all_mixins()
        if len(all_mixins) == 0:
            pytest.skip("No mixins available for testing")

        base_mixin = all_mixins[0]

        # Find compatible mixins
        compatible = discovery.find_compatible_mixins([base_mixin.name])

        # Build a composition
        composition = [base_mixin.name]

        # Add compatible mixins one by one, validating each step
        for mixin in compatible[:3]:  # Take up to 3 compatible mixins
            test_composition = composition + [mixin.name]
            is_valid, errors = discovery.validate_composition(test_composition)

            if is_valid:
                composition.append(mixin.name)

        # Final composition should be valid
        is_valid, errors = discovery.validate_composition(composition)
        assert is_valid
        assert len(errors) == 0

    def test_dependency_resolution_workflow(self) -> None:
        """Test workflow for resolving all dependencies."""
        discovery = MixinDiscovery()

        # Get all mixins and their dependencies
        all_mixins = discovery.get_all_mixins()

        dependency_map = {}
        for mixin in all_mixins:
            try:
                deps = discovery.get_mixin_dependencies(mixin.name)
                dependency_map[mixin.name] = deps
            except ModelOnexError:
                # Some mixins might not have dependencies
                dependency_map[mixin.name] = []

        # Verify we got dependencies for all mixins
        assert len(dependency_map) == len(all_mixins)
