"""Threat types for intelligent context routing safety mechanisms."""

from enum import Enum


class EnumThreatType(str, Enum):
    """Types of threats the safety mechanisms protect against."""

    INFINITE_LOOP = "infinite_loop"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    MALICIOUS_INJECTION = "malicious_injection"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    DATA_CORRUPTION = "data_corruption"
    CASCADE_FAILURE = "cascade_failure"
