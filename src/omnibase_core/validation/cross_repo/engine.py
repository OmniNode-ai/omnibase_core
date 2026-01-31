"""Validation engine for cross-repo conformance.

Orchestrates the validation process: discover files, scan imports,
run rules, aggregate results.

Related ticket: OMN-1771
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleForbiddenImportsConfig,
    ModelRuleRepoBoundariesConfig,
)
from omnibase_core.models.validation.model_validation_policy_contract import (
    ModelValidationPolicyContract,
)
from omnibase_core.validation.cross_repo.rules.rule_forbidden_imports import (
    RuleForbiddenImports,
)
from omnibase_core.validation.cross_repo.rules.rule_repo_boundaries import (
    RuleRepoBoundaries,
)
from omnibase_core.validation.cross_repo.scanners.scanner_file_discovery import (
    ScannerFileDiscovery,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
    ScannerImportGraph,
)


class CrossRepoValidationEngine:
    """Orchestrates cross-repo validation.

    Coordinates file discovery, import scanning, and rule execution.
    Returns aggregated validation results.
    """

    def __init__(self, policy: ModelValidationPolicyContract) -> None:
        """Initialize the engine with a policy contract.

        Args:
            policy: The validation policy to enforce.
        """
        self.policy = policy
        self._file_scanner = ScannerFileDiscovery(policy.discovery)
        self._import_scanner = ScannerImportGraph()

    def validate(
        self,
        root: Path,
        rules: list[str] | None = None,
    ) -> ModelValidationResult[None]:
        """Run validation on a directory.

        Args:
            root: Root directory to validate.
            rules: Specific rule IDs to run (default: all enabled).

        Returns:
            Validation result with all issues found.
        """
        start_time = datetime.now(tz=UTC)
        all_issues: list[ModelValidationIssue] = []
        rules_executed: list[str] = []
        rules_skipped: list[str] = []

        # Discover files
        files = self._file_scanner.discover(root)

        # Scan imports
        file_imports = self._import_scanner.scan_files(files)

        # Determine which rules to run
        rules_to_run = rules if rules else list(self.policy.rules.keys())

        # Execute rules
        for rule_id in rules_to_run:
            if rule_id not in self.policy.rules:
                rules_skipped.append(rule_id)
                continue

            config = self.policy.rules[rule_id]

            if not config.enabled:
                rules_skipped.append(rule_id)
                continue

            rule_issues = self._execute_rule(rule_id, config, file_imports)
            all_issues.extend(rule_issues)
            rules_executed.append(rule_id)

        # Calculate duration
        end_time = datetime.now(tz=UTC)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Sort issues by severity, then file, then line
        severity_order = {
            EnumSeverity.FATAL: 0,
            EnumSeverity.CRITICAL: 1,
            EnumSeverity.ERROR: 2,
            EnumSeverity.WARNING: 3,
            EnumSeverity.INFO: 4,
            EnumSeverity.DEBUG: 5,
        }

        sorted_issues = sorted(
            all_issues,
            key=lambda i: (
                severity_order.get(i.severity, 99),
                str(i.file_path or ""),
                i.line_number or 0,
            ),
        )

        # Determine validity
        error_count = sum(
            1
            for i in sorted_issues
            if i.severity
            in (EnumSeverity.ERROR, EnumSeverity.CRITICAL, EnumSeverity.FATAL)
        )
        is_valid = error_count == 0

        # Build metadata
        metadata = ModelValidationMetadata(
            validation_type="cross_repo",
            duration_ms=duration_ms,
            files_processed=len(files),
            rules_applied=len(rules_executed),
            violations_found=len(sorted_issues),
        )

        return ModelValidationResult[None](
            is_valid=is_valid,
            issues=sorted_issues,
            summary=f"Cross-repo validation: {len(sorted_issues)} issues in {len(files)} files",
            metadata=metadata,
        )

    def _execute_rule(
        self,
        rule_id: str,  # string-id-ok: rule registry key
        config: object,
        file_imports: dict[Path, ModelFileImports],
    ) -> list[ModelValidationIssue]:
        """Execute a single rule.

        Args:
            rule_id: The rule to execute.
            config: The rule's configuration.
            file_imports: Import data from scanner.

        Returns:
            List of issues from this rule.
        """
        if rule_id == "repo_boundaries":
            if isinstance(config, ModelRuleRepoBoundariesConfig):
                boundaries_rule = RuleRepoBoundaries(config)
                return boundaries_rule.validate(file_imports, self.policy.repo_id)

        elif rule_id == "forbidden_imports":
            if isinstance(config, ModelRuleForbiddenImportsConfig):
                forbidden_rule = RuleForbiddenImports(config)
                return forbidden_rule.validate(file_imports)

        # Rule not implemented yet
        return []


def run_cross_repo_validation(
    directory: Path,
    policy: ModelValidationPolicyContract,
    rules: list[str] | None = None,
) -> ModelValidationResult[None]:
    """Convenience function to run cross-repo validation.

    Args:
        directory: Directory to validate.
        policy: Validation policy.
        rules: Specific rules to run (default: all).

    Returns:
        Validation result.
    """
    engine = CrossRepoValidationEngine(policy)
    return engine.validate(directory, rules)


__all__ = ["CrossRepoValidationEngine", "run_cross_repo_validation"]
