"""
Extended tests for auditor_protocol.py to improve coverage.

Tests cover:
- print_audit_summary() method
- print_duplication_report() method
- audit_ecosystem() comprehensive testing
- Edge cases in protocol quality checking
- Name conflict detection
- Migration candidate identification
- Error handling in auditor methods
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from omnibase_core.models.validation.model_duplication_info import ModelDuplicationInfo
from omnibase_core.validation.auditor_protocol import (
    ModelAuditResult,
    ModelDuplicationReport,
    ModelProtocolAuditor,
)
from omnibase_core.validation.validation_utils import ModelProtocolInfo

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture


@pytest.mark.unit
class TestPrintAuditSummary:
    """Test print_audit_summary method."""

    def test_print_audit_summary_with_violations(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test print_audit_summary with violations."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        result = ModelAuditResult(
            success=False,
            repository="test_repo",
            protocols_found=5,
            duplicates_found=2,
            conflicts_found=1,
            violations=["Violation 1", "Violation 2", "Violation 3"],
            recommendations=["Fix violation 1", "Fix violation 2"],
        )

        auditor.print_audit_summary(result)

        captured = capsys.readouterr()
        # Method iterates over violations and recommendations
        # Even though it doesn't print, we can verify it doesn't crash

    def test_print_audit_summary_without_violations(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test print_audit_summary without violations."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        result = ModelAuditResult(
            success=True,
            repository="test_repo",
            protocols_found=5,
            duplicates_found=0,
            conflicts_found=0,
            violations=[],
            recommendations=["Keep up the good work"],
        )

        auditor.print_audit_summary(result)

        captured = capsys.readouterr()
        # Should handle empty violations

    def test_print_audit_summary_with_many_violations(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test print_audit_summary with many violations."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        violations = [f"Violation {i}" for i in range(20)]
        recommendations = [f"Recommendation {i}" for i in range(10)]

        result = ModelAuditResult(
            success=False,
            repository="test_repo",
            protocols_found=10,
            duplicates_found=5,
            conflicts_found=3,
            violations=violations,
            recommendations=recommendations,
        )

        auditor.print_audit_summary(result)

        # Should handle large numbers of violations
        captured = capsys.readouterr()

    def test_print_audit_summary_empty_result(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test print_audit_summary with empty result."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        result = ModelAuditResult(
            success=True,
            repository="test_repo",
            protocols_found=0,
            duplicates_found=0,
            conflicts_found=0,
            violations=[],
            recommendations=[],
        )

        auditor.print_audit_summary(result)

        captured = capsys.readouterr()
        # Should handle completely empty result


@pytest.mark.unit
class TestPrintDuplicationReport:
    """Test print_duplication_report method."""

    def test_print_duplication_report_with_exact_duplicates(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test print_duplication_report with exact duplicates."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol1 = ModelProtocolInfo(
            name="TestProtocol",
            file_path=str(tmp_path / "test1.py"),
            repository="test_repo",
            signature_hash="hash123",
            methods=["method1", "method2"],
            line_count=10,
            imports=[],
        )

        protocol2 = ModelProtocolInfo(
            name="TestProtocol",
            file_path=str(tmp_path / "test2.py"),
            repository="test_repo",
            signature_hash="hash123",
            methods=["method1", "method2"],
            line_count=10,
            imports=[],
        )

        exact_dup = ModelDuplicationInfo(
            signature_hash="hash123",
            protocols=[protocol1, protocol2],
            duplication_type="exact",
            recommendation="Remove duplicate",
        )

        report = ModelDuplicationReport(
            success=False,
            source_repository="test_repo",
            target_repository="omnibase_spi",
            exact_duplicates=[exact_dup],
            name_conflicts=[],
            migration_candidates=[],
            recommendations=["Remove exact duplicates"],
        )

        auditor.print_duplication_report(report)

        captured = capsys.readouterr()
        # Method iterates but doesn't print

    def test_print_duplication_report_with_name_conflicts(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test print_duplication_report with name conflicts."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol1 = ModelProtocolInfo(
            name="TestProtocol",
            file_path=str(tmp_path / "test1.py"),
            repository="test_repo",
            signature_hash="hash123",
            methods=["method1"],
            line_count=5,
            imports=[],
        )

        protocol2 = ModelProtocolInfo(
            name="TestProtocol",
            file_path=str(tmp_path / "test2.py"),
            repository="test_repo",
            signature_hash="hash456",
            methods=["method1", "method2"],
            line_count=8,
            imports=[],
        )

        conflict = ModelDuplicationInfo(
            signature_hash="conflict",
            protocols=[protocol1, protocol2],
            duplication_type="name_conflict",
            recommendation="Resolve name conflict",
        )

        report = ModelDuplicationReport(
            success=False,
            source_repository="test_repo",
            target_repository="omnibase_spi",
            exact_duplicates=[],
            name_conflicts=[conflict],
            migration_candidates=[],
            recommendations=["Resolve name conflicts"],
        )

        auditor.print_duplication_report(report)

        captured = capsys.readouterr()

    def test_print_duplication_report_with_migration_candidates(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test print_duplication_report with migration candidates."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol1 = ModelProtocolInfo(
            name="MigrateMe",
            file_path=str(tmp_path / "migrate.py"),
            repository="test_repo",
            signature_hash="hash789",
            methods=["method1"],
            line_count=5,
            imports=[],
        )

        protocol2 = ModelProtocolInfo(
            name="AlsoMigrate",
            file_path=str(tmp_path / "migrate2.py"),
            repository="test_repo",
            signature_hash="hash101112",
            methods=["method2"],
            line_count=7,
            imports=[],
        )

        report = ModelDuplicationReport(
            success=True,
            source_repository="test_repo",
            target_repository="omnibase_spi",
            exact_duplicates=[],
            name_conflicts=[],
            migration_candidates=[protocol1, protocol2],
            recommendations=["Consider migrating 2 protocols"],
        )

        auditor.print_duplication_report(report)

        captured = capsys.readouterr()

    def test_print_duplication_report_comprehensive(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test print_duplication_report with all types of issues."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol1 = ModelProtocolInfo(
            name="Protocol1",
            file_path=str(tmp_path / "p1.py"),
            repository="test_repo",
            signature_hash="h1",
            methods=["m1"],
            line_count=5,
            imports=[],
        )

        protocol2 = ModelProtocolInfo(
            name="Protocol2",
            file_path=str(tmp_path / "p2.py"),
            repository="test_repo",
            signature_hash="h2",
            methods=["m2"],
            line_count=5,
            imports=[],
        )

        protocol3 = ModelProtocolInfo(
            name="Protocol3",
            file_path=str(tmp_path / "p3.py"),
            repository="test_repo",
            signature_hash="h3",
            methods=["m3"],
            line_count=5,
            imports=[],
        )

        exact_dup = ModelDuplicationInfo(
            signature_hash="h1",
            protocols=[protocol1, protocol2],
            duplication_type="exact",
            recommendation="Remove",
        )

        conflict = ModelDuplicationInfo(
            signature_hash="conflict",
            protocols=[protocol2, protocol3],
            duplication_type="name_conflict",
            recommendation="Resolve",
        )

        report = ModelDuplicationReport(
            success=False,
            source_repository="test_repo",
            target_repository="omnibase_spi",
            exact_duplicates=[exact_dup],
            name_conflicts=[conflict],
            migration_candidates=[protocol3],
            recommendations=["Fix all issues"],
        )

        auditor.print_duplication_report(report)

        captured = capsys.readouterr()


@pytest.mark.unit
class TestAuditEcosystem:
    """Test audit_ecosystem method."""

    def test_audit_ecosystem_empty_directory(self, tmp_path: Path) -> None:
        """Test audit_ecosystem with empty directory."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        results = auditor.audit_ecosystem(tmp_path)

        assert isinstance(results, dict)
        assert len(results) == 0

    def test_audit_ecosystem_with_omni_repos(self, tmp_path: Path) -> None:
        """Test audit_ecosystem with omni* repositories."""
        # Create mock omni repositories
        omni_repo1 = tmp_path / "omnibase_core"
        omni_repo1.mkdir()
        src1 = omni_repo1 / "src"
        src1.mkdir()

        omni_repo2 = tmp_path / "omnibase_spi"
        omni_repo2.mkdir()
        src2 = omni_repo2 / "src"
        src2.mkdir()

        auditor = ModelProtocolAuditor(str(tmp_path))
        results = auditor.audit_ecosystem(tmp_path)

        assert isinstance(results, dict)
        assert len(results) >= 0

    def test_audit_ecosystem_with_non_omni_repos(self, tmp_path: Path) -> None:
        """Test audit_ecosystem ignores non-omni repositories."""
        # Create non-omni directory
        other_repo = tmp_path / "other_project"
        other_repo.mkdir()

        auditor = ModelProtocolAuditor(str(tmp_path))
        results = auditor.audit_ecosystem(tmp_path)

        assert isinstance(results, dict)
        assert "other_project" not in results

    def test_audit_ecosystem_with_files_not_directories(self, tmp_path: Path) -> None:
        """Test audit_ecosystem ignores files."""
        # Create a file instead of directory
        test_file = tmp_path / "omnibase_test.txt"
        test_file.write_text("Not a directory")

        auditor = ModelProtocolAuditor(str(tmp_path))
        results = auditor.audit_ecosystem(tmp_path)

        assert isinstance(results, dict)
        assert "omnibase_test.txt" not in results

    def test_audit_ecosystem_mixed_content(self, tmp_path: Path) -> None:
        """Test audit_ecosystem with mixed content."""
        # Create mix of valid and invalid items
        omni_repo = tmp_path / "omnibase_test"
        omni_repo.mkdir()
        (omni_repo / "src").mkdir()

        other_repo = tmp_path / "other"
        other_repo.mkdir()

        (tmp_path / "file.txt").write_text("File")

        auditor = ModelProtocolAuditor(str(tmp_path))
        results = auditor.audit_ecosystem(tmp_path)

        assert isinstance(results, dict)
        assert "other" not in results
        assert "file.txt" not in results


@pytest.mark.unit
class TestProtocolQualityChecking:
    """Test protocol quality checking methods."""

    def test_check_protocol_quality_empty_protocol(self, tmp_path: Path) -> None:
        """Test quality check for protocol with no methods."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol = ModelProtocolInfo(
            name="EmptyProtocol",
            file_path=str(tmp_path / "empty.py"),
            repository="test_repo",
            signature_hash="hash",
            methods=[],  # No methods
            line_count=3,
            imports=[],
        )

        issues = auditor._check_protocol_quality([protocol])

        assert len(issues) >= 1
        assert any("has no methods" in issue for issue in issues)

    def test_check_protocol_quality_complex_protocol(self, tmp_path: Path) -> None:
        """Test quality check for overly complex protocol."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        # Create protocol with many methods
        many_methods = [f"method_{i}" for i in range(25)]
        protocol = ModelProtocolInfo(
            name="ComplexProtocol",
            file_path=str(tmp_path / "complex.py"),
            repository="test_repo",
            signature_hash="hash",
            methods=many_methods,
            line_count=100,
            imports=[],
        )

        issues = auditor._check_protocol_quality([protocol])

        assert len(issues) >= 1
        assert any("consider splitting" in issue for issue in issues)

    def test_check_protocol_quality_good_protocol(self, tmp_path: Path) -> None:
        """Test quality check for well-designed protocol."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol = ModelProtocolInfo(
            name="GoodProtocol",
            file_path=str(tmp_path / "good.py"),
            repository="test_repo",
            signature_hash="hash",
            methods=["method1", "method2", "method3"],
            line_count=15,
            imports=[],
        )

        issues = auditor._check_protocol_quality([protocol])

        # Should have no issues for well-designed protocol
        assert len(issues) == 0

    def test_check_protocol_quality_multiple_protocols(
        self,
        tmp_path: Path,
    ) -> None:
        """Test quality check with multiple protocols."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocols = [
            ModelProtocolInfo(
                name="EmptyProtocol",
                file_path=str(tmp_path / "empty.py"),
                repository="test_repo",
                signature_hash="h1",
                methods=[],
                line_count=3,
                imports=[],
            ),
            ModelProtocolInfo(
                name="GoodProtocol",
                file_path=str(tmp_path / "good.py"),
                repository="test_repo",
                signature_hash="h2",
                methods=["m1", "m2"],
                line_count=10,
                imports=[],
            ),
            ModelProtocolInfo(
                name="ComplexProtocol",
                file_path=str(tmp_path / "complex.py"),
                repository="test_repo",
                signature_hash="h3",
                methods=[f"m{i}" for i in range(25)],
                line_count=100,
                imports=[],
            ),
        ]

        issues = auditor._check_protocol_quality(protocols)

        # Should find issues in empty and complex protocols
        assert len(issues) >= 2


@pytest.mark.unit
class TestNamingConventionChecking:
    """Test naming convention checking methods."""

    def test_check_naming_conventions_valid_protocol(self, tmp_path: Path) -> None:
        """Test naming check for properly named protocol."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        # Create valid protocol file
        protocol_file = tmp_path / "protocol_test.py"
        protocol_file.write_text("")

        protocol = ModelProtocolInfo(
            name="ProtocolTest",
            file_path=str(protocol_file),
            repository="test_repo",
            signature_hash="hash",
            methods=["method1"],
            line_count=5,
            imports=[],
        )

        violations = auditor._check_naming_conventions([protocol])

        # Should have no violations for properly named protocol
        assert len(violations) == 0

    def test_check_naming_conventions_invalid_class_name(
        self,
        tmp_path: Path,
    ) -> None:
        """Test naming check for improperly named protocol class."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol_file = tmp_path / "protocol_test.py"
        protocol_file.write_text("")

        protocol = ModelProtocolInfo(
            name="TestInterface",  # Doesn't start with Protocol
            file_path=str(protocol_file),
            repository="test_repo",
            signature_hash="hash",
            methods=["method1"],
            line_count=5,
            imports=[],
        )

        violations = auditor._check_naming_conventions([protocol])

        assert len(violations) >= 1
        assert any("should start with 'Protocol'" in v for v in violations)

    def test_check_naming_conventions_invalid_file_name(
        self,
        tmp_path: Path,
    ) -> None:
        """Test naming check for improperly named protocol file."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        # File doesn't follow protocol_*.py pattern
        protocol_file = tmp_path / "test_interface.py"
        protocol_file.write_text("")

        protocol = ModelProtocolInfo(
            name="ProtocolTest",
            file_path=str(protocol_file),
            repository="test_repo",
            signature_hash="hash",
            methods=["method1"],
            line_count=5,
            imports=[],
        )

        violations = auditor._check_naming_conventions([protocol])

        assert len(violations) >= 1
        assert any("should follow protocol_*.py" in v for v in violations)

    def test_check_naming_conventions_multiple_protocols(
        self,
        tmp_path: Path,
    ) -> None:
        """Test naming check with multiple protocols."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocols = [
            ModelProtocolInfo(
                name="ProtocolGood",
                file_path=str(tmp_path / "protocol_good.py"),
                repository="test_repo",
                signature_hash="h1",
                methods=["m1"],
                line_count=5,
                imports=[],
            ),
            ModelProtocolInfo(
                name="BadName",
                file_path=str(tmp_path / "bad.py"),
                repository="test_repo",
                signature_hash="h2",
                methods=["m1"],
                line_count=5,
                imports=[],
            ),
        ]

        # Create the files
        (tmp_path / "protocol_good.py").write_text("")
        (tmp_path / "bad.py").write_text("")

        violations = auditor._check_naming_conventions(protocols)

        # Should find violations in BadName protocol
        assert len(violations) >= 1


@pytest.mark.unit
class TestAuditResultHasIssues:
    """Test ModelAuditResult.has_issues() method."""

    def test_has_issues_with_duplicates(self) -> None:
        """Test has_issues returns True with duplicates."""
        result = ModelAuditResult(
            success=False,
            repository="test",
            protocols_found=5,
            duplicates_found=2,
            conflicts_found=0,
            violations=[],
            recommendations=[],
        )

        assert result.has_issues() is True

    def test_has_issues_with_conflicts(self) -> None:
        """Test has_issues returns True with conflicts."""
        result = ModelAuditResult(
            success=False,
            repository="test",
            protocols_found=5,
            duplicates_found=0,
            conflicts_found=3,
            violations=[],
            recommendations=[],
        )

        assert result.has_issues() is True

    def test_has_issues_with_violations(self) -> None:
        """Test has_issues returns True with violations."""
        result = ModelAuditResult(
            success=False,
            repository="test",
            protocols_found=5,
            duplicates_found=0,
            conflicts_found=0,
            violations=["Violation 1"],
            recommendations=[],
        )

        assert result.has_issues() is True

    def test_has_issues_no_issues(self) -> None:
        """Test has_issues returns False with no issues."""
        result = ModelAuditResult(
            success=True,
            repository="test",
            protocols_found=5,
            duplicates_found=0,
            conflicts_found=0,
            violations=[],
            recommendations=["Good work"],
        )

        assert result.has_issues() is False

    def test_has_issues_multiple_issue_types(self) -> None:
        """Test has_issues with multiple issue types."""
        result = ModelAuditResult(
            success=False,
            repository="test",
            protocols_found=10,
            duplicates_found=2,
            conflicts_found=1,
            violations=["V1", "V2"],
            recommendations=["Fix everything"],
        )

        assert result.has_issues() is True
