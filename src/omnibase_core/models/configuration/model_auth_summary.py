"""Masked authentication summary model for logging and debugging.

Provides safe authentication information display without exposing sensitive data.
"""

from pydantic import BaseModel, Field


class ModelAuthSummary(BaseModel):
    """Masked authentication summary for logging/debugging.

    Attributes:
        auth_type: Type of authentication (basic, bearer, etc.)
        username: Username for basic auth (if applicable)
        password: Password placeholder (always masked)  # secret-ok: model field name
        token: Token placeholder (always masked)  # secret-ok: model field name
    """

    auth_type: str = Field(default="unknown", description="Type of authentication")
    username: str | None = Field(default=None, description="Username (if basic auth)")
    password: str | None = Field(  # secret-ok: model field name
        default=None, description="Password placeholder (always masked)"
    )
    token: str | None = Field(  # secret-ok: model field name
        default=None, description="Token placeholder (always masked)"
    )


__all__ = ["ModelAuthSummary"]
