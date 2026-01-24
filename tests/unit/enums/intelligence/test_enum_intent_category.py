"""Tests for EnumIntentCategory."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.intelligence.enum_intent_category import EnumIntentCategory
from omnibase_core.utils.util_str_enum_base import StrValueHelper


@pytest.mark.unit
class TestEnumIntentCategory:
    """Test suite for EnumIntentCategory basic functionality."""

    def test_enum_values_exist_and_correct(self):
        """Test that all 13 enum values exist with correct snake_case values."""
        # Development intents
        assert EnumIntentCategory.CODE_GENERATION.value == "code_generation"
        assert EnumIntentCategory.DEBUGGING.value == "debugging"
        assert EnumIntentCategory.REFACTORING.value == "refactoring"
        assert EnumIntentCategory.TESTING.value == "testing"
        assert EnumIntentCategory.DOCUMENTATION.value == "documentation"
        assert EnumIntentCategory.ANALYSIS.value == "analysis"

        # Intelligence intents
        assert EnumIntentCategory.PATTERN_LEARNING.value == "pattern_learning"
        assert EnumIntentCategory.QUALITY_ASSESSMENT.value == "quality_assessment"
        assert EnumIntentCategory.SEMANTIC_ANALYSIS.value == "semantic_analysis"

        # Meta intents
        assert EnumIntentCategory.HELP.value == "help"
        assert EnumIntentCategory.CLARIFY.value == "clarify"
        assert EnumIntentCategory.FEEDBACK.value == "feedback"

        # Fallback
        assert EnumIntentCategory.UNKNOWN.value == "unknown"

    def test_enum_count(self):
        """Test that enum has exactly 13 values."""
        values = list(EnumIntentCategory)
        assert len(values) == 13

    def test_enum_inheritance(self):
        """Test that enum inherits from StrValueHelper, str, and Enum."""
        assert issubclass(EnumIntentCategory, StrValueHelper)
        assert issubclass(EnumIntentCategory, str)
        assert issubclass(EnumIntentCategory, Enum)

    def test_str_value_helper_behavior(self):
        """Test that StrValueHelper provides correct __str__ behavior."""
        # str() should return the value (snake_case)
        assert str(EnumIntentCategory.CODE_GENERATION) == "code_generation"
        assert str(EnumIntentCategory.DEBUGGING) == "debugging"
        assert str(EnumIntentCategory.PATTERN_LEARNING) == "pattern_learning"
        assert str(EnumIntentCategory.HELP) == "help"
        assert str(EnumIntentCategory.UNKNOWN) == "unknown"

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings due to str inheritance."""
        intent = EnumIntentCategory.CODE_GENERATION
        assert isinstance(intent, str)
        assert intent == "code_generation"
        assert len(intent) == 15
        assert intent.startswith("code")
        assert intent.endswith("generation")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumIntentCategory)
        assert EnumIntentCategory.CODE_GENERATION in values
        assert EnumIntentCategory.DEBUGGING in values
        assert EnumIntentCategory.UNKNOWN in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "code_generation" in EnumIntentCategory
        assert "debugging" in EnumIntentCategory
        assert "pattern_learning" in EnumIntentCategory
        assert "unknown" in EnumIntentCategory
        assert "invalid_intent" not in EnumIntentCategory

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        intent1 = EnumIntentCategory.CODE_GENERATION
        intent2 = EnumIntentCategory.DEBUGGING

        assert intent1 != intent2
        assert intent1 == "code_generation"
        assert intent2 == "debugging"

        # Same enum value comparison
        intent3 = EnumIntentCategory.CODE_GENERATION
        assert intent1 == intent3
        assert intent1 is intent3  # Same instance due to enum singleton

    def test_enum_serialization(self):
        """Test that enum values can be serialized to JSON."""
        intent = EnumIntentCategory.QUALITY_ASSESSMENT
        serialized = intent.value
        assert serialized == "quality_assessment"

        # Test JSON serialization (works due to str inheritance)
        json_str = json.dumps(intent)
        assert json_str == '"quality_assessment"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        intent = EnumIntentCategory("code_generation")
        assert intent == EnumIntentCategory.CODE_GENERATION

        intent = EnumIntentCategory("pattern_learning")
        assert intent == EnumIntentCategory.PATTERN_LEARNING

        intent = EnumIntentCategory("unknown")
        assert intent == EnumIntentCategory.UNKNOWN

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumIntentCategory("invalid_intent")

        with pytest.raises(ValueError):
            EnumIntentCategory("CODE_GENERATION")  # Wrong case (uppercase)

        with pytest.raises(ValueError):
            EnumIntentCategory("codeGeneration")  # Wrong case (camelCase)

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "code_generation",
            "debugging",
            "refactoring",
            "testing",
            "documentation",
            "analysis",
            "pattern_learning",
            "quality_assessment",
            "semantic_analysis",
            "help",
            "clarify",
            "feedback",
            "unknown",
        }

        actual_values = {member.value for member in EnumIntentCategory}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumIntentCategory.__doc__ is not None
        assert "intent" in EnumIntentCategory.__doc__.lower()

    def test_enum_uniqueness(self):
        """Test that @unique decorator ensures unique values."""
        # The @unique decorator ensures all values are distinct
        values = [member.value for member in EnumIntentCategory]
        assert len(values) == len(set(values))

    def test_enum_names_match_expected(self):
        """Test that enum names follow expected naming convention."""
        expected_names = {
            "CODE_GENERATION",
            "DEBUGGING",
            "REFACTORING",
            "TESTING",
            "DOCUMENTATION",
            "ANALYSIS",
            "PATTERN_LEARNING",
            "QUALITY_ASSESSMENT",
            "SEMANTIC_ANALYSIS",
            "HELP",
            "CLARIFY",
            "FEEDBACK",
            "UNKNOWN",
        }

        actual_names = {member.name for member in EnumIntentCategory}
        assert actual_names == expected_names


@pytest.mark.unit
class TestIsDevelopmentIntent:
    """Tests for is_development_intent classmethod."""

    def test_development_intents_return_true(self):
        """Test that development intents return True."""
        dev_intents = [
            EnumIntentCategory.CODE_GENERATION,
            EnumIntentCategory.DEBUGGING,
            EnumIntentCategory.REFACTORING,
            EnumIntentCategory.TESTING,
            EnumIntentCategory.DOCUMENTATION,
            EnumIntentCategory.ANALYSIS,
        ]

        for intent in dev_intents:
            assert EnumIntentCategory.is_development_intent(intent) is True, (
                f"Expected {intent} to be a development intent"
            )

    def test_non_development_intents_return_false(self):
        """Test that non-development intents return False."""
        non_dev_intents = [
            EnumIntentCategory.PATTERN_LEARNING,
            EnumIntentCategory.QUALITY_ASSESSMENT,
            EnumIntentCategory.SEMANTIC_ANALYSIS,
            EnumIntentCategory.HELP,
            EnumIntentCategory.CLARIFY,
            EnumIntentCategory.FEEDBACK,
            EnumIntentCategory.UNKNOWN,
        ]

        for intent in non_dev_intents:
            assert EnumIntentCategory.is_development_intent(intent) is False, (
                f"Expected {intent} to NOT be a development intent"
            )

    def test_development_intent_count(self):
        """Test that exactly 6 intents are development intents."""
        dev_count = sum(
            1
            for intent in EnumIntentCategory
            if EnumIntentCategory.is_development_intent(intent)
        )
        assert dev_count == 6


@pytest.mark.unit
class TestIsIntelligenceIntent:
    """Tests for is_intelligence_intent classmethod."""

    def test_intelligence_intents_return_true(self):
        """Test that intelligence intents return True."""
        intel_intents = [
            EnumIntentCategory.PATTERN_LEARNING,
            EnumIntentCategory.QUALITY_ASSESSMENT,
            EnumIntentCategory.SEMANTIC_ANALYSIS,
        ]

        for intent in intel_intents:
            assert EnumIntentCategory.is_intelligence_intent(intent) is True, (
                f"Expected {intent} to be an intelligence intent"
            )

    def test_non_intelligence_intents_return_false(self):
        """Test that non-intelligence intents return False."""
        non_intel_intents = [
            EnumIntentCategory.CODE_GENERATION,
            EnumIntentCategory.DEBUGGING,
            EnumIntentCategory.REFACTORING,
            EnumIntentCategory.TESTING,
            EnumIntentCategory.DOCUMENTATION,
            EnumIntentCategory.ANALYSIS,
            EnumIntentCategory.HELP,
            EnumIntentCategory.CLARIFY,
            EnumIntentCategory.FEEDBACK,
            EnumIntentCategory.UNKNOWN,
        ]

        for intent in non_intel_intents:
            assert EnumIntentCategory.is_intelligence_intent(intent) is False, (
                f"Expected {intent} to NOT be an intelligence intent"
            )

    def test_intelligence_intent_count(self):
        """Test that exactly 3 intents are intelligence intents."""
        intel_count = sum(
            1
            for intent in EnumIntentCategory
            if EnumIntentCategory.is_intelligence_intent(intent)
        )
        assert intel_count == 3


@pytest.mark.unit
class TestIsMetaIntent:
    """Tests for is_meta_intent classmethod."""

    def test_meta_intents_return_true(self):
        """Test that meta intents return True."""
        meta_intents = [
            EnumIntentCategory.HELP,
            EnumIntentCategory.CLARIFY,
            EnumIntentCategory.FEEDBACK,
        ]

        for intent in meta_intents:
            assert EnumIntentCategory.is_meta_intent(intent) is True, (
                f"Expected {intent} to be a meta intent"
            )

    def test_non_meta_intents_return_false(self):
        """Test that non-meta intents return False."""
        non_meta_intents = [
            EnumIntentCategory.CODE_GENERATION,
            EnumIntentCategory.DEBUGGING,
            EnumIntentCategory.REFACTORING,
            EnumIntentCategory.TESTING,
            EnumIntentCategory.DOCUMENTATION,
            EnumIntentCategory.ANALYSIS,
            EnumIntentCategory.PATTERN_LEARNING,
            EnumIntentCategory.QUALITY_ASSESSMENT,
            EnumIntentCategory.SEMANTIC_ANALYSIS,
            EnumIntentCategory.UNKNOWN,
        ]

        for intent in non_meta_intents:
            assert EnumIntentCategory.is_meta_intent(intent) is False, (
                f"Expected {intent} to NOT be a meta intent"
            )

    def test_meta_intent_count(self):
        """Test that exactly 3 intents are meta intents."""
        meta_count = sum(
            1
            for intent in EnumIntentCategory
            if EnumIntentCategory.is_meta_intent(intent)
        )
        assert meta_count == 3


@pytest.mark.unit
class TestIsClassified:
    """Tests for is_classified classmethod."""

    def test_classified_intents_return_true(self):
        """Test that all classified intents return True."""
        classified_intents = [
            EnumIntentCategory.CODE_GENERATION,
            EnumIntentCategory.DEBUGGING,
            EnumIntentCategory.REFACTORING,
            EnumIntentCategory.TESTING,
            EnumIntentCategory.DOCUMENTATION,
            EnumIntentCategory.ANALYSIS,
            EnumIntentCategory.PATTERN_LEARNING,
            EnumIntentCategory.QUALITY_ASSESSMENT,
            EnumIntentCategory.SEMANTIC_ANALYSIS,
            EnumIntentCategory.HELP,
            EnumIntentCategory.CLARIFY,
            EnumIntentCategory.FEEDBACK,
        ]

        for intent in classified_intents:
            assert EnumIntentCategory.is_classified(intent) is True, (
                f"Expected {intent} to be classified"
            )

    def test_unknown_returns_false(self):
        """Test that UNKNOWN returns False."""
        assert EnumIntentCategory.is_classified(EnumIntentCategory.UNKNOWN) is False

    def test_classified_count(self):
        """Test that exactly 12 intents are classified (all except UNKNOWN)."""
        classified_count = sum(
            1
            for intent in EnumIntentCategory
            if EnumIntentCategory.is_classified(intent)
        )
        assert classified_count == 12


@pytest.mark.unit
class TestGetDevelopmentIntents:
    """Tests for get_development_intents classmethod."""

    def test_returns_correct_set(self):
        """Test that get_development_intents returns the correct set."""
        expected = {
            EnumIntentCategory.CODE_GENERATION,
            EnumIntentCategory.DEBUGGING,
            EnumIntentCategory.REFACTORING,
            EnumIntentCategory.TESTING,
            EnumIntentCategory.DOCUMENTATION,
            EnumIntentCategory.ANALYSIS,
        }

        actual = EnumIntentCategory.get_development_intents()
        assert actual == expected

    def test_returns_set_type(self):
        """Test that get_development_intents returns a set."""
        result = EnumIntentCategory.get_development_intents()
        assert isinstance(result, set)

    def test_count_matches_helper(self):
        """Test that count matches is_development_intent helper."""
        getter_result = EnumIntentCategory.get_development_intents()
        helper_count = sum(
            1
            for intent in EnumIntentCategory
            if EnumIntentCategory.is_development_intent(intent)
        )
        assert len(getter_result) == helper_count


@pytest.mark.unit
class TestGetIntelligenceIntents:
    """Tests for get_intelligence_intents classmethod."""

    def test_returns_correct_set(self):
        """Test that get_intelligence_intents returns the correct set."""
        expected = {
            EnumIntentCategory.PATTERN_LEARNING,
            EnumIntentCategory.QUALITY_ASSESSMENT,
            EnumIntentCategory.SEMANTIC_ANALYSIS,
        }

        actual = EnumIntentCategory.get_intelligence_intents()
        assert actual == expected

    def test_returns_set_type(self):
        """Test that get_intelligence_intents returns a set."""
        result = EnumIntentCategory.get_intelligence_intents()
        assert isinstance(result, set)

    def test_count_matches_helper(self):
        """Test that count matches is_intelligence_intent helper."""
        getter_result = EnumIntentCategory.get_intelligence_intents()
        helper_count = sum(
            1
            for intent in EnumIntentCategory
            if EnumIntentCategory.is_intelligence_intent(intent)
        )
        assert len(getter_result) == helper_count


@pytest.mark.unit
class TestGetMetaIntents:
    """Tests for get_meta_intents classmethod."""

    def test_returns_correct_set(self):
        """Test that get_meta_intents returns the correct set."""
        expected = {
            EnumIntentCategory.HELP,
            EnumIntentCategory.CLARIFY,
            EnumIntentCategory.FEEDBACK,
        }

        actual = EnumIntentCategory.get_meta_intents()
        assert actual == expected

    def test_returns_set_type(self):
        """Test that get_meta_intents returns a set."""
        result = EnumIntentCategory.get_meta_intents()
        assert isinstance(result, set)

    def test_count_matches_helper(self):
        """Test that count matches is_meta_intent helper."""
        getter_result = EnumIntentCategory.get_meta_intents()
        helper_count = sum(
            1
            for intent in EnumIntentCategory
            if EnumIntentCategory.is_meta_intent(intent)
        )
        assert len(getter_result) == helper_count


@pytest.mark.unit
class TestCategoryGroupCoverage:
    """Tests for category group coverage and consistency."""

    def test_no_overlap_between_categories(self):
        """Test that category groups do not overlap."""
        dev_intents = EnumIntentCategory.get_development_intents()
        intel_intents = EnumIntentCategory.get_intelligence_intents()
        meta_intents = EnumIntentCategory.get_meta_intents()

        # No overlap between development and intelligence
        assert dev_intents.isdisjoint(intel_intents), (
            "Development and intelligence intents should not overlap"
        )

        # No overlap between development and meta
        assert dev_intents.isdisjoint(meta_intents), (
            "Development and meta intents should not overlap"
        )

        # No overlap between intelligence and meta
        assert intel_intents.isdisjoint(meta_intents), (
            "Intelligence and meta intents should not overlap"
        )

    def test_all_categories_covered_except_unknown(self):
        """Test that all categories except UNKNOWN are in exactly one group."""
        dev_intents = EnumIntentCategory.get_development_intents()
        intel_intents = EnumIntentCategory.get_intelligence_intents()
        meta_intents = EnumIntentCategory.get_meta_intents()

        # Union of all groups
        all_grouped = dev_intents | intel_intents | meta_intents

        # All intents except UNKNOWN should be in exactly one group
        all_intents = set(EnumIntentCategory)
        expected_grouped = all_intents - {EnumIntentCategory.UNKNOWN}

        assert all_grouped == expected_grouped, (
            "All intents except UNKNOWN should be covered by exactly one group"
        )

    def test_unknown_not_in_any_group(self):
        """Test that UNKNOWN is not in any category group."""
        unknown = EnumIntentCategory.UNKNOWN

        assert not EnumIntentCategory.is_development_intent(unknown)
        assert not EnumIntentCategory.is_intelligence_intent(unknown)
        assert not EnumIntentCategory.is_meta_intent(unknown)

        assert unknown not in EnumIntentCategory.get_development_intents()
        assert unknown not in EnumIntentCategory.get_intelligence_intents()
        assert unknown not in EnumIntentCategory.get_meta_intents()

    def test_total_group_counts_match_enum_size(self):
        """Test that group sizes + UNKNOWN equals total enum size."""
        dev_count = len(EnumIntentCategory.get_development_intents())
        intel_count = len(EnumIntentCategory.get_intelligence_intents())
        meta_count = len(EnumIntentCategory.get_meta_intents())
        unknown_count = 1  # UNKNOWN

        total_enum_size = len(list(EnumIntentCategory))

        assert dev_count + intel_count + meta_count + unknown_count == total_enum_size

    def test_helper_and_getter_consistency(self):
        """Test that helper methods and getter methods are consistent."""
        for intent in EnumIntentCategory:
            is_dev = EnumIntentCategory.is_development_intent(intent)
            in_dev_set = intent in EnumIntentCategory.get_development_intents()
            assert is_dev == in_dev_set, (
                f"Inconsistent for {intent}: is_development_intent={is_dev}, "
                f"in_get_development_intents={in_dev_set}"
            )

            is_intel = EnumIntentCategory.is_intelligence_intent(intent)
            in_intel_set = intent in EnumIntentCategory.get_intelligence_intents()
            assert is_intel == in_intel_set, (
                f"Inconsistent for {intent}: is_intelligence_intent={is_intel}, "
                f"in_get_intelligence_intents={in_intel_set}"
            )

            is_meta = EnumIntentCategory.is_meta_intent(intent)
            in_meta_set = intent in EnumIntentCategory.get_meta_intents()
            assert is_meta == in_meta_set, (
                f"Inconsistent for {intent}: is_meta_intent={is_meta}, "
                f"in_get_meta_intents={in_meta_set}"
            )

    def test_each_classified_intent_in_exactly_one_group(self):
        """Test that each classified intent is in exactly one group."""
        for intent in EnumIntentCategory:
            if intent == EnumIntentCategory.UNKNOWN:
                continue

            is_dev = EnumIntentCategory.is_development_intent(intent)
            is_intel = EnumIntentCategory.is_intelligence_intent(intent)
            is_meta = EnumIntentCategory.is_meta_intent(intent)

            group_count = sum([is_dev, is_intel, is_meta])
            assert group_count == 1, (
                f"Intent {intent} should be in exactly one group, "
                f"but is in {group_count} groups"
            )
