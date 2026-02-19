# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract schema validation rule.

Validates YAML contract files against schema requirements.
Checks for required fields and warns on deprecated field usage.

Related ticket: OMN-1775
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import yaml

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleContractSchemaConfig,
)
from omnibase_core.validation.cross_repo.util_fingerprint import generate_fingerprint

if TYPE_CHECKING:
    from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
        ModelFileImports,
    )


class RuleContractSchema:
    """Validates contract YAML files against schema requirements.

    Subchecks:
    - MISSING_FIELD: Required field is absent
    - DEPRECATED_FIELD: Using deprecated field (e.g., 'version' instead of 'contract_version')
    - INVALID_YAML: YAML parsing failure
    """

    rule_id: ClassVar[str] = "contract_schema_valid"  # string-id-ok: rule registry key
    requires_scanners: ClassVar[list[str]] = []  # Uses file discovery, not import graph

    def __init__(self, config: ModelRuleContractSchemaConfig) -> None:
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
        """Validate contract YAML files in the repository.

        Args:
            file_imports: Map of file paths to their imports (unused, for interface compat).
            repo_id: The repository being validated.
            root_directory: Root directory to scan for contracts.

        Returns:
            List of validation issues found.
        """
        if not self.config.enabled:
            return []

        if root_directory is None:
            return []

        issues: list[ModelValidationIssue] = []

        # Find contract YAML files
        contract_files = self._discover_contract_files(root_directory)

        for contract_path in contract_files:
            file_issues = self._validate_contract_file(contract_path, repo_id)
            issues.extend(file_issues)

        return issues

    def _discover_contract_files(self, root_directory: Path) -> list[Path]:
        """Find all contract YAML files in configured directories.

        Args:
            root_directory: Root directory to scan.

        Returns:
            List of contract file paths.
        """
        contract_files: list[Path] = []

        for contract_dir in self.config.contract_directories:
            full_dir = root_directory / contract_dir
            if full_dir.exists() and full_dir.is_dir():
                # Recursively find all YAML files
                contract_files.extend(full_dir.rglob("*.yaml"))
                contract_files.extend(full_dir.rglob("*.yml"))

        return contract_files

    def _validate_contract_file(
        self,
        contract_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> list[ModelValidationIssue]:
        """Validate a single contract YAML file.

        Args:
            contract_path: Path to the contract file.
            repo_id: The repository being validated.

        Returns:
            List of validation issues for this file.
        """
        issues: list[ModelValidationIssue] = []

        # Try to parse YAML
        try:
            with contract_path.open() as f:
                content = yaml.safe_load(f)  # yaml-ok: validation rule checks raw YAML
        except yaml.YAMLError as e:
            fingerprint = generate_fingerprint(
                self.rule_id, str(contract_path), "parse_error"
            )
            issues.append(
                ModelValidationIssue(
                    severity=self.config.severity,
                    message=f"Invalid YAML: {e}",
                    code="CONTRACT_SCHEMA_INVALID_YAML",
                    file_path=contract_path,
                    rule_name=self.rule_id,
                    suggestion="Fix YAML syntax errors",
                    context={
                        "fingerprint": fingerprint,
                        "repo_id": repo_id,
                        "symbol": "yaml_parse",
                    },
                )
            )
            return issues
        except OSError as e:
            # File read error - skip silently
            return issues

        if not isinstance(content, dict):
            fingerprint = generate_fingerprint(
                self.rule_id, str(contract_path), "not_dict"
            )
            issues.append(
                ModelValidationIssue(
                    severity=self.config.severity,
                    message="Contract must be a YAML mapping (dict), not a scalar or list",
                    code="CONTRACT_SCHEMA_INVALID_YAML",
                    file_path=contract_path,
                    rule_name=self.rule_id,
                    context={
                        "fingerprint": fingerprint,
                        "repo_id": repo_id,
                        "symbol": "yaml_structure",
                    },
                )
            )
            return issues

        # Check required fields
        for field in self.config.required_fields:
            if field not in content:
                fingerprint = generate_fingerprint(
                    self.rule_id, str(contract_path), f"missing_{field}"
                )
                issues.append(
                    ModelValidationIssue(
                        severity=self.config.severity,
                        message=f"Missing required field: '{field}'",
                        code="CONTRACT_SCHEMA_MISSING_FIELD",
                        file_path=contract_path,
                        rule_name=self.rule_id,
                        suggestion=f"Add the '{field}' field to the contract",
                        context={
                            "fingerprint": fingerprint,
                            "missing_field": field,
                            "repo_id": repo_id,
                            "symbol": field,
                        },
                    )
                )

        # Check deprecated fields
        for deprecated_field, guidance in self.config.deprecated_fields.items():
            if deprecated_field in content:
                fingerprint = generate_fingerprint(
                    self.rule_id, str(contract_path), f"deprecated_{deprecated_field}"
                )
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.WARNING,
                        message=f"Deprecated field: '{deprecated_field}'",
                        code="CONTRACT_SCHEMA_DEPRECATED_FIELD",
                        file_path=contract_path,
                        rule_name=self.rule_id,
                        suggestion=guidance,
                        context={
                            "fingerprint": fingerprint,
                            "deprecated_field": deprecated_field,
                            "repo_id": repo_id,
                            "symbol": deprecated_field,
                        },
                    )
                )

        return issues
