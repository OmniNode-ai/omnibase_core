"""
ModelPermissionEvaluationContext: Context for permission evaluation.

This model provides structured context for permission evaluation without using Any types.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelPermissionEvaluationContext(BaseModel):
    """Context for permission evaluation."""

    user_id: Optional[str] = Field(None, description="User identifier")
    resource_path: Optional[str] = Field(None, description="Resource being accessed")
    requested_action: Optional[str] = Field(None, description="Action being requested")
    timestamp: Optional[datetime] = Field(None, description="Request timestamp")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    session_id: Optional[str] = Field(None, description="Session identifier")

    # Separate dictionaries for different types to avoid Union
    string_attributes: Dict[str, str] = Field(
        default_factory=dict, description="String context attributes"
    )
    integer_attributes: Dict[str, int] = Field(
        default_factory=dict, description="Integer context attributes"
    )
    boolean_attributes: Dict[str, bool] = Field(
        default_factory=dict, description="Boolean context attributes"
    )
