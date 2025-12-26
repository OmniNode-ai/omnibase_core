"""Valid module with correct __all__ exports."""

__all__ = ["MyClass", "my_function", "MY_CONSTANT", "imported_name"]

# Import
from os import path as imported_name


class MyClass:
    """A sample class."""


def my_function() -> None:
    """A sample function."""


MY_CONSTANT = 42
