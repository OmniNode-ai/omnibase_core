# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Partition key rule - require explicit partition_key in topic configs.

Enforces that Kafka topic configuration classes declare an explicit
partition key strategy, preventing implicit/undefined partitioning.

Related ticket: OMN-1906
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRulePartitionKeyConfig,
)
from omnibase_core.validation.cross_repo.util_exclusion import (
    get_relative_path_safe,
    should_exclude_path,
)
from omnibase_core.validation.cross_repo.util_fingerprint import generate_fingerprint

if TYPE_CHECKING:
    from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
        ModelFileImports,
    )


class RulePartitionKey:
    """Requires explicit partition_key declaration in topic configurations.

    Flags topic config classes that don't declare a partition key strategy,
    forcing explicitness about message partitioning behavior.
    """

    rule_id: ClassVar[str] = "partition_key"  # string-id-ok: rule registry key
    requires_scanners: ClassVar[list[str]] = []  # Uses file discovery, parses AST

    def __init__(self, config: ModelRulePartitionKeyConfig) -> None:
        """Initialize with rule configuration.

        Args:
            config: Typed configuration for this rule.
        """
        self.config = config
        self._pattern = re.compile(config.topic_config_pattern)

    def validate(
        self,
        file_imports: dict[Path, ModelFileImports],
        repo_id: str,  # string-id-ok: human-readable repository identifier
        root_directory: Path | None = None,
    ) -> list[ModelValidationIssue]:
        """Validate partition_key presence in topic configurations.

        Args:
            file_imports: Map of file paths to their imports.
            repo_id: The repository being validated.
            root_directory: Root directory for computing repo-relative paths.
                Used for: (1) exclusion pattern matching, (2) stable fingerprints.

        Returns:
            List of validation issues for missing partition keys.
        """
        if not self.config.enabled:
            return []

        if not self.config.require_partition_key:
            return []

        issues: list[ModelValidationIssue] = []

        for file_path in file_imports:
            # root_directory used here for exclusion pattern matching
            if should_exclude_path(
                file_path, root_directory, self.config.exclude_patterns
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
        """Scan a Python file for topic configs missing partition_key.

        Args:
            file_path: Path to the Python file.
            repo_id: The repository being validated.
            root_directory: Root directory for computing repo-relative paths.

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

        # Compute repo-relative path for stable fingerprints across environments.
        relative_path = get_relative_path_safe(file_path, root_directory)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            # Check if class name matches topic config pattern
            if not self._pattern.match(node.name):
                continue

            # Check if class has partition_key field
            if not self._has_partition_key_field(node):
                # Use repo-relative path for fingerprint stability
                fingerprint = generate_fingerprint(
                    self.rule_id, str(relative_path), node.name
                )
                issues.append(
                    ModelValidationIssue(
                        severity=self.config.severity,
                        message=f"Topic config '{node.name}' missing partition_key field",
                        code="MISSING_PARTITION_KEY",
                        file_path=file_path,
                        line_number=node.lineno,
                        rule_name=self.rule_id,
                        suggestion=f"Add partition_key field with one of: {', '.join(self.config.allowed_strategies)}",
                        context={
                            "fingerprint": fingerprint,
                            "class_name": node.name,
                            "repo_id": repo_id,
                            "allowed_strategies": ", ".join(
                                self.config.allowed_strategies
                            ),
                            "symbol": node.name,
                        },
                    )
                )

        return issues

    def _has_partition_key_field(self, class_node: ast.ClassDef) -> bool:
        """Check if a class has a partition_key field defined.

        Handles both direct assignment and Field() patterns:
        - partition_key: str = "correlation_id"
        - partition_key: str = Field(default="correlation_id")
        - partition_key = "correlation_id"

        Args:
            class_node: The class definition AST node.

        Returns:
            True if partition_key field is found.
        """
        for item in class_node.body:
            # Check annotated assignment: partition_key: str = ...
            if isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    if item.target.id == "partition_key":
                        return True

            # Check simple assignment: partition_key = ...
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "partition_key":
                            return True

        return False
