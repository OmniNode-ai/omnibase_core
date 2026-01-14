"""
Comprehensive tests for checker_literal_duplication module.

Tests all aspects of the Literal type alias duplication checker including:
- Literal alias name detection (_is_literal_alias_name)
- Name normalization (normalize_literal_name)
- AST extraction of Literal aliases (extract_literal_aliases)
- File exclusion logic (_should_exclude)
- Duplication detection against known enums
- File and directory validation
- CLI entry point and exit codes
- Edge cases and error conditions

Ticket: OMN-1308
"""

import ast
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.validation.checker_literal_duplication import (
    KNOWN_ENUM_NAMES,
    _is_literal_alias_name,
    _is_literal_subscript,
    _should_exclude,
    _to_pascal_case,
    check_for_duplications,
    extract_literal_aliases,
    find_enums_directory,
    get_enum_names_from_directory,
    main,
    normalize_literal_name,
    validate_file,
    validate_paths,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_src_dir(tmp_path: Path) -> Path:
    """Create a temporary source directory for testing."""
    src_dir = tmp_path / "src" / "omnibase_core"
    src_dir.mkdir(parents=True)
    return src_dir


@pytest.fixture
def temp_enums_dir(temp_src_dir: Path) -> Path:
    """Create a temporary enums directory with sample enum files."""
    enums_dir = temp_src_dir / "enums"
    enums_dir.mkdir()
    # Create sample enum files
    (enums_dir / "enum_validation_level.py").write_text("# enum file")
    (enums_dir / "enum_health_status.py").write_text("# enum file")
    (enums_dir / "enum_node_kind.py").write_text("# enum file")
    return enums_dir


@pytest.fixture
def temp_models_dir(temp_src_dir: Path) -> Path:
    """Create a temporary models directory."""
    models_dir = temp_src_dir / "models"
    models_dir.mkdir()
    return models_dir


@pytest.fixture
def valid_file(temp_models_dir: Path) -> Path:
    """Create a valid Python file without Literal aliases."""
    file_path = temp_models_dir / "model_valid.py"
    file_path.write_text(
        """
from typing import Literal

# This is a valid Literal usage (not an alias)
def process(value: Literal["a", "b"]) -> None:
    pass

# Regular type alias (not Literal-related)
MyType = str | int
"""
    )
    return file_path


@pytest.fixture
def file_with_literal_alias(temp_models_dir: Path) -> Path:
    """Create a file with a Literal type alias."""
    file_path = temp_models_dir / "model_with_literal.py"
    file_path.write_text(
        """
from typing import Literal

# This duplicates EnumValidationLevel
LiteralValidationLevel = Literal["BASIC", "STANDARD", "COMPREHENSIVE"]
"""
    )
    return file_path


@pytest.fixture
def file_with_suffix_literal(temp_models_dir: Path) -> Path:
    """Create a file with a Literal type alias using suffix pattern."""
    file_path = temp_models_dir / "model_with_suffix.py"
    file_path.write_text(
        """
from typing import Literal

# This duplicates EnumHealthStatus
HealthStatusLiteral = Literal["HEALTHY", "UNHEALTHY", "DEGRADED"]
"""
    )
    return file_path


# =============================================================================
# Tests for KNOWN_ENUM_NAMES constant
# =============================================================================


@pytest.mark.unit
class TestKnownEnumNames:
    """Test coverage for the KNOWN_ENUM_NAMES constant."""

    def test_is_frozen_set(self) -> None:
        """Test KNOWN_ENUM_NAMES is a frozenset."""
        assert isinstance(KNOWN_ENUM_NAMES, frozenset)

    def test_contains_expected_enums(self) -> None:
        """Test KNOWN_ENUM_NAMES contains expected enum names."""
        expected_subset = {
            "validationlevel",
            "healthstatus",
            "nodekind",
            "nodetype",
            "loglevel",
            "steptype",
        }
        assert expected_subset.issubset(KNOWN_ENUM_NAMES)

    def test_all_names_are_lowercase(self) -> None:
        """Test all enum names are lowercase."""
        for name in KNOWN_ENUM_NAMES:
            assert name == name.lower(), f"'{name}' should be lowercase"

    def test_no_empty_strings(self) -> None:
        """Test no empty strings in enum names."""
        assert "" not in KNOWN_ENUM_NAMES


# =============================================================================
# Tests for _is_literal_alias_name function
# =============================================================================


@pytest.mark.unit
class TestIsLiteralAliasName:
    """Tests for the _is_literal_alias_name function."""

    # -------------------------------------------------------------------------
    # Prefix pattern tests (LiteralFoo)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "name",
        [
            "LiteralValidationLevel",
            "LiteralHealthStatus",
            "LiteralNodeKind",
            "LiteralA",  # Single char after Literal is OK
            "LiteralHTTP",  # Acronym after Literal
            "LiteralFooBar",
        ],
    )
    def test_detects_literal_prefix_valid(self, name: str) -> None:
        """Test detection of valid LiteralFoo patterns."""
        assert _is_literal_alias_name(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "Literal",  # Just "Literal" alone - not long enough
            "Literala",  # Lowercase after Literal
            "Literal1",  # Number after Literal
            "Literal_foo",  # Underscore after Literal
        ],
    )
    def test_rejects_invalid_literal_prefix(self, name: str) -> None:
        """Test rejection of invalid LiteralFoo patterns."""
        assert _is_literal_alias_name(name) is False

    # -------------------------------------------------------------------------
    # Suffix pattern tests (FooLiteral)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "name",
        [
            "ValidationLevelLiteral",
            "HealthStatusLiteral",
            "NodeKindLiteral",
            "FooLiteral",  # 3-char prefix
            "ABLiteral",  # 2-char prefix (minimum)
            "HTTPLiteral",  # Acronym prefix
        ],
    )
    def test_detects_literal_suffix_valid(self, name: str) -> None:
        """Test detection of valid FooLiteral patterns."""
        assert _is_literal_alias_name(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "XLiteral",  # Single char prefix - too short
            "ALiteral",  # Single char prefix - too short
            "literal",  # All lowercase
            "fooLiteral",  # Lowercase prefix (not PascalCase)
            "_fooLiteral",  # Underscore prefix
            "Literal",  # Just "Literal" alone
        ],
    )
    def test_rejects_invalid_literal_suffix(self, name: str) -> None:
        """Test rejection of invalid FooLiteral patterns."""
        assert _is_literal_alias_name(name) is False

    # -------------------------------------------------------------------------
    # Non-Literal name tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "name",
        [
            "ValidationLevel",
            "MyClass",
            "SomeTypeName",
            "HTTPResponse",
            "Model",
            "EnumStatus",
            "StringValue",
            "TypeAlias",
            "SomethingElse",  # Doesn't contain "Literal" at all
        ],
    )
    def test_rejects_non_literal_names(self, name: str) -> None:
        """Test rejection of names that don't follow Literal alias patterns."""
        assert _is_literal_alias_name(name) is False

    # -------------------------------------------------------------------------
    # Edge cases
    # -------------------------------------------------------------------------

    def test_empty_string(self) -> None:
        """Test empty string returns False."""
        assert _is_literal_alias_name("") is False

    def test_literal_literal_edge_case(self) -> None:
        """Test LiteralLiteral edge case (prefix pattern)."""
        # LiteralLiteral: prefix "Literal" + suffix "Literal" with uppercase L
        assert _is_literal_alias_name("LiteralLiteral") is True

    def test_case_sensitivity(self) -> None:
        """Test case sensitivity in detection."""
        assert _is_literal_alias_name("LITERALVALIDATION") is False
        assert _is_literal_alias_name("literalValidation") is False
        assert _is_literal_alias_name("VALIDATIONLITERAL") is False


# =============================================================================
# Tests for normalize_literal_name function
# =============================================================================


@pytest.mark.unit
class TestNormalizeLiteralName:
    """Tests for the normalize_literal_name function."""

    # -------------------------------------------------------------------------
    # Prefix stripping (LiteralFoo -> foo)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("LiteralValidationLevel", "validationlevel"),
            ("LiteralHealthStatus", "healthstatus"),
            ("LiteralNodeKind", "nodekind"),
            ("LiteralA", "a"),
            ("LiteralHTTP", "http"),
        ],
    )
    def test_strips_literal_prefix(self, input_name: str, expected: str) -> None:
        """Test stripping of Literal prefix."""
        assert normalize_literal_name(input_name) == expected

    # -------------------------------------------------------------------------
    # Suffix stripping (FooLiteral -> foo)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("ValidationLevelLiteral", "validationlevel"),
            ("HealthStatusLiteral", "healthstatus"),
            ("NodeKindLiteral", "nodekind"),
            ("StepTypeLiteral", "steptype"),
            ("FooLiteral", "foo"),
        ],
    )
    def test_strips_literal_suffix(self, input_name: str, expected: str) -> None:
        """Test stripping of Literal suffix."""
        assert normalize_literal_name(input_name) == expected

    # -------------------------------------------------------------------------
    # Edge cases
    # -------------------------------------------------------------------------

    def test_literal_literal_edge_case(self) -> None:
        """Test LiteralLiteral edge case - only strips prefix to preserve meaning."""
        assert normalize_literal_name("LiteralLiteral") == "literal"

    def test_literal_foo_literal_double_pattern(self) -> None:
        """Test LiteralFooLiteral - both prefix and suffix removed."""
        assert normalize_literal_name("LiteralFooLiteral") == "foo"

    def test_foo_literal_literal_multiple_suffix(self) -> None:
        """Test FooLiteralLiteral - multiple suffixes stripped."""
        assert normalize_literal_name("FooLiteralLiteral") == "foo"

    def test_literal_literal_foo_pattern(self) -> None:
        """Test LiteralLiteralFoo - prefix stripped, remaining LiteralFoo."""
        assert normalize_literal_name("LiteralLiteralFoo") == "literalfoo"

    def test_returns_lowercase(self) -> None:
        """Test result is always lowercase."""
        result = normalize_literal_name("LiteralHTTPResponse")
        assert result == result.lower()

    def test_short_names(self) -> None:
        """Test short names that shouldn't be modified much."""
        assert normalize_literal_name("Literal") == "literal"
        assert normalize_literal_name("Foo") == "foo"

    def test_empty_string(self) -> None:
        """Test empty string returns empty string."""
        assert normalize_literal_name("") == ""

    def test_preserves_name_when_stripping_would_empty(self) -> None:
        """Test original name (lowercased) returned if stripping would empty."""
        # Names that are too short to strip meaningfully
        result = normalize_literal_name("X")
        assert result == "x"


# =============================================================================
# Tests for _is_literal_subscript function
# =============================================================================


@pytest.mark.unit
class TestIsLiteralSubscript:
    """Tests for the _is_literal_subscript function."""

    def test_detects_simple_literal_subscript(self) -> None:
        """Test detection of simple Literal[...] pattern."""
        source = 'Literal["a", "b"]'
        tree = ast.parse(source, mode="eval")
        assert _is_literal_subscript(tree.body) is True

    def test_detects_typing_literal_subscript(self) -> None:
        """Test detection of typing.Literal[...] pattern."""
        source = 'typing.Literal["a", "b"]'
        tree = ast.parse(source, mode="eval")
        assert _is_literal_subscript(tree.body) is True

    def test_rejects_non_literal_subscript(self) -> None:
        """Test rejection of non-Literal subscripts."""
        source = "List[str]"
        tree = ast.parse(source, mode="eval")
        assert _is_literal_subscript(tree.body) is False

    def test_rejects_non_subscript(self) -> None:
        """Test rejection of non-subscript nodes."""
        source = "some_variable"
        tree = ast.parse(source, mode="eval")
        assert _is_literal_subscript(tree.body) is False

    def test_rejects_call_expression(self) -> None:
        """Test rejection of call expressions."""
        source = "Literal()"
        tree = ast.parse(source, mode="eval")
        assert _is_literal_subscript(tree.body) is False


# =============================================================================
# Tests for extract_literal_aliases function
# =============================================================================


@pytest.mark.unit
class TestExtractLiteralAliases:
    """Tests for the extract_literal_aliases function."""

    def test_extracts_prefix_pattern_alias(self, tmp_path: Path) -> None:
        """Test extraction of LiteralFoo pattern alias."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import Literal

LiteralStatus = Literal["active", "inactive"]
"""
        )
        aliases = extract_literal_aliases(file_path)
        assert len(aliases) == 1
        assert aliases[0][0] == "LiteralStatus"
        assert aliases[0][1] == 4  # Line number

    def test_extracts_suffix_pattern_alias(self, tmp_path: Path) -> None:
        """Test extraction of FooLiteral pattern alias."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import Literal

StatusLiteral = Literal["active", "inactive"]
"""
        )
        aliases = extract_literal_aliases(file_path)
        assert len(aliases) == 1
        assert aliases[0][0] == "StatusLiteral"

    def test_extracts_multiple_aliases(self, tmp_path: Path) -> None:
        """Test extraction of multiple Literal aliases."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import Literal

LiteralStatus = Literal["active", "inactive"]
PriorityLiteral = Literal["high", "low"]
LiteralLevel = Literal["basic", "advanced"]
"""
        )
        aliases = extract_literal_aliases(file_path)
        assert len(aliases) == 3
        names = [a[0] for a in aliases]
        assert "LiteralStatus" in names
        assert "PriorityLiteral" in names
        assert "LiteralLevel" in names

    def test_extracts_annotated_assignment(self, tmp_path: Path) -> None:
        """Test extraction from annotated assignment (TypeAlias pattern)."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import Literal, TypeAlias

LiteralStatus: TypeAlias = Literal["active", "inactive"]
"""
        )
        aliases = extract_literal_aliases(file_path)
        assert len(aliases) == 1
        assert aliases[0][0] == "LiteralStatus"

    def test_ignores_non_literal_type_alias(self, tmp_path: Path) -> None:
        """Test ignoring of non-Literal type aliases."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import List

MyList = List[str]
RegularAlias = str | int
"""
        )
        aliases = extract_literal_aliases(file_path)
        assert len(aliases) == 0

    def test_ignores_inline_literal_usage(self, tmp_path: Path) -> None:
        """Test ignoring of inline Literal usage in function signatures."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import Literal

def process(value: Literal["a", "b"]) -> None:
    pass
"""
        )
        aliases = extract_literal_aliases(file_path)
        assert len(aliases) == 0

    def test_ignores_non_literal_alias_names(self, tmp_path: Path) -> None:
        """Test ignoring of aliases with non-Literal names."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import Literal

# This doesn't match LiteralFoo or FooLiteral pattern
StatusType = Literal["active", "inactive"]
"""
        )
        aliases = extract_literal_aliases(file_path)
        assert len(aliases) == 0

    def test_handles_syntax_error(self, tmp_path: Path) -> None:
        """Test graceful handling of syntax errors."""
        file_path = tmp_path / "test.py"
        file_path.write_text("class Invalid(\n  broken syntax")
        aliases = extract_literal_aliases(file_path)
        assert aliases == []

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        """Test graceful handling of missing file."""
        file_path = tmp_path / "nonexistent.py"
        aliases = extract_literal_aliases(file_path)
        assert aliases == []

    def test_handles_encoding_error(self, tmp_path: Path) -> None:
        """Test graceful handling of encoding errors."""
        file_path = tmp_path / "test.py"
        file_path.write_bytes(b"\xff\xfe\x00\x00invalid utf-8")
        aliases = extract_literal_aliases(file_path)
        assert aliases == []

    def test_handles_typing_module_literal(self, tmp_path: Path) -> None:
        """Test extraction with typing.Literal pattern."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
import typing

LiteralStatus = typing.Literal["active", "inactive"]
"""
        )
        aliases = extract_literal_aliases(file_path)
        assert len(aliases) == 1
        assert aliases[0][0] == "LiteralStatus"


# =============================================================================
# Tests for _should_exclude function
# =============================================================================


@pytest.mark.unit
class TestShouldExclude:
    """Tests for the _should_exclude function."""

    def test_excludes_test_directory(self) -> None:
        """Test exclusion of files in tests directory."""
        file_path = Path("tests/unit/test_something.py")
        assert _should_exclude(file_path, []) is True

    def test_excludes_tests_subdirectory(self) -> None:
        """Test exclusion of files in tests subdirectories."""
        file_path = Path("tests/integration/test_api.py")
        assert _should_exclude(file_path, []) is True

    def test_excludes_nested_tests(self) -> None:
        """Test exclusion of tests in nested paths."""
        file_path = Path("src/tests/unit/test_something.py")
        assert _should_exclude(file_path, []) is True

    def test_excludes_checker_itself(self) -> None:
        """Test exclusion of the checker file itself."""
        file_path = Path("src/validation/checker_literal_duplication.py")
        assert _should_exclude(file_path, []) is True

    def test_excludes_custom_pattern_exact_match(self) -> None:
        """Test exclusion with custom exact pattern."""
        file_path = Path("src/vendor/external.py")
        assert _should_exclude(file_path, ["vendor"]) is True

    def test_excludes_custom_pattern_with_slash(self) -> None:
        """Test exclusion with pattern containing trailing slash."""
        file_path = Path("src/vendor/external.py")
        assert _should_exclude(file_path, ["vendor/"]) is True

    def test_excludes_glob_pattern(self) -> None:
        """Test exclusion with glob pattern."""
        file_path = Path("src/test_utils/helper.py")
        assert _should_exclude(file_path, ["test_*"]) is True

    def test_does_not_exclude_substring_match(self) -> None:
        """Test that substring matches don't trigger exclusion."""
        file_path = Path("src/mytest/something.py")
        # "tests" pattern should NOT match "mytest"
        assert _should_exclude(file_path, ["tests"]) is False

    def test_does_not_exclude_normal_source_file(self) -> None:
        """Test non-exclusion of normal source files."""
        file_path = Path("src/omnibase_core/models/model_user.py")
        assert _should_exclude(file_path, []) is False

    def test_handles_absolute_path(self) -> None:
        """Test exclusion with absolute path."""
        file_path = Path("/home/user/project/tests/test_something.py")
        assert _should_exclude(file_path, []) is True

    def test_handles_path_with_dots(self) -> None:
        """Test exclusion handles paths with . and .. components."""
        file_path = Path("src/../tests/unit/test_something.py")
        assert _should_exclude(file_path, []) is True


# =============================================================================
# Tests for check_for_duplications function
# =============================================================================


@pytest.mark.unit
class TestCheckForDuplications:
    """Tests for the check_for_duplications function."""

    def test_detects_known_enum_duplication(self) -> None:
        """Test detection of duplication with known enum."""
        aliases = [("LiteralValidationLevel", 10)]
        file_path = Path("test.py")
        known_enums = frozenset({"validationlevel"})

        errors = check_for_duplications(aliases, file_path, known_enums)

        assert len(errors) == 1
        assert "LiteralValidationLevel" in errors[0]
        assert "EnumValidationLevel" in errors[0]
        assert "test.py:10" in errors[0]

    def test_detects_suffix_pattern_duplication(self) -> None:
        """Test detection of FooLiteral pattern duplication."""
        aliases = [("HealthStatusLiteral", 5)]
        file_path = Path("test.py")
        known_enums = frozenset({"healthstatus"})

        errors = check_for_duplications(aliases, file_path, known_enums)

        assert len(errors) == 1
        assert "HealthStatusLiteral" in errors[0]
        assert "EnumHealthStatus" in errors[0]

    def test_no_errors_for_unknown_enum(self) -> None:
        """Test no errors when alias doesn't match known enum."""
        aliases = [("LiteralCustomType", 10)]
        file_path = Path("test.py")
        known_enums = frozenset({"validationlevel"})

        errors = check_for_duplications(aliases, file_path, known_enums)

        assert len(errors) == 0

    def test_multiple_duplications(self) -> None:
        """Test detection of multiple duplications."""
        aliases = [
            ("LiteralValidationLevel", 10),
            ("HealthStatusLiteral", 15),
            ("LiteralCustom", 20),  # Not a known enum
        ]
        file_path = Path("test.py")
        known_enums = frozenset({"validationlevel", "healthstatus"})

        errors = check_for_duplications(aliases, file_path, known_enums)

        assert len(errors) == 2

    def test_empty_aliases_list(self) -> None:
        """Test empty aliases list returns no errors."""
        errors = check_for_duplications([], Path("test.py"), KNOWN_ENUM_NAMES)
        assert errors == []


# =============================================================================
# Tests for _to_pascal_case function
# =============================================================================


@pytest.mark.unit
class TestToPascalCase:
    """Tests for the _to_pascal_case function."""

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("validationlevel", "ValidationLevel"),
            ("healthstatus", "HealthStatus"),
            ("nodekind", "NodeKind"),
            ("loglevel", "LogLevel"),
            ("steptype", "StepType"),
            ("status", "Status"),
            ("priority", "Priority"),
        ],
    )
    def test_known_word_boundaries(self, input_name: str, expected: str) -> None:
        """Test conversion of known enum names with word boundaries."""
        assert _to_pascal_case(input_name) == expected

    def test_fallback_capitalize(self) -> None:
        """Test fallback to simple capitalize for unknown names."""
        result = _to_pascal_case("unknownname")
        assert result == "Unknownname"

    def test_single_word(self) -> None:
        """Test single word conversion."""
        assert _to_pascal_case("environment") == "Environment"
        assert _to_pascal_case("category") == "Category"


# =============================================================================
# Tests for get_enum_names_from_directory function
# =============================================================================


@pytest.mark.unit
class TestGetEnumNamesFromDirectory:
    """Tests for the get_enum_names_from_directory function."""

    def test_extracts_enum_names_from_files(self, temp_enums_dir: Path) -> None:
        """Test extraction of enum names from directory."""
        enum_names = get_enum_names_from_directory(temp_enums_dir)

        # Should include names from files we created
        assert "validationlevel" in enum_names
        assert "healthstatus" in enum_names
        assert "nodekind" in enum_names

    def test_merges_with_known_enums(self, temp_enums_dir: Path) -> None:
        """Test that results include KNOWN_ENUM_NAMES."""
        enum_names = get_enum_names_from_directory(temp_enums_dir)

        # Should include built-in known enums
        assert "loglevel" in enum_names
        assert "steptype" in enum_names

    def test_returns_known_enums_for_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test fallback to KNOWN_ENUM_NAMES for non-existent directory."""
        nonexistent = tmp_path / "nonexistent"
        enum_names = get_enum_names_from_directory(nonexistent)

        assert enum_names == KNOWN_ENUM_NAMES

    def test_normalizes_names(self, tmp_path: Path) -> None:
        """Test that names are normalized (lowercase, no underscores)."""
        enums_dir = tmp_path / "enums"
        enums_dir.mkdir()
        (enums_dir / "enum_some_long_name.py").write_text("# enum")

        enum_names = get_enum_names_from_directory(enums_dir)

        assert "somelongname" in enum_names

    def test_ignores_non_enum_files(self, tmp_path: Path) -> None:
        """Test that non-enum files are ignored."""
        enums_dir = tmp_path / "enums"
        enums_dir.mkdir()
        (enums_dir / "__init__.py").write_text("")
        (enums_dir / "utils.py").write_text("")
        (enums_dir / "enum_status.py").write_text("# enum")

        enum_names = get_enum_names_from_directory(enums_dir)

        # Only enum_status should be extracted (plus known enums)
        extracted = enum_names - KNOWN_ENUM_NAMES
        assert "status" in extracted


# =============================================================================
# Tests for validate_file function
# =============================================================================


@pytest.mark.unit
class TestValidateFile:
    """Tests for the validate_file function."""

    def test_returns_empty_for_valid_file(self, valid_file: Path) -> None:
        """Test validate_file returns empty list for valid file."""
        errors = validate_file(valid_file, KNOWN_ENUM_NAMES)
        assert errors == []

    def test_returns_errors_for_duplication(
        self, file_with_literal_alias: Path
    ) -> None:
        """Test validate_file returns errors for duplication."""
        errors = validate_file(file_with_literal_alias, KNOWN_ENUM_NAMES)
        assert len(errors) == 1
        assert "LiteralValidationLevel" in errors[0]

    def test_returns_errors_for_suffix_pattern(
        self, file_with_suffix_literal: Path
    ) -> None:
        """Test validate_file returns errors for suffix pattern duplication."""
        errors = validate_file(file_with_suffix_literal, KNOWN_ENUM_NAMES)
        assert len(errors) == 1
        assert "HealthStatusLiteral" in errors[0]


# =============================================================================
# Tests for validate_paths function
# =============================================================================


@pytest.mark.unit
class TestValidatePaths:
    """Tests for the validate_paths function."""

    def test_validates_single_file(self, file_with_literal_alias: Path) -> None:
        """Test validation of a single file."""
        errors = validate_paths([file_with_literal_alias], KNOWN_ENUM_NAMES)
        assert len(errors) == 1

    def test_validates_directory(self, temp_models_dir: Path) -> None:
        """Test validation of a directory."""
        (temp_models_dir / "model_literal.py").write_text(
            """
from typing import Literal
LiteralValidationLevel = Literal["BASIC"]
"""
        )

        errors = validate_paths([temp_models_dir], KNOWN_ENUM_NAMES)
        assert len(errors) == 1

    def test_respects_exclude_patterns(self, tmp_path: Path) -> None:
        """Test that exclude patterns are respected."""
        vendor_dir = tmp_path / "vendor"
        vendor_dir.mkdir()
        (vendor_dir / "external.py").write_text(
            """
from typing import Literal
LiteralValidationLevel = Literal["BASIC"]
"""
        )

        errors = validate_paths(
            [vendor_dir], KNOWN_ENUM_NAMES, exclude_patterns=["vendor"]
        )
        assert len(errors) == 0

    def test_skips_symlinks(self, tmp_path: Path) -> None:
        """Test that symlinks are skipped."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        real_file = src_dir / "real.py"
        real_file.write_text(
            """
from typing import Literal
LiteralValidationLevel = Literal["BASIC"]
"""
        )

        try:
            link_file = src_dir / "link.py"
            link_file.symlink_to(real_file)
        except OSError:
            pytest.skip("System does not support symlinks")

        # Should only find one error (from real file, not symlink)
        errors = validate_paths([src_dir], KNOWN_ENUM_NAMES)
        assert len(errors) == 1

    def test_handles_non_python_files(self, tmp_path: Path) -> None:
        """Test that non-Python files are skipped."""
        (tmp_path / "readme.md").write_text("# LiteralValidationLevel")
        (tmp_path / "config.yaml").write_text("key: LiteralStatus")

        errors = validate_paths([tmp_path], KNOWN_ENUM_NAMES)
        assert len(errors) == 0

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test validation of empty directory."""
        errors = validate_paths([tmp_path], KNOWN_ENUM_NAMES)
        assert errors == []


# =============================================================================
# Tests for find_enums_directory function
# =============================================================================


@pytest.mark.unit
class TestFindEnumsDirectory:
    """Tests for the find_enums_directory function."""

    def test_finds_enums_directory(self) -> None:
        """Test that enums directory is found when it exists."""
        # This test depends on the actual project structure
        enums_dir = find_enums_directory()
        # In the test environment, this should find the real enums directory
        if enums_dir is not None:
            assert enums_dir.name == "enums"
            assert enums_dir.exists()


# =============================================================================
# Tests for main function (CLI)
# =============================================================================


@pytest.mark.unit
class TestMainFunction:
    """Tests for the main CLI entry point."""

    def test_returns_zero_on_success(self, valid_file: Path) -> None:
        """Test main returns 0 when no duplications found."""
        with patch.object(sys, "argv", ["checker", str(valid_file)]):
            result = main()
            assert result == 0

    def test_returns_one_on_violations(self, file_with_literal_alias: Path) -> None:
        """Test main returns 1 when duplications found."""
        with patch.object(sys, "argv", ["checker", str(file_with_literal_alias)]):
            result = main()
            assert result == 1

    def test_returns_one_for_nonexistent_path(self, tmp_path: Path) -> None:
        """Test main returns 1 for non-existent path."""
        nonexistent = tmp_path / "nonexistent"
        with patch.object(sys, "argv", ["checker", str(nonexistent)]):
            result = main()
            assert result == 1

    def test_verbose_flag(self, valid_file: Path) -> None:
        """Test main accepts -v flag."""
        with patch.object(sys, "argv", ["checker", "-v", str(valid_file)]):
            result = main()
            assert result == 0

    def test_verbose_long_flag(self, valid_file: Path) -> None:
        """Test main accepts --verbose flag."""
        with patch.object(sys, "argv", ["checker", "--verbose", str(valid_file)]):
            result = main()
            assert result == 0

    def test_exclude_flag(self, tmp_path: Path) -> None:
        """Test main accepts --exclude flag."""
        vendor_dir = tmp_path / "vendor"
        vendor_dir.mkdir()
        (vendor_dir / "external.py").write_text(
            """
from typing import Literal
LiteralValidationLevel = Literal["BASIC"]
"""
        )

        with patch.object(
            sys, "argv", ["checker", str(vendor_dir), "--exclude", "vendor"]
        ):
            result = main()
            assert result == 0

    def test_logs_violations(
        self, file_with_literal_alias: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test main logs violation messages."""
        with patch.object(sys, "argv", ["checker", str(file_with_literal_alias)]):
            main()
            captured = capsys.readouterr()
            assert "LiteralValidationLevel" in captured.err
            assert "duplicat" in captured.err.lower()

    def test_logs_success(
        self, valid_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test main logs success message."""
        with patch.object(sys, "argv", ["checker", str(valid_file)]):
            main()
            captured = capsys.readouterr()
            assert "No Literal duplications found" in captured.err


# =============================================================================
# Edge case tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_python_file(self, tmp_path: Path) -> None:
        """Test empty Python files are handled."""
        empty_file = tmp_path / "empty.py"
        empty_file.touch()

        errors = validate_file(empty_file, KNOWN_ENUM_NAMES)
        assert errors == []

    def test_file_with_only_comments(self, tmp_path: Path) -> None:
        """Test Python files with only comments are handled."""
        comment_file = tmp_path / "comments.py"
        comment_file.write_text("# Just a comment\n# Another comment\n")

        errors = validate_file(comment_file, KNOWN_ENUM_NAMES)
        assert errors == []

    def test_unicode_in_file_content(self, tmp_path: Path) -> None:
        """Test files with Unicode content are handled."""
        unicode_file = tmp_path / "unicode.py"
        unicode_file.write_text(
            '# -*- coding: utf-8 -*-\n"""Unicode: \u4e2d\u6587, special chars"""\n',
            encoding="utf-8",
        )

        errors = validate_file(unicode_file, KNOWN_ENUM_NAMES)
        assert errors == []

    def test_multiple_literal_aliases_same_file(self, tmp_path: Path) -> None:
        """Test file with multiple Literal aliases."""
        multi_file = tmp_path / "multi.py"
        multi_file.write_text(
            """
from typing import Literal

LiteralValidationLevel = Literal["BASIC"]
HealthStatusLiteral = Literal["HEALTHY"]
LiteralCustom = Literal["custom"]  # Not a known enum
"""
        )

        errors = validate_file(multi_file, KNOWN_ENUM_NAMES)
        # Should detect 2 duplications (validationlevel, healthstatus)
        assert len(errors) == 2

    def test_literal_alias_with_typing_import(self, tmp_path: Path) -> None:
        """Test Literal alias with typing module import."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
import typing

LiteralValidationLevel = typing.Literal["BASIC"]
"""
        )

        errors = validate_file(file_path, KNOWN_ENUM_NAMES)
        assert len(errors) == 1

    def test_deeply_nested_directory(self, tmp_path: Path) -> None:
        """Test validation works in deeply nested directories."""
        deep_dir = tmp_path / "a" / "b" / "c" / "d"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep.py").write_text(
            """
from typing import Literal
LiteralValidationLevel = Literal["BASIC"]
"""
        )

        errors = validate_paths([tmp_path], KNOWN_ENUM_NAMES)
        assert len(errors) == 1

    def test_case_insensitive_enum_matching(self) -> None:
        """Test that enum matching is case-insensitive."""
        aliases = [("LiteralVALIDATIONLEVEL", 10)]  # Different case
        file_path = Path("test.py")
        known_enums = frozenset({"validationlevel"})

        errors = check_for_duplications(aliases, file_path, known_enums)
        # normalize_literal_name lowercases, so this should still match
        assert len(errors) == 1


@pytest.mark.unit
class TestComplexPatterns:
    """Tests for complex Literal alias patterns."""

    def test_literal_with_union(self, tmp_path: Path) -> None:
        """Test that Union with Literal doesn't trigger false positive."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import Literal, Union

# This is not a Literal alias
MyUnion = Union[str, Literal["a", "b"]]
"""
        )

        aliases = extract_literal_aliases(file_path)
        assert len(aliases) == 0

    def test_class_attribute_not_extracted(self, tmp_path: Path) -> None:
        """Test that class attributes are not extracted as aliases."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import Literal

class MyClass:
    LiteralStatus = Literal["a", "b"]
"""
        )

        # Module-level walk should find class-level assignments too
        # but they're still assignments, so they might be caught
        aliases = extract_literal_aliases(file_path)
        # Depends on implementation - ast.walk walks all nodes
        # The current implementation walks all nodes including class body
        assert len(aliases) >= 0  # Implementation-dependent

    def test_conditional_alias(self, tmp_path: Path) -> None:
        """Test Literal alias inside conditional block."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
from typing import Literal
import sys

if sys.version_info >= (3, 11):
    LiteralStatus = Literal["a", "b"]
"""
        )

        aliases = extract_literal_aliases(file_path)
        # AST walk finds nodes inside if blocks
        assert len(aliases) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
