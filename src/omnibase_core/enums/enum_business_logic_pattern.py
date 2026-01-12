from enum import Enum, unique


@unique
class EnumBusinessLogicPattern(str, Enum):
    """Business logic pattern classifications."""

    STATELESS = "stateless"
    STATEFUL = "stateful"
    COORDINATION = "coordination"
    AGGREGATION = "aggregation"
