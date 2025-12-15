"""
Typed metadata model for node capabilities.

This module provides strongly-typed metadata for node capability patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelNodeCapabilitiesMetadata(BaseModel):
    """
    Typed metadata for node capabilities.

    Replaces dict[str, Any] metadata field in ModelNodeCapabilities
    with explicit typed fields for common node metadata.

    Note: All fields are optional as metadata may be partially populated
    depending on the source and context. This is intentional for metadata
    models that aggregate information from multiple sources.
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    description: str | None = Field(
        default=None,
        description="Human-readable description of the node",
    )
    author: str | None = Field(
        default=None,
        description="Author or maintainer of the node",
    )
    copyright: str | None = Field(
        default=None,
        description="Copyright information for the node",
    )
    trust_score: float | None = Field(
        default=None,
        description="Trust score for the node (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    documentation_url: str | None = Field(
        default=None,
        description="URL to node documentation",
    )
    source_repository: str | None = Field(
        default=None,
        description="Source code repository URL",
    )
    license: str | None = Field(
        default=None,
        description="Software license identifier",
    )
    maintainers: list[str] = Field(
        default_factory=list,
        description="List of node maintainers",
    )


__all__ = ["ModelNodeCapabilitiesMetadata"]
