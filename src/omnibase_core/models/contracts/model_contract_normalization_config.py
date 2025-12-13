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

Hash Length Analysis:
    The default hash_length of 12 hex characters (48 bits) provides:

    - **~281 trillion possible values** (2^48 = 281,474,976,710,656)
    - **Birthday Paradox Analysis**: With N contracts, collision probability
      is approximately N^2 / (2 * 2^48). For example:
      - 1,000 contracts: ~0.0000002% collision chance
      - 10,000 contracts: ~0.00002% collision chance
      - 100,000 contracts: ~0.002% collision chance
    - **Practical Registry Size**: Most contract registries contain hundreds
      to low thousands of contracts, well within safe bounds.
    - **Human Readability**: 12 chars is short enough for copy/paste and
      visual inspection while long enough for uniqueness.

    For higher security requirements (e.g., multi-tenant registries with
    100k+ contracts), increase to 16 chars (64 bits) or higher.

Typical Usage:
    The configuration is typically used by fingerprint computation utilities:
    - Contract registration
    - Drift detection
    - Version comparison

See Also:
    CONTRACT_STABILITY_SPEC.md: Detailed specification for normalization rules.
    docs/conventions/NAMING_CONVENTIONS.md: Fingerprint format specification.
    scripts/README.md: Fingerprint tooling documentation.
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
        exclude_fields: Fields to exclude from normalization/hashing.
            Default: {"fingerprint", "correlation_id"} - fingerprint is excluded
            to prevent self-referential hashing; correlation_id is excluded because
            it's a runtime-generated UUID that shouldn't affect contract identity.

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
    exclude_fields: frozenset[str] = Field(
        default=frozenset({"fingerprint", "correlation_id"}),
        description=(
            "Fields to exclude from normalization/hashing. Default excludes 'fingerprint' "
            "(to prevent self-referential hashing where fingerprint value affects its own "
            "computation) and 'correlation_id' (runtime-generated UUID that changes per "
            "instantiation and shouldn't affect contract identity)."
        ),
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )
