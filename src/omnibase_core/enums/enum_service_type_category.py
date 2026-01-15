from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumServiceTypeCategory(StrValueHelper, str, Enum):
    """Core service type categories."""

    SERVICE_DISCOVERY = "service_discovery"
    EVENT_BUS = "event_bus"
    CACHE = "cache"
    DATABASE = "database"
    REST_API = "rest_api"
    CUSTOM = "custom"


__all__ = ["EnumServiceTypeCategory"]
