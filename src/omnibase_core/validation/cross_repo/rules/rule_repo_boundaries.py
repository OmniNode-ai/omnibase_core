"""Repo boundaries rule - the 'where code lives' gate.

Enforces that code is in the correct repository and layer.
Prevents boundary leaks like infra importing app code or
apps importing infra internals.

Related ticket: OMN-1771
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleRepoBoundariesConfig,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
    ModelImportInfo,
)


class RuleRepoBoundaries:
    """Enforces repository boundary rules.

    Checks:
    - Forbidden import prefixes (e.g., app can't import infra.services)
    - Allowed cross-repo prefixes (e.g., only *.protocols allowed)
    - Ownership mapping (which repo owns which module prefix)
    """

    rule_id: ClassVar[str] = "repo_boundaries"  # string-id-ok: rule registry key
    requires_scanners: ClassVar[list[str]] = ["import_graph"]

    def __init__(self, config: ModelRuleRepoBoundariesConfig) -> None:
        """Initialize with rule configuration.

        Args:
            config: Typed configuration for this rule.
        """
        self.config = config

    def validate(
        self,
        file_imports: dict[Path, ModelFileImports],
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> list[ModelValidationIssue]:
        """Check imports against boundary rules.

        Args:
            file_imports: Map of file paths to their imports.
            repo_id: The repository being validated.

        Returns:
            List of validation issues found.
        """
        if not self.config.enabled:
            return []

        issues: list[ModelValidationIssue] = []

        for file_path, imports in file_imports.items():
            if imports.parse_error:
                # Report parse errors as issues
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.WARNING,
                        message=f"Could not parse file: {imports.parse_error}",
                        file_path=file_path,
                        rule_name=self.rule_id,
                    )
                )
                continue

            for imp in imports.imports:
                issue = self._check_import(file_path, imp, repo_id)
                if issue:
                    issues.append(issue)

        return issues

    def _check_import(
        self,
        file_path: Path,
        imp: ModelImportInfo,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> ModelValidationIssue | None:
        """Check a single import against boundary rules.

        Args:
            file_path: Path to the file containing the import.
            imp: The import information.
            repo_id: The repository being validated.

        Returns:
            Validation issue if the import violates rules, None otherwise.
        """
        import_path = imp.full_import_path

        # Skip relative imports (start with empty string or .)
        if not import_path or import_path.startswith("."):
            return None

        # Check forbidden import prefixes
        for forbidden in self.config.forbidden_import_prefixes:
            if import_path.startswith(forbidden):
                return ModelValidationIssue(
                    severity=self.config.severity,
                    message=(
                        f"Forbidden import: '{import_path}' "
                        f"matches forbidden prefix '{forbidden}'"
                    ),
                    code="CROSS_REPO_FORBIDDEN_IMPORT",
                    file_path=file_path,
                    line_number=imp.line_number,
                    rule_name=self.rule_id,
                    suggestion=f"Use a public API instead of importing from '{forbidden}'",
                    context={
                        "import": import_path,
                        "forbidden_prefix": forbidden,
                        "repo_id": repo_id,
                    },
                )

        # Check cross-repo imports against allowed prefixes
        import_repo = self._get_owning_repo(import_path)

        if import_repo and import_repo != repo_id:
            # This is a cross-repo import - check if allowed
            if not self._is_allowed_cross_repo(import_path):
                return ModelValidationIssue(
                    severity=self.config.severity,
                    message=(
                        f"Cross-repo import not in allowed prefixes: '{import_path}' "
                        f"(from '{repo_id}' importing '{import_repo}')"
                    ),
                    code="CROSS_REPO_BOUNDARY_VIOLATION",
                    file_path=file_path,
                    line_number=imp.line_number,
                    rule_name=self.rule_id,
                    suggestion=(
                        f"Import from allowed public APIs: "
                        f"{', '.join(self.config.allowed_cross_repo_prefixes) or 'none configured'}"
                    ),
                    context={
                        "import": import_path,
                        "source_repo": repo_id,
                        "target_repo": import_repo,
                    },
                )

        return None

    def _get_owning_repo(self, import_path: str) -> str | None:
        """Determine which repo owns a module path.

        Args:
            import_path: The module import path.

        Returns:
            The repo_id that owns this module, or None if unknown.
        """
        # Check ownership map - longest prefix match wins
        best_match: str | None = None
        best_length = 0

        for prefix, repo in self.config.ownership.items():
            if import_path.startswith(prefix) and len(prefix) > best_length:
                best_match = repo
                best_length = len(prefix)

        return best_match

    def _is_allowed_cross_repo(self, import_path: str) -> bool:
        """Check if a cross-repo import is allowed.

        Args:
            import_path: The module import path.

        Returns:
            True if the import matches an allowed cross-repo prefix.
        """
        for allowed in self.config.allowed_cross_repo_prefixes:
            if import_path.startswith(allowed):
                return True
        return False
