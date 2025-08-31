"""Kafka topics for OmniMemory integration."""

from enum import Enum


class EnumKafkaTopic(str, Enum):
    """Kafka topics for OmniMemory integration."""

    USER_MESSAGE = "omnimemory.user.message"
    CONTEXT_ANALYSIS = "omnimemory.context.analysis"
    SECURITY_VALIDATION = "omnimemory.security.validation"
