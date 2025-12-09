"""Contract Drift Detection Result Model.

Provides detailed information about differences between expected
and computed fingerprints, useful for debugging migration issues.

See: CONTRACT_STABILITY_SPEC.md for detailed specification.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_contract_fingerprint import (
    ModelContractFingerprint,
)
from omnibase_core.models.contracts.model_drift_details import ModelDriftDetails


class ModelDriftResult(BaseModel):
    """Result of drift detection between two contract versions.

    Provides detailed information about differences between expected
    and computed fingerprints, useful for debugging migration issues.
    """

    contract_name: str = Field(
        ...,
        description="Human-readable name of the contract being checked",
    )
    has_drift: bool = Field(
        ...,
        description="True if contract has drifted from registered fingerprint",
    )
    expected_fingerprint: ModelContractFingerprint | None = Field(
        default=None,
        description="Expected fingerprint from registry",
    )
    computed_fingerprint: ModelContractFingerprint | None = Field(
        default=None,
        description="Computed fingerprint from current contract",
    )
    drift_type: str | None = Field(
        default=None,
        description="Type of drift: 'version', 'content', 'both', or None",
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when drift was detected",
    )
    details: ModelDriftDetails = Field(
        default_factory=ModelDriftDetails,
        description="Additional details about the drift",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )


__all__ = ["ModelDriftResult"]
