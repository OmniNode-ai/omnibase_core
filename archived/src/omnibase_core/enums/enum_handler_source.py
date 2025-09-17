from enum import Enum


class HandlerSourceEnum(str, Enum):
    """
    Canonical source types for file type handlers in ONEX/OmniBase.
    Used for registry, plugin, and protocol compliance.
    """

    CORE = "core"
    RUNTIME = "runtime"
    NODE_LOCAL = "node-local"
    PLUGIN = "plugin"
    TEST = "test"
