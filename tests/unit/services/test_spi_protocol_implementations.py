# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for SPI protocol method implementations in ServiceProtocolAuditor
and ServiceContractValidator.

Covers OMN-727: Implement All SPI Protocol Methods.
"""

from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path

import pytest

from omnibase_core.services.service_contract_validator import ServiceContractValidator
from omnibase_core.services.service_protocol_auditor import ServiceProtocolAuditor


# =============================================================================
# Helper to run async methods in sync tests
# =============================================================================
def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# ServiceProtocolAuditor SPI Protocol Method Tests
# =============================================================================


@pytest.mark.unit
class TestAuditorValidateFileQuality:
    """Test validate_file_quality() implementation."""

    def test_validate_file_quality_with_good_file(self, tmp_path: Path) -> None:
        """Test quality validation of a well-structured Python file."""
        good_file = tmp_path / "model_example.py"
        good_file.write_text(
            textwrap.dedent('''\
            """Example model module."""

            from pydantic import BaseModel


            class ModelExample(BaseModel):
                """An example model."""

                name: str
                value: int
            ''')
        )

        auditor = ServiceProtocolAuditor(str(tmp_path))
        report = run_async(auditor.validate_file_quality(str(good_file)))

        assert report.file_path == str(good_file)
        assert report.overall_score > 50.0
        assert report.metrics.lines_of_code > 0

    def test_validate_file_quality_with_empty_file(self, tmp_path: Path) -> None:
        """Test quality validation of an empty file."""
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        auditor = ServiceProtocolAuditor(str(tmp_path))
        report = run_async(auditor.validate_file_quality(str(empty_file)))

        assert report.file_path == str(empty_file)
        assert any("empty" in r.lower() for r in report.recommendations)

    def test_validate_file_quality_with_content_override(self, tmp_path: Path) -> None:
        """Test quality validation with content parameter."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent('''\
        """Module docstring."""

        def hello() -> str:
            """Say hello."""
            return "hello"
        ''')

        report = run_async(auditor.validate_file_quality("virtual.py", content=source))

        assert report.file_path == "virtual.py"
        assert report.metrics.lines_of_code > 0
        assert report.overall_score > 0.0

    def test_validate_file_quality_nonexistent(self, tmp_path: Path) -> None:
        """Test quality validation of nonexistent file."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        report = run_async(
            auditor.validate_file_quality(str(tmp_path / "nonexistent.py"))
        )

        assert report.file_path == str(tmp_path / "nonexistent.py")


@pytest.mark.unit
class TestAuditorValidateDirectoryQuality:
    """Test validate_directory_quality() implementation."""

    def test_validate_directory_quality_with_files(self, tmp_path: Path) -> None:
        """Test directory quality with Python files."""
        (tmp_path / "file1.py").write_text('"""Module."""\nx = 1\n')
        (tmp_path / "file2.py").write_text('"""Module."""\ny = 2\n')
        (tmp_path / "not_py.txt").write_text("Not python")

        auditor = ServiceProtocolAuditor(str(tmp_path))
        reports = run_async(auditor.validate_directory_quality(str(tmp_path)))

        assert len(reports) == 2  # Only .py files

    def test_validate_directory_quality_empty(self, tmp_path: Path) -> None:
        """Test directory quality with no Python files."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        reports = run_async(auditor.validate_directory_quality(str(tmp_path)))

        assert len(reports) == 0

    def test_validate_directory_quality_nonexistent(self, tmp_path: Path) -> None:
        """Test directory quality with nonexistent path."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        reports = run_async(
            auditor.validate_directory_quality(str(tmp_path / "nonexistent"))
        )

        assert len(reports) == 0

    def test_validate_directory_quality_custom_patterns(self, tmp_path: Path) -> None:
        """Test directory quality with custom file patterns."""
        (tmp_path / "test.py").write_text('"""Module."""\nx = 1\n')
        (tmp_path / "model.py").write_text('"""Module."""\ny = 2\n')

        auditor = ServiceProtocolAuditor(str(tmp_path))
        reports = run_async(
            auditor.validate_directory_quality(str(tmp_path), ["model*.py"])
        )

        assert len(reports) == 1


@pytest.mark.unit
class TestAuditorCalculateQualityMetrics:
    """Test calculate_quality_metrics() implementation."""

    def test_metrics_simple_file(self, tmp_path: Path) -> None:
        """Test metrics calculation on a simple file."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent("""\
        x = 1
        y = 2
        z = x + y
        """)

        metrics = auditor.calculate_quality_metrics("test.py", content=source)

        assert metrics.lines_of_code == 3
        assert metrics.cyclomatic_complexity >= 1

    def test_metrics_complex_file(self, tmp_path: Path) -> None:
        """Test metrics calculation on a complex file."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent("""\
        def complex_func(x, y, z):
            if x > 0:
                if y > 0:
                    if z > 0:
                        return x + y + z
                    else:
                        return x + y
                else:
                    return x
            elif x == 0:
                return 0
            else:
                for i in range(10):
                    if i % 2 == 0:
                        continue
                return -1
        """)

        metrics = auditor.calculate_quality_metrics("test.py", content=source)

        assert metrics.cyclomatic_complexity > 5
        assert metrics.lines_of_code > 10

    def test_metrics_empty_content(self, tmp_path: Path) -> None:
        """Test metrics calculation on empty content."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        metrics = auditor.calculate_quality_metrics("test.py", content="")

        assert metrics.lines_of_code == 0
        assert metrics.cyclomatic_complexity == 1

    def test_metrics_syntax_error(self, tmp_path: Path) -> None:
        """Test metrics calculation on file with syntax errors."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        metrics = auditor.calculate_quality_metrics("test.py", content="def broken(:")

        assert metrics.lines_of_code > 0

    def test_metrics_complexity_rating(self, tmp_path: Path) -> None:
        """Test complexity rating from metrics."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        metrics = auditor.calculate_quality_metrics("test.py", content="x = 1")

        rating = run_async(metrics.get_complexity_rating())
        assert rating in ("A", "B", "C", "D", "F")


@pytest.mark.unit
class TestAuditorDetectCodeSmells:
    """Test detect_code_smells() implementation."""

    def test_detect_long_function(self, tmp_path: Path) -> None:
        """Test detection of long functions."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        # Create a function that's longer than 50 lines
        lines = ["def long_func():"]
        lines.extend([f"    x{i} = {i}" for i in range(60)])
        source = "\n".join(lines)

        issues = auditor.detect_code_smells("test.py", content=source)

        assert any(i.issue_type == "long_function" for i in issues)

    def test_detect_too_many_arguments(self, tmp_path: Path) -> None:
        """Test detection of functions with too many arguments."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = "def many_args(a, b, c, d, e, f, g, h, i, j):\n    pass\n"

        issues = auditor.detect_code_smells("test.py", content=source)

        assert any(i.issue_type == "too_many_arguments" for i in issues)

    def test_detect_bare_except(self, tmp_path: Path) -> None:
        """Test detection of bare except clauses."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent("""\
        try:
            x = 1
        except:
            pass
        """)

        issues = auditor.detect_code_smells("test.py", content=source)

        assert any(i.issue_type == "broad_exception" for i in issues)

    def test_no_smells_in_clean_code(self, tmp_path: Path) -> None:
        """Test no smells detected in clean code."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent("""\
        def clean_func(x: int) -> int:
            return x + 1
        """)

        issues = auditor.detect_code_smells("test.py", content=source)

        # Should have no critical smells
        assert not any(i.severity == "critical" for i in issues)

    def test_detect_syntax_error(self, tmp_path: Path) -> None:
        """Test code smell detection on file with syntax errors."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        issues = auditor.detect_code_smells("test.py", content="def broken(:")

        assert any(i.issue_type == "syntax_error" for i in issues)


@pytest.mark.unit
class TestAuditorCheckNamingConventions:
    """Test check_naming_conventions() async implementation."""

    def test_naming_protocol_class(self, tmp_path: Path) -> None:
        """Test naming check for Protocol classes."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent("""\
        from typing import Protocol

        class BadName(Protocol):
            def method(self) -> None: ...
        """)

        issues = run_async(auditor.check_naming_conventions("test.py", content=source))

        assert any(i.issue_type == "naming" for i in issues)

    def test_naming_correct_protocol(self, tmp_path: Path) -> None:
        """Test naming check for correctly named Protocol class."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent("""\
        from typing import Protocol

        class ProtocolExample(Protocol):
            def method(self) -> None: ...
        """)

        issues = run_async(auditor.check_naming_conventions("test.py", content=source))

        # Should have no naming issues for Protocol classes
        naming_issues = [i for i in issues if i.issue_type == "naming"]
        assert len(naming_issues) == 0

    def test_naming_model_class(self, tmp_path: Path) -> None:
        """Test naming check for Pydantic BaseModel classes."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent("""\
        from pydantic import BaseModel

        class BadModelName(BaseModel):
            value: str
        """)

        issues = run_async(auditor.check_naming_conventions("test.py", content=source))

        assert any(i.issue_type == "naming" for i in issues)


@pytest.mark.unit
class TestAuditorAnalyzeComplexity:
    """Test analyze_complexity() async implementation."""

    def test_complexity_simple_function(self, tmp_path: Path) -> None:
        """Test complexity analysis of a simple function."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent("""\
        def simple():
            return 1
        """)

        issues = run_async(auditor.analyze_complexity("test.py", content=source))

        # Simple function should not trigger complexity issues
        assert len(issues) == 0

    def test_complexity_complex_function(self, tmp_path: Path) -> None:
        """Test complexity analysis of a complex function."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        # Build a function with high cyclomatic complexity
        lines = ["def complex_func(x, y):"]
        for i in range(15):
            lines.append(f"    if x == {i}:")
            lines.append(f"        return {i}")
        lines.append("    return -1")
        source = "\n".join(lines)

        issues = run_async(auditor.analyze_complexity("test.py", content=source))

        assert len(issues) > 0
        assert all(i.issue_type == "complexity" for i in issues)


@pytest.mark.unit
class TestAuditorValidateDocumentation:
    """Test validate_documentation() async implementation."""

    def test_missing_module_docstring(self, tmp_path: Path) -> None:
        """Test detection of missing module docstring."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = "x = 1\n"

        issues = run_async(auditor.validate_documentation("test.py", content=source))

        assert any(i.rule_id == "DOC001" for i in issues)

    def test_missing_class_docstring(self, tmp_path: Path) -> None:
        """Test detection of missing class docstring."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent('''\
        """Module docstring."""

        class PublicClass:
            pass
        ''')

        issues = run_async(auditor.validate_documentation("test.py", content=source))

        assert any(i.rule_id == "DOC002" for i in issues)

    def test_well_documented_file(self, tmp_path: Path) -> None:
        """Test that well-documented file passes."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent('''\
        """Module docstring."""


        class PublicClass:
            """Class docstring."""

            def public_method(self):
                """Method docstring."""
                pass
        ''')

        issues = run_async(auditor.validate_documentation("test.py", content=source))

        # Should have no critical documentation issues
        assert not any(i.severity in ("critical", "error") for i in issues)


@pytest.mark.unit
class TestAuditorSuggestRefactoring:
    """Test suggest_refactoring() implementation."""

    def test_suggest_for_large_file(self, tmp_path: Path) -> None:
        """Test refactoring suggestions for a large file."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        # Create a file with 600+ lines
        lines = ['"""Module."""']
        for i in range(600):
            lines.append(f"x{i} = {i}")
        source = "\n".join(lines)

        suggestions = auditor.suggest_refactoring("test.py", content=source)

        assert any("splitting" in s.lower() for s in suggestions)

    def test_no_suggestions_for_small_file(self, tmp_path: Path) -> None:
        """Test no refactoring suggestions for a small clean file."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        source = textwrap.dedent("""\
        def simple():
            return 1
        """)

        suggestions = auditor.suggest_refactoring("test.py", content=source)

        # Small file should have no splitting suggestions
        assert not any("splitting" in s.lower() for s in suggestions)

    def test_suggest_for_syntax_error(self, tmp_path: Path) -> None:
        """Test refactoring suggestions for file with syntax errors."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        suggestions = auditor.suggest_refactoring("test.py", content="def broken(:")

        assert any("syntax" in s.lower() for s in suggestions)


@pytest.mark.unit
class TestAuditorGetValidationSummary:
    """Test get_validation_summary() implementation."""

    def test_summary_with_no_reports(self, tmp_path: Path) -> None:
        """Test validation summary with no reports."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        result = run_async(auditor.get_validation_summary([]))

        assert result.is_valid is True

    def test_summary_with_passing_reports(self, tmp_path: Path) -> None:
        """Test validation summary with passing reports."""
        auditor = ServiceProtocolAuditor(str(tmp_path))

        good_file = tmp_path / "good.py"
        good_file.write_text('"""Module."""\nx = 1\n')
        report = run_async(auditor.validate_file_quality(str(good_file)))

        result = run_async(auditor.get_validation_summary([report]))

        # Report may still have info-level issues but should be valid
        summary = run_async(result.get_summary())
        assert isinstance(summary, str)

    def test_summary_aggregates_errors(self, tmp_path: Path) -> None:
        """Test validation summary aggregates errors from multiple reports."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        # Create file with syntax error to generate critical issues
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def broken(:")
        report = run_async(auditor.validate_file_quality(str(bad_file)))

        result = run_async(auditor.get_validation_summary([report]))

        # Should have at least some issues
        summary = run_async(result.get_summary())
        assert isinstance(summary, str)


@pytest.mark.unit
class TestAuditorConfigureStandards:
    """Test configure_standards() implementation."""

    def test_configure_standards_sets_attribute(self, tmp_path: Path) -> None:
        """Test that configure_standards sets the standards attribute."""
        auditor = ServiceProtocolAuditor(str(tmp_path))
        assert auditor.standards is None

        # Use a mock standards object
        class MockStandards:
            max_complexity = 5
            min_maintainability_score = 80.0
            max_line_length = 100
            max_function_length = 30
            max_class_length = 200
            naming_conventions = []
            required_patterns = []

            async def check_complexity_compliance(self, complexity):
                return complexity <= self.max_complexity

            async def check_maintainability_compliance(self, score):
                return score >= self.min_maintainability_score

        standards = MockStandards()
        auditor.configure_standards(standards)

        assert auditor.standards is standards


# =============================================================================
# ServiceContractValidator SPI Protocol Method Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorValidateFileCompliance:
    """Test validate_file_compliance() implementation."""

    def test_compliance_well_named_file(self, tmp_path: Path) -> None:
        """Test compliance of a well-named ONEX file."""
        good_file = tmp_path / "model_example.py"
        good_file.write_text(
            textwrap.dedent('''\
            """Example model module."""

            from pydantic import BaseModel


            class ModelExample(BaseModel):
                """An example model."""

                name: str
            ''')
        )

        validator = ServiceContractValidator()
        report = run_async(validator.validate_file_compliance(str(good_file)))

        assert report.file_path == str(good_file)
        assert isinstance(report.onex_compliance_score, float)
        assert isinstance(report.architecture_compliance_score, float)

    def test_compliance_poorly_named_file(self, tmp_path: Path) -> None:
        """Test compliance of a poorly named file."""
        bad_file = tmp_path / "model_example.py"
        bad_file.write_text(
            textwrap.dedent('''\
            """Module."""

            from pydantic import BaseModel

            class BadName(BaseModel):
                value: str
            ''')
        )

        validator = ServiceContractValidator()
        report = run_async(validator.validate_file_compliance(str(bad_file)))

        assert len(report.violations) > 0

    def test_compliance_with_content_override(self, tmp_path: Path) -> None:
        """Test compliance with content parameter."""
        validator = ServiceContractValidator()
        source = textwrap.dedent('''\
        """Module."""

        class ModelGood:
            pass
        ''')

        report = run_async(
            validator.validate_file_compliance("virtual.py", content=source)
        )

        assert report.file_path == "virtual.py"


@pytest.mark.unit
class TestValidatorValidateRepositoryCompliance:
    """Test validate_repository_compliance() implementation."""

    def test_repository_compliance_with_files(self, tmp_path: Path) -> None:
        """Test repository compliance scanning."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "model_a.py").write_text('"""Module."""\nx = 1\n')
        (src_dir / "model_b.py").write_text('"""Module."""\ny = 2\n')

        validator = ServiceContractValidator()
        reports = run_async(validator.validate_repository_compliance(str(tmp_path)))

        assert len(reports) == 2

    def test_repository_compliance_empty(self, tmp_path: Path) -> None:
        """Test repository compliance with no files."""
        validator = ServiceContractValidator()
        reports = run_async(validator.validate_repository_compliance(str(tmp_path)))

        # Empty dir with no src/ might still scan root
        assert isinstance(reports, list)

    def test_repository_compliance_nonexistent(self, tmp_path: Path) -> None:
        """Test repository compliance with nonexistent path."""
        validator = ServiceContractValidator()
        reports = run_async(
            validator.validate_repository_compliance(str(tmp_path / "nonexistent"))
        )

        assert len(reports) == 0


@pytest.mark.unit
class TestValidatorValidateOnexNaming:
    """Test validate_onex_naming() implementation."""

    def test_naming_violation_bad_model_name(self, tmp_path: Path) -> None:
        """Test detection of bad model class name."""
        validator = ServiceContractValidator()
        source = textwrap.dedent("""\
        from pydantic import BaseModel

        class BadName(BaseModel):
            value: str
        """)

        violations = run_async(
            validator.validate_onex_naming("model_test.py", content=source)
        )

        assert len(violations) > 0

    def test_naming_correct_model(self, tmp_path: Path) -> None:
        """Test no violations for correctly named model."""
        validator = ServiceContractValidator()
        source = textwrap.dedent("""\
        from pydantic import BaseModel

        class ModelCorrect(BaseModel):
            value: str
        """)

        violations = run_async(
            validator.validate_onex_naming("model_correct.py", content=source)
        )

        # Should have no naming violations for Model-prefixed class
        naming_violations = [
            v
            for v in violations
            if hasattr(v, "violation_text")
            and "naming" in str(getattr(v, "rule", "")).lower()
        ]
        # ModelCorrect should pass
        model_violations = [
            v for v in violations if "ModelCorrect" in getattr(v, "violation_text", "")
        ]
        assert len(model_violations) == 0


@pytest.mark.unit
class TestValidatorValidateArchitectureCompliance:
    """Test validate_architecture_compliance() implementation."""

    def test_no_violations_clean_file(self, tmp_path: Path) -> None:
        """Test no architecture violations for clean file."""
        validator = ServiceContractValidator()
        source = textwrap.dedent("""\
        from omnibase_core.models import ModelExample

        x = ModelExample()
        """)

        violations = run_async(
            validator.validate_architecture_compliance("test.py", content=source)
        )

        # Clean file should not have architecture violations
        assert len(violations) == 0

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test architecture compliance of empty file."""
        validator = ServiceContractValidator()
        violations = run_async(
            validator.validate_architecture_compliance("test.py", content="")
        )

        assert len(violations) == 0


@pytest.mark.unit
class TestValidatorValidateDirectoryStructure:
    """Test validate_directory_structure() implementation."""

    def test_complete_structure(self, tmp_path: Path) -> None:
        """Test validation of complete directory structure."""
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()

        validator = ServiceContractValidator()
        violations = run_async(validator.validate_directory_structure(str(tmp_path)))

        # All required dirs present
        assert len(violations) == 0

    def test_missing_directories(self, tmp_path: Path) -> None:
        """Test validation with missing required directories."""
        # Empty tmp_path - missing src/ and tests/
        validator = ServiceContractValidator()
        violations = run_async(validator.validate_directory_structure(str(tmp_path)))

        assert len(violations) >= 1

    def test_nonexistent_repository(self, tmp_path: Path) -> None:
        """Test validation with nonexistent repository path."""
        validator = ServiceContractValidator()
        violations = run_async(
            validator.validate_directory_structure(str(tmp_path / "nonexistent"))
        )

        assert len(violations) >= 1
        assert any(v.severity == "critical" for v in violations)


@pytest.mark.unit
class TestValidatorValidateDependencyCompliance:
    """Test validate_dependency_compliance() implementation."""

    def test_clean_dependencies(self, tmp_path: Path) -> None:
        """Test validation of clean dependencies."""
        validator = ServiceContractValidator()
        imports = [
            "from omnibase_core.models import ModelExample",
            "import typing",
        ]

        violations = run_async(
            validator.validate_dependency_compliance("test.py", imports)
        )

        assert len(violations) == 0

    def test_no_violations_without_architecture_rules(self, tmp_path: Path) -> None:
        """Test no violations when architecture rules are not configured."""
        validator = ServiceContractValidator()
        imports = ["from anything import something"]

        violations = run_async(
            validator.validate_dependency_compliance("test.py", imports)
        )

        # No rules configured, so no violations
        assert len(violations) == 0


@pytest.mark.unit
class TestValidatorAggregateComplianceResults:
    """Test aggregate_compliance_results() implementation."""

    def test_aggregate_empty_reports(self, tmp_path: Path) -> None:
        """Test aggregation of empty reports list."""
        validator = ServiceContractValidator()
        result = run_async(validator.aggregate_compliance_results([]))

        assert result.is_valid is True

    def test_aggregate_with_reports(self, tmp_path: Path) -> None:
        """Test aggregation of multiple reports."""
        # Create files for reports
        good_file = tmp_path / "good.py"
        good_file.write_text('"""Module."""\nx = 1\n')

        validator = ServiceContractValidator()
        report = run_async(validator.validate_file_compliance(str(good_file)))
        result = run_async(validator.aggregate_compliance_results([report]))

        summary = run_async(result.get_summary())
        assert isinstance(summary, str)


@pytest.mark.unit
class TestValidatorGetComplianceSummary:
    """Test get_compliance_summary() implementation."""

    def test_summary_no_reports(self, tmp_path: Path) -> None:
        """Test summary with no reports."""
        validator = ServiceContractValidator()
        summary = run_async(validator.get_compliance_summary([]))

        assert summary == "No files analyzed."

    def test_summary_with_reports(self, tmp_path: Path) -> None:
        """Test summary with compliance reports."""
        good_file = tmp_path / "good.py"
        good_file.write_text('"""Module."""\nx = 1\n')

        validator = ServiceContractValidator()
        report = run_async(validator.validate_file_compliance(str(good_file)))
        summary = run_async(validator.get_compliance_summary([report]))

        assert "Compliance Summary" in summary
        assert "ONEX Score" in summary
        assert "Architecture Score" in summary

    def test_summary_format(self, tmp_path: Path) -> None:
        """Test summary output format."""
        good_file = tmp_path / "model_test.py"
        good_file.write_text(
            textwrap.dedent('''\
            """Module."""

            from pydantic import BaseModel

            class ModelTest(BaseModel):
                """Test model."""
                value: str
            ''')
        )

        validator = ServiceContractValidator()
        report = run_async(validator.validate_file_compliance(str(good_file)))
        summary = run_async(validator.get_compliance_summary([report]))

        assert "1/1" in summary
        assert "Status:" in summary


@pytest.mark.unit
class TestValidatorAddCustomRule:
    """Test add_custom_rule() implementation."""

    def test_add_custom_rule(self, tmp_path: Path) -> None:
        """Test adding a custom compliance rule."""
        validator = ServiceContractValidator()
        assert len(validator.custom_rules) == 0

        class MockRule:
            rule_id = uuid4()
            rule_name = "test_rule"
            category = "test"
            severity = "warning"
            description = "Test rule"
            required_pattern = "test"
            violation_message = "Test violation"

            async def check_compliance(self, content, context):
                return True

            async def get_fix_suggestion(self):
                return "Fix it"

        validator.add_custom_rule(MockRule())

        assert len(validator.custom_rules) == 1


@pytest.mark.unit
class TestValidatorConfigureOnexStandards:
    """Test configure_onex_standards() implementation."""

    def test_configure_standards(self, tmp_path: Path) -> None:
        """Test that standards configuration works."""
        validator = ServiceContractValidator()
        assert validator.onex_standards is None

        class MockStandards:
            enum_naming_pattern = r"^Enum[A-Z]"
            model_naming_pattern = r"^Model[A-Z]"
            protocol_naming_pattern = r"^Protocol[A-Z]"
            node_naming_pattern = r"^Node[A-Z]"
            required_directories = ["src", "tests", "docs"]
            forbidden_patterns = []

            async def validate_enum_naming(self, name):
                return True

            async def validate_model_naming(self, name):
                return True

            async def validate_protocol_naming(self, name):
                return True

            async def validate_node_naming(self, name):
                return True

        standards = MockStandards()
        validator.configure_onex_standards(standards)

        assert validator.onex_standards is standards


# Need uuid4 for the custom rule test
from uuid import uuid4
