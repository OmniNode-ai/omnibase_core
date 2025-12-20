"""
Unit tests for EnumConfigCategory.

Tests all aspects of the configuration category enum including:
- Enum value validation
- Helper methods and class methods
- String representation
- JSON serialization compatibility
- Pydantic integration
- Category classification logic
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_config_category import EnumConfigCategory


@pytest.mark.unit
class TestEnumConfigCategory:
    """Test cases for EnumConfigCategory."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        # Core system categories
        assert EnumConfigCategory.GENERATION.value == "generation"
        assert EnumConfigCategory.VALIDATION.value == "validation"
        assert EnumConfigCategory.TEMPLATE.value == "template"
        assert EnumConfigCategory.MAINTENANCE.value == "maintenance"
        assert EnumConfigCategory.RUNTIME.value == "runtime"

        # Infrastructure categories
        assert EnumConfigCategory.CLI.value == "cli"
        assert EnumConfigCategory.DISCOVERY.value == "discovery"
        assert EnumConfigCategory.SCHEMA.value == "schema"
        assert EnumConfigCategory.LOGGING.value == "logging"
        assert EnumConfigCategory.TESTING.value == "testing"

        # Generic categories
        assert EnumConfigCategory.GENERAL.value == "general"
        assert EnumConfigCategory.UNKNOWN.value == "unknown"

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumConfigCategory.GENERATION) == "generation"
        assert str(EnumConfigCategory.VALIDATION) == "validation"
        assert str(EnumConfigCategory.CLI) == "cli"
        assert str(EnumConfigCategory.GENERAL) == "general"

    def test_get_system_categories(self):
        """Test get_system_categories class method."""
        system_categories = EnumConfigCategory.get_system_categories()

        # Should return all core system categories
        assert len(system_categories) == 5
        assert EnumConfigCategory.GENERATION in system_categories
        assert EnumConfigCategory.VALIDATION in system_categories
        assert EnumConfigCategory.TEMPLATE in system_categories
        assert EnumConfigCategory.MAINTENANCE in system_categories
        assert EnumConfigCategory.RUNTIME in system_categories

        # Should not include infrastructure categories
        assert EnumConfigCategory.CLI not in system_categories
        assert EnumConfigCategory.DISCOVERY not in system_categories
        assert EnumConfigCategory.GENERAL not in system_categories

    def test_get_infrastructure_categories(self):
        """Test get_infrastructure_categories class method."""
        infra_categories = EnumConfigCategory.get_infrastructure_categories()

        # Should return all infrastructure categories
        assert len(infra_categories) == 5
        assert EnumConfigCategory.CLI in infra_categories
        assert EnumConfigCategory.DISCOVERY in infra_categories
        assert EnumConfigCategory.SCHEMA in infra_categories
        assert EnumConfigCategory.LOGGING in infra_categories
        assert EnumConfigCategory.TESTING in infra_categories

        # Should not include system categories
        assert EnumConfigCategory.GENERATION not in infra_categories
        assert EnumConfigCategory.VALIDATION not in infra_categories
        assert EnumConfigCategory.GENERAL not in infra_categories

    def test_is_system_category(self):
        """Test is_system_category classification method."""
        # Should be system categories
        assert (
            EnumConfigCategory.is_system_category(EnumConfigCategory.GENERATION) is True
        )
        assert (
            EnumConfigCategory.is_system_category(EnumConfigCategory.VALIDATION) is True
        )
        assert (
            EnumConfigCategory.is_system_category(EnumConfigCategory.TEMPLATE) is True
        )
        assert (
            EnumConfigCategory.is_system_category(EnumConfigCategory.MAINTENANCE)
            is True
        )
        assert EnumConfigCategory.is_system_category(EnumConfigCategory.RUNTIME) is True

        # Should not be system categories
        assert EnumConfigCategory.is_system_category(EnumConfigCategory.CLI) is False
        assert (
            EnumConfigCategory.is_system_category(EnumConfigCategory.DISCOVERY) is False
        )
        assert (
            EnumConfigCategory.is_system_category(EnumConfigCategory.GENERAL) is False
        )
        assert (
            EnumConfigCategory.is_system_category(EnumConfigCategory.UNKNOWN) is False
        )

    def test_is_infrastructure_category(self):
        """Test is_infrastructure_category classification method."""
        # Should be infrastructure categories
        assert (
            EnumConfigCategory.is_infrastructure_category(EnumConfigCategory.CLI)
            is True
        )
        assert (
            EnumConfigCategory.is_infrastructure_category(EnumConfigCategory.DISCOVERY)
            is True
        )
        assert (
            EnumConfigCategory.is_infrastructure_category(EnumConfigCategory.SCHEMA)
            is True
        )
        assert (
            EnumConfigCategory.is_infrastructure_category(EnumConfigCategory.LOGGING)
            is True
        )
        assert (
            EnumConfigCategory.is_infrastructure_category(EnumConfigCategory.TESTING)
            is True
        )

        # Should not be infrastructure categories
        assert (
            EnumConfigCategory.is_infrastructure_category(EnumConfigCategory.GENERATION)
            is False
        )
        assert (
            EnumConfigCategory.is_infrastructure_category(EnumConfigCategory.VALIDATION)
            is False
        )
        assert (
            EnumConfigCategory.is_infrastructure_category(EnumConfigCategory.GENERAL)
            is False
        )
        assert (
            EnumConfigCategory.is_infrastructure_category(EnumConfigCategory.UNKNOWN)
            is False
        )

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        assert EnumConfigCategory.GENERATION == EnumConfigCategory.GENERATION
        assert EnumConfigCategory.GENERATION != EnumConfigCategory.VALIDATION
        assert EnumConfigCategory.GENERATION == "generation"
        assert EnumConfigCategory.CLI != "generation"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert EnumConfigCategory.GENERATION in EnumConfigCategory
        assert EnumConfigCategory.CLI in EnumConfigCategory
        assert EnumConfigCategory.GENERAL in EnumConfigCategory

    def test_enum_iteration(self):
        """Test iteration over enum values."""
        categories = list(EnumConfigCategory)
        assert len(categories) == 12  # 5 system + 5 infrastructure + 2 generic
        assert EnumConfigCategory.GENERATION in categories
        assert EnumConfigCategory.CLI in categories
        assert EnumConfigCategory.GENERAL in categories

    def test_json_serialization(self):
        """Test JSON serialization of enum values."""
        assert json.dumps(EnumConfigCategory.GENERATION) == '"generation"'
        assert json.dumps(EnumConfigCategory.CLI) == '"cli"'

    def test_pydantic_model_integration(self):
        """Test Pydantic model integration with enum."""

        class Config(BaseModel):
            category: EnumConfigCategory

        # Test valid enum value
        config = Config(category=EnumConfigCategory.GENERATION)
        assert config.category == EnumConfigCategory.GENERATION

        # Test valid string value
        config = Config(category="validation")
        assert config.category == EnumConfigCategory.VALIDATION

        # Test invalid value
        with pytest.raises(ValidationError):
            Config(category="invalid_category")

    def test_enum_uniqueness(self):
        """Test that all enum values are unique."""
        values = [category.value for category in EnumConfigCategory]
        assert len(values) == len(set(values))

    def test_category_classification_mutually_exclusive(self):
        """Test that categories are either system or infrastructure (or neither)."""
        for category in EnumConfigCategory:
            is_system = EnumConfigCategory.is_system_category(category)
            is_infrastructure = EnumConfigCategory.is_infrastructure_category(category)
            # Should not be both system and infrastructure
            assert not (is_system and is_infrastructure)

    def test_all_categories_classified(self):
        """Test that all non-generic categories are classified."""
        unclassified = []
        for category in EnumConfigCategory:
            is_system = EnumConfigCategory.is_system_category(category)
            is_infrastructure = EnumConfigCategory.is_infrastructure_category(category)
            is_generic = category in {
                EnumConfigCategory.GENERAL,
                EnumConfigCategory.UNKNOWN,
            }

            if not (is_system or is_infrastructure or is_generic):
                unclassified.append(category)

        # All categories should be classified
        assert len(unclassified) == 0


@pytest.mark.unit
class TestEnumConfigCategoryEdgeCases:
    """Test edge cases for EnumConfigCategory."""

    def test_case_sensitivity(self):
        """Test that enum values are case-sensitive."""

        class Config(BaseModel):
            category: EnumConfigCategory

        # Lowercase should work
        config = Config(category="generation")
        assert config.category == EnumConfigCategory.GENERATION

        # Uppercase should fail
        with pytest.raises(ValidationError):
            Config(category="GENERATION")

        # Mixed case should fail
        with pytest.raises(ValidationError):
            Config(category="Generation")

    def test_whitespace_handling(self):
        """Test that whitespace in values is rejected."""

        class Config(BaseModel):
            category: EnumConfigCategory

        with pytest.raises(ValidationError):
            Config(category=" generation")

        with pytest.raises(ValidationError):
            Config(category="generation ")

    def test_system_and_infrastructure_categories_disjoint(self):
        """Test that system and infrastructure category sets are disjoint."""
        system_categories = set(EnumConfigCategory.get_system_categories())
        infra_categories = set(EnumConfigCategory.get_infrastructure_categories())

        # Sets should not overlap
        assert len(system_categories & infra_categories) == 0

        # Union should not include generic categories
        all_classified = system_categories | infra_categories
        assert EnumConfigCategory.GENERAL not in all_classified
        assert EnumConfigCategory.UNKNOWN not in all_classified

    def test_helper_methods_return_lists(self):
        """Test that helper methods return lists, not sets."""
        system_categories = EnumConfigCategory.get_system_categories()
        infra_categories = EnumConfigCategory.get_infrastructure_categories()

        assert isinstance(system_categories, list)
        assert isinstance(infra_categories, list)
