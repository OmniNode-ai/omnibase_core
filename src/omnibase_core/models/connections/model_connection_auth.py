"""
Connection Authentication Model.

Authentication configuration for network connections.
Part of the ModelConnectionInfo restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, Field, SecretStr, field_serializer
from typing import Any

from ...enums.enum_auth_type import EnumAuthType


class ModelConnectionAuth(BaseModel):
    """
    Connection authentication information.

    Contains authentication credentials and configuration
    without endpoint or pooling concerns.
    """

    # Authentication type
    auth_type: EnumAuthType | None = Field(None, description="Authentication type")

    # Basic authentication
    user_id: UUID | None = Field(None, description="UUID for user identity")
    user_display_name: str | None = Field(
        None,
        description="Human-readable username",
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._@-]+$",
    )
    password: SecretStr | None = Field(
        None, description="Password (encrypted)", min_length=1
    )

    # Token-based authentication
    api_key: SecretStr | None = Field(
        None, description="API key (encrypted)", min_length=1
    )
    token: SecretStr | None = Field(
        None, description="Auth token (encrypted)", min_length=1
    )

    def validate_auth_requirements(self) -> bool:
        """Validate authentication configuration is complete."""
        if self.auth_type == EnumAuthType.BASIC:
            return bool(self.user_display_name and self.password)
        elif self.auth_type == EnumAuthType.BEARER:
            return bool(self.token)
        elif self.auth_type == EnumAuthType.API_KEY:
            return bool(self.api_key)
        elif self.auth_type is None:
            return True  # No authentication required
        return False

    def has_credentials(self) -> bool:
        """Check if any credentials are configured."""
        return bool(
            self.user_display_name
            or self.password
            or self.api_key
            or self.token
        )

    def get_auth_header(self) -> dict[str, str] | None:
        """Generate authentication header."""
        if self.auth_type == EnumAuthType.BEARER and self.token:
            return {"Authorization": f"Bearer {self.token.get_secret_value()}"}
        elif self.auth_type == EnumAuthType.API_KEY and self.api_key:
            return {"X-API-Key": self.api_key.get_secret_value()}
        return None

    def is_secure_auth(self) -> bool:
        """Check if authentication method is secure."""
        return self.auth_type in {
            EnumAuthType.OAUTH2,
            EnumAuthType.JWT,
            EnumAuthType.MTLS,
            EnumAuthType.BEARER,
        }

    def clear_credentials(self) -> None:
        """Clear all credentials (for security)."""
        self.user_id = None
        self.user_display_name = None
        self.password = None
        self.api_key = None
        self.token = None

    @property
    def username(self) -> str | None:
        """Backward compatibility property for username."""
        return self.user_display_name

    @username.setter
    def username(self, value: str | None) -> None:
        """Backward compatibility setter for username."""
        if value:
            import hashlib
            user_hash = hashlib.sha256(value.encode()).hexdigest()
            self.user_id = UUID(f"{user_hash[:8]}-{user_hash[8:12]}-{user_hash[12:16]}-{user_hash[16:20]}-{user_hash[20:32]}")
        else:
            self.user_id = None
        self.user_display_name = value

    @field_serializer("password", "api_key", "token")
    def serialize_secret(self, value: Any) -> str:
        """Serialize secrets safely."""
        if value and hasattr(value, "get_secret_value"):
            return "***MASKED***"
        return str(value) if value else ""

    @classmethod
    def create_basic_auth(
        cls,
        username: str,
        password: str,
    ) -> ModelConnectionAuth:
        """Create basic authentication."""
        import hashlib

        # Generate UUID from username
        user_hash = hashlib.sha256(username.encode()).hexdigest()
        user_id = UUID(f"{user_hash[:8]}-{user_hash[8:12]}-{user_hash[12:16]}-{user_hash[16:20]}-{user_hash[20:32]}")

        return cls(
            auth_type=EnumAuthType.BASIC,
            user_id=user_id,
            user_display_name=username,
            password=SecretStr(password),
        )

    @classmethod
    def create_bearer_token(
        cls,
        token: str,
    ) -> ModelConnectionAuth:
        """Create bearer token authentication."""
        return cls(
            auth_type=EnumAuthType.BEARER,
            token=SecretStr(token),
        )

    @classmethod
    def create_api_key(
        cls,
        api_key: str,
    ) -> ModelConnectionAuth:
        """Create API key authentication."""
        return cls(
            auth_type=EnumAuthType.API_KEY,
            api_key=SecretStr(api_key),
        )

    @classmethod
    def create_no_auth(cls) -> ModelConnectionAuth:
        """Create no authentication."""
        return cls()


# Export for use
__all__ = ["ModelConnectionAuth"]