"""
Protocol auditor for detecting duplicates and violations across omni* ecosystem.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .exceptions import ConfigurationError, InputValidationError
from .validation_utils import (
    DuplicationInfo,
    ProtocolInfo,
    ValidationResult,
    determine_repository_name,
    extract_protocols_from_directory,
    validate_directory_path,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Result of protocol audit operation."""

    success: bool
    repository: str
    protocols_found: int
    duplicates_found: int
    conflicts_found: int
    violations: List[str]
    recommendations: List[str]
    execution_time_ms: int = 0

    def has_issues(self) -> bool:
        """Check if audit found any issues."""
        return (
            self.duplicates_found > 0
            or self.conflicts_found > 0
            or len(self.violations) > 0
        )


@dataclass
class DuplicationReport:
    """Report of protocol duplications between repositories."""

    success: bool
    source_repository: str
    target_repository: str
    exact_duplicates: List[DuplicationInfo]
    name_conflicts: List[DuplicationInfo]
    migration_candidates: List[ProtocolInfo]
    recommendations: List[str]


class ProtocolAuditor:
    """
    Centralized protocol auditing for omni* ecosystem.

    Provides different audit modes:
    - Current repository only (fast)
    - Current repository vs SPI (medium)
    - Full ecosystem scan (comprehensive)
    """

    def __init__(self, repository_path: str = "."):
        try:
            self.repository_path = validate_directory_path(
                Path(repository_path), "repository"
            )
        except InputValidationError as e:
            raise ConfigurationError(f"Invalid repository configuration: {e}")

        self.repository_name = determine_repository_name(self.repository_path)
        logger.info(
            f"ProtocolAuditor initialized for repository '{self.repository_name}' "
            f"at {self.repository_path}"
        )

    def check_current_repository(self) -> AuditResult:
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
            return AuditResult(
                success=True,
                repository=self.repository_name,
                protocols_found=0,
                duplicates_found=0,
                conflicts_found=0,
                violations=[
                    "No src directory found - repository might not have protocols"
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

        return AuditResult(
            success=len(violations) == 0,
            repository=self.repository_name,
            protocols_found=len(protocols),
            duplicates_found=len(local_duplicates),
            conflicts_found=0,  # No external conflicts in single-repo audit
            violations=violations,
            recommendations=recommendations,
        )

    def check_against_spi(self, spi_path: str = "../omnibase_spi") -> DuplicationReport:
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
        except InputValidationError as e:
            raise ConfigurationError(f"Invalid SPI path configuration: {e}")

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

        return DuplicationReport(
            success=len(duplications["exact_duplicates"]) == 0
            and len(duplications["name_conflicts"]) == 0,
            source_repository=self.repository_name,
            target_repository="omnibase_spi",
            exact_duplicates=duplications["exact_duplicates"],
            name_conflicts=duplications["name_conflicts"],
            migration_candidates=migration_candidates,
            recommendations=recommendations,
        )

    def audit_ecosystem(self, omni_root: Path) -> Dict[str, AuditResult]:
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
            auditor = ProtocolAuditor(str(repo_path))
            result = auditor.check_current_repository()
            results[repo_name] = result

        return results

    def _find_local_duplicates(
        self, protocols: List[ProtocolInfo]
    ) -> List[DuplicationInfo]:
        """Find duplicate protocols within the same repository."""
        duplicates = []
        by_signature = defaultdict(list)

        for protocol in protocols:
            by_signature[protocol.signature_hash].append(protocol)

        for signature_hash, protocol_group in by_signature.items():
            if len(protocol_group) > 1:
                duplicates.append(
                    DuplicationInfo(
                        signature_hash=signature_hash,
                        protocols=protocol_group,
                        duplication_type="exact",
                        recommendation=f"Merge or remove duplicate {protocol_group[0].name} protocols",
                    )
                )

        return duplicates

    def _check_naming_conventions(self, protocols: List[ProtocolInfo]) -> List[str]:
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

    def _check_protocol_quality(self, protocols: List[ProtocolInfo]) -> List[str]:
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
        self, source_protocols: List[ProtocolInfo], target_protocols: List[ProtocolInfo]
    ) -> Dict[str, List[DuplicationInfo]]:
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
                    DuplicationInfo(
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
                        DuplicationInfo(
                            signature_hash="conflict",
                            protocols=[source_protocol, target_protocol],
                            duplication_type="name_conflict",
                            recommendation=f"Resolve name conflict for {source_protocol.name}",
                        )
                    )

        return {"exact_duplicates": exact_duplicates, "name_conflicts": name_conflicts}

    def _has_duplicate_in_spi(
        self, protocol: ProtocolInfo, spi_protocols: List[ProtocolInfo]
    ) -> bool:
        """Check if protocol has a duplicate in SPI."""
        for spi_protocol in spi_protocols:
            if (
                protocol.signature_hash == spi_protocol.signature_hash
                or protocol.name == spi_protocol.name
            ):
                return True
        return False

    def print_audit_summary(self, result: AuditResult):
        """Print human-readable audit summary."""
        print(f"\n{'='*60}")
        print(f"🔍 PROTOCOL AUDIT SUMMARY - {result.repository}")
        print(f"{'='*60}")

        print(f"\n📊 INVENTORY:")
        print(f"   Protocols found: {result.protocols_found}")
        print(f"   Duplicates: {result.duplicates_found}")
        print(f"   Conflicts: {result.conflicts_found}")

        if result.violations:
            print(f"\n🚨 VIOLATIONS FOUND ({len(result.violations)}):")
            for violation in result.violations:
                print(f"   • {violation}")

        if result.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(result.recommendations)}):")
            for recommendation in result.recommendations:
                print(f"   • {recommendation}")

        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"\n{status}")

    def print_duplication_report(self, report: DuplicationReport):
        """Print human-readable duplication report."""
        print(f"\n{'='*60}")
        print(f"🔍 DUPLICATION REPORT")
        print(f"   {report.source_repository} vs {report.target_repository}")
        print(f"{'='*60}")

        if report.exact_duplicates:
            print(f"\n🚨 EXACT DUPLICATES ({len(report.exact_duplicates)}):")
            for dup in report.exact_duplicates:
                print(f"   • {dup.protocols[0].name} (signature: {dup.signature_hash})")
                print(f"     Recommendation: {dup.recommendation}")

        if report.name_conflicts:
            print(f"\n⚠️  NAME CONFLICTS ({len(report.name_conflicts)}):")
            for conflict in report.name_conflicts:
                print(f"   • {conflict.protocols[0].name}")
                print(f"     Recommendation: {conflict.recommendation}")

        if report.migration_candidates:
            print(f"\n🎯 MIGRATION CANDIDATES ({len(report.migration_candidates)}):")
            for candidate in report.migration_candidates:
                print(f"   • {candidate.name} ({len(candidate.methods)} methods)")

        status = "✅ CLEAN" if report.success else "❌ ISSUES FOUND"
        print(f"\n{status}")
