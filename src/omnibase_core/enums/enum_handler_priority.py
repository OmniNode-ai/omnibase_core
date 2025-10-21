from enum import Enum


class EnumHandlerPriority(int, Enum):
    """
    Canonical priority levels for file type handlers in ONEX/OmniBase.
    Used for registry, plugin, and protocol compliance.
    """

    CORE = 100
    RUNTIME = 50
    NODE_LOCAL = 10
    PLUGIN = 0
    CUSTOM = 25
    CONTRACT = 75
    LOW = PLUGIN  # Explicit alias for lowest priority
    HIGH = CORE  # Explicit alias for highest priority
    TEST = 5
