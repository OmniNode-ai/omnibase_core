"""
Contract Node Metadata Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed
- Breaking changes require major version bump

This module defines the metadata model for declarative node contracts.

NOTE: This is distinct from omnibase_core.models.core.model_node_metadata.ModelNodeMetadata
which is used for general node metadata. This class is specifically for
contract-level metadata in the NodeMetaModel.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractNodeMetadata(BaseModel):
    """Typed model for additional node contract metadata.

    Provides structured typed fields for metadata (replaces untyped dict).
    This is used within NodeMetaModel for contract-specific metadata.

    NOTE: This is distinct from omnibase_core.models.core.model_node_metadata.ModelNodeMetadata
    which is used for general node metadata throughout the system.
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
        frozen=True,
    )


__all__ = [
    "ModelContractNodeMetadata",
]
