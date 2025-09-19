#!/usr/bin/env python3
"""Valid model file example following naming conventions."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ModelUserAuth(BaseModel):
    """User authentication model."""

    user_id: str
    username: str
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True

    class Config:
        extra = "forbid"
        validate_assignment = True


class ModelUserSession(BaseModel):
    """User session tracking model."""

    session_id: str
    user_id: str
    expires_at: datetime
    ip_address: str
    user_agent: str
