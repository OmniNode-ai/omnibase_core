"""ModelDeliveryGuarantee: Required delivery semantics"""

from enum import Enum


class ModelDeliveryGuarantee(str, Enum):
    """Required delivery semantics"""

    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"
