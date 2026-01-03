"""Contract Fingerprint Model.

This module provides the ModelContractFingerprint class for representing
computed contract fingerprints that combine semantic versioning with
cryptographic hashing for contract integrity verification.

Format: `<semver>:<sha256-first-N-hex-chars>`
Example: `0.4.0:8fa1e2b4c9d1`

The fingerprint serves two purposes:
    1. Version tracking: The semantic version provides human-readable context
       about the contract's compatibility level.
    2. Integrity verification: The hash prefix (from SHA256) ensures the
       contract content hasn't been modified unexpectedly.

Typical Usage:
    - Computed during contract registration to establish a baseline
    - Compared during drift detection to identify unauthorized changes
    - Stored in contract registries for versioned contract management

See Also:
    CONTRACT_STABILITY_SPEC.md: Detailed specification for fingerprint format
    and computation algorithm.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_contract_version import ModelContractVersion
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelContractFingerprint(BaseModel):
    """Represents a computed contract fingerprint for integrity verification.

    A contract fingerprint uniquely identifies a specific version and content
    of a contract. It combines semantic versioning for human-readable version
    tracking with a cryptographic hash for content integrity verification.

    Format: `<semver>:<sha256-first-N-hex-chars>`
    Example: `0.4.0:8fa1e2b4c9d1`

    The fingerprint is immutable (frozen) once created to ensure integrity
    throughout its lifecycle.

    Attributes:
        version: Semantic version of the contract (ModelContractVersion).
        hash_prefix: First N characters of the SHA256 hash (8-64 chars, lowercase hex).
        full_hash: Complete 64-character SHA256 hash for detailed comparison.
        computed_at: UTC timestamp when the fingerprint was computed.
        normalized_content: Optional normalized JSON content for debugging.

    Example:
        >>> from omnibase_core.models.contracts import ModelContractVersion
        >>> fingerprint = ModelContractFingerprint(
        ...     version=ModelContractVersion.from_string("1.0.0"),
        ...     hash_prefix="8fa1e2b4c9d1",
        ...     full_hash="8fa1e2b4c9d1" + "0" * 52,
        ... )
        >>> str(fingerprint)
        '1.0.0:8fa1e2b4c9d1'
    """

    version: ModelContractVersion = Field(
        ...,
        description="Semantic version of the contract",
    )
    hash_prefix: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r"^[a-f0-9]+$",
        description="Hexadecimal prefix of SHA256 hash (lowercase)",
    )
    full_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]+$",
        description="Full SHA256 hash for detailed comparison",
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when fingerprint was computed",
    )
    normalized_content: str | None = Field(
        default=None,
        description="Optional: normalized JSON content (for debugging)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,  # pytest-xdist compatibility
    )

    def __str__(self) -> str:
        """Return fingerprint in canonical string format.

        Returns:
            String in format `<semver>:<hash_prefix>`, e.g., '1.0.0:8fa1e2b4c9d1'.
        """
        return f"{self.version}:{self.hash_prefix}"

    def __eq__(self, other: object) -> bool:
        """Check equality based on version and hash prefix.

        Two fingerprints are equal if they have the same version and hash prefix.
        Also supports comparison with fingerprint strings.

        Args:
            other: Another ModelContractFingerprint or a fingerprint string.

        Returns:
            True if fingerprints match, False otherwise.
            NotImplemented if other is not a supported type.
        """
        if isinstance(other, ModelContractFingerprint):
            return (
                self.version == other.version and self.hash_prefix == other.hash_prefix
            )
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries.

        The hash is computed from the version string and hash prefix,
        ensuring consistent hashing for fingerprint objects.

        Returns:
            Integer hash value.
        """
        return hash((str(self.version), self.hash_prefix))

    @classmethod
    def from_string(cls, fingerprint_str: str) -> ModelContractFingerprint:
        """Parse a fingerprint string into a ModelContractFingerprint.

        Args:
            fingerprint_str: String in format `<semver>:<hash_prefix>`

        Returns:
            Parsed ModelContractFingerprint

        Raises:
            ModelOnexError: If format is invalid

        Note:
            Input validation is performed on all components (version format,
            hash prefix format, and length constraints). When parsing untrusted
            input in high-throughput scenarios, consider implementing rate
            limiting at the application layer to prevent resource exhaustion
            from malformed fingerprint strings.
        """
        if ":" not in fingerprint_str:
            raise ModelOnexError(
                message=f"Invalid fingerprint format: '{fingerprint_str}'. Expected '<semver>:<hash>'.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                fingerprint=fingerprint_str,
                expected_format="<semver>:<hash>",
            )

        # Split on first colon only (version may contain hyphens but not colons)
        # split(":", 1) always returns exactly 2 parts since we verified colon exists above
        version_str, hash_prefix = fingerprint_str.split(":", 1)

        try:
            version = ModelContractVersion.from_string(version_str)
        except ModelOnexError as e:
            raise ModelOnexError(
                message=f"Invalid version in fingerprint: '{version_str}'.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                fingerprint=fingerprint_str,
                version_error=str(e),
            ) from e

        # Validate hash prefix format (must be hexadecimal)
        if not hash_prefix or not all(
            c in "0123456789abcdef" for c in hash_prefix.lower()
        ):
            raise ModelOnexError(
                message=f"Invalid hash prefix in fingerprint: '{hash_prefix}'. Must be hexadecimal.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                fingerprint=fingerprint_str,
                hash_prefix=hash_prefix,
            )

        # Validate hash prefix length (8-64 characters as defined in model schema)
        if len(hash_prefix) < 8 or len(hash_prefix) > 64:
            raise ModelOnexError(
                message=f"Invalid hash prefix length: {len(hash_prefix)}. Must be between 8 and 64 characters.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                fingerprint=fingerprint_str,
                hash_prefix=hash_prefix,
                hash_prefix_length=len(hash_prefix),
            )

        # For parsed fingerprints, use hash_prefix as full_hash placeholder.
        # The full hash is not available from string representation (strings only
        # contain the prefix). This padded value is a synthetic placeholder - it
        # will NOT match any real computed hash. Use matches() for comparison,
        # which uses hash_prefix, not full_hash.
        return cls(
            version=version,
            hash_prefix=hash_prefix.lower(),
            full_hash=hash_prefix.lower().ljust(64, "0"),  # Synthetic placeholder
        )

    def matches(self, other: ModelContractFingerprint | str) -> bool:
        """Check if this fingerprint matches another.

        Args:
            other: Another fingerprint or fingerprint string to compare

        Returns:
            True if fingerprints match (same version and hash prefix)
        """
        if isinstance(other, str):
            try:
                other = ModelContractFingerprint.from_string(other)
            except ModelOnexError:
                return False
        return self.version == other.version and self.hash_prefix == other.hash_prefix
