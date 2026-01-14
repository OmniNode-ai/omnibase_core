"""
Tests for CheckerEnumGovernance - Contract-driven validator for enum governance rules.

This module provides comprehensive tests for the CheckerEnumGovernance class,
covering:
- ENUM_001: Enum member casing (UPPER_SNAKE_CASE)
- ENUM_002: Literal type aliases that should be Enums
- ENUM_003: Duplicate enum values across files
- Suppression comment handling
- Multi-phase scanning
- Deterministic output ordering
- Exit codes

Additionally, tests the legacy function-based API:
- E001: Enum members must use UPPER_SNAKE_CASE
- E002: Literal types should not duplicate existing enum values

Ticket: OMN-1313
"""

import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity

from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.checker_enum_governance import (
    RULE_DUPLICATE_ENUM_VALUES,
    RULE_ENUM_MEMBER_CASING,
    RULE_LITERAL_SHOULD_BE_ENUM,
    UPPER_SNAKE_CASE_PATTERN,
    CheckerEnumGovernance,
    GovernanceASTVisitor,
    GovernanceViolation,
    LiteralAliasInfo,
    MemberInfo,
    _CollectedEnumData,
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
# Test Helpers
# =============================================================================


def create_test_file(tmp_path: Path, filename: str, content: str) -> Path:
    """Write Python content to a temporary file.

    Args:
        tmp_path: Pytest tmp_path fixture.
        filename: Name of the file to create.
        content: Python source code content.

    Returns:
        Path to the created file.
    """
    file_path = tmp_path / filename
    file_path.write_text(textwrap.dedent(content).strip())
    return file_path


def create_test_contract(
    suppression_comments: list[str] | None = None,
    severity_default: EnumValidationSeverity = EnumValidationSeverity.ERROR,
    rules: list[ModelValidatorRule] | None = None,
    exclude_patterns: list[str] | None = None,
    fail_on_warning: bool = False,
) -> ModelValidatorSubcontract:
    """Create a test contract for CheckerEnumGovernance.

    Args:
        suppression_comments: List of suppression comment patterns.
        severity_default: Default severity for rules.
        rules: List of rule configurations.
        exclude_patterns: List of file patterns to exclude.
        fail_on_warning: Whether to fail on warnings.

    Returns:
        ModelValidatorSubcontract configured for testing.
    """
    default_rules = [
        ModelValidatorRule(
            rule_id=RULE_ENUM_MEMBER_CASING,
            description="Enforce UPPER_SNAKE_CASE naming for enum members",
            severity=EnumValidationSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_LITERAL_SHOULD_BE_ENUM,
            description="Detect Literal type aliases that should be enums",
            severity=EnumValidationSeverity.ERROR,
            enabled=True,
            parameters={
                "min_values": 3,
                "allowed_aliases": [],
            },
        ),
        ModelValidatorRule(
            rule_id=RULE_DUPLICATE_ENUM_VALUES,
            description="Detect enums with overlapping value sets",
            severity=EnumValidationSeverity.WARNING,
            enabled=True,
            parameters={
                "require_name_similarity": True,
                "approved_overlaps": [],
            },
        ),
    ]
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="enum-governance",
        validator_name="Enum Governance Validator",
        validator_description="Test validator for enum governance",
        target_patterns=["**/*.py"],
        exclude_patterns=exclude_patterns or [],
        suppression_comments=suppression_comments
        or ["# enum-ok:", "# ONEX_EXCLUDE: enum", "# noqa: enum"],
        fail_on_error=True,
        fail_on_warning=fail_on_warning,
        severity_default=severity_default,
        rules=rules if rules is not None else default_rules,
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
# CheckerEnumGovernance Initialization Tests
# =============================================================================


@pytest.mark.unit
class TestCheckerEnumGovernanceInit:
    """Tests for CheckerEnumGovernance initialization."""

    def test_validator_id(self) -> None:
        """Test that validator_id is set correctly."""
        assert CheckerEnumGovernance.validator_id == "enum-governance"

    def test_init_with_contract(self) -> None:
        """Test initialization with a pre-loaded contract."""
        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)

        assert validator.contract is contract

    def test_init_without_contract(self) -> None:
        """Test initialization without a contract (lazy loading behavior)."""
        validator = CheckerEnumGovernance()
        assert validator is not None
        assert validator.validator_id == "enum-governance"


# =============================================================================
# Tests for CollectorAST
# =============================================================================


@pytest.mark.unit
class TestCollectorAST:
    """Tests for the CollectorAST AST visitor."""

    def test_collects_basic_enum(self, tmp_path: Path) -> None:
        """Test collecting a basic enum class."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
"""
        )
        enums = collect_enums_from_file(enum_file)
        assert "EnumStatus" in enums
        assert len(enums["EnumStatus"]) == 2

    def test_collects_str_enum(self, tmp_path: Path) -> None:
        """Test collecting a str, Enum class."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumNodeKind(str, Enum):
    EFFECT = "effect"
    COMPUTE = "compute"
"""
        )
        enums = collect_enums_from_file(enum_file)
        assert "EnumNodeKind" in enums
        assert len(enums["EnumNodeKind"]) == 2

    def test_extracts_member_values(self, tmp_path: Path) -> None:
        """Test that member values are correctly extracted."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumTest(Enum):
    VALUE_ONE = "value_one"
    VALUE_TWO = "value_two"
"""
        )
        enums = collect_enums_from_file(enum_file)
        values = {m.member_value for m in enums["EnumTest"]}
        assert values == {"value_one", "value_two"}

    def test_handles_auto_values(self, tmp_path: Path) -> None:
        """Test that auto() values are handled."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text(
            """
from enum import Enum, auto

class EnumAuto(Enum):
    FIRST = auto()
    SECOND = auto()
"""
        )
        enums = collect_enums_from_file(enum_file)
        assert "EnumAuto" in enums
        # auto() values should result in None member_value
        values = [m.member_value for m in enums["EnumAuto"]]
        assert all(v is None for v in values)

    def test_skips_non_enum_classes(self, tmp_path: Path) -> None:
        """Test that non-enum classes are not collected."""
        enum_file = tmp_path / "enum_test.py"
        enum_file.write_text(
            """
from enum import Enum

class NotAnEnum:
    CONSTANT = "value"

class EnumReal(Enum):
    VALUE = "value"
"""
        )
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
# ENUM_001 Tests - Enum Member Casing
# =============================================================================


@pytest.mark.unit
class TestEnumMemberCasing:
    """Tests for ENUM_001: Enum member casing validation."""

    def test_valid_upper_snake_case(self, tmp_path: Path) -> None:
        """UPPER_SNAKE_CASE members should pass."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"
            PENDING_REVIEW = "pending_review"
            HTTP_200 = "200"
            V1_BETA = "v1_beta"
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 0

    def test_invalid_lowercase(self, tmp_path: Path) -> None:
        """lowercase members should fail with suggestion."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            active = "active"
            inactive = "inactive"
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 2
        assert "Status.active" in casing_issues[0].message
        assert "UPPER_SNAKE_CASE" in casing_issues[0].message
        assert casing_issues[0].suggestion is not None
        assert "ACTIVE" in casing_issues[0].suggestion

    def test_invalid_camel_case(self, tmp_path: Path) -> None:
        """camelCase members should fail with suggestion."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            activeStatus = "active"
            pendingReview = "pending"
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 2
        # Verify suggestions are generated
        for issue in casing_issues:
            assert issue.suggestion is not None

    def test_invalid_pascal_case(self, tmp_path: Path) -> None:
        """PascalCase members should fail with suggestion."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            ActiveStatus = "active"
            PendingReview = "pending"
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 2

    def test_mixed_valid_invalid(self, tmp_path: Path) -> None:
        """Enums with both valid and invalid members should report only invalid."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            VALID_MEMBER = "valid"
            invalidMember = "invalid"
            ANOTHER_VALID = "another"
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 1
        assert "invalidMember" in casing_issues[0].message

    def test_int_enum(self, tmp_path: Path) -> None:
        """IntEnum subclasses should also be validated."""
        file_content = """
        from enum import IntEnum

        class Priority(IntEnum):
            low = 1
            medium = 2
            high = 3
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 3

    def test_private_members_ignored(self, tmp_path: Path) -> None:
        """Private members (_name) should be ignored."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            _ignore_this = "ignored"
            __also_ignore = "also_ignored"
            VALID = "valid"
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 0

    def test_suppression_comment_enum_ok(self, tmp_path: Path) -> None:
        """Suppression comments with enum-ok: should suppress violations."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):  # enum-ok: legacy naming preserved
            active = "active"
            inactive = "inactive"
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 0

    def test_suppression_comment_onex_exclude(self, tmp_path: Path) -> None:
        """Suppression comments with ONEX_EXCLUDE: enum should suppress violations."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):  # ONEX_EXCLUDE: enum
            active = "active"
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 0

    def test_suppression_comment_noqa_enum(self, tmp_path: Path) -> None:
        """Suppression comments with noqa: enum should suppress violations."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):  # noqa: enum
            active = "active"
        """
        file_path = create_test_file(tmp_path, "test_enum.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 0


# =============================================================================
# Tests for LiteralCollector
# =============================================================================


@pytest.mark.unit
class TestLiteralCollector:
    """Tests for the LiteralCollector AST visitor."""

    def test_collects_literal_type(self, tmp_path: Path) -> None:
        """Test collecting Literal type definitions."""
        model_file = tmp_path / "model_test.py"
        model_file.write_text(
            """
from typing import Literal

StatusType = Literal["active", "inactive"]
"""
        )
        literals = collect_literals_from_file(model_file)
        assert len(literals) == 1
        _, values = literals[0]
        assert values == {"active", "inactive"}

    def test_collects_multiple_literals(self, tmp_path: Path) -> None:
        """Test collecting multiple Literal type definitions."""
        model_file = tmp_path / "model_test.py"
        model_file.write_text(
            """
from typing import Literal

Status = Literal["a", "b"]
Mode = Literal["x", "y", "z"]
"""
        )
        literals = collect_literals_from_file(model_file)
        assert len(literals) == 2

    def test_collects_single_value_literal(self, tmp_path: Path) -> None:
        """Test collecting Literal with single value."""
        model_file = tmp_path / "model_test.py"
        model_file.write_text(
            """
from typing import Literal

SingleValue = Literal["only"]
"""
        )
        literals = collect_literals_from_file(model_file)
        assert len(literals) == 1
        _, values = literals[0]
        assert values == {"only"}

    def test_handles_typing_literal(self, tmp_path: Path) -> None:
        """Test handling of typing.Literal form."""
        model_file = tmp_path / "model_test.py"
        model_file.write_text(
            """
import typing

Status = typing.Literal["a", "b"]
"""
        )
        literals = collect_literals_from_file(model_file)
        assert len(literals) == 1


# =============================================================================
# ENUM_002 Tests - Literal Should Be Enum
# =============================================================================


@pytest.mark.unit
class TestLiteralShouldBeEnum:
    """Tests for ENUM_002: Literal type alias detection."""

    def test_module_scope_literal_flagged(self, tmp_path: Path) -> None:
        """Module-scope Literal matching all conditions should be flagged."""
        file_content = """
        from typing import Literal

        StatusType = Literal["active", "inactive", "pending"]
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 1
        assert "StatusType" in literal_issues[0].message
        assert "3 values" in literal_issues[0].message
        assert literal_issues[0].suggestion is not None
        assert "class StatusType(str, Enum)" in literal_issues[0].suggestion

    def test_function_scope_literal_not_flagged(self, tmp_path: Path) -> None:
        """Function-local Literals should NOT be flagged."""
        file_content = """
        from typing import Literal

        def process():
            StatusType = Literal["active", "inactive", "pending"]
            return StatusType
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 0

    def test_class_scope_literal_not_flagged(self, tmp_path: Path) -> None:
        """Class-local Literals should NOT be flagged."""
        file_content = """
        from typing import Literal

        class MyClass:
            StatusType = Literal["active", "inactive", "pending"]
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 0

    def test_non_pattern_name_not_flagged(self, tmp_path: Path) -> None:
        """Literals without pattern words should NOT be flagged."""
        file_content = """
        from typing import Literal

        ColorChoice = Literal["red", "green", "blue"]
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 0

    def test_too_few_values_not_flagged(self, tmp_path: Path) -> None:
        """Literals with < 3 values should NOT be flagged."""
        file_content = """
        from typing import Literal

        StatusType = Literal["on", "off"]
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 0

    def test_pattern_words_all_trigger(self, tmp_path: Path) -> None:
        """All pattern words should trigger detection."""
        pattern_words = ["Status", "State", "Phase", "Mode", "Health", "Type", "Kind"]

        for word in pattern_words:
            file_content = f"""
            from typing import Literal

            My{word} = Literal["a", "b", "c"]
            """
            file_path = create_test_file(
                tmp_path, f"test_{word.lower()}.py", file_content
            )

            contract = create_test_contract()
            validator = CheckerEnumGovernance(contract=contract)
            result = validator.validate(file_path)

            literal_issues = [
                i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
            ]
            assert len(literal_issues) == 1, f"Expected 1 issue for {word}"

    def test_typing_literal_attribute(self, tmp_path: Path) -> None:
        """typing.Literal should also be detected."""
        file_content = """
        import typing

        StatusType = typing.Literal["active", "inactive", "pending"]
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 1

    def test_annotated_assignment(self, tmp_path: Path) -> None:
        """TypeAlias annotated assignments should be detected."""
        file_content = """
        from typing import Literal, TypeAlias

        StatusType: TypeAlias = Literal["active", "inactive", "pending"]
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 1

    def test_allowed_aliases_not_flagged(self, tmp_path: Path) -> None:
        """Literals in allowed_aliases should NOT be flagged."""
        file_content = """
        from typing import Literal

        StatusType = Literal["active", "inactive", "pending"]
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_LITERAL_SHOULD_BE_ENUM,
                description="Detect Literal type aliases",
                severity=EnumValidationSeverity.ERROR,
                enabled=True,
                parameters={
                    "min_values": 3,
                    "allowed_aliases": ["StatusType"],
                },
            ),
        ]
        contract = create_test_contract(rules=rules)
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 0

    def test_non_string_literal_not_flagged(self, tmp_path: Path) -> None:
        """Literals with non-string values should NOT be flagged."""
        file_content = """
        from typing import Literal

        StatusType = Literal[1, 2, 3]
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 0

    def test_non_string_literal_mixed_types_not_flagged(self, tmp_path: Path) -> None:
        """Literals with mixed string and non-string values should NOT be flagged."""
        file_content = """
        from typing import Literal

        StatusType = Literal["active", 1, "pending"]
        """
        file_path = create_test_file(tmp_path, "test_literal.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        literal_issues = [
            i for i in result.issues if i.code == RULE_LITERAL_SHOULD_BE_ENUM
        ]
        assert len(literal_issues) == 0


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
# ENUM_003 Tests - Duplicate Enum Values
# =============================================================================


@pytest.mark.unit
class TestDuplicateEnumValues:
    """Tests for ENUM_003: Duplicate enum values detection."""

    def test_overlapping_enums_flagged(self, tmp_path: Path) -> None:
        """Enums with same values and similar names should be flagged."""
        file1_content = """
        from enum import Enum

        class ExecutionStatus(str, Enum):
            PENDING = "pending"
            RUNNING = "running"
            COMPLETED = "completed"
        """
        file2_content = """
        from enum import Enum

        class WorkflowStatus(str, Enum):
            PENDING = "pending"
            RUNNING = "running"
            COMPLETED = "completed"
        """
        create_test_file(tmp_path, "status1.py", file1_content)
        create_test_file(tmp_path, "status2.py", file2_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        duplicate_issues = [
            i for i in result.issues if i.code == RULE_DUPLICATE_ENUM_VALUES
        ]
        assert len(duplicate_issues) == 1
        assert "ExecutionStatus" in duplicate_issues[0].message
        assert "WorkflowStatus" in duplicate_issues[0].message
        assert "3 overlapping values" in duplicate_issues[0].message

    def test_partial_overlap_flagged(self, tmp_path: Path) -> None:
        """Enums with partial overlapping values should be flagged."""
        file1_content = """
        from enum import Enum

        class ExecutionStatus(str, Enum):
            PENDING = "pending"
            RUNNING = "running"
            COMPLETED = "completed"
        """
        file2_content = """
        from enum import Enum

        class OperationStatus(str, Enum):
            PENDING = "pending"
            ACTIVE = "active"
            COMPLETED = "completed"
        """
        create_test_file(tmp_path, "status1.py", file1_content)
        create_test_file(tmp_path, "status2.py", file2_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        duplicate_issues = [
            i for i in result.issues if i.code == RULE_DUPLICATE_ENUM_VALUES
        ]
        assert len(duplicate_issues) == 1
        assert "2 overlapping values" in duplicate_issues[0].message

    def test_same_file_overlap_flagged(self, tmp_path: Path) -> None:
        """Overlapping enums in the same file should be flagged."""
        file_content = """
        from enum import Enum

        class ExecutionStatus(str, Enum):
            PENDING = "pending"
            RUNNING = "running"
            COMPLETED = "completed"

        class TaskStatus(str, Enum):
            PENDING = "pending"
            IN_PROGRESS = "in_progress"
            COMPLETED = "completed"
        """
        create_test_file(tmp_path, "statuses.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        duplicate_issues = [
            i for i in result.issues if i.code == RULE_DUPLICATE_ENUM_VALUES
        ]
        assert len(duplicate_issues) == 1

    def test_different_values_not_flagged(self, tmp_path: Path) -> None:
        """Enums with different values should NOT be flagged."""
        file1_content = """
        from enum import Enum

        class ExecutionStatus(str, Enum):
            PENDING = "pending"
            RUNNING = "running"
        """
        file2_content = """
        from enum import Enum

        class OperationStatus(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"
        """
        create_test_file(tmp_path, "status1.py", file1_content)
        create_test_file(tmp_path, "status2.py", file2_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        duplicate_issues = [
            i for i in result.issues if i.code == RULE_DUPLICATE_ENUM_VALUES
        ]
        assert len(duplicate_issues) == 0

    def test_no_pattern_word_not_flagged(self, tmp_path: Path) -> None:
        """Enums without pattern words (with require_name_similarity) not flagged."""
        file1_content = """
        from enum import Enum

        class Color(str, Enum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"
        """
        file2_content = """
        from enum import Enum

        class Shade(str, Enum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"
        """
        create_test_file(tmp_path, "color1.py", file1_content)
        create_test_file(tmp_path, "color2.py", file2_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        duplicate_issues = [
            i for i in result.issues if i.code == RULE_DUPLICATE_ENUM_VALUES
        ]
        # Neither name contains pattern words like "Status", "State", etc.
        assert len(duplicate_issues) == 0

    def test_approved_overlap_not_flagged(self, tmp_path: Path) -> None:
        """Pairs in approved_overlaps should NOT be flagged."""
        file1_content = """
        from enum import Enum

        class ExecutionStatus(str, Enum):
            PENDING = "pending"
            RUNNING = "running"
        """
        file2_content = """
        from enum import Enum

        class WorkflowStatus(str, Enum):
            PENDING = "pending"
            RUNNING = "running"
        """
        create_test_file(tmp_path, "status1.py", file1_content)
        create_test_file(tmp_path, "status2.py", file2_content)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_ENUM_MEMBER_CASING,
                description="Casing rule",
                severity=EnumValidationSeverity.ERROR,
                enabled=True,
            ),
            ModelValidatorRule(
                rule_id=RULE_DUPLICATE_ENUM_VALUES,
                description="Detect overlapping enums",
                severity=EnumValidationSeverity.WARNING,
                enabled=True,
                parameters={
                    "require_name_similarity": True,
                    "approved_overlaps": ["ExecutionStatus,WorkflowStatus"],
                },
            ),
        ]
        contract = create_test_contract(rules=rules)
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        duplicate_issues = [
            i for i in result.issues if i.code == RULE_DUPLICATE_ENUM_VALUES
        ]
        assert len(duplicate_issues) == 0

    def test_overlap_context_includes_file_b(self, tmp_path: Path) -> None:
        """Issue context should include the second file path."""
        file1_content = """
        from enum import Enum

        class ExecutionStatus(str, Enum):
            PENDING = "pending"
        """
        file2_content = """
        from enum import Enum

        class WorkflowStatus(str, Enum):
            PENDING = "pending"
        """
        create_test_file(tmp_path, "status1.py", file1_content)
        file2_path = create_test_file(tmp_path, "status2.py", file2_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        duplicate_issues = [
            i for i in result.issues if i.code == RULE_DUPLICATE_ENUM_VALUES
        ]
        assert len(duplicate_issues) == 1
        assert duplicate_issues[0].context is not None
        assert "file_b" in duplicate_issues[0].context


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

    def test_deduplication_only_first_exact_match(self) -> None:
        """Test only first exact match is reported when Literal matches multiple enums."""
        # Two enums with same values (rare but possible)
        enum_index = {
            "EnumStatusA": {"active", "inactive"},
            "EnumStatusB": {"active", "inactive"},
        }
        literals = [(Path("test.py"), 10, {"active", "inactive"})]
        violations = check_literal_duplication(enum_index, literals)
        # Should only report ONE violation, not two
        assert len(violations) == 1
        assert violations[0].severity == "ERROR"
        assert "duplicates values from enum" in violations[0].message

    def test_deduplication_exact_match_suppresses_subset(self) -> None:
        """Test exact match prevents subset warning for same Literal."""
        enum_index = {
            "EnumSmall": {"active", "inactive"},
            "EnumLarge": {"active", "inactive", "pending", "deleted"},
        }
        literals = [(Path("test.py"), 10, {"active", "inactive"})]
        violations = check_literal_duplication(enum_index, literals)
        # Should report exact match, NOT subset warning
        assert len(violations) == 1
        assert violations[0].severity == "ERROR"
        assert "duplicates values from enum" in violations[0].message
        assert "EnumSmall" in violations[0].message

    def test_deduplication_only_first_subset_match(self) -> None:
        """Test only first subset match is reported when no exact match exists."""
        enum_index = {
            "EnumLargeA": {"active", "inactive", "pending"},
            "EnumLargeB": {"active", "inactive", "deleted"},
        }
        # Literal is subset of both enums
        literals = [(Path("test.py"), 10, {"active", "inactive"})]
        violations = check_literal_duplication(enum_index, literals)
        # Should only report ONE warning, not two
        assert len(violations) == 1
        assert violations[0].severity == "WARNING"
        assert "subset of enum" in violations[0].message


# =============================================================================
# GovernanceASTVisitor Tests
# =============================================================================


@pytest.mark.unit
class TestGovernanceASTVisitor:
    """Tests for the GovernanceASTVisitor AST visitor."""

    def test_collects_enum_info(self, tmp_path: Path) -> None:
        """Visitor should collect _CollectedEnumData for enum classes."""
        import ast

        file_content = """
from enum import Enum

class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
"""
        file_path = create_test_file(tmp_path, "test.py", file_content)
        source = file_path.read_text()
        tree = ast.parse(source)

        visitor = GovernanceASTVisitor(file_path)
        visitor.visit(tree)

        assert len(visitor.enums) == 1
        enum_info = visitor.enums[0]
        assert enum_info.name == "Status"
        assert enum_info.file_path == file_path
        assert enum_info.member_names == ("ACTIVE", "INACTIVE")
        assert enum_info.values == frozenset({"active", "inactive"})

    def test_collects_literal_alias_info(self, tmp_path: Path) -> None:
        """Visitor should collect LiteralAliasInfo for module-scope Literals."""
        import ast

        file_content = """
from typing import Literal

StatusType = Literal["active", "inactive"]
"""
        file_path = create_test_file(tmp_path, "test.py", file_content)
        source = file_path.read_text()
        tree = ast.parse(source)

        visitor = GovernanceASTVisitor(file_path)
        visitor.visit(tree)

        assert len(visitor.literal_aliases) == 1
        alias_info = visitor.literal_aliases[0]
        assert alias_info.name == "StatusType"
        assert alias_info.file_path == file_path
        assert alias_info.values == ("active", "inactive")

    def test_ignores_function_scope_literal(self, tmp_path: Path) -> None:
        """Visitor should ignore Literals inside functions."""
        import ast

        file_content = """
from typing import Literal

def func():
    LocalType = Literal["a", "b"]
"""
        file_path = create_test_file(tmp_path, "test.py", file_content)
        source = file_path.read_text()
        tree = ast.parse(source)

        visitor = GovernanceASTVisitor(file_path)
        visitor.visit(tree)

        assert len(visitor.literal_aliases) == 0

    def test_ignores_class_scope_literal(self, tmp_path: Path) -> None:
        """Visitor should ignore Literals inside classes."""
        import ast

        file_content = """
from typing import Literal

class MyClass:
    LocalType = Literal["a", "b"]
"""
        file_path = create_test_file(tmp_path, "test.py", file_content)
        source = file_path.read_text()
        tree = ast.parse(source)

        visitor = GovernanceASTVisitor(file_path)
        visitor.visit(tree)

        assert len(visitor.literal_aliases) == 0


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorIntegration:
    """Integration tests for CheckerEnumGovernance."""

    def test_validate_single_file(self, tmp_path: Path) -> None:
        """validate() should work on single files."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            active = "active"
        """
        file_path = create_test_file(tmp_path, "test.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(file_path)

        assert len(result.issues) >= 1

    def test_validate_directory(self, tmp_path: Path) -> None:
        """validate() should work on directories."""
        file1_content = """
        from enum import Enum

        class Status1(str, Enum):
            active = "active"
        """
        file2_content = """
        from enum import Enum

        class Status2(str, Enum):
            inactive = "inactive"
        """
        create_test_file(tmp_path, "file1.py", file1_content)
        create_test_file(tmp_path, "file2.py", file2_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 2

    def test_validate_list_of_files(self, tmp_path: Path) -> None:
        """validate() should work on a list of files."""
        file1 = create_test_file(
            tmp_path,
            "file1.py",
            "from enum import Enum\nclass S1(str, Enum):\n    a = 'a'",
        )
        file2 = create_test_file(
            tmp_path,
            "file2.py",
            "from enum import Enum\nclass S2(str, Enum):\n    b = 'b'",
        )

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate([file1, file2])

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 2

    def test_deterministic_output(self, tmp_path: Path) -> None:
        """Output should be deterministic regardless of file order."""
        file1_content = """
        from enum import Enum

        class StatusA(str, Enum):
            active = "active"
        """
        file2_content = """
        from enum import Enum

        class StatusB(str, Enum):
            inactive = "inactive"
        """
        create_test_file(tmp_path, "aaa.py", file1_content)
        create_test_file(tmp_path, "zzz.py", file2_content)

        contract = create_test_contract()
        validator1 = CheckerEnumGovernance(contract=contract)
        result1 = validator1.validate(tmp_path)

        validator2 = CheckerEnumGovernance(contract=contract)
        result2 = validator2.validate(tmp_path)

        # Results should be identical
        assert len(result1.issues) == len(result2.issues)
        for i, issue1 in enumerate(result1.issues):
            issue2 = result2.issues[i]
            assert issue1.message == issue2.message
            assert issue1.code == issue2.code
            assert issue1.file_path == issue2.file_path

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory should return valid result with no issues."""
        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        assert result.is_valid
        assert len(result.issues) == 0

    def test_syntax_error_handled_gracefully(self, tmp_path: Path) -> None:
        """Files with syntax errors should be skipped gracefully."""
        file_content = """
        def foo(
            # Missing closing paren
        """
        create_test_file(tmp_path, "broken.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        # Should not crash, return valid result
        assert result.is_valid

    def test_excluded_files_skipped(self, tmp_path: Path) -> None:
        """Excluded files should be skipped."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            active = "active"
        """
        create_test_file(tmp_path, "test_something.py", file_content)

        contract = create_test_contract(exclude_patterns=["**/test_*.py"])
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        assert result.is_valid
        assert len(result.issues) == 0


# =============================================================================
# Tests for validate_enum_directory
# =============================================================================


@pytest.mark.unit
class TestValidateEnumDirectory:
    """Tests for validating enum files in a directory."""

    def test_valid_enums_pass(self, temp_enums_dir: Path) -> None:
        """Test valid enum files pass validation."""
        enum_file = temp_enums_dir / "enum_status.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
"""
        )
        violations, enum_index = validate_enum_directory(temp_enums_dir)
        assert len(violations) == 0
        assert "EnumStatus" in enum_index

    def test_invalid_casing_detected(self, temp_enums_dir: Path) -> None:
        """Test invalid casing is detected."""
        enum_file = temp_enums_dir / "enum_bad.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumBad(Enum):
    active = "active"  # lowercase - violation
    INACTIVE = "inactive"  # valid
"""
        )
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
        model_file.write_text(
            """
from typing import Literal

StatusType = Literal["active", "inactive"]
"""
        )
        enum_index = {"EnumStatus": {"active", "inactive"}}
        violations = validate_literal_usage(temp_omnibase_dir, enum_index)
        assert len(violations) == 1
        assert violations[0].rule_code == "E002"

    def test_empty_enum_index(self, temp_omnibase_dir: Path) -> None:
        """Test empty enum index returns no violations."""
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        model_file = models_dir / "model_test.py"
        model_file.write_text(
            """
from typing import Literal

StatusType = Literal["active", "inactive"]
"""
        )
        enum_index: dict[str, set[str]] = {}
        violations = validate_literal_usage(temp_omnibase_dir, enum_index)
        assert len(violations) == 0


# =============================================================================
# Tests for validate_directory
# =============================================================================


@pytest.mark.unit
class TestValidateDirectoryLegacy:
    """Tests for the full directory validation."""

    def test_clean_codebase_passes(self, temp_omnibase_dir: Path) -> None:
        """Test clean codebase produces no violations."""
        enums_dir = temp_omnibase_dir / "enums"
        enums_dir.mkdir()
        enum_file = enums_dir / "enum_status.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
"""
        )
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        model_file = models_dir / "model_test.py"
        model_file.write_text(
            """
from typing import Literal

DifferentType = Literal["running", "stopped"]
"""
        )
        violations = validate_directory(temp_omnibase_dir)
        assert len(violations) == 0

    def test_finds_violations(self, temp_omnibase_dir: Path) -> None:
        """Test violations are found and reported."""
        enums_dir = temp_omnibase_dir / "enums"
        enums_dir.mkdir()
        enum_file = enums_dir / "enum_status.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    active = "active"  # E001: lowercase
    INACTIVE = "inactive"
"""
        )
        violations = validate_directory(temp_omnibase_dir)
        assert len(violations) == 1
        assert violations[0].rule_code == "E001"


# =============================================================================
# Exit Code Tests
# =============================================================================


@pytest.mark.unit
class TestExitCodes:
    """Tests for exit code behavior."""

    def test_exit_code_success_no_issues(self, tmp_path: Path) -> None:
        """Exit code should be 0 for no issues."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            ACTIVE = "active"
        """
        create_test_file(tmp_path, "test.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        exit_code = validator.get_exit_code(result)
        assert exit_code == 0
        assert result.is_valid

    def test_exit_code_errors(self, tmp_path: Path) -> None:
        """Exit code should be 1 for errors."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            active = "active"
        """
        create_test_file(tmp_path, "test.py", file_content)

        contract = create_test_contract()
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        exit_code = validator.get_exit_code(result)
        assert exit_code == 1
        assert not result.is_valid

    def test_exit_code_warnings_only_pass(self, tmp_path: Path) -> None:
        """Exit code should be 0 for warnings only (fail_on_warning=false)."""
        file1_content = """
        from enum import Enum

        class ExecutionStatus(str, Enum):
            PENDING = "pending"
        """
        file2_content = """
        from enum import Enum

        class WorkflowStatus(str, Enum):
            PENDING = "pending"
        """
        create_test_file(tmp_path, "status1.py", file1_content)
        create_test_file(tmp_path, "status2.py", file2_content)

        # Only enable the warning-level rule
        rules = [
            ModelValidatorRule(
                rule_id=RULE_ENUM_MEMBER_CASING,
                description="Casing rule",
                severity=EnumValidationSeverity.ERROR,
                enabled=False,  # Disabled
            ),
            ModelValidatorRule(
                rule_id=RULE_LITERAL_SHOULD_BE_ENUM,
                description="Literal rule",
                severity=EnumValidationSeverity.ERROR,
                enabled=False,  # Disabled
            ),
            ModelValidatorRule(
                rule_id=RULE_DUPLICATE_ENUM_VALUES,
                description="Duplicate detection",
                severity=EnumValidationSeverity.WARNING,
                enabled=True,
                parameters={"require_name_similarity": True, "approved_overlaps": []},
            ),
        ]
        contract = create_test_contract(rules=rules, fail_on_warning=False)
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        # Has warnings but not failing on them
        assert result.is_valid
        exit_code = validator.get_exit_code(result)
        assert exit_code == 0

    def test_exit_code_warnings_fail_when_enabled(self, tmp_path: Path) -> None:
        """Exit code should be 2 for warnings when fail_on_warning=true."""
        file1_content = """
        from enum import Enum

        class ExecutionStatus(str, Enum):
            PENDING = "pending"
        """
        file2_content = """
        from enum import Enum

        class WorkflowStatus(str, Enum):
            PENDING = "pending"
        """
        create_test_file(tmp_path, "status1.py", file1_content)
        create_test_file(tmp_path, "status2.py", file2_content)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_ENUM_MEMBER_CASING,
                description="Casing rule",
                severity=EnumValidationSeverity.ERROR,
                enabled=False,
            ),
            ModelValidatorRule(
                rule_id=RULE_LITERAL_SHOULD_BE_ENUM,
                description="Literal rule",
                severity=EnumValidationSeverity.ERROR,
                enabled=False,
            ),
            ModelValidatorRule(
                rule_id=RULE_DUPLICATE_ENUM_VALUES,
                description="Duplicate detection",
                severity=EnumValidationSeverity.WARNING,
                enabled=True,
                parameters={"require_name_similarity": True, "approved_overlaps": []},
            ),
        ]
        contract = create_test_contract(rules=rules, fail_on_warning=True)
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        assert not result.is_valid
        exit_code = validator.get_exit_code(result)
        assert exit_code == 2


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
        enum_file.write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
"""
        )
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
        enum_file.write_text(
            """
from enum import Enum

class EnumBad(Enum):
    lowercase = "bad"  # Violation
"""
        )
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
        enum_file.write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
"""
        )
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
        enum_file.write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
"""
        )
        # Create a Literal that would be a violation
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        model_file = models_dir / "model_test.py"
        model_file.write_text(
            """
from typing import Literal

StatusType = Literal["active"]  # Would be duplicate
"""
        )
        # With --enums-only, the Literal duplication should not be checked
        with patch.object(
            sys, "argv", ["checker", str(temp_omnibase_dir), "--enums-only"]
        ):
            result = main()
            assert result == 0


# =============================================================================
# Rule Configuration Tests
# =============================================================================


@pytest.mark.unit
class TestRuleConfiguration:
    """Tests for per-rule configuration."""

    def test_disabled_rule_skipped(self, tmp_path: Path) -> None:
        """Disabled rules should produce no issues."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            active = "active"
        """
        create_test_file(tmp_path, "test.py", file_content)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_ENUM_MEMBER_CASING,
                description="Disabled",
                severity=EnumValidationSeverity.ERROR,
                enabled=False,
            ),
        ]
        contract = create_test_contract(rules=rules)
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 0

    def test_severity_override(self, tmp_path: Path) -> None:
        """Severity should be overridden from contract rules."""
        file_content = """
        from enum import Enum

        class Status(str, Enum):
            active = "active"
        """
        create_test_file(tmp_path, "test.py", file_content)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_ENUM_MEMBER_CASING,
                description="Warning severity",
                severity=EnumValidationSeverity.WARNING,
                enabled=True,
            ),
        ]
        contract = create_test_contract(rules=rules)
        validator = CheckerEnumGovernance(contract=contract)
        result = validator.validate(tmp_path)

        casing_issues = [i for i in result.issues if i.code == RULE_ENUM_MEMBER_CASING]
        assert len(casing_issues) == 1
        assert casing_issues[0].severity == EnumValidationSeverity.WARNING


# =============================================================================
# DataClass Tests
# =============================================================================


@pytest.mark.unit
class TestDataClasses:
    """Tests for _CollectedEnumData and LiteralAliasInfo dataclasses."""

    def test_enum_info_frozen(self) -> None:
        """_CollectedEnumData should be frozen (immutable)."""
        info = _CollectedEnumData(
            name="Status",
            file_path=Path("/test.py"),
            line_number=1,
            values=frozenset({"active"}),
            member_names=("ACTIVE",),
        )

        with pytest.raises(AttributeError):
            info.name = "Changed"  # type: ignore[misc]

    def test_literal_alias_info_frozen(self) -> None:
        """LiteralAliasInfo should be frozen (immutable)."""
        info = LiteralAliasInfo(
            name="StatusType",
            file_path=Path("/test.py"),
            line_number=1,
            values=("active", "inactive"),
        )

        with pytest.raises(AttributeError):
            info.name = "Changed"  # type: ignore[misc]


# =============================================================================
# Edge case tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_enum(self, tmp_path: Path) -> None:
        """Test enum with no members."""
        enum_file = tmp_path / "enum_empty.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumEmpty(Enum):
    pass
"""
        )
        enums = collect_enums_from_file(enum_file)
        assert "EnumEmpty" in enums
        assert len(enums["EnumEmpty"]) == 0

    def test_enum_with_methods(self, tmp_path: Path) -> None:
        """Test enum with methods (not just values)."""
        enum_file = tmp_path / "enum_methods.py"
        enum_file.write_text(
            """
from enum import Enum

class EnumWithMethods(Enum):
    ACTIVE = "active"

    def is_active(self) -> bool:
        return self == EnumWithMethods.ACTIVE
"""
        )
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
        enum_file.write_text(
            """
from enum import Enum

class Outer:
    class EnumInner(Enum):
        NESTED = "nested"
"""
        )
        enums = collect_enums_from_file(enum_file)
        # Nested enums should also be collected
        assert "EnumInner" in enums


# =============================================================================
# Import Tests
# =============================================================================


@pytest.mark.unit
class TestImports:
    """Tests for module imports."""

    def test_import_checker(self) -> None:
        """Test that CheckerEnumGovernance can be imported."""
        from omnibase_core.validation.checker_enum_governance import (
            CheckerEnumGovernance,
        )

        assert CheckerEnumGovernance is not None

    def test_import_rule_constants(self) -> None:
        """Test that rule constants can be imported."""
        from omnibase_core.validation.checker_enum_governance import (
            RULE_DUPLICATE_ENUM_VALUES,
            RULE_ENUM_MEMBER_CASING,
            RULE_LITERAL_SHOULD_BE_ENUM,
        )

        assert RULE_ENUM_MEMBER_CASING == "enum_member_casing"
        assert RULE_LITERAL_SHOULD_BE_ENUM == "literal_should_be_enum"
        assert RULE_DUPLICATE_ENUM_VALUES == "duplicate_enum_values"

    def test_import_data_classes(self) -> None:
        """Test that data classes can be imported."""
        from omnibase_core.validation.checker_enum_governance import (
            GovernanceASTVisitor,
            LiteralAliasInfo,
            _CollectedEnumData,
        )

        assert _CollectedEnumData is not None
        assert LiteralAliasInfo is not None
        assert GovernanceASTVisitor is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
