from enum import Enum


class HandlerTypeEnum(str, Enum):
    """
    Canonical handler types for ONEX/OmniBase file type handlers.
    Used for registry, plugin, and protocol compliance.
    """

    EXTENSION = "extension"
    SPECIAL = "special"
    NAMED = "named"
