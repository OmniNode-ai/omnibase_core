"""
Resource Usage Metric Model.

Strongly-typed model for resource usage metrics.
Replaces dict[str, float] with proper type safety and validation.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_resource_unit import EnumResourceUnit
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelResourceUsageMetric(BaseModel):
    """
    Strongly-typed resource usage metric.

    Provides structured resource usage information with proper
    validation and type safety.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

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

    usage_unit: EnumResourceUnit = Field(
        default=EnumResourceUnit.PERCENTAGE,
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
        description="Whether usage_value should be treated as a percentage (enforced max 150 for burst scenarios)",
    )

    @model_validator(mode="after")
    def validate_percentage_range(self) -> "ModelResourceUsageMetric":
        """Validate percentage values are within reasonable range."""
        if self.is_percentage and self.usage_value > 150.0:
            raise ModelOnexError(
                message=f"Percentage usage_value {self.usage_value} exceeds maximum (150%). "
                "Use is_percentage=False for non-percentage metrics.",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        return self

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
