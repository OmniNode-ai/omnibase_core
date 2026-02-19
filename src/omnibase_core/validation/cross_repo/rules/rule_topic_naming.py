# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Topic naming validation rule.

Enforces Kafka topic naming conventions per ONEX topic taxonomy.
Reuses validator_topic_suffix.py for validation logic.

Related ticket: OMN-1775
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleTopicNamingConfig,
)
from omnibase_core.validation.cross_repo.util_fingerprint import generate_fingerprint
from omnibase_core.validation.validator_topic_suffix import validate_topic_suffix

if TYPE_CHECKING:
    from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
        ModelFileImports,
    )


# Pattern to detect potential topic string literals
# Matches strings that look like topic names (contain dots and look like topics)
TOPIC_LIKE_PATTERN = re.compile(r"^(onex|dev|staging|prod|test|local)\.[a-z]")


class RuleTopicNaming:
    """Enforces Kafka topic naming conventions.

    Subchecks:
    - INVALID_FORMAT: Topic doesn't match allowed patterns
    - HARDCODED_TOPIC: Topic string literal found in code (not in constants module)

    Uses validator_topic_suffix.py for validation logic.
    """

    rule_id: ClassVar[str] = "topic_naming"  # string-id-ok: rule registry key
    requires_scanners: ClassVar[list[str]] = []  # Uses file discovery, parses AST

    def __init__(self, config: ModelRuleTopicNamingConfig) -> None:
        """Initialize with rule configuration.

        Args:
            config: Typed configuration for this rule.
        """
        self.config = config
        # Compile allowed patterns
        self._allowed_patterns = [re.compile(p) for p in config.allowed_patterns]
        self._forbidden_patterns = [re.compile(p) for p in config.forbidden_patterns]

    def validate(
        self,
        file_imports: dict[Path, ModelFileImports],
        repo_id: str,  # string-id-ok: human-readable repository identifier
        root_directory: Path | None = None,
    ) -> list[ModelValidationIssue]:
        """Validate topic naming conventions in Python files.

        Args:
            file_imports: Map of file paths to their imports.
            repo_id: The repository being validated.
            root_directory: Root directory being validated.

        Returns:
            List of validation issues found.
        """
        if not self.config.enabled:
            return []

        issues: list[ModelValidationIssue] = []

        # Scan all Python files for topic string literals
        for file_path in file_imports:
            # Skip the constants module itself - that's where topics SHOULD be defined
            if self._is_constants_module(file_path):
                continue

            file_issues = self._scan_file_for_topics(file_path, repo_id)
            issues.extend(file_issues)

        return issues

    def _is_constants_module(self, file_path: Path) -> bool:
        """Check if this file is the allowed constants module.

        Args:
            file_path: Path to check.

        Returns:
            True if this is the constants module where topics should be defined.
        """
        # Convert module path to file path pattern
        # e.g., "omnibase_core.constants.constants_topic_taxonomy" -> "constants_topic_taxonomy.py"
        constants_file = self.config.constants_module.split(".")[-1] + ".py"
        return file_path.name == constants_file

    def _scan_file_for_topics(
        self,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> list[ModelValidationIssue]:
        """Scan a Python file for topic string literals.

        Args:
            file_path: Path to the Python file.
            repo_id: The repository being validated.

        Returns:
            List of validation issues found.
        """
        issues: list[ModelValidationIssue] = []

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (OSError, SyntaxError):
            # Skip files that can't be read or parsed
            return issues

        # Find all string literals
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                string_value = node.value

                # Check if this looks like a topic name
                if not TOPIC_LIKE_PATTERN.match(string_value):
                    continue

                # Validate the topic format
                issue = self._check_topic_string(
                    file_path,
                    string_value,
                    getattr(node, "lineno", None),
                    repo_id,
                )
                if issue:
                    issues.append(issue)

        return issues

    def _check_topic_string(
        self,
        file_path: Path,
        topic_string: str,
        line_number: int | None,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> ModelValidationIssue | None:
        """Check a potential topic string for violations.

        Args:
            file_path: Path to the file containing the string.
            topic_string: The string value to check.
            line_number: Line number where the string appears.
            repo_id: The repository being validated.

        Returns:
            Validation issue if violation found, None otherwise.
        """
        # First check if it matches forbidden patterns
        for pattern in self._forbidden_patterns:
            if pattern.match(topic_string):
                fingerprint = generate_fingerprint(
                    self.rule_id, str(file_path), topic_string
                )
                return ModelValidationIssue(
                    severity=self.config.severity,
                    message=f"Topic matches forbidden pattern: '{topic_string}'",
                    code="TOPIC_NAMING_FORBIDDEN_PATTERN",
                    file_path=file_path,
                    line_number=line_number,
                    rule_name=self.rule_id,
                    suggestion="Remove or rename this topic",
                    context={
                        "fingerprint": fingerprint,
                        "repo_id": repo_id,
                        "symbol": topic_string,
                        "topic": topic_string,
                    },
                )

        # Use the existing validator for ONEX format validation
        validation_result = validate_topic_suffix(topic_string)

        if not validation_result.is_valid:
            # Check if it matches any allowed pattern (config override)
            for pattern in self._allowed_patterns:
                if pattern.match(topic_string):
                    # Matches allowed pattern, check if hardcoded
                    return self._check_hardcoded_topic(
                        file_path, topic_string, line_number, repo_id
                    )

            # Invalid format
            fingerprint = generate_fingerprint(
                self.rule_id, str(file_path), topic_string
            )
            return ModelValidationIssue(
                severity=self.config.severity,
                message=f"Invalid topic format: '{topic_string}' - {validation_result.error}",
                code="TOPIC_NAMING_INVALID_FORMAT",
                file_path=file_path,
                line_number=line_number,
                rule_name=self.rule_id,
                suggestion="Use format: onex.{kind}.{producer}.{event-name}.v{n}",
                context={
                    "fingerprint": fingerprint,
                    "repo_id": repo_id,
                    "symbol": topic_string,
                    "topic": topic_string,
                    "validation_error": validation_result.error or "unknown",
                },
            )

        # Valid format - check if hardcoded
        return self._check_hardcoded_topic(
            file_path, topic_string, line_number, repo_id
        )

    def _check_hardcoded_topic(
        self,
        file_path: Path,
        topic_string: str,
        line_number: int | None,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> ModelValidationIssue | None:
        """Check if a valid topic is hardcoded instead of using constants.

        Args:
            file_path: Path to the file containing the string.
            topic_string: The topic string.
            line_number: Line number where the string appears.
            repo_id: The repository being validated.

        Returns:
            Validation issue if hardcoded, None otherwise.
        """
        # This is a hardcoded topic string outside the constants module
        fingerprint = generate_fingerprint(self.rule_id, str(file_path), topic_string)
        return ModelValidationIssue(
            severity=EnumSeverity.WARNING,
            message=f"Hardcoded topic string: '{topic_string}'",
            code="TOPIC_NAMING_HARDCODED",
            file_path=file_path,
            line_number=line_number,
            rule_name=self.rule_id,
            suggestion=f"Define this topic in {self.config.constants_module} and import the constant",
            context={
                "fingerprint": fingerprint,
                "repo_id": repo_id,
                "symbol": topic_string,
                "topic": topic_string,
            },
        )
