"""Contract Drift Detection Result Model.

This module provides the ModelDriftResult class, which encapsulates the
complete result of a drift detection operation, including both fingerprints
and detailed comparison information.

Drift Detection Workflow:
    1. Load expected fingerprint from contract registry
    2. Compute fingerprint from current contract content
    3. Compare fingerprints to detect drift
    4. Populate ModelDriftResult with comparison details

The result model is designed to provide all information needed for:
    - Automated CI/CD decision making (has_drift flag)
    - Human debugging (detailed fingerprint comparison)
    - Migration tooling (drift_type classification)

Drift Types:
    - 'version': Only the semantic version changed
    - 'content': Only the content hash changed
    - 'both': Both version and content changed
    - 'not_registered': Contract not found in registry
    - None: No drift detected

See Also:
    CONTRACT_STABILITY_SPEC.md: Detailed specification for drift detection.
    ModelDriftDetails: Nested model with granular drift information.
    ModelContractFingerprint: Fingerprint model used for comparison.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_contract_fingerprint import (
    ModelContractFingerprint,
)
from omnibase_core.models.contracts.model_drift_details import ModelDriftDetails

# Type alias for valid drift type values
DriftType = Literal[  # enum-ok: model type annotation
    "version", "content", "both", "not_registered"
]


class ModelDriftResult(BaseModel):
    """Result of drift detection between two contract versions.

    Encapsulates the complete result of comparing an expected contract
    fingerprint (from registry) with a computed fingerprint (from current
    contract content). Provides all information needed for debugging
    migration issues and making CI/CD decisions.

    This model is immutable (frozen) to ensure drift results remain
    consistent throughout the handling process.

    Attributes:
        contract_name: Human-readable identifier for the contract.
        has_drift: Primary flag indicating if drift was detected.
        expected_fingerprint: Fingerprint from the contract registry.
        computed_fingerprint: Fingerprint computed from current content.
        drift_type: Classification of drift ('version', 'content', 'both', None).
        detected_at: UTC timestamp when drift detection was performed.
        details: Detailed drift information (ModelDriftDetails).

    Example:
        >>> from omnibase_core.models.contracts import ModelDriftResult
        >>> result = ModelDriftResult(
        ...     contract_name="ModelContractCompute",
        ...     has_drift=True,
        ...     drift_type="content",
        ... )
        >>> result.has_drift
        True
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
    drift_type: DriftType | None = Field(
        default=None,
        description="Type of drift: 'version', 'content', 'both', 'not_registered', or None",
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
        from_attributes=True,  # pytest-xdist compatibility
    )


__all__ = ["DriftType", "ModelDriftDetails", "ModelDriftResult"]
