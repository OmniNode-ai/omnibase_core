"""
Tests for checker_enum_governance module.

Tests the enum governance rules:
- E001: Enum members must use UPPER_SNAKE_CASE
- E002: Literal types should not duplicate existing enum values

Ticket: OMN-1313
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.validation.checker_enum_governance import (
    UPPER_SNAKE_CASE_PATTERN,
    GovernanceViolation,
    MemberInfo,
    check_enum_member_casing,
    check_literal_duplication,
    collect_enums_from_file,
    collect_literals_from_file,
    main,
    validate_directory,
    validate_enum_directory,
    validate_literal_usage,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_omnibase_dir(tmp_path: Path) -> Path:
    """Create a temporary directory structure mimicking omnibase_core."""
    omnibase_dir = tmp_path / "src" / "omnibase_core"
    omnibase_dir.mkdir(parents=True)
    return omnibase_dir


@pytest.fixture
def temp_enums_dir(temp_omnibase_dir: Path) -> Path:
    """Create a temporary enums directory."""
    enums_dir = temp_omnibase_dir / "enums"
    enums_dir.mkdir(parents=True)
    return enums_dir


# =============================================================================
# Tests for UPPER_SNAKE_CASE_PATTERN
# =============================================================================


@pytest.mark.unit
class TestUpperSnakeCasePattern:
    """Tests for the UPPER_SNAKE_CASE regex pattern."""

    @pytest.mark.parametrize(
        "name",
        [
            "ACTIVE",
            "PENDING",
            "HTTP_404",
            "A",
            "A1",
            "MY_ENUM_VALUE",
            "UPPER_SNAKE_CASE",
            "VALUE_123",
            "A_B_C",
        ],
    )
    def test_valid_upper_snake_case(self, name: str) -> None:
        """Test valid UPPER_SNAKE_CASE names match pattern."""
        assert UPPER_SNAKE_CASE_PATTERN.match(name) is not None

    @pytest.mark.parametrize(
        "name",
        [
            "active",
            "Active",
            "camelCase",
            "Mixed_Case",
            "TRAILING_",
            "_LEADING",
            "double__underscore",
            "123_STARTS_WITH_NUMBER",
            "",
        ],
    )
    def test_invalid_upper_snake_case(self, name: str) -> None:
        """Test invalid names do not match UPPER_SNAKE_CASE pattern."""
        assert UPPER_SNAKE_CASE_PATTERN.match(name) is None


# =============================================================================
# Tests for GovernanceViolation
# =============================================================================


@pytest.mark.unit
class TestGovernanceViolation:
    """Tests for the GovernanceViolation dataclass."""

    def test_str_format(self) -> None:
        """Test string representation format."""
        violation = GovernanceViolation(
            file_path=Path("/path/to/file.py"),
            line=42,
            rule_code="E001",
            message="Test message",
        )
        result = str(violation)
        assert "ERROR" in result
        assert "/path/to/file.py:42" in result
        assert "E001" in result
        assert "Test message" in result

    def test_warning_severity(self) -> None:
        """Test warning severity in string representation."""
        violation = GovernanceViolation(
            file_path=Path("/path/to/file.py"),
            line=10,
            rule_code="E002",
            message="Warning message",
            severity="WARNING",
        )
        result = str(violation)
        assert "WARNING" in result


# =============================================================================
# Tests for CollectorAST
# =============================================================================


@pytest.mark.unit
class TestCollectorAST:
    """Tests for the CollectorAST AST visitor."""

    def test_collects_basic_enum(self, tmp_path: Path) -> None:
        """Test collecting a basic enum class."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text("""
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
""")
        enums = collect_enums_from_file(enum_file)
        assert "EnumStatus" in enums
        assert len(enums["EnumStatus"]) == 2

    def test_collects_str_enum(self, tmp_path: Path) -> None:
        """Test collecting a str, Enum class."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text("""
from enum import Enum

class EnumNodeKind(str, Enum):
    EFFECT = "effect"
    COMPUTE = "compute"
""")
        enums = collect_enums_from_file(enum_file)
        assert "EnumNodeKind" in enums
        assert len(enums["EnumNodeKind"]) == 2

    def test_extracts_member_values(self, tmp_path: Path) -> None:
        """Test that member values are correctly extracted."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text("""
from enum import Enum

class EnumTest(Enum):
    VALUE_ONE = "value_one"
    VALUE_TWO = "value_two"
""")
        enums = collect_enums_from_file(enum_file)
        values = {m.member_value for m in enums["EnumTest"]}
        assert values == {"value_one", "value_two"}

    def test_handles_auto_values(self, tmp_path: Path) -> None:
        """Test that auto() values are handled."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text("""
from enum import Enum, auto

class EnumAuto(Enum):
    FIRST = auto()
    SECOND = auto()
""")
        enums = collect_enums_from_file(enum_file)
        assert "EnumAuto" in enums
        # auto() values should result in None member_value
        values = [m.member_value for m in enums["EnumAuto"]]
        assert all(v is None for v in values)

    def test_skips_non_enum_classes(self, tmp_path: Path) -> None:
        """Test that non-enum classes are not collected."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text("""
from enum import Enum

class NotAnEnum:
    CONSTANT = "value"

class EnumReal(Enum):
    VALUE = "value"
""")
        enums = collect_enums_from_file(enum_file)
        assert "NotAnEnum" not in enums
        assert "EnumReal" in enums

    def test_handles_syntax_error(self, tmp_path: Path) -> None:
        """Test handling of files with syntax errors."""
        enum_file = tmp_path / "bad_enum.py"
        enum_file.write_text("class Broken(")
        enums = collect_enums_from_file(enum_file)
        assert enums == {}


# =============================================================================
# Tests for LiteralCollector
# =============================================================================


@pytest.mark.unit
class TestLiteralCollector:
    """Tests for the LiteralCollector AST visitor."""

    def test_collects_literal_type(self, tmp_path: Path) -> None:
        """Test collecting Literal type definitions."""
        model_file = tmp_path / "model_test.py"
        model_file.write_text("""
from typing import Literal

StatusType = Literal["active", "inactive"]
""")
        literals = collect_literals_from_file(model_file)
        assert len(literals) == 1
        _, values = literals[0]
        assert values == {"active", "inactive"}

    def test_collects_multiple_literals(self, tmp_path: Path) -> None:
        """Test collecting multiple Literal type definitions."""
        model_file = tmp_path / "model_test.py"
        model_file.write_text("""
from typing import Literal

Status = Literal["a", "b"]
Mode = Literal["x", "y", "z"]
""")
        literals = collect_literals_from_file(model_file)
        assert len(literals) == 2

    def test_collects_single_value_literal(self, tmp_path: Path) -> None:
        """Test collecting Literal with single value."""
        model_file = tmp_path / "model_test.py"
        model_file.write_text("""
from typing import Literal

SingleValue = Literal["only"]
""")
        literals = collect_literals_from_file(model_file)
        assert len(literals) == 1
        _, values = literals[0]
        assert values == {"only"}

    def test_handles_typing_literal(self, tmp_path: Path) -> None:
        """Test handling of typing.Literal form."""
        model_file = tmp_path / "model_test.py"
        model_file.write_text("""
import typing

Status = typing.Literal["a", "b"]
""")
        literals = collect_literals_from_file(model_file)
        assert len(literals) == 1


# =============================================================================
# Tests for check_enum_member_casing
# =============================================================================


@pytest.mark.unit
class TestCheckEnumMemberCasing:
    """Tests for E001: Enum member casing validation."""

    def test_valid_upper_snake_case_members(self) -> None:
        """Test valid UPPER_SNAKE_CASE members pass."""
        members = [
            MemberInfo(
                enum_name="EnumTest",
                member_name="ACTIVE",
                member_value="active",
                file_path=Path("test.py"),
                line=10,
            ),
            MemberInfo(
                enum_name="EnumTest",
                member_name="PENDING_APPROVAL",
                member_value="pending",
                file_path=Path("test.py"),
                line=11,
            ),
        ]
        violations = check_enum_member_casing(members)
        assert len(violations) == 0

    def test_invalid_lowercase_member(self) -> None:
        """Test lowercase members are flagged."""
        members = [
            MemberInfo(
                enum_name="EnumTest",
                member_name="active",
                member_value="active",
                file_path=Path("test.py"),
                line=10,
            ),
        ]
        violations = check_enum_member_casing(members)
        assert len(violations) == 1
        assert violations[0].rule_code == "E001"
        assert "UPPER_SNAKE_CASE" in violations[0].message

    def test_invalid_mixed_case_member(self) -> None:
        """Test mixed case members are flagged."""
        members = [
            MemberInfo(
                enum_name="EnumTest",
                member_name="Active",
                member_value="active",
                file_path=Path("test.py"),
                line=10,
            ),
        ]
        violations = check_enum_member_casing(members)
        assert len(violations) == 1

    def test_skips_private_members(self) -> None:
        """Test private members (starting with _) are skipped."""
        members = [
            MemberInfo(
                enum_name="EnumTest",
                member_name="_private",
                member_value="private",
                file_path=Path("test.py"),
                line=10,
            ),
        ]
        violations = check_enum_member_casing(members)
        assert len(violations) == 0

    def test_multiple_violations(self) -> None:
        """Test multiple violations are reported."""
        members = [
            MemberInfo(
                enum_name="EnumTest",
                member_name="active",
                member_value="active",
                file_path=Path("test.py"),
                line=10,
            ),
            MemberInfo(
                enum_name="EnumTest",
                member_name="Pending",
                member_value="pending",
                file_path=Path("test.py"),
                line=11,
            ),
            MemberInfo(
                enum_name="EnumTest",
                member_name="VALID",
                member_value="valid",
                file_path=Path("test.py"),
                line=12,
            ),
        ]
        violations = check_enum_member_casing(members)
        assert len(violations) == 2


# =============================================================================
# Tests for check_literal_duplication
# =============================================================================


@pytest.mark.unit
class TestCheckLiteralDuplication:
    """Tests for E002: Literal duplication detection."""

    def test_exact_match_is_error(self) -> None:
        """Test exact value match produces ERROR."""
        enum_index = {"EnumStatus": {"active", "inactive"}}
        literals = [(Path("test.py"), 10, {"active", "inactive"})]
        violations = check_literal_duplication(enum_index, literals)
        assert len(violations) == 1
        assert violations[0].severity == "ERROR"
        assert "duplicates values from enum" in violations[0].message

    def test_subset_is_warning(self) -> None:
        """Test subset match produces WARNING."""
        enum_index = {"EnumStatus": {"active", "inactive", "pending"}}
        literals = [(Path("test.py"), 10, {"active", "inactive"})]
        violations = check_literal_duplication(enum_index, literals)
        assert len(violations) == 1
        assert violations[0].severity == "WARNING"
        assert "subset of enum" in violations[0].message

    def test_no_match_is_clean(self) -> None:
        """Test no match produces no violations."""
        enum_index = {"EnumStatus": {"active", "inactive"}}
        literals = [(Path("test.py"), 10, {"running", "stopped"})]
        violations = check_literal_duplication(enum_index, literals)
        assert len(violations) == 0

    def test_single_value_subset_ignored(self) -> None:
        """Test single value subsets are ignored."""
        enum_index = {"EnumStatus": {"active", "inactive", "pending"}}
        literals = [(Path("test.py"), 10, {"active"})]
        violations = check_literal_duplication(enum_index, literals)
        # Single value subsets should not produce warnings
        assert len(violations) == 0

    def test_empty_enum_index(self) -> None:
        """Test empty enum index produces no violations."""
        enum_index: dict[str, set[str]] = {}
        literals = [(Path("test.py"), 10, {"active", "inactive"})]
        violations = check_literal_duplication(enum_index, literals)
        assert len(violations) == 0


# =============================================================================
# Tests for validate_enum_directory
# =============================================================================


@pytest.mark.unit
class TestValidateEnumDirectory:
    """Tests for validating enum files in a directory."""

    def test_valid_enums_pass(self, temp_enums_dir: Path) -> None:
        """Test valid enum files pass validation."""
        enum_file = temp_enums_dir / "enum_status.py"
        enum_file.write_text("""
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
""")
        violations, enum_index = validate_enum_directory(temp_enums_dir)
        assert len(violations) == 0
        assert "EnumStatus" in enum_index

    def test_invalid_casing_detected(self, temp_enums_dir: Path) -> None:
        """Test invalid casing is detected."""
        enum_file = temp_enums_dir / "enum_bad.py"
        enum_file.write_text("""
from enum import Enum

class EnumBad(Enum):
    active = "active"  # lowercase - violation
    INACTIVE = "inactive"  # valid
""")
        violations, _ = validate_enum_directory(temp_enums_dir)
        assert len(violations) == 1
        assert violations[0].rule_code == "E001"

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test non-existent directory returns empty results."""
        nonexistent = tmp_path / "nonexistent"
        violations, enum_index = validate_enum_directory(nonexistent)
        assert len(violations) == 0
        assert len(enum_index) == 0


# =============================================================================
# Tests for validate_literal_usage
# =============================================================================


@pytest.mark.unit
class TestValidateLiteralUsage:
    """Tests for scanning source files for Literal duplication."""

    def test_detects_duplication(self, temp_omnibase_dir: Path) -> None:
        """Test detection of Literal duplicating enum values."""
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        model_file = models_dir / "model_test.py"
        model_file.write_text("""
from typing import Literal

StatusType = Literal["active", "inactive"]
""")
        enum_index = {"EnumStatus": {"active", "inactive"}}
        violations = validate_literal_usage(temp_omnibase_dir, enum_index)
        assert len(violations) == 1
        assert violations[0].rule_code == "E002"

    def test_empty_enum_index(self, temp_omnibase_dir: Path) -> None:
        """Test empty enum index returns no violations."""
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        model_file = models_dir / "model_test.py"
        model_file.write_text("""
from typing import Literal

StatusType = Literal["active", "inactive"]
""")
        enum_index: dict[str, set[str]] = {}
        violations = validate_literal_usage(temp_omnibase_dir, enum_index)
        assert len(violations) == 0


# =============================================================================
# Tests for validate_directory
# =============================================================================


@pytest.mark.unit
class TestValidateDirectory:
    """Tests for the full directory validation."""

    def test_clean_codebase_passes(self, temp_omnibase_dir: Path) -> None:
        """Test clean codebase produces no violations."""
        enums_dir = temp_omnibase_dir / "enums"
        enums_dir.mkdir()
        enum_file = enums_dir / "enum_status.py"
        enum_file.write_text("""
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
""")
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        model_file = models_dir / "model_test.py"
        model_file.write_text("""
from typing import Literal

DifferentType = Literal["running", "stopped"]
""")
        violations = validate_directory(temp_omnibase_dir)
        assert len(violations) == 0

    def test_finds_violations(self, temp_omnibase_dir: Path) -> None:
        """Test violations are found and reported."""
        enums_dir = temp_omnibase_dir / "enums"
        enums_dir.mkdir()
        enum_file = enums_dir / "enum_status.py"
        enum_file.write_text("""
from enum import Enum

class EnumStatus(Enum):
    active = "active"  # E001: lowercase
    INACTIVE = "inactive"
""")
        violations = validate_directory(temp_omnibase_dir)
        assert len(violations) == 1
        assert violations[0].rule_code == "E001"


# =============================================================================
# Tests for main function (CLI)
# =============================================================================


@pytest.mark.unit
class TestMainFunction:
    """Tests for the CLI entry point."""

    def test_returns_zero_on_success(self, temp_omnibase_dir: Path) -> None:
        """Test main returns 0 when no violations."""
        enums_dir = temp_omnibase_dir / "enums"
        enums_dir.mkdir()
        enum_file = enums_dir / "enum_status.py"
        enum_file.write_text("""
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
""")
        with patch.object(
            sys, "argv", ["checker", str(temp_omnibase_dir), "--enums-only"]
        ):
            result = main()
            assert result == 0

    def test_returns_one_on_violations(self, temp_omnibase_dir: Path) -> None:
        """Test main returns 1 when violations found."""
        enums_dir = temp_omnibase_dir / "enums"
        enums_dir.mkdir()
        enum_file = enums_dir / "enum_bad.py"
        enum_file.write_text("""
from enum import Enum

class EnumBad(Enum):
    lowercase = "bad"  # Violation
""")
        with patch.object(
            sys, "argv", ["checker", str(temp_omnibase_dir), "--enums-only"]
        ):
            result = main()
            assert result == 1

    def test_returns_one_for_nonexistent_directory(self) -> None:
        """Test main returns 1 for non-existent directory."""
        with patch.object(sys, "argv", ["checker", "/nonexistent/path"]):
            result = main()
            assert result == 1

    def test_verbose_flag(self, temp_omnibase_dir: Path) -> None:
        """Test verbose flag is accepted."""
        enums_dir = temp_omnibase_dir / "enums"
        enums_dir.mkdir()
        enum_file = enums_dir / "enum_status.py"
        enum_file.write_text("""
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
""")
        with patch.object(
            sys, "argv", ["checker", str(temp_omnibase_dir), "--enums-only", "-v"]
        ):
            result = main()
            assert result == 0

    def test_enums_only_flag(self, temp_omnibase_dir: Path) -> None:
        """Test --enums-only flag skips Literal checking."""
        enums_dir = temp_omnibase_dir / "enums"
        enums_dir.mkdir()
        enum_file = enums_dir / "enum_status.py"
        enum_file.write_text("""
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
""")
        # Create a Literal that would be a violation
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        model_file = models_dir / "model_test.py"
        model_file.write_text("""
from typing import Literal

StatusType = Literal["active"]  # Would be duplicate
""")
        # With --enums-only, the Literal duplication should not be checked
        with patch.object(
            sys, "argv", ["checker", str(temp_omnibase_dir), "--enums-only"]
        ):
            result = main()
            assert result == 0


# =============================================================================
# Edge case tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_enum(self, tmp_path: Path) -> None:
        """Test enum with no members."""
        enum_file = tmp_path / "enum_empty.py"
        enum_file.write_text("""
from enum import Enum

class EnumEmpty(Enum):
    pass
""")
        enums = collect_enums_from_file(enum_file)
        assert "EnumEmpty" in enums
        assert len(enums["EnumEmpty"]) == 0

    def test_enum_with_methods(self, tmp_path: Path) -> None:
        """Test enum with methods (not just values)."""
        enum_file = tmp_path / "enum_methods.py"
        enum_file.write_text("""
from enum import Enum

class EnumWithMethods(Enum):
    ACTIVE = "active"

    def is_active(self) -> bool:
        return self == EnumWithMethods.ACTIVE
""")
        enums = collect_enums_from_file(enum_file)
        assert "EnumWithMethods" in enums
        assert len(enums["EnumWithMethods"]) == 1

    def test_unicode_in_enum_values(self, tmp_path: Path) -> None:
        """Test enum with Unicode values."""
        enum_file = tmp_path / "enum_unicode.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumUnicode(Enum):
    CHINESE = "chinese"
    EMOJI = "emoji"
""",
            encoding="utf-8",
        )
        enums = collect_enums_from_file(enum_file)
        assert "EnumUnicode" in enums

    def test_nested_enum_class(self, tmp_path: Path) -> None:
        """Test nested enum class inside another class."""
        enum_file = tmp_path / "enum_nested.py"
        enum_file.write_text("""
from enum import Enum

class Outer:
    class EnumInner(Enum):
        NESTED = "nested"
""")
        enums = collect_enums_from_file(enum_file)
        # Nested enums should also be collected
        assert "EnumInner" in enums


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
