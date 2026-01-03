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

    def __init__(self, allowed_import_paths: list[str] | None = None) -> None:
        """Initialize the invariant evaluator.

        Args:
            allowed_import_paths: Optional allow-list for custom callable imports.
                If None, all paths are allowed (trusted code model).
                If provided, only callable_path values starting with one of
                these prefixes are permitted for CUSTOM invariants.
        """
        self.allowed_import_paths = allowed_import_paths

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

        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        critical_failures = sum(
            1
            for r in results
            if not r.passed and r.severity == EnumInvariantSeverity.CRITICAL
        )
        warning_failures = sum(
            1
            for r in results
            if not r.passed and r.severity == EnumInvariantSeverity.WARNING
        )
        info_failures = sum(
            1
            for r in results
            if not r.passed and r.severity == EnumInvariantSeverity.INFO
        )

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
            if re.search(pattern, actual_str):
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
        except (TypeError, ValueError):
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
            except (TypeError, ValueError):
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
            except (TypeError, ValueError):
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
        except (TypeError, ValueError):
            return (False, f"Invalid max_ms value: {max_ms!r}", None, None)

        # Look for latency_ms or duration_ms
        actual_ms: float | None = None
        for field_name in ["latency_ms", "duration_ms"]:
            found, value = self._resolve_field_path(output, field_name)
            if found:
                try:
                    actual_ms = float(value)  # type: ignore[arg-type]
                    break
                except (TypeError, ValueError):
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
        except (TypeError, ValueError):
            return (False, f"Invalid max_cost value: {max_cost!r}", None, None)

        # Look for cost directly
        found, cost_value = self._resolve_field_path(output, "cost")
        if found:
            try:
                actual_cost = float(cost_value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
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
                except (TypeError, ValueError):
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

        Args:
            config: Must contain 'callable_path' with module.path:function format.
            output: The output to pass to the custom callable.

        Returns:
            Tuple of (passed, message, actual_value, expected_value).
        """
        callable_path = config.get("callable_path")
        if not isinstance(callable_path, str):
            return (False, "Invalid config: callable_path must be a string", None, None)

        # Check against allowed import paths if configured
        if self.allowed_import_paths is not None:
            allowed = any(
                callable_path.startswith(prefix) for prefix in self.allowed_import_paths
            )
            if not allowed:
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
        except (ImportError, AttributeError) as e:
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
        except (
            Exception
        ) as e:  # fallback-ok: custom callable errors must be captured as failed result
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

        Examples:
            "user.name" -> data["user"]["name"]
            "items.0.id" -> data["items"][0]["id"]

        Args:
            data: The dictionary to traverse.
            path: Dot-notation path with optional array indices.

        Returns:
            Tuple of (found: bool, value: Any).
            If not found, value is None.
        """
        parts = path.split(".")
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
                except ValueError:
                    # Not a valid index
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
