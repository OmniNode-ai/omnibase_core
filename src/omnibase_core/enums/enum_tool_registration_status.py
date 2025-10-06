from enum import Enum


class EnumToolRegistrationStatus(str, Enum):
    """Status of tool registration."""

    REGISTERED = "registered"
    PENDING = "pending"
    FAILED = "failed"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
