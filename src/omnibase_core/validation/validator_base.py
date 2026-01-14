"""
ValidatorBase - Contract-driven base class for file validators.

This module provides a concrete base class for implementing file-based validators
with shared behavior for file targeting, suppression handling, and result ordering.

Key Features:
    - Contract-driven configuration via ModelValidatorSubcontract
    - Glob-based file targeting with exclusion patterns
    - Inline suppression comment support
    - Deterministic violation ordering (severity -> file -> line)
    - CLI integration with exit code mapping

Usage Examples:
    Subclass implementation::

        from pathlib import Path
        from omnibase_core.validation.validator_base import ValidatorBase
        from omnibase_core.models.contracts.subcontracts import ModelValidatorSubcontract
        from omnibase_core.models.common.model_validation_issue import ModelValidationIssue

        class NamingValidator(ValidatorBase):
            validator_id = "naming-convention"

            def _validate_file(
                self,
                path: Path,
                contract: ModelValidatorSubcontract,
            ) -> tuple[ModelValidationIssue, ...]:
                issues = []
                # ... validation logic ...
                return tuple(issues)

    Programmatic usage::

        validator = NamingValidator()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        if __name__ == "__main__":
            import sys
            sys.exit(NamingValidator.main())

Thread Safety:
    ValidatorBase instances are NOT thread-safe. Create separate instances
    for concurrent use or protect with external synchronization. The contract
    (ModelValidatorSubcontract) is immutable (frozen) and safe to share.

Schema Version:
    v1.0.0 - Initial version (OMN-1291)

See Also:
    - ModelValidatorSubcontract: Contract model for validator configuration
    - ModelValidationResult: Unified validation result model
    - ModelValidationIssue: Individual validation issue model
"""

import argparse
import fnmatch
import logging
import sys
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

import yaml

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import (
    FILE_IO_ERRORS,
    PYDANTIC_MODEL_ERRORS,
    YAML_PARSING_ERRORS,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Configure logger for this module
logger = logging.getLogger(__name__)

# Exit code constants
EXIT_SUCCESS = 0
EXIT_ERRORS = 1
EXIT_WARNINGS = 2

# Severity priority for deterministic ordering (lower = higher priority)
SEVERITY_PRIORITY: dict[EnumSeverity, int] = {
    EnumSeverity.FATAL: 0,
    EnumSeverity.CRITICAL: 1,
    EnumSeverity.ERROR: 2,
    EnumSeverity.WARNING: 3,
    EnumSeverity.INFO: 4,
    EnumSeverity.DEBUG: 5,
}


class ValidatorBase(ABC):
    """Concrete base class for contract-driven file validators.

    Provides shared behavior for:
    - File targeting via glob patterns
    - Exclusion filtering
    - Suppression comment handling
    - Deterministic result ordering
    - CLI exit code mapping

    Subclasses must implement:
    - validator_id (class attribute): Unique identifier for this validator
    - _validate_file(path, contract) -> tuple of validation issues

    Optional overrides:
    - _load_contract(): Custom contract loading logic
    - _get_contract_path(): Custom contract path resolution

    Thread Safety:
        ValidatorBase instances are NOT thread-safe due to internal mutable state.
        Specifically:

        - ``_file_line_cache``: Caches file contents during validation. Concurrent
          access from multiple threads could cause cache corruption or stale reads.

        - ``_rule_config_cache``: Lazily built dictionary mapping rule IDs to
          configurations. While the lazy initialization is mostly safe due to
          Python's GIL, concurrent first-access from multiple threads could
          cause redundant computation.

        **When using parallel execution (e.g., pytest-xdist workers or
        ThreadPoolExecutor), create separate validator instances per worker.**
        Do not share instances across threads without external synchronization.
        The contract (ModelValidatorSubcontract) is immutable (frozen=True) and
        safe to share across threads.

        For more details, see the Threading Guide: ``docs/guides/THREADING.md``

    Attributes:
        validator_id: Unique identifier for this validator (must be set by subclass).
        contract: The validator contract (loaded lazily if not provided).
    """

    # ONEX_EXCLUDE: string_id - human-readable validator identifier
    validator_id: ClassVar[str]

    def __init__(self, contract: ModelValidatorSubcontract | None = None) -> None:
        """Initialize validator with optional pre-loaded contract.

        Args:
            contract: Pre-loaded validator contract. If None, the contract
                will be loaded from the default YAML location when first accessed.
        """
        self._contract = contract
        # Thread Safety: This cache is NOT thread-safe. When using parallel
        # execution (e.g., pytest-xdist), create separate validator instances
        # per worker. Cache is cleared after validate() completes to prevent
        # unbounded memory growth.
        self._file_line_cache: dict[Path, list[str]] = {}
        # Precomputed rule configuration cache for O(1) lookups
        # Maps rule_id -> (enabled, severity)
        # Thread Safety: This cache is lazily initialized on first access.
        # While Python's GIL provides basic atomicity, concurrent first-access
        # from multiple threads could cause redundant computation. For thread-safe
        # usage, create separate validator instances per thread/worker.
        # See docs/guides/THREADING.md for details.
        self._rule_config_cache: dict[str, tuple[bool, EnumSeverity]] | None = None

    @property
    def contract(self) -> ModelValidatorSubcontract:
        """Get the validator contract, loading from YAML if needed.

        Returns:
            The loaded ModelValidatorSubcontract instance.

        Raises:
            ModelOnexError: If contract loading fails.
        """
        if self._contract is None:
            self._contract = self._load_contract()
        return self._contract

    def validate(
        self,
        targets: Path | list[Path],
    ) -> ModelValidationResult[None]:
        """Validate target files/directories and return aggregated result.

        Resolves all target paths, filters exclusions, validates each file,
        and aggregates results into a single ModelValidationResult.

        Args:
            targets: Single path or list of paths to validate. Paths can be
                files or directories. Directories are expanded using the
                contract's target_patterns.

        Returns:
            ModelValidationResult containing all issues found, with deterministic
            ordering (by severity, then file path, then line number).
        """
        start_time = time.time()

        # Normalize to list
        if isinstance(targets, Path):
            targets = [targets]

        # Resolve all target files
        resolved_files = self._resolve_targets(targets)

        # Filter excluded files
        files_to_validate = [f for f in resolved_files if not self._is_excluded(f)]

        # Validate each file and collect issues
        all_issues: list[ModelValidationIssue] = []
        files_with_violations: list[str] = []

        try:
            for file_path in files_to_validate:
                file_issues = self._validate_file_with_suppression(file_path)
                if file_issues:
                    all_issues.extend(file_issues)
                    files_with_violations.append(str(file_path))

                # Check violation limit
                if (
                    self.contract.max_violations > 0
                    and len(all_issues) >= self.contract.max_violations
                ):
                    break

            duration_ms = int((time.time() - start_time) * 1000)

            return self._build_result(
                files_checked=files_to_validate,
                issues=all_issues,
                files_with_violations=files_with_violations,
                duration_ms=duration_ms,
            )
        finally:
            # Cache lifecycle: _file_line_cache is populated during validation via
            # _get_file_lines() calls. Clear in finally block to ensure cleanup even
            # on errors, preventing unbounded memory growth in long-lived instances.
            self._file_line_cache.clear()

    def validate_file(self, path: Path) -> ModelValidationResult[None]:
        """Validate a single file and return result.

        Convenience method for validating a single file. Respects exclusion
        patterns and suppression comments.

        Args:
            path: Path to the file to validate.

        Returns:
            ModelValidationResult for this single file.
        """
        start_time = time.time()

        # Check if file should be excluded
        if self._is_excluded(path):
            return ModelValidationResult.create_valid(
                summary=f"File excluded by pattern: {path}",
            )

        try:
            # Validate with suppression handling
            issues = self._validate_file_with_suppression(path)

            duration_ms = int((time.time() - start_time) * 1000)

            files_with_violations = [str(path)] if issues else []

            return self._build_result(
                files_checked=[path],
                issues=list(issues),
                files_with_violations=files_with_violations,
                duration_ms=duration_ms,
            )
        finally:
            # Cache lifecycle: Same as validate() - clear in finally block to ensure
            # cleanup even on errors, preventing unbounded memory growth.
            self._file_line_cache.clear()

    @abstractmethod
    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single file. Must be implemented by subclasses.

        This is the core validation method that subclasses implement.
        The base class handles file discovery, exclusion, suppression,
        and result aggregation.

        Args:
            path: Path to file being validated. Guaranteed to exist and
                not be excluded by patterns.
            contract: The validator contract with rules configuration.

        Returns:
            Tuple of validation issues found (empty if valid).
            Issues should have file_path and line_number set for
            proper suppression handling and ordering.
        """
        ...

    def _validate_file_with_suppression(
        self,
        path: Path,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate file and filter suppressed issues.

        Calls _validate_file and filters out any issues that are suppressed
        by inline comments.

        Args:
            path: Path to file being validated.

        Returns:
            Tuple of non-suppressed validation issues.
        """
        # Get raw issues from subclass implementation
        issues = self._validate_file(path, self.contract)

        # Filter suppressed issues
        return tuple(
            issue
            for issue in issues
            if not self._is_suppressed(
                path,
                issue.line_number if issue.line_number is not None else 0,
            )
        )

    def _resolve_targets(self, targets: list[Path]) -> list[Path]:
        """Expand directories and glob patterns into file list.

        For each target:
        - If it's a file, include it directly
        - If it's a directory, expand using contract's target_patterns

        Security: Validates source_root for path traversal before use.
        This is defense-in-depth; the primary validation is in
        ModelValidatorSubcontract.validate_source_root_no_traversal().

        Args:
            targets: List of file or directory paths.

        Returns:
            Deduplicated list of file paths, sorted for deterministic order.

        Raises:
            ModelOnexError: If source_root contains path traversal sequences.
        """
        resolved: set[Path] = set()

        for target in targets:
            if not target.exists():
                continue

            if target.is_file():
                resolved.add(target.resolve())
            elif target.is_dir():
                # Use source_root from contract if set, otherwise use target
                base_dir = self.contract.source_root or target

                # Security: Defense-in-depth path traversal check for source_root
                if self.contract.source_root is not None:
                    source_root_str = str(self.contract.source_root)
                    # Check for traversal patterns (.., //)
                    if ".." in source_root_str or "//" in source_root_str:
                        raise ModelOnexError(
                            message=(
                                f"Security: Path traversal detected in "
                                f"source_root: {source_root_str}"
                            ),
                            error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                            context={
                                "source_root": source_root_str,
                                "validator_id": self.validator_id,
                            },
                        )
                    # Resolve to absolute path and verify it exists
                    base_dir = self.contract.source_root.resolve()

                for pattern in self.contract.target_patterns:
                    # Handle absolute vs relative glob patterns
                    for match in base_dir.glob(pattern):
                        if match.is_file() and not match.is_symlink():
                            resolved.add(match.resolve())

        return sorted(resolved)

    def _is_excluded(self, path: Path) -> bool:
        """Check if path matches any exclusion pattern.

        Uses fnmatch for pattern matching against the contract's
        exclude_patterns. Supports three matching strategies:

        1. **Full path match**: Pattern matched against complete path string
           (both OS-native and POSIX formats for cross-platform compatibility)

        2. **Directory component match**: For patterns that target specific
           directories (like `**/__pycache__/**`), extracts the core directory
           name and matches against individual path components.

        Pattern Handling:
            - Patterns like `**/dirname/**` match any path containing `dirname/`
            - Patterns like `**/*_test.py` match files ending with `_test.py`
            - Literal patterns (no wildcards) require exact matches

        Args:
            path: Path to check.

        Returns:
            True if the path should be excluded, False otherwise.
        """
        path_str = str(path)
        path_posix = path.as_posix()

        for pattern in self.contract.exclude_patterns:
            # Match against both string representation and POSIX path
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if fnmatch.fnmatch(path_posix, pattern):
                return True

            # Component-based matching for directory patterns
            # Only strip leading/trailing wildcards if the pattern is a typical
            # glob pattern (contains **). This handles patterns like:
            #   - "**/node_modules/**" -> matches 'node_modules' in any path part
            #   - "**/__pycache__/**" -> matches '__pycache__' in any path part
            #
            # We use lstrip/rstrip separately to be more precise about what we remove,
            # avoiding the issue where strip("*/") would remove characters in any order.
            if "**" in pattern or pattern.startswith("*/") or pattern.endswith("/*"):
                # Extract the core pattern by removing glob traversal markers
                # Start with the full pattern
                core_pattern = pattern
                # Remove leading glob patterns (**, */)
                while core_pattern.startswith(("**/", "*/")):
                    core_pattern = core_pattern[
                        3 if core_pattern.startswith("**/") else 2 :
                    ]
                # Remove trailing glob patterns (**, /*)
                while core_pattern.endswith(("/**", "/*")):
                    core_pattern = core_pattern[
                        : -3 if core_pattern.endswith("/**") else -2
                    ]

                # Only proceed if we extracted a meaningful pattern
                if core_pattern and core_pattern != "*":
                    for part in path.parts:
                        if fnmatch.fnmatch(part, core_pattern):
                            return True

        return False

    def _is_suppressed(self, path: Path, line_number: int) -> bool:
        """Check if violation at line is suppressed by comment.

        Reads the file and checks if the specified line contains any
        of the suppression comment patterns from the contract.

        Args:
            path: Path to the file.
            line_number: Line number to check (1-indexed).

        Returns:
            True if the line contains a suppression comment, False otherwise.
        """
        if line_number <= 0:
            return False

        # Get file lines (with caching)
        lines = self._get_file_lines(path)
        if not lines or line_number > len(lines):
            return False

        # Get the line (convert to 0-indexed)
        line = lines[line_number - 1]

        # Check for suppression comments
        for pattern in self.contract.suppression_comments:
            if pattern in line:
                return True

        return False

    def _get_file_lines(self, path: Path) -> list[str]:
        """Read file lines with caching.

        Caches file contents to avoid repeated reads during validation.

        Args:
            path: Path to the file.

        Returns:
            List of lines in the file, or empty list on error.
        """
        if path in self._file_line_cache:
            return self._file_line_cache[path]

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            self._file_line_cache[path] = lines
            return lines
        except FILE_IO_ERRORS as e:
            # fallback-ok: log warning and return empty list if file cannot be read
            logger.warning(
                "Cannot read file for suppression check: %s (error: %s)",
                path,
                e,
            )
            return []

    def _build_rule_config_cache(
        self,
        contract: ModelValidatorSubcontract,
    ) -> dict[str, tuple[bool, EnumSeverity]]:
        """Build precomputed cache of rule configurations for O(1) lookups.

        Creates a dictionary mapping rule_id to (enabled, severity) tuple.
        This is called once when the contract is first accessed, avoiding
        repeated iteration over contract rules during validation.

        Thread Safety:
            This method itself is safe to call from multiple threads, but the
            cache it builds should only be stored in instance state when the
            caller can guarantee single-writer semantics. See class docstring
            for thread safety guidelines.

        Args:
            contract: Validator contract with rule configurations.

        Returns:
            Dictionary mapping rule_id to (enabled, severity) tuple.
        """
        cache: dict[str, tuple[bool, EnumSeverity]] = {}
        for rule in contract.rules:
            # Guard against None severity - use contract default if None
            # Note: severity has a default in ModelValidatorRule, but this is defensive
            # for future model changes or external data sources
            if rule.severity is None:
                # NOTE(OMN-1302): Defensive logging for impossible case. Safe because guards external data.
                logger.debug(  # type: ignore[unreachable]
                    "Rule %s missing severity, using default: %s",
                    rule.rule_id,
                    contract.severity_default,
                )
            severity = (
                rule.severity
                if rule.severity is not None
                else contract.severity_default
            )
            cache[rule.rule_id] = (rule.enabled, severity)
        return cache

    def _get_rule_config(
        self,
        rule_id: str | None,
        contract: ModelValidatorSubcontract,
    ) -> tuple[bool, EnumSeverity]:
        """Get rule enabled state and severity from precomputed cache.

        Uses O(1) dictionary lookup instead of iterating through all rules.
        Cache is lazily built on first access.

        Thread Safety:
            This method uses lazy initialization which is mostly safe due to
            Python's GIL, but concurrent first-access from multiple threads
            could cause redundant computation. For thread-safe usage, create
            separate validator instances per thread/worker.
            See docs/guides/THREADING.md for details.

        Default Behavior for Missing Rules:
            Rules NOT explicitly defined in the contract are **disabled** by default.
            This follows the principle of explicit opt-in: validators must explicitly
            list rules they want to enforce. This ensures consistent behavior across
            all validators and prevents unexpected validation failures when new rules
            are added to a validator implementation.

        Args:
            rule_id: The rule identifier to look up. If None, returns
                (False, default_severity) - no rule ID means rule is not configured.
            contract: Validator contract with rule configurations.

        Returns:
            Tuple of (enabled, severity) for the rule. If rule is not in
            contract or rule_id is None, returns (False, default_severity)
            because missing rules are disabled by default.
        """
        if rule_id is None:
            logger.debug(
                "Rule ID is None, rule disabled by default (severity: %s)",
                contract.severity_default,
            )
            return (False, contract.severity_default)

        # Lazily build cache on first access
        if self._rule_config_cache is None:
            self._rule_config_cache = self._build_rule_config_cache(contract)

        # O(1) lookup from cache
        if rule_id in self._rule_config_cache:
            return self._rule_config_cache[rule_id]

        # Rule not in contract - disabled by default (explicit opt-in required)
        logger.debug(
            "Rule %s not in contract, disabled by default (severity: %s)",
            rule_id,
            contract.severity_default,
        )
        return (False, contract.severity_default)

    def _load_contract(self) -> ModelValidatorSubcontract:
        """Load contract from default YAML location.

        Loads the contract from {module_dir}/contracts/{validator_id}.validation.yaml.
        Subclasses can override this for custom loading logic.

        Returns:
            Loaded ModelValidatorSubcontract instance.

        Raises:
            ModelOnexError: If contract file not found or invalid.
        """
        contract_path = self._get_contract_path()

        if not contract_path.exists():
            raise ModelOnexError(
                message=f"Validator contract not found: {contract_path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                context={
                    "validator_id": self.validator_id,
                    "contract_path": str(contract_path),
                },
            )

        try:
            content = contract_path.read_text(encoding="utf-8")
            # ONEX_EXCLUDE: manual_yaml - validator contract loading requires raw YAML
            data = yaml.safe_load(content)

            if not isinstance(data, dict):
                raise ModelOnexError(
                    message="Contract must be a YAML mapping",
                    error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                    context={
                        "validator_id": self.validator_id,
                        "contract_path": str(contract_path),
                    },
                )

            # Handle nested 'validation:' structure (common in validation_subcontract files)
            if "validation" in data and isinstance(data["validation"], dict):
                data = data["validation"]

            try:
                return ModelValidatorSubcontract.model_validate(data)
            except PYDANTIC_MODEL_ERRORS as e:
                # boundary-ok: convert Pydantic validation errors to structured error
                raise ModelOnexError(
                    message=f"Contract schema validation failed: {e}",
                    error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                    context={
                        "validator_id": self.validator_id,
                        "contract_path": str(contract_path),
                        "validation_error": str(e),
                    },
                ) from e

        except FILE_IO_ERRORS as e:
            # boundary-ok: convert file I/O errors to structured error
            raise ModelOnexError(
                message=f"Cannot read contract file: {e}",
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                context={
                    "validator_id": self.validator_id,
                    "contract_path": str(contract_path),
                    "error": str(e),
                },
            ) from e
        except YAML_PARSING_ERRORS as e:
            # boundary-ok: convert YAML parsing errors to structured error
            raise ModelOnexError(
                message=f"Invalid YAML in contract file: {e}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                context={
                    "validator_id": self.validator_id,
                    "contract_path": str(contract_path),
                    "yaml_error": str(e),
                },
            ) from e

    def _get_contract_path(self) -> Path:
        """Get path to contract YAML file.

        Default implementation returns:
        {module_dir}/contracts/{validator_id}.validation.yaml

        Subclasses can override for custom path resolution.

        Returns:
            Path to the contract YAML file.
        """
        # Get the module directory of the subclass
        import inspect

        subclass_file = inspect.getfile(self.__class__)
        module_dir = Path(subclass_file).parent

        return module_dir / "contracts" / f"{self.validator_id}.validation.yaml"

    def _build_result(
        self,
        files_checked: list[Path],
        issues: list[ModelValidationIssue],
        files_with_violations: list[str],
        duration_ms: int,
    ) -> ModelValidationResult[None]:
        """Build final result with deterministic ordering.

        Sorts issues by severity (priority), then file path, then line number
        to ensure deterministic output across runs.

        Args:
            files_checked: List of files that were checked.
            issues: List of validation issues found.
            files_with_violations: List of file paths with violations.
            duration_ms: Validation duration in milliseconds.

        Returns:
            ModelValidationResult with sorted issues and metadata.
        """
        # Sort issues deterministically: severity -> file -> line
        sorted_issues = sorted(
            issues,
            key=lambda i: (
                SEVERITY_PRIORITY.get(i.severity, 999),
                str(i.file_path or ""),
                i.line_number or 0,
            ),
        )

        # Count by severity
        error_level_count = sum(
            1 for i in sorted_issues if i.severity == EnumSeverity.ERROR
        )
        warning_count = sum(
            1 for i in sorted_issues if i.severity == EnumSeverity.WARNING
        )
        critical_count = sum(
            1 for i in sorted_issues if i.severity == EnumSeverity.CRITICAL
        )

        # Determine validity based on contract settings
        has_errors = error_level_count > 0 or critical_count > 0
        has_warnings = warning_count > 0

        is_valid = True
        if self.contract.fail_on_error and has_errors:
            is_valid = False
        if self.contract.fail_on_warning and has_warnings:
            is_valid = False

        # Build summary
        total_issues = len(sorted_issues)
        if total_issues == 0:
            summary = f"Validation passed: {len(files_checked)} files checked"
        else:
            summary = (
                f"Validation {'failed' if not is_valid else 'completed'}: "
                f"{total_issues} issue(s) in {len(files_with_violations)} file(s)"
            )

        # Build metadata
        metadata = ModelValidationMetadata(
            validation_type=self.validator_id,
            duration_ms=duration_ms,
            files_processed=len(files_checked),
            rules_applied=len([r for r in self.contract.rules if r.enabled]),
            timestamp=datetime.now(tz=UTC).isoformat(),
            validator_version=self.contract.version,
            violations_found=total_issues,
            files_with_violations=files_with_violations,
            files_with_violations_count=len(files_with_violations),
            strict_mode=self.contract.fail_on_warning,
        )

        return ModelValidationResult[None](
            is_valid=is_valid,
            issues=sorted_issues,
            summary=summary,
            metadata=metadata,
        )

    def get_exit_code(self, result: ModelValidationResult[None]) -> int:
        """Map validation result to CLI exit code.

        Exit codes:
            - 0: Success (no errors or warnings requiring failure)
            - 1: Errors found (ERROR or CRITICAL severity)
            - 2: Warnings found (when fail_on_warning is True)

        Args:
            result: The validation result to map.

        Returns:
            Integer exit code for shell integration.
        """
        if result.is_valid:
            return EXIT_SUCCESS

        # Check for errors/critical issues
        if result.has_errors() or result.has_critical_issues():
            return EXIT_ERRORS

        # Must be warnings (when fail_on_warning is True)
        return EXIT_WARNINGS

    @classmethod
    def _validate_cli_path(cls, path: Path, context: str) -> Path | None:
        """Validate CLI-provided path for security.

        Security: Comprehensive checks for path traversal attempts in user-provided
        paths. This is critical for CLI tools where paths come from untrusted input.

        Checks performed:
            - Standard traversal: ``..`` patterns (Unix-style)
            - Windows traversal: ``..\\`` patterns (backslash separator)
            - URL-encoded traversal: ``%2e%2e`` (encoded dots), ``%2f`` (encoded slash)
            - Null bytes: ``\\x00`` (can truncate paths in some systems)
            - Double slashes: ``//`` (can bypass path normalization)

        This method is available for all validators to use for consistent
        path validation across the validation framework.

        Args:
            path: User-provided path to validate.
            context: Description of the path for error messages.

        Returns:
            Resolved path if valid, None if security check fails.
        """
        path_str = str(path)

        # Security: Reject paths with null bytes (can truncate paths)
        if "\x00" in path_str:
            print(
                f"Security error: Null byte detected in {context}: {path!r}",
                file=sys.stderr,
            )
            return None

        # Security: Reject paths with traversal sequences (..)
        # This catches both Unix-style (../) and Windows-style (..\\) traversal
        if ".." in path_str:
            print(
                f"Security error: Path traversal detected in {context}: {path}",
                file=sys.stderr,
            )
            return None

        # Security: Reject paths with URL-encoded traversal sequences
        # %2e = '.', %2f = '/', %5c = '\\' - common bypass attempts
        path_lower = path_str.lower()
        if "%2e" in path_lower or "%2f" in path_lower or "%5c" in path_lower:
            print(
                f"Security error: URL-encoded path traversal detected in {context}: {path}",
                file=sys.stderr,
            )
            return None

        # Security: Reject paths with double slashes (bypass attempts)
        if "//" in path_str:
            print(
                f"Security error: Invalid path format in {context}: {path}",
                file=sys.stderr,
            )
            return None

        try:
            return path.resolve()
        except (OSError, ValueError) as e:
            print(f"Error resolving {context}: {path} ({e})", file=sys.stderr)
            return None

    @classmethod
    def main(cls) -> int:
        """CLI entry point for running validator standalone.

        Parses command-line arguments and runs validation on the specified
        targets (or current directory by default).

        Security: All user-provided paths are validated for path traversal
        attacks before use. Paths containing ".." or "//" are rejected.

        Returns:
            Exit code for shell integration (0 = success, non-zero = failure).

        Example:
            if __name__ == "__main__":
                import sys
                sys.exit(MyValidator.main())
        """
        parser = argparse.ArgumentParser(
            description=f"Run {cls.validator_id} validator",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "targets",
            nargs="*",
            type=Path,
            default=[Path()],
            help="Files or directories to validate (default: current directory)",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Print detailed output",
        )
        parser.add_argument(
            "--contract",
            type=Path,
            default=None,
            help="Path to custom contract YAML file",
        )

        args = parser.parse_args()

        # Security: Validate all user-provided target paths
        validated_targets: list[Path] = []
        for target in args.targets:
            validated = cls._validate_cli_path(target, "target path")
            if validated is None:
                return EXIT_ERRORS
            validated_targets.append(validated)

        # Load custom contract if specified
        contract: ModelValidatorSubcontract | None = None
        if args.contract:
            # Security: Validate contract path before reading
            validated_contract = cls._validate_cli_path(args.contract, "contract path")
            if validated_contract is None:
                return EXIT_ERRORS

            if not validated_contract.exists():
                print(
                    f"Error: Contract file not found: {validated_contract}",
                    file=sys.stderr,
                )
                return EXIT_ERRORS

            if not validated_contract.is_file():
                print(
                    f"Error: Contract path is not a file: {validated_contract}",
                    file=sys.stderr,
                )
                return EXIT_ERRORS

            try:
                content = validated_contract.read_text(encoding="utf-8")
            except FILE_IO_ERRORS as e:
                print(
                    f"Error reading contract file {validated_contract}: {e}",
                    file=sys.stderr,
                )
                return EXIT_ERRORS

            try:
                # ONEX_EXCLUDE: manual_yaml - validator contract loading
                data = yaml.safe_load(content)
            except YAML_PARSING_ERRORS as e:
                print(
                    f"Error parsing contract YAML {validated_contract}: {e}",
                    file=sys.stderr,
                )
                return EXIT_ERRORS

            if not isinstance(data, dict):
                print(
                    f"Error loading contract {validated_contract}: must be a YAML mapping",
                    file=sys.stderr,
                )
                return EXIT_ERRORS

            # Handle nested 'validation:' structure (match _load_contract behavior)
            if "validation" in data and isinstance(data["validation"], dict):
                data = data["validation"]

            try:
                contract = ModelValidatorSubcontract.model_validate(data)
            except PYDANTIC_MODEL_ERRORS as e:
                print(
                    f"Contract schema validation failed for {validated_contract}: {e}",
                    file=sys.stderr,
                )
                return EXIT_ERRORS

        # Create validator and run
        validator = cls(contract=contract)

        try:
            result = validator.validate(validated_targets)
        except ModelOnexError as e:
            print(f"Validation error: {e.message}", file=sys.stderr)
            return EXIT_ERRORS

        # Print results
        if args.verbose or not result.is_valid:
            print(result.summary)
            if result.issues:
                print()
                for issue in result.issues:
                    location = ""
                    if issue.file_path:
                        location = str(issue.file_path)
                        if issue.line_number:
                            location += f":{issue.line_number}"
                        location += ": "
                    print(
                        f"  [{issue.severity.value.upper()}] {location}{issue.message}"
                    )

        return validator.get_exit_code(result)


__all__ = [
    "EXIT_ERRORS",
    "EXIT_SUCCESS",
    "EXIT_WARNINGS",
    "SEVERITY_PRIORITY",
    "ValidatorBase",
]
