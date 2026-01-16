"""Metrics policy violation action enum for observability cardinality enforcement."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetricsPolicyViolationAction(StrValueHelper, str, Enum):
    """Action to take when a metrics policy violation is detected.

    Used by ModelMetricsPolicy to control behavior when forbidden labels
    are used or label values exceed length limits.

    Actions:
        RAISE: Raise an error immediately. Use in strict/test environments.
        WARN_AND_DROP: Log warning and drop the metric. Default behavior.
        DROP_SILENT: Drop the metric without logging. Avoid in production.
        WARN_AND_STRIP: Log warning and strip/truncate offending data.
            Acceptable for max_label_value_length violations, not for forbidden keys.
    """

    RAISE = "raise"
    WARN_AND_DROP = "warn_and_drop"
    DROP_SILENT = "drop_silent"
    WARN_AND_STRIP = "warn_and_strip"


__all__ = ["EnumMetricsPolicyViolationAction"]
