"""
Raw Registry Mode Model for ONEX Configuration System.

Strongly typed model for unvalidated registry mode data loaded from YAML files.
"""

from pydantic import BaseModel, Field


class ModelRawRegistryMode(BaseModel):
    """
    Strongly typed model for raw registry mode data from YAML files.

    This represents the structure we expect for registry mode definitions
    in YAML configuration files before validation and conversion.
    """

    required_services: list[str] | None = Field(
        default_factory=list,
        description="List of required service names",
    )

    fallback_strategy: str | None = Field(
        default="bootstrap",
        description="Raw fallback strategy name from YAML",
    )

    health_check_interval: int | None = Field(
        default=30,
        description="Health check interval in seconds",
        ge=5,
        le=300,
    )

    circuit_breaker_threshold: int | None = Field(
        default=5,
        description="Circuit breaker failure threshold",
        ge=1,
        le=20,
    )

    circuit_breaker_timeout: int | None = Field(
        default=60,
        description="Circuit breaker timeout in seconds",
        ge=10,
        le=600,
    )
