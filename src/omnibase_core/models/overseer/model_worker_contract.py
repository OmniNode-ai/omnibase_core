# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelWorkerContract — per-worker machine-readable contract (OMN-10251).

Wire type loaded at worker spawn time from contract.yaml. Parallel to
ModelOvernightContract (session-level) and ModelSessionContract (pipeline-level).
"""

from __future__ import annotations

import re as _re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.functional_validators import AfterValidator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.overseer.model_worker_evidence_requirement import (
    ModelWorkerEvidenceRequirement,
)


def _validate_semver(v: str) -> str:
    if not _re.fullmatch(r"\d+\.\d+\.\d+", v):
        raise ModelOnexError(
            message=f"schema_version must match x.y.z, got {v!r}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return v


_SemVer = Annotated[str, AfterValidator(_validate_semver)]


class ModelWorkerContract(BaseModel):
    """Per-worker machine-readable contract.

    Loaded at worker spawn time from a contract.yaml beside the worker
    definition. All fields are immutable (frozen=True) and unknown fields are
    rejected (extra="forbid").
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: _SemVer = "1.0.0"
    worker_name: str

    heartbeat_interval_seconds: int = Field(
        default=300,
        gt=0,
        description="Max silence (no TaskUpdate or SendMessage) before stall fires.",
    )
    stall_action: Literal["kill_and_respawn", "kill_only", "warn_only"] = (
        "kill_and_respawn"
    )

    required_evidence: Mapping[str, tuple[ModelWorkerEvidenceRequirement, ...]] = Field(
        default_factory=lambda: MappingProxyType({}),
        description=(
            "Map from TaskUpdate status transition (e.g. 'completed', "
            "'in_progress') to the list of evidence requirements that must "
            "be satisfied on the TaskUpdate body."
        ),
    )

    @field_validator("required_evidence", mode="before")
    @classmethod
    def _freeze_required_evidence(
        cls, value: Any
    ) -> Mapping[str, tuple[ModelWorkerEvidenceRequirement, ...]]:
        if value is None:
            return MappingProxyType({})
        if not isinstance(value, Mapping):
            raise ModelOnexError(
                message="required_evidence must be a mapping",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        coerced: dict[str, tuple[ModelWorkerEvidenceRequirement, ...]] = {}
        for k, v in value.items():
            if not isinstance(v, (list, tuple)):
                raise ModelOnexError(
                    message=f"required_evidence[{k!r}] must be a list, got {type(v).__name__}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            items: list[ModelWorkerEvidenceRequirement] = []
            for item in v:
                if isinstance(item, ModelWorkerEvidenceRequirement):
                    items.append(item)
                elif isinstance(item, dict):
                    items.append(ModelWorkerEvidenceRequirement.model_validate(item))
                else:
                    raise ModelOnexError(
                        message=(
                            f"required_evidence[{k!r}] items must be dicts or "
                            f"ModelWorkerEvidenceRequirement, got {type(item).__name__}"
                        ),
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    )
            coerced[k] = tuple(items)
        return MappingProxyType(coerced)

    allowed_skills: tuple[str, ...] | Literal["*"] = Field(
        default="*",
        description=(
            "Skill slugs this worker may invoke via the Skill tool. '*' "
            "means no restriction. An empty tuple means no skills allowed."
        ),
    )
    allowed_tools: tuple[str, ...] | Literal["*"] = Field(
        default="*",
        description=(
            "Tool names this worker may invoke. '*' means no restriction. "
            "An empty tuple means no tools allowed (unusual)."
        ),
    )

    applicable_runbooks: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "Runbook slugs the overseer should match against observed "
            "events for this worker."
        ),
    )
    preflight_gates: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "Preflight check names that must pass before the worker's first tool call."
        ),
    )

    snapshot_on_tick: bool = Field(
        default=False,
        description="If true, HandlerOvernight writes a state snapshot for this worker on every tick.",
    )
    lease_seconds: int = Field(
        default=900,
        gt=0,
        description="Claim lease duration for task ownership.",
    )


def load_worker_contract(data: Any) -> ModelWorkerContract:
    """Validate a ModelWorkerContract from an already-parsed mapping."""
    if not isinstance(data, Mapping):
        raise ModelOnexError(
            message=f"worker contract data must be a mapping, got {type(data).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return ModelWorkerContract.model_validate(dict(data))


__all__ = [
    "ModelWorkerContract",
    "load_worker_contract",
]
