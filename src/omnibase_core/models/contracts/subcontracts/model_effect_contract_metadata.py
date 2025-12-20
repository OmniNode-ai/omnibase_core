"""
Effect Contract Metadata Model.

Contract-level metadata for tooling, versioning, and RSD compatibility.
Enables contract diffing, migration tracking, ONEX introspection,
code generation, audit trails, and change history.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_effect_limits import EFFECT_AUTHOR_MAX_LENGTH

__all__ = ["ModelEffectContractMetadata"]


class ModelEffectContractMetadata(BaseModel):
    """
    Contract-level metadata for tooling, versioning, and RSD compatibility.

    Enables:
    - Contract diffing and migration tracking
    - ONEX introspection and code generation
    - Audit trails and change history
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract_id: UUID = Field(
        default_factory=uuid4, description="Stable contract identity"
    )
    revision: int = Field(default=1, ge=1, description="Monotonic revision number")
    created_at: str | None = Field(
        default=None, description="ISO-8601 creation timestamp"
    )
    updated_at: str | None = Field(
        default=None, description="ISO-8601 last update timestamp"
    )
    author: str | None = Field(default=None, max_length=EFFECT_AUTHOR_MAX_LENGTH)
    tags: list[str] = Field(default_factory=list, description="Searchable tags")

    # Contract hash for tooling and RSD
    contract_hash: str | None = Field(
        default=None,
        description=(
            "SHA256 hash of canonicalized contract for tooling support.\n\n"
            "Enables:\n"
            "- Contract diffing and migration detection\n"
            "- Audit trail verification\n"
            "- RSD experiment reproducibility\n"
            "- Cache invalidation\n\n"
            "Computed from sorted keys, normalized whitespace. "
            "If not provided, tooling may compute on load."
        ),
    )
