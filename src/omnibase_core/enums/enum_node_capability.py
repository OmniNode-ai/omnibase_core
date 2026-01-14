"""
Enum for node capabilities.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeCapability(StrValueHelper, str, Enum):
    """Standard node capabilities that can be declared via introspection."""

    SUPPORTS_DRY_RUN = "supports_dry_run"
    SUPPORTS_BATCH_PROCESSING = "supports_batch_processing"
    SUPPORTS_CUSTOM_HANDLERS = "supports_custom_handlers"
    TELEMETRY_ENABLED = "telemetry_enabled"
    SUPPORTS_CORRELATION_ID = "supports_correlation_id"
    SUPPORTS_EVENT_BUS = "supports_event_bus"
    SUPPORTS_SCHEMA_VALIDATION = "supports_schema_validation"
    SUPPORTS_ERROR_RECOVERY = "supports_error_recovery"
    SUPPORTS_EVENT_DISCOVERY = "supports_event_discovery"


__all__ = ["EnumNodeCapability"]
