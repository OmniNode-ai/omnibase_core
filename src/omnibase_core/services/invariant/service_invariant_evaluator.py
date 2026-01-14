"""Service for evaluating invariants against execution outputs.

This module provides the ServiceInvariantEvaluator class for validating
that outputs conform to defined invariants (validation rules).

Thread Safety:
    ServiceInvariantEvaluator is NOT thread-safe. Create separate instances
    per thread or use thread-local storage. The schema validator cache is
    instance-level and should not be shared across threads.

Example:
    >>> from omnibase_core.services.invariant.service_invariant_evaluator import (
    ...     ServiceInvariantEvaluator,
    ... )
    >>> from omnibase_core.models.invariant import ModelInvariant, ModelInvariantSet
    >>> from omnibase_core.enums import EnumInvariantType, EnumSeverity
    >>>
    >>> evaluator = ServiceInvariantEvaluator()
    >>> invariant = ModelInvariant(
    ...     name="latency_check",
    ...     type=EnumInvariantType.LATENCY,
    ...     severity=EnumSeverity.CRITICAL,
    ...     config={"max_ms": 500},
    ... )
    >>> result = evaluator.evaluate(invariant, {"latency_ms": 250})
    >>> print(result.passed)  # True
"""

import hashlib
import importlib
import json
import logging
import re
import signal
import sys
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import UTC, datetime
from typing import Any

import jsonschema
from jsonschema.protocols import Validator

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.errors.error_regex_timeout import RegexTimeoutError
from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
from omnibase_core.models.invariant import (
    ModelEvaluationSummary,
    ModelInvariant,
    ModelInvariantResult,
    ModelInvariantSet,
)

logger = logging.getLogger(__name__)


class ServiceInvariantEvaluator:
    """Evaluates invariants against execution outputs.

    Provides methods to evaluate single invariants, batches from an invariant set,
    and full evaluation with summary statistics.

    Attributes:
        allowed_import_paths: Optional allow-list for custom callable imports.
            If None, all paths are allowed (trusted code model).
        SLOW_EVALUATION_THRESHOLD_MS: Threshold in milliseconds above which
            evaluation time triggers a warning log.
        SCHEMA_VALIDATOR_CACHE_SIZE: Maximum number of compiled schema validators
            to cache. Uses LRU eviction when limit is reached.

    Thread Safety:
        This class is NOT thread-safe. Create separate instances per thread
        or use thread-local storage. The schema validator cache is instance-level
        and should not be shared across threads.

    Example:
        >>> evaluator = ServiceInvariantEvaluator()
        >>> result = evaluator.evaluate(invariant, output)
        >>> if not result.passed:
        ...     print(f"Failed: {result.message}")
    """

    SLOW_EVALUATION_THRESHOLD_MS: float = 25.0
    MAX_FIELD_PATH_DEPTH: int = 20
    MAX_REGEX_PATTERN_LENGTH: int = 1000
    MAX_REGEX_INPUT_LENGTH: int = 100000  # 100KB max input for regex operations
    REGEX_TIMEOUT_SECONDS: float = 1.0
    SCHEMA_VALIDATOR_CACHE_SIZE: int = 128

    # Patterns that indicate potential ReDoS vulnerability (nested quantifiers)
    # These detect nested quantifiers and overlapping alternations that can cause
    # catastrophic backtracking
    _REDOS_DANGEROUS_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"\([^)]*[+*]\)[+*]"),  # Nested quantifiers like (a+)+ or (a*)*
        re.compile(r"\([^)]*\{[^}]+\}\)[+*]"),  # Nested {n,m} with + or *
        re.compile(r"\([^)]*\|[^)]*\)[+*]"),  # Alternation with quantifier: (a|b)+
        re.compile(r"[+*]\??\.[+*]"),  # Adjacent quantifiers with wildcards: .*.*
        re.compile(r"(\.\*){2,}"),  # Multiple .* sequences
        re.compile(
            r"\[[^\]]*\][+*]\[[^\]]*\][+*]"
        ),  # Adjacent char classes: [a-z]+[0-9]+
    )

    # Pattern for validating Python module paths (security: prevents injection attacks)
    # Matches: module.path, module.path:function, module.path.function
    # Each segment must be a valid Python identifier (starts with letter/underscore,
    # followed by letters/digits/underscores)
    _VALID_MODULE_PATH_PATTERN: re.Pattern[str] = re.compile(
        r"^[a-zA-Z_][a-zA-Z0-9_]*"  # First segment (required)
        r"(\.[a-zA-Z_][a-zA-Z0-9_]*)*"  # Additional dot-separated segments (optional)
        r"(:[a-zA-Z_][a-zA-Z0-9_]*)?$"  # Colon-separated function name (optional)
    )

    # Pattern for validating module paths only (without function name)
    # Used for defense-in-depth validation of the parsed module_path
    _VALID_MODULE_ONLY_PATTERN: re.Pattern[str] = re.compile(
        r"^[a-zA-Z_][a-zA-Z0-9_]*"  # First segment (required)
        r"(\.[a-zA-Z_][a-zA-Z0-9_]*)*$"  # Additional dot-separated segments (optional)
    )

    def __init__(self, allowed_import_paths: list[str] | None = None) -> None:
        """Initialize the invariant evaluator.

        Args:
            allowed_import_paths: Optional allow-list for custom callable imports.
                If None, all paths are allowed (trusted code model).
                If provided, only callable_path values starting with one of
                these prefixes are permitted for CUSTOM invariants.
        """
        self.allowed_import_paths = allowed_import_paths
        # LRU cache for compiled schema validators (OrderedDict maintains insertion order)
        # Key: SHA-256 hash of JSON-serialized schema
        # Value: Compiled validator instance
        self._schema_validator_cache: OrderedDict[str, Validator] = OrderedDict()

    def _is_import_path_allowed(self, callable_path: str) -> bool:
        """Check if callable_path is allowed by the configured allow-list.

        This method validates custom callable paths against a configurable
        allow-list to prevent unauthorized code execution. It implements
        multiple security layers to ensure only trusted callables are invoked.

        Security Model:
            The allow-list security model operates as follows:

            1. **Trusted Code Model** (allow-list=None):
               When no allow-list is configured, all valid Python paths are
               permitted. Use this only in fully trusted environments where
               all invariant configurations come from trusted sources.

            2. **Restricted Model** (allow-list configured):
               Only callables from explicitly allowed module prefixes are
               permitted. This is the recommended mode for production use
               where invariant configurations may come from external sources.

        Security Measures:
            1. **Path Format Validation**: Only valid Python module paths are
               accepted. Malformed paths (containing invalid characters or
               injection attempts) are rejected before checking the allow-list.
               Pattern: ``^[a-zA-Z_][a-zA-Z0-9_]*(\\.[a-zA-Z_][a-zA-Z0-9_]*)*``

            2. **Empty Prefix Rejection**: Empty strings in the allow-list are
               ignored with a warning log, as they could match unintended paths.

            3. **Prefix Format Validation**: Each allow-list prefix is validated
               to ensure it's a valid Python module path format before use.

            4. **Strict Boundary Matching**: Uses exact segment boundaries (dot
               or colon) to prevent prefix bypass attacks. For example, if
               ``"builtins"`` is in the allow-list, ``"builtins_evil"`` will
               NOT match because there's no valid boundary separator.

        Path Notation Formats:
            The check handles both common Python callable path formats:

            - **Dot notation**: ``"module.submodule.function"``
            - **Colon notation**: ``"module.submodule:function"``

            Both formats are equivalent; colon notation is commonly used in
            entry point specifications (e.g., setuptools console_scripts).

        Examples:
            Configure evaluator with allow-list::

                # Only allow validators from your application modules
                evaluator = ServiceInvariantEvaluator(
                    allowed_import_paths=[
                        "myapp.validators",       # All functions in this module
                        "myapp.checks",           # All functions in this module
                        "myapp.validators.core",  # Submodule
                    ]
                )

            Matching behavior examples::

                # With allow-list = ["myapp.validators"]:
                "myapp.validators.check_output"      # ALLOWED (prefix + dot)
                "myapp.validators:check_output"      # ALLOWED (prefix + colon)
                "myapp.validators"                   # ALLOWED (exact match)
                "myapp.validators_evil.check"        # BLOCKED (no boundary)
                "myapp.validators_extended.check"    # BLOCKED (no boundary)
                "os.system"                          # BLOCKED (not in list)
                "builtins.eval"                      # BLOCKED (not in list)

            Production configuration recommendation::

                # Be specific about allowed modules
                evaluator = ServiceInvariantEvaluator(
                    allowed_import_paths=[
                        "mycompany.app.validators",
                        "mycompany.app.business_rules",
                    ]
                )
                # Avoid overly broad prefixes like "mycompany" which would
                # allow any module in your entire codebase

        Args:
            callable_path: The full callable path to check. Must be in valid
                Python module path format (e.g., ``"module.submodule.function"``
                or ``"module.submodule:function"``).

        Returns:
            True if path is allowed by the configured security policy:
                - No allow-list configured (trusted code model), OR
                - Path matches an allowed prefix with proper boundaries
            False if the path is blocked due to:
                - Path not in allow-list
                - Path has invalid format (fails regex validation)
                - Allow-list contains invalid prefixes (logged as warning)
        """
        if self.allowed_import_paths is None:
            return True

        # Security: Validate callable_path format before checking allow-list
        # This prevents injection attacks via malformed paths
        if not self._VALID_MODULE_PATH_PATTERN.match(callable_path):
            logger.warning(
                "Invalid callable path format rejected (security): %r",
                callable_path[:100] if len(callable_path) > 100 else callable_path,
            )
            return False

        for prefix in self.allowed_import_paths:
            # Security: Skip empty prefixes - they could match unintended paths
            if not prefix:
                logger.warning(
                    "Empty prefix in allowed_import_paths ignored (security risk)"
                )
                continue

            # Security: Validate prefix format - must be valid module path prefix
            # Use a simpler pattern for prefixes (no colon, since prefix shouldn't
            # include function name)
            if not re.match(
                r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$", prefix
            ):
                logger.warning(
                    "Invalid prefix format in allowed_import_paths ignored: %r",
                    prefix[:100] if len(prefix) > 100 else prefix,
                )
                continue

            # Exact match
            if callable_path == prefix:
                return True
            # Prefix match with proper boundary (dot or colon separator)
            if callable_path.startswith(prefix + "."):
                return True
            if callable_path.startswith(prefix + ":"):
                return True

        return False

    def _is_module_path_allowed(self, module_path: str) -> bool:
        """Check if a module path is allowed by the configured allow-list.

        This is a stricter check that validates the actual module to be imported,
        providing defense-in-depth after parsing the callable_path.

        Security Measures:
            1. Validates module_path format (only valid Python module paths)
            2. Uses strict boundary matching (dot separator only)
            3. Ensures the module being imported is within allowed namespaces

        Args:
            module_path: The module path to check (without function name).

        Returns:
            True if the path is allowed, False otherwise.
        """
        if self.allowed_import_paths is None:
            return True

        # Security: Validate module_path format
        if not self._VALID_MODULE_ONLY_PATTERN.match(module_path):
            logger.warning(
                "Invalid module path format rejected (security): %r",
                module_path[:100] if len(module_path) > 100 else module_path,
            )
            return False

        for prefix in self.allowed_import_paths:
            # Skip empty or invalid prefixes (already validated in _is_import_path_allowed)
            if not prefix or not re.match(
                r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$", prefix
            ):
                continue

            # Exact match
            if module_path == prefix:
                return True
            # Prefix match with proper boundary (dot separator only for modules)
            if module_path.startswith(prefix + "."):
                return True

        return False

    def _is_regex_safe(self, pattern: str) -> tuple[bool, str]:
        """Check if a regex pattern is safe from ReDoS attacks.

        Validates pattern for dangerous constructs that could cause
        catastrophic backtracking.

        Args:
            pattern: The regex pattern to validate.

        Returns:
            Tuple of (is_safe, error_message). If safe, error_message is empty.
        """
        # Check pattern length
        if len(pattern) > self.MAX_REGEX_PATTERN_LENGTH:
            return (
                False,
                f"Pattern too long (max {self.MAX_REGEX_PATTERN_LENGTH} chars)",
            )

        # Check for dangerous patterns that can cause catastrophic backtracking
        for dangerous_pattern in self._REDOS_DANGEROUS_PATTERNS:
            if dangerous_pattern.search(pattern):
                return (
                    False,
                    "Pattern contains potentially dangerous nested quantifiers",
                )

        # Try to compile the pattern to catch syntax errors
        try:
            re.compile(pattern)
        except re.error as e:
            return (False, f"Invalid regex pattern: {e}")

        return (True, "")

    def _regex_timeout_handler(self, signum: int, frame: Any) -> None:
        """Signal handler for regex timeout.

        Args:
            signum: Signal number.
            frame: Current stack frame.

        Raises:
            RegexTimeoutError: Always raised to interrupt the regex operation.
        """
        raise RegexTimeoutError("Regex operation timed out")

    def _safe_regex_search(
        self, pattern: str, text: str
    ) -> tuple[bool, re.Match[str] | None, str]:
        """Perform a regex search with safety checks and timeout protection.

        Thread Safety:
            This method is thread-safe and can be called from any thread.

            - **Main thread on Unix**: Uses signal.alarm for efficient timeout.
            - **Non-main threads or Windows**: Uses ThreadPoolExecutor with timeout.
              The regex runs in a worker thread and is abandoned if it exceeds
              the timeout. This properly raises RegexTimeoutError on timeout.

        Security:
            Provides protection against ReDoS (Regular Expression Denial of Service):
            1. Pattern validation rejects known dangerous patterns before execution
            2. Input length limits prevent excessive processing
            3. Timeout enforcement stops runaway regex operations

        Args:
            pattern: The regex pattern to search for.
            text: The text to search within.

        Returns:
            Tuple of (success, match, error_message).
            If success is True, match contains the result (or None if no match).
            If success is False, error_message contains the error description.

        Raises:
            This method does not raise exceptions. All errors are captured and
            returned as (False, None, error_message) tuples.
        """
        # First validate the pattern is safe
        is_safe, error_msg = self._is_regex_safe(pattern)
        if not is_safe:
            return (False, None, error_msg)

        # Security: Limit input text length to prevent DoS
        if len(text) > self.MAX_REGEX_INPUT_LENGTH:
            return (
                False,
                None,
                f"Input text too long (max {self.MAX_REGEX_INPUT_LENGTH} chars)",
            )

        # Determine if we can use signal-based timeout
        # Signal handlers only work in the main thread on Unix systems
        # Thread safety: signal.signal() raises ValueError if called from non-main thread
        can_use_signal = (
            sys.platform != "win32"
            and hasattr(signal, "SIGALRM")
            and hasattr(signal, "alarm")
            and threading.current_thread() is threading.main_thread()
        )

        if can_use_signal:
            # Use signal-based timeout on Unix main thread
            old_handler = signal.signal(signal.SIGALRM, self._regex_timeout_handler)
            try:
                # Set alarm for timeout (rounded up to next second)
                signal.alarm(int(self.REGEX_TIMEOUT_SECONDS) + 1)
                match = re.search(pattern, text)
                signal.alarm(0)  # Cancel the alarm
                return (True, match, "")
            except RegexTimeoutError:
                return (
                    False,
                    None,
                    f"Regex timed out after {self.REGEX_TIMEOUT_SECONDS}s",
                )
            except re.error as e:
                signal.alarm(0)
                return (False, None, f"Regex error: {e}")
            finally:
                signal.alarm(0)  # Ensure alarm is cancelled
                signal.signal(signal.SIGALRM, old_handler)
        else:
            # Thread-based timeout: works on any platform and any thread
            # Uses ThreadPoolExecutor to run regex in a separate thread with timeout
            # Note: The worker thread continues running after timeout, but we return
            # immediately. This is acceptable for regex operations which are CPU-bound
            # and will eventually complete (even if slowly).
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(re.search, pattern, text)
                    try:
                        match = future.result(timeout=self.REGEX_TIMEOUT_SECONDS)
                        return (True, match, "")
                    except FuturesTimeoutError:
                        # Regex operation exceeded timeout - potential ReDoS
                        logger.warning(
                            "Regex timeout: pattern took longer than %.1fs (pattern: %s)",
                            self.REGEX_TIMEOUT_SECONDS,
                            pattern[:50] + "..." if len(pattern) > 50 else pattern,
                        )
                        raise RegexTimeoutError(
                            f"Regex operation timed out after {self.REGEX_TIMEOUT_SECONDS}s"
                        )
            except RegexTimeoutError:
                return (
                    False,
                    None,
                    f"Regex timed out after {self.REGEX_TIMEOUT_SECONDS}s",
                )
            except re.error as e:
                return (False, None, f"Regex error: {e}")

    def _compute_schema_hash(self, schema: dict[str, object]) -> str:
        """Compute a stable hash for a JSON schema.

        Uses SHA-256 of the JSON-serialized schema with sorted keys to ensure
        consistent hashing regardless of dict ordering.

        Args:
            schema: The JSON schema dictionary.

        Returns:
            Hex-encoded SHA-256 hash of the serialized schema.
        """
        # Use sort_keys=True for deterministic ordering
        # Use separators to minimize whitespace for consistent hashing
        serialized = json.dumps(schema, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _get_cached_validator(self, schema: dict[str, object]) -> Validator:
        """Get or create a cached validator for the given schema.

        Uses LRU eviction when cache size exceeds SCHEMA_VALIDATOR_CACHE_SIZE.
        The validator class is auto-detected based on the schema's $schema field.

        Args:
            schema: The JSON schema dictionary.

        Returns:
            A compiled validator instance for the schema.
        """
        schema_hash = self._compute_schema_hash(schema)

        # Check if validator is cached (and move to end for LRU ordering)
        if schema_hash in self._schema_validator_cache:
            # Move to end to mark as recently used
            self._schema_validator_cache.move_to_end(schema_hash)
            return self._schema_validator_cache[schema_hash]

        # Create new validator using the appropriate validator class
        # validator_for auto-detects based on $schema field, defaults to Draft7
        validator_cls = jsonschema.validators.validator_for(schema)
        # check_schema validates the schema itself before we use it
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)

        # Evict oldest entries if cache is full
        while len(self._schema_validator_cache) >= self.SCHEMA_VALIDATOR_CACHE_SIZE:
            self._schema_validator_cache.popitem(last=False)

        # Cache the new validator
        self._schema_validator_cache[schema_hash] = validator

        return validator

    def clear_validator_cache(self) -> None:
        """Clear the schema validator cache.

        Useful for testing or when memory needs to be freed.
        """
        self._schema_validator_cache.clear()

    def get_validator_cache_size(self) -> int:
        """Get the current number of cached validators.

        Returns:
            Number of validators currently in the cache.
        """
        return len(self._schema_validator_cache)

    def evaluate(
        self,
        invariant: ModelInvariant,
        output: dict[str, object],
    ) -> ModelInvariantResult:
        """Evaluate a single invariant against output.

        Args:
            invariant: The invariant to evaluate.
            output: The output dictionary to validate against.

        Returns:
            ModelInvariantResult containing pass/fail status and details.
        """
        start_time = time.perf_counter()

        try:
            passed, message, actual_value, expected_value = self._dispatch_evaluator(
                invariant.type, invariant.config, output
            )
        except Exception as e:  # catch-all-ok: evaluation must not crash
            passed = False
            message = f"Evaluation error: {type(e).__name__}: {e}"
            actual_value = None
            expected_value = None

        duration_ms = (time.perf_counter() - start_time) * 1000

        if duration_ms > self.SLOW_EVALUATION_THRESHOLD_MS:
            logger.warning(
                "Slow invariant evaluation: %s took %.2f ms (threshold: %.2f ms)",
                invariant.name,
                duration_ms,
                self.SLOW_EVALUATION_THRESHOLD_MS,
            )

        return ModelInvariantResult(
            invariant_id=invariant.id,
            invariant_name=invariant.name,
            passed=passed,
            severity=invariant.severity,
            actual_value=actual_value,
            expected_value=expected_value,
            message=message,
            evaluated_at=datetime.now(UTC),
        )

    def evaluate_batch(
        self,
        invariant_set: ModelInvariantSet,
        output: dict[str, object],
        enabled_only: bool = True,
    ) -> list[ModelInvariantResult]:
        """Evaluate all invariants in a set.

        Evaluates each invariant sequentially, preserving order. Does not
        stop on failure.

        Args:
            invariant_set: The set of invariants to evaluate.
            output: The output dictionary to validate against.
            enabled_only: If True, only evaluate enabled invariants.

        Returns:
            List of ModelInvariantResult for each evaluated invariant.
        """
        invariants = (
            invariant_set.enabled_invariants
            if enabled_only
            else invariant_set.invariants
        )

        return [self.evaluate(inv, output) for inv in invariants]

    def evaluate_all(
        self,
        invariant_set: ModelInvariantSet,
        output: dict[str, object],
        fail_fast: bool = False,
    ) -> ModelEvaluationSummary:
        """Evaluate all invariants with summary statistics.

        Args:
            invariant_set: The set of invariants to evaluate.
            output: The output dictionary to validate against.
            fail_fast: If True, stop on first CRITICAL or FATAL failure.

        Returns:
            ModelEvaluationSummary with aggregate statistics and all results.
        """
        start_time = time.perf_counter()

        results: list[ModelInvariantResult] = []
        for invariant in invariant_set.enabled_invariants:
            result = self.evaluate(invariant, output)
            results.append(result)

            if (
                fail_fast
                and not result.passed
                and result.severity in (EnumSeverity.CRITICAL, EnumSeverity.FATAL)
            ):
                break

        total_duration_ms = (time.perf_counter() - start_time) * 1000

        # Count all statistics in a single pass over results
        passed_count = 0
        fatal_failures = 0
        critical_failures = 0
        error_failures = 0
        warning_failures = 0
        info_failures = 0

        for r in results:
            if r.passed:
                passed_count += 1
            elif r.severity == EnumSeverity.FATAL:
                fatal_failures += 1
            elif r.severity == EnumSeverity.CRITICAL:
                critical_failures += 1
            elif r.severity == EnumSeverity.ERROR:
                error_failures += 1
            elif r.severity == EnumSeverity.WARNING:
                warning_failures += 1
            elif r.severity in (EnumSeverity.INFO, EnumSeverity.DEBUG):
                # DEBUG is less severe than INFO, count both together
                info_failures += 1

        failed_count = len(results) - passed_count

        overall_passed = critical_failures == 0 and fatal_failures == 0

        return ModelEvaluationSummary(
            results=results,
            passed_count=passed_count,
            failed_count=failed_count,
            fatal_failures=fatal_failures,
            critical_failures=critical_failures,
            error_failures=error_failures,
            warning_failures=warning_failures,
            info_failures=info_failures,
            overall_passed=overall_passed,
            total_duration_ms=total_duration_ms,
            evaluated_at=datetime.now(UTC),
        )

    def _dispatch_evaluator(
        self,
        invariant_type: EnumInvariantType,
        config: dict[str, object],
        output: dict[str, object],
    ) -> tuple[bool, str, Any, Any]:
        """Dispatch to the appropriate evaluator based on invariant type.

        Args:
            invariant_type: The type of invariant.
            config: Type-specific configuration.
            output: The output to validate.

        Returns:
            Tuple of (passed, message, actual_value, expected_value).
        """
        evaluators = {
            EnumInvariantType.SCHEMA: self._evaluate_schema,
            EnumInvariantType.FIELD_PRESENCE: self._evaluate_field_presence,
            EnumInvariantType.FIELD_VALUE: self._evaluate_field_value,
            EnumInvariantType.THRESHOLD: self._evaluate_threshold,
            EnumInvariantType.LATENCY: self._evaluate_latency,
            EnumInvariantType.COST: self._evaluate_cost,
            EnumInvariantType.CUSTOM: self._evaluate_custom,
        }

        evaluator = evaluators.get(invariant_type)
        if evaluator is None:
            return (
                False,
                f"Unknown invariant type: {invariant_type}",
                None,
                None,
            )

        return evaluator(config, output)

    def _evaluate_schema(
        self,
        config: dict[str, object],
        output: dict[str, object],
    ) -> tuple[bool, str, Any, Any]:
        """Evaluate JSON schema validation.

        Uses cached validators for improved performance when validating
        multiple outputs against the same schema.

        Args:
            config: Must contain 'json_schema' key with a JSON Schema dict.
            output: The output to validate against the schema.

        Returns:
            Tuple of (passed, message, actual_value, expected_value).
        """
        json_schema = config.get("json_schema")
        if not isinstance(json_schema, dict):
            return (
                False,
                "Invalid schema config: json_schema must be a dict",
                None,
                None,
            )

        try:
            # Get or create cached validator for this schema
            validator = self._get_cached_validator(json_schema)
            # Validate the output against the cached validator
            validator.validate(output)
            return (True, "Schema validation passed", None, json_schema)
        except jsonschema.ValidationError as e:
            path = (
                ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            )
            return (
                False,
                f"Schema validation failed at '{path}': {e.message}",
                e.instance,
                e.schema,
            )
        except jsonschema.SchemaError as e:
            return (False, f"Invalid JSON schema: {e.message}", None, json_schema)

    def _evaluate_field_presence(
        self,
        config: dict[str, object],
        output: dict[str, object],
    ) -> tuple[bool, str, Any, Any]:
        """Evaluate required field presence.

        Args:
            config: Must contain 'fields' key with list of field paths.
            output: The output to check for field presence.

        Returns:
            Tuple of (passed, message, actual_value, expected_value).
        """
        fields = config.get("fields")
        if not isinstance(fields, list):
            return (False, "Invalid config: fields must be a list", None, None)

        missing_fields: list[str] = []
        for field_path in fields:
            if not isinstance(field_path, str):
                # Configuration error: field paths must be strings - fail fast
                logger.warning(
                    "Invalid field path type in config: expected str, got %s (value: %r)",
                    type(field_path).__name__,
                    field_path,
                )
                return (
                    False,
                    f"Invalid config: field path must be a string, got {type(field_path).__name__}: {field_path!r}",
                    None,
                    fields,
                )
            found, _ = self._resolve_field_path(output, field_path)
            if not found:
                missing_fields.append(field_path)

        if missing_fields:
            return (
                False,
                f"Missing required fields: {', '.join(missing_fields)}",
                missing_fields,
                fields,
            )

        return (True, "All required fields present", list(fields), fields)

    def _evaluate_field_value(
        self,
        config: dict[str, object],
        output: dict[str, object],
    ) -> tuple[bool, str, Any, Any]:
        """Evaluate field value match or pattern.

        Args:
            config: Must contain 'field_path' and either 'expected_value' or 'pattern'.
            output: The output to check field value against.

        Returns:
            Tuple of (passed, message, actual_value, expected_value).
        """
        field_path = config.get("field_path")
        if not isinstance(field_path, str):
            return (False, "Invalid config: field_path must be a string", None, None)

        found, actual_value = self._resolve_field_path(output, field_path)
        if not found:
            return (
                False,
                f"Field not found: {field_path}",
                None,
                config.get("expected_value") or config.get("pattern"),
            )

        # Check expected_value if present
        if "expected_value" in config:
            expected_value = config["expected_value"]
            if actual_value == expected_value:
                return (
                    True,
                    f"Field '{field_path}' matches expected value",
                    actual_value,
                    expected_value,
                )
            return (
                False,
                f"Field '{field_path}' value mismatch: got {actual_value!r}, expected {expected_value!r}",
                actual_value,
                expected_value,
            )

        # Check pattern if present
        if "pattern" in config:
            pattern = config["pattern"]
            if not isinstance(pattern, str):
                return (
                    False,
                    "Invalid config: pattern must be a string",
                    actual_value,
                    pattern,
                )

            actual_str = str(actual_value)

            # Use safe regex search with ReDoS protection
            success, match, error_msg = self._safe_regex_search(pattern, actual_str)
            if not success:
                return (
                    False,
                    f"Invalid config: {error_msg}",
                    actual_value,
                    pattern,
                )

            if match:
                return (
                    True,
                    f"Field '{field_path}' matches pattern",
                    actual_value,
                    pattern,
                )
            return (
                False,
                f"Field '{field_path}' does not match pattern: got {actual_value!r}, pattern {pattern!r}",
                actual_value,
                pattern,
            )

        return (
            False,
            "Invalid config: must provide expected_value or pattern",
            actual_value,
            None,
        )

    def _evaluate_threshold(
        self,
        config: dict[str, object],
        output: dict[str, object],
    ) -> tuple[bool, str, Any, Any]:
        """Evaluate metric threshold bounds.

        Args:
            config: Must contain 'metric_name' and optionally 'min_value'/'max_value'.
            output: The output containing the metric value.

        Returns:
            Tuple of (passed, message, actual_value, expected_value).
        """
        metric_name = config.get("metric_name")
        if not isinstance(metric_name, str):
            return (False, "Invalid config: metric_name must be a string", None, None)

        found, actual_value = self._resolve_field_path(output, metric_name)
        if not found:
            return (
                False,
                f"Metric not found: {metric_name}",
                None,
                {
                    "min_value": config.get("min_value"),
                    "max_value": config.get("max_value"),
                },
            )

        try:
            # NOTE(OMN-1302): Runtime conversion from unknown dict value. Safe because ValueError caught below.
            actual_num = float(actual_value)  # type: ignore[arg-type]
        except (
            TypeError,
            ValueError,
        ):  # fallback-ok: non-numeric values fail validation
            return (
                False,
                f"Metric '{metric_name}' is not numeric: {actual_value!r}",
                actual_value,
                {
                    "min_value": config.get("min_value"),
                    "max_value": config.get("max_value"),
                },
            )

        min_value = config.get("min_value")
        max_value = config.get("max_value")
        expected = {"min_value": min_value, "max_value": max_value}

        if min_value is not None:
            try:
                # NOTE(OMN-1302): Config value from dict lookup. Safe because ValueError caught below.
                min_num = float(min_value)  # type: ignore[arg-type]
                if actual_num < min_num:
                    return (
                        False,
                        f"Metric '{metric_name}' below minimum: {actual_num} < {min_num}",
                        actual_num,
                        expected,
                    )
            except (
                TypeError,
                ValueError,
            ):  # fallback-ok: invalid min_value config fails validation
                return (
                    False,
                    f"Invalid min_value: {min_value!r}",
                    actual_num,
                    expected,
                )

        if max_value is not None:
            try:
                # NOTE(OMN-1302): Config value from dict lookup. Safe because ValueError caught below.
                max_num = float(max_value)  # type: ignore[arg-type]
                if actual_num > max_num:
                    return (
                        False,
                        f"Metric '{metric_name}' above maximum: {actual_num} > {max_num}",
                        actual_num,
                        expected,
                    )
            except (
                TypeError,
                ValueError,
            ):  # fallback-ok: invalid max_value config fails validation
                return (
                    False,
                    f"Invalid max_value: {max_value!r}",
                    actual_num,
                    expected,
                )

        return (True, f"Metric '{metric_name}' within threshold", actual_num, expected)

    def _evaluate_latency(
        self,
        config: dict[str, object],
        output: dict[str, object],
    ) -> tuple[bool, str, Any, Any]:
        """Evaluate latency constraint.

        Args:
            config: Must contain 'max_ms' with maximum allowed latency.
            output: The output containing latency info (latency_ms or duration_ms).

        Returns:
            Tuple of (passed, message, actual_value, expected_value).
        """
        max_ms = config.get("max_ms")
        if max_ms is None:
            return (False, "Invalid config: max_ms is required", None, None)

        try:
            # NOTE(OMN-1302): Config value from dict lookup. Safe because ValueError caught below.
            max_ms_num = float(max_ms)  # type: ignore[arg-type]
        except VALIDATION_ERRORS:  # fallback-ok: invalid config fails validation
            return (False, f"Invalid max_ms value: {max_ms!r}", None, None)

        # Look for latency_ms or duration_ms
        actual_ms: float | None = None
        for field_name in ["latency_ms", "duration_ms"]:
            found, value = self._resolve_field_path(output, field_name)
            if found:
                try:
                    # NOTE(OMN-1302): Runtime conversion from resolved field. Safe because ValueError caught below.
                    actual_ms = float(value)  # type: ignore[arg-type]
                    break
                except (
                    TypeError,
                    ValueError,
                ):  # fallback-ok: try next field if conversion fails
                    continue

        if actual_ms is None:
            return (
                False,
                "Latency metric not found (expected 'latency_ms' or 'duration_ms')",
                None,
                max_ms_num,
            )

        if actual_ms <= max_ms_num:
            return (
                True,
                f"Latency within limit: {actual_ms}ms <= {max_ms_num}ms",
                actual_ms,
                max_ms_num,
            )

        return (
            False,
            f"Latency exceeds limit: {actual_ms}ms > {max_ms_num}ms",
            actual_ms,
            max_ms_num,
        )

    def _evaluate_cost(
        self,
        config: dict[str, object],
        output: dict[str, object],
    ) -> tuple[bool, str, Any, Any]:
        """Evaluate cost constraint.

        Args:
            config: Must contain 'max_cost' with maximum allowed cost.
            output: The output containing cost info (cost or usage.total_tokens).

        Returns:
            Tuple of (passed, message, actual_value, expected_value).
        """
        max_cost = config.get("max_cost")
        if max_cost is None:
            return (False, "Invalid config: max_cost is required", None, None)

        try:
            # NOTE(OMN-1302): Config value from dict lookup. Safe because ValueError caught below.
            max_cost_num = float(max_cost)  # type: ignore[arg-type]
        except VALIDATION_ERRORS:  # fallback-ok: invalid config fails validation
            return (False, f"Invalid max_cost value: {max_cost!r}", None, None)

        # Look for cost directly
        found, cost_value = self._resolve_field_path(output, "cost")
        if found:
            try:
                # NOTE(OMN-1302): Runtime conversion from resolved field. Safe because ValueError caught below.
                actual_cost = float(cost_value)  # type: ignore[arg-type]
            except (
                TypeError,
                ValueError,
            ):  # fallback-ok: non-numeric cost fails validation
                return (
                    False,
                    f"Invalid cost value: {cost_value!r}",
                    cost_value,
                    max_cost_num,
                )
        else:
            # Try to calculate from usage.total_tokens
            found, tokens = self._resolve_field_path(output, "usage.total_tokens")
            if found:
                try:
                    # NOTE(OMN-1302): Runtime conversion from resolved field. Safe because ValueError caught below.
                    token_count = float(tokens)  # type: ignore[arg-type]
                    # Default cost rate per token (can be customized via config)
                    cost_per_token = config.get("cost_per_token", 0.0001)
                    # NOTE(OMN-1302): Config value from dict lookup. Safe because ValueError caught below.
                    actual_cost = token_count * float(cost_per_token)  # type: ignore[arg-type]
                except (
                    TypeError,
                    ValueError,
                ):  # fallback-ok: non-numeric tokens fails validation
                    return (
                        False,
                        f"Invalid token count: {tokens!r}",
                        tokens,
                        max_cost_num,
                    )
            else:
                return (
                    False,
                    "Cost metric not found (expected 'cost' or 'usage.total_tokens')",
                    None,
                    max_cost_num,
                )

        if actual_cost <= max_cost_num:
            return (
                True,
                f"Cost within budget: {actual_cost} <= {max_cost_num}",
                actual_cost,
                max_cost_num,
            )

        return (
            False,
            f"Cost exceeds budget: {actual_cost} > {max_cost_num}",
            actual_cost,
            max_cost_num,
        )

    def _evaluate_custom(
        self,
        config: dict[str, object],
        output: dict[str, object],
    ) -> tuple[bool, str, Any, Any]:
        """Evaluate custom callable validation.

        Dynamically imports and executes a user-defined validation function.
        This allows users to define arbitrary validation logic that cannot be
        expressed with the built-in invariant types (SCHEMA, FIELD_PRESENCE,
        FIELD_VALUE, THRESHOLD, LATENCY, COST).

        Custom Callable Signatures:
            Custom callables must follow one of these two signature patterns:

            **Pattern 1: Boolean-only return** (simple validators)::

                def my_validator(output: dict[str, Any], **kwargs) -> bool:
                    '''Returns True if validation passes, False otherwise.'''
                    return "required_field" in output

            **Pattern 2: Tuple return with message** (descriptive validators)::

                def my_validator(output: dict[str, Any], **kwargs) -> tuple[bool, str]:
                    '''Returns (passed, message) for detailed feedback.'''
                    if "required_field" not in output:
                        return (False, "Missing required_field")
                    return (True, "Validation passed")

            The ``**kwargs`` parameter receives any additional configuration keys
            from the invariant config (excluding ``callable_path`` itself).

        Configuration Schema:
            The config dictionary must contain:

            - ``callable_path`` (str, required): Fully qualified Python path to
              the validation function. Supports two formats:

              - Dot notation: ``"module.submodule.function_name"``
              - Colon notation: ``"module.submodule:function_name"``

            - Additional keys (optional): Any other key-value pairs in the config
              are passed as keyword arguments to the callable.

        Security Model:
            Custom callables involve dynamic code execution, which requires
            careful security consideration:

            **Trusted Code Model** (default):
                When ``allowed_import_paths=None``, any valid Python path is
                permitted. Use only when all invariant configurations come from
                trusted sources (e.g., version-controlled config files).

            **Restricted Model** (recommended for production):
                When ``allowed_import_paths`` is set, only callables from the
                specified module prefixes are allowed. Uses strict boundary
                matching to prevent bypass attacks.

            See ``_is_import_path_allowed()`` for detailed security documentation.

        Examples:
            **Basic boolean validator**::

                # Validator function
                def has_valid_status(output: dict, **kwargs) -> bool:
                    return output.get("status") in ["success", "completed"]

                # Invariant config
                invariant = ModelInvariant(
                    name="status_check",
                    type=EnumInvariantType.CUSTOM,
                    severity=EnumSeverity.CRITICAL,
                    config={"callable_path": "myapp.validators.has_valid_status"},
                )

            **Validator with kwargs**::

                # Validator function
                def check_min_items(
                    output: dict,
                    min_count: int = 1,
                    field: str = "items",
                    **kwargs
                ) -> tuple[bool, str]:
                    items = output.get(field, [])
                    count = len(items) if isinstance(items, list) else 0
                    if count >= min_count:
                        return (True, f"Found {count} items (min: {min_count})")
                    return (False, f"Only {count} items, need at least {min_count}")

                # Invariant config - kwargs are passed to the function
                config = {
                    "callable_path": "myapp.validators:check_min_items",
                    "min_count": 5,
                    "field": "results"
                }

            **Validator with complex business logic**::

                def validate_api_response(
                    output: dict,
                    require_pagination: bool = False,
                    **kwargs
                ) -> tuple[bool, str]:
                    '''Validate API response structure and content.'''
                    errors = []

                    # Check required fields
                    if "data" not in output:
                        errors.append("Missing 'data' field")

                    # Check pagination if required
                    if require_pagination:
                        if "pagination" not in output:
                            errors.append("Missing 'pagination' field")
                        elif not output["pagination"].get("total"):
                            errors.append("Pagination missing 'total'")

                    if errors:
                        return (False, "; ".join(errors))
                    return (True, "API response is valid")

            **Using colon notation (entry point style)**::

                config = {"callable_path": "myapp.validators:check_response"}
                # Equivalent to: "myapp.validators.check_response"

        Thread Safety:
            Custom callables should be stateless and thread-safe. Avoid using
            module-level mutable state in validator functions. If state is
            required, use thread-local storage or pass configuration via kwargs.

        Error Handling:
            - **Import errors**: Returns failure with import error message
            - **Missing function**: Returns failure with AttributeError message
            - **Exception in callable**: Captured and returned as failure
            - **Invalid return type**: Returns failure with type error message

        Args:
            config: Configuration dictionary. Must contain ``callable_path`` with
                the fully qualified Python path to the validation function.
                Additional keys are passed as keyword arguments to the callable.
            output: The output dictionary to validate. Passed as the first
                positional argument to the custom callable.

        Returns:
            Tuple of (passed, message, actual_value, expected_value):

            - ``passed``: True if validation succeeded, False otherwise
            - ``message``: Description of the result (from callable or generated)
            - ``actual_value``: Always None for custom callables
            - ``expected_value``: The callable_path that was invoked

        Raises:
            This method does not raise exceptions. All errors are captured and
            returned as failed validation results with descriptive messages.
        """
        callable_path = config.get("callable_path")
        if not isinstance(callable_path, str):
            return (False, "Invalid config: callable_path must be a string", None, None)

        # Check against allowed import paths if configured (using strict boundary matching)
        if not self._is_import_path_allowed(callable_path):
            return (
                False,
                f"Callable path not in allowed list: {callable_path}",
                None,
                callable_path,
            )

        # Parse callable_path (module.path:function_name or module.path.function_name)
        if ":" in callable_path:
            module_path, func_name = callable_path.rsplit(":", 1)
        elif "." in callable_path:
            module_path, func_name = callable_path.rsplit(".", 1)
        else:
            return (
                False,
                f"Invalid callable_path format: {callable_path}",
                None,
                callable_path,
            )

        # Security: Defense-in-depth - also validate the parsed module_path
        # This catches edge cases where callable_path validation might pass
        # but the actual module being imported is different
        if not self._is_module_path_allowed(module_path):
            logger.warning(
                "Module path not in allowed list (security): %r",
                module_path[:100] if len(module_path) > 100 else module_path,
            )
            return (
                False,
                f"Module path not in allowed list: {module_path}",
                None,
                callable_path,
            )

        # Dynamic import
        try:
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
        except (
            AttributeError,
            ImportError,
        ) as e:  # fallback-ok: import errors fail validation
            return (
                False,
                f"Failed to import callable: {e}",
                None,
                callable_path,
            )

        # Security: Verify the resolved attribute is actually callable
        if not callable(func):
            logger.warning(
                "Resolved attribute is not callable (security): %r -> %s",
                callable_path,
                type(func).__name__,
            )
            return (
                False,
                f"Resolved path is not callable: {callable_path} (got {type(func).__name__})",
                None,
                callable_path,
            )

        # Extract kwargs from config (excluding callable_path)
        kwargs = {k: v for k, v in config.items() if k != "callable_path"}

        # Call the custom function
        try:
            result = func(output, **kwargs)
        except Exception as e:  # fallback-ok: custom callable boundary - must capture all errors to return result
            return (
                False,
                f"Custom callable raised exception: {type(e).__name__}: {e}",
                None,
                callable_path,
            )

        # Handle result - can be bool or tuple[bool, str]
        if isinstance(result, bool):
            passed = result
            message = (
                "Custom validation passed" if passed else "Custom validation failed"
            )
        elif isinstance(result, tuple) and len(result) == 2:
            passed, message = result
            if not isinstance(passed, bool) or not isinstance(message, str):
                return (
                    False,
                    f"Invalid custom callable return: expected (bool, str), got {type(result)}",
                    result,
                    callable_path,
                )
        else:
            return (
                False,
                f"Invalid custom callable return type: expected bool or (bool, str), got {type(result)}",
                result,
                callable_path,
            )

        return (passed, message, None, callable_path)

    def _resolve_field_path(
        self,
        data: dict[str, object],
        path: str,
    ) -> tuple[bool, Any]:
        """Resolve dot-notation path with array index support.

        Security: Enforces MAX_FIELD_PATH_DEPTH limit to prevent DoS attacks
        via deeply nested paths.

        Examples:
            "user.name" -> data["user"]["name"]
            "items.0.id" -> data["items"][0]["id"]

        Args:
            data: The dictionary to traverse.
            path: Dot-notation path with optional array indices.

        Returns:
            Tuple of (found: bool, value: Any).
            If not found or depth exceeded, value is None.
        """
        parts = path.split(".")
        if len(parts) > self.MAX_FIELD_PATH_DEPTH:
            logger.warning(
                "Field path depth limit exceeded: %d > %d (path: %s)",
                len(parts),
                self.MAX_FIELD_PATH_DEPTH,
                path[:100] + "..." if len(path) > 100 else path,
            )
            return (False, None)
        current: Any = data

        for part in parts:
            if current is None:
                return (False, None)

            # Try as array index first
            if isinstance(current, (list, tuple)):
                try:
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return (False, None)
                except (
                    ValueError
                ):  # fallback-ok: non-integer path segment, field not found
                    return (False, None)
            elif isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return (False, None)
            else:
                # Cannot traverse non-container type
                return (False, None)

        return (True, current)


__all__ = ["ServiceInvariantEvaluator"]
