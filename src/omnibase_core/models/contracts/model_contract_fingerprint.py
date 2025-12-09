"""Contract Fingerprint Model.

Represents a computed contract fingerprint with version and hash.

Format: `<semver>:<sha256-first-N-hex-chars>`
Example: `0.4.0:8fa1e2b4c9d1`

See: CONTRACT_STABILITY_SPEC.md for detailed specification.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_contract_version import ModelContractVersion
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelContractFingerprint(BaseModel):
    """Represents a computed contract fingerprint.

    Format: `<semver>:<sha256-first-N-hex-chars>`
    Example: `0.4.0:8fa1e2b4c9d1`

    The fingerprint combines semantic version for human context with
    cryptographic hash for integrity verification.
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
        validate_assignment=True,
    )

    def __str__(self) -> str:
        """Return fingerprint in canonical format: `<semver>:<hash_prefix>`."""
        return f"{self.version}:{self.hash_prefix}"

    def __eq__(self, other: object) -> bool:
        """Check equality based on version and hash prefix."""
        if isinstance(other, ModelContractFingerprint):
            return (
                self.version == other.version and self.hash_prefix == other.hash_prefix
            )
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented

    def __hash__(self) -> int:
        """Return hash for use in sets/dicts."""
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
        """
        if ":" not in fingerprint_str:
            raise ModelOnexError(
                message=f"Invalid fingerprint format: '{fingerprint_str}'. Expected '<semver>:<hash>'.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                fingerprint=fingerprint_str,
                expected_format="<semver>:<hash>",
            )

        # Split on first colon only (version may contain hyphens but not colons)
        parts = fingerprint_str.split(":", 1)
        if len(parts) != 2:
            raise ModelOnexError(
                message=f"Invalid fingerprint format: '{fingerprint_str}'. Expected exactly one colon separator.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                fingerprint=fingerprint_str,
            )

        version_str, hash_prefix = parts

        try:
            version = ModelContractVersion.from_string(version_str)
        except ModelOnexError as e:
            raise ModelOnexError(
                message=f"Invalid version in fingerprint: '{version_str}'.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                fingerprint=fingerprint_str,
                version_error=str(e),
            ) from e

        # Validate hash prefix format
        if not hash_prefix or not all(
            c in "0123456789abcdef" for c in hash_prefix.lower()
        ):
            raise ModelOnexError(
                message=f"Invalid hash prefix in fingerprint: '{hash_prefix}'. Must be hexadecimal.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                fingerprint=fingerprint_str,
                hash_prefix=hash_prefix,
            )

        # For parsed fingerprints, use hash_prefix as full_hash placeholder
        # (full hash not available from string representation)
        return cls(
            version=version,
            hash_prefix=hash_prefix.lower(),
            full_hash=hash_prefix.lower().ljust(64, "0"),  # Pad to 64 chars
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
