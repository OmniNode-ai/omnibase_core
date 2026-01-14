from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumServiceStatus(StrValueHelper, str, Enum):
    """Service status values for Container Adapter coordination."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PROVISIONING = "provisioning"
    DECOMMISSIONING = "decommissioning"
    HEALTH_CHECK_FAILING = "health_check_failing"
