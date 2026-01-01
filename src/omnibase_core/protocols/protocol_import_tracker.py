"""
Protocol for import tracking objects.

Defines the interface for import trackers passed to UtilityReferenceResolver.
"""

from typing import Protocol, runtime_checkable

__all__ = ["ProtocolImportTracker"]


@runtime_checkable
class ProtocolImportTracker(Protocol):
    """
    Protocol for import tracking objects.

    Defines the interface for import trackers passed to UtilityReferenceResolver.
    """

    def add_subcontract_model(
        self,
        subcontract_path: str,
        model_name: str,
        package_name: str,
        import_path: str,
    ) -> None:
        """
        Track a subcontract model for import generation.

        Args:
            subcontract_path: Path to the subcontract file
            model_name: Resolved model name
            package_name: Package name for the model
            import_path: Python import path
        """
        ...
