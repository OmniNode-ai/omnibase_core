"""Contract Normalization Configuration Model.

This module provides configuration options for the contract normalization
pipeline, which prepares contracts for fingerprint computation by ensuring
deterministic, canonical representations.

Normalization Process:
    1. Default Resolution: Optional fields get their default values inserted
    2. Null Removal: None/null values are recursively removed
    3. Key Sorting: All dictionary keys are sorted alphabetically
    4. Compact Serialization: JSON output uses minimal whitespace
    5. Hash Computation: SHA256 hash is computed from normalized content

The default settings ensure maximum compatibility across different
environments and deterministic hash computation regardless of field
ordering in source files.

Typical Usage:
    The configuration is typically used by fingerprint computation utilities:
    - Contract registration
    - Drift detection
    - Version comparison

See Also:
    CONTRACT_STABILITY_SPEC.md: Detailed specification for normalization rules.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelContractNormalizationConfig(BaseModel):
    """Configuration for contract normalization pipeline.

    Controls how contracts are normalized before fingerprint computation to
    ensure consistent, deterministic hash values. The normalization process
    transforms contracts into a canonical form that is independent of:
    - Field ordering in source files
    - Optional field presence/absence
    - JSON formatting preferences

    This model is immutable (frozen) to prevent accidental modification
    during the normalization process.

    Attributes:
        resolve_defaults: Whether to insert default values for optional fields.
            Default: True (ensures consistent normalization regardless of input).
        remove_nulls: Whether to recursively remove None/null values.
            Default: True (null vs absent field should produce same hash).
        sort_keys: Whether to alphabetically sort all dictionary keys.
            Default: True (ensures key order doesn't affect hash).
        compact_json: Whether to use compact JSON (no whitespace).
            Default: True (whitespace doesn't affect semantics).
        hash_length: Number of hex characters from SHA256 to use (8-64).
            Default: 12 (48 bits, ~281 trillion possibilities - sufficient
            for collision avoidance in typical contract registries while
            keeping fingerprints readable).

    Example:
        >>> config = ModelContractNormalizationConfig(
        ...     hash_length=16,  # Use 16 hex chars instead of default 12
        ... )
        >>> config.resolve_defaults
        True
    """

    resolve_defaults: bool = Field(
        default=True,
        description="Insert default values for optional fields with defined defaults",
    )
    remove_nulls: bool = Field(
        default=True,
        description="Recursively remove None/null values from the contract",
    )
    sort_keys: bool = Field(
        default=True,
        description="Alphabetically sort all keys recursively for canonical ordering",
    )
    compact_json: bool = Field(
        default=True,
        description="Use compact JSON serialization (no whitespace)",
    )
    hash_length: int = Field(
        default=12,
        ge=8,
        le=64,
        description="Number of hex characters from SHA256 hash (default: 12)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,  # pytest-xdist compatibility
    )
