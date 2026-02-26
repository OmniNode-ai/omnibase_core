# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Protocol auditor for detecting duplicates and violations across omni* ecosystem.

Implements ProtocolQualityValidator for SPI compliance.
"""

from __future__ import annotations

import ast
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.errors.exception_base import (
    ExceptionConfigurationError,
    ExceptionInputValidationError,
)
from omnibase_core.models.validation.model_audit_result import ModelAuditResult
from omnibase_core.models.validation.model_duplication_report import (
    ModelDuplicationReport,
)
from omnibase_core.validation.validator_utils import (
    ModelDuplicationInfo,
    ModelProtocolInfo,
    determine_repository_name,
    extract_protocols_from_directory,
    validate_directory_path,
)

if TYPE_CHECKING:
    from omnibase_spi.protocols.validation.protocol_quality_validator import (
        ProtocolQualityIssue,
        ProtocolQualityMetrics,
        ProtocolQualityReport,
        ProtocolQualityStandards,
    )
    from omnibase_spi.protocols.validation.protocol_validation import (
        ProtocolValidationResult,
    )


# =============================================================================
# Concrete implementations satisfying SPI protocol interfaces
# =============================================================================

# ONEX naming patterns for quality checks
_PROTOCOL_NAME_PATTERN = re.compile(r"^Protocol[A-Z][a-zA-Z0-9]*$")
_MODEL_NAME_PATTERN = re.compile(r"^Model[A-Z][a-zA-Z0-9]*$")
_ENUM_NAME_PATTERN = re.compile(r"^Enum[A-Z][a-zA-Z0-9]*$")
_NODE_NAME_PATTERN = re.compile(
    r"^Node[A-Z][a-zA-Z0-9]*(Effect|Compute|Reducer|Orchestrator)$"
)
_SERVICE_NAME_PATTERN = re.compile(r"^Service[A-Z][a-zA-Z0-9]*$")

# Complexity thresholds
_DEFAULT_MAX_COMPLEXITY = 10
_DEFAULT_MAX_FUNCTION_LENGTH = 50
_DEFAULT_MAX_CLASS_LENGTH = 300
_DEFAULT_MAX_LINE_LENGTH = 120
_DEFAULT_MIN_MAINTAINABILITY = 50.0


@dataclass
class _QualityMetrics:
    """Concrete implementation of ProtocolQualityMetrics."""

    cyclomatic_complexity: int = 1
    maintainability_index: float = 100.0
    lines_of_code: int = 0
    code_duplication_percentage: float = 0.0
    test_coverage_percentage: float = 0.0
    technical_debt_score: float = 0.0

    async def get_complexity_rating(self) -> str:
        """Return letter grade based on cyclomatic complexity."""
        if self.cyclomatic_complexity <= 5:
            return "A"
        if self.cyclomatic_complexity <= 10:
            return "B"
        if self.cyclomatic_complexity <= 20:
            return "C"
        if self.cyclomatic_complexity <= 50:
            return "D"
        return "F"


@dataclass
class _QualityIssue:
    """Concrete implementation of ProtocolQualityIssue."""

    issue_type: str = ""
    severity: str = "info"
    file_path: str = ""
    line_number: int = 0
    column_number: int = 0
    message: str = ""
    rule_id: str = ""
    suggested_fix: str | None = None

    async def get_issue_summary(self) -> str:
        """Return a one-line summary of the issue."""
        location = f"{self.file_path}:{self.line_number}"
        return f"[{self.severity.upper()}] {location} - {self.message}"


@dataclass
class _QualityReport:
    """Concrete implementation of ProtocolQualityReport."""

    file_path: str = ""
    metrics: _QualityMetrics = field(default_factory=_QualityMetrics)
    issues: list[_QualityIssue] = field(default_factory=list)
    standards_compliance: bool = True
    overall_score: float = 100.0
    recommendations: list[str] = field(default_factory=list)

    async def get_critical_issues(self) -> list[_QualityIssue]:
        """Return only critical-severity issues."""
        return [i for i in self.issues if i.severity == "critical"]


@dataclass
class _ValidationResult:
    """Concrete implementation of ProtocolValidationResult for summaries."""

    is_valid: bool = True
    protocol_name: str = "ProtocolQualityValidator"
    implementation_name: str = "ServiceProtocolAuditor"
    errors: list[object] = field(default_factory=list)
    warnings: list[object] = field(default_factory=list)

    def add_error(
        self,
        error_type: str,
        message: str,
        context: dict[str, object] | None = None,
        severity: str | None = None,
    ) -> None:
        """Add an error to the result."""
        self.errors.append(
            {
                "error_type": error_type,
                "message": message,
                "severity": severity or "error",
            }
        )
        self.is_valid = False

    def add_warning(
        self,
        error_type: str,
        message: str,
        context: dict[str, object] | None = None,
    ) -> None:
        """Add a warning to the result."""
        self.warnings.append({"error_type": error_type, "message": message})

    async def get_summary(self) -> str:
        """Get a summary of the validation result."""
        status = "PASS" if self.is_valid else "FAIL"
        return f"{status}: {len(self.errors)} error(s), {len(self.warnings)} warning(s)"


# Configure logger for this module
logger = logging.getLogger(__name__)


class ServiceProtocolAuditor:
    """
    Centralized protocol auditing for omni* ecosystem.

    Provides different audit modes:
    - Current repository only (fast)
    - Current repository vs SPI (medium)
    - Full ecosystem scan (comprehensive)

    Implements ProtocolQualityValidator for SPI compliance.

    Thread Safety:
        This class is NOT thread-safe. It maintains mutable instance state
        including configuration options (standards, enable_* flags) that can
        be modified via configure_standards(). Additionally, audit methods
        perform filesystem I/O operations that are not atomic. Each thread
        should use its own instance or wrap access with external locks.
        See docs/guides/THREADING.md for more details.

    .. note::
        Previously named ``ModelProtocolAuditor``. Renamed in v0.4.0
        to follow ONEX naming conventions (OMN-1071). The ``Model``
        prefix is reserved for Pydantic BaseModel classes; ``Service``
        prefix indicates a stateful service class.
    """

    def __init__(
        self,
        repository_path: str = ".",
        standards: ProtocolQualityStandards | None = None,
        enable_complexity_analysis: bool = True,
        enable_duplication_detection: bool = True,
        enable_style_checking: bool = True,
    ):
        try:
            self.repository_path = validate_directory_path(
                Path(repository_path), "repository"
            )
        except ExceptionInputValidationError as e:
            msg = f"Invalid repository configuration: {e}"
            raise ExceptionConfigurationError(msg)

        self.repository_name = determine_repository_name(self.repository_path)

        # Protocol compliance attributes
        self.standards = standards
        self.enable_complexity_analysis = enable_complexity_analysis
        self.enable_duplication_detection = enable_duplication_detection
        self.enable_style_checking = enable_style_checking

        logger.info(
            f"ServiceProtocolAuditor initialized for repository '{self.repository_name}' "
            f"at {self.repository_path}"
        )

    @standard_error_handling("Current repository audit")
    def check_current_repository(self) -> ModelAuditResult:
        """
        Audit protocols in current repository only.

        Fast check for basic protocol issues like:
        - Malformed protocol definitions
        - Missing method implementations
        - Naming convention violations
        """
        src_path = self.repository_path / "src"
        violations = []
        recommendations = []

        if not src_path.exists():
            return ModelAuditResult(
                success=True,
                repository=self.repository_name,
                protocols_found=0,
                duplicates_found=0,
                conflicts_found=0,
                violations=[
                    "No src directory found - repository might not have protocols",
                ],
                recommendations=["Ensure repository follows standard src/ structure"],
            )

        # Find all protocols in current repository
        protocols = extract_protocols_from_directory(src_path)

        # Check for local duplicates within the repository
        local_duplicates = self._find_local_duplicates(protocols)

        # Check naming conventions
        naming_violations = self._check_naming_conventions(protocols)

        # Check protocol quality
        quality_issues = self._check_protocol_quality(protocols)

        violations.extend(naming_violations)
        violations.extend(quality_issues)

        if local_duplicates:
            violations.extend(
                [f"Local duplicate: {dup.signature_hash}" for dup in local_duplicates]
            )

        # Generate recommendations
        if protocols:
            recommendations.append(
                f"Consider migrating {len(protocols)} protocols to omnibase_spi"
            )

        return ModelAuditResult(
            success=len(violations) == 0,
            repository=self.repository_name,
            protocols_found=len(protocols),
            duplicates_found=len(local_duplicates),
            conflicts_found=0,  # No external conflicts in single-repo audit
            violations=violations,
            recommendations=recommendations,
        )

    @standard_error_handling("SPI compatibility check")
    def check_against_spi(
        self, spi_path: str = "../omnibase_spi"
    ) -> ModelDuplicationReport:
        """
        Check current repository protocols against omnibase_spi for duplicates.

        Medium-scope check that identifies:
        - Exact duplicates with SPI
        - Name conflicts with SPI
        - Migration opportunities
        """
        # Validate SPI path
        try:
            validated_spi_path = validate_directory_path(Path(spi_path), "SPI")
        except ExceptionInputValidationError as e:
            msg = f"Invalid SPI path configuration: {e}"
            raise ExceptionConfigurationError(msg)

        src_path = self.repository_path / "src"
        spi_protocols_path = validated_spi_path / "src" / "omnibase_spi" / "protocols"

        # Validate SPI protocols directory exists
        if not spi_protocols_path.exists():
            logger.warning(f"SPI protocols directory not found: {spi_protocols_path}")
            # Continue with empty SPI protocols list rather than failing

        # Get protocols from both repositories
        current_protocols = (
            extract_protocols_from_directory(src_path) if src_path.exists() else []
        )
        spi_protocols = (
            extract_protocols_from_directory(spi_protocols_path)
            if spi_protocols_path.exists()
            else []
        )

        # Analyze duplications
        duplications = self._analyze_cross_repo_duplicates(
            current_protocols, spi_protocols
        )

        # Find migration candidates (protocols that should move to SPI)
        migration_candidates = [
            p
            for p in current_protocols
            if not self._has_duplicate_in_spi(p, spi_protocols)
        ]

        recommendations = []
        if duplications["exact_duplicates"]:
            recommendations.append(
                "Remove exact duplicates from current repository - use SPI versions"
            )
        if duplications["name_conflicts"]:
            recommendations.append(
                "Resolve name conflicts by renaming or merging protocols"
            )
        if migration_candidates:
            recommendations.append(
                f"Consider migrating {len(migration_candidates)} unique protocols to SPI"
            )

        return ModelDuplicationReport(
            success=len(duplications["exact_duplicates"]) == 0
            and len(duplications["name_conflicts"]) == 0,
            source_repository=self.repository_name,
            target_repository="omnibase_spi",
            exact_duplicates=duplications["exact_duplicates"],
            name_conflicts=duplications["name_conflicts"],
            migration_candidates=migration_candidates,
            recommendations=recommendations,
        )

    @standard_error_handling("Ecosystem audit")
    def audit_ecosystem(self, omni_root: Path) -> dict[str, ModelAuditResult]:
        """
        Comprehensive audit across all omni* repositories.

        Slow but thorough check that provides complete ecosystem view.
        """
        results = {}

        # Find all omni* repositories
        for repo_path in omni_root.iterdir():
            if not repo_path.is_dir():
                continue

            repo_name = repo_path.name
            if not (repo_name.startswith("omni") or repo_name == "omnibase_spi"):
                continue

            # Audit each repository
            auditor = ServiceProtocolAuditor(str(repo_path))
            result = auditor.check_current_repository()
            results[repo_name] = result

        return results

    def _find_local_duplicates(
        self, protocols: list[ModelProtocolInfo]
    ) -> list[ModelDuplicationInfo]:
        """Find duplicate protocols within the same repository."""
        duplicates = []
        by_signature: dict[str, list[ModelProtocolInfo]] = defaultdict(list)

        for protocol in protocols:
            by_signature[protocol.signature_hash].append(protocol)

        for signature_hash, protocol_group in by_signature.items():
            if len(protocol_group) > 1:
                duplicates.append(
                    ModelDuplicationInfo(
                        signature_hash=signature_hash,
                        protocols=protocol_group,
                        duplication_type="exact",
                        recommendation=f"Merge or remove duplicate {protocol_group[0].name} protocols",
                    )
                )

        return duplicates

    def _check_naming_conventions(
        self, protocols: list[ModelProtocolInfo]
    ) -> list[str]:
        """Check protocol naming conventions."""
        violations = []

        for protocol in protocols:
            # Check class name starts with Protocol
            if not ("Protocol" in protocol.name and protocol.name[0].isupper()):
                violations.append(
                    f"Protocol {protocol.name} should start with 'Protocol'"
                )

            # Check file name follows protocol_*.py pattern
            file_path = Path(protocol.file_path)
            expected_filename = (
                f"protocol_{protocol.name[8:].lower()}.py"  # Remove "Protocol" prefix
            )
            if file_path.name != expected_filename and not file_path.name.startswith(
                "protocol_"
            ):
                violations.append(
                    f"File {file_path.name} should follow protocol_*.py naming pattern"
                )

        return violations

    def _check_protocol_quality(self, protocols: list[ModelProtocolInfo]) -> list[str]:
        """Check protocol implementation quality."""
        issues = []

        for protocol in protocols:
            # Check for empty protocols
            if not protocol.methods:
                issues.append(
                    f"Protocol {protocol.name} has no methods - consider if it's needed"
                )

            # Check for overly complex protocols
            if len(protocol.methods) > 20:
                issues.append(
                    f"Protocol {protocol.name} has {len(protocol.methods)} methods - consider splitting"
                )

        return issues

    def _analyze_cross_repo_duplicates(
        self,
        source_protocols: list[ModelProtocolInfo],
        target_protocols: list[ModelProtocolInfo],
    ) -> dict[str, list[ModelDuplicationInfo]]:
        """Analyze duplications between two sets of protocols."""
        exact_duplicates = []
        name_conflicts = []

        # Group target protocols by signature and name
        target_by_signature = {p.signature_hash: p for p in target_protocols}
        target_by_name = {p.name: p for p in target_protocols}

        for source_protocol in source_protocols:
            # Check for exact duplicates (same signature)
            if source_protocol.signature_hash in target_by_signature:
                target_protocol = target_by_signature[source_protocol.signature_hash]
                exact_duplicates.append(
                    ModelDuplicationInfo(
                        signature_hash=source_protocol.signature_hash,
                        protocols=[source_protocol, target_protocol],
                        duplication_type="exact",
                        recommendation=f"Remove {source_protocol.name} from source - use SPI version",
                    )
                )

            # Check for name conflicts (same name, different signature)
            elif source_protocol.name in target_by_name:
                target_protocol = target_by_name[source_protocol.name]
                if source_protocol.signature_hash != target_protocol.signature_hash:
                    name_conflicts.append(
                        ModelDuplicationInfo(
                            signature_hash="conflict",
                            protocols=[source_protocol, target_protocol],
                            duplication_type="name_conflict",
                            recommendation=f"Resolve name conflict for {source_protocol.name}",
                        )
                    )

        return {"exact_duplicates": exact_duplicates, "name_conflicts": name_conflicts}

    def _has_duplicate_in_spi(
        self, protocol: ModelProtocolInfo, spi_protocols: list[ModelProtocolInfo]
    ) -> bool:
        """Check if protocol has a duplicate in SPI."""
        for spi_protocol in spi_protocols:
            if (
                protocol.signature_hash == spi_protocol.signature_hash
                or protocol.name == spi_protocol.name
            ):
                return True
        return False

    def print_audit_summary(self, result: ModelAuditResult) -> None:
        """Print human-readable audit summary."""

        if result.violations:
            for _violation in result.violations:
                pass

        if result.recommendations:
            for _recommendation in result.recommendations:
                pass

    def print_duplication_report(self, report: ModelDuplicationReport) -> None:
        """Print human-readable duplication report."""

        if report.exact_duplicates:
            for _dup in report.exact_duplicates:
                pass

        if report.name_conflicts:
            for _conflict in report.name_conflicts:
                pass

        if report.migration_candidates:
            for _candidate in report.migration_candidates:
                pass

    # ProtocolQualityValidator interface methods

    def _read_file_content(self, file_path: str, content: str | None) -> str:
        """Read file content from path or return provided content."""
        if content is not None:
            return content
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""

    @staticmethod
    def _compute_cyclomatic_complexity(tree: ast.AST) -> int:
        """Compute aggregate cyclomatic complexity from an AST.

        Counts decision points: if, elif, for, while, except, with, assert,
        boolean operators (and/or), and ternary expressions.
        """
        complexity = 1  # base path
        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # Each 'and'/'or' adds a branch
                complexity += len(node.values) - 1
            elif isinstance(node, ast.IfExp):
                complexity += 1
        return complexity

    @staticmethod
    def _compute_maintainability_index(
        loc: int, complexity: int, num_comments: int
    ) -> float:
        """Compute a simplified maintainability index (0-100 scale).

        Based on a simplified version of the Halstead/MI formula.
        """
        import math

        if loc == 0:
            return 100.0
        volume = loc * math.log2(max(loc, 1))
        comment_ratio = num_comments / max(loc, 1)
        mi = max(
            0.0,
            min(
                100.0,
                171.0
                - 5.2 * math.log(max(volume, 1))
                - 0.23 * complexity
                - 16.2 * math.log(max(loc, 1))
                + 50.0 * math.sqrt(2.46 * comment_ratio),
            ),
        )
        return round(mi, 2)

    async def validate_file_quality(
        self, file_path: str, content: str | None = None
    ) -> ProtocolQualityReport:
        """
        Validate file quality metrics.

        Performs comprehensive quality analysis including complexity, naming,
        documentation, and code smell detection.

        Args:
            file_path: Path to file to validate
            content: Optional file content (reads from file if not provided)

        Returns:
            Quality report with metrics and issues
        """
        source = self._read_file_content(file_path, content)
        metrics = self.calculate_quality_metrics(file_path, source)
        issues: list[_QualityIssue] = []

        # Gather all issue types
        if self.enable_complexity_analysis:
            issues.extend(await self.analyze_complexity(file_path, source))  # type: ignore[arg-type]
        if self.enable_style_checking:
            issues.extend(await self.check_naming_conventions(file_path, source))  # type: ignore[arg-type]
        issues.extend(await self.validate_documentation(file_path, source))  # type: ignore[arg-type]
        issues.extend(self.detect_code_smells(file_path, source))  # type: ignore[arg-type]

        # Determine compliance and score
        critical_count = sum(1 for i in issues if i.severity == "critical")
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        score = max(
            0.0,
            100.0
            - (critical_count * 25.0)
            - (error_count * 10.0)
            - (warning_count * 3.0),
        )
        standards_ok = critical_count == 0 and error_count == 0

        recommendations: list[str] = []
        if metrics.cyclomatic_complexity > _DEFAULT_MAX_COMPLEXITY:
            recommendations.append(
                f"Reduce cyclomatic complexity from {metrics.cyclomatic_complexity} "
                f"to {_DEFAULT_MAX_COMPLEXITY} or below"
            )
        if metrics.maintainability_index < _DEFAULT_MIN_MAINTAINABILITY:
            recommendations.append(
                f"Improve maintainability index from {metrics.maintainability_index:.1f} "
                f"to {_DEFAULT_MIN_MAINTAINABILITY} or above"
            )
        if not source.strip():
            recommendations.append("File is empty or could not be read")

        return _QualityReport(
            file_path=file_path,
            metrics=metrics,  # type: ignore[arg-type]
            issues=issues,  # type: ignore[assignment]
            standards_compliance=standards_ok,
            overall_score=round(score, 2),
            recommendations=recommendations,
        )  # type: ignore[return-value]

    async def validate_directory_quality(
        self, directory_path: str, file_patterns: list[str] | None = None
    ) -> list[ProtocolQualityReport]:
        """
        Validate directory quality by scanning all matching Python files.

        Args:
            directory_path: Path to directory
            file_patterns: Optional glob patterns (defaults to ``["*.py"]``)

        Returns:
            List of quality reports, one per file
        """
        dir_path = Path(directory_path)
        if not dir_path.exists() or not dir_path.is_dir():
            return []

        patterns = file_patterns or ["*.py"]
        files: list[Path] = []
        for pattern in patterns:
            files.extend(dir_path.rglob(pattern))

        reports: list[ProtocolQualityReport] = []
        for f in sorted(set(files)):
            if f.is_file():
                report = await self.validate_file_quality(str(f))
                reports.append(report)
        return reports

    def calculate_quality_metrics(
        self, file_path: str, content: str | None = None
    ) -> ProtocolQualityMetrics:
        """
        Calculate quality metrics for a file using AST analysis.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            Quality metrics including complexity, maintainability, LOC
        """
        source = self._read_file_content(file_path, content)
        if not source.strip():
            return _QualityMetrics()  # type: ignore[return-value]

        lines = source.splitlines()
        loc = len([line for line in lines if line.strip()])
        comment_lines = len([line for line in lines if line.strip().startswith("#")])

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return _QualityMetrics(lines_of_code=loc)  # type: ignore[return-value]

        complexity = self._compute_cyclomatic_complexity(tree)
        maintainability = self._compute_maintainability_index(
            loc, complexity, comment_lines
        )

        return _QualityMetrics(
            cyclomatic_complexity=complexity,
            maintainability_index=maintainability,
            lines_of_code=loc,
            code_duplication_percentage=0.0,
            test_coverage_percentage=0.0,
            technical_debt_score=max(0.0, (complexity - _DEFAULT_MAX_COMPLEXITY) * 2.0)
            if complexity > _DEFAULT_MAX_COMPLEXITY
            else 0.0,
        )  # type: ignore[return-value]

    def detect_code_smells(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolQualityIssue]:
        """
        Detect code smells in a Python file.

        Checks for: overly long functions, overly long classes, too many
        arguments, deeply nested code, and broad exception handlers.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of detected code smells
        """
        source = self._read_file_content(file_path, content)
        if not source.strip():
            return []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return [
                _QualityIssue(
                    issue_type="syntax_error",
                    severity="critical",
                    file_path=file_path,
                    line_number=1,
                    message="File contains syntax errors",
                    rule_id="SMELL001",
                ),
            ]  # type: ignore[list-item]

        issues: list[_QualityIssue] = []

        for node in ast.walk(tree):
            # Long functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = (node.end_lineno or node.lineno) - node.lineno + 1
                if func_lines > _DEFAULT_MAX_FUNCTION_LENGTH:
                    issues.append(
                        _QualityIssue(
                            issue_type="long_function",
                            severity="warning",
                            file_path=file_path,
                            line_number=node.lineno,
                            message=(
                                f"Function '{node.name}' is {func_lines} lines long "
                                f"(max {_DEFAULT_MAX_FUNCTION_LENGTH})"
                            ),
                            rule_id="SMELL002",
                            suggested_fix="Extract helper functions to reduce length",
                        ),
                    )
                # Too many arguments
                arg_count = len(node.args.args)
                if arg_count > 7:
                    issues.append(
                        _QualityIssue(
                            issue_type="too_many_arguments",
                            severity="warning",
                            file_path=file_path,
                            line_number=node.lineno,
                            message=(
                                f"Function '{node.name}' has {arg_count} arguments "
                                f"(max 7)"
                            ),
                            rule_id="SMELL003",
                            suggested_fix="Group related arguments into a dataclass or config object",
                        ),
                    )

            # Long classes
            if isinstance(node, ast.ClassDef):
                class_lines = (node.end_lineno or node.lineno) - node.lineno + 1
                if class_lines > _DEFAULT_MAX_CLASS_LENGTH:
                    issues.append(
                        _QualityIssue(
                            issue_type="long_class",
                            severity="warning",
                            file_path=file_path,
                            line_number=node.lineno,
                            message=(
                                f"Class '{node.name}' is {class_lines} lines long "
                                f"(max {_DEFAULT_MAX_CLASS_LENGTH})"
                            ),
                            rule_id="SMELL004",
                            suggested_fix="Extract related methods into separate classes or mixins",
                        ),
                    )

            # Broad exception handlers
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(
                        _QualityIssue(
                            issue_type="broad_exception",
                            severity="warning",
                            file_path=file_path,
                            line_number=node.lineno,
                            message="Bare except clause catches all exceptions",
                            rule_id="SMELL005",
                            suggested_fix="Catch specific exception types instead of using bare except",
                        ),
                    )
                elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    issues.append(
                        _QualityIssue(
                            issue_type="broad_exception",
                            severity="info",
                            file_path=file_path,
                            line_number=node.lineno,
                            message="Catching broad Exception type",
                            rule_id="SMELL006",
                            suggested_fix="Consider catching more specific exception types",
                        ),
                    )

        return issues  # type: ignore[return-value]

    async def check_naming_conventions(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolQualityIssue]:
        """
        Check naming convention compliance against ONEX standards.

        Validates class names follow ONEX patterns: Model*, Protocol*,
        Enum*, Node*Type, Service*.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of naming convention issues
        """
        source = self._read_file_content(file_path, content)
        if not source.strip():
            return []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        issues: list[_QualityIssue] = []
        path = Path(file_path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            name = node.name
            bases = [ast.unparse(b) for b in node.bases]
            bases_str = " ".join(bases)

            # Check Protocol classes
            if "Protocol" in bases_str and not _PROTOCOL_NAME_PATTERN.match(name):
                if not name.startswith("_"):  # skip private
                    issues.append(
                        _QualityIssue(
                            issue_type="naming",
                            severity="warning",
                            file_path=file_path,
                            line_number=node.lineno,
                            message=(
                                f"Protocol class '{name}' should follow "
                                f"'Protocol<Name>' naming convention"
                            ),
                            rule_id="NAME001",
                            suggested_fix=f"Rename to 'Protocol{name}'",
                        ),
                    )

            # Check BaseModel classes
            if "BaseModel" in bases_str and not _MODEL_NAME_PATTERN.match(name):
                if not name.startswith("_"):
                    issues.append(
                        _QualityIssue(
                            issue_type="naming",
                            severity="warning",
                            file_path=file_path,
                            line_number=node.lineno,
                            message=(
                                f"Pydantic model class '{name}' should follow "
                                f"'Model<Name>' naming convention"
                            ),
                            rule_id="NAME002",
                            suggested_fix=f"Rename to 'Model{name}'",
                        ),
                    )

            # Check file naming for protocol files
            if path.name.startswith("protocol_") and "Protocol" not in name:
                if not name.startswith("_"):
                    issues.append(
                        _QualityIssue(
                            issue_type="naming",
                            severity="info",
                            file_path=file_path,
                            line_number=node.lineno,
                            message=(
                                f"Class '{name}' in protocol file should use "
                                f"Protocol prefix"
                            ),
                            rule_id="NAME003",
                        ),
                    )

        return issues  # type: ignore[return-value]

    async def analyze_complexity(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolQualityIssue]:
        """
        Analyze code complexity at the function level.

        Reports functions with cyclomatic complexity exceeding the threshold.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of complexity issues
        """
        source = self._read_file_content(file_path, content)
        if not source.strip():
            return []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        issues: list[_QualityIssue] = []
        max_complexity = _DEFAULT_MAX_COMPLEXITY
        if self.standards is not None:
            max_complexity = getattr(
                self.standards, "max_complexity", _DEFAULT_MAX_COMPLEXITY
            )

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            func_complexity = self._compute_cyclomatic_complexity(node)
            if func_complexity > max_complexity:
                severity = (
                    "error" if func_complexity > max_complexity * 2 else "warning"
                )
                issues.append(
                    _QualityIssue(
                        issue_type="complexity",
                        severity=severity,
                        file_path=file_path,
                        line_number=node.lineno,
                        message=(
                            f"Function '{node.name}' has cyclomatic complexity "
                            f"{func_complexity} (max {max_complexity})"
                        ),
                        rule_id="CMPLX001",
                        suggested_fix="Break into smaller functions or simplify control flow",
                    ),
                )

        return issues  # type: ignore[return-value]

    async def validate_documentation(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolQualityIssue]:
        """
        Validate documentation quality.

        Checks for missing module docstrings, missing class docstrings,
        and missing function docstrings on public entities.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of documentation issues
        """
        source = self._read_file_content(file_path, content)
        if not source.strip():
            return []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        issues: list[_QualityIssue] = []

        # Check module docstring
        if not ast.get_docstring(tree):
            issues.append(
                _QualityIssue(
                    issue_type="documentation",
                    severity="info",
                    file_path=file_path,
                    line_number=1,
                    message="Module is missing a docstring",
                    rule_id="DOC001",
                    suggested_fix="Add a module-level docstring describing the module purpose",
                ),
            )

        for node in ast.walk(tree):
            # Check class docstrings
            if isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node) and not node.name.startswith("_"):
                    issues.append(
                        _QualityIssue(
                            issue_type="documentation",
                            severity="warning",
                            file_path=file_path,
                            line_number=node.lineno,
                            message=f"Public class '{node.name}' is missing a docstring",
                            rule_id="DOC002",
                            suggested_fix=f"Add a docstring to class '{node.name}'",
                        ),
                    )

            # Check function docstrings (public functions only)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_") and not ast.get_docstring(node):
                    issues.append(
                        _QualityIssue(
                            issue_type="documentation",
                            severity="info",
                            file_path=file_path,
                            line_number=node.lineno,
                            message=f"Public function '{node.name}' is missing a docstring",
                            rule_id="DOC003",
                            suggested_fix=f"Add a docstring to function '{node.name}'",
                        ),
                    )

        return issues  # type: ignore[return-value]

    def suggest_refactoring(
        self, file_path: str, content: str | None = None
    ) -> list[str]:
        """
        Suggest refactoring opportunities based on static analysis.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of refactoring suggestions
        """
        source = self._read_file_content(file_path, content)
        if not source.strip():
            return []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return ["Fix syntax errors before refactoring"]

        suggestions: list[str] = []
        lines = source.splitlines()
        loc = len([line for line in lines if line.strip()])

        # File-level suggestions
        if loc > 500:
            suggestions.append(
                f"File has {loc} lines of code - consider splitting into multiple modules"
            )

        class_count = 0
        function_count = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_count += 1
                # Suggest splitting large classes
                class_lines = (node.end_lineno or node.lineno) - node.lineno + 1
                if class_lines > _DEFAULT_MAX_CLASS_LENGTH:
                    suggestions.append(
                        f"Class '{node.name}' ({class_lines} lines) - "
                        f"extract cohesive method groups into mixins or helper classes"
                    )
                # Suggest splitting classes with too many methods
                method_count = sum(
                    1
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                if method_count > 15:
                    suggestions.append(
                        f"Class '{node.name}' has {method_count} methods - "
                        f"consider splitting into focused classes"
                    )

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
                func_lines = (node.end_lineno or node.lineno) - node.lineno + 1
                if func_lines > _DEFAULT_MAX_FUNCTION_LENGTH:
                    suggestions.append(
                        f"Function '{node.name}' ({func_lines} lines) - "
                        f"extract sub-operations into helper functions"
                    )

        if class_count > 5:
            suggestions.append(
                f"File has {class_count} classes - consider splitting into separate modules"
            )

        return suggestions

    def configure_standards(self, standards: ProtocolQualityStandards) -> None:
        """
        Configure quality standards.

        Args:
            standards: Quality standards configuration
        """
        self.standards = standards

    async def get_validation_summary(
        self, reports: list[ProtocolQualityReport]
    ) -> ProtocolValidationResult:
        """
        Get validation summary from quality reports.

        Aggregates all quality reports into a single validation result with
        overall pass/fail status, error count, and warning count.

        Args:
            reports: List of quality reports

        Returns:
            Validation result summary
        """
        result = _ValidationResult()

        total_issues = 0
        total_critical = 0
        total_errors = 0
        total_warnings = 0
        failing_files: list[str] = []

        for report in reports:
            for issue in report.issues:
                total_issues += 1
                severity = getattr(issue, "severity", "info")
                if severity == "critical":
                    total_critical += 1
                    result.add_error(
                        "critical_issue",
                        getattr(issue, "message", "Critical issue detected"),
                    )
                elif severity == "error":
                    total_errors += 1
                    result.add_error(
                        "error_issue",
                        getattr(issue, "message", "Error issue detected"),
                    )
                elif severity == "warning":
                    total_warnings += 1
                    result.add_warning(
                        "warning_issue",
                        getattr(issue, "message", "Warning issue detected"),
                    )

            if not report.standards_compliance:
                failing_files.append(report.file_path)

        result.is_valid = total_critical == 0 and total_errors == 0

        if failing_files:
            result.add_warning(
                "non_compliant_files",
                f"{len(failing_files)} file(s) do not meet quality standards",
            )

        return result  # type: ignore[return-value]
