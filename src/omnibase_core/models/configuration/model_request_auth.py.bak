from pydantic import Field

"""
Request authentication configuration model.
"""

from pydantic import BaseModel, Field, SecretStr, field_serializer


class ModelRequestAuth(BaseModel):
    """Request authentication configuration."""

    auth_type: str = Field(
        ...,
        description="Authentication type (basic/bearer/oauth2/api_key)",
    )
    username: str | None = Field(None, description="Username for basic auth")
    password: SecretStr | None = Field(None, description="Password for basic auth")
    token: SecretStr | None = Field(None, description="Bearer token")
    api_key: SecretStr | None = Field(None, description="API key")
    api_key_header: str | None = Field(
        "X-API-Key",
        description="API key header name",
    )

    @field_serializer("password", "token", "api_key")
    def serialize_secret(self, value):
        if value and hasattr(value, "get_secret_value"):
            return "***MASKED***"
        return value
