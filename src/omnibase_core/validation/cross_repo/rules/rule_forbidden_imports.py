"""Forbidden imports rule - granular import blocking.

Blocks specific imports at module or prefix level,
with support for exceptions.

Related ticket: OMN-1771
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleForbiddenImportsConfig,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
    ModelImportInfo,
)


class RuleForbiddenImports:
    """Enforces forbidden import restrictions.

    Blocks imports that match forbidden prefixes or modules,
    unless they match an exception pattern.
    """

    rule_id: ClassVar[str] = "forbidden_imports"  # string-id-ok: rule registry key
    requires_scanners: ClassVar[list[str]] = ["import_graph"]

    def __init__(self, config: ModelRuleForbiddenImportsConfig) -> None:
        """Initialize with rule configuration.

        Args:
            config: Typed configuration for this rule.
        """
        self.config = config

    def validate(
        self,
        file_imports: dict[Path, ModelFileImports],
    ) -> list[ModelValidationIssue]:
        """Check imports against forbidden patterns.

        Args:
            file_imports: Map of file paths to their imports.

        Returns:
            List of validation issues found.
        """
        if not self.config.enabled:
            return []

        issues: list[ModelValidationIssue] = []

        for file_path, imports in file_imports.items():
            if imports.parse_error:
                continue  # Skip files with parse errors

            for imp in imports.imports:
                issue = self._check_import(file_path, imp)
                if issue:
                    issues.append(issue)

        return issues

    def _check_import(
        self,
        file_path: Path,
        imp: ModelImportInfo,
    ) -> ModelValidationIssue | None:
        """Check a single import against forbidden patterns.

        Args:
            file_path: Path to the file containing the import.
            imp: The import information.

        Returns:
            Validation issue if the import is forbidden, None otherwise.
        """
        import_path = imp.full_import_path

        # Skip relative imports
        if not import_path or import_path.startswith("."):
            return None

        # Check if import matches any exception (allowed despite other rules)
        for exception in self.config.exceptions:
            if import_path.startswith(exception) or import_path == exception:
                return None

        # Check forbidden prefixes
        for forbidden in self.config.forbidden_prefixes:
            if import_path.startswith(forbidden):
                return ModelValidationIssue(
                    severity=self.config.severity,
                    message=f"Forbidden import prefix: '{import_path}' matches '{forbidden}'",
                    code="FORBIDDEN_IMPORT_PREFIX",
                    file_path=file_path,
                    line_number=imp.line_number,
                    rule_name=self.rule_id,
                    suggestion=f"Remove or replace import from '{forbidden}'",
                    context={
                        "import": import_path,
                        "forbidden_prefix": forbidden,
                    },
                )

        # Check exact forbidden modules
        for forbidden in self.config.forbidden_modules:
            if import_path == forbidden:
                return ModelValidationIssue(
                    severity=self.config.severity,
                    message=f"Forbidden module import: '{import_path}'",
                    code="FORBIDDEN_MODULE_IMPORT",
                    file_path=file_path,
                    line_number=imp.line_number,
                    rule_name=self.rule_id,
                    suggestion=f"Remove or replace import of '{forbidden}'",
                    context={
                        "import": import_path,
                        "forbidden_module": forbidden,
                    },
                )

        return None
