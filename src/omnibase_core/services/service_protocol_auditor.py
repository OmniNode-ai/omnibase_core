"""
Protocol auditor for detecting duplicates and violations across omni* ecosystem.

Implements ProtocolQualityValidator for SPI compliance.
"""

from __future__ import annotations

import logging
from collections import defaultdict
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

    async def validate_file_quality(
        self, file_path: str, content: str | None = None
    ) -> ProtocolQualityReport:
        """
        Validate file quality metrics.

        Args:
            file_path: Path to file to validate
            content: Optional file content

        Returns:
            Quality report with metrics and issues

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "validate_file_quality() protocol method not yet implemented. "
            "Use check_current_repository() or check_against_spi() instead."
        )

    async def validate_directory_quality(
        self, directory_path: str, file_patterns: list[str] | None = None
    ) -> list[ProtocolQualityReport]:
        """
        Validate directory quality.

        Args:
            directory_path: Path to directory
            file_patterns: Optional file patterns to validate

        Returns:
            List of quality reports

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "validate_directory_quality() protocol method not yet implemented"
        )

    def calculate_quality_metrics(
        self, file_path: str, content: str | None = None
    ) -> ProtocolQualityMetrics:
        """
        Calculate quality metrics for file.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            Quality metrics

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "calculate_quality_metrics() protocol method not yet implemented"
        )

    def detect_code_smells(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolQualityIssue]:
        """
        Detect code smells in file.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of detected code smells

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "detect_code_smells() protocol method not yet implemented"
        )

    async def check_naming_conventions(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolQualityIssue]:
        """
        Check naming convention compliance.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of naming convention issues

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "check_naming_conventions() protocol method not yet implemented"
        )

    async def analyze_complexity(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolQualityIssue]:
        """
        Analyze code complexity.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of complexity issues

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "analyze_complexity() protocol method not yet implemented"
        )

    async def validate_documentation(
        self, file_path: str, content: str | None = None
    ) -> list[ProtocolQualityIssue]:
        """
        Validate documentation quality.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of documentation issues

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "validate_documentation() protocol method not yet implemented"
        )

    def suggest_refactoring(
        self, file_path: str, content: str | None = None
    ) -> list[str]:
        """
        Suggest refactoring opportunities.

        Args:
            file_path: Path to file
            content: Optional file content

        Returns:
            List of refactoring suggestions

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "suggest_refactoring() protocol method not yet implemented"
        )

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

        Args:
            reports: List of quality reports

        Returns:
            Validation result summary

        Raises:
            NotImplementedError: Protocol method not yet implemented
        """
        raise NotImplementedError(  # stub-ok: SPI protocol method - implementation pending
            "get_validation_summary() protocol method not yet implemented"
        )
