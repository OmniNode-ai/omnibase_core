"""Request field names in Claude API."""

from enum import Enum


class EnumRequestField(str, Enum):
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
