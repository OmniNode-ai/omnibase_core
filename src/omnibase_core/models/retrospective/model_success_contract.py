# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Versioned success contract of one experiment, frozen before outcomes are read (OMN-21627)."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_experiment_slot import EnumExperimentSlot
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelSuccessContract(BaseModel):
    """Everything the evaluator needs to judge one experiment, or the gaps that block it.

    A value the approved configuration has not set stays ``None``; any ``None`` below
    blocks evaluation with ``CONTRACT_UNRESOLVED``. Values are never guessed.

    Attributes:
        experiment_id: The experiment.
        slot: Origin slot.
        contract_version: Version of this contract.
        evaluator_version: Evaluator version the contract was frozen against.
        frozen_at: When the contract was frozen, before treatment outcomes were read.
        cohort_floor: Minimum number of eligible due units.
        coverage_floor: Capture coverage needed to trust the measurement (0 to 1).
        baseline_rate: Primary-endpoint rate of the baseline snapshot.
        target_rate: Primary-endpoint rate the treatment must not exceed.
        coverage_target: Operational coverage target, distinct from the floor (0 to 1).
        maturity_hours: Hours after a unit is due before its outcome counts.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: UUID
    slot: EnumExperimentSlot
    contract_version: ModelSemVer
    evaluator_version: ModelSemVer
    frozen_at: AwareDatetime
    cohort_floor: int | None = Field(default=None, ge=1)
    coverage_floor: float | None = Field(default=None, ge=0.0, le=1.0)
    baseline_rate: float | None = Field(default=None, ge=0.0)
    target_rate: float | None = Field(default=None, ge=0.0)
    coverage_target: float | None = Field(default=None, ge=0.0, le=1.0)
    maturity_hours: int | None = Field(default=None, ge=0)

    def unresolved_fields(self) -> tuple[str, ...]:
        """Names of the contract values that are still unset, in declaration order."""
        return tuple(
            name
            for name in (
                "cohort_floor",
                "coverage_floor",
                "baseline_rate",
                "target_rate",
                "coverage_target",
                "maturity_hours",
            )
            if getattr(self, name) is None
        )
