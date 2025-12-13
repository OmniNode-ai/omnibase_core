"""
Raw Service Model for ONEX Configuration System.

Strongly typed model for unvalidated service data loaded from YAML files.
"""

from pydantic import BaseModel, Field


class ModelRawService(BaseModel):
    """
    Strongly typed model for raw service data from YAML files.

    This represents the structure we expect for service definitions
    in YAML configuration files before validation and conversion.
    """

    type: str | None = Field(
        default=None,
        description="Raw service type name from YAML",
    )

    detection: str | None = Field(
        default=None,
        description="Raw detection configuration name from YAML",
    )

    priority: int | None = Field(
        default=1,
        description="Service priority level",
        ge=1,
    )

    required: bool | None = Field(
        default=True,
        description="Whether service is required",
    )

    fallback_enabled: bool | None = Field(
        default=True,
        description="Whether fallback is enabled",
    )
