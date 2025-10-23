"""
Storage Credentials Model - ONEX Standards Compliant.

Strongly-typed model for storage backend authentication credentials.
"""

import json
from typing import Any, Optional

from pydantic import BaseModel, Field, SecretStr

from .model_storage_credentials_config import ModelConfig


class ModelStorageCredentials(BaseModel):
    """
    Model for storage backend authentication credentials.

    Used by storage backends to securely handle authentication
    information for various storage systems.
    """

    username: Optional[str] = Field(
        description="Username for authentication", default=None
    )

    password: Optional[SecretStr] = Field(
        description="Password for authentication (secure)", default=None
    )

    api_key: Optional[SecretStr] = Field(
        description="API key for authentication (secure)", default=None
    )

    token: Optional[SecretStr] = Field(
        description="Bearer token for authentication (secure)", default=None
    )

    connection_string: Optional[SecretStr] = Field(
        description="Complete connection string (secure)", default=None
    )

    additional_params: dict[str, str] = Field(
        description="Additional authentication parameters", default_factory=dict
    )
