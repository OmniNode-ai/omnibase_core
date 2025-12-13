"""Module with nested classes - nested ones should NOT be detected as module-level."""

__all__ = ["OuterClass"]


class OuterClass:
    """This is a module-level class."""

    class InnerClass:
        """This is nested - should NOT be detected as module-level."""

    class AnotherInner:
        """Another nested class."""


# The InnerClass and AnotherInner should NOT be in defined names
