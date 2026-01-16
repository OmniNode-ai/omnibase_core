"""
Security Metadata Reference Model.

Provides an opaque reference to security metadata for handlers and nodes.
This is a minimal reference model that enables registry-resolved security
configuration without embedding the full security policy inline.

Security metadata referenced by this model includes (but is not limited to):
    - Allowed domains: Network domains the handler is permitted to access
    - Secret scopes: Named scopes for secret/credential access (e.g., "api-keys", "db-creds")
    - Classification: Security classification level (e.g., "internal", "confidential")
    - Access control: Role-based or attribute-based access control policies
    - Audit requirements: Logging and compliance requirements

The actual security configuration is resolved at runtime via the reference
identifier (ref field), typically from a security registry or configuration
store. This separation of reference from definition enables:
    - Centralized security policy management
    - Runtime policy updates without handler redeployment
    - Security policy versioning and rollback
    - Environment-specific security overrides

Thread Safety:
    ModelSecurityMetadataRef is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access from multiple threads
    or async tasks. This follows ONEX thread safety guidelines for reference
    models used in handler configuration.

See Also:
    - docs/architecture/SECURITY_METADATA_ARCHITECTURE.md (planned)
    - omnibase_core.models.contracts.model_node_ref: Similar reference pattern
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelSecurityMetadataRef(BaseModel):
    """
    Opaque reference to security metadata for registry-resolved security configuration.

    This model provides a stable reference identifier that can be resolved at runtime
    to retrieve the full security metadata definition from a registry or configuration
    store. The opaque reference pattern decouples handlers from their security policies,
    enabling centralized security management.

    Security metadata includes allowed domains, secret scopes, classification levels,
    access control policies, and audit requirements. The actual security configuration
    is NOT stored in this model - only a reference to where it can be retrieved.

    Attributes:
        ref: Opaque stable identifier for the security metadata.
            This is the primary lookup key used to resolve the full security
            configuration from the registry. Format is registry-specific but
            should be stable across deployments (e.g., "security://handlers/api-gateway",
            "urn:onex:security:policy-v1").
        digest: Optional content digest/checksum for integrity verification.
            When provided, the resolved security configuration can be verified
            against this digest to detect tampering or corruption. Format is
            typically "algorithm:hex" (e.g., "sha256:abc123...").
        version: Optional semantic version of the security metadata.
            Enables version-pinned security policies and controlled rollouts.
            When None, the latest version is used.
        source: Optional source location or registry identifier.
            Specifies where to resolve the reference when multiple registries
            are available (e.g., "vault://prod", "consul://security-store").

    Example:
        >>> ref = ModelSecurityMetadataRef(ref="security://handlers/api-gateway")
        >>> ref.ref
        'security://handlers/api-gateway'

        >>> # With version pinning
        >>> ref = ModelSecurityMetadataRef(
        ...     ref="security://handlers/api-gateway",
        ...     version=ModelSemVer(major=1, minor=2, patch=0),
        ...     digest="sha256:abc123def456",
        ... )

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.
    """

    ref: str = Field(
        ...,
        description=(
            "Opaque stable identifier for the security metadata. "
            "Used as the primary lookup key to resolve full security configuration "
            "from a registry or configuration store at runtime."
        ),
        min_length=1,
    )

    digest: str | None = Field(
        default=None,
        description=(
            "Optional content digest/checksum for integrity verification. "
            "Format is typically 'algorithm:hex' (e.g., 'sha256:abc123...'). "
            "When provided, the resolved configuration can be verified against this digest."
        ),
    )

    version: ModelSemVer | None = Field(
        default=None,
        description=(
            "Optional semantic version of the security metadata. "
            "Enables version-pinned security policies. When None, latest version is used."
        ),
    )

    source: str | None = Field(
        default=None,
        description=(
            "Optional source location or registry identifier. "
            "Specifies where to resolve the reference when multiple registries "
            "are available (e.g., 'vault://prod', 'consul://security-store')."
        ),
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        parts = [f"ref={self.ref!r}"]
        if self.version:
            parts.append(f"version={self.version}")
        return f"ModelSecurityMetadataRef({', '.join(parts)})"


__all__ = ["ModelSecurityMetadataRef"]
