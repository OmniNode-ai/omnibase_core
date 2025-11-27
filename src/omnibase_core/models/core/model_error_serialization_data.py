"""
Error serialization data model for ONEX core.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class ModelErrorSerializationData(BaseModel):
    """Strong typing for error serialization data."""

    message: str = Field(description="Error message")
    error_code: str | None = Field(default=None, description="Error code")
    status: EnumOnexStatus = Field(description="Error status")
    correlation_id: UUID | None = Field(default=None, description="Correlation ID")
    timestamp: datetime | None = Field(default=None, description="Error timestamp")
    context_strings: dict[str, str] = Field(
        default_factory=dict,
        description="String context data",
    )
    context_numbers: dict[str, int] = Field(
        default_factory=dict,
        description="Numeric context data",
    )
    context_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean context data",
    )
