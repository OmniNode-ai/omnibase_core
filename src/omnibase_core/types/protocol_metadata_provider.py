from typing import Dict

"""
ProtocolMetadataProvider Protocol

Protocol for objects that provide metadata information.

This protocol defines the interface for objects that can provide
metadata through a metadata property, providing a consistent pattern
for metadata management across the system.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- omnibase_core.types.* (no dependencies on this module)
- Standard library modules
"""

from typing import Any, Dict, Protocol


class ProtocolMetadataProvider(Protocol):
    """
    Protocol for objects that provide metadata information.

    This protocol provides a consistent interface for metadata access,
    requiring objects to have a metadata property that returns a
    dictionary of metadata information.

    Key Features:
    - Dictionary-based metadata
    - Simple property interface
    - Consistent metadata pattern
    - Designed for ONEX architecture compliance
    """

    @property
    def metadata(self) -> dict[str, Any]:
        """
        Get the metadata for this object.

        Returns:
            dict[str, Any]: Dictionary containing metadata information
        """
        ...
