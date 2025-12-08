"""
Tests for validate-union-usage.py script.

Tests the UnionLegitimacyValidator class, specifically the companion Literal
discriminator detection logic in _is_discriminated_union method (lines 141-181).

This module provides comprehensive tests for edge cases in type normalization,
threshold calculation, and the companion Literal pattern detection.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


@pytest.fixture(scope="module")
def validate_union_usage_module() -> ModuleType:
    """Load the validate-union-usage.py script as a module.

    Returns:
        The loaded module containing UnionPattern and UnionLegitimacyValidator.
    """
    # Get the project root by navigating up from tests/unit/validation/
    scripts_path = Path(__file__).parent.parent.parent.parent / "scripts" / "validation"
    spec = importlib.util.spec_from_file_location(
        "validate_union_usage",
        scripts_path / "validate-union-usage.py",
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class TestCompanionLiteralEdgeCases:
    """Test edge cases for companion Literal discriminator detection.

    These tests focus on edge cases in the _is_discriminated_union method,
    particularly around type normalization and threshold calculations.
    """

    def test_empty_string_in_union_types_ignored(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that empty strings in union types are safely ignored."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        # Simulate a pattern with an empty string type (edge case)
        pattern = UnionPattern(
            ["bool", "", "str", "int"],  # Empty string included
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int]
    value_type: Literal["bool", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        # Should still detect - empty string is filtered out during normalization
        assert result is True, "Should handle empty strings in union types"

    def test_whitespace_only_type_handled(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that whitespace-only type strings are handled safely."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "   ", "str", "int"],  # Whitespace-only type
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int]
    value_type: Literal["bool", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        # Should detect - whitespace is stripped during base_type normalization
        assert result is True, "Should handle whitespace-only type strings"

    def test_subscripted_list_type_normalization(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test normalization of list[Any] to 'list'."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "list[Any]", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    value: Union[bool, list[Any], str, int]
    value_type: Literal["bool", "list", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should normalize list[Any] to 'list'"

    def test_complex_nested_generic_type_normalization(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test normalization of complex nested generics like dict[str, list[int]]."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "dict[str, list[int]]", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict[str, list[int]], str, int]
    value_type: Literal["bool", "dict", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should normalize complex generic to base type"

    def test_threshold_for_two_type_union(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test threshold calculation for 2-type union.

        Threshold = min(3, 2 // 2 + 1) = min(3, 2) = 2
        So need 2 matching types.
        """
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    value: Union[str, int]
    value_type: Literal["str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with 2 matching types for 2-type union"

    def test_threshold_for_four_type_union(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test threshold calculation for 4-type union.

        Threshold = min(3, 4 // 2 + 1) = min(3, 3) = 3
        So need 3 matching types.
        """
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int", "float"],
            line=10,
            file_path="/test/path.py",
        )

        # Only 2 matching types - below threshold of 3
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int, float]
    value_type: Literal["bool", "str"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is False, "Should not detect with only 2 matches for 4-type union"

    def test_threshold_boundary_exactly_at_threshold(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test detection exactly at the threshold boundary.

        For 4-type union: threshold = min(3, 4 // 2 + 1) = 3
        3 matches should pass.
        """
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int", "float"],
            line=10,
            file_path="/test/path.py",
        )

        # Exactly 3 matching types - at threshold
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int, float]
    value_type: Literal["bool", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with exactly 3 matches at threshold"

    def test_threshold_for_large_union(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test threshold calculation for large union (8+ types).

        Threshold = min(3, 8 // 2 + 1) = min(3, 5) = 3
        For unions >= 6 types, threshold caps at 3.
        """
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int", "float", "list", "dict", "tuple", "set"],
            line=10,
            file_path="/test/path.py",
        )

        # Exactly 3 matching types - at threshold of 3
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int, float, list, dict, tuple, set]
    value_type: Literal["bool", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with 3 matches for 8-type union"

    def test_threshold_for_large_union_below_minimum(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that 2 matches fails for large union (8 types) where threshold is 3."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int", "float", "list", "dict", "tuple", "set"],
            line=10,
            file_path="/test/path.py",
        )

        # Only 2 matching types - below threshold of 3
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int, float, list, dict, tuple, set]
    value_type: Literal["bool", "str"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is False, "Should not detect with only 2 matches for 8-type union"

    def test_mixed_quotes_in_literal(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test detection with mixed single and double quotes in Literal values."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int", "float"],
            line=10,
            file_path="/test/path.py",
        )

        # Mixed quotes in Literal values - using escaped quotes for test
        file_content = (
            "class MyModel(BaseModel):\n"
            "    value: Union[bool, str, int, float]\n"
            "    value_type: Literal[\"bool\", 'str', \"int\", 'float']\n"
        )

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with mixed quotes in Literal"

    def test_empty_literal_values(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that Literal with no word values does not trigger detection."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # Literal with numeric values only (no word matches)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int]
    count: Literal[1, 2, 3]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        # The regex only extracts word values ["\'](\w+)["\']
        # Numeric literals won't match, so no detection
        assert result is False, "Should not detect with non-word Literal values"

    def test_literal_with_underscore_type_names(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test detection with underscore-containing type names."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["my_type", "other_type", "third_type"],
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    value: Union[my_type, other_type, third_type]
    value_type: Literal["my_type", "other_type", "third_type"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with underscore-containing type names"


class TestRegexPatternCompilation:
    """Test the pre-compiled regex patterns used in the validator."""

    def test_literal_discriminator_pattern_matches_basic(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test LITERAL_DISCRIMINATOR_PATTERN matches basic Literal types."""
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        test_content = 'value_type: Literal["bool", "str", "int"]'

        matches = validator.LITERAL_DISCRIMINATOR_PATTERN.findall(test_content)
        assert len(matches) == 1
        assert '"bool", "str", "int"' in matches[0]

    def test_literal_discriminator_pattern_matches_single_quotes(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test LITERAL_DISCRIMINATOR_PATTERN matches single-quoted Literals."""
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        test_content = "value_type: Literal['bool', 'str', 'int']"

        matches = validator.LITERAL_DISCRIMINATOR_PATTERN.findall(test_content)
        assert len(matches) == 1
        assert "'bool', 'str', 'int'" in matches[0]

    def test_literal_value_pattern_extracts_words(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test LITERAL_VALUE_PATTERN extracts word values correctly."""
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        test_content = '"bool", "str", "int_type"'

        values = validator.LITERAL_VALUE_PATTERN.findall(test_content)
        assert len(values) == 3
        assert "bool" in values
        assert "str" in values
        assert "int_type" in values

    def test_field_discriminator_pattern_matches(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test FIELD_DISCRIMINATOR_PATTERN matches Field discriminator syntax."""
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        test_content = 'value: Union[A, B] = Field(..., discriminator="type")'

        match = validator.FIELD_DISCRIMINATOR_PATTERN.search(test_content)
        assert match is not None

    def test_field_discriminator_pattern_flexible_parameter_order(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test FIELD_DISCRIMINATOR_PATTERN matches with discriminator in different positions."""
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()

        # Discriminator at start
        test1 = 'value: Union[A, B] = Field(discriminator="type", default=None)'
        assert validator.FIELD_DISCRIMINATOR_PATTERN.search(test1) is not None

        # Discriminator at end
        test2 = 'value: Union[A, B] = Field(default=None, discriminator="type")'
        assert validator.FIELD_DISCRIMINATOR_PATTERN.search(test2) is not None


class TestFullValidationWorkflow:
    """Test the complete validation workflow with companion Literal detection."""

    def test_discriminated_union_returns_legitimate(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that discriminated unions are marked as legitimate."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int", "float"],
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int, float]
    value_type: Literal["bool", "str", "int", "float"]
"""

        result = validator.validate_union_legitimacy(pattern, file_content)

        assert result["is_legitimate"] is True
        assert result["pattern_type"] == "discriminated"
        assert result["confidence"] == 0.9
        assert len(result["issues"]) == 0

    def test_non_discriminated_union_flagged(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that non-discriminated primitive unions are flagged."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["str", "int", "bool", "float"],
            line=10,
            file_path="/test/path.py",
        )

        # No Literal discriminator
        file_content = """
class MyModel(BaseModel):
    value: Union[str, int, bool, float]
"""

        result = validator.validate_union_legitimacy(pattern, file_content)

        # Should be flagged as primitive_soup or similar
        assert result["is_legitimate"] is False
        assert result["pattern_type"] == "primitive_soup"


class TestCompanionLiteralDiscriminatorDetection:
    """Test edge cases for companion literal discriminator detection.

    These tests focus on the detection logic that identifies Literal fields
    as discriminators for Union types, including false positive prevention
    and correct matching with multiple Literal fields.
    """

    def test_companion_literal_requires_matching_type_values(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that companion literal detection requires matching type values.

        A Literal field should only be considered a discriminator if its values
        match the union type names. Unrelated Literal values should not trigger
        false positive detection.
        """
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # Unrelated Literal field (not a discriminator for this union)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int]
    status: Literal["active", "inactive"]  # Not related to value types
"""

        result = validator._is_discriminated_union(pattern, file_content)
        # Should NOT detect as discriminated - status values don't match union types
        assert result is False, (
            "Should not detect unrelated Literal fields as discriminators"
        )

    def test_multiple_literal_fields_correct_match(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test detection with multiple Literal fields - should match correct one.

        When multiple Literal fields exist in a file, the detection should
        correctly identify the one that matches the union type names.
        """
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    status: Literal["active", "inactive"]  # Unrelated
    value: Union[bool, str, int]
    value_type: Literal["bool", "str", "int"]  # Matching discriminator
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, (
            "Should detect matching discriminator among multiple Literal fields"
        )

    def test_partial_overlap_below_threshold_not_detected(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that partial overlap below threshold is not detected.

        If a Literal field only partially matches the union types and doesn't
        meet the threshold, it should not be considered a discriminator.
        """
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        # 4-type union: threshold = min(3, 4 // 2 + 1) = 3
        pattern = UnionPattern(
            ["bool", "str", "int", "float"],
            line=10,
            file_path="/test/path.py",
        )

        # Only 1 matching type - well below threshold of 3
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int, float]
    mode: Literal["bool", "debug", "verbose"]  # Only "bool" matches
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is False, "Should not detect with only 1 match for 4-type union"

    def test_literal_field_with_superset_of_union_types(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test detection when Literal has more values than union types.

        The Literal field may contain additional values beyond the union types,
        but if enough values match, it should still be detected as a discriminator.
        """
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # Literal has extra values beyond union types
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int]
    value_type: Literal["bool", "str", "int", "float", "list"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        # Should detect - all 3 union types are in the Literal
        assert result is True, (
            "Should detect when Literal contains all union types plus extras"
        )

    def test_no_literal_field_in_file(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that absence of Literal field means no companion detection."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # No Literal field at all
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int]
    name: str
    count: int
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is False, "Should not detect when no Literal field exists"

    def test_literal_with_case_mismatch_still_matches(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that case-insensitive matching works for Literal values.

        Literal values like "Bool" should match union type "bool" due to
        case-insensitive comparison in the detection logic.
        """
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # Literal values with different case
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int]
    value_type: Literal["BOOL", "STR", "INT"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with case-insensitive matching"


class TestTypeNormalizationDetails:
    """Detailed tests for type normalization logic."""

    def test_uppercase_type_names_normalized(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that uppercase type names are normalized to lowercase."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        # Uppercase type names
        pattern = UnionPattern(
            ["Bool", "Str", "Int"],
            line=10,
            file_path="/test/path.py",
        )

        # Literal with lowercase
        file_content = """
class MyModel(BaseModel):
    value: Union[Bool, Str, Int]
    value_type: Literal["bool", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should normalize uppercase types to lowercase"

    def test_optional_type_extraction(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test that Optional[X] in pattern is handled correctly."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        # Optional is subscripted
        pattern = UnionPattern(
            ["Optional[str]", "int", "bool"],
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    value: Union[Optional[str], int, bool]
    value_type: Literal["optional", "int", "bool"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        # Base type of Optional[str] is "optional" (before the [)
        assert result is True, "Should extract base type from Optional[str]"

    def test_type_with_only_bracket_start(
        self, validate_union_usage_module: ModuleType
    ) -> None:
        """Test handling of malformed type with only opening bracket."""
        UnionPattern = validate_union_usage_module.UnionPattern
        UnionLegitimacyValidator = validate_union_usage_module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        # Malformed type (edge case)
        pattern = UnionPattern(
            ["dict[", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        file_content = """
class MyModel(BaseModel):
    value: Union[dict, str, int]
    value_type: Literal["dict", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        # split("[")[0] should give "dict"
        assert result is True, "Should handle malformed bracketed types"
