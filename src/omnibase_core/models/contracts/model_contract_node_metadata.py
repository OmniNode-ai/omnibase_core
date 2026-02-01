"""Contract Node Metadata Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

This module defines the metadata model for declarative node contracts, providing
structured storage for contract-specific information like source files, package
names, and deprecation status.

Stability Guarantee:
    - All fields, methods, and validators are stable interfaces
    - New optional fields may be added in minor versions only
    - Existing fields cannot be removed or have types/constraints changed
    - Breaking changes require major version bump

Important Distinction:
    This ModelContractNodeMetadata is specifically for contract-level metadata
    within the NodeMetaModel. It is distinct from:
    - omnibase_core.models.core.model_node_metadata.ModelNodeMetadata
      (used for general node metadata throughout the system)

Typical Usage:
    Used within ModelContractMeta to store additional contract metadata:
    - Source file location for code generation
    - Package information for module resolution
    - Deprecation tracking for version migration

Example:
    >>> metadata = ModelContractNodeMetadata(
    ...     source_file="src/nodes/my_node.py",
    ...     package_name="omnibase_core.nodes",
    ...     deprecated=False,
    ... )
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractNodeMetadata(BaseModel):
    """Typed model for additional node contract metadata.

    Provides structured, typed fields for contract metadata, replacing untyped
    dictionaries with a schema-enforced model. This model is immutable (frozen)
    after creation to ensure contract stability.

    This is used within ModelContractMeta for contract-specific metadata that
    describes where the node is defined, its package context, and deprecation status.

    Note:
        This is distinct from omnibase_core.models.core.model_node_metadata.ModelNodeMetadata
        which is used for general node metadata throughout the system.

    Attributes:
        source_file: Filesystem path where the node is defined.
        package_name: Python package containing the node.
        documentation_url: URL to external documentation.
        deprecated: Whether this node is deprecated.
        deprecation_message: Human-readable deprecation notice.

    Example:
        >>> metadata = ModelContractNodeMetadata(
        ...     source_file="src/omnibase_core/nodes/compute.py",
        ...     package_name="omnibase_core.nodes",
        ...     documentation_url="https://docs.example.com/compute",
        ...     deprecated=False,
        ... )
    """

    # Common metadata fields
    source_file: str | None = Field(
        default=None,
        description="Source file path where node is defined",
    )
    package_name: str | None = Field(
        default=None,
        description="Package name containing this node",
    )
    documentation_url: str | None = Field(
        default=None,
        description="URL to documentation for this node",
    )
    deprecated: bool = Field(
        default=False,
        description="Whether this node is deprecated",
    )
    deprecation_message: str | None = Field(
        default=None,
        description="Deprecation message if deprecated",
    )

    model_config = ConfigDict(
        extra="allow",  # Allow additional fields for extensibility
        from_attributes=True,
        frozen=True,
    )


__all__ = [
    "ModelContractNodeMetadata",
]
