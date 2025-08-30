"""
Protocol for Reference Resolver functionality.

Defines the interface for resolving $ref references in JSON Schema
to Python type names for code generation.
"""

from typing import Dict, Optional, Protocol


class ProtocolReferenceResolver(Protocol):
    """Protocol for reference resolution functionality.

    This protocol defines the interface for resolving JSON Schema
    $ref references to Python type names, handling both internal
    and external references.
    """

    def resolve_ref(self, ref: str) -> str:
        """Main entry point to resolve a $ref to a type name.

        Args:
            ref: Reference string (e.g., "#/definitions/Foo", "contracts/bar.yaml#/definitions/Baz")

        Returns:
            Resolved Python type name (e.g., "ModelFoo", "ModelBaz")
        """
        ...

    def resolve_internal_ref(self, ref: str) -> str:
        """Resolve internal reference (#/definitions/...).

        Args:
            ref: Internal reference string

        Returns:
            Resolved type name
        """
        ...

    def resolve_external_ref(self, ref: str) -> str:
        """Resolve external reference (file.yaml#/definitions/...).

        Args:
            ref: External reference string

        Returns:
            Resolved type name
        """
        ...

    def resolve_subcontract_ref(self, ref: str) -> str:
        """Resolve subcontract reference (contracts/file.yaml#/...).

        Args:
            ref: Subcontract reference string

        Returns:
            Resolved type name with subcontract prefix
        """
        ...

    def extract_definition_name(self, ref: str) -> str:
        """Extract the definition name from a reference.

        Args:
            ref: Reference string

        Returns:
            Definition name extracted from reference
        """
        ...

    def is_internal_ref(self, ref: str) -> bool:
        """Check if reference is internal.

        Args:
            ref: Reference to check

        Returns:
            True if internal reference
        """
        ...

    def is_subcontract_ref(self, ref: str) -> bool:
        """Check if reference is to a subcontract.

        Args:
            ref: Reference to check

        Returns:
            True if subcontract reference
        """
        ...

    def get_ref_parts(self, ref: str) -> Dict[str, Optional[str]]:
        """Parse reference into component parts.

        Args:
            ref: Reference to parse

        Returns:
            Dict with 'file', 'path', and 'name' components
        """
        ...
