from enum import Enum


class EnumServiceStatus(str, Enum):
    """Service status values for Container Adapter coordination."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PROVISIONING = "provisioning"
    DECOMMISSIONING = "decommissioning"
    HEALTH_CHECK_FAILING = "health_check_failing"
