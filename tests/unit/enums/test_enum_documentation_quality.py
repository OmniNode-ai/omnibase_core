# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for EnumDocumentationQuality.

Comprehensive tests for documentation quality enumeration and assessment methods.
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_documentation_quality import EnumDocumentationQuality


@pytest.mark.unit
class TestEnumDocumentationQuality:
    """Test EnumDocumentationQuality enumeration."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "NONE": "none",
            "POOR": "poor",
            "MINIMAL": "minimal",
            "BASIC": "basic",
            "ADEQUATE": "adequate",
            "GOOD": "good",
            "COMPREHENSIVE": "comprehensive",
            "EXCELLENT": "excellent",
            "OUTSTANDING": "outstanding",
            "MISSING": "missing",
            "INCOMPLETE": "incomplete",
            "OUTDATED": "outdated",
            "UNKNOWN": "unknown",
        }

        for name, value in expected_values.items():
            quality = getattr(EnumDocumentationQuality, name)
            assert quality.value == value
            assert str(quality) == value

    def test_str_representation(self):
        """Test __str__ returns the value for serialization."""
        assert str(EnumDocumentationQuality.NONE) == "none"
        assert str(EnumDocumentationQuality.EXCELLENT) == "excellent"
        assert str(EnumDocumentationQuality.OUTDATED) == "outdated"

    def test_enum_uniqueness(self):
        """Test that all enum values are unique."""
        values = [e.value for e in EnumDocumentationQuality]
        assert len(values) == len(set(values))

    def test_enum_members_count(self):
        """Test that we have exactly 13 documentation quality levels."""
        assert len(list(EnumDocumentationQuality)) == 13


@pytest.mark.unit
class TestNumericScore:
    """Test get_numeric_score method."""

    def test_all_quality_levels_have_scores(self):
        """Test that all quality levels return valid numeric scores."""
        for quality in EnumDocumentationQuality:
            score = EnumDocumentationQuality.get_numeric_score(quality)
            assert isinstance(score, int)
            assert 0 <= score <= 10

    def test_none_and_missing_score_zero(self):
        """Test that NONE and MISSING have score of 0."""
        assert (
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.NONE)
            == 0
        )
        assert (
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.MISSING)
            == 0
        )

    def test_poor_score(self):
        """Test POOR quality score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.POOR)
            == 1
        )

    def test_minimal_score(self):
        """Test MINIMAL quality score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.MINIMAL)
            == 2
        )

    def test_incomplete_score(self):
        """Test INCOMPLETE quality score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.INCOMPLETE
            )
            == 3
        )

    def test_basic_score(self):
        """Test BASIC quality score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.BASIC)
            == 4
        )

    def test_adequate_score(self):
        """Test ADEQUATE quality score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.ADEQUATE
            )
            == 5
        )

    def test_outdated_score(self):
        """Test OUTDATED quality score - good content but not current."""
        assert (
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.OUTDATED
            )
            == 4
        )

    def test_good_score(self):
        """Test GOOD quality score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.GOOD)
            == 6
        )

    def test_comprehensive_score(self):
        """Test COMPREHENSIVE quality score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.COMPREHENSIVE
            )
            == 8
        )

    def test_excellent_score(self):
        """Test EXCELLENT quality score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.EXCELLENT
            )
            == 9
        )

    def test_outstanding_score(self):
        """Test OUTSTANDING quality score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.OUTSTANDING
            )
            == 10
        )

    def test_unknown_score(self):
        """Test UNKNOWN quality defaults to middle score."""
        assert (
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.UNKNOWN)
            == 5
        )

    def test_score_ordering(self):
        """Test that scores are properly ordered from low to high."""
        scores = [
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.NONE),
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.POOR),
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.MINIMAL
            ),
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.BASIC),
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.ADEQUATE
            ),
            EnumDocumentationQuality.get_numeric_score(EnumDocumentationQuality.GOOD),
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.COMPREHENSIVE
            ),
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.EXCELLENT
            ),
            EnumDocumentationQuality.get_numeric_score(
                EnumDocumentationQuality.OUTSTANDING
            ),
        ]
        # Verify strictly increasing
        for i in range(len(scores) - 1):
            assert scores[i] < scores[i + 1]


@pytest.mark.unit
class TestIsAcceptable:
    """Test is_acceptable method."""

    def test_acceptable_quality_levels(self):
        """Test quality levels that are acceptable."""
        acceptable = [
            EnumDocumentationQuality.ADEQUATE,
            EnumDocumentationQuality.GOOD,
            EnumDocumentationQuality.COMPREHENSIVE,
            EnumDocumentationQuality.EXCELLENT,
            EnumDocumentationQuality.OUTSTANDING,
        ]
        for quality in acceptable:
            assert EnumDocumentationQuality.is_acceptable(quality) is True

    def test_unacceptable_quality_levels(self):
        """Test quality levels that are not acceptable."""
        unacceptable = [
            EnumDocumentationQuality.NONE,
            EnumDocumentationQuality.POOR,
            EnumDocumentationQuality.MINIMAL,
            EnumDocumentationQuality.BASIC,
            EnumDocumentationQuality.MISSING,
            EnumDocumentationQuality.INCOMPLETE,
            EnumDocumentationQuality.OUTDATED,
            EnumDocumentationQuality.UNKNOWN,
        ]
        for quality in unacceptable:
            assert EnumDocumentationQuality.is_acceptable(quality) is False


@pytest.mark.unit
class TestNeedsImprovement:
    """Test needs_improvement method."""

    def test_quality_needing_improvement(self):
        """Test quality levels that need improvement."""
        needs_work = [
            EnumDocumentationQuality.NONE,
            EnumDocumentationQuality.POOR,
            EnumDocumentationQuality.MINIMAL,
            EnumDocumentationQuality.BASIC,
            EnumDocumentationQuality.MISSING,
            EnumDocumentationQuality.INCOMPLETE,
            EnumDocumentationQuality.OUTDATED,
        ]
        for quality in needs_work:
            assert EnumDocumentationQuality.needs_improvement(quality) is True

    def test_quality_not_needing_improvement(self):
        """Test quality levels that don't need improvement."""
        satisfactory = [
            EnumDocumentationQuality.ADEQUATE,
            EnumDocumentationQuality.GOOD,
            EnumDocumentationQuality.COMPREHENSIVE,
            EnumDocumentationQuality.EXCELLENT,
            EnumDocumentationQuality.OUTSTANDING,
            EnumDocumentationQuality.UNKNOWN,
        ]
        for quality in satisfactory:
            assert EnumDocumentationQuality.needs_improvement(quality) is False


@pytest.mark.unit
class TestIsHighQuality:
    """Test is_high_quality method."""

    def test_high_quality_levels(self):
        """Test quality levels considered high quality."""
        high_quality = [
            EnumDocumentationQuality.COMPREHENSIVE,
            EnumDocumentationQuality.EXCELLENT,
            EnumDocumentationQuality.OUTSTANDING,
        ]
        for quality in high_quality:
            assert EnumDocumentationQuality.is_high_quality(quality) is True

    def test_not_high_quality_levels(self):
        """Test quality levels not considered high quality."""
        not_high = [
            EnumDocumentationQuality.NONE,
            EnumDocumentationQuality.POOR,
            EnumDocumentationQuality.MINIMAL,
            EnumDocumentationQuality.BASIC,
            EnumDocumentationQuality.ADEQUATE,
            EnumDocumentationQuality.GOOD,
            EnumDocumentationQuality.MISSING,
            EnumDocumentationQuality.INCOMPLETE,
            EnumDocumentationQuality.OUTDATED,
            EnumDocumentationQuality.UNKNOWN,
        ]
        for quality in not_high:
            assert EnumDocumentationQuality.is_high_quality(quality) is False


@pytest.mark.unit
class TestImprovementSuggestion:
    """Test get_improvement_suggestion method."""

    def test_all_qualities_have_suggestions(self):
        """Test that all quality levels have improvement suggestions."""
        for quality in EnumDocumentationQuality:
            suggestion = EnumDocumentationQuality.get_improvement_suggestion(quality)
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0

    def test_none_suggestion(self):
        """Test improvement suggestion for NONE quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.NONE
        )
        assert "Create basic documentation" in suggestion
        assert "purpose" in suggestion.lower()

    def test_missing_suggestion(self):
        """Test improvement suggestion for MISSING quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.MISSING
        )
        assert "Add documentation files" in suggestion

    def test_poor_suggestion(self):
        """Test improvement suggestion for POOR quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.POOR
        )
        assert "clarity" in suggestion.lower() or "details" in suggestion.lower()

    def test_minimal_suggestion(self):
        """Test improvement suggestion for MINIMAL quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.MINIMAL
        )
        assert "examples" in suggestion.lower()

    def test_basic_suggestion(self):
        """Test improvement suggestion for BASIC quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.BASIC
        )
        assert "detailed" in suggestion.lower() or "edge cases" in suggestion.lower()

    def test_incomplete_suggestion(self):
        """Test improvement suggestion for INCOMPLETE quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.INCOMPLETE
        )
        assert "Complete" in suggestion or "missing" in suggestion.lower()

    def test_outdated_suggestion(self):
        """Test improvement suggestion for OUTDATED quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.OUTDATED
        )
        assert "Update" in suggestion or "current" in suggestion.lower()

    def test_adequate_suggestion(self):
        """Test improvement suggestion for ADEQUATE quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.ADEQUATE
        )
        assert (
            "examples" in suggestion.lower() or "best practices" in suggestion.lower()
        )

    def test_good_suggestion(self):
        """Test improvement suggestion for GOOD quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.GOOD
        )
        assert "advanced" in suggestion.lower() or "tutorials" in suggestion.lower()

    def test_comprehensive_suggestion(self):
        """Test improvement suggestion for COMPREHENSIVE quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.COMPREHENSIVE
        )
        assert "Maintain" in suggestion

    def test_excellent_suggestion(self):
        """Test improvement suggestion for EXCELLENT quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.EXCELLENT
        )
        assert "maintain" in suggestion.lower()

    def test_outstanding_suggestion(self):
        """Test improvement suggestion for OUTSTANDING quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.OUTSTANDING
        )
        assert "example" in suggestion.lower()

    def test_unknown_suggestion(self):
        """Test improvement suggestion for UNKNOWN quality."""
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(
            EnumDocumentationQuality.UNKNOWN
        )
        assert "Assess" in suggestion or "assess" in suggestion


@pytest.mark.unit
class TestFromScore:
    """Test from_score method."""

    def test_score_zero_maps_to_none(self):
        """Test score of 0 maps to NONE."""
        assert EnumDocumentationQuality.from_score(0) == EnumDocumentationQuality.NONE

    def test_negative_score_maps_to_none(self):
        """Test negative scores map to NONE."""
        assert EnumDocumentationQuality.from_score(-1) == EnumDocumentationQuality.NONE
        assert EnumDocumentationQuality.from_score(-10) == EnumDocumentationQuality.NONE

    def test_score_one_maps_to_poor(self):
        """Test score of 1 maps to POOR."""
        assert EnumDocumentationQuality.from_score(1) == EnumDocumentationQuality.POOR

    def test_score_two_maps_to_minimal(self):
        """Test score of 2 maps to MINIMAL."""
        assert (
            EnumDocumentationQuality.from_score(2) == EnumDocumentationQuality.MINIMAL
        )

    def test_score_three_maps_to_basic(self):
        """Test score of 3 maps to BASIC."""
        assert EnumDocumentationQuality.from_score(3) == EnumDocumentationQuality.BASIC

    def test_score_four_maps_to_adequate(self):
        """Test score of 4 maps to ADEQUATE."""
        assert (
            EnumDocumentationQuality.from_score(4) == EnumDocumentationQuality.ADEQUATE
        )

    def test_score_five_to_six_maps_to_good(self):
        """Test scores 5-6 map to GOOD."""
        assert EnumDocumentationQuality.from_score(5) == EnumDocumentationQuality.GOOD
        assert EnumDocumentationQuality.from_score(6) == EnumDocumentationQuality.GOOD

    def test_score_seven_to_eight_maps_to_comprehensive(self):
        """Test scores 7-8 map to COMPREHENSIVE."""
        assert (
            EnumDocumentationQuality.from_score(7)
            == EnumDocumentationQuality.COMPREHENSIVE
        )
        assert (
            EnumDocumentationQuality.from_score(8)
            == EnumDocumentationQuality.COMPREHENSIVE
        )

    def test_score_nine_maps_to_excellent(self):
        """Test score of 9 maps to EXCELLENT."""
        assert (
            EnumDocumentationQuality.from_score(9) == EnumDocumentationQuality.EXCELLENT
        )

    def test_score_ten_plus_maps_to_outstanding(self):
        """Test scores 10+ map to OUTSTANDING."""
        assert (
            EnumDocumentationQuality.from_score(10)
            == EnumDocumentationQuality.OUTSTANDING
        )
        assert (
            EnumDocumentationQuality.from_score(11)
            == EnumDocumentationQuality.OUTSTANDING
        )
        assert (
            EnumDocumentationQuality.from_score(100)
            == EnumDocumentationQuality.OUTSTANDING
        )

    def test_score_round_trip(self):
        """Test that from_score and get_numeric_score are consistent."""
        # For quality levels with single score values
        quality_score_pairs = [
            (EnumDocumentationQuality.NONE, 0),
            (EnumDocumentationQuality.POOR, 1),
            (EnumDocumentationQuality.MINIMAL, 2),
        ]
        for quality, expected_score in quality_score_pairs:
            score = EnumDocumentationQuality.get_numeric_score(quality)
            assert score == expected_score
            reconstructed = EnumDocumentationQuality.from_score(score)
            # Should map to same or similar quality level
            assert (
                EnumDocumentationQuality.get_numeric_score(reconstructed) <= score + 1
            )


@pytest.mark.unit
class TestEnumIntegration:
    """Integration tests for documentation quality enum."""

    def test_quality_classification_consistency(self):
        """Test that quality classifications are logically consistent."""
        # High quality should be acceptable but not need improvement
        for quality in [
            EnumDocumentationQuality.COMPREHENSIVE,
            EnumDocumentationQuality.EXCELLENT,
            EnumDocumentationQuality.OUTSTANDING,
        ]:
            assert EnumDocumentationQuality.is_high_quality(quality)
            assert EnumDocumentationQuality.is_acceptable(quality)
            assert not EnumDocumentationQuality.needs_improvement(quality)
            assert EnumDocumentationQuality.get_numeric_score(quality) >= 8

    def test_poor_quality_characteristics(self):
        """Test characteristics of poor quality documentation."""
        poor_qualities = [
            EnumDocumentationQuality.NONE,
            EnumDocumentationQuality.POOR,
            EnumDocumentationQuality.MISSING,
        ]
        for quality in poor_qualities:
            assert not EnumDocumentationQuality.is_acceptable(quality)
            assert EnumDocumentationQuality.needs_improvement(quality)
            assert not EnumDocumentationQuality.is_high_quality(quality)
            assert EnumDocumentationQuality.get_numeric_score(quality) <= 1

    def test_enum_serialization(self):
        """Test that enum can be serialized to JSON-compatible format."""
        for quality in EnumDocumentationQuality:
            assert isinstance(str(quality), str)
            assert isinstance(quality.value, str)
            assert str(quality) == quality.value

    def test_enum_from_value(self):
        """Test creating enum from string value."""
        assert EnumDocumentationQuality("none") == EnumDocumentationQuality.NONE
        assert (
            EnumDocumentationQuality("excellent") == EnumDocumentationQuality.EXCELLENT
        )
        assert EnumDocumentationQuality("outdated") == EnumDocumentationQuality.OUTDATED

    def test_invalid_value_raises_error(self):
        """Test that invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumDocumentationQuality("invalid_quality")

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class DocumentationModel(BaseModel):
            quality: EnumDocumentationQuality

        # Test valid enum assignment
        doc = DocumentationModel(quality=EnumDocumentationQuality.GOOD)
        assert doc.quality == EnumDocumentationQuality.GOOD

        # Test string assignment
        doc = DocumentationModel(quality="excellent")
        assert doc.quality == EnumDocumentationQuality.EXCELLENT

        # Test invalid value
        with pytest.raises(ValidationError):
            DocumentationModel(quality="invalid")

    def test_json_serialization(self):
        """Test JSON serialization."""
        quality = EnumDocumentationQuality.COMPREHENSIVE
        json_str = json.dumps(quality, default=str)
        assert json_str == '"comprehensive"'

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        assert EnumDocumentationQuality.GOOD == EnumDocumentationQuality.GOOD
        assert EnumDocumentationQuality.GOOD != EnumDocumentationQuality.EXCELLENT
        assert EnumDocumentationQuality.NONE != EnumDocumentationQuality.POOR

    def test_enum_in_collection(self):
        """Test that enum can be used in collections."""
        qualities = {
            EnumDocumentationQuality.GOOD,
            EnumDocumentationQuality.EXCELLENT,
        }
        assert EnumDocumentationQuality.GOOD in qualities
        assert EnumDocumentationQuality.POOR not in qualities

    def test_enum_as_dict_key(self):
        """Test that enum can be used as dictionary key."""
        quality_handlers = {
            EnumDocumentationQuality.NONE: "create_new_docs",
            EnumDocumentationQuality.OUTDATED: "update_docs",
            EnumDocumentationQuality.EXCELLENT: "maintain_docs",
        }
        assert quality_handlers[EnumDocumentationQuality.NONE] == "create_new_docs"
        assert len(quality_handlers) == 3

    def test_score_based_workflow(self):
        """Test a complete workflow using scores."""
        # Start with a score from assessment
        assessment_score = 7

        # Convert to quality level
        quality = EnumDocumentationQuality.from_score(assessment_score)
        assert quality == EnumDocumentationQuality.COMPREHENSIVE

        # Check if acceptable
        assert EnumDocumentationQuality.is_acceptable(quality)

        # Get improvement suggestion
        suggestion = EnumDocumentationQuality.get_improvement_suggestion(quality)
        assert isinstance(suggestion, str)

        # Verify numeric score consistency
        numeric = EnumDocumentationQuality.get_numeric_score(quality)
        assert numeric == 8  # COMPREHENSIVE maps to 8
