"""Module with public names not in __all__ (for --warn-missing testing)."""

__all__ = ["ExportedClass"]


class ExportedClass:
    """This class is in __all__."""


class NotExportedClass:
    """This public class is NOT in __all__ - should trigger warning."""


def not_exported_function() -> None:
    """This public function is NOT in __all__ - should trigger warning."""


NOT_EXPORTED_CONSTANT = "value"


def _private_function() -> None:
    """Private functions should NOT trigger warnings."""


_PRIVATE_CONSTANT = "private"
