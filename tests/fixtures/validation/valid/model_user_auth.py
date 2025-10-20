#!/usr/bin/env python3
"""Valid model file example following naming conventions."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ModelUserAuth(BaseModel):
    """User authentication model."""

    user_id: str
    username: str
    email: str
    created_at: datetime
    last_login: datetime | None = None
    is_active: bool = True

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class ModelUserSession(BaseModel):
    """User session tracking model."""

    session_id: str
    user_id: str
    expires_at: datetime
    ip_address: str
    user_agent: str
