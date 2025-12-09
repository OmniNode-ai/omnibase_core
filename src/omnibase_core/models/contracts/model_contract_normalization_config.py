"""Contract Normalization Configuration Model.

Controls how contracts are normalized before fingerprint computation.
Default settings ensure maximum compatibility and determinism.

See: CONTRACT_STABILITY_SPEC.md for detailed specification.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelContractNormalizationConfig(BaseModel):
    """Configuration for contract normalization pipeline.

    Controls how contracts are normalized before fingerprint computation.
    Default settings ensure maximum compatibility and determinism.
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
        validate_assignment=True,
    )
