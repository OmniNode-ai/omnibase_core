"""Comprehensive tests for ModelMixinMetadata and related models.

Tests cover:
- Version parsing and validation
- Config field validation
- Code pattern models
- Main metadata model
- YAML loading and parsing
- Helper methods and queries
- Compatibility validation
"""

from pathlib import Path

import pytest

from omnibase_core.models.core.model_mixin_metadata import (
    ModelMixinCodePatterns,
    ModelMixinConfigField,
    ModelMixinMetadata,
    ModelMixinMetadataCollection,
    ModelMixinMethod,
    ModelMixinPerformance,
    ModelMixinPerformanceUseCase,
    ModelMixinPreset,
    ModelMixinProperty,
    ModelMixinVersion,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


# =============================================================================
# ModelMixinVersion Tests
# =============================================================================


class TestModelMixinVersion:
    """Test ModelMixinVersion parsing and formatting."""

    def test_version_creation(self) -> None:
        """Test creating version from components."""
        version = ModelMixinVersion(major=1, minor=2, patch=3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert str(version) == "1.2.3"

    def test_version_from_string_valid(self) -> None:
        """Test parsing valid version string."""
        version = ModelMixinVersion.from_string("2.5.7")
        assert version.major == 2
        assert version.minor == 5
        assert version.patch == 7

    def test_version_from_string_invalid_format(self) -> None:
        """Test parsing invalid version string raises error."""
        with pytest.raises(ModelOnexError, match="Invalid version string"):
            ModelMixinVersion.from_string("1.2")

    def test_version_from_string_non_numeric(self) -> None:
        """Test parsing non-numeric version raises error."""
        with pytest.raises(ModelOnexError, match="Invalid version string"):
            ModelMixinVersion.from_string("1.2.x")

    def test_version_negative_numbers(self) -> None:
        """Test negative version numbers are rejected."""
        with pytest.raises(ValueError):
            ModelMixinVersion(major=-1, minor=0, patch=0)

    def test_version_zero_valid(self) -> None:
        """Test zero versions are valid."""
        version = ModelMixinVersion(major=0, minor=0, patch=0)
        assert str(version) == "0.0.0"


# =============================================================================
# ModelMixinConfigField Tests
# =============================================================================


class TestModelMixinConfigField:
    """Test ModelMixinConfigField validation."""

    def test_config_field_basic(self) -> None:
        """Test creating basic config field."""
        field = ModelMixinConfigField(
            type="string", default="value", description="A string field"
        )
        assert field.type == "string"
        assert field.default == "value"
        assert field.description == "A string field"

    def test_config_field_numeric_with_bounds(self) -> None:
        """Test numeric field with min/max bounds."""
        field = ModelMixinConfigField(
            type="integer",
            default=5,
            minimum=0,
            maximum=10,
            description="Count field",
        )
        assert field.minimum == 0
        assert field.maximum == 10

    def test_config_field_enum(self) -> None:
        """Test enum field with allowed values."""
        field = ModelMixinConfigField(
            type="string",
            enum=["option1", "option2", "option3"],
            default="option1",
            description="Choice field",
        )
        assert field.enum == ["option1", "option2", "option3"]

    def test_config_field_array_with_items(self) -> None:
        """Test array field with item schema."""
        field = ModelMixinConfigField(
            type="array",
            items={"type": "string"},
            default=[],
            description="String array",
        )
        assert field.items == {"type": "string"}

    def test_config_field_invalid_type(self) -> None:
        """Test invalid field type raises error."""
        with pytest.raises(ValueError, match="Invalid field type"):
            ModelMixinConfigField(type="invalid_type", description="Bad field")


# =============================================================================
# Code Pattern Model Tests
# =============================================================================


class TestModelMixinMethod:
    """Test ModelMixinMethod model."""

    def test_method_creation(self) -> None:
        """Test creating method definition."""
        method = ModelMixinMethod(
            name="my_method",
            signature="async def my_method(self, arg: str) -> bool",
            description="Does something",
            example="result = await obj.my_method('test')",
        )
        assert method.name == "my_method"
        assert "async def" in method.signature
        assert method.description == "Does something"
        assert method.example != ""


class TestModelMixinProperty:
    """Test ModelMixinProperty model."""

    def test_property_creation(self) -> None:
        """Test creating property definition."""
        prop = ModelMixinProperty(
            name="is_ready", type="bool", description="Ready state"
        )
        assert prop.name == "is_ready"
        assert prop.type == "bool"
        assert prop.description == "Ready state"


class TestModelMixinCodePatterns:
    """Test ModelMixinCodePatterns model."""

    def test_code_patterns_full(self) -> None:
        """Test code patterns with all fields."""
        patterns = ModelMixinCodePatterns(
            inheritance="class Node(Base, Mixin):",
            initialization="self._state = initial",
            methods=[
                ModelMixinMethod(
                    name="process", signature="def process(self)", description="Process"
                )
            ],
            properties=[
                ModelMixinProperty(name="state", type="str", description="State")
            ],
        )
        assert "class Node" in patterns.inheritance
        assert len(patterns.methods) == 1
        assert len(patterns.properties) == 1

    def test_code_patterns_empty(self) -> None:
        """Test code patterns with defaults."""
        patterns = ModelMixinCodePatterns()
        assert patterns.inheritance == ""
        assert patterns.methods == []
        assert patterns.properties == []


# =============================================================================
# Preset and Performance Tests
# =============================================================================


class TestModelMixinPreset:
    """Test ModelMixinPreset model."""

    def test_preset_creation(self) -> None:
        """Test creating preset configuration."""
        preset = ModelMixinPreset(
            description="Quick retry", config={"max_retries": 3, "delay": 1.0}
        )
        assert preset.description == "Quick retry"
        assert preset.config["max_retries"] == 3


class TestModelMixinPerformance:
    """Test ModelMixinPerformance model."""

    def test_performance_full(self) -> None:
        """Test performance with all fields."""
        perf = ModelMixinPerformance(
            overhead_per_call="~1ms",
            memory_per_instance="~5KB",
            recommended_max_retries=10,
            typical_use_cases=[
                ModelMixinPerformanceUseCase(
                    use_case="HTTP calls",
                    recommended_config="http",
                    expected_overhead="~2ms",
                )
            ],
        )
        assert perf.overhead_per_call == "~1ms"
        assert len(perf.typical_use_cases) == 1
        assert perf.typical_use_cases[0].use_case == "HTTP calls"


# =============================================================================
# ModelMixinMetadata Tests
# =============================================================================


class TestModelMixinMetadata:
    """Test main ModelMixinMetadata model."""

    def test_metadata_minimal(self) -> None:
        """Test creating minimal metadata."""
        metadata = ModelMixinMetadata(
            name="MixinTest",
            description="Test mixin",
            version=ModelMixinVersion(major=1, minor=0, patch=0),
            category="utility",
        )
        assert metadata.name == "MixinTest"
        assert metadata.category == "utility"
        assert str(metadata.version) == "1.0.0"

    def test_metadata_with_dependencies(self) -> None:
        """Test metadata with requires and compatibility."""
        metadata = ModelMixinMetadata(
            name="MixinTest",
            description="Test",
            version=ModelMixinVersion(major=1, minor=0, patch=0),
            category="flow_control",
            requires=["pydantic", "asyncio"],
            compatible_with=["MixinA", "MixinB"],
            incompatible_with=["MixinC"],
        )
        assert len(metadata.requires) == 2
        assert "MixinA" in metadata.compatible_with
        assert "MixinC" in metadata.incompatible_with

    def test_metadata_with_config_schema(self) -> None:
        """Test metadata with configuration schema."""
        metadata = ModelMixinMetadata(
            name="MixinTest",
            description="Test",
            version=ModelMixinVersion(major=1, minor=0, patch=0),
            category="utility",
            config_schema={
                "max_retries": ModelMixinConfigField(
                    type="integer", default=3, minimum=0, maximum=10
                ),
                "enabled": ModelMixinConfigField(type="boolean", default=True),
            },
        )
        assert "max_retries" in metadata.config_schema
        assert metadata.config_schema["max_retries"].default == 3
        assert metadata.config_schema["enabled"].type == "boolean"

    def test_metadata_category_validation(self) -> None:
        """Test category validation accepts known and unknown categories."""
        # Known category
        metadata = ModelMixinMetadata(
            name="Test",
            description="Test",
            version=ModelMixinVersion(major=1, minor=0, patch=0),
            category="flow_control",
        )
        assert metadata.category == "flow_control"

        # Unknown category - should still accept but could warn
        metadata = ModelMixinMetadata(
            name="Test",
            description="Test",
            version=ModelMixinVersion(major=1, minor=0, patch=0),
            category="custom_category",
        )
        assert metadata.category == "custom_category"

    def test_metadata_compatibility_conflict(self) -> None:
        """Test conflicting compatibility raises error."""
        with pytest.raises(
            ValueError, match="conflicting compatibility"
        ):
            ModelMixinMetadata(
                name="Test",
                description="Test",
                version=ModelMixinVersion(major=1, minor=0, patch=0),
                category="utility",
                compatible_with=["MixinA"],
                incompatible_with=["MixinA"],  # Conflict!
            )

    def test_metadata_with_presets(self) -> None:
        """Test metadata with preset configurations."""
        metadata = ModelMixinMetadata(
            name="Test",
            description="Test",
            version=ModelMixinVersion(major=1, minor=0, patch=0),
            category="utility",
            presets={
                "simple": ModelMixinPreset(
                    description="Simple config", config={"enabled": True}
                ),
                "advanced": ModelMixinPreset(
                    description="Advanced config", config={"enabled": True, "debug": True}
                ),
            },
        )
        assert "simple" in metadata.presets
        assert "advanced" in metadata.presets


# =============================================================================
# ModelMixinMetadataCollection Tests
# =============================================================================


class TestModelMixinMetadataCollection:
    """Test ModelMixinMetadataCollection functionality."""

    def test_collection_creation(self) -> None:
        """Test creating empty collection."""
        collection = ModelMixinMetadataCollection()
        assert collection.get_mixin_count() == 0

    def test_collection_add_mixins(self) -> None:
        """Test adding mixins to collection."""
        collection = ModelMixinMetadataCollection(
            mixins={
                "mixin_a": ModelMixinMetadata(
                    name="MixinA",
                    description="A",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                ),
                "mixin_b": ModelMixinMetadata(
                    name="MixinB",
                    description="B",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="flow_control",
                ),
            }
        )
        assert collection.get_mixin_count() == 2

    def test_get_mixin_by_key(self) -> None:
        """Test getting mixin by key."""
        collection = ModelMixinMetadataCollection(
            mixins={
                "mixin_test": ModelMixinMetadata(
                    name="MixinTest",
                    description="Test",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                )
            }
        )
        mixin = collection.get_mixin("mixin_test")
        assert mixin is not None
        assert mixin.name == "MixinTest"

    def test_get_mixin_by_class_name(self) -> None:
        """Test getting mixin by class name."""
        collection = ModelMixinMetadataCollection(
            mixins={
                "mixin_test": ModelMixinMetadata(
                    name="MixinTest",
                    description="Test",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                )
            }
        )
        mixin = collection.get_mixin("MixinTest")
        assert mixin is not None
        assert mixin.name == "MixinTest"

    def test_get_mixin_not_found(self) -> None:
        """Test getting non-existent mixin returns None."""
        collection = ModelMixinMetadataCollection()
        mixin = collection.get_mixin("NonExistent")
        assert mixin is None

    def test_get_mixins_by_category(self) -> None:
        """Test getting mixins by category."""
        collection = ModelMixinMetadataCollection(
            mixins={
                "mixin_a": ModelMixinMetadata(
                    name="MixinA",
                    description="A",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                ),
                "mixin_b": ModelMixinMetadata(
                    name="MixinB",
                    description="B",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                ),
                "mixin_c": ModelMixinMetadata(
                    name="MixinC",
                    description="C",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="flow_control",
                ),
            }
        )
        utility_mixins = collection.get_mixins_by_category("utility")
        assert len(utility_mixins) == 2
        assert all(m.category == "utility" for m in utility_mixins)

    def test_validate_compatibility_success(self) -> None:
        """Test validating compatible mixins."""
        collection = ModelMixinMetadataCollection(
            mixins={
                "mixin_a": ModelMixinMetadata(
                    name="MixinA",
                    description="A",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                    compatible_with=["MixinB"],
                ),
                "mixin_b": ModelMixinMetadata(
                    name="MixinB",
                    description="B",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                    compatible_with=["MixinA"],
                ),
            }
        )
        is_compatible, conflicts = collection.validate_compatibility(
            ["MixinA", "MixinB"]
        )
        assert is_compatible
        assert len(conflicts) == 0

    def test_validate_compatibility_conflict(self) -> None:
        """Test validating incompatible mixins."""
        collection = ModelMixinMetadataCollection(
            mixins={
                "mixin_a": ModelMixinMetadata(
                    name="MixinA",
                    description="A",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                    incompatible_with=["MixinB"],
                ),
                "mixin_b": ModelMixinMetadata(
                    name="MixinB",
                    description="B",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                ),
            }
        )
        is_compatible, conflicts = collection.validate_compatibility(
            ["MixinA", "MixinB"]
        )
        assert not is_compatible
        assert len(conflicts) == 1
        assert "Incompatible" in conflicts[0]

    def test_validate_compatibility_unknown_mixin(self) -> None:
        """Test validating with unknown mixin."""
        collection = ModelMixinMetadataCollection()
        is_compatible, conflicts = collection.validate_compatibility(
            ["UnknownMixin"]
        )
        assert not is_compatible
        assert len(conflicts) == 1
        assert "Unknown mixin" in conflicts[0]

    def test_get_all_categories(self) -> None:
        """Test getting all unique categories."""
        collection = ModelMixinMetadataCollection(
            mixins={
                "mixin_a": ModelMixinMetadata(
                    name="MixinA",
                    description="A",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                ),
                "mixin_b": ModelMixinMetadata(
                    name="MixinB",
                    description="B",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="flow_control",
                ),
                "mixin_c": ModelMixinMetadata(
                    name="MixinC",
                    description="C",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility",
                ),
            }
        )
        categories = collection.get_all_categories()
        assert len(categories) == 2
        assert "utility" in categories
        assert "flow_control" in categories
        assert categories == sorted(categories)  # Should be sorted


# =============================================================================
# YAML Loading Tests
# =============================================================================


class TestYAMLLoading:
    """Test loading from actual mixin_metadata.yaml file."""

    def test_load_actual_yaml_file(self) -> None:
        """Test loading the actual mixin_metadata.yaml file."""
        # Find the actual file
        yaml_path = (
            Path(__file__).parents[4]
            / "src"
            / "omnibase_core"
            / "mixins"
            / "mixin_metadata.yaml"
        )

        # Skip if file doesn't exist (for isolated test environments)
        if not yaml_path.exists():
            pytest.skip(f"mixin_metadata.yaml not found at {yaml_path}")

        collection = ModelMixinMetadataCollection.load_from_yaml(yaml_path)

        # Basic validation
        assert collection.get_mixin_count() > 0
        assert len(collection.get_all_categories()) > 0

        # Test specific mixin if it exists
        retry_mixin = collection.get_mixin("mixin_retry")
        if retry_mixin:
            assert retry_mixin.name == "MixinRetry"
            assert retry_mixin.category == "flow_control"
            assert len(retry_mixin.requires) > 0

    def test_load_nonexistent_file(self) -> None:
        """Test loading non-existent file raises error."""
        with pytest.raises(ModelOnexError, match="not found"):
            ModelMixinMetadataCollection.load_from_yaml("/nonexistent/path.yaml")

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        """Test loading invalid YAML raises error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("{ invalid yaml content [")

        with pytest.raises(ModelOnexError, match="Failed to load YAML"):
            ModelMixinMetadataCollection.load_from_yaml(yaml_file)

    def test_load_non_dict_yaml(self, tmp_path: Path) -> None:
        """Test loading non-dict YAML raises error."""
        yaml_file = tmp_path / "list.yaml"
        yaml_file.write_text("- item1\n- item2\n")

        with pytest.raises(ModelOnexError, match="Expected dict"):
            ModelMixinMetadataCollection.load_from_yaml(yaml_file)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow: create → save → load → query."""
        # Create test metadata
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: {major: 1, minor: 0, patch: 0}
  category: "utility"
  requires:
    - "pydantic"
  compatible_with:
    - "MixinA"
  config_schema:
    enabled:
      type: "boolean"
      default: true
      description: "Enable feature"
  presets:
    simple:
      description: "Simple preset"
      config:
        enabled: true
"""
        yaml_file = tmp_path / "test_mixins.yaml"
        yaml_file.write_text(yaml_content)

        # Load
        collection = ModelMixinMetadataCollection.load_from_yaml(yaml_file)

        # Query
        assert collection.get_mixin_count() == 1
        mixin = collection.get_mixin("mixin_test")
        assert mixin is not None
        assert mixin.name == "MixinTest"
        assert "enabled" in mixin.config_schema
        assert "simple" in mixin.presets

    def test_multi_category_query(self) -> None:
        """Test querying across multiple categories."""
        collection = ModelMixinMetadataCollection(
            mixins={
                f"mixin_{i}": ModelMixinMetadata(
                    name=f"Mixin{i}",
                    description=f"Mixin {i}",
                    version=ModelMixinVersion(major=1, minor=0, patch=0),
                    category="utility" if i % 2 == 0 else "flow_control",
                )
                for i in range(10)
            }
        )

        utility = collection.get_mixins_by_category("utility")
        flow = collection.get_mixins_by_category("flow_control")

        assert len(utility) == 5
        assert len(flow) == 5
        assert len(utility) + len(flow) == collection.get_mixin_count()
