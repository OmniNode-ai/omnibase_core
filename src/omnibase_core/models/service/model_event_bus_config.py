from pydantic import Field, field_validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Event bus configuration model for service communication.
"""

import os
from urllib.parse import urlparse

from pydantic import BaseModel, ValidationError


class ModelEventBusConfig(BaseModel):
    """Event bus configuration for service communication."""

    url: str = Field(
        default_factory=lambda: os.getenv("EVENT_BUS_URL", "http://localhost:8083"),
        description="Event bus service URL",
    )
    timeout_ms: int = Field(
        default=30000,
        description="Event bus timeout in milliseconds",
        ge=1000,
        le=300000,
    )
    retry_attempts: int = Field(
        default=3, description="Number of retry attempts", ge=1, le=10
    )
    connection_pool_size: int = Field(
        default=10,
        description="Connection pool size",
        ge=1,
        le=100,
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate event bus URL format."""
        try:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                msg = "Invalid event bus URL format - missing scheme or netloc"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
            return v
        except (ValueError, ValidationError) as e:
            if isinstance(e, ValidationError):
                raise
            msg = "Invalid event bus URL"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
