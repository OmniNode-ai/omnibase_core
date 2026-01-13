"""
Tests for ValidatorBase - Contract-driven base class for file validators.

This module provides comprehensive tests for the ValidatorBase abstract base class,
covering:
- Contract loading and validation
- File targeting and exclusion patterns
- Suppression comment handling
- Deterministic result ordering
- CLI exit code mapping
- Error handling

Ticket: OMN-1291
"""

from pathlib import Path
from typing import ClassVar

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_base import (
    EXIT_ERRORS,
    EXIT_SUCCESS,
    EXIT_WARNINGS,
    SEVERITY_PRIORITY,
    ValidatorBase,
)

# =============================================================================
# Test Helpers - Concrete Implementation of ValidatorBase
# =============================================================================


class MockValidator(ValidatorBase):
    """Mock validator for testing ValidatorBase functionality."""

    validator_id: ClassVar[str] = "mock_validator"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        issues_to_return: list[ModelValidationIssue] | None = None,
    ) -> None:
        """Initialize mock validator with optional issues to return."""
        super().__init__(contract)
        self._issues_to_return = issues_to_return or []

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Return pre-configured issues for testing."""
        return tuple(self._issues_to_return)


def create_test_contract(
    validator_id: str = "mock_validator",
    target_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    suppression_comments: list[str] | None = None,
    fail_on_error: bool = True,
    fail_on_warning: bool = False,
    max_violations: int = 0,
    severity_default: EnumSeverity = EnumSeverity.ERROR,
) -> ModelValidatorSubcontract:
    """Create a test contract with specified configuration."""
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id=validator_id,
        validator_name="Mock Validator",
        validator_description="Mock validator for testing",
        target_patterns=target_patterns or ["**/*.py"],
        exclude_patterns=exclude_patterns or [],
        suppression_comments=suppression_comments or ["# noqa:"],
        fail_on_error=fail_on_error,
        fail_on_warning=fail_on_warning,
        max_violations=max_violations,
        severity_default=severity_default,
    )


# =============================================================================
# ValidatorBase Initialization Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseInit:
    """Tests for ValidatorBase initialization."""

    def test_init_with_contract(self) -> None:
        """Test initialization with a pre-loaded contract."""
        contract = create_test_contract()
        validator = MockValidator(contract=contract)

        # Verify contract is accessible via public property
        assert validator.contract is contract

    def test_init_without_contract(self) -> None:
        """Test initialization without a contract (lazy loading behavior).

        When no contract is provided, the validator should still be created
        successfully and will load the contract lazily when first accessed.
        """
        validator = MockValidator()

        # Validator should be created successfully without a contract
        assert validator is not None
        assert validator.validator_id == "mock_validator"

    def test_contract_property_caches_loaded_contract(self) -> None:
        """Test that contract property caches the loaded contract."""
        contract = create_test_contract()
        validator = MockValidator(contract=contract)

        # Access property multiple times
        result1 = validator.contract
        result2 = validator.contract

        assert result1 is result2
        assert result1 is contract


# =============================================================================
# File Targeting Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseFileTargeting:
    """Tests for file targeting and resolution."""

    def test_resolve_targets_file(self, tmp_path: Path) -> None:
        """Test that single files are resolved correctly."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        contract = create_test_contract()
        validator = MockValidator(contract=contract)

        resolved = validator._resolve_targets([test_file])

        assert len(resolved) == 1
        assert resolved[0] == test_file.resolve()

    def test_resolve_targets_directory(self, tmp_path: Path) -> None:
        """Test that directories are expanded using glob patterns."""
        # Create test files
        (tmp_path / "file1.py").write_text("# test1")
        (tmp_path / "file2.py").write_text("# test2")
        (tmp_path / "file.txt").write_text("text file")  # Non-Python

        contract = create_test_contract(target_patterns=["**/*.py"])
        validator = MockValidator(contract=contract)

        resolved = validator._resolve_targets([tmp_path])

        # Should only find .py files
        assert len(resolved) == 2
        resolved_names = [p.name for p in resolved]
        assert "file1.py" in resolved_names
        assert "file2.py" in resolved_names
        assert "file.txt" not in resolved_names

    def test_resolve_targets_nonexistent_path(self, tmp_path: Path) -> None:
        """Test that non-existent paths are skipped."""
        nonexistent = tmp_path / "does_not_exist.py"

        contract = create_test_contract()
        validator = MockValidator(contract=contract)

        resolved = validator._resolve_targets([nonexistent])

        assert len(resolved) == 0

    def test_resolve_targets_deduplicates(self, tmp_path: Path) -> None:
        """Test that duplicate paths are deduplicated."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        contract = create_test_contract()
        validator = MockValidator(contract=contract)

        resolved = validator._resolve_targets([test_file, test_file, test_file])

        assert len(resolved) == 1


# =============================================================================
# Exclusion Pattern Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseExclusion:
    """Tests for file exclusion patterns."""

    def test_is_excluded_matches_pattern(self, tmp_path: Path) -> None:
        """Test that files matching exclusion patterns are excluded."""
        # Use pattern that won't conflict with pytest's temp dir names
        contract = create_test_contract(exclude_patterns=["**/excluded_*.py"])
        validator = MockValidator(contract=contract)

        excluded_file = tmp_path / "excluded_example.py"
        included_file = tmp_path / "example.py"

        assert validator._is_excluded(excluded_file) is True
        assert validator._is_excluded(included_file) is False

    def test_is_excluded_directory_pattern(self, tmp_path: Path) -> None:
        """Test that directory patterns exclude files in that directory."""
        contract = create_test_contract(exclude_patterns=["**/node_modules/**"])
        validator = MockValidator(contract=contract)

        # Create a nested path
        excluded_path = tmp_path / "node_modules" / "package" / "file.py"

        assert validator._is_excluded(excluded_path) is True

    def test_is_excluded_multiple_patterns(self, tmp_path: Path) -> None:
        """Test that multiple exclusion patterns are all checked."""
        # Use patterns that won't conflict with pytest's temp dir names
        contract = create_test_contract(
            exclude_patterns=[
                "**/excluded_*.py",
                "**/__pycache__/**",
                "**/migrations/**",
            ]
        )
        validator = MockValidator(contract=contract)

        excluded_file = tmp_path / "excluded_example.py"
        cache_file = tmp_path / "__pycache__" / "module.pyc"
        migration_file = tmp_path / "migrations" / "001_initial.py"
        normal_file = tmp_path / "module.py"

        assert validator._is_excluded(excluded_file) is True
        assert validator._is_excluded(cache_file) is True
        assert validator._is_excluded(migration_file) is True
        assert validator._is_excluded(normal_file) is False


# =============================================================================
# Suppression Comment Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseSuppression:
    """Tests for suppression comment handling."""

    def test_is_suppressed_with_comment(self, tmp_path: Path) -> None:
        """Test that lines with suppression comments are detected."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# line 1\ncode = 'value'  # noqa: E501\n# line 3")

        contract = create_test_contract(suppression_comments=["# noqa:"])
        validator = MockValidator(contract=contract)

        # Load file into cache
        validator._get_file_lines(test_file)

        assert validator._is_suppressed(test_file, 1) is False
        assert validator._is_suppressed(test_file, 2) is True
        assert validator._is_suppressed(test_file, 3) is False

    def test_is_suppressed_invalid_line_number(self, tmp_path: Path) -> None:
        """Test that invalid line numbers return False."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# line 1\n# line 2")

        contract = create_test_contract()
        validator = MockValidator(contract=contract)

        assert validator._is_suppressed(test_file, 0) is False
        assert validator._is_suppressed(test_file, -1) is False
        assert validator._is_suppressed(test_file, 999) is False

    def test_is_suppressed_multiple_patterns(self, tmp_path: Path) -> None:
        """Test that multiple suppression patterns are all checked."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "code1  # noqa: E501\ncode2  # type: ignore\ncode3  # normal comment"
        )

        contract = create_test_contract(
            suppression_comments=["# noqa:", "# type: ignore"]
        )
        validator = MockValidator(contract=contract)

        # Load file into cache
        validator._get_file_lines(test_file)

        assert validator._is_suppressed(test_file, 1) is True
        assert validator._is_suppressed(test_file, 2) is True  # type-ignore pattern
        assert validator._is_suppressed(test_file, 3) is False  # normal comment


# =============================================================================
# Validation Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseValidation:
    """Tests for validation execution."""

    def test_validate_single_file(self, tmp_path: Path) -> None:
        """Test validating a single file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test file")

        contract = create_test_contract()
        issue = ModelValidationIssue(
            severity=EnumSeverity.ERROR,
            message="Test issue",
            code="test_error",
            file_path=test_file,
            line_number=1,
        )
        validator = MockValidator(contract=contract, issues_to_return=[issue])

        result = validator.validate_file(test_file)

        assert not result.is_valid
        assert len(result.issues) == 1
        assert result.issues[0].message == "Test issue"

    def test_validate_multiple_files(self, tmp_path: Path) -> None:
        """Test validating multiple files."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("# file 1")
        file2.write_text("# file 2")

        contract = create_test_contract()
        issue = ModelValidationIssue(
            severity=EnumSeverity.WARNING,
            message="Warning",
            code="test_warning",
        )
        validator = MockValidator(contract=contract, issues_to_return=[issue])

        result = validator.validate([file1, file2])

        # Each file returns one issue
        assert len(result.issues) == 2

    def test_validate_respects_max_violations(self, tmp_path: Path) -> None:
        """Test that validation stops at max_violations limit."""
        # Create multiple files
        for i in range(5):
            (tmp_path / f"file{i}.py").write_text(f"# file {i}")

        contract = create_test_contract(max_violations=2)
        issue = ModelValidationIssue(
            severity=EnumSeverity.ERROR,
            message="Error",
            code="test_error",
        )
        validator = MockValidator(contract=contract, issues_to_return=[issue])

        result = validator.validate(tmp_path)

        # Should stop at max_violations
        assert len(result.issues) <= 2

    def test_validate_excluded_file_returns_valid(self, tmp_path: Path) -> None:
        """Test that excluded files return valid result."""
        test_file = tmp_path / "test_excluded.py"
        test_file.write_text("# excluded")

        contract = create_test_contract(exclude_patterns=["**/test_*.py"])
        validator = MockValidator(contract=contract)

        result = validator.validate_file(test_file)

        assert result.is_valid


# =============================================================================
# Result Building Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseResultBuilding:
    """Tests for result building and ordering."""

    def test_build_result_sorts_by_severity(self, tmp_path: Path) -> None:
        """Test that issues are sorted by severity (critical first)."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.WARNING,
                message="Warning",
                code="warn",
            ),
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message="Error",
                code="error",
            ),
            ModelValidationIssue(
                severity=EnumSeverity.CRITICAL,
                message="Critical",
                code="critical",
            ),
        ]

        contract = create_test_contract()
        validator = MockValidator(contract=contract, issues_to_return=issues)

        result = validator.validate_file(test_file)

        # Should be sorted: CRITICAL, ERROR, WARNING
        assert result.issues[0].severity == EnumSeverity.CRITICAL
        assert result.issues[1].severity == EnumSeverity.ERROR
        assert result.issues[2].severity == EnumSeverity.WARNING

    def test_build_result_sorts_by_file_then_line(self, tmp_path: Path) -> None:
        """Test that issues are sorted by file path then line number."""
        file_a = tmp_path / "a_file.py"
        file_b = tmp_path / "b_file.py"
        file_a.write_text("# a")
        file_b.write_text("# b")

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message="B:10",
                code="err",
                file_path=file_b,
                line_number=10,
            ),
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message="A:5",
                code="err",
                file_path=file_a,
                line_number=5,
            ),
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message="A:1",
                code="err",
                file_path=file_a,
                line_number=1,
            ),
        ]

        contract = create_test_contract()
        validator = MockValidator(contract=contract, issues_to_return=issues)

        result = validator.validate_file(file_a)

        # Should be sorted by file then line
        # All have same severity, so sort by file (a before b) then line
        assert result.issues[0].message == "A:1"
        assert result.issues[1].message == "A:5"
        assert result.issues[2].message == "B:10"

    def test_build_result_is_valid_with_no_errors(self, tmp_path: Path) -> None:
        """Test that result is valid when no errors or critical issues."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        # Only warnings
        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.WARNING,
                message="Warning",
                code="warn",
            ),
        ]

        contract = create_test_contract(fail_on_error=True, fail_on_warning=False)
        validator = MockValidator(contract=contract, issues_to_return=issues)

        result = validator.validate_file(test_file)

        # Warnings don't cause failure by default
        assert result.is_valid

    def test_build_result_invalid_with_errors(self, tmp_path: Path) -> None:
        """Test that result is invalid when errors exist."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message="Error",
                code="err",
            ),
        ]

        contract = create_test_contract(fail_on_error=True)
        validator = MockValidator(contract=contract, issues_to_return=issues)

        result = validator.validate_file(test_file)

        assert not result.is_valid

    def test_build_result_fail_on_warning(self, tmp_path: Path) -> None:
        """Test that fail_on_warning causes warnings to fail."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.WARNING,
                message="Warning",
                code="warn",
            ),
        ]

        contract = create_test_contract(fail_on_error=True, fail_on_warning=True)
        validator = MockValidator(contract=contract, issues_to_return=issues)

        result = validator.validate_file(test_file)

        assert not result.is_valid


# =============================================================================
# Exit Code Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseExitCodes:
    """Tests for CLI exit code mapping."""

    def test_exit_code_success(self, tmp_path: Path) -> None:
        """Test that valid results return EXIT_SUCCESS."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        contract = create_test_contract()
        validator = MockValidator(contract=contract, issues_to_return=[])

        result = validator.validate_file(test_file)
        exit_code = validator.get_exit_code(result)

        assert exit_code == EXIT_SUCCESS

    def test_exit_code_errors(self, tmp_path: Path) -> None:
        """Test that error issues return EXIT_ERRORS."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message="Error",
                code="err",
            ),
        ]

        contract = create_test_contract(fail_on_error=True)
        validator = MockValidator(contract=contract, issues_to_return=issues)

        result = validator.validate_file(test_file)
        exit_code = validator.get_exit_code(result)

        assert exit_code == EXIT_ERRORS

    def test_exit_code_warnings(self, tmp_path: Path) -> None:
        """Test that warning issues with fail_on_warning return EXIT_WARNINGS."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        issues = [
            ModelValidationIssue(
                severity=EnumSeverity.WARNING,
                message="Warning",
                code="warn",
            ),
        ]

        contract = create_test_contract(fail_on_error=True, fail_on_warning=True)
        validator = MockValidator(contract=contract, issues_to_return=issues)

        result = validator.validate_file(test_file)
        exit_code = validator.get_exit_code(result)

        assert exit_code == EXIT_WARNINGS


# =============================================================================
# Constants Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseConstants:
    """Tests for module constants."""

    def test_exit_code_values(self) -> None:
        """Test that exit codes have expected values."""
        assert EXIT_SUCCESS == 0
        assert EXIT_ERRORS == 1
        assert EXIT_WARNINGS == 2

    def test_severity_priority_ordering(self) -> None:
        """Test that severity priority ordering is correct."""
        # Lower number = higher priority
        assert SEVERITY_PRIORITY[EnumSeverity.CRITICAL] == 0
        assert SEVERITY_PRIORITY[EnumSeverity.ERROR] == 1
        assert SEVERITY_PRIORITY[EnumSeverity.WARNING] == 2
        assert SEVERITY_PRIORITY[EnumSeverity.INFO] == 3

    def test_severity_priority_all_severities_covered(self) -> None:
        """Test that all severities are covered in priority map."""
        expected_severities = {
            EnumSeverity.CRITICAL,
            EnumSeverity.ERROR,
            EnumSeverity.WARNING,
            EnumSeverity.INFO,
        }
        assert set(SEVERITY_PRIORITY.keys()) == expected_severities


# =============================================================================
# File Line Cache Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseFileLineCache:
    """Tests for file line caching."""

    def test_get_file_lines_caches_result(self, tmp_path: Path) -> None:
        """Test that file lines are cached."""
        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\nline3")

        contract = create_test_contract()
        validator = MockValidator(contract=contract)

        # First read
        lines1 = validator._get_file_lines(test_file)

        # Second read (should use cache)
        lines2 = validator._get_file_lines(test_file)

        assert lines1 is lines2  # Same object (cached)
        assert lines1 == ["line1", "line2", "line3"]

    def test_get_file_lines_unreadable_file(self, tmp_path: Path) -> None:
        """Test that unreadable files return empty list."""
        nonexistent = tmp_path / "does_not_exist.py"

        contract = create_test_contract()
        validator = MockValidator(contract=contract)

        lines = validator._get_file_lines(nonexistent)

        assert lines == []

    def test_validate_clears_cache_after(self, tmp_path: Path) -> None:
        """Test that validation clears the line cache after completion."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        contract = create_test_contract()
        validator = MockValidator(contract=contract)

        # Pre-populate cache
        validator._get_file_lines(test_file)
        assert len(validator._file_line_cache) == 1

        # Validate clears cache
        validator.validate_file(test_file)
        assert len(validator._file_line_cache) == 0


# =============================================================================
# Contract Loading Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseContractLoading:
    """Tests for contract loading from YAML."""

    def test_load_contract_not_found(self, tmp_path: Path) -> None:
        """Test that missing contract raises appropriate error."""

        class TestValidator(ValidatorBase):
            validator_id: ClassVar[str] = "test_validator"

            def _get_contract_path(self) -> Path:
                return tmp_path / "contracts" / "nonexistent.yaml"

            def _validate_file(
                self,
                path: Path,
                contract: ModelValidatorSubcontract,
            ) -> tuple[ModelValidationIssue, ...]:
                return ()

        validator = TestValidator()

        with pytest.raises(ModelOnexError) as exc_info:
            _ = validator.contract

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_load_contract_invalid_yaml(self, tmp_path: Path) -> None:
        """Test that invalid YAML raises appropriate error."""
        contract_dir = tmp_path / "contracts"
        contract_dir.mkdir(parents=True)
        contract_file = contract_dir / "test_validator.validation.yaml"
        contract_file.write_text("invalid: yaml: content: [[[")

        class TestValidator(ValidatorBase):
            validator_id: ClassVar[str] = "test_validator"

            def _get_contract_path(self) -> Path:
                return contract_file

            def _validate_file(
                self,
                path: Path,
                contract: ModelValidatorSubcontract,
            ) -> tuple[ModelValidationIssue, ...]:
                return ()

        validator = TestValidator()

        with pytest.raises(ModelOnexError) as exc_info:
            _ = validator.contract

        assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR


# =============================================================================
# Import Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBaseImports:
    """Tests for module imports."""

    def test_import_validator_base(self) -> None:
        """Test that ValidatorBase can be imported."""
        from omnibase_core.validation.validator_base import ValidatorBase

        assert ValidatorBase is not None

    def test_import_exit_codes(self) -> None:
        """Test that exit code constants can be imported."""
        from omnibase_core.validation.validator_base import (
            EXIT_ERRORS,
            EXIT_SUCCESS,
            EXIT_WARNINGS,
        )

        assert EXIT_SUCCESS == 0
        assert EXIT_ERRORS == 1
        assert EXIT_WARNINGS == 2

    def test_import_severity_priority(self) -> None:
        """Test that SEVERITY_PRIORITY can be imported."""
        from omnibase_core.validation.validator_base import SEVERITY_PRIORITY

        assert isinstance(SEVERITY_PRIORITY, dict)


# =============================================================================
# Path Traversal Security Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorBasePathTraversalSecurity:
    """Security tests for path traversal attack prevention.

    These tests verify that the validator properly rejects path traversal
    attempts and returns the correct SECURITY_VIOLATION error codes.
    """

    def test_validate_cli_path_rejects_double_dot_traversal(self) -> None:
        """Test that CLI path validation rejects '..' traversal sequences.

        Security: Paths containing '..' could escape the intended directory
        and access sensitive system files.
        """
        malicious_path = Path("../../../etc/passwd")

        result = MockValidator._validate_cli_path(malicious_path, "target path")

        # Should return None (rejection)
        assert result is None

    def test_validate_cli_path_rejects_double_slash(self) -> None:
        """Test that CLI path validation rejects '//' bypass attempts.

        Security: Double slashes can be used to bypass path normalization
        in some systems.
        """
        malicious_path = Path("//etc/passwd")

        result = MockValidator._validate_cli_path(malicious_path, "target path")

        # Should return None (rejection)
        assert result is None

    def test_validate_cli_path_accepts_valid_path(self, tmp_path: Path) -> None:
        """Test that CLI path validation accepts legitimate paths."""
        valid_path = tmp_path / "test_file.py"
        valid_path.write_text("# test")

        result = MockValidator._validate_cli_path(valid_path, "target path")

        # Should return resolved path
        assert result is not None
        assert result == valid_path.resolve()

    def test_resolve_targets_rejects_source_root_traversal(
        self, tmp_path: Path
    ) -> None:
        """Test that _resolve_targets rejects source_root with path traversal.

        Security: source_root from YAML contracts could contain traversal
        sequences if not validated.
        """
        # Create a contract with malicious source_root
        contract = create_test_contract()
        # Use model_copy to add malicious source_root
        malicious_contract = contract.model_copy(
            update={"source_root": Path("../../../etc")}
        )
        validator = MockValidator(contract=malicious_contract)

        # Create a target directory
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Should raise SECURITY_VIOLATION error
        with pytest.raises(ModelOnexError) as exc_info:
            validator._resolve_targets([target_dir])

        # Verify the actual error code is SECURITY_VIOLATION
        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
        # Verify the error message mentions path traversal
        assert "traversal" in exc_info.value.message.lower()

    def test_resolve_targets_rejects_double_slash_in_source_root(
        self, tmp_path: Path
    ) -> None:
        """Test that _resolve_targets rejects source_root with double slashes.

        Security: Double slashes can indicate path manipulation attempts.
        """
        # Create a contract with malicious source_root (double slash)
        contract = create_test_contract()
        malicious_contract = contract.model_copy(
            update={"source_root": Path("//usr/local")}
        )
        validator = MockValidator(contract=malicious_contract)

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Should raise SECURITY_VIOLATION error
        with pytest.raises(ModelOnexError) as exc_info:
            validator._resolve_targets([target_dir])

        # Verify the actual error code is SECURITY_VIOLATION
        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION

    def test_model_validator_subcontract_rejects_traversal_in_source_root(
        self,
    ) -> None:
        """Test that ModelValidatorSubcontract validation rejects traversal.

        Security: The subcontract model validation should catch path traversal
        at the earliest point - during model construction.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidatorSubcontract(
                version=ModelSemVer(major=1, minor=0, patch=0),
                validator_id="test",
                validator_name="Test Validator",
                validator_description="Test description",
                source_root=Path("../../../etc/passwd"),
            )

        # Verify the actual error code is SECURITY_VIOLATION
        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
        # Verify error message mentions path traversal
        assert "traversal" in exc_info.value.message.lower()

    def test_model_validator_subcontract_rejects_double_slash(self) -> None:
        """Test that ModelValidatorSubcontract rejects double slash paths.

        Security: Double slashes are another form of path manipulation.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidatorSubcontract(
                version=ModelSemVer(major=1, minor=0, patch=0),
                validator_id="test",
                validator_name="Test Validator",
                validator_description="Test description",
                source_root=Path("//usr//local"),
            )

        # Verify the actual error code is SECURITY_VIOLATION
        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
        # Verify error message mentions path traversal
        assert "traversal" in exc_info.value.message.lower()

    def test_model_validator_subcontract_accepts_valid_source_root(
        self, tmp_path: Path
    ) -> None:
        """Test that ModelValidatorSubcontract accepts valid source_root."""
        # Create a valid source root path (no traversal)
        valid_source_root = tmp_path / "src"
        valid_source_root.mkdir()

        # Should not raise
        contract = ModelValidatorSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            validator_id="test",
            validator_name="Test Validator",
            validator_description="Test description",
            source_root=valid_source_root,
        )

        assert contract.source_root == valid_source_root

    def test_path_traversal_payloads(self) -> None:
        """Test multiple path traversal payload patterns.

        Security: Tests a variety of path traversal attack patterns
        to ensure comprehensive protection.
        """
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//etc/passwd",
            "/var/log/../../../etc/passwd",
            "foo/../../../etc/passwd",
        ]

        for payload in traversal_payloads:
            path = Path(payload)
            result = MockValidator._validate_cli_path(path, "test")
            assert result is None, f"Should reject traversal payload: {payload}"
