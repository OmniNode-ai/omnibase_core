from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHandlerSource(StrValueHelper, str, Enum):
    """
    Canonical source types for file type handlers in ONEX/OmniBase.
    Used for registry, plugin, and protocol compliance.
    """

    CORE = "core"
    RUNTIME = "runtime"
    NODE_LOCAL = "node-local"
    PLUGIN = "plugin"
    TEST = "test"


__all__ = ["EnumHandlerSource"]
