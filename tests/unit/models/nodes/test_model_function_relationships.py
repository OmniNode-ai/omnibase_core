"""
Unit tests for ModelFunctionRelationships.

Tests all aspects of the function relationships model including:
- Model instantiation and validation
- Dependencies and related functions management
- Tags and categories handling
- Summary generation
- Factory methods
- Protocol implementations
"""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_category import EnumCategory
from omnibase_core.models.nodes.model_function_relationships import (
    ModelFunctionRelationships,
)


class TestModelFunctionRelationships:
    """Test cases for ModelFunctionRelationships."""

    def test_model_instantiation_default(self):
        """Test that model can be instantiated with defaults."""
        rel = ModelFunctionRelationships()

        assert rel.dependencies == []
        assert rel.related_functions == []
        assert rel.tags == []
        assert rel.categories == []

    def test_model_instantiation_with_data(self):
        """Test model instantiation with data."""
        dep1 = uuid4()
        dep2 = uuid4()
        func1 = uuid4()

        rel = ModelFunctionRelationships(
            dependencies=[dep1, dep2],
            related_functions=[func1],
            tags=["tag1", "tag2"],
            categories=[EnumCategory.CORE, EnumCategory.AUXILIARY],
        )

        assert rel.dependencies == [dep1, dep2]
        assert rel.related_functions == [func1]
        assert rel.tags == ["tag1", "tag2"]
        assert rel.categories == [EnumCategory.CORE, EnumCategory.AUXILIARY]

    def test_add_dependency(self):
        """Test add_dependency method."""
        rel = ModelFunctionRelationships()
        dep = uuid4()

        rel.add_dependency(dep)
        assert dep in rel.dependencies
        assert len(rel.dependencies) == 1

    def test_add_dependency_no_duplicate(self):
        """Test add_dependency doesn't add duplicates."""
        dep = uuid4()
        rel = ModelFunctionRelationships(dependencies=[dep])

        rel.add_dependency(dep)
        assert rel.dependencies.count(dep) == 1

    def test_add_multiple_dependencies(self):
        """Test adding multiple dependencies."""
        rel = ModelFunctionRelationships()
        dep1 = uuid4()
        dep2 = uuid4()
        dep3 = uuid4()

        rel.add_dependency(dep1)
        rel.add_dependency(dep2)
        rel.add_dependency(dep3)

        assert len(rel.dependencies) == 3

    def test_add_related_function(self):
        """Test add_related_function method."""
        rel = ModelFunctionRelationships()
        func = uuid4()

        rel.add_related_function(func)
        assert func in rel.related_functions
        assert len(rel.related_functions) == 1

    def test_add_related_function_no_duplicate(self):
        """Test add_related_function doesn't add duplicates."""
        func = uuid4()
        rel = ModelFunctionRelationships(related_functions=[func])

        rel.add_related_function(func)
        assert rel.related_functions.count(func) == 1

    def test_add_multiple_related_functions(self):
        """Test adding multiple related functions."""
        rel = ModelFunctionRelationships()
        func1 = uuid4()
        func2 = uuid4()

        rel.add_related_function(func1)
        rel.add_related_function(func2)

        assert len(rel.related_functions) == 2

    def test_add_tag(self):
        """Test add_tag method."""
        rel = ModelFunctionRelationships()

        rel.add_tag("tag1")
        assert "tag1" in rel.tags
        assert len(rel.tags) == 1

    def test_add_tag_no_duplicate(self):
        """Test add_tag doesn't add duplicates."""
        rel = ModelFunctionRelationships(tags=["tag1"])

        rel.add_tag("tag1")
        assert rel.tags.count("tag1") == 1

    def test_add_multiple_tags(self):
        """Test adding multiple tags."""
        rel = ModelFunctionRelationships()

        rel.add_tag("tag1")
        rel.add_tag("tag2")
        rel.add_tag("tag3")

        assert len(rel.tags) == 3

    def test_remove_tag(self):
        """Test remove_tag method."""
        rel = ModelFunctionRelationships(tags=["tag1", "tag2"])

        rel.remove_tag("tag1")
        assert "tag1" not in rel.tags
        assert "tag2" in rel.tags

    def test_remove_tag_not_present(self):
        """Test remove_tag when tag not present doesn't raise error."""
        rel = ModelFunctionRelationships(tags=["tag1"])

        # Should not raise error
        rel.remove_tag("tag2")
        assert "tag1" in rel.tags

    def test_add_category(self):
        """Test add_category method."""
        rel = ModelFunctionRelationships()

        rel.add_category(EnumCategory.CORE)
        assert EnumCategory.CORE in rel.categories
        assert len(rel.categories) == 1

    def test_add_category_no_duplicate(self):
        """Test add_category doesn't add duplicates."""
        rel = ModelFunctionRelationships(categories=[EnumCategory.CORE])

        rel.add_category(EnumCategory.CORE)
        assert rel.categories.count(EnumCategory.CORE) == 1

    def test_add_multiple_categories(self):
        """Test adding multiple categories."""
        rel = ModelFunctionRelationships()

        rel.add_category(EnumCategory.CORE)
        rel.add_category(EnumCategory.AUXILIARY)
        rel.add_category(EnumCategory.SECONDARY)

        assert len(rel.categories) == 3

    def test_has_dependencies_true(self):
        """Test has_dependencies returns True when dependencies exist."""
        dep = uuid4()
        rel = ModelFunctionRelationships(dependencies=[dep])

        assert rel.has_dependencies() is True

    def test_has_dependencies_false(self):
        """Test has_dependencies returns False when no dependencies."""
        rel = ModelFunctionRelationships()

        assert rel.has_dependencies() is False

    def test_has_related_functions_true(self):
        """Test has_related_functions returns True when functions exist."""
        func = uuid4()
        rel = ModelFunctionRelationships(related_functions=[func])

        assert rel.has_related_functions() is True

    def test_has_related_functions_false(self):
        """Test has_related_functions returns False when no functions."""
        rel = ModelFunctionRelationships()

        assert rel.has_related_functions() is False

    def test_has_tags_true(self):
        """Test has_tags returns True when tags exist."""
        rel = ModelFunctionRelationships(tags=["tag1"])

        assert rel.has_tags() is True

    def test_has_tags_false(self):
        """Test has_tags returns False when no tags."""
        rel = ModelFunctionRelationships()

        assert rel.has_tags() is False

    def test_has_categories_true(self):
        """Test has_categories returns True when categories exist."""
        rel = ModelFunctionRelationships(categories=[EnumCategory.CORE])

        assert rel.has_categories() is True

    def test_has_categories_false(self):
        """Test has_categories returns False when no categories."""
        rel = ModelFunctionRelationships()

        assert rel.has_categories() is False

    def test_get_relationships_summary(self):
        """Test get_relationships_summary method."""
        dep = uuid4()
        func = uuid4()
        rel = ModelFunctionRelationships(
            dependencies=[dep],
            related_functions=[func],
            tags=["tag1", "tag2"],
            categories=[EnumCategory.CORE, EnumCategory.AUXILIARY],
        )

        summary = rel.get_relationships_summary()

        assert summary["dependencies_count"] == 1
        assert summary["related_functions_count"] == 1
        assert summary["tags_count"] == 2
        assert summary["categories_count"] == 2
        assert summary["has_dependencies"] is True
        assert summary["has_related_functions"] is True
        assert summary["has_tags"] is True
        assert summary["has_categories"] is True
        assert summary["primary_category"] == "core"

    def test_get_relationships_summary_empty(self):
        """Test get_relationships_summary with empty data."""
        rel = ModelFunctionRelationships()

        summary = rel.get_relationships_summary()

        assert summary["dependencies_count"] == 0
        assert summary["related_functions_count"] == 0
        assert summary["tags_count"] == 0
        assert summary["categories_count"] == 0
        assert summary["has_dependencies"] is False
        assert summary["has_related_functions"] is False
        assert summary["has_tags"] is False
        assert summary["has_categories"] is False
        assert summary["primary_category"] == "None"

    def test_create_tagged_factory(self):
        """Test create_tagged factory method."""
        rel = ModelFunctionRelationships.create_tagged(
            tags=["tag1", "tag2"],
            categories=[EnumCategory.CORE],
        )

        assert rel.tags == ["tag1", "tag2"]
        assert rel.categories == [EnumCategory.CORE]

    def test_create_tagged_factory_no_categories(self):
        """Test create_tagged without categories."""
        rel = ModelFunctionRelationships.create_tagged(
            tags=["tag1"],
        )

        assert rel.tags == ["tag1"]
        assert rel.categories == []

    def test_create_with_dependencies_factory(self):
        """Test create_with_dependencies factory method."""
        dep1 = uuid4()
        dep2 = uuid4()
        func1 = uuid4()

        rel = ModelFunctionRelationships.create_with_dependencies(
            dependencies=[dep1, dep2],
            related_functions=[func1],
        )

        assert rel.dependencies == [dep1, dep2]
        assert rel.related_functions == [func1]

    def test_create_with_dependencies_factory_no_related(self):
        """Test create_with_dependencies without related functions."""
        dep = uuid4()

        rel = ModelFunctionRelationships.create_with_dependencies(
            dependencies=[dep],
        )

        assert rel.dependencies == [dep]
        assert rel.related_functions == []

    def test_get_id_protocol(self):
        """Test get_id protocol method raises OnexError without ID field."""
        from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError

        rel = ModelFunctionRelationships()

        with pytest.raises(OnexError) as exc_info:
            rel.get_id()

        assert "must have a valid ID field" in str(exc_info.value)

    def test_get_metadata_protocol(self):
        """Test get_metadata protocol method."""
        rel = ModelFunctionRelationships()

        metadata = rel.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata_protocol(self):
        """Test set_metadata protocol method."""
        rel = ModelFunctionRelationships()

        result = rel.set_metadata({"tags": ["new_tag"]})
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        rel = ModelFunctionRelationships(tags=["tag1"])

        serialized = rel.serialize()
        assert isinstance(serialized, dict)
        assert "tags" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        rel = ModelFunctionRelationships()

        assert rel.validate_instance() is True

    def test_model_config_extra_ignore(self):
        """Test that model ignores extra fields."""
        # Should not raise error with extra fields
        rel = ModelFunctionRelationships(
            tags=["tag1"],
            extra_field="ignored",
        )
        assert rel.tags == ["tag1"]

    def test_model_config_validate_assignment(self):
        """Test that model validates on assignment."""
        rel = ModelFunctionRelationships()

        # Should validate new assignments
        rel.tags = ["new_tag"]
        assert rel.tags == ["new_tag"]

    def test_dependencies_list_mutation(self):
        """Test that dependencies list can be modified."""
        rel = ModelFunctionRelationships()
        dep = uuid4()

        rel.dependencies.append(dep)
        assert dep in rel.dependencies

    def test_categories_with_different_enum_values(self):
        """Test multiple different category enum values."""
        rel = ModelFunctionRelationships()

        rel.add_category(EnumCategory.CORE)
        rel.add_category(EnumCategory.AUXILIARY)
        rel.add_category(EnumCategory.AUXILIARY)  # Duplicate will be ignored
        rel.add_category(EnumCategory.SECONDARY)

        # Only 3 unique categories (duplicate AUXILIARY is removed)
        assert len(rel.categories) == 3
        assert EnumCategory.CORE in rel.categories
        assert EnumCategory.AUXILIARY in rel.categories
