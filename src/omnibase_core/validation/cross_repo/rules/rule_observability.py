"""Observability rule - flag print() and raw logging usage.

Encourages use of ProtocolLogger for structured, consistent logging
instead of direct print() or logging.getLogger() calls.

Related ticket: OMN-1906
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleObservabilityConfig,
)
from omnibase_core.validation.cross_repo.util_exclusion import (
    get_relative_path_safe,
    should_exclude_path_with_modules,
)
from omnibase_core.validation.cross_repo.util_fingerprint import generate_fingerprint

if TYPE_CHECKING:
    from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
        ModelFileImports,
    )


class RuleObservability:
    """Flags direct print() and raw logging.getLogger() usage.

    Encourages consistent use of ProtocolLogger for structured logging
    instead of ad-hoc print statements or raw logging module usage.
    """

    rule_id: ClassVar[str] = "observability"  # string-id-ok: rule registry key
    requires_scanners: ClassVar[list[str]] = []  # Uses file discovery, parses AST

    def __init__(self, config: ModelRuleObservabilityConfig) -> None:
        """Initialize with rule configuration.

        Args:
            config: Typed configuration for this rule.
        """
        self.config = config

    def validate(
        self,
        file_imports: dict[Path, ModelFileImports],
        repo_id: str,  # string-id-ok: human-readable repository identifier
        root_directory: Path | None = None,
    ) -> list[ModelValidationIssue]:
        """Find print() and logging.getLogger() calls.

        Args:
            file_imports: Map of file paths to their imports.
            repo_id: The repository being validated.
            root_directory: Root directory being validated.

        Returns:
            List of validation issues for observability violations.
        """
        if not self.config.enabled:
            return []

        issues: list[ModelValidationIssue] = []

        for file_path in file_imports:
            if should_exclude_path_with_modules(
                file_path,
                root_directory,
                self.config.exclude_patterns,
                self.config.allowlist_modules,
            ):
                continue

            file_issues = self._scan_file(file_path, repo_id, root_directory)
            issues.extend(file_issues)

        return issues

    def _scan_file(
        self,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
        root_directory: Path | None = None,
    ) -> list[ModelValidationIssue]:
        """Scan a Python file for observability violations.

        Args:
            file_path: Path to the Python file.
            repo_id: The repository being validated.
            root_directory: Root directory for computing relative paths.

        Returns:
            List of validation issues found.
        """
        issues: list[ModelValidationIssue] = []

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (OSError, SyntaxError, UnicodeDecodeError):
            # Skip files that can't be read, parsed, or decoded
            return issues

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            issue = self._check_call(node, file_path, repo_id, root_directory)
            if issue:
                issues.append(issue)

        return issues

    def _check_call(
        self,
        node: ast.Call,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
        root_directory: Path | None = None,
    ) -> ModelValidationIssue | None:
        """Check if a call is a forbidden observability pattern.

        Args:
            node: Call AST node.
            file_path: Path to the file.
            repo_id: The repository being validated.
            root_directory: Root directory for computing relative paths.

        Returns:
            Validation issue if this is a forbidden call, None otherwise.
        """
        # Compute repo-relative path for stable fingerprints across environments.
        # Using relative paths ensures fingerprints are consistent regardless of
        # where the repository is checked out (e.g., /home/user/repo vs /tmp/repo).
        # Uses safe helper to handle ValueError when file is not under root_directory.
        relative_path = get_relative_path_safe(file_path, root_directory)

        # Check for print() calls
        if self.config.flag_print and self._is_print_call(node):
            fingerprint = generate_fingerprint(
                self.rule_id, str(relative_path), f"print_{node.lineno}"
            )
            return ModelValidationIssue(
                severity=self.config.print_severity,
                message="Direct print() call detected",
                code="OBSERVABILITY_PRINT",
                file_path=file_path,
                line_number=node.lineno,
                rule_name=self.rule_id,
                suggestion="Use ProtocolLogger for consistent, structured logging",
                context={
                    "fingerprint": fingerprint,
                    "call_type": "print",
                    "repo_id": repo_id,
                    "symbol": "print",
                },
            )

        # Check for logging.getLogger() calls
        if self.config.flag_raw_logging and self._is_logging_get_logger(node):
            fingerprint = generate_fingerprint(
                self.rule_id, str(relative_path), f"logging_{node.lineno}"
            )
            return ModelValidationIssue(
                severity=self.config.raw_logging_severity,
                message="Direct logging.getLogger() call detected",
                code="OBSERVABILITY_RAW_LOGGING",
                file_path=file_path,
                line_number=node.lineno,
                rule_name=self.rule_id,
                suggestion="Use ProtocolLogger instead of raw logging module",
                context={
                    "fingerprint": fingerprint,
                    "call_type": "logging.getLogger",
                    "repo_id": repo_id,
                    "symbol": "logging.getLogger",
                },
            )

        return None

    def _is_print_call(self, node: ast.Call) -> bool:
        """Check if a call is a print() call.

        Args:
            node: Call AST node.

        Returns:
            True if this is a print() call.
        """
        if isinstance(node.func, ast.Name):
            return node.func.id == "print"
        return False

    def _is_logging_get_logger(self, node: ast.Call) -> bool:
        """Check if a call is logging.getLogger().

        Matches:
        - logging.getLogger(...)
        - log.getLogger(...)  (if imported as log)

        Args:
            node: Call AST node.

        Returns:
            True if this is a logging.getLogger() call.
        """
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "getLogger":
                # Check if it's called on 'logging' or similar
                if isinstance(node.func.value, ast.Name):
                    return node.func.value.id in ("logging", "log")
        return False
