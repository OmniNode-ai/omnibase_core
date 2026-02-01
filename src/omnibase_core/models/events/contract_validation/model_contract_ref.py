"""
Contract reference model for ONEX contract validation events.

Provides a lightweight reference to a contract that can be used in
validation events to identify which contract was validated or failed
validation, without embedding the full contract contents.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelContractRef"]


class ModelContractRef(BaseModel):
    """
    Lightweight reference to a contract for validation events.

    Used to identify contracts in validation success/failure events
    without embedding the full contract contents. Provides multiple
    identification strategies: stable ID, file path, content hash,
    and schema version.

    Thread Safety:
        This model is immutable (frozen=True) and thread-safe after instantiation.
        Instances can be safely shared across threads without synchronization.

    See Also:
        - docs/guides/THREADING.md for thread safety guidelines
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    contract_name: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for the contract",
    )
    path: Path | None = Field(
        default=None,
        description="Optional file path where the contract is located",
    )
    content_hash: str | None = Field(
        default=None,
        description="Optional hash of the contract content for integrity verification",
    )
    schema_version: ModelSemVer | None = Field(
        default=None,
        description="Optional semantic version of the contract schema",
    )
