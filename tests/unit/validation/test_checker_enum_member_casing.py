"""
Comprehensive tests for checker_enum_member_casing module.

Tests all aspects of the enum member casing checker including:
- UPPER_SNAKE_CASE validation for enum members
- Enum class detection (Enum, IntEnum, StrEnum, custom subclasses)
- Private and dunder member handling
- File and directory validation
- CLI entry point and exit codes
- Edge cases and error conditions

Ticket: OMN-1226
"""

import ast
import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.validation.checker_enum_member_casing import (
    ENUM_BASE_NAMES,
    UPPER_SNAKE_CASE_PATTERN,
    MemberCasingChecker,
    main,
    suggest_upper_snake_case,
    validate_directory,
    validate_file,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_enums_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for enum files."""
    enums_dir = tmp_path / "enums"
    enums_dir.mkdir(parents=True)
    return enums_dir


@pytest.fixture
def valid_enum_file(temp_enums_dir: Path) -> Path:
    """Create a valid enum file with proper UPPER_SNAKE_CASE members."""
    file_path = temp_enums_dir / "enum_valid.py"
    file_path.write_text(
        """
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_REVIEW = "pending_review"
"""
    )
    return file_path


@pytest.fixture
def invalid_enum_file(temp_enums_dir: Path) -> Path:
    """Create an invalid enum file with lowercase members."""
    file_path = temp_enums_dir / "enum_invalid.py"
    file_path.write_text(
        """
from enum import Enum

class Status(Enum):
    active = "active"
    inactive = "inactive"
"""
    )
    return file_path


# =============================================================================
# Tests for UPPER_SNAKE_CASE_PATTERN constant
# =============================================================================


@pytest.mark.unit
class TestUpperSnakeCasePattern:
    """Test the UPPER_SNAKE_CASE regex pattern."""

    @pytest.mark.parametrize(
        "name",
        [
            "ACTIVE",
            "HTTP_2",
            "V1_BETA",
            "SHA256",
            "SOME_LONG_NAME",
            "A",
            "AB",
            "A1",
            "HTTP2",
            "STATUS_CODE_200",
            "X509_CERTIFICATE",
        ],
    )
    def test_valid_upper_snake_case_passes(self, name: str) -> None:
        """Test valid UPPER_SNAKE_CASE names match the pattern."""
        assert UPPER_SNAKE_CASE_PATTERN.match(name) is not None

    @pytest.mark.parametrize(
        "name",
        [
            "active",
            "status",
            "pending_review",
            "some_value",
        ],
    )
    def test_lowercase_names_rejected(self, name: str) -> None:
        """Test lowercase names do not match the pattern."""
        assert UPPER_SNAKE_CASE_PATTERN.match(name) is None

    @pytest.mark.parametrize(
        "name",
        [
            "Active",
            "someValue",
            "camelCase",
            "PascalCase",
            "Mixed_Case",
            "active_STATUS",
            "STATUS_active",
        ],
    )
    def test_mixed_case_rejected(self, name: str) -> None:
        """Test mixed case names do not match the pattern."""
        assert UPPER_SNAKE_CASE_PATTERN.match(name) is None

    def test_trailing_underscore_rejected(self) -> None:
        """Test names ending with underscore are rejected.

        The pattern ^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$ requires underscore groups
        to be followed by at least one alphanumeric character.
        """
        assert UPPER_SNAKE_CASE_PATTERN.match("HTTP_") is None
        assert UPPER_SNAKE_CASE_PATTERN.match("STATUS__") is None
        assert UPPER_SNAKE_CASE_PATTERN.match("ACTIVE_") is None

    def test_leading_underscore_rejected(self) -> None:
        """Test names starting with underscore do not match (not uppercase start)."""
        assert UPPER_SNAKE_CASE_PATTERN.match("_PRIVATE") is None
        assert UPPER_SNAKE_CASE_PATTERN.match("__DUNDER__") is None

    def test_single_lowercase_letter_rejected(self) -> None:
        """Test single lowercase letter does not match."""
        assert UPPER_SNAKE_CASE_PATTERN.match("a") is None

    def test_numbers_only_rejected(self) -> None:
        """Test pure numbers do not match (must start with uppercase letter)."""
        assert UPPER_SNAKE_CASE_PATTERN.match("123") is None
        assert UPPER_SNAKE_CASE_PATTERN.match("2XX") is None


# =============================================================================
# Tests for ENUM_BASE_NAMES constant
# =============================================================================


@pytest.mark.unit
class TestEnumBaseNames:
    """Test the ENUM_BASE_NAMES constant."""

    def test_contains_expected_bases(self) -> None:
        """Test all expected enum bases are included."""
        expected = {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"}
        assert expected == ENUM_BASE_NAMES

    def test_is_frozen_set(self) -> None:
        """Test ENUM_BASE_NAMES is a frozenset."""
        assert isinstance(ENUM_BASE_NAMES, frozenset)


# =============================================================================
# Tests for suggest_upper_snake_case function
# =============================================================================


@pytest.mark.unit
class TestSuggestUpperSnakeCase:
    """Tests for the suggest_upper_snake_case conversion function.

    This function converts various naming conventions to UPPER_SNAKE_CASE
    and is used in error messages to suggest corrections.
    """

    # -------------------------------------------------------------------------
    # Docstring examples (must pass as documented)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("active", "ACTIVE"),
            ("someValue", "SOME_VALUE"),
            ("HTTPResponse", "HTTP_RESPONSE"),
        ],
    )
    def test_docstring_examples(self, input_name: str, expected: str) -> None:
        """Test examples from the function docstring."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Simple lowercase conversion
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("active", "ACTIVE"),
            ("status", "STATUS"),
            ("pending", "PENDING"),
            ("value", "VALUE"),
        ],
    )
    def test_simple_lowercase(self, input_name: str, expected: str) -> None:
        """Test conversion of simple lowercase names."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # camelCase conversion
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("someValue", "SOME_VALUE"),
            ("camelCase", "CAMEL_CASE"),
            ("myLongVariableName", "MY_LONG_VARIABLE_NAME"),
            ("getValue", "GET_VALUE"),
            ("isActive", "IS_ACTIVE"),
        ],
    )
    def test_camel_case(self, input_name: str, expected: str) -> None:
        """Test conversion of camelCase names."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # PascalCase conversion
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("SomeValue", "SOME_VALUE"),
            ("PascalCase", "PASCAL_CASE"),
            ("MyClassName", "MY_CLASS_NAME"),
            ("Status", "STATUS"),
        ],
    )
    def test_pascal_case(self, input_name: str, expected: str) -> None:
        """Test conversion of PascalCase names."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Acronym handling
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("HTTPResponse", "HTTP_RESPONSE"),
            ("XMLParser", "XML_PARSER"),
            ("URLConnection", "URL_CONNECTION"),
            ("SSLContext", "SSL_CONTEXT"),
            ("IOError", "IO_ERROR"),
            ("HTMLElement", "HTML_ELEMENT"),
            ("JSONData", "JSON_DATA"),
        ],
    )
    def test_acronym_handling(self, input_name: str, expected: str) -> None:
        """Test conversion of names containing acronyms.

        The function detects acronym boundaries by finding uppercase letters
        followed by lowercase letters after a sequence of uppercase letters.
        """
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Already correct (UPPER_SNAKE_CASE passthrough)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "name",
        [
            "ALREADY_CORRECT",
            "UPPER_SNAKE_CASE",
            "HTTP_RESPONSE",
            "SOME_VALUE",
            "A",
            "AB",
            "ABC",
            "STATUS",
            "HTTP_2",
            "V1",
        ],
    )
    def test_already_upper_snake_case(self, name: str) -> None:
        """Test that already correct UPPER_SNAKE_CASE names pass through unchanged."""
        assert suggest_upper_snake_case(name) == name

    # -------------------------------------------------------------------------
    # Empty string edge case
    # -------------------------------------------------------------------------

    def test_empty_string(self) -> None:
        """Test that empty string returns empty string."""
        assert suggest_upper_snake_case("") == ""

    # -------------------------------------------------------------------------
    # Single character edge cases
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("a", "A"),
            ("A", "A"),
            ("z", "Z"),
            ("Z", "Z"),
        ],
    )
    def test_single_letter(self, input_name: str, expected: str) -> None:
        """Test conversion of single letters."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Numbers in names
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("HTTP2", "HTTP2"),
            ("http2", "HTTP2"),
            ("SHA256", "SHA256"),
            ("sha256", "SHA256"),
            ("V1", "V1"),
            ("v1", "V1"),
            ("status200", "STATUS200"),
            ("error404", "ERROR404"),
        ],
    )
    def test_numbers_in_names(self, input_name: str, expected: str) -> None:
        """Test conversion of names containing numbers.

        Numbers do not trigger underscore insertion because they are neither
        uppercase nor lowercase (isupper/islower both return False).
        """
        assert suggest_upper_snake_case(input_name) == expected

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            # Numbers do not trigger underscore insertion - digits are neither
            # isupper() nor islower(), so they don't satisfy the conditions for
            # inserting an underscore before the following uppercase letter.
            ("V1Beta", "V1BETA"),
            ("HTTP2Response", "HTTP2RESPONSE"),
            ("SHA256Hash", "SHA256HASH"),
        ],
    )
    def test_numbers_followed_by_pascal_case(
        self, input_name: str, expected: str
    ) -> None:
        """Test names with numbers followed by PascalCase word.

        Note: The function does NOT insert underscores after digits because
        digits are neither uppercase nor lowercase (isupper/islower return
        False), so the underscore insertion conditions are not met.
        """
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Leading underscore handling
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("_private", "PRIVATE"),
            ("_value", "VALUE"),
            ("_someValue", "SOME_VALUE"),
        ],
    )
    def test_leading_underscore_stripped(self, input_name: str, expected: str) -> None:
        """Test that leading underscores are stripped from the result."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Trailing underscore handling
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("value_", "VALUE"),
            ("status_", "STATUS"),
            ("someValue_", "SOME_VALUE"),
        ],
    )
    def test_trailing_underscore_stripped(self, input_name: str, expected: str) -> None:
        """Test that trailing underscores are stripped from the result."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Dunder name handling
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("__dunder__", "DUNDER"),
            ("__init__", "INIT"),
            ("__name__", "NAME"),
        ],
    )
    def test_dunder_names(self, input_name: str, expected: str) -> None:
        """Test that dunder names have leading/trailing underscores stripped."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Multiple underscore cleanup
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("some__value", "SOME_VALUE"),
            ("a___b", "A_B"),
            ("ALREADY__DOUBLE", "ALREADY_DOUBLE"),
            ("multi____underscore", "MULTI_UNDERSCORE"),
        ],
    )
    def test_multiple_underscores_collapsed(
        self, input_name: str, expected: str
    ) -> None:
        """Test that multiple consecutive underscores are collapsed to single."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Mixed case with underscores
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("some_Value", "SOME_VALUE"),
            ("Some_value", "SOME_VALUE"),
            ("SOME_value", "SOME_VALUE"),
            ("some_VALUE", "SOME_VALUE"),
        ],
    )
    def test_mixed_case_with_underscores(self, input_name: str, expected: str) -> None:
        """Test conversion of mixed case names that already contain underscores."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # Complex mixed patterns
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("getHTTPResponseCode", "GET_HTTP_RESPONSE_CODE"),
            ("parseXMLDocument", "PARSE_XML_DOCUMENT"),
            ("loadURLFromAPI", "LOAD_URL_FROM_API"),
            ("handleIOException", "HANDLE_IO_EXCEPTION"),
        ],
    )
    def test_complex_mixed_patterns(self, input_name: str, expected: str) -> None:
        """Test conversion of complex patterns mixing camelCase and acronyms."""
        assert suggest_upper_snake_case(input_name) == expected

    # -------------------------------------------------------------------------
    # All uppercase input
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "name",
        [
            "HTTP",
            "URL",
            "API",
            "XML",
            "JSON",
            "HTML",
            "CSS",
        ],
    )
    def test_all_uppercase_no_change(self, name: str) -> None:
        """Test that all-uppercase acronyms remain unchanged."""
        assert suggest_upper_snake_case(name) == name


# =============================================================================
# Tests for MemberCasingChecker class
# =============================================================================


@pytest.mark.unit
class TestMemberCasingCheckerInit:
    """Tests for MemberCasingChecker initialization."""

    def test_init_sets_file_path(self) -> None:
        """Test __init__ correctly sets file_path."""
        checker = MemberCasingChecker("test.py")
        assert checker.file_path == "test.py"

    def test_init_creates_empty_issues_list(self) -> None:
        """Test __init__ creates empty issues list."""
        checker = MemberCasingChecker("test.py")
        assert checker.issues == []

    def test_init_with_absolute_path(self) -> None:
        """Test __init__ with absolute path."""
        checker = MemberCasingChecker("/home/user/project/src/enum.py")
        assert checker.file_path == "/home/user/project/src/enum.py"


@pytest.mark.unit
class TestMemberCasingCheckerValidNames:
    """Tests for valid UPPER_SNAKE_CASE enum members."""

    @pytest.mark.parametrize(
        "member_name",
        [
            "ACTIVE",
            "HTTP_2",
            "V1_BETA",
            "SHA256",
            "SOME_LONG_NAME",
            "STATUS_CODE_200",
        ],
    )
    def test_valid_upper_snake_case_passes(self, member_name: str) -> None:
        """Test valid UPPER_SNAKE_CASE enum members pass."""
        source = f"""
from enum import Enum

class Status(Enum):
    {member_name} = "value"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_multiple_valid_members(self) -> None:
        """Test multiple valid enum members pass."""
        source = """
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_single_letter_uppercase_valid(self) -> None:
        """Test single uppercase letter is valid."""
        source = """
from enum import Enum

class Letter(Enum):
    A = 1
    B = 2
    X = 24
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0


@pytest.mark.unit
class TestMemberCasingCheckerInvalidNames:
    """Tests for invalid enum member names."""

    @pytest.mark.parametrize(
        "member_name",
        [
            "active",
            "status",
            "pending_review",
        ],
    )
    def test_lowercase_names_rejected(self, member_name: str) -> None:
        """Test lowercase enum member names are flagged."""
        source = f"""
from enum import Enum

class Status(Enum):
    {member_name} = "value"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert member_name in checker.issues[0]
        assert "UPPER_SNAKE_CASE" in checker.issues[0]

    @pytest.mark.parametrize(
        "member_name",
        [
            "Active",
            "someValue",
            "camelCase",
            "PascalCase",
        ],
    )
    def test_mixed_case_rejected(self, member_name: str) -> None:
        """Test mixed case enum member names are flagged."""
        source = f"""
from enum import Enum

class Status(Enum):
    {member_name} = "value"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert member_name in checker.issues[0]

    def test_single_lowercase_letter_rejected(self) -> None:
        """Test single lowercase letter is flagged."""
        source = """
from enum import Enum

class Letter(Enum):
    a = 1
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "a" in checker.issues[0]

    def test_multiple_invalid_members_all_flagged(self) -> None:
        """Test all invalid members in a class are flagged."""
        source = """
from enum import Enum

class Status(Enum):
    active = "active"
    inactive = "inactive"
    VALID = "valid"
    camelCase = "camel"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # Should flag: active, inactive, camelCase (3 issues)
        assert len(checker.issues) == 3


@pytest.mark.unit
class TestMemberCasingCheckerIgnoredMembers:
    """Tests for members that should be ignored (dunder, private)."""

    def test_dunder_members_ignored(self) -> None:
        """Test dunder members (__name__, __init__) are ignored."""
        source = """
from enum import Enum

class Status(Enum):
    __name__ = "Status"
    __init__ = None
    ACTIVE = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # Only ACTIVE should be checked and it's valid
        assert len(checker.issues) == 0

    def test_private_members_ignored(self) -> None:
        """Test private members (_private) are ignored."""
        source = """
from enum import Enum

class Status(Enum):
    _private = "private"
    _internal_value = 42
    ACTIVE = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # _private and _internal_value should be ignored
        assert len(checker.issues) == 0

    def test_single_underscore_prefix_ignored(self) -> None:
        """Test members with single underscore prefix are ignored."""
        source = """
from enum import Enum

class Status(Enum):
    _value = 1
    ACTIVE = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0


@pytest.mark.unit
class TestMemberCasingCheckerEnumDetection:
    """Tests for enum class detection."""

    def test_detects_enum_subclass(self) -> None:
        """Test detection of direct Enum subclass."""
        source = """
from enum import Enum

class Status(Enum):
    active = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1

    def test_detects_str_enum_mixin(self) -> None:
        """Test detection of str, Enum mixin pattern."""
        source = """
from enum import Enum

class Status(str, Enum):
    active = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1

    def test_detects_int_enum(self) -> None:
        """Test detection of IntEnum subclass."""
        source = """
from enum import IntEnum

class Priority(IntEnum):
    high = 1
    low = 2
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 2

    def test_detects_str_enum(self) -> None:
        """Test detection of StrEnum subclass."""
        source = """
from enum import StrEnum

class Color(StrEnum):
    red = "red"
    blue = "blue"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 2

    def test_detects_flag(self) -> None:
        """Test detection of Flag subclass."""
        source = """
from enum import Flag

class Permission(Flag):
    read = 1
    write = 2
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 2

    def test_detects_int_flag(self) -> None:
        """Test detection of IntFlag subclass."""
        source = """
from enum import IntFlag

class Permission(IntFlag):
    read = 1
    write = 2
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 2

    def test_detects_custom_enum_subclass(self) -> None:
        """Test detection of custom enum subclass (ends with Enum)."""
        source = """
class MyCustomEnum:
    pass

class Status(MyCustomEnum):
    active = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # MyCustomEnum ends with "Enum", so Status should be checked
        assert len(checker.issues) == 1

    def test_ignores_non_enum_class(self) -> None:
        """Test non-enum classes are ignored."""
        source = """
class RegularClass:
    active = "active"
    camelCase = "value"

class AnotherClass(object):
    lower_case = "value"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # Regular classes should not be checked
        assert len(checker.issues) == 0

    def test_ignores_class_with_similar_base_name(self) -> None:
        """Test class with base that doesn't end in Enum is ignored."""
        source = """
class MyEnumerator:
    pass

class Status(MyEnumerator):
    active = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # MyEnumerator doesn't end with "Enum", should be ignored
        assert len(checker.issues) == 0

    def test_detects_enum_via_attribute_access(self) -> None:
        """Test detection of enum via attribute access (enum.Enum)."""
        source = """
import enum

class Status(enum.Enum):
    active = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1


@pytest.mark.unit
class TestMemberCasingCheckerNestedClasses:
    """Tests for nested enum classes."""

    def test_nested_enum_checked(self) -> None:
        """Test nested enum classes are checked."""
        source = """
from enum import Enum

class Outer:
    class Inner(Enum):
        active = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "Inner" in checker.issues[0]

    def test_deeply_nested_enum_checked(self) -> None:
        """Test deeply nested enum classes are checked."""
        source = """
from enum import Enum

class Level1:
    class Level2:
        class Level3(Enum):
            invalid = "value"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "Level3" in checker.issues[0]


@pytest.mark.unit
class TestMemberCasingCheckerNonMemberStatements:
    """Tests for non-member statements in enum classes."""

    def test_method_definitions_ignored(self) -> None:
        """Test method definitions in enum class are ignored."""
        source = """
from enum import Enum

class Status(Enum):
    ACTIVE = "active"

    def describe(self):
        return self.value
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_class_method_ignored(self) -> None:
        """Test class methods in enum class are ignored."""
        source = """
from enum import Enum

class Status(Enum):
    ACTIVE = "active"

    @classmethod
    def fromString(cls, value):
        pass
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_docstring_ignored(self) -> None:
        """Test docstrings in enum class are ignored."""
        source = '''
from enum import Enum

class Status(Enum):
    """This is a docstring."""
    ACTIVE = "active"
'''
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_annotation_without_assignment_ignored(self) -> None:
        """Test type annotations without assignment are ignored."""
        source = """
from enum import Enum

class Status(Enum):
    value: str
    ACTIVE = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_tuple_unpacking_ignored(self) -> None:
        """Test tuple unpacking assignments are ignored."""
        source = """
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    a, b = 1, 2  # Not an enum member pattern
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0


@pytest.mark.unit
class TestMemberCasingCheckerLineNumbers:
    """Tests for line number reporting in issues."""

    def test_line_numbers_in_issues(self) -> None:
        """Test line numbers are correctly reported in issues."""
        source = """
from enum import Enum

class Status(Enum):
    active = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        # active is on line 5
        assert ":5:" in checker.issues[0]

    def test_multiple_issues_different_lines(self) -> None:
        """Test multiple issues report correct line numbers."""
        source = """
from enum import Enum

class Status(Enum):
    first = 1
    VALID = 2
    second = 3
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 2
        # first on line 5, second on line 7
        assert any(":5:" in issue for issue in checker.issues)
        assert any(":7:" in issue for issue in checker.issues)


# =============================================================================
# Tests for _is_enum_class method
# =============================================================================


@pytest.mark.unit
class TestIsEnumClass:
    """Tests for the _is_enum_class method."""

    def test_returns_true_for_enum_base(self) -> None:
        """Test returns True when base is Enum."""
        source = """
from enum import Enum

class Status(Enum):
    pass
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        class_def = tree.body[1]  # Second statement is the class
        assert checker._is_enum_class(class_def) is True

    def test_returns_false_for_non_enum_base(self) -> None:
        """Test returns False when base is not an enum."""
        source = """
class Status(object):
    pass
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        class_def = tree.body[0]
        assert checker._is_enum_class(class_def) is False

    def test_returns_false_for_no_bases(self) -> None:
        """Test returns False when class has no bases."""
        source = """
class Status:
    pass
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        class_def = tree.body[0]
        assert checker._is_enum_class(class_def) is False


# =============================================================================
# Tests for _extract_base_name method
# =============================================================================


@pytest.mark.unit
class TestExtractBaseName:
    """Tests for the _extract_base_name method."""

    def test_extracts_simple_name(self) -> None:
        """Test extraction of simple Name node."""
        source = """
class Status(Enum):
    pass
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        class_def = tree.body[0]
        base = class_def.bases[0]
        assert checker._extract_base_name(base) == "Enum"

    def test_extracts_attribute_name(self) -> None:
        """Test extraction of Attribute node (enum.Enum)."""
        source = """
import enum

class Status(enum.Enum):
    pass
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        class_def = tree.body[1]
        base = class_def.bases[0]
        assert checker._extract_base_name(base) == "Enum"

    def test_returns_none_for_unsupported_expression(self) -> None:
        """Test returns None for unsupported expressions."""
        source = """
class Status(get_base_class()):
    pass
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        class_def = tree.body[0]
        base = class_def.bases[0]  # This is a Call node
        assert checker._extract_base_name(base) is None


# =============================================================================
# Tests for _is_enum_member method
# =============================================================================


@pytest.mark.unit
class TestIsEnumMember:
    """Tests for the _is_enum_member method."""

    def test_simple_assignment_is_member(self) -> None:
        """Test simple assignment is detected as member."""
        source = """
ACTIVE = "active"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        stmt = tree.body[0]
        is_member, name, line = checker._is_enum_member(stmt)
        assert is_member is True
        assert name == "ACTIVE"
        assert line == 2

    def test_function_def_not_member(self) -> None:
        """Test function definition is not a member."""
        source = """
def method():
    pass
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        stmt = tree.body[0]
        is_member, _name, _line = checker._is_enum_member(stmt)
        assert is_member is False
        assert _name is None

    def test_dunder_not_member(self) -> None:
        """Test dunder assignment is not a member."""
        source = """
__name__ = "test"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        stmt = tree.body[0]
        is_member, _name, _line = checker._is_enum_member(stmt)
        assert is_member is False

    def test_private_not_member(self) -> None:
        """Test private assignment is not a member."""
        source = """
_private = "test"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        stmt = tree.body[0]
        is_member, _name, _line = checker._is_enum_member(stmt)
        assert is_member is False

    def test_multiple_targets_not_member(self) -> None:
        """Test multiple target assignment is not a member."""
        source = """
a = b = 1
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        stmt = tree.body[0]
        is_member, _name, _line = checker._is_enum_member(stmt)
        # This has two targets [a, b], so it should not be a member
        # Actually, a = b = 1 creates an Assign with targets [a, b]
        # The check is len(targets) != 1, so this should fail
        assert is_member is False

    def test_tuple_target_not_member(self) -> None:
        """Test tuple target assignment is not a member."""
        source = """
a, b = 1, 2
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        stmt = tree.body[0]
        is_member, _name, _line = checker._is_enum_member(stmt)
        assert is_member is False


# =============================================================================
# Tests for validate_file function
# =============================================================================


@pytest.mark.unit
class TestValidateFile:
    """Tests for the validate_file function."""

    def test_returns_empty_for_valid_file(self, valid_enum_file: Path) -> None:
        """Test validate_file returns empty list for valid file."""
        issues = validate_file(valid_enum_file)
        assert issues == []

    def test_returns_issues_for_invalid_file(self, invalid_enum_file: Path) -> None:
        """Test validate_file returns issues for invalid file."""
        issues = validate_file(invalid_enum_file)
        assert len(issues) == 2
        assert any("active" in issue for issue in issues)
        assert any("inactive" in issue for issue in issues)

    def test_handles_syntax_error(self, temp_enums_dir: Path) -> None:
        """Test validate_file handles syntax errors gracefully."""
        syntax_error_file = temp_enums_dir / "enum_syntax_error.py"
        syntax_error_file.write_text("class Status(Enum:\n  invalid syntax here")
        issues = validate_file(syntax_error_file)
        # Should return empty list on syntax error (logged as warning)
        assert issues == []

    def test_handles_missing_file(self, temp_enums_dir: Path) -> None:
        """Test validate_file handles missing file gracefully."""
        missing_file = temp_enums_dir / "nonexistent.py"
        issues = validate_file(missing_file)
        # Should return empty list on missing file (logged as warning)
        assert issues == []

    def test_handles_unicode_decode_error(self, temp_enums_dir: Path) -> None:
        """Test validate_file handles encoding errors gracefully."""
        binary_file = temp_enums_dir / "enum_binary.py"
        binary_file.write_bytes(b"\xff\xfe\x00\x00invalid utf-8")
        issues = validate_file(binary_file)
        # Should return empty list on decode error
        assert issues == []

    def test_returns_file_path_in_issues(self, invalid_enum_file: Path) -> None:
        """Test issues include the file path."""
        issues = validate_file(invalid_enum_file)
        assert all(str(invalid_enum_file) in issue for issue in issues)


# =============================================================================
# Tests for validate_directory function
# =============================================================================


@pytest.mark.unit
class TestValidateDirectory:
    """Tests for the validate_directory function."""

    def test_empty_directory(self, temp_enums_dir: Path) -> None:
        """Test empty directory returns no issues."""
        issues = validate_directory(temp_enums_dir)
        assert issues == []

    def test_finds_all_issues(self, temp_enums_dir: Path) -> None:
        """Test validate_directory finds issues in all files."""
        # Create multiple files with issues
        (temp_enums_dir / "enum_a.py").write_text(
            """
from enum import Enum
class A(Enum):
    invalid = 1
"""
        )
        (temp_enums_dir / "enum_b.py").write_text(
            """
from enum import Enum
class B(Enum):
    alsoInvalid = 2
"""
        )

        issues = validate_directory(temp_enums_dir)
        assert len(issues) == 2

    def test_skips_symlinks(self, temp_enums_dir: Path) -> None:
        """Test validate_directory skips symbolic links."""
        # Create a valid file
        valid_file = temp_enums_dir / "enum_valid.py"
        valid_file.write_text(
            """
from enum import Enum
class Valid(Enum):
    VALID = 1
"""
        )

        # Create a symlink to it
        symlink = temp_enums_dir / "enum_link.py"
        try:
            symlink.symlink_to(valid_file)
        except OSError:
            # Skip test on systems that don't support symlinks (e.g., Windows without admin)
            pytest.skip("System does not support symlinks")

        issues = validate_directory(temp_enums_dir)
        # Should not process symlink, so still no issues
        assert issues == []

    def test_recursive_validation(self, temp_enums_dir: Path) -> None:
        """Test validate_directory recursively checks subdirectories."""
        subdir = temp_enums_dir / "subdir"
        subdir.mkdir()
        (subdir / "enum_nested.py").write_text(
            """
from enum import Enum
class Nested(Enum):
    invalid = 1
"""
        )

        issues = validate_directory(temp_enums_dir)
        assert len(issues) == 1
        assert "subdir" in issues[0]

    def test_verbose_mode(
        self, temp_enums_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test verbose mode logs checked files."""
        (temp_enums_dir / "enum_test.py").write_text(
            """
from enum import Enum
class Test(Enum):
    VALID = 1
"""
        )

        with caplog.at_level(logging.DEBUG):
            validate_directory(temp_enums_dir, verbose=True)

        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1
        assert any("Checking:" in r.message for r in debug_records)

    def test_skips_non_python_files(self, temp_enums_dir: Path) -> None:
        """Test non-Python files are skipped."""
        (temp_enums_dir / "not_python.txt").write_text("active = 1")
        (temp_enums_dir / "config.yaml").write_text("key: value")

        issues = validate_directory(temp_enums_dir)
        assert issues == []


# =============================================================================
# Tests for main function (CLI)
# =============================================================================


@pytest.mark.unit
class TestMainFunction:
    """Tests for the main CLI entry point."""

    def test_returns_zero_on_success(self, valid_enum_file: Path) -> None:
        """Test main returns 0 when all files are valid."""
        with patch.object(sys, "argv", ["checker", str(valid_enum_file)]):
            result = main()
            assert result == 0

    def test_returns_one_on_violations(self, invalid_enum_file: Path) -> None:
        """Test main returns 1 when violations found."""
        with patch.object(sys, "argv", ["checker", str(invalid_enum_file)]):
            result = main()
            assert result == 1

    def test_multiple_files(
        self, valid_enum_file: Path, invalid_enum_file: Path
    ) -> None:
        """Test main handles multiple file arguments."""
        with patch.object(
            sys,
            "argv",
            ["checker", str(valid_enum_file), str(invalid_enum_file)],
        ):
            result = main()
            assert result == 1  # Has violations

    def test_directory_mode(self, temp_enums_dir: Path) -> None:
        """Test main with --directory flag."""
        (temp_enums_dir / "enum_valid.py").write_text(
            """
from enum import Enum
class Valid(Enum):
    VALID = 1
"""
        )

        with patch.object(sys, "argv", ["checker", "--directory", str(temp_enums_dir)]):
            result = main()
            assert result == 0

    def test_directory_mode_with_violations(self, temp_enums_dir: Path) -> None:
        """Test main with --directory flag and violations."""
        (temp_enums_dir / "enum_invalid.py").write_text(
            """
from enum import Enum
class Invalid(Enum):
    invalid = 1
"""
        )

        with patch.object(sys, "argv", ["checker", "--directory", str(temp_enums_dir)]):
            result = main()
            assert result == 1

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test main with non-existent directory."""
        nonexistent = tmp_path / "nonexistent"
        with patch.object(sys, "argv", ["checker", "--directory", str(nonexistent)]):
            result = main()
            assert result == 1

    def test_verbose_flag(self, valid_enum_file: Path) -> None:
        """Test main accepts -v flag."""
        with patch.object(sys, "argv", ["checker", "-v", str(valid_enum_file)]):
            result = main()
            assert result == 0

    def test_verbose_long_flag(self, valid_enum_file: Path) -> None:
        """Test main accepts --verbose flag."""
        with patch.object(sys, "argv", ["checker", "--verbose", str(valid_enum_file)]):
            result = main()
            assert result == 0

    def test_skips_nonexistent_files(self, tmp_path: Path) -> None:
        """Test main logs error for non-existent files."""
        nonexistent = tmp_path / "nonexistent.py"
        with patch.object(sys, "argv", ["checker", str(nonexistent)]):
            result = main()
            # Should continue without error (just logs warning)
            assert result == 0

    def test_skips_non_python_files(self, temp_enums_dir: Path) -> None:
        """Test main skips non-Python files."""
        txt_file = temp_enums_dir / "test.txt"
        txt_file.write_text("active = 1")

        with patch.object(sys, "argv", ["checker", str(txt_file)]):
            result = main()
            assert result == 0

    def test_default_directory(self) -> None:
        """Test main uses default directory when none specified."""
        with patch.object(sys, "argv", ["checker"]):
            result = main()
            # Result depends on actual codebase state
            assert result in [0, 1]

    def test_logs_violations(
        self, invalid_enum_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test main logs violation messages."""
        with patch.object(sys, "argv", ["checker", str(invalid_enum_file)]):
            main()
            captured = capsys.readouterr()
            assert "violation" in captured.err.lower()

    def test_logs_success_in_directory_mode(
        self, temp_enums_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test main logs success message in directory mode."""
        (temp_enums_dir / "enum_valid.py").write_text(
            """
from enum import Enum
class Valid(Enum):
    VALID = 1
"""
        )

        with patch.object(sys, "argv", ["checker", "--directory", str(temp_enums_dir)]):
            main()
            captured = capsys.readouterr()
            assert (
                "UPPER_SNAKE_CASE" in captured.err or "conform" in captured.err.lower()
            )


# =============================================================================
# Edge case tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_python_file(self, temp_enums_dir: Path) -> None:
        """Test empty Python files are handled."""
        empty_file = temp_enums_dir / "enum_empty.py"
        empty_file.touch()

        issues = validate_file(empty_file)
        assert issues == []

    def test_file_with_only_comments(self, temp_enums_dir: Path) -> None:
        """Test Python files with only comments are handled."""
        comment_file = temp_enums_dir / "enum_comments.py"
        comment_file.write_text("# Just a comment\n# Another comment\n")

        issues = validate_file(comment_file)
        assert issues == []

    def test_unicode_in_enum_members(self, temp_enums_dir: Path) -> None:
        """Test enums with Unicode characters in values (not names)."""
        unicode_file = temp_enums_dir / "enum_unicode.py"
        unicode_file.write_text(
            """
from enum import Enum

class Emoji(Enum):
    SMILE = "😀"
    HEART = "❤️"
""",
            encoding="utf-8",
        )

        issues = validate_file(unicode_file)
        assert issues == []

    def test_multiple_enums_in_file(self, temp_enums_dir: Path) -> None:
        """Test file with multiple enum classes."""
        multi_file = temp_enums_dir / "enum_multi.py"
        multi_file.write_text(
            """
from enum import Enum

class Status(Enum):
    ACTIVE = 1
    invalid = 2

class Priority(Enum):
    HIGH = 1
    low = 2
"""
        )

        issues = validate_file(multi_file)
        assert len(issues) == 2
        assert any("invalid" in issue for issue in issues)
        assert any("low" in issue for issue in issues)

    def test_enum_with_auto(self, temp_enums_dir: Path) -> None:
        """Test enum using auto() for values."""
        auto_file = temp_enums_dir / "enum_auto.py"
        auto_file.write_text(
            """
from enum import Enum, auto

class Status(Enum):
    ACTIVE = auto()
    INACTIVE = auto()
    invalid = auto()
"""
        )

        issues = validate_file(auto_file)
        assert len(issues) == 1
        assert "invalid" in issues[0]

    def test_checker_with_empty_file_path(self) -> None:
        """Test MemberCasingChecker with empty file path."""
        source = """
from enum import Enum

class Status(Enum):
    VALID = 1
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_enum_inheriting_from_multiple_bases(self) -> None:
        """Test enum inheriting from multiple bases."""
        source = """
from enum import Enum

class Status(str, Enum):
    active = "active"
    VALID = "valid"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "active" in checker.issues[0]

    def test_class_issue_includes_class_name(self) -> None:
        """Test issue message includes enum class name."""
        source = """
from enum import Enum

class MyEnumClass(Enum):
    invalid = 1
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "MyEnumClass" in checker.issues[0]
        assert "invalid" in checker.issues[0]

    def test_issue_format(self) -> None:
        """Test issue message format matches expected pattern."""
        source = """
from enum import Enum

class Status(Enum):
    invalid = 1
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        # Format: "file:line: Class.member violates UPPER_SNAKE_CASE: member"
        issue = checker.issues[0]
        assert "test.py:" in issue
        assert "Status.invalid" in issue
        assert "UPPER_SNAKE_CASE" in issue


@pytest.mark.unit
class TestMultipleAssignmentPatterns:
    """Tests for various assignment patterns in enum classes."""

    def test_augmented_assignment_ignored(self) -> None:
        """Test augmented assignments (+=, etc.) are not enum members."""
        source = """
from enum import Enum

class Counter(Enum):
    VALID = 1

    # This shouldn't be in an enum, but test it doesn't crash
Counter.VALID += 1  # This is outside the class
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # Only the enum class should be checked
        assert len(checker.issues) == 0

    def test_annotated_assignment_invalid_detected(self) -> None:
        """Test annotated assignment with invalid casing is detected.

        AnnAssign (x: int = 1) with a value should be checked for
        UPPER_SNAKE_CASE compliance just like regular assignments.
        """
        source = """
from enum import Enum

class Status(Enum):
    invalid: str = "invalid"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # Annotated assignments with values should be detected as members
        assert len(checker.issues) == 1
        assert "invalid" in checker.issues[0]
        assert "UPPER_SNAKE_CASE" in checker.issues[0]

    def test_annotated_assignment_valid_passes(self) -> None:
        """Test annotated assignment with valid UPPER_SNAKE_CASE passes."""
        source = """
from enum import Enum

class Status(Enum):
    ACTIVE: str = "active"
    HTTP_CODE: int = 200
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # Valid UPPER_SNAKE_CASE annotated assignments should pass
        assert len(checker.issues) == 0

    def test_annotated_assignment_private_ignored(self) -> None:
        """Test annotated assignment with private name is ignored."""
        source = """
from enum import Enum

class Status(Enum):
    _private: str = "private"
    VALID: str = "valid"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # Private annotated assignments should be ignored
        assert len(checker.issues) == 0

    def test_annotated_assignment_dunder_ignored(self) -> None:
        """Test annotated assignment with dunder name is ignored."""
        source = """
from enum import Enum

class Status(Enum):
    __dunder__: str = "dunder"
    VALID: str = "valid"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # Dunder annotated assignments should be ignored
        assert len(checker.issues) == 0

    def test_annotated_assignment_multiple_violations(self) -> None:
        """Test multiple annotated assignments with violations."""
        source = """
from enum import Enum

class Status(Enum):
    first: str = "first"
    VALID: str = "valid"
    second: int = 2
    camelCase: str = "camel"
"""
        tree = ast.parse(source)
        checker = MemberCasingChecker("test.py")
        checker.visit(tree)
        # Should detect 3 violations: first, second, camelCase
        assert len(checker.issues) == 3
        issue_text = " ".join(checker.issues)
        assert "first" in issue_text
        assert "second" in issue_text
        assert "camelCase" in issue_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
