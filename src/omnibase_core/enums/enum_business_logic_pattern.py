from enum import Enum


class EnumBusinessLogicPattern(str, Enum):
    """Business logic pattern classifications."""

    STATELESS = "stateless"
    STATEFUL = "stateful"
    COORDINATION = "coordination"
    AGGREGATION = "aggregation"
