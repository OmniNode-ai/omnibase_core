"""
Model for masked configuration output.
"""

from pydantic import BaseModel, Field


class ModelMaskedConfig(BaseModel):
    """Masked configuration with sensitive fields redacted."""

    service_name: str = Field(description="Service name")
    service_type: str = Field(description="Service type")
    connection_config: dict[str, str | int | bool] = Field(
        description="Connection config with masked sensitive values",
    )
    health_check_enabled: bool = Field(description="Health check status")
    health_check_timeout: int = Field(description="Health check timeout")
    required: bool = Field(description="Whether service is required")
    retry_config: dict[str, str | int] | None = Field(
        default=None,
        description="Retry configuration",
    )
    tags: dict[str, str] | None = Field(default=None, description="Service tags")
