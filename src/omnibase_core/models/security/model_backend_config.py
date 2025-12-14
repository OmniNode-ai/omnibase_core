"""
ModelBackendConfig: Configuration for secret backends.

This model represents the configuration parameters for different secret backends.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ModelBackendConfig(BaseModel):
    """Configuration parameters for secret backends."""

    model_config = ConfigDict(from_attributes=True)

    # Environment backend config
    env_prefix: str | None = Field(
        default=None, description="Environment variable prefix"
    )

    # Dotenv backend config
    dotenv_path: Path | None = Field(default=None, description="Path to .env file")

    auto_load_dotenv: bool | None = Field(
        default=None,
        description="Automatically load .env file",
    )

    # Vault backend config
    vault_url: str | None = Field(
        default=None,
        description="Vault server URL",
        pattern=r"^https?://.*$",
    )

    vault_token: SecretStr | None = Field(
        default=None,
        description="Vault authentication token",
    )

    vault_namespace: str | None = Field(default=None, description="Vault namespace")

    vault_path: str | None = Field(default=None, description="Vault secret path prefix")

    vault_role: str | None = Field(
        default=None, description="Vault role for authentication"
    )

    # Kubernetes backend config
    namespace: str | None = Field(default=None, description="Kubernetes namespace")

    secret_name: str | None = Field(default=None, description="Kubernetes secret name")

    # File backend config
    file_path: Path | None = Field(default=None, description="Path to secret file")

    encryption_key: SecretStr | None = Field(
        default=None,
        description="Encryption key for file backend",
    )

    file_permissions: str | None = Field(
        default=None,
        description="File permissions (e.g., '600')",
        pattern=r"^[0-7]{3,4}$",
    )
