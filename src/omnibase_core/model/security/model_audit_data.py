"""
ModelAuditData: Audit data representation.

This model provides structured audit data without using Any types.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelAuditData(BaseModel):
    """Audit data representation."""

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Audit timestamp"
    )
    user_id: Optional[str] = Field(None, description="User identifier")
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource accessed")
    result: str = Field(..., description="Action result")
    security_level: str = Field(..., description="Security classification")
    compliance_tags: List[str] = Field(
        default_factory=list, description="Compliance tags"
    )
    audit_metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional audit metadata"
    )
