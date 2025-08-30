#!/usr/bin/env python3
"""
Error serialization data model for ONEX core.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class ModelErrorSerializationData(BaseModel):
    """Strong typing for error serialization data."""

    message: str = Field(description="Error message")
    error_code: Optional[str] = Field(default=None, description="Error code")
    status: EnumOnexStatus = Field(description="Error status")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID")
    timestamp: Optional[datetime] = Field(default=None, description="Error timestamp")
    context_strings: Dict[str, str] = Field(
        default_factory=dict, description="String context data"
    )
    context_numbers: Dict[str, int] = Field(
        default_factory=dict, description="Numeric context data"
    )
    context_flags: Dict[str, bool] = Field(
        default_factory=dict, description="Boolean context data"
    )
