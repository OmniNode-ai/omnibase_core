# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Correlated-readback receipt for the demand-aware liveness state machine.

OMN-15126 implementation of the OMN-14845 design
(``docs/design/2026-07-20-demand-aware-liveness-state-machine-design.md``,
omni_home#201, design §5). The receipt binds one input event id to one
terminal event id to one exact projection key/value (never a count) — this
is the structural fix for the false-green failure mode balanced topic
offsets cannot detect.

Per-state required-field enforcement follows the same pattern already
established by ``ModelProofPacket.enforce_tier_required_fields`` and
``ModelRuntimeAlivenessProbeReceipt._validate_status_failure_states``: a
receipt cannot declare a state without the fields that state's proof
requires, and cannot carry another state's discriminator fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_liveness_state import EnumLivenessState
from omnibase_core.models.runtime.model_event_ref import ModelEventRef
from omnibase_core.models.runtime.model_sampling_policy import ModelSamplingPolicy

__all__ = ["ModelLivenessReceipt"]

# Fields whose presence/absence is a per-state discriminator on
# ModelLivenessReceipt. Each entry lists the states for which the field MUST
# be non-None; for every other state the field MUST be None. Kept as a module
# constant (not inline in the validator) so the required-field policy is
# grep-able and testable, mirroring ModelProofPacket's ``_TIER_ADDED_FIELDS``.
_REQUIRED_FOR_STATES: dict[str, tuple[EnumLivenessState, ...]] = {
    "correlation_id": (EnumLivenessState.HEALTHY, EnumLivenessState.RED),
    "input_event_ref": (EnumLivenessState.HEALTHY, EnumLivenessState.RED),
    "projection_key_canonical": (EnumLivenessState.HEALTHY, EnumLivenessState.RED),
    "expected_value_predicate_result": (
        EnumLivenessState.HEALTHY,
        EnumLivenessState.RED,
    ),
    "checked_count": (EnumLivenessState.HEALTHY, EnumLivenessState.RED),
    "failed_count": (EnumLivenessState.HEALTHY, EnumLivenessState.RED),
    "failed_ratio": (EnumLivenessState.HEALTHY, EnumLivenessState.RED),
    "not_ready_reason": (EnumLivenessState.NOT_READY,),
    "demand_query_evidence": (EnumLivenessState.NO_DEMAND,),
    "failure_detail": (EnumLivenessState.RED,),
}
# terminal_event_ref, projection_expected_value_hash, projection_value_hash:
# required for HEALTHY only (a HEALTHY receipt without the exact observed
# projection value would prove nothing); permitted-but-not-required for RED
# ("None-with-reason"); forbidden elsewhere.
_REQUIRED_HEALTHY_ONLY: tuple[str, ...] = (
    "terminal_event_ref",
    "projection_expected_value_hash",
    "projection_value_hash",
)
_PERMITTED_FOR_RED: tuple[str, ...] = (
    "terminal_event_ref",
    "projection_expected_value_hash",
    "projection_value_hash",
)


class ModelLivenessReceipt(BaseModel):
    """Correlated-readback receipt: one liveness evaluation outcome (design §5).

    The receipt binds one input event id to one terminal event id to one
    exact projection key/value (never a count) — this is the structural fix
    for the false-green failure mode balanced topic offsets cannot detect.
    Topic high-watermark movement is retained only as supplemental telemetry
    on ``sampling_applied`` context, never as a ``state`` input.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    receipt_id: UUID
    surface_id: str = Field(..., min_length=1)
    state: EnumLivenessState

    correlation_id: UUID | None = Field(default=None)
    input_event_ref: ModelEventRef | None = Field(default=None)
    terminal_event_ref: ModelEventRef | None = Field(default=None)
    projection_key_canonical: str | None = Field(default=None, min_length=1)
    projection_value_hash: str | None = Field(default=None, min_length=1)
    projection_expected_value_hash: str | None = Field(default=None, min_length=1)
    expected_value_predicate_result: bool | None = Field(default=None)
    checked_count: int | None = Field(default=None, ge=0)
    failed_count: int | None = Field(default=None, ge=0)
    failed_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    sampling_applied: ModelSamplingPolicy | None = Field(default=None)

    lane: str = Field(..., min_length=1)
    deployed_sha: str = Field(..., min_length=1)
    image_digest: str = Field(..., min_length=1)
    config_digest: str = Field(..., min_length=1)
    evaluated_at: datetime
    freshness_window_seconds: int = Field(..., ge=1)
    runner: str = Field(..., min_length=1)
    independent_verifier: str | None = Field(default=None)
    demand_synthetic: bool = Field(default=False)

    not_ready_reason: str | None = Field(default=None, min_length=1)
    demand_query_evidence: str | None = Field(default=None, min_length=1)
    last_healthy_receipt_id: UUID | None = Field(default=None)
    last_healthy_at: datetime | None = Field(default=None)
    failure_detail: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_state_required_fields(self) -> Self:
        for field_name, required_states in _REQUIRED_FOR_STATES.items():
            value = getattr(self, field_name)
            if self.state in required_states:
                if value is None:
                    raise ValueError(  # error-ok: intentional receipt-shape rejection
                        f"state={self.state.value!r} requires non-None "
                        f"'{field_name}'; got None."
                    )
            elif value is not None:
                raise ValueError(  # error-ok: intentional receipt-shape rejection
                    f"'{field_name}' is only valid for states "
                    f"{[s.value for s in required_states]}; got state="
                    f"{self.state.value!r} with '{field_name}'={value!r}."
                )

        for field_name in _REQUIRED_HEALTHY_ONLY:
            value = getattr(self, field_name)
            if self.state == EnumLivenessState.HEALTHY and value is None:
                raise ValueError(  # error-ok: intentional receipt-shape rejection
                    f"state=HEALTHY requires non-None '{field_name}'; got None."
                )
            if (
                self.state != EnumLivenessState.HEALTHY
                and field_name not in _PERMITTED_FOR_RED
            ):
                if value is not None:
                    raise ValueError(  # error-ok: intentional receipt-shape rejection
                        f"'{field_name}' is only valid for state=HEALTHY; got "
                        f"state={self.state.value!r} with '{field_name}'={value!r}."
                    )
            if self.state not in (EnumLivenessState.HEALTHY, EnumLivenessState.RED):
                if value is not None:
                    raise ValueError(  # error-ok: intentional receipt-shape rejection
                        f"'{field_name}' is only valid for states "
                        f"['healthy', 'red']; got state={self.state.value!r} "
                        f"with '{field_name}'={value!r}."
                    )

        if self.state in (EnumLivenessState.HEALTHY, EnumLivenessState.RED):
            checked = self.checked_count
            failed = self.failed_count
            ratio = self.failed_ratio
            if checked is not None and checked == 0:
                raise ValueError(  # error-ok: intentional receipt-shape rejection
                    "checked_count must be >= 1 for state in (HEALTHY, RED) — "
                    "zero eligible items checked cannot produce either state "
                    "(design §3.2 step 3/4: zero eligible demand routes to "
                    "NO_DEMAND or STALE instead)."
                )
            if checked is not None and failed is not None and ratio is not None:
                expected_ratio = failed / checked
                if abs(expected_ratio - ratio) > 1e-9:
                    raise ValueError(  # error-ok: intentional receipt-shape rejection
                        f"failed_ratio={ratio!r} does not equal "
                        f"failed_count/checked_count={expected_ratio!r}."
                    )

        if self.state == EnumLivenessState.STALE:
            has_id = self.last_healthy_receipt_id is not None
            has_at = self.last_healthy_at is not None
            if has_id != has_at:
                raise ValueError(  # error-ok: intentional receipt-shape rejection
                    "last_healthy_receipt_id and last_healthy_at must be "
                    "provided together (or both omitted) for state=STALE; got "
                    f"last_healthy_receipt_id={self.last_healthy_receipt_id!r} "
                    f"last_healthy_at={self.last_healthy_at!r}."
                )
            if has_at:
                assert self.last_healthy_at is not None  # narrowed by has_at above
                age_seconds = (self.evaluated_at - self.last_healthy_at).total_seconds()
                if age_seconds <= self.freshness_window_seconds:
                    raise ValueError(  # error-ok: intentional receipt-shape rejection
                        "state=STALE contradicts a prior HEALTHY receipt still "
                        f"inside freshness_window_seconds={self.freshness_window_seconds}: "
                        f"age_seconds={age_seconds!r} — a fresh prior HEALTHY "
                        "reads NO_DEMAND, not STALE (design §3.2 step 4)."
                    )
        elif (
            self.last_healthy_receipt_id is not None or self.last_healthy_at is not None
        ):
            raise ValueError(  # error-ok: intentional receipt-shape rejection
                "last_healthy_receipt_id/last_healthy_at are only valid for "
                f"state=STALE; got state={self.state.value!r}."
            )

        return self
