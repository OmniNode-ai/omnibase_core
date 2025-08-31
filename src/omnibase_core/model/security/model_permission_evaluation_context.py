"""
ModelPermissionEvaluationContext: Context for permission evaluation.

This model provides structured context for permission evaluation without using Any types.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelPermissionEvaluationContext(BaseModel):
    """Context for permission evaluation."""

    user_id: str | None = Field(None, description="User identifier")
    resource_path: str | None = Field(None, description="Resource being accessed")
    requested_action: str | None = Field(None, description="Action being requested")
    timestamp: datetime | None = Field(None, description="Request timestamp")
    client_ip: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="Client user agent")
    session_id: str | None = Field(None, description="Session identifier")

    # Separate dictionaries for different types to avoid Union
    string_attributes: dict[str, str] = Field(
        default_factory=dict,
        description="String context attributes",
    )
    integer_attributes: dict[str, int] = Field(
        default_factory=dict,
        description="Integer context attributes",
    )
    boolean_attributes: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean context attributes",
    )
