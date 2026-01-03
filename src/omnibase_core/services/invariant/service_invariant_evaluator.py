"""Service for evaluating invariants against execution outputs.

This module provides the ServiceInvariantEvaluator class for validating
that outputs conform to defined invariants (validation rules).

Thread Safety:
    ServiceInvariantEvaluator is NOT thread-safe. Create separate instances
    per thread or use thread-local storage.

Example:
    >>> from omnibase_core.services.invariant.service_invariant_evaluator import (
    ...     ServiceInvariantEvaluator,
    ... )
    >>> from omnibase_core.models.invariant import ModelInvariant, ModelInvariantSet
    >>> from omnibase_core.enums import EnumInvariantType, EnumInvariantSeverity
    >>>
    >>> evaluator = ServiceInvariantEvaluator()
    >>> invariant = ModelInvariant(
    ...     name="latency_check",
    ...     type=EnumInvariantType.LATENCY,
    ...     severity=EnumInvariantSeverity.CRITICAL,
    ...     config={"max_ms": 500},
    ... )
    >>> result = evaluator.evaluate(invariant, {"latency_ms": 250})
    >>> print(result.passed)  # True
"""

import importlib
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any

import jsonschema

from omnibase_core.enums import EnumInvariantSeverity, EnumInvariantType
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

    Thread Safety:
        This class is NOT thread-safe. Create separate instances per thread
        or use thread-local storage.

    Example:
        >>> evaluator = ServiceInvariantEvaluator()
        >>> result = evaluator.evaluate(invariant, output)
        >>> if not result.passed:
        ...     print(f"Failed: {result.message}")
    """

    SLOW_EVALUATION_THRESHOLD_MS: float = 25.0
    MAX_FIELD_PATH_DEPTH: int = 20
    MAX_REGEX_PATTERN_LENGTH: int = 1000
    REGEX_TIMEOUT_SECONDS: float = 1.0

    # Patterns that indicate potential ReDoS vulnerability (nested quantifiers)
    # These detect nested quantifiers and overlapping alternations that can cause
    # catastrophic backtracking
    _REDOS_DANGEROUS_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"\([^)]*[+*]\)[+*]"),  # Nested quantifiers like (a+)+ or (a*)*
        re.compile(r"\([^)]*\{[^}]+\}\)[+*]"),  # Nested {n,m} with + or *
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

    def __init__(self, allowed_import_paths: list[str] | None = None) -> None:
        """Initialize the invariant evaluator.

        Args:
            allowed_import_paths: Optional allow-list for custom callable imports.
                If None, all paths are allowed (trusted code model).
                If provided, only callable_path values starting with one of
                these prefixes are permitted for CUSTOM invariants.
        """
        self.allowed_import_paths = allowed_import_paths

    def _is_import_path_allowed(self, callable_path: str) -> bool:
        """Check if callable_path is allowed by the configured allow-list.

        Security Measures:
            1. Validates callable_path format (only valid Python module paths)
            2. Rejects empty or malformed prefixes in allow-list
            3. Uses strict boundary matching (dot or colon separator)
            4. Logs warnings for security-relevant rejections

        Uses strict boundary matching to prevent bypass attacks.
        For example, if "builtins" is allowed, "builtins_evil" will NOT match.

        The check handles both separator formats:
        - Dot notation: "module.path.function"
        - Colon notation: "module.path:function"

        Args:
            callable_path: The full callable path to check.

        Returns:
            True if the path is allowed, False otherwise.
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

    def _safe_regex_search(
        self, pattern: str, text: str
    ) -> tuple[bool, re.Match[str] | None, str]:
        """Perform a regex search with safety checks and timeout protection.

        Args:
            pattern: The regex pattern to search for.
            text: The text to search within.

        Returns:
            Tuple of (success, match, error_message).
            If success is True, match contains the result (or None if no match).
            If success is False, error_message contains the error description.
        """
        # First validate the pattern is safe
        is_safe, error_msg = self._is_regex_safe(pattern)
        if not is_safe:
            return (False, None, error_msg)

        # Perform the search with time tracking
        start_time = time.perf_counter()
        try:
            match = re.search(pattern, text)
            elapsed = time.perf_counter() - start_time

            # Log warning if regex took too long (potential slow pattern)
            if elapsed > self.REGEX_TIMEOUT_SECONDS:
                logger.warning(
                    "Slow regex pattern detected: took %.2f seconds (pattern: %s)",
                    elapsed,
                    pattern[:50] + "..." if len(pattern) > 50 else pattern,
                )

            return (True, match, "")
        except re.error as e:
            return (False, None, f"Regex error: {e}")

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
            fail_fast: If True, stop on first CRITICAL failure.

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
                and result.severity == EnumInvariantSeverity.CRITICAL
            ):
                break

        total_duration_ms = (time.perf_counter() - start_time) * 1000

        # Count all statistics in a single pass over results
        passed_count = 0
        critical_failures = 0
        warning_failures = 0
        info_failures = 0

        for r in results:
            if r.passed:
                passed_count += 1
            elif r.severity == EnumInvariantSeverity.CRITICAL:
                critical_failures += 1
            elif r.severity == EnumInvariantSeverity.WARNING:
                warning_failures += 1
            elif r.severity == EnumInvariantSeverity.INFO:
                info_failures += 1

        failed_count = len(results) - passed_count

        overall_passed = critical_failures == 0

        return ModelEvaluationSummary(
            results=results,
            passed_count=passed_count,
            failed_count=failed_count,
            critical_failures=critical_failures,
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
            jsonschema.validate(output, json_schema)
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
                logger.warning("Skipping non-string field path: %r", field_path)
                continue
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
            max_ms_num = float(max_ms)  # type: ignore[arg-type]
        except (TypeError, ValueError):  # fallback-ok: invalid config fails validation
            return (False, f"Invalid max_ms value: {max_ms!r}", None, None)

        # Look for latency_ms or duration_ms
        actual_ms: float | None = None
        for field_name in ["latency_ms", "duration_ms"]:
            found, value = self._resolve_field_path(output, field_name)
            if found:
                try:
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
            max_cost_num = float(max_cost)  # type: ignore[arg-type]
        except (TypeError, ValueError):  # fallback-ok: invalid config fails validation
            return (False, f"Invalid max_cost value: {max_cost!r}", None, None)

        # Look for cost directly
        found, cost_value = self._resolve_field_path(output, "cost")
        if found:
            try:
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
                    token_count = float(tokens)  # type: ignore[arg-type]
                    # Default cost rate per token (can be customized via config)
                    cost_per_token = config.get("cost_per_token", 0.0001)
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

        Custom Callable Patterns:
            Callables must accept (output: dict, **kwargs) and return either:

            1. Boolean only:
                def my_validator(output: dict, **kwargs) -> bool:
                    return "required_field" in output

            2. Tuple with message:
                def my_validator(output: dict, **kwargs) -> tuple[bool, str]:
                    if "required_field" not in output:
                        return (False, "Missing required_field")
                    return (True, "Validation passed")

        Configuration:
            - callable_path: Module path in "module.path:function" or
              "module.path.function" format
            - Additional config keys are passed as kwargs to the callable

        Security:
            When allowed_import_paths is configured, only callables from
            authorized module prefixes are permitted. The check uses strict
            boundary matching (checking for '.' or ':' after prefix) to prevent
            bypass attacks like "builtins_evil" matching "builtins".

            Example:
                evaluator = ServiceInvariantEvaluator(
                    allowed_import_paths=["myapp.validators", "myapp.checks"]
                )
                # Only callables starting with these prefixes are allowed

        Examples:
            Config for tuple-returning validator::

                {"callable_path": "myapp.validators:check_response", "strict": True}

            Config for bool-returning validator::

                {"callable_path": "myapp.validators.is_valid"}

            Custom validator with kwargs::

                def check_min_length(output: dict, min_length: int = 10, **kwargs) -> tuple[bool, str]:
                    text = output.get("text", "")
                    if len(text) >= min_length:
                        return (True, f"Text length {len(text)} meets minimum {min_length}")
                    return (False, f"Text length {len(text)} below minimum {min_length}")

                # Config: {"callable_path": "myapp.validators:check_min_length", "min_length": 50}

        Args:
            config: Must contain 'callable_path' with module.path:function format.
                Additional keys are passed as kwargs to the callable.
            output: The output dictionary to pass to the custom callable.

        Returns:
            Tuple of (passed, message, actual_value, expected_value).
            On import/attribute error: (False, error_message, None, callable_path)
            On callable exception: (False, exception_message, None, callable_path)
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

        # Extract kwargs from config (excluding callable_path)
        kwargs = {k: v for k, v in config.items() if k != "callable_path"}

        # Call the custom function
        try:
            result = func(output, **kwargs)
        except Exception as e:  # fallback-ok: custom callable errors must be captured
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
