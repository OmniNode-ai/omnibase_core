from enum import Enum


class EnumServiceTypeCategory(str, Enum):
    """Core service type categories."""

    SERVICE_DISCOVERY = "service_discovery"
    EVENT_BUS = "event_bus"
    CACHE = "cache"
    DATABASE = "database"
    REST_API = "rest_api"
    CUSTOM = "custom"
