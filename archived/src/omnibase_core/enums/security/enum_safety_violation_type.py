"""Safety violation types for intelligent context routing protection mechanisms."""

from enum import Enum


class EnumSafetyViolationType(str, Enum):
    """Types of safety violations that trigger protective actions."""

    PRODUCTION_IMPACT = "production_impact"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    ERROR_RATE_SPIKE = "error_rate_spike"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATA_CORRUPTION = "data_corruption"
    SECURITY_BREACH = "security_breach"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    STATISTICAL_ANOMALY = "statistical_anomaly"
