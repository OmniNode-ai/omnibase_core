"""
ModelBackendCapabilities: Secret backend capability configuration.

This model represents the capabilities supported by different secret backends.
"""

from pydantic import BaseModel, Field


class ModelBackendCapabilities(BaseModel):
    """Capabilities supported by a secret backend."""

    supports_secrets: bool = Field(
        default=True,
        description="Whether backend supports storing secrets",
    )

    supports_rotation: bool = Field(
        default=False,
        description="Whether backend supports automatic secret rotation",
    )

    supports_encryption: bool = Field(
        default=False,
        description="Whether backend supports encryption at rest",
    )

    supports_audit: bool = Field(
        default=False,
        description="Whether backend supports audit logging",
    )

    supports_versioning: bool = Field(
        default=False,
        description="Whether backend supports secret versioning",
    )

    supports_access_control: bool = Field(
        default=False,
        description="Whether backend supports fine-grained access control",
    )

    production_ready: bool = Field(
        default=False,
        description="Whether backend is suitable for production use",
    )

    requires_external_service: bool = Field(
        default=False,
        description="Whether backend requires an external service",
    )
