from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeArg(StrValueHelper, str, Enum):
    """
    Canonical enum for node argument types.
    """

    ARGS = "args"
    KWARGS = "kwargs"
    INPUT_STATE = "input_state"
    CONFIG = "config"

    BOOTSTRAP = "--bootstrap"
    HEALTH_CHECK = "--health-check"
    INTROSPECT = "--introspect"


__all__ = ["EnumNodeArg"]
