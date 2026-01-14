"""Tool category enumeration."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumToolCategory(StrValueHelper, str, Enum):
    """
    Tool category classification.

    Defines the functional category or domain of tools in the system.
    """

    CUSTOM = "custom"
    CORE = "core"
    SECURITY = "security"
    INTEGRATION = "integration"
    BUSINESS_LOGIC = "business_logic"
    VALIDATION = "validation"
    MONITORING = "monitoring"
    PERFORMANCE = "performance"
    DATA_PROCESSING = "data_processing"
    EXTERNAL_SERVICE = "external_service"
    UTILITY = "utility"
    REGISTRY = "registry"
    TRANSFORMATION = "transformation"
    OUTPUT = "output"


__all__ = ["EnumToolCategory"]
