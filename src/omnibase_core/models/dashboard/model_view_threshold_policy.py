# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A declared threshold policy for one mapped view field (OMN-21999).

The policy is the only place a view turns a number into a severity. Its bands are
declared, ordered and non-overlapping; a value that falls in no band is
out-of-band, and there is no default band to catch it. The evaluator is
``ModelViewThresholdPolicy.evaluate``.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_severity_verdict import ModelSeverityVerdict
from omnibase_core.models.dashboard.model_view_id_patterns import ViewId
from omnibase_core.models.dashboard.model_view_threshold_band import (
    ModelViewThresholdBand,
)
from omnibase_core.models.dashboard.model_view_threshold_out_of_band import (
    ModelViewThresholdOutOfBand,
)
from omnibase_core.models.dashboard.model_view_threshold_policy_pin import (
    ModelViewThresholdPolicyPin,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_canonical_hash import compute_canonical_hash

__all__ = ["ModelViewThresholdPolicy"]


class ModelViewThresholdPolicy(BaseModel):
    """Policy id, version, the mapped field it reads and its ordered bands.

    Bands are ordered by ascending lower edge. A band's upper edge may not pass
    the next band's lower edge; a gap between two bands is allowed, and a value
    in the gap is out-of-band.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    policy_id: ViewId = Field(..., description="Identifier of this policy")
    policy_version: ModelSemVer = Field(..., description="Version of this policy")
    mapped_field: str = Field(
        ...,
        pattern=r"^[A-Za-z_][A-Za-z0-9_.-]{0,127}$",
        description="Name of the mapped view field whose value this policy reads",
    )
    bands: tuple[ModelViewThresholdBand, ...] = Field(
        ..., min_length=1, description="Bands in ascending order of lower edge"
    )

    @model_validator(mode="after")
    def validate_bands_ordered_and_disjoint(self) -> Self:
        """Refuse bands that are unordered or overlap.

        Raises:
            ValueError: If a band's lower edge is not above the previous band's,
                or the previous band reaches past this band's lower edge.
        """
        for index in range(1, len(self.bands)):
            previous, current = self.bands[index - 1], self.bands[index]
            if current.lower_inclusive <= previous.lower_inclusive:
                raise ValueError(
                    f"bands must be in strictly ascending order of lower edge; "
                    f"band {index} starts at {current.lower_inclusive}, band "
                    f"{index - 1} at {previous.lower_inclusive}"
                )
            if (
                previous.upper_exclusive is None
                or previous.upper_exclusive > current.lower_inclusive
            ):
                raise ValueError(
                    f"bands {index - 1} and {index} overlap: band {index - 1} ends "
                    f"at {previous.upper_exclusive} (None is unbounded), band "
                    f"{index} starts at {current.lower_inclusive}"
                )
        return self

    def compute_digest(self) -> str:
        """Digest of the whole policy as ``sha256:<hex>``; any band change changes it."""
        return f"sha256:{compute_canonical_hash(self)}"

    def verify_pin(self, pin: ModelViewThresholdPolicyPin) -> None:
        """Refuse a reference whose id, version or digest is not this policy's.

        Pure: compares the reference with the digest computed from the bands.

        Raises:
            ModelOnexError: If the id, the version or the digest differs.
        """
        if pin.policy_id != self.policy_id:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"pinned policy_id '{pin.policy_id}' is not this policy "
                    f"'{self.policy_id}'"
                ),
            )
        if pin.policy_version != self.policy_version:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"pinned policy_version {pin.policy_version} is not this "
                    f"policy's {self.policy_version}"
                ),
            )
        computed = self.compute_digest()
        if pin.policy_digest != computed:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"pinned policy_digest {pin.policy_digest} differs from the "
                    f"computed digest {computed} for policy '{self.policy_id}'"
                ),
            )

    def evaluate(
        self, value: float
    ) -> ModelSeverityVerdict | ModelViewThresholdOutOfBand:
        """Return the verdict of the band holding ``value``, else the out-of-band outcome.

        Pure: no I/O, no clock, no default band. A band holds ``value`` when
        ``lower <= value < upper_exclusive`` (no upper edge when
        ``upper_exclusive`` is None); where two bands meet, a value on the shared
        edge belongs to the upper band. NaN compares false against every edge, so
        it is out-of-band. The verdict carries the policy id, version and digest;
        its ``status_value`` is the band's label, else the severity value.
        """
        digest = self.compute_digest()
        for band in self.bands:
            if value >= band.lower_inclusive and (
                band.upper_exclusive is None or value < band.upper_exclusive
            ):
                return ModelSeverityVerdict(
                    severity=band.severity,
                    status_value=band.threshold.label or band.severity.value,
                    policy_id=self.policy_id,
                    policy_version=self.policy_version,
                    policy_digest=digest,
                )
        return ModelViewThresholdOutOfBand(
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            policy_digest=digest,
            mapped_field=self.mapped_field,
            value=value,
        )
