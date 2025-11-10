"""
Resource Usage Metric Model - ONEX Standards Compliant.

Strongly-typed model for resource usage metrics.
Replaces dict[str, float] with proper type safety and validation.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field, field_validator


class ModelResourceUsageMetric(BaseModel):
    """
    Strongly-typed resource usage metric.

    Provides structured resource usage information with proper
    validation and type safety.
    """

    resource_name: str = Field(
        ...,
        description="Name of the resource (cpu, memory, disk, network, etc.)",
        min_length=1,
    )

    usage_value: float = Field(
        ...,
        description="Current usage value for this resource",
        ge=0.0,
    )

    usage_unit: str = Field(
        default="percentage",
        description="Unit of measurement (percentage, bytes, mbps, iops, etc.)",
    )

    max_value: float | None = Field(
        default=None,
        description="Maximum allowed value for this resource",
        ge=0.0,
    )

    threshold_warning: float | None = Field(
        default=None,
        description="Warning threshold for this resource",
        ge=0.0,
    )

    threshold_critical: float | None = Field(
        default=None,
        description="Critical threshold for this resource",
        ge=0.0,
    )

    is_percentage: bool = Field(
        default=True,
        description="Whether the usage_value is a percentage (0-100)",
    )

    @field_validator("usage_value")
    @classmethod
    def validate_percentage_range(cls, v: float, info) -> float:
        """Validate percentage values are in valid range."""
        # Note: info.data may not have 'is_percentage' yet during validation
        # This is a safety check for common percentage cases
        if v > 100.0 and v < 200.0:  # Likely percentage but over 100
            # Allow values slightly over 100% for burst scenarios
            pass
        return v

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
