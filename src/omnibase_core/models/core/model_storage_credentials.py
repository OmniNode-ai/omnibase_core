"""
Storage Credentials Model.

Strongly-typed model for storage backend authentication credentials.
"""

from pydantic import BaseModel, Field, SecretStr


class ModelStorageCredentials(BaseModel):
    """
    Model for storage backend authentication credentials.

    Used by storage backends to securely handle authentication
    information for various storage systems.
    """

    username: str | None = Field(
        description="Username for authentication", default=None
    )

    password: SecretStr | None = Field(
        description="Password for authentication (secure)", default=None
    )

    api_key: SecretStr | None = Field(
        description="API key for authentication (secure)", default=None
    )

    token: SecretStr | None = Field(
        description="Bearer token for authentication (secure)", default=None
    )

    connection_string: SecretStr | None = Field(
        description="Complete connection string (secure)", default=None
    )

    additional_params: dict[str, str] = Field(
        description="Additional authentication parameters", default_factory=dict
    )
