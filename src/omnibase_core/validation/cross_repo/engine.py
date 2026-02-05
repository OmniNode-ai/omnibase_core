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
    ModelRuleAsyncPolicyConfig,
    ModelRuleContractSchemaConfig,
    ModelRuleDuplicateProtocolsConfig,
    ModelRuleErrorTaxonomyConfig,
    ModelRuleForbiddenImportsConfig,
    ModelRuleObservabilityConfig,
    ModelRulePartitionKeyConfig,
    ModelRuleRepoBoundariesConfig,
    ModelRuleTopicNamingConfig,
)
from omnibase_core.models.validation.model_validation_policy_contract import (
    ModelValidationPolicyContract,
)
from omnibase_core.models.validation.model_violation_baseline import (
    ModelViolationBaseline,
)
from omnibase_core.validation.cross_repo.rules.rule_async_policy import (
    RuleAsyncPolicy,
)
from omnibase_core.validation.cross_repo.rules.rule_contract_schema import (
    RuleContractSchema,
)
from omnibase_core.validation.cross_repo.rules.rule_duplicate_protocols import (
    RuleDuplicateProtocols,
)
from omnibase_core.validation.cross_repo.rules.rule_error_taxonomy import (
    RuleErrorTaxonomy,
)
from omnibase_core.validation.cross_repo.rules.rule_forbidden_imports import (
    RuleForbiddenImports,
)
from omnibase_core.validation.cross_repo.rules.rule_repo_boundaries import (
    RuleRepoBoundaries,
)
from omnibase_core.validation.cross_repo.rules.rule_topic_naming import (
    RuleTopicNaming,
)
from omnibase_core.validation.cross_repo.rules.validator_observability import (
    ValidatorObservability,
)
from omnibase_core.validation.cross_repo.rules.validator_partition_key import (
    ValidatorPartitionKey,
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
        baseline: ModelViolationBaseline | None = None,
    ) -> ModelValidationResult[None]:
        """Run validation on a directory.

        Args:
            root: Root directory to validate.
            rules: Specific rule IDs to run (default: all enabled).
            baseline: Optional baseline for suppressing known violations.
                Baselined violations are downgraded to INFO and marked as suppressed.

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

            rule_issues = self._execute_rule(rule_id, config, file_imports, root)
            all_issues.extend(rule_issues)
            rules_executed.append(rule_id)

        # Calculate duration
        end_time = datetime.now(tz=UTC)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Apply baseline suppression
        processed_issues = self._apply_baseline(all_issues, baseline, root)

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
            processed_issues,
            key=lambda i: (
                severity_order.get(i.severity, 99),
                str(i.file_path or ""),
                i.line_number or 0,
            ),
        )

        # Determine validity - only unsuppressed errors cause failure
        error_count = sum(
            1
            for i in sorted_issues
            if i.severity
            in (EnumSeverity.ERROR, EnumSeverity.CRITICAL, EnumSeverity.FATAL)
            and not self._is_suppressed(i)
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

    def _apply_baseline(
        self,
        issues: list[ModelValidationIssue],
        baseline: ModelViolationBaseline | None,
        root: Path,
    ) -> list[ModelValidationIssue]:
        """Apply baseline suppression to issues.

        For each issue, check if it exists in the baseline. If so, downgrade
        its severity to INFO and mark it as suppressed. Suppressed violations
        still appear in output but don't cause failure.

        Args:
            issues: Raw issues from rule execution.
            baseline: Optional baseline to check against.
            root: Root directory for path normalization.

        Returns:
            Issues with baseline suppression applied.
        """
        if baseline is None:
            # No baseline - mark all issues as unsuppressed
            result = []
            for issue in issues:
                context = dict(issue.context) if issue.context else {}
                context["suppressed"] = "false"
                result.append(
                    ModelValidationIssue(
                        severity=issue.severity,
                        message=issue.message,
                        code=issue.code,
                        file_path=issue.file_path,
                        line_number=issue.line_number,
                        column_number=issue.column_number,
                        rule_name=issue.rule_name,
                        suggestion=issue.suggestion,
                        context=context,
                    )
                )
            return result

        result = []
        for issue in issues:
            # Get fingerprint from context
            fingerprint = issue.context.get("fingerprint") if issue.context else None

            # Check if this issue is baselined
            is_baselined = fingerprint is not None and baseline.has_violation(
                fingerprint
            )

            context = dict(issue.context) if issue.context else {}

            if is_baselined:
                # Downgrade to INFO and mark suppressed
                context["suppressed"] = "true"
                result.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.INFO,
                        message=issue.message,
                        code=issue.code,
                        file_path=issue.file_path,
                        line_number=issue.line_number,
                        column_number=issue.column_number,
                        rule_name=issue.rule_name,
                        suggestion=issue.suggestion,
                        context=context,
                    )
                )
            else:
                # New violation - keep original severity
                context["suppressed"] = "false"
                result.append(
                    ModelValidationIssue(
                        severity=issue.severity,
                        message=issue.message,
                        code=issue.code,
                        file_path=issue.file_path,
                        line_number=issue.line_number,
                        column_number=issue.column_number,
                        rule_name=issue.rule_name,
                        suggestion=issue.suggestion,
                        context=context,
                    )
                )

        return result

    @staticmethod
    def _is_suppressed(issue: ModelValidationIssue) -> bool:
        """Check if an issue is suppressed by baseline.

        Args:
            issue: The issue to check.

        Returns:
            True if the issue is suppressed.
        """
        if issue.context is None:
            return False
        return issue.context.get("suppressed") == "true"

    def _execute_rule(
        self,
        rule_id: str,  # string-id-ok: rule registry key
        config: object,
        file_imports: dict[Path, ModelFileImports],
        root_directory: Path,
    ) -> list[ModelValidationIssue]:
        """Execute a single rule.

        Args:
            rule_id: The rule to execute.
            config: The rule's configuration.
            file_imports: Import data from scanner.
            root_directory: Root directory being validated.

        Returns:
            List of issues from this rule.
        """
        # Phase 0 rules
        if rule_id == "repo_boundaries":
            if isinstance(config, ModelRuleRepoBoundariesConfig):
                return RuleRepoBoundaries(config).validate(
                    file_imports, self.policy.repo_id
                )

        elif rule_id == "forbidden_imports":
            if isinstance(config, ModelRuleForbiddenImportsConfig):
                return RuleForbiddenImports(config).validate(file_imports)

        # Phase 1 rules (OMN-1775)
        elif rule_id == "error_taxonomy":
            if isinstance(config, ModelRuleErrorTaxonomyConfig):
                return RuleErrorTaxonomy(config).validate(
                    file_imports, self.policy.repo_id, root_directory
                )

        elif rule_id == "contract_schema_valid":
            if isinstance(config, ModelRuleContractSchemaConfig):
                return RuleContractSchema(config).validate(
                    file_imports, self.policy.repo_id, root_directory
                )

        elif rule_id == "topic_naming":
            if isinstance(config, ModelRuleTopicNamingConfig):
                return RuleTopicNaming(config).validate(
                    file_imports, self.policy.repo_id, root_directory
                )

        # Phase 3 rules (OMN-1906)
        elif rule_id == "duplicate_protocols":
            if isinstance(config, ModelRuleDuplicateProtocolsConfig):
                return RuleDuplicateProtocols(config).validate(
                    file_imports, self.policy.repo_id, root_directory
                )

        elif rule_id == "partition_key":
            if isinstance(config, ModelRulePartitionKeyConfig):
                return ValidatorPartitionKey(config).validate(
                    file_imports, self.policy.repo_id, root_directory
                )

        elif rule_id == "observability":
            if isinstance(config, ModelRuleObservabilityConfig):
                return ValidatorObservability(config).validate(
                    file_imports, self.policy.repo_id, root_directory
                )

        elif rule_id == "async_policy":
            if isinstance(config, ModelRuleAsyncPolicyConfig):
                return RuleAsyncPolicy(config).validate(
                    file_imports, self.policy.repo_id, root_directory
                )

        # Rule not implemented yet
        return []


def run_cross_repo_validation(
    directory: Path,
    policy: ModelValidationPolicyContract,
    rules: list[str] | None = None,
    baseline: ModelViolationBaseline | None = None,
) -> ModelValidationResult[None]:
    """Convenience function to run cross-repo validation.

    Args:
        directory: Directory to validate.
        policy: Validation policy.
        rules: Specific rules to run (default: all).
        baseline: Optional baseline for suppressing known violations.

    Returns:
        Validation result.
    """
    engine = CrossRepoValidationEngine(policy)
    return engine.validate(directory, rules, baseline)


__all__ = ["CrossRepoValidationEngine", "run_cross_repo_validation"]
