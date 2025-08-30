"""
ModelBackendConfig: Configuration for secret backends.

This model represents the configuration parameters for different secret backends.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, SecretStr


class ModelBackendConfig(BaseModel):
    """Configuration parameters for secret backends."""

    # Environment backend config
    env_prefix: Optional[str] = Field(None, description="Environment variable prefix")

    # Dotenv backend config
    dotenv_path: Optional[Path] = Field(None, description="Path to .env file")

    auto_load_dotenv: Optional[bool] = Field(
        None, description="Automatically load .env file"
    )

    # Vault backend config
    vault_url: Optional[str] = Field(
        None, description="Vault server URL", pattern=r"^https?://.*$"
    )

    vault_token: Optional[SecretStr] = Field(
        None, description="Vault authentication token"
    )

    vault_namespace: Optional[str] = Field(None, description="Vault namespace")

    vault_path: Optional[str] = Field(None, description="Vault secret path prefix")

    vault_role: Optional[str] = Field(None, description="Vault role for authentication")

    # Kubernetes backend config
    namespace: Optional[str] = Field(None, description="Kubernetes namespace")

    secret_name: Optional[str] = Field(None, description="Kubernetes secret name")

    # File backend config
    file_path: Optional[Path] = Field(None, description="Path to secret file")

    encryption_key: Optional[SecretStr] = Field(
        None, description="Encryption key for file backend"
    )

    file_permissions: Optional[str] = Field(
        None, description="File permissions (e.g., '600')", pattern=r"^[0-7]{3,4}$"
    )
