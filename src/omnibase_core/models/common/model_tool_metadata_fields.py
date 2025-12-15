"""
Typed metadata model for discovered tools.

This module provides strongly-typed metadata for tool discovery patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelToolMetadataFields(BaseModel):
    """
    Typed metadata for discovered tools.

    Replaces dict[str, Any] metadata field in ModelDiscoveredTool
    with explicit typed fields for common tool metadata.

    Note: All fields are optional as metadata may be partially populated
    depending on the source and context. This is intentional for metadata
    models that aggregate information from multiple sources.
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    author: str | None = Field(
        default=None,
        description="Author or maintainer of the tool",
    )
    trust_score: float | None = Field(
        default=None,
        description="Trust score for the tool (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    documentation_url: str | None = Field(
        default=None,
        description="URL to tool documentation",
    )
    source_repository: str | None = Field(
        default=None,
        description="Source code repository URL",
    )
    license: str | None = Field(
        default=None,
        description="Software license identifier",
    )
    category: str | None = Field(
        default=None,
        description="Tool category for classification",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of tool capabilities",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of tool dependencies",
    )


__all__ = ["ModelToolMetadataFields"]
