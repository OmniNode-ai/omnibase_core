"""Business logic pattern classifications for node categorization."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumBusinessLogicPattern(StrValueHelper, str, Enum):
    """Business logic pattern classifications."""

    STATELESS = "stateless"
    STATEFUL = "stateful"
    COORDINATION = "coordination"
    AGGREGATION = "aggregation"


__all__ = ["EnumBusinessLogicPattern"]
