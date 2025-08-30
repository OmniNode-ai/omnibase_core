"""ModelEventPriority: Event processing priority for queue management"""

from enum import Enum


class ModelEventPriority(str, Enum):
    """Event processing priority for queue management"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
