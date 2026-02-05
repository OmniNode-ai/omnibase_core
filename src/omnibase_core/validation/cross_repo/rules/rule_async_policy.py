"""Async policy rule - flag blocking calls inside async functions.

Prevents event loop blocking by detecting synchronous I/O calls
(time.sleep, requests, subprocess, open) inside async functions.

Related ticket: OMN-1906
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleAsyncPolicyConfig,
)
from omnibase_core.validation.cross_repo.util_exclusion import should_exclude_path
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
            if should_exclude_path(
                file_path, root_directory, self.config.exclude_patterns
            ):
                continue

            file_issues = self._scan_file(file_path, repo_id)
            issues.extend(file_issues)

        return issues

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
        self._check_node_for_blocking_calls(
            func_node, func_node.name, file_path, repo_id, issues, inside_wrapper=False
        )
        return issues

    def _is_allowlisted_wrapper(self, call_name: str) -> bool:
        """Check if a call is an allowlisted wrapper function.

        Allowlisted wrappers like asyncio.to_thread make blocking calls
        safe by running them in a thread pool.

        Args:
            call_name: Full dotted call name.

        Returns:
            True if this is an allowlisted wrapper.
        """
        for wrapper in self.config.allowlist_wrappers:
            if self._matches_call(call_name, wrapper):
                return True
        return False

    def _check_node_for_blocking_calls(
        self,
        node: ast.AST,
        async_func_name: str,
        file_path: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
        issues: list[ModelValidationIssue],
        inside_wrapper: bool,
    ) -> None:
        """Recursively check an AST node for blocking calls.

        Tracks whether we're inside an allowlisted wrapper to avoid
        false positives for properly wrapped blocking calls.

        Args:
            node: AST node to check.
            async_func_name: Name of the containing async function.
            file_path: Path to the file.
            repo_id: The repository being validated.
            issues: List to append found issues to.
            inside_wrapper: Whether we're inside an allowlisted wrapper call.
        """
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Call):
                call_name = self._get_full_call_name(child)

                # Check if this call is an allowlisted wrapper
                is_wrapper = call_name is not None and self._is_allowlisted_wrapper(
                    call_name
                )

                # Only check for blocking calls if not inside a wrapper
                if not inside_wrapper and call_name is not None:
                    issue = self._check_blocking_call(
                        child, call_name, async_func_name, file_path, repo_id
                    )
                    if issue:
                        issues.append(issue)

                # Recurse into children, marking inside_wrapper if this is a wrapper
                # This allows blocking calls as arguments to wrappers
                self._check_node_for_blocking_calls(
                    child,
                    async_func_name,
                    file_path,
                    repo_id,
                    issues,
                    inside_wrapper=inside_wrapper or is_wrapper,
                )
            else:
                # Non-call nodes: continue recursion with same wrapper state
                self._check_node_for_blocking_calls(
                    child,
                    async_func_name,
                    file_path,
                    repo_id,
                    issues,
                    inside_wrapper=inside_wrapper,
                )

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

        Supports exact matches and prefix matches (for module patterns only):
        - "time.sleep" matches "time.sleep" (exact)
        - "requests.get.something" matches "requests.get" (prefix, pattern has dot)
        - "open" matches "open" (exact only, no prefix for simple names)
        - "open_file" does NOT match "open" (no prefix for simple names)

        Args:
            call_name: Full dotted call name.
            pattern: Pattern to match against.

        Returns:
            True if the call matches the pattern.
        """
        # Exact match always works
        if call_name == pattern:
            return True

        # Prefix match only for module patterns (those containing a dot)
        # This prevents "requests" from matching "requests_mock.get" or
        # "open" from matching "open_file.something"
        if "." in pattern and call_name.startswith(pattern + "."):
            return True

        return False
