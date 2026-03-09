# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Requirement model for ticket specification."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.ticket.model_acceptance_criterion import (
    ModelAcceptanceCriterion,
)
from omnibase_core.models.ticket.model_proof_requirement import ModelProofRequirement


class ModelRequirement(BaseModel):
    """A requirement for the ticket specification.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.

    Legacy format coercion:
        The ``acceptance`` field accepts both old ``list[str]`` format and
        new ``list[ModelAcceptanceCriterion]`` format. Old string entries are
        coerced to ``ModelAcceptanceCriterion`` via a Pydantic pre-validator.
        This handles the 54% of contracts (132/243) still using the old format
        (see OMN-4337 audit).

    Referential integrity:
        All ``criterion_id`` values in ``proof_requirements`` must reference
        an ``id`` in ``acceptance``. Duplicate ``acceptance`` IDs are rejected.
    """

    id: str = Field(..., description="Unique identifier for the requirement")
    statement: str = Field(..., description="The requirement statement")
    rationale: str | None = Field(
        default=None, description="Reasoning behind the requirement"
    )
    acceptance: list[ModelAcceptanceCriterion] = Field(
        default_factory=list, description="Acceptance criteria for the requirement"
    )
    proof_requirements: list[ModelProofRequirement] = Field(
        default_factory=list,
        description="Proof references linking criteria to machine-resolvable proofs",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @field_validator("acceptance", mode="before")
    @classmethod
    def coerce_legacy_acceptance(cls, v: Any) -> Any:
        """Accept old list[str] format alongside new list[ModelAcceptanceCriterion] format.

        Old format: ``acceptance: ["criterion text", ...]``
        New format: ``acceptance: [{id: "...", statement: "..."}]``

        String entries are assigned sequential IDs (``ac_1``, ``ac_2``, ...).
        """
        if not isinstance(v, list):
            return v
        coerced: list[Any] = []
        idx = 1
        for item in v:
            if isinstance(item, str):
                coerced.append({"id": f"ac_{idx}", "statement": item})
                idx += 1
            else:
                coerced.append(item)
                idx += 1
        return coerced

    @model_validator(mode="after")
    def validate_referential_integrity(self) -> ModelRequirement:
        """Enforce referential integrity between proof_requirements and acceptance.

        Rules:

        - Duplicate acceptance IDs are not allowed.
        - Every criterion_id in proof_requirements must reference a known acceptance ID.
        """
        acceptance_ids = [a.id for a in self.acceptance]

        # Reject duplicate criterion IDs
        if len(acceptance_ids) != len(set(acceptance_ids)):
            seen: set[str] = set()
            dupes = [aid for aid in acceptance_ids if aid in seen or seen.add(aid)]  # type: ignore[func-returns-value]
            raise ValueError(f"Duplicate acceptance criterion IDs: {dupes}")

        # All proof criterion_ids must reference an existing criterion
        known_ids = set(acceptance_ids)
        for proof in self.proof_requirements:
            if proof.criterion_id not in known_ids:
                raise ValueError(
                    f"proof_requirements references unknown criterion_id="
                    f"{proof.criterion_id!r}. Known IDs: {sorted(known_ids)}"
                )
        return self

    def is_proof_complete(self) -> bool:
        """True if every acceptance criterion has at least one proof reference.

        Returns True if acceptance is empty (vacuously true — no criteria to
        cover). Returns False if any criterion lacks a proof reference.
        """
        if not self.acceptance:
            return True
        covered = {p.criterion_id for p in self.proof_requirements}
        return {a.id for a in self.acceptance}.issubset(covered)

    def is_machine_provable(self) -> bool:
        """True if at least one proof reference is machine-verifiable.

        Returns True if acceptance is empty (vacuously true).
        Returns False if all proofs are MANUAL or there are no proofs.
        """
        if not self.acceptance:
            return True
        return any(p.is_machine_verifiable() for p in self.proof_requirements)


# Alias for cleaner imports
Requirement = ModelRequirement

__all__ = [
    "ModelRequirement",
    "Requirement",
]
