# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Capability metadata model for documentation and discovery.

This module provides the ModelCapabilityMetadata model that describes
what a capability is, its requirements, and example providers. This is
metadata about capabilities for documentation and discovery purposes,
NOT runtime registration.

OMN-1156: ModelCapabilityMetadata - Capability metadata for documentation/discovery.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelCapabilityMetadata(BaseModel):
    """
    Metadata about a capability for documentation and discovery.

    This model describes what a capability is, what features it requires
    or optionally supports, and which providers are known to offer it.
    Capability IDs are semantic strings (e.g., "database.relational"),
    NOT UUIDs. UUIDs are for runtime instances only.

    Use Cases:
    - Documentation: Describe what a capability provides
    - Discovery: Find capabilities by tags or features
    - Provider matching: Identify compatible providers by feature requirements
    - Capability catalog: Build a registry of available capabilities

    Example:
        metadata = ModelCapabilityMetadata(
            capability="database.relational",
            name="Relational Database",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="SQL-based relational database operations",
            tags=("storage", "sql", "acid"),
            required_features=("query", "transactions"),
            optional_features=("json_support", "full_text_search"),
            example_providers=("PostgreSQL", "MySQL", "SQLite"),
        )

    Note:
        - from_attributes=True allows Pydantic to accept objects with matching
          attributes even when class identity differs (e.g., in pytest-xdist
          parallel execution where model classes are imported in separate workers).
        - See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # ==========================================================================
    # Required Fields
    # ==========================================================================

    capability: str = Field(
        ...,
        description="Semantic capability identifier, e.g. 'database.relational'",
    )

    name: str = Field(
        ...,
        description="Human-readable name",
    )

    version: ModelSemVer = Field(
        ...,
        description="Capability version",
    )

    description: str = Field(
        ...,
        description="Short description of what this capability provides",
    )

    # ==========================================================================
    # Optional Fields (default to empty tuples for immutable collections)
    # ==========================================================================

    tags: tuple[str, ...] = Field(
        default=(),
        description="Tags for categorization/filtering",
    )

    required_features: tuple[str, ...] = Field(
        default=(),
        description="Features a provider MUST have",
    )

    optional_features: tuple[str, ...] = Field(
        default=(),
        description="Features a provider MAY have",
    )

    example_providers: tuple[str, ...] = Field(
        default=(),
        description="Known provider types that offer this capability",
    )


__all__ = ["ModelCapabilityMetadata"]
