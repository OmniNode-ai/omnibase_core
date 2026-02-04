"""Error taxonomy validation rule.

Enforces canonical error module usage and proper error context.
Merged from error_taxonomy + error_context per OMN-1775 decision.

Subchecks:
- WILD_EXCEPTION: Exception class defined outside canonical modules
- BAD_INHERITANCE: Exception not inheriting from ModelOnexError
- MISSING_ERROR_CODE: ModelOnexError raise without error_code
- BARE_RAISE: Bare 'raise' without context in except block

Related ticket: OMN-1775
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleErrorTaxonomyConfig,
)
from omnibase_core.validation.cross_repo.util_fingerprint import generate_fingerprint

if TYPE_CHECKING:
    from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
        ModelFileImports,
    )


# Known base exception classes that indicate an exception definition
EXCEPTION_BASE_NAMES = frozenset(
    {
        "Exception",
        "BaseException",
        "RuntimeError",
        "ValueError",
        "TypeError",
        "OSError",
        "IOError",
        "ModelOnexError",
        "RuntimeHostError",
        "ContractValidationError",
        "HandlerExecutionError",
        "InvalidOperationError",
        "ExceptionValidationFrameworkError",
    }
)


class RuleErrorTaxonomy:
    """Enforces canonical error module usage and proper error context.

    Subchecks:
    - WILD_EXCEPTION: Exception class defined outside canonical modules
    - BAD_INHERITANCE: Exception not inheriting from base error class
    - MISSING_ERROR_CODE: ModelOnexError raise without error_code
    - BARE_RAISE: Bare 'raise' without context in except block (warning)
    """

    rule_id: ClassVar[str] = "error_taxonomy"  # string-id-ok: rule registry key
    requires_scanners: ClassVar[list[str]] = []  # Uses file discovery, parses AST

    def __init__(self, config: ModelRuleErrorTaxonomyConfig) -> None:
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
        """Validate error taxonomy and context in Python files.

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

        for file_path in file_imports:
            file_issues = self._scan_file(file_path, repo_id)
            issues.extend(file_issues)

        return issues

    def _scan_file(
        self,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> list[ModelValidationIssue]:
        """Scan a Python file for error taxonomy violations.

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

        # Check for exception class definitions
        issues.extend(self._check_exception_definitions(tree, file_path, repo_id))

        # Check for ModelOnexError raises without error_code
        if self.config.require_error_code:
            issues.extend(self._check_error_raises(tree, file_path, repo_id))

        # Check for bare raises
        if self.config.warn_bare_raise:
            issues.extend(self._check_bare_raises(tree, file_path, repo_id))

        return issues

    def _check_exception_definitions(
        self,
        tree: ast.AST,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> list[ModelValidationIssue]:
        """Check exception class definitions are in canonical modules.

        Args:
            tree: AST of the file.
            file_path: Path to the file.
            repo_id: The repository being validated.

        Returns:
            List of validation issues for exception definitions.
        """
        issues: list[ModelValidationIssue] = []

        # Determine if this file is in a canonical module
        is_canonical = self._is_canonical_module(file_path)
        is_forbidden = self._is_forbidden_module(file_path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            # Check if this looks like an exception class
            if not self._is_exception_class(node):
                continue

            class_name = node.name

            # Check 1: Exception in forbidden module
            if is_forbidden:
                fingerprint = generate_fingerprint(
                    self.rule_id, str(file_path), class_name
                )
                issues.append(
                    ModelValidationIssue(
                        severity=self.config.severity,
                        message=f"Exception '{class_name}' defined in forbidden module",
                        code="ERROR_TAXONOMY_WILD_EXCEPTION",
                        file_path=file_path,
                        line_number=node.lineno,
                        rule_name=self.rule_id,
                        suggestion=f"Move exception to a canonical error module: {', '.join(self.config.canonical_error_modules)}",
                        context={
                            "fingerprint": fingerprint,
                            "class_name": class_name,
                            "repo_id": repo_id,
                            "symbol": class_name,
                        },
                    )
                )
                continue

            # Check 2: Exception outside canonical modules (if canonical modules are configured)
            if self.config.canonical_error_modules and not is_canonical:
                fingerprint = generate_fingerprint(
                    self.rule_id, str(file_path), class_name
                )
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.WARNING,
                        message=f"Exception '{class_name}' defined outside canonical error modules",
                        code="ERROR_TAXONOMY_WILD_EXCEPTION",
                        file_path=file_path,
                        line_number=node.lineno,
                        rule_name=self.rule_id,
                        suggestion=f"Consider moving to: {', '.join(self.config.canonical_error_modules)}",
                        context={
                            "fingerprint": fingerprint,
                            "class_name": class_name,
                            "repo_id": repo_id,
                            "symbol": class_name,
                        },
                    )
                )

            # Check 3: Exception not inheriting from base error class
            if not self._inherits_from_base(node):
                fingerprint = generate_fingerprint(
                    self.rule_id, str(file_path), f"{class_name}_inheritance"
                )
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.WARNING,
                        message=f"Exception '{class_name}' does not inherit from {self.config.base_error_class}",
                        code="ERROR_TAXONOMY_BAD_INHERITANCE",
                        file_path=file_path,
                        line_number=node.lineno,
                        rule_name=self.rule_id,
                        suggestion=f"Inherit from {self.config.base_error_class} for structured error handling",
                        context={
                            "fingerprint": fingerprint,
                            "class_name": class_name,
                            "repo_id": repo_id,
                            "symbol": class_name,
                        },
                    )
                )

        return issues

    def _check_error_raises(
        self,
        tree: ast.AST,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> list[ModelValidationIssue]:
        """Check ModelOnexError raises include error_code.

        Args:
            tree: AST of the file.
            file_path: Path to the file.
            repo_id: The repository being validated.

        Returns:
            List of validation issues for error raises.
        """
        issues: list[ModelValidationIssue] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise):
                continue

            if node.exc is None:
                # Bare raise - handled separately
                continue

            # Check if raising ModelOnexError or subclass
            call_node = self._get_raise_call(node.exc)
            if call_node is None:
                continue

            error_class_name = self._get_call_name(call_node)
            if error_class_name is None:
                continue

            # Check if it's a known error class
            if not self._is_known_error_class(error_class_name):
                continue

            # Check if error_code is provided
            if not self._has_error_code_kwarg(call_node):
                fingerprint = generate_fingerprint(
                    self.rule_id, str(file_path), f"raise_{node.lineno}"
                )
                issues.append(
                    ModelValidationIssue(
                        severity=self.config.severity,
                        message=f"'{error_class_name}' raised without explicit error_code",
                        code="ERROR_TAXONOMY_MISSING_CODE",
                        file_path=file_path,
                        line_number=node.lineno,
                        rule_name=self.rule_id,
                        suggestion="Add error_code=EnumCoreErrorCode.XXX to the raise statement",
                        context={
                            "fingerprint": fingerprint,
                            "error_class": error_class_name,
                            "repo_id": repo_id,
                            "symbol": error_class_name,
                        },
                    )
                )

        return issues

    def _check_bare_raises(
        self,
        tree: ast.AST,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> list[ModelValidationIssue]:
        """Check for bare raise statements in except blocks.

        Args:
            tree: AST of the file.
            file_path: Path to the file.
            repo_id: The repository being validated.

        Returns:
            List of validation issues for bare raises.
        """
        issues: list[ModelValidationIssue] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue

            # Look for bare raises in this except block
            for child in ast.walk(node):
                if isinstance(child, ast.Raise) and child.exc is None:
                    fingerprint = generate_fingerprint(
                        self.rule_id, str(file_path), f"bare_raise_{child.lineno}"
                    )
                    issues.append(
                        ModelValidationIssue(
                            severity=EnumSeverity.WARNING,
                            message="Bare 'raise' without adding context",
                            code="ERROR_TAXONOMY_BARE_RAISE",
                            file_path=file_path,
                            line_number=child.lineno,
                            rule_name=self.rule_id,
                            suggestion="Consider wrapping in ModelOnexError with context, or add '# reraise-ok' comment",
                            context={
                                "fingerprint": fingerprint,
                                "repo_id": repo_id,
                                "symbol": "raise",
                            },
                        )
                    )

        return issues

    def _is_canonical_module(self, file_path: Path) -> bool:
        """Check if a file is in a canonical error module.

        Args:
            file_path: Path to check.

        Returns:
            True if file is in a canonical error module.
        """
        path_str = str(file_path)
        for module in self.config.canonical_error_modules:
            # Convert module path to directory pattern
            # e.g., "omnibase_core.errors" -> "omnibase_core/errors"
            module_path = module.replace(".", "/")
            if module_path in path_str:
                return True
        return False

    def _is_forbidden_module(self, file_path: Path) -> bool:
        """Check if a file is in a forbidden module.

        Args:
            file_path: Path to check.

        Returns:
            True if file is in a forbidden module.
        """
        path_str = str(file_path)
        for module in self.config.forbidden_error_modules:
            module_path = module.replace(".", "/")
            if module_path in path_str:
                return True
        return False

    def _is_exception_class(self, node: ast.ClassDef) -> bool:
        """Check if a class definition is an exception class.

        Args:
            node: Class definition AST node.

        Returns:
            True if this looks like an exception class.
        """
        # Check class name ends with Error or Exception
        if node.name.endswith(("Error", "Exception")):
            return True

        # Check if it inherits from a known exception base
        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name in EXCEPTION_BASE_NAMES:
                return True

        return False

    def _inherits_from_base(self, node: ast.ClassDef) -> bool:
        """Check if exception inherits from the configured base class.

        Args:
            node: Class definition AST node.

        Returns:
            True if it inherits from the base error class.
        """
        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name == self.config.base_error_class:
                return True
            # Also accept known subclasses of ModelOnexError
            if base_name in {
                "RuntimeHostError",
                "ContractValidationError",
                "HandlerExecutionError",
                "InvalidOperationError",
            }:
                return True
        return False

    def _get_base_name(self, base: ast.expr) -> str | None:
        """Get the name of a base class from AST.

        Args:
            base: Base class AST expression.

        Returns:
            Name of the base class, or None if can't determine.
        """
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        return None

    def _get_raise_call(self, exc: ast.expr) -> ast.Call | None:
        """Get the Call node from a raise expression.

        Args:
            exc: The exception expression from a raise statement.

        Returns:
            Call node if the raise is a function call, None otherwise.
        """
        if isinstance(exc, ast.Call):
            return exc
        return None

    def _get_call_name(self, call: ast.Call) -> str | None:
        """Get the name of the function being called.

        Args:
            call: Call AST node.

        Returns:
            Name of the function, or None if can't determine.
        """
        if isinstance(call.func, ast.Name):
            return call.func.id
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        return None

    def _is_known_error_class(self, name: str) -> bool:
        """Check if a name is a known error class that should have error_code.

        Args:
            name: Class name to check.

        Returns:
            True if this is a known error class.
        """
        return name in {
            "ModelOnexError",
            "RuntimeHostError",
            "ContractValidationError",
            "HandlerExecutionError",
            "InvalidOperationError",
            "EventBusError",
        }

    def _has_error_code_kwarg(self, call: ast.Call) -> bool:
        """Check if a call has an error_code keyword argument.

        Args:
            call: Call AST node.

        Returns:
            True if error_code is provided.
        """
        for keyword in call.keywords:
            if keyword.arg == "error_code":
                return True
        return False
