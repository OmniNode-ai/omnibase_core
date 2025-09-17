from enum import Enum


class EnumNodeArg(str, Enum):
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
