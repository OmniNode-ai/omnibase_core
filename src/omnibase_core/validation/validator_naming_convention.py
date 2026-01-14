"""
ValidatorNamingConvention - Contract-driven naming convention validator.

This module provides the ValidatorNamingConvention class for validating
file, class, and function naming conventions in Python source code.

The validator uses:
- Directory-based file name prefix rules (e.g., model_*.py in models/)
- AST analysis for class naming (PascalCase, anti-pattern detection)
- AST analysis for function naming (snake_case)

Exemptions are respected via:
- Allowed files (__init__.py, conftest.py, py.typed)
- Allowed prefixes (private modules starting with _)
- Inline suppression comments from contract configuration

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorNamingConvention

        validator = ValidatorNamingConvention()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.validator_naming_convention src/

Thread Safety:
    ValidatorNamingConvention instances are NOT thread-safe. Create separate
    instances for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1291)

See Also:
    - ValidatorBase: Base class for contract-driven validators
    - ModelValidatorSubcontract: Contract model for validator configuration
    - checker_naming_convention: Original implementation with backward compat exports
"""

import ast
import logging
import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_naming_convention import (
    ALLOWED_FILE_PREFIXES,
    ALLOWED_FILES,
    DIRECTORY_PREFIX_RULES,
    NamingConventionChecker,
    check_file_name,
)
from omnibase_core.validation.validator_base import ValidatorBase

# Configure logger for this module (must be after all imports per PEP 8)
logger = logging.getLogger(__name__)

# Rule identifiers for issue tracking
RULE_FILE_NAMING = "file_naming"
RULE_CLASS_NAMING = "class_naming"
RULE_FUNCTION_NAMING = "function_naming"
RULE_UNKNOWN_NAMING = "unknown_naming"

# Message prefix constants for issue categorization
# These MUST match the exact prefixes used by NamingConventionChecker in
# checker_naming_convention.py. If checker messages change, update these constants.
#
# Current checker message formats:
#   - Class: "Class name '{name}' contains anti-pattern..."
#   - Class: "Class name '{name}' should use PascalCase"
#   - Function: "Function name '{name}' should use snake_case"
#   - Async: "Async function name '{name}' should use snake_case"
_MSG_PREFIX_CLASS: str = "Class name"
_MSG_PREFIX_FUNCTION: str = "Function name"
_MSG_PREFIX_ASYNC_FUNCTION: str = "Async function name"


class ValidatorNamingConvention(ValidatorBase):
    """Validator for naming conventions in Python code.

    This validator uses file inspection and AST analysis to detect naming
    convention violations, including:
    - File names not following directory-specific prefix rules
    - Class names not using PascalCase
    - Class names using anti-pattern terms (Manager, Handler, etc.)
    - Function names not using snake_case

    The validator respects exemptions via:
    - Allowed files (__init__.py, conftest.py, py.typed)
    - Private modules (files starting with _)
    - Inline suppression comments

    Rule configuration is precomputed at initialization for O(1) lookups
    during validation, avoiding repeated iteration over contract rules.

    Thread Safety:
        ValidatorNamingConvention instances are NOT thread-safe due to internal
        mutable state. Specifically:

        - ``_file_line_cache`` (inherited from ValidatorBase): Caches file
          contents during validation. Concurrent access from multiple threads
          could cause cache corruption or stale reads.

        - ``_rule_config_cache``: Lazily built dictionary mapping rule IDs to
          configurations. While the lazy initialization is mostly safe due to
          Python's GIL, concurrent first-access from multiple threads could
          cause redundant computation.

        **When using parallel execution (e.g., pytest-xdist workers or
        ThreadPoolExecutor), create separate validator instances per worker.**

        The contract (ModelValidatorSubcontract) is immutable (frozen=True)
        and safe to share across threads.

        For more details, see the Threading Guide:
        ``docs/guides/THREADING.md``

    Attributes:
        validator_id: Unique identifier for this validator ("naming_convention").

    Usage Example:
        >>> from pathlib import Path
        >>> from omnibase_core.validation.validator_naming_convention import (
        ...     ValidatorNamingConvention
        ... )
        >>> validator = ValidatorNamingConvention()
        >>> result = validator.validate(Path("src/"))
        >>> print(f"Valid: {result.is_valid}, Issues: {len(result.issues)}")
    """

    # ONEX_EXCLUDE: string_id - human-readable validator identifier
    validator_id: ClassVar[str] = "naming_convention"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single Python file for naming convention violations.

        Checks:
        1. File name follows directory-specific prefix conventions
        2. Class names use PascalCase and avoid anti-patterns
        3. Function names use snake_case

        Args:
            path: Path to the Python file to validate.
            contract: Validator contract with configuration.

        Returns:
            Tuple of ModelValidationIssue instances for violations found.
        """
        issues: list[ModelValidationIssue] = []

        # Compute default severity with defensive fallback and logging
        # Note: contract.severity_default should never be None per model definition,
        # but we guard against it for robustness against external data sources
        default_severity = contract.severity_default or EnumSeverity.WARNING
        if contract.severity_default is None:
            # NOTE(OMN-1302): Defensive logging for impossible case. Safe because guards external data.
            logger.warning(  # type: ignore[unreachable]
                "Contract severity_default is None - using WARNING as fallback. "
                "This indicates a contract configuration issue."
            )

        # Get rule configs from precomputed cache (O(1) lookups)
        # Note: _get_rule_config returns non-None severity (base class handles fallback),
        # but we add defensive fallback here for robustness against future changes.
        # Log warnings when severity is None to surface contract issues.
        file_naming_enabled, file_naming_severity = self._get_rule_config(
            RULE_FILE_NAMING, contract
        )
        if file_naming_severity is None:
            # NOTE(OMN-1302): Defensive logging for impossible case. Safe because guards external data.
            logger.warning(  # type: ignore[unreachable]
                "Rule %s has None severity - using default %s. "
                "This indicates a contract configuration issue.",
                RULE_FILE_NAMING,
                default_severity,
            )
            file_naming_severity = default_severity

        class_naming_enabled, class_naming_severity = self._get_rule_config(
            RULE_CLASS_NAMING, contract
        )
        if class_naming_severity is None:
            # NOTE(OMN-1302): Defensive logging for impossible case. Safe because guards external data.
            logger.warning(  # type: ignore[unreachable]
                "Rule %s has None severity - using default %s. "
                "This indicates a contract configuration issue.",
                RULE_CLASS_NAMING,
                default_severity,
            )
            class_naming_severity = default_severity

        function_naming_enabled, function_naming_severity = self._get_rule_config(
            RULE_FUNCTION_NAMING, contract
        )
        if function_naming_severity is None:
            # NOTE(OMN-1302): Defensive logging for impossible case. Safe because guards external data.
            logger.warning(  # type: ignore[unreachable]
                "Rule %s has None severity - using default %s. "
                "This indicates a contract configuration issue.",
                RULE_FUNCTION_NAMING,
                default_severity,
            )
            function_naming_severity = default_severity

        # Hoist unknown_naming rule config lookup (optimization: avoids repeated
        # lookup in _validate_ast for each file and keeps all rule lookups together)
        unknown_naming_enabled, unknown_naming_severity = self._get_rule_config(
            RULE_UNKNOWN_NAMING, contract
        )
        if unknown_naming_severity is None:
            # NOTE(OMN-1302): Defensive logging for impossible case. Safe because guards external data.
            logger.warning(  # type: ignore[unreachable]
                "Rule %s has None severity - using default %s. "
                "This indicates a contract configuration issue.",
                RULE_UNKNOWN_NAMING,
                default_severity,
            )
            unknown_naming_severity = default_severity

        # 1. Check file naming (line 0 = file-level issue)
        if file_naming_enabled:
            error = check_file_name(path)
            if error:
                issues.append(
                    ModelValidationIssue(
                        severity=file_naming_severity,
                        message=error,
                        code=RULE_FILE_NAMING,
                        file_path=path,
                        line_number=1,  # File-level issue at line 1
                        rule_name=RULE_FILE_NAMING,
                        suggestion=self._get_file_naming_suggestion(path),
                    )
                )

        # 2 & 3. Check class and function naming via AST
        if class_naming_enabled or function_naming_enabled:
            ast_issues = self._validate_ast(
                path=path,
                contract=contract,
                class_naming_enabled=class_naming_enabled,
                function_naming_enabled=function_naming_enabled,
                class_naming_severity=class_naming_severity,
                function_naming_severity=function_naming_severity,
                unknown_naming_enabled=unknown_naming_enabled,
                unknown_naming_severity=unknown_naming_severity,
            )
            issues.extend(ast_issues)

        return tuple(issues)

    def _validate_ast(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
        class_naming_enabled: bool,
        function_naming_enabled: bool,
        class_naming_severity: EnumSeverity,
        function_naming_severity: EnumSeverity,
        unknown_naming_enabled: bool,
        unknown_naming_severity: EnumSeverity,
    ) -> list[ModelValidationIssue]:
        """Run AST-based validation for class and function naming.

        Args:
            path: Path to Python file to analyze.
            contract: Validator contract with configuration.
            class_naming_enabled: Whether to check class naming.
            function_naming_enabled: Whether to check function naming.
            class_naming_severity: Severity for class naming issues.
            function_naming_severity: Severity for function naming issues.
            unknown_naming_enabled: Whether to emit issues for unknown naming patterns.
            unknown_naming_severity: Severity for unknown naming issues.

        Returns:
            List of ModelValidationIssue instances for AST-based violations.
        """
        issues: list[ModelValidationIssue] = []

        try:
            source = path.read_text(encoding="utf-8")
        except OSError as e:
            # fallback-ok: log warning and skip file on read errors
            logger.warning("Cannot read file %s: %s", path, e)
            return issues

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            # fallback-ok: log warning and skip file with syntax errors
            logger.warning(
                "Skipping file with syntax error: path=%s, line=%s, error=%s",
                path,
                e.lineno,
                e.msg,
            )
            return issues

        # Use the existing NamingConventionChecker from checker_naming_convention
        checker = NamingConventionChecker(str(path))
        checker.visit(tree)

        # Default severity for fallback in edge cases (all severities should be
        # non-None at this point, but we keep a final fallback for safety)
        default_severity = contract.severity_default or EnumSeverity.WARNING

        # Convert checker issues to ModelValidationIssue
        for issue_str in checker.issues:
            # Parse the issue string format: "Line {lineno}: {message}"
            line_number = 1  # Default
            message = issue_str

            if issue_str.startswith("Line "):
                try:
                    # Extract line number from "Line {lineno}: {message}"
                    parts = issue_str.split(":", 1)
                    if len(parts) >= 2:
                        line_part = parts[0]  # "Line {lineno}"
                        line_number = int(line_part.replace("Line ", "").strip())
                        message = parts[1].strip()
                except (IndexError, ValueError) as e:
                    # fallback-ok: log parsing failure, use original message
                    # but strip "Line X:" prefix if present to avoid duplication
                    logger.warning(
                        "Failed to parse line number from issue '%s': %s",
                        issue_str,
                        e,
                    )
                    # Attempt to clean up message even on parse failure
                    if ":" in issue_str:
                        # Strip everything before first colon if it looks like "Line X"
                        potential_prefix = issue_str.split(":", 1)[0]
                        if potential_prefix.strip().startswith("Line"):
                            message = issue_str.split(":", 1)[1].strip()

            # Determine rule type and severity based on message content
            # IMPORTANT: Use the defined constants (_MSG_PREFIX_*) for pattern matching.
            # These constants MUST be kept synchronized with checker_naming_convention.py.
            # Check message (extracted content) not issue_str (which includes "Line N:" prefix)
            # to ensure accurate matching against the actual violation message.
            #
            # Severity fallback chain:
            # 1. Passed-in severity (guaranteed non-None by _validate_file)
            # 2. default_severity (from contract.severity_default, for edge cases)
            if message.startswith(_MSG_PREFIX_CLASS):
                if not class_naming_enabled:
                    continue
                severity = class_naming_severity or default_severity
                rule_name = RULE_CLASS_NAMING
                code = RULE_CLASS_NAMING
            elif message.startswith(_MSG_PREFIX_ASYNC_FUNCTION):
                # Check async first - it's more specific than plain "Function name"
                if not function_naming_enabled:
                    continue
                severity = function_naming_severity or default_severity
                rule_name = RULE_FUNCTION_NAMING
                code = RULE_FUNCTION_NAMING
            elif message.startswith(_MSG_PREFIX_FUNCTION):
                if not function_naming_enabled:
                    continue
                severity = function_naming_severity or default_severity
                rule_name = RULE_FUNCTION_NAMING
                code = RULE_FUNCTION_NAMING
            else:
                # Unknown issue type - this indicates either:
                # 1. A new issue type was added to NamingConventionChecker without updating
                #    the _MSG_PREFIX_* constants here
                # 2. A message format change that broke pattern matching
                # 3. A genuinely unexpected issue from a different source
                #
                # Check if unknown_naming rule is enabled before emitting
                if not unknown_naming_enabled:
                    logger.debug(
                        "Skipping unknown naming issue (rule disabled): %s",
                        issue_str,
                    )
                    continue

                # Log at warning level to surface unexpected patterns for investigation
                # Include the extracted message to help identify the pattern
                logger.warning(
                    "Unknown naming issue type detected - message does not match "
                    "known prefixes ('%s', '%s', '%s'). Raw issue: %s, Extracted message: %s",
                    _MSG_PREFIX_CLASS,
                    _MSG_PREFIX_ASYNC_FUNCTION,
                    _MSG_PREFIX_FUNCTION,
                    issue_str,
                    message,
                )

                # Use unknown_naming_severity with fallback for edge cases
                severity = unknown_naming_severity or default_severity
                rule_name = RULE_UNKNOWN_NAMING
                code = RULE_UNKNOWN_NAMING

            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=message,
                    code=code,
                    file_path=path,
                    line_number=line_number,
                    rule_name=rule_name,
                )
            )

        return issues

    def _get_file_naming_suggestion(self, path: Path) -> str | None:
        """Generate a suggestion for fixing file naming violations.

        Args:
            path: Path to the file with naming violation.

        Returns:
            Suggestion string or None if no suggestion can be generated.
        """
        file_name = path.name

        # Skip non-Python files and allowed files
        if not file_name.endswith(".py"):
            return None
        if file_name in ALLOWED_FILES:
            return None
        if any(file_name.startswith(prefix) for prefix in ALLOWED_FILE_PREFIXES):
            return None

        # Find the relevant directory rule
        parts = path.parts
        try:
            omnibase_idx = parts.index("omnibase_core")
            if omnibase_idx + 1 < len(parts) - 1:
                relevant_dir = parts[omnibase_idx + 1]
                if relevant_dir in DIRECTORY_PREFIX_RULES:
                    prefixes = DIRECTORY_PREFIX_RULES[relevant_dir]
                    suggested_prefix = prefixes[0]  # Use first prefix as suggestion
                    base_name = file_name[:-3]  # Remove .py
                    return f"Consider renaming to '{suggested_prefix}{base_name}.py'"
        except ValueError:
            # Path does not contain 'omnibase_core' - this can happen when:
            # 1. Validating files outside the omnibase_core package
            # 2. Running from a different project structure
            # This is expected for external validation and not an error
            logger.debug(
                "Cannot generate naming suggestion: 'omnibase_core' not in path: %s",
                path,
            )

        return None


# CLI entry point
if __name__ == "__main__":
    sys.exit(ValidatorNamingConvention.main())


__all__ = [
    "RULE_CLASS_NAMING",
    "RULE_FILE_NAMING",
    "RULE_FUNCTION_NAMING",
    "RULE_UNKNOWN_NAMING",
    "ValidatorNamingConvention",
]
