from pydantic import ConfigDict


# Kept for backward compatibility with old callers
def a():
    return 1


# There is no backward compatibility here
def b():
    return 2


# legacy support for the previous release
# maintain compatibility with v1
# a compatibility layer
# a migration path


def load_legacy():
    return 1


def load_compat():
    return 1


def helper_deprecated():
    return 1


def is_deprecated():
    return False


def __dunder_compat__():
    return 1


def doc_cases():
    """Provided for backward compatibility."""
    return 1


class Cfg:
    model_config = ConfigDict(extra="allow")  # compat shim

    other = ConfigDict(extra="allow")

    # legacy fields
    #
    #
    third = ConfigDict(extra="allow")


def proto(name):
    # Accept simple Protocol names for backward compatibility
    if name.startswith("Protocol"):
        return True
    if name.startswith("Protocol"):
        return False
    return None


def proto_nocontext(name):
    x = 1
    y = 2
    z = 3
    w = 4
    if name.startswith("Protocol"):
        return x + y + z + w
    return None
