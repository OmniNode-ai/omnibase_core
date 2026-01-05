# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Handler Packaging Metadata Model.

Defines artifact references, integrity hashes, signatures, and sandbox compatibility
for secure handler distribution and verification.

Design Principles:
    - Security-first: All artifacts require integrity hashes
    - Portable: Artifact references use explicit URI schemes (no raw local paths)
    - Verifiable: Optional cryptographic signatures for supply chain security
    - Sandbox-aware: Includes sandbox requirements for secure execution

Artifact Reference Schemes (v1):
    - https://...       - HTTPS URL
    - file:///...       - Local file URL (absolute path)
    - oci://...         - OCI container registry reference
    - registry://...    - Internal registry reference

Algorithm Support (v1):
    - Hash: SHA256 only (64 lowercase hex characters)
    - Signature: ED25519 only

Relationship to ModelPackagingMetadataRef:
    - ModelPackagingMetadataRef is an opaque **reference** (pointer) to packaging metadata
    - ModelHandlerPackaging is the **full metadata** that the ref points to
    - ModelHandlerDescriptor.packaging_metadata_ref → resolves to → ModelHandlerPackaging

Thread Safety:
    ModelHandlerPackaging is immutable (frozen=True) after creation.
    Thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.handlers.model_handler_packaging import (
    ...     ModelHandlerPackaging,
    ... )
    >>> from omnibase_core.models.handlers.model_sandbox_requirements import (
    ...     ModelSandboxRequirements,
    ... )
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> packaging = ModelHandlerPackaging(
    ...     artifact_reference="oci://ghcr.io/omninode/handlers/validator:v1.0.0",
    ...     integrity_hash="a" * 64,  # SHA256 hash
    ...     sandbox_compatibility=ModelSandboxRequirements(
    ...         requires_network=False,
    ...         memory_limit_mb=256,
    ...     ),
    ...     min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
    ... )

See Also:
    - ModelPackagingMetadataRef: Opaque reference to packaging metadata
    - ModelSandboxRequirements: Sandbox resource constraints
    - EnumHashAlgorithm: Supported hash algorithms
    - EnumSignatureAlgorithm: Supported signature algorithms
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_hash_algorithm import EnumHashAlgorithm
from omnibase_core.enums.enum_signature_algorithm import EnumSignatureAlgorithm
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.handlers.model_sandbox_requirements import (
    ModelSandboxRequirements,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Allowed artifact reference schemes (v1)
_ALLOWED_SCHEMES = frozenset({"https://", "file:///", "oci://", "registry://"})


def _validate_artifact_reference(reference: str) -> bool:
    """
    Validate artifact reference uses an allowed URI scheme.

    Args:
        reference: Artifact reference string

    Returns:
        True if reference starts with an allowed scheme
    """
    return any(reference.startswith(scheme) for scheme in _ALLOWED_SCHEMES)


class ModelHandlerPackaging(BaseModel):
    """
    Full packaging metadata for secure handler distribution.

    This model contains all information needed to:
        - Locate a handler artifact (artifact_reference)
        - Verify its integrity (integrity_hash, hash_algorithm)
        - Verify its authenticity (signature_reference, signature_algorithm)
        - Determine sandbox requirements (sandbox_compatibility)
        - Check runtime compatibility (min/max_runtime_version)

    The packaging metadata is the resolved form of ModelPackagingMetadataRef.
    When a handler descriptor has a packaging_metadata_ref, it resolves to
    an instance of this model.

    Attributes:
        artifact_reference: URI pointing to the handler artifact. Must use an
            explicit scheme (https://, file:///, oci://, registry://). Raw local
            paths are not allowed for portability.
        integrity_hash: SHA256 hash of the artifact (64 lowercase hex chars).
            Used to verify artifact integrity after download.
        hash_algorithm: Hash algorithm used for integrity_hash. v1 supports
            only SHA256.
        signature_reference: Optional URI to detached signature file for
            cryptographic verification.
        signature_algorithm: Algorithm used for signature. v1 supports only
            ED25519. Required if signature_reference is set.
        sandbox_compatibility: Resource constraints and permissions required
            by this handler when running in a sandbox.
        min_runtime_version: Minimum ONEX runtime version required to run
            this handler.
        max_runtime_version: Optional maximum runtime version. Useful for
            handlers with known incompatibilities with newer runtimes.

    Example:
        >>> # Minimal packaging (no signature)
        >>> packaging = ModelHandlerPackaging(
        ...     artifact_reference="https://releases.example.com/handler-1.0.0.whl",
        ...     integrity_hash="abc123..." + "0" * 58,  # 64 chars total
        ...     sandbox_compatibility=ModelSandboxRequirements(),
        ...     min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        ... )

        >>> # With signature verification
        >>> signed_packaging = ModelHandlerPackaging(
        ...     artifact_reference="oci://ghcr.io/myorg/handler:v1.0.0",
        ...     integrity_hash="def456..." + "0" * 58,
        ...     signature_reference="https://releases.example.com/handler-1.0.0.sig",
        ...     signature_algorithm=EnumSignatureAlgorithm.ED25519,
        ...     sandbox_compatibility=ModelSandboxRequirements(requires_network=True),
        ...     min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        ...     max_runtime_version=ModelSemVer(major=1, minor=0, patch=0),
        ... )

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # =========================================================================
    # Artifact Location
    # =========================================================================

    artifact_reference: str = Field(
        ...,
        description=(
            "URI pointing to the handler artifact. Must use an explicit scheme: "
            "https://, file:///, oci://, or registry://. "
            "Raw local paths (e.g., /path/to/file) are not allowed."
        ),
        min_length=1,
    )

    # =========================================================================
    # Integrity Verification
    # =========================================================================

    integrity_hash: str = Field(
        ...,
        description=(
            "SHA256 hash of the artifact for integrity verification. "
            "Must be exactly 64 lowercase hexadecimal characters."
        ),
        min_length=64,
        max_length=64,
    )

    hash_algorithm: EnumHashAlgorithm = Field(
        default=EnumHashAlgorithm.SHA256,
        description=(
            "Hash algorithm used for integrity_hash. v1 supports only SHA256."
        ),
    )

    # =========================================================================
    # Signature Verification (Optional)
    # =========================================================================

    signature_reference: str | None = Field(
        default=None,
        description=(
            "Optional URI to detached signature file. When present, "
            "signature_algorithm must also be specified."
        ),
    )

    signature_algorithm: EnumSignatureAlgorithm | None = Field(
        default=None,
        description=(
            "Algorithm used for signature verification. Required if "
            "signature_reference is set. v1 supports only ED25519."
        ),
    )

    # =========================================================================
    # Sandbox Compatibility
    # =========================================================================

    sandbox_compatibility: ModelSandboxRequirements = Field(
        ...,
        description=(
            "Resource constraints and permissions required by this handler "
            "when running in a sandboxed environment."
        ),
    )

    # =========================================================================
    # Runtime Compatibility
    # =========================================================================

    min_runtime_version: ModelSemVer = Field(
        ...,
        description=(
            "Minimum ONEX runtime version required to run this handler. "
            "The runtime will reject handlers requiring newer versions."
        ),
    )

    max_runtime_version: ModelSemVer | None = Field(
        default=None,
        description=(
            "Optional maximum runtime version. Useful for handlers with known "
            "incompatibilities with newer runtime versions."
        ),
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("artifact_reference", mode="after")
    @classmethod
    def validate_artifact_reference_scheme(cls, value: str) -> str:
        """Validate artifact reference uses an allowed URI scheme."""
        if not _validate_artifact_reference(value):
            allowed = ", ".join(sorted(_ALLOWED_SCHEMES))
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid artifact_reference: '{value}'. "
                    f"Must use one of the allowed schemes: {allowed}. "
                    f"Raw local paths are not allowed for portability."
                ),
            )
        return value

    @field_validator("integrity_hash", mode="after")
    @classmethod
    def validate_integrity_hash_format(cls, value: str) -> str:
        """Validate integrity hash is valid SHA256 format."""
        if not EnumHashAlgorithm.SHA256.validate_hash(value):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid integrity_hash format. "
                    f"Expected 64 lowercase hexadecimal characters for SHA256. "
                    f"Got: '{value[:20]}...' (length={len(value)})"
                ),
            )
        return value

    @field_validator("hash_algorithm", mode="after")
    @classmethod
    def validate_hash_algorithm_v1(cls, value: EnumHashAlgorithm) -> EnumHashAlgorithm:
        """Validate hash algorithm is supported in v1."""
        if value != EnumHashAlgorithm.SHA256:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Unsupported hash_algorithm: {value.value}. "
                    f"v1 supports only SHA256."
                ),
            )
        return value

    @field_validator("signature_algorithm", mode="after")
    @classmethod
    def validate_signature_algorithm_v1(
        cls, value: EnumSignatureAlgorithm | None
    ) -> EnumSignatureAlgorithm | None:
        """Validate signature algorithm is supported in v1."""
        if value is not None and value != EnumSignatureAlgorithm.ED25519:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Unsupported signature_algorithm: {value.value}. "
                    f"v1 supports only ED25519."
                ),
            )
        return value

    @model_validator(mode="after")
    def validate_signature_consistency(self) -> "ModelHandlerPackaging":
        """Validate signature_reference and signature_algorithm are consistent."""
        has_ref = self.signature_reference is not None
        has_algo = self.signature_algorithm is not None

        if has_ref and not has_algo:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    "signature_algorithm is required when signature_reference is set. "
                    f"Got signature_reference='{self.signature_reference}' but "
                    f"signature_algorithm is None."
                ),
            )

        if has_algo and not has_ref:
            # Safe to access .value since has_algo ensures signature_algorithm is not None
            assert self.signature_algorithm is not None  # for type narrowing
            algo_value = self.signature_algorithm.value
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    "signature_reference is required when signature_algorithm is set. "
                    f"Got signature_algorithm={algo_value} but "
                    f"signature_reference is None."
                ),
            )

        return self

    @model_validator(mode="after")
    def validate_version_ordering(self) -> "ModelHandlerPackaging":
        """Validate min_runtime_version <= max_runtime_version if both set."""
        if self.max_runtime_version is not None:
            if self.min_runtime_version > self.max_runtime_version:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=(
                        f"min_runtime_version ({self.min_runtime_version}) must be "
                        f"<= max_runtime_version ({self.max_runtime_version})."
                    ),
                )
        return self

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        # Extract scheme for display
        for scheme in _ALLOWED_SCHEMES:
            if self.artifact_reference.startswith(scheme):
                scheme_name = scheme.rstrip(":/")
                break
        else:
            scheme_name = "unknown"

        parts = [f"scheme={scheme_name}"]
        parts.append(f"min_version={self.min_runtime_version}")
        if self.signature_reference:
            parts.append("signed=True")
        return f"ModelHandlerPackaging({', '.join(parts)})"


# Rebuild model to resolve forward references
ModelHandlerPackaging.model_rebuild()

__all__ = ["ModelHandlerPackaging"]
