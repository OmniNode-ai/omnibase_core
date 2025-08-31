"""
Enum for alert types.

Types of alerts that can be triggered.
"""

from enum import Enum


class EnumAlertType(str, Enum):
    """Types of alerts that can be triggered."""

    SYSTEM_DOWN = "system_down"
    QUOTA_EXHAUSTION = "quota_exhaustion"
    CASCADE_FAILURE = "cascade_failure"
    DATA_LOSS_RISK = "data_loss_risk"
    HIGH_ERROR_RATE = "high_error_rate"
    QUOTA_DEPLETION = "quota_depletion"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    COST_OVERRUN = "cost_overrun"
    AGENT_FAILURE = "agent_failure"
    CAPACITY_LIMIT = "capacity_limit"
    ANOMALY_DETECTED = "anomaly_detected"
