"""Metrics cardinality policy model for observability."""

from __future__ import annotations

import logging
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_label_violation_type import EnumLabelViolationType
from omnibase_core.enums.enum_metrics_policy_violation_action import (
    EnumMetricsPolicyViolationAction,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.observability.model_label_validation_result import (
    ModelLabelValidationResult,
)
from omnibase_core.models.observability.model_label_violation import ModelLabelViolation

_logger = logging.getLogger(__name__)


class ModelMetricsPolicy(BaseModel):
    """Cardinality policy for metrics labels.

    Enforces rules to prevent high-cardinality label explosions that can
    overwhelm metrics backends. Supports both allowlist (strict) and
    denylist (permissive) modes.

    Policy Semantics:
        - If `allowed_label_keys` is set (not None): strict mode.
          Only keys in allowed_label_keys are permitted, minus anything in forbidden.
        - If `allowed_label_keys` is None: permissive mode.
          Any key not in forbidden_label_keys is allowed.
        - `forbidden_label_keys` ALWAYS wins over allowed.
          If a key is in both, it is forbidden.

    Default Forbidden Labels:
        High-cardinality identifiers that should never be metric labels:
        - envelope_id: Unique per-message identifier
        - correlation_id: Request correlation identifier
        - node_id: Node instance identifier
        - runtime_id: Runtime instance identifier

    Attributes:
        allowed_label_keys: Whitelist of permitted label keys (strict mode if set).
        forbidden_label_keys: Denylist of forbidden label keys (always enforced).
        max_label_value_length: Maximum allowed length for label values.
        on_violation: Action to take when policy is violated.

    Methods:
        validate_labels: Pure validation returning result with violations.
        enforce_labels: Validation + enforcement based on on_violation action.

    Example:
        >>> policy = ModelMetricsPolicy(
        ...     on_violation=EnumMetricsPolicyViolationAction.RAISE
        ... )
        >>> # Using validate_labels (pure validation, no side effects)
        >>> result = policy.validate_labels({"envelope_id": "abc"})
        >>> result.is_valid
        False
        >>> # Using enforce_labels (takes action based on on_violation)
        >>> policy.enforce_labels({"envelope_id": "abc"})  # raises ValueError
    """

    DEFAULT_FORBIDDEN: ClassVar[frozenset[str]] = frozenset(
        {
            "envelope_id",
            "correlation_id",
            "node_id",
            "runtime_id",
        }
    )

    allowed_label_keys: frozenset[str] | None = Field(
        default=None,
        description="Whitelist of allowed label keys (None = permissive mode)",
    )
    forbidden_label_keys: frozenset[str] = Field(
        default_factory=lambda: ModelMetricsPolicy.DEFAULT_FORBIDDEN,
        description="Denylist of forbidden label keys (always enforced)",
    )
    max_label_value_length: int = Field(
        default=128,
        ge=1,
        le=1024,
        description="Maximum allowed length for label values",
    )
    on_violation: EnumMetricsPolicyViolationAction = Field(
        default=EnumMetricsPolicyViolationAction.WARN_AND_DROP,
        description="Action to take when policy is violated",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    def validate_labels(self, labels: dict[str, str]) -> ModelLabelValidationResult:
        """Validate labels against this policy.

        Checks each label key and value against policy rules:
        1. Key must not be in forbidden_label_keys
        2. If allowed_label_keys is set, key must be in allowed_label_keys
        3. Value must not exceed max_label_value_length

        Args:
            labels: Dictionary of label key-value pairs to validate.

        Returns:
            ModelLabelValidationResult with validation status, any violations,
            and optionally sanitized labels.
        """
        violations: list[ModelLabelViolation] = []
        sanitized: dict[str, str] = {}

        for key, value in labels.items():
            key_valid = True

            # Check forbidden keys (always wins)
            if key in self.forbidden_label_keys:
                violations.append(
                    ModelLabelViolation(
                        violation_type=EnumLabelViolationType.FORBIDDEN_KEY,
                        key=key,
                        value=value,
                        message=f"Label key '{key}' is forbidden (high-cardinality identifier)",
                    )
                )
                key_valid = False

            # Check allowed keys (strict mode)
            elif (
                self.allowed_label_keys is not None
                and key not in self.allowed_label_keys
            ):
                violations.append(
                    ModelLabelViolation(
                        violation_type=EnumLabelViolationType.KEY_NOT_ALLOWED,
                        key=key,
                        value=value,
                        message=f"Label key '{key}' is not in the allowed list",
                    )
                )
                key_valid = False

            # Check value length
            if len(value) > self.max_label_value_length:
                violations.append(
                    ModelLabelViolation(
                        violation_type=EnumLabelViolationType.VALUE_TOO_LONG,
                        key=key,
                        value=value,
                        message=(
                            f"Label value for '{key}' exceeds max length "
                            f"({len(value)} > {self.max_label_value_length})"
                        ),
                    )
                )
                # For value length violations, we can still include truncated value
                if key_valid:
                    sanitized[key] = value[: self.max_label_value_length]
            elif key_valid:
                sanitized[key] = value

        is_valid = len(violations) == 0

        return ModelLabelValidationResult(
            is_valid=is_valid,
            violations=violations,
            sanitized_labels=sanitized if sanitized else None,
        )

    def enforce_labels(self, labels: dict[str, str]) -> dict[str, str] | None:
        """Validate labels and enforce policy based on on_violation action.

        This method combines validation with enforcement. It calls validate_labels()
        internally and then takes action based on the on_violation setting:

        - RAISE: Raises ValueError if any violations found.
        - WARN_AND_DROP: Logs warning and returns None (drop the metric).
        - DROP_SILENT: Returns None without logging (drop silently).
        - WARN_AND_STRIP: Logs warning and returns sanitized_labels.

        Args:
            labels: Dictionary of label key-value pairs to validate and enforce.

        Returns:
            - Original labels if no violations found.
            - Sanitized labels for WARN_AND_STRIP action.
            - None for DROP actions (WARN_AND_DROP, DROP_SILENT).

        Raises:
            ValueError: If on_violation is RAISE and violations are found.
        """
        result = self.validate_labels(labels)

        if result.is_valid:
            return labels

        # Format violation messages for logging/errors
        violation_messages = [v.message for v in result.violations]
        violation_summary = "; ".join(violation_messages)

        if self.on_violation == EnumMetricsPolicyViolationAction.RAISE:
            raise ModelOnexError(
                message=f"Metrics policy violation(s): {violation_summary}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if self.on_violation == EnumMetricsPolicyViolationAction.WARN_AND_DROP:
            _logger.warning(
                "Dropping metric due to policy violation(s): %s",
                violation_summary,
            )
            return None

        if self.on_violation == EnumMetricsPolicyViolationAction.DROP_SILENT:
            return None

        # WARN_AND_STRIP: log warning and return sanitized labels
        _logger.warning(
            "Stripping invalid labels due to policy violation(s): %s",
            violation_summary,
        )
        return result.sanitized_labels


__all__ = ["ModelMetricsPolicy"]
