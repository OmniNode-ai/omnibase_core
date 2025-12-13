"""
Typed metadata model for discovered tools.

This module provides strongly-typed metadata for tool discovery patterns.
"""

from pydantic import BaseModel, Field


class ModelToolMetadataFields(BaseModel):
    """
    Typed metadata for discovered tools.

    Replaces dict[str, Any] metadata field in ModelDiscoveredTool
    with explicit typed fields for common tool metadata.
    """

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
