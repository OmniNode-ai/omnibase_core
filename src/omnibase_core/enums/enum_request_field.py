"""Request field names in Claude API."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRequestField(StrValueHelper, str, Enum):
    """Request field names in Claude API."""

    MODEL = "model"
    SYSTEM = "system"
    MESSAGES = "messages"
    TOOLS = "tools"
    MAX_TOKENS = "max_tokens"
    TEMPERATURE = "temperature"
    CONTENT = "content"
    ROLE = "role"
    TYPE = "type"
    TEXT = "text"


__all__ = ["EnumRequestField"]
