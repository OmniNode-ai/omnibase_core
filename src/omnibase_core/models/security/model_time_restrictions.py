"""
ModelTimeRestrictions: Time-based access restrictions model.

This model represents time-based access restrictions for security policies.
"""

from pydantic import BaseModel, Field


class ModelTimeRestrictions(BaseModel):
    """Time-based access restrictions."""

    start_time: str | None = Field(
        default=None,
        description="Start time in HH:MM format",
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    end_time: str | None = Field(
        default=None,
        description="End time in HH:MM format",
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    allowed_days: str | None = Field(
        default=None,
        description="Allowed days (Monday-Sunday or Mon-Sun)",
        pattern=r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)(,(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun))*$",
    )

    timezone: str | None = Field(
        default="UTC", description="Timezone for time restrictions"
    )

    enforce_business_hours_only: bool = Field(
        default=False,
        description="Whether to enforce business hours only",
    )
