from enum import Enum, unique


@unique
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
