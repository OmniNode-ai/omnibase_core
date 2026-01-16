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
    - https://...       - HTTPS URL (requires host and path)
    - file:///...       - Local file URL (absolute path, no host)
    - oci://...         - OCI container registry reference (requires host and path)
    - registry://...    - Internal registry reference (requires host and path)

File Scheme Notes:
    The file:// scheme uses RFC 8089 semantics with three slashes for absolute paths:
    - file:///path/to/file     - Correct: absolute path on local filesystem
    - file://localhost/path    - Not supported: use file:/// instead
    - file://./relative        - Invalid: relative paths not allowed
    - file:///                  - Invalid: path must be non-empty

    The three slashes consist of: scheme "file:" + "//" for authority + "/" for absolute path.
    Since we require no host (empty authority), file:/// is the correct format.

IP Address Literals:
    IP addresses are ALLOWED in the netloc (host) portion of URLs:
    - https://192.168.1.100:8080/path    - IPv4 address with port
    - oci://10.0.0.5:5000/org/handler    - IPv4 in OCI reference
    - registry://[2001:db8::1]:8443/path - IPv6 address (bracketed)

    Validation only checks URL structure, not IP format or reachability.
    Domain name format and DNS resolution are handled at runtime by the
    artifact fetcher.

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

from urllib.parse import urlparse

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
# Keys are scheme names, values are tuples of (requires_netloc, requires_path)
_SCHEME_REQUIREMENTS: dict[str, tuple[bool, bool]] = {
    "https": (True, True),  # Must have host and path: https://host/path
    "file": (False, True),  # No host, but must have path: file:///path
    "oci": (True, True),  # Must have registry and reference: oci://registry/image
    "registry": (True, True),  # Must have host and path: registry://host/path
}

# Derive allowed scheme prefixes from _SCHEME_REQUIREMENTS
# file:// uses three slashes (file:///), others use two (scheme://)
_ALLOWED_SCHEMES = frozenset(
    "file:///" if scheme == "file" else f"{scheme}://"
    for scheme in _SCHEME_REQUIREMENTS
)


def _validate_artifact_reference(reference: str) -> tuple[bool, str]:
    """
    Validate artifact reference uses an allowed URI scheme and has proper structure.

    Uses urllib.parse.urlparse() to validate URL structure including:
    - Scheme is one of: https, file, oci, registry
    - netloc (host) is present when required by scheme
    - path is present when required by scheme

    IP Address Literal Handling:
        IP address literals (e.g., 192.168.1.1, [::1]) are ALLOWED in the netloc
        (host) portion of URLs. This validation only checks that a netloc exists
        when required by the scheme; it does not validate the format or
        reachability of the host. IP addresses are valid hosts for artifact
        references, useful for:
        - Local development/testing with private registries
        - Air-gapped environments without DNS
        - Internal infrastructure with IP-based addressing

        Examples of valid URLs with IP addresses:
        - https://192.168.1.100:8080/artifacts/handler.whl
        - oci://10.0.0.5:5000/myorg/handler:v1.0.0
        - registry://[2001:db8::1]:8443/handlers/validator

        Domain name validation (format, TLD, etc.) is intentionally NOT performed
        here to keep this validation focused on URI structure. Domain/IP
        resolution and reachability checks are the responsibility of the artifact
        fetcher at runtime.

    Args:
        reference: Artifact reference string

    Returns:
        Tuple of (is_valid, error_message). If is_valid is True, error_message
        is empty. If is_valid is False, error_message describes the issue.

    Example:
        >>> _validate_artifact_reference("https://example.com/handler.whl")
        (True, "")
        >>> _validate_artifact_reference("https://")
        (False, "https:// URLs must include a host (netloc)")
    """
    # Fast prefix check before expensive URL parsing
    if not any(reference.startswith(scheme) for scheme in _ALLOWED_SCHEMES):
        return (False, "scheme_not_allowed")

    # Parse URL for structural validation
    parsed = urlparse(reference)
    scheme = parsed.scheme.lower()

    # Get requirements for this scheme
    requirements = _SCHEME_REQUIREMENTS.get(scheme)
    if requirements is None:
        return (False, f"Unknown scheme: {scheme}")

    requires_netloc, requires_path = requirements

    # Validate netloc (host) if required
    if requires_netloc and not parsed.netloc:
        return (False, f"{scheme}:// URLs must include a host (netloc)")

    # Validate path if required
    # Note: file:// URLs have the path in parsed.path (e.g., file:///opt/x -> path=/opt/x)
    # For https/oci/registry, path should be non-empty after the host
    if requires_path:
        if scheme == "file":
            # file:/// URLs: path must be non-empty (absolute path)
            if not parsed.path or parsed.path == "/":
                return (False, "file:/// URLs must include a path")
        # https/oci/registry: path must exist after host
        elif not parsed.path or parsed.path == "/":
            return (False, f"{scheme}:// URLs must include a path after the host")

    return (True, "")


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

    Public Key Distribution:
        When using signature verification (signature_reference + signature_algorithm),
        the runtime must have access to the public key to verify signatures. Public
        keys are distributed through one of these mechanisms:

        1. **Embedded in Runtime Configuration**: Public keys for trusted publishers
           are configured in the runtime's trust store (e.g., via YAML config or
           environment variables).

        2. **Key Discovery via Well-Known Endpoints**: The runtime can fetch public
           keys from well-known endpoints based on the artifact source (e.g.,
           https://keys.example.com/.well-known/onex-keys.json).

        3. **Registry-Provided Keys**: For oci:// and registry:// schemes, the
           container registry or handler registry may provide the public key as
           part of its metadata API.

        4. **Signature File Metadata**: The detached signature file (.sig) may
           include key ID/fingerprint hints that the runtime uses to look up the
           appropriate public key from its trust store.

        The public key is NOT embedded in this model to avoid key material bloat
        and to allow key rotation without updating all handler manifests. The
        signature_reference points to a detached signature file that the runtime
        verifies using the appropriate public key from its trust store.

    Attributes:
        artifact_reference: URI pointing to the handler artifact. Must use an
            explicit scheme (https://, file:///, oci://, registry://). Raw local
            paths are not allowed for portability. URLs must have proper structure
            including host (for https/oci/registry) and path.
        integrity_hash: SHA256 hash of the artifact (64 lowercase hex chars).
            Used to verify artifact integrity after download.
        hash_algorithm: Hash algorithm used for integrity_hash. v1 supports
            only SHA256.
        signature_reference: Optional URI to detached signature file for
            cryptographic verification. The signature is verified using the
            public key from the runtime's trust store (see Public Key Distribution).
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
            "Raw local paths (e.g., /path/to/file) are not allowed. "
            "IP address literals (IPv4 and IPv6) are allowed in the host portion. "
            "For file:// URLs, use three slashes (file:///path) for absolute paths; "
            "relative paths and hostnames are not supported."
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
        """Validate artifact reference uses an allowed URI scheme and structure.

        Validates:
        - Scheme is one of: https://, file:///, oci://, registry://
        - URL has proper structure (host and path where required)
        """
        is_valid, error_msg = _validate_artifact_reference(value)
        if not is_valid:
            if error_msg == "scheme_not_allowed":
                allowed = ", ".join(sorted(_ALLOWED_SCHEMES))
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=(
                        f"Invalid artifact_reference: '{value}'. "
                        f"Must use one of the allowed schemes: {allowed}. "
                        f"Raw local paths are not allowed for portability."
                    ),
                )
            # Structural validation error (missing host/path)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid artifact_reference structure: '{value}'. {error_msg}"
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
        # Check: signature_reference set but signature_algorithm missing
        if self.signature_reference is not None and self.signature_algorithm is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    "signature_algorithm is required when signature_reference is set. "
                    f"Got signature_reference='{self.signature_reference}' but "
                    f"signature_algorithm is None."
                ),
            )

        # Check: signature_algorithm set but signature_reference missing
        # Inline check allows mypy to narrow type without separate assert
        if self.signature_algorithm is not None and self.signature_reference is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    "signature_reference is required when signature_algorithm is set. "
                    f"Got signature_algorithm={self.signature_algorithm.value} but "
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
