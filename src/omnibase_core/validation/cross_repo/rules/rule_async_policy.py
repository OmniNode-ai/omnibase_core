"""Async policy rule - flag blocking calls inside async functions.

Prevents event loop blocking by detecting synchronous I/O calls
(time.sleep, requests, subprocess, open) inside async functions.

Related ticket: OMN-1906
"""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleAsyncPolicyConfig,
)
from omnibase_core.validation.cross_repo.util_fingerprint import generate_fingerprint

if TYPE_CHECKING:
    from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
        ModelFileImports,
    )


class RuleAsyncPolicy:
    """Flags blocking I/O calls inside async functions.

    Detects synchronous operations that would block the event loop,
    such as time.sleep(), requests.*, subprocess.run(), and open().
    """

    rule_id: ClassVar[str] = "async_policy"  # string-id-ok: rule registry key
    requires_scanners: ClassVar[list[str]] = []  # Uses file discovery, parses AST

    def __init__(self, config: ModelRuleAsyncPolicyConfig) -> None:
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
        """Find blocking calls inside async functions.

        Args:
            file_imports: Map of file paths to their imports.
            repo_id: The repository being validated.
            root_directory: Root directory being validated.

        Returns:
            List of validation issues for async policy violations.
        """
        if not self.config.enabled:
            return []

        issues: list[ModelValidationIssue] = []

        for file_path in file_imports:
            if self._should_exclude(file_path, root_directory):
                continue

            file_issues = self._scan_file(file_path, repo_id)
            issues.extend(file_issues)

        return issues

    def _should_exclude(
        self,
        file_path: Path,
        root_directory: Path | None,
    ) -> bool:
        """Check if a file should be excluded from validation.

        Args:
            file_path: Path to check.
            root_directory: Root directory for relative path calculation.

        Returns:
            True if the file should be excluded.
        """
        # Get relative path for pattern matching
        if root_directory:
            try:
                relative_path = file_path.relative_to(root_directory)
            except ValueError:
                relative_path = file_path
        else:
            relative_path = file_path

        path_str = str(relative_path)

        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True
            # Also check if any parent directory matches
            for parent in relative_path.parents:
                if fnmatch.fnmatch(str(parent), pattern.removesuffix("/**")):
                    return True

        return False

    def _scan_file(
        self,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> list[ModelValidationIssue]:
        """Scan a Python file for async policy violations.

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

        # Find all async function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                async_issues = self._check_async_function(node, file_path, repo_id)
                issues.extend(async_issues)

        return issues

    def _check_async_function(
        self,
        func_node: ast.AsyncFunctionDef,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> list[ModelValidationIssue]:
        """Check an async function for blocking calls.

        Args:
            func_node: Async function definition AST node.
            file_path: Path to the file.
            repo_id: The repository being validated.

        Returns:
            List of validation issues for this function.
        """
        issues: list[ModelValidationIssue] = []

        for node in ast.walk(func_node):
            if not isinstance(node, ast.Call):
                continue

            call_name = self._get_full_call_name(node)
            if call_name is None:
                continue

            # Skip if this call is inside an allowlisted wrapper
            # (simplified check - we don't track nested context)

            # Check for blocking calls
            issue = self._check_blocking_call(
                node, call_name, func_node.name, file_path, repo_id
            )
            if issue:
                issues.append(issue)

        return issues

    def _get_full_call_name(self, node: ast.Call) -> str | None:
        """Get the full dotted name of a function call.

        Examples:
        - print() -> "print"
        - time.sleep() -> "time.sleep"
        - requests.get() -> "requests.get"

        Args:
            node: Call AST node.

        Returns:
            Full dotted call name, or None if can't determine.
        """
        if isinstance(node.func, ast.Name):
            return node.func.id

        if isinstance(node.func, ast.Attribute):
            parts: list[str] = []
            current: ast.expr = node.func

            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value

            if isinstance(current, ast.Name):
                parts.append(current.id)
                return ".".join(reversed(parts))

        return None

    def _check_blocking_call(
        self,
        node: ast.Call,
        call_name: str,
        async_func_name: str,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
    ) -> ModelValidationIssue | None:
        """Check if a call is a blocking operation.

        Args:
            node: Call AST node.
            call_name: Full dotted call name.
            async_func_name: Name of the containing async function.
            file_path: Path to the file.
            repo_id: The repository being validated.

        Returns:
            Validation issue if this is a blocking call, None otherwise.
        """
        # Check ERROR severity blocking calls
        for blocked in self.config.blocking_calls_error:
            if self._matches_call(call_name, blocked):
                fingerprint = generate_fingerprint(
                    self.rule_id, str(file_path), f"{call_name}_{node.lineno}"
                )
                return ModelValidationIssue(
                    severity=EnumSeverity.ERROR,
                    message=f"Blocking call '{call_name}' in async function '{async_func_name}'",
                    code="ASYNC_POLICY_BLOCKING_CALL",
                    file_path=file_path,
                    line_number=node.lineno,
                    rule_name=self.rule_id,
                    suggestion="Use async equivalent or run in thread pool (e.g., asyncio.to_thread)",
                    context={
                        "fingerprint": fingerprint,
                        "blocking_call": call_name,
                        "async_function": async_func_name,
                        "repo_id": repo_id,
                        "symbol": call_name,
                    },
                )

        # Check WARNING severity blocking calls
        for blocked in self.config.blocking_calls_warning:
            if self._matches_call(call_name, blocked):
                fingerprint = generate_fingerprint(
                    self.rule_id, str(file_path), f"{call_name}_{node.lineno}"
                )
                return ModelValidationIssue(
                    severity=EnumSeverity.WARNING,
                    message=f"Potentially blocking call '{call_name}' in async function '{async_func_name}'",
                    code="ASYNC_POLICY_BLOCKING_CALL",
                    file_path=file_path,
                    line_number=node.lineno,
                    rule_name=self.rule_id,
                    suggestion="Consider using aiofiles or running in thread pool",
                    context={
                        "fingerprint": fingerprint,
                        "blocking_call": call_name,
                        "async_function": async_func_name,
                        "repo_id": repo_id,
                        "symbol": call_name,
                    },
                )

        return None

    def _matches_call(self, call_name: str, pattern: str) -> bool:
        """Check if a call name matches a blocking pattern.

        Supports exact matches and prefix matches:
        - "time.sleep" matches "time.sleep"
        - "requests.get" matches "requests.get"
        - "open" matches "open"

        Args:
            call_name: Full dotted call name.
            pattern: Pattern to match against.

        Returns:
            True if the call matches the pattern.
        """
        # Exact match
        if call_name == pattern:
            return True

        # Prefix match for module.* patterns
        # e.g., "requests.get" starts with "requests."
        if call_name.startswith(pattern + "."):
            return True

        return False
