"""
Contract Identity Model for Execution Manifest.

Defines the ModelContractIdentity model which captures the identity of the
contract that drove execution during a pipeline run. This is used by the
Execution Manifest to answer "what contract drove execution?".

This model captures identity and reference only - it does NOT embed full
contract payloads.

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelContractIdentity(BaseModel):
    """
    Identity of the contract that drove pipeline execution.

    This model captures the essential information about which contract
    was used to configure and drive the pipeline execution. It provides
    traceability without embedding the full contract payload.

    Attributes:
        contract_id: Unique identifier for the contract
        contract_path: Optional path to the contract file
        contract_version: Optional semantic version of the contract
        contract_hash: Optional SHA256 hash of the contract content
        schema_version: Optional schema version the contract conforms to
        profile_name: Optional execution profile name used

    Example:
        >>> identity = ModelContractIdentity(
        ...     contract_id="compute-text-transform-contract",
        ...     contract_path="contracts/text/transform.yaml",
        ...     profile_name="orchestrator_safe",
        ... )
        >>> identity.contract_id
        'compute-text-transform-contract'

    Note:
        This model captures identity and reference only. Full contract
        payloads should NOT be embedded - use contract_hash for integrity
        verification if needed.

    See Also:
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          The parent manifest model that uses this identity
        - :class:`~omnibase_core.models.contracts.model_contract_base.ModelContractBase`:
          The actual contract model

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    # === Required Identity Fields ===

    contract_id: str = Field(  # string-id-ok: user-facing identifier
        ...,
        min_length=1,
        description="Unique identifier for the contract",
    )

    # === Optional Identity Fields ===

    contract_path: str | None = Field(
        default=None,
        description="Path to the contract file (e.g., 'contracts/text/transform.yaml')",
    )

    contract_version: ModelSemVer | None = Field(
        default=None,
        description="Semantic version of the contract",
    )

    contract_hash: str | None = Field(
        default=None,
        description="SHA256 hash of the contract content for integrity verification",
    )

    schema_version: str | None = Field(
        default=None,
        description="Schema version the contract conforms to",
    )

    profile_name: str | None = Field(
        default=None,
        description="Execution profile name used (e.g., 'orchestrator_safe')",
    )

    # === Utility Methods ===

    def has_version(self) -> bool:
        """
        Check if contract version is specified.

        Returns:
            True if contract_version is set, False otherwise
        """
        return self.contract_version is not None

    def has_hash(self) -> bool:
        """
        Check if contract hash is specified.

        Returns:
            True if contract_hash is set, False otherwise
        """
        return self.contract_hash is not None

    def get_version_string(self) -> str | None:
        """
        Get the version as a string if available.

        Returns:
            Version string in SemVer format or None
        """
        if self.contract_version:
            return str(self.contract_version)
        return None

    def get_short_hash(self, length: int = 8) -> str | None:
        """
        Get a shortened version of the contract hash.

        Args:
            length: Number of characters to include (default 8)

        Returns:
            Shortened hash or None if no hash is set
        """
        if self.contract_hash:
            return self.contract_hash[:length]
        return None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        parts = [f"Contract({self.contract_id}"]
        if self.contract_version:
            parts.append(f"@{self.get_version_string()}")
        if self.profile_name:
            parts.append(f", profile={self.profile_name}")
        parts.append(")")
        return "".join(parts)

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelContractIdentity(contract_id={self.contract_id!r}, "
            f"contract_path={self.contract_path!r}, "
            f"contract_version={self.contract_version!r}, "
            f"profile_name={self.profile_name!r})"
        )


# Export for use
__all__ = ["ModelContractIdentity"]
