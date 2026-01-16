"""
Capability metadata model for documentation and discovery.

This module provides the ModelCapabilityMetadata model that describes
what a capability is, its requirements, and example providers. This is
metadata about capabilities for documentation and discovery purposes,
NOT runtime registration.

OMN-1156: ModelCapabilityMetadata - Capability metadata for documentation/discovery.
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Pattern for semantic capability identifiers:
# - Must start with a lowercase letter
# - Segments separated by dots (.)
# - Each segment: starts with lowercase letter, followed by lowercase letters, digits, or underscores
# Examples: "llm.generation", "storage.vector_db", "compute.gpu.nvidia"
CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")


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

    @field_validator("capability")
    @classmethod
    def validate_capability_format(cls, v: str) -> str:
        """
        Validate that capability follows semantic identifier format.

        Valid format: lowercase alphanumeric with underscores, dot-separated segments.
        Each segment must start with a lowercase letter.

        Examples of valid capabilities:
            - "llm.generation"
            - "storage.vector_db"
            - "compute.gpu.nvidia"
            - "database"

        Examples of invalid capabilities:
            - "LLM.Generation" (uppercase not allowed)
            - "123.abc" (must start with letter)
            - ".invalid" (cannot start with dot)
            - "invalid." (cannot end with dot)
            - "invalid..segment" (empty segments not allowed)
        """
        if not CAPABILITY_PATTERN.match(v):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Invalid capability format: '{v}'. "
                "Capability must be a semantic identifier with dot-separated segments. "
                "Each segment must start with a lowercase letter and contain only "
                "lowercase letters, digits, or underscores. "
                "Examples: 'llm.generation', 'storage.vector_db', 'compute.gpu.nvidia'"
            )
        return v

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
