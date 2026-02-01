"""
Connection Authentication Model.

Authentication configuration for network connections.
Part of the ModelConnectionInfo restructuring to reduce excessive string fields.
"""

from __future__ import annotations

import hashlib
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_serializer,
)

from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH
from omnibase_core.enums.enum_auth_type import EnumAuthType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict


class ModelConnectionAuth(BaseModel):
    """
    Connection authentication information.

    Contains authentication credentials and configuration
    without endpoint or pooling concerns.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    # Authentication type
    auth_type: EnumAuthType | None = Field(
        default=None, description="Authentication type"
    )

    # Basic authentication
    user_id: UUID | None = Field(default=None, description="UUID for user identity")
    user_display_name: str | None = Field(
        default=None,
        description="Human-readable username",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
        pattern=r"^[a-zA-Z0-9._@-]+$",
    )
    password: SecretStr | None = Field(
        default=None,
        description="Password (encrypted)",
        min_length=1,
    )

    # Token-based authentication
    api_key: SecretStr | None = Field(
        default=None,
        description="API key (encrypted)",
        min_length=1,
    )
    token: SecretStr | None = Field(
        default=None,
        description="Auth token (encrypted)",
        min_length=1,
    )

    def validate_auth_requirements(self) -> bool:
        """Validate authentication configuration is complete."""
        if self.auth_type == EnumAuthType.BASIC:
            return bool(self.user_display_name and self.password)
        elif self.auth_type == EnumAuthType.BEARER:
            return bool(self.token)
        elif self.auth_type == EnumAuthType.API_KEY_HEADER:
            return bool(self.api_key)
        else:
            # None or NONE - no authentication required
            return True

    def has_credentials(self) -> bool:
        """Check if any credentials are configured."""
        return bool(
            self.user_display_name or self.password or self.api_key or self.token,
        )

    def get_auth_header(self) -> dict[str, str] | None:
        """Generate authentication header."""
        if self.auth_type == EnumAuthType.BEARER and self.token:
            return {"Authorization": f"Bearer {self.token.get_secret_value()}"}
        if self.auth_type == EnumAuthType.API_KEY_HEADER and self.api_key:
            return {"X-API-Key": self.api_key.get_secret_value()}
        return None

    def is_secure_auth(self) -> bool:
        """Check if authentication method is secure."""
        return self.auth_type in {
            EnumAuthType.BEARER,
            EnumAuthType.API_KEY_HEADER,
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
        """Access username."""
        return self.user_display_name

    @username.setter
    def username(self, value: str | None) -> None:
        """Set username and generate corresponding user ID."""
        if value:
            user_hash = hashlib.sha256(value.encode()).hexdigest()
            self.user_id = UUID(
                f"{user_hash[:8]}-{user_hash[8:12]}-{user_hash[12:16]}-{user_hash[16:20]}-{user_hash[20:32]}",
            )
        else:
            self.user_id = None
        self.user_display_name = value

    @field_serializer("password", "api_key", "token")
    def serialize_secret(self, value: SecretStr | None) -> str:
        """Serialize secrets safely."""
        if value and hasattr(value, "get_secret_value"):
            return "***MASKED***"
        return str(value) if value else ""

    @classmethod
    def create_password_auth(
        cls,
        username: str,
        password: str,
    ) -> ModelConnectionAuth:
        """Create password-based authentication."""

        # Generate UUID from username
        user_hash = hashlib.sha256(username.encode()).hexdigest()
        user_id = UUID(
            f"{user_hash[:8]}-{user_hash[8:12]}-{user_hash[12:16]}-{user_hash[16:20]}-{user_hash[20:32]}",
        )

        return cls(
            auth_type=EnumAuthType.BASIC,
            user_id=user_id,
            user_display_name=username,
            password=SecretStr(password),
            api_key=None,
            token=None,
        )

    @classmethod
    def create_bearer_token(
        cls,
        token: str,
    ) -> ModelConnectionAuth:
        """Create bearer token authentication."""
        return cls(
            auth_type=EnumAuthType.BEARER,
            user_id=None,
            user_display_name=None,
            password=None,
            api_key=None,
            token=SecretStr(token),
        )

    @classmethod
    def create_api_key(
        cls,
        api_key: str,
    ) -> ModelConnectionAuth:
        """Create API key authentication."""
        return cls(
            auth_type=EnumAuthType.API_KEY_HEADER,
            user_id=None,
            user_display_name=None,
            password=None,
            api_key=SecretStr(api_key),
            token=None,
        )

    @classmethod
    def create_no_auth(cls) -> ModelConnectionAuth:
        """Create no authentication."""
        return cls(
            auth_type=None,
            user_id=None,
            user_display_name=None,
            password=None,
            api_key=None,
            token=None,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, TypeError, ValidationError, ValueError) as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Pydantic handles validation automatically during instantiation.
        # This method exists to satisfy the ProtocolValidatable interface.
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelConnectionAuth"]
