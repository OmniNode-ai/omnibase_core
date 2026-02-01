"""
[Any]Type Enumerations

ONEX-compatible enums for task types to replace string literals.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTaskTypes(StrValueHelper, str, Enum):
    """[Any]type enumeration."""

    DOCUMENT_ANALYSIS = "document_analysis"
    CUSTOM_FUNCTION = "custom_function"
    BATCH_PROCESSING = "batch_processing"
    MAINTENANCE = "maintenance"
    HEALTH_CHECK = "health_check"
    CLEANUP = "cleanup"
    REPORT_GENERATION = "report_generation"
    DATA_VALIDATION = "data_validation"
    SYNC_OPERATION = "sync_operation"
    NOTIFICATION = "notification"
    # LLM-related task types
    LLM_GENERATION = "llm_generation"
    LLM_ANALYSIS = "llm_analysis"
    LLM_BATCH_PROCESSING = "llm_batch_processing"
    LLM_EMBEDDINGS = "llm_embeddings"
    LLM_CHAT_COMPLETION = "llm_chat_completion"
    # Autonomous task types
    AUTONOMOUS_TOOL_BOOTSTRAP = "autonomous_tool_bootstrap"
    UNKNOWN = "unknown"


__all__ = ["EnumTaskTypes"]
