"""
Filter Conditions Model.

Strongly-typed filter conditions model that replaces dict[str, str | int | float | bool] patterns
with proper Pydantic validation and type safety.

Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelFilterConditions(BaseModel):
    """
    Strongly-typed filter conditions for event filtering.

    Replaces dict[str, str | int | float | bool] patterns with proper Pydantic model
    providing runtime validation and type safety for event filtering.

    Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
    """

    # ONEX correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking filter conditions across operations",
    )

    # String-based filters
    event_type_pattern: str | None = Field(
        default=None,
        description="Event type pattern filter",
        max_length=200,
    )

    source_pattern: str | None = Field(
        default=None,
        description="Event source pattern filter",
        max_length=200,
    )

    subject_pattern: str | None = Field(
        default=None,
        description="Event subject pattern filter",
        max_length=500,
    )

    # Exact match filters
    event_type: str | None = Field(
        default=None,
        description="Exact event type match",
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    source: str | None = Field(
        default=None,
        description="Exact source match",
        max_length=200,
    )

    # Numeric filters
    min_priority: int | None = Field(
        default=None,
        description="Minimum event priority",
        ge=0,
        le=100,
    )

    max_priority: int | None = Field(
        default=None,
        description="Maximum event priority",
        ge=0,
        le=100,
    )

    min_size_bytes: int | None = Field(
        default=None,
        description="Minimum event size in bytes",
        ge=0,
    )

    max_size_bytes: int | None = Field(
        default=None,
        description="Maximum event size in bytes",
        ge=0,
    )

    # Float filters
    min_version: float | None = Field(
        default=None,
        description="Minimum event schema version",
        ge=0.0,
    )

    max_version: float | None = Field(
        default=None,
        description="Maximum event schema version",
        ge=0.0,
    )

    # Boolean filters
    require_authentication: bool | None = Field(
        default=None,
        description="Whether to require authenticated events",
    )

    require_encryption: bool | None = Field(
        default=None,
        description="Whether to require encrypted events",
    )

    exclude_system_events: bool | None = Field(
        default=None,
        description="Whether to exclude system-generated events",
    )

    include_debug_events: bool | None = Field(
        default=None,
        description="Whether to include debug-level events",
    )

    # Time-based filters
    after_timestamp: datetime | None = Field(
        default=None,
        description="DateTime - only events after this time",
    )

    before_timestamp: datetime | None = Field(
        default=None,
        description="DateTime - only events before this time",
    )

    # List-based filters
    allowed_sources: list[str] = Field(
        default_factory=list,
        description="List of allowed event sources",
    )

    blocked_sources: list[str] = Field(
        default_factory=list,
        description="List of blocked event sources",
    )

    allowed_types: list[str] = Field(
        default_factory=list,
        description="List of allowed event types",
    )

    blocked_types: list[str] = Field(
        default_factory=list,
        description="List of blocked event types",
    )

    # Tags and categories
    required_tags: list[str] = Field(
        default_factory=list,
        description="List of tags that must be present",
    )

    forbidden_tags: list[str] = Field(
        default_factory=list,
        description="List of tags that must not be present",
    )

    category: str | None = Field(
        default=None,
        description="Event category filter",
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    # Advanced filters
    severity_level: Literal["debug", "info", "warn", "error", "critical"] | None = (
        Field(
            default=None,
            description="Minimum severity level to include",
        )
    )

    environment: str | None = Field(
        default=None,
        description="Environment filter (dev, staging, prod)",
        max_length=50,
    )

    @field_validator("after_timestamp", "before_timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime | None) -> datetime | None:
        """Validate datetime object."""
        if v is not None:
            # Ensure datetime is timezone-aware or convert to UTC
            if v.tzinfo is None:
                # If naive datetime, treat as UTC

                v = v.replace(tzinfo=UTC)
        return v

    @field_validator(
        "allowed_sources",
        "blocked_sources",
        "allowed_types",
        "blocked_types",
    )
    @classmethod
    def validate_source_type_lists(cls, v: list[str]) -> list[str]:
        """Validate source and type filter list[Any]s."""
        validated = []
        for item in v:
            item = item.strip()
            if not item:
                continue

            if len(item) > 200:
                raise ModelOnexError(
                    message=f"Source/type filter '{item}' too long. Maximum 200 characters.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

            validated.append(item)

        return validated

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
