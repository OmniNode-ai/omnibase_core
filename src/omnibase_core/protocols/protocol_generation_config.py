"""
Protocol for generation configuration objects.

Defines the interface for config objects passed to UtilityReferenceResolver.
"""

from typing import Protocol, runtime_checkable

__all__ = ["ProtocolGenerationConfig"]


@runtime_checkable
class ProtocolGenerationConfig(Protocol):
    """
    Protocol for generation configuration objects.

    Defines the interface for config objects passed to UtilityReferenceResolver.
    """

    @property
    def subcontract_import_map(self) -> dict[str, dict[str, str]] | None:
        """Map of subcontract paths to import configuration."""
        ...

    @property
    def use_imports_for_subcontracts(self) -> bool:
        """Whether to use imports for subcontract references."""
        ...
