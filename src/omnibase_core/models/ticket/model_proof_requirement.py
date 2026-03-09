# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Proof requirement model with criterion_id FK and field validation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


class EnumProofKind(str, Enum):
    """Kind of proof reference in a ModelProofRequirement.

    Ref semantics by kind:
    - ``unit_test`` / ``integration_test``: pytest node ID
      (``path/to/test.py::test_function_name``)
    - ``static_check``: registered validator ID
      (see ``static_checks_registry.yaml``)
    - ``artifact``: file path relative to repo root
    - ``manual``: human-readable description — satisfies traceability only,
      NOT machine-verifiable proof
    """

    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    STATIC_CHECK = "static_check"
    ARTIFACT = "artifact"
    MANUAL = "manual"  # traceability only; not machine-verifiable


class ModelProofRequirement(BaseModel):
    """Links a single acceptance criterion (by id) to a machine-resolvable proof
    reference.

    ``criterion_id`` must match the ``id`` of a ``ModelAcceptanceCriterion`` in
    the same ``ModelRequirement``. Referential integrity is enforced at
    ``ModelRequirement`` level, not here.

    Immutability:
        This model uses ``frozen=True``, making instances immutable after
        creation. This enables safe sharing across threads without
        synchronisation.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    criterion_id: str
    kind: EnumProofKind
    ref: str
    description: str | None = None

    @field_validator("criterion_id", "ref")
    @classmethod
    def must_be_nonempty(cls, v: str) -> str:
        """Reject empty strings and whitespace-only values."""
        if not v.strip():
            raise ValueError("must be non-empty and not whitespace-only")
        return v

    def is_machine_verifiable(self) -> bool:
        """Return False for MANUAL proofs, True for all other kinds."""
        return self.kind != EnumProofKind.MANUAL


__all__ = ["EnumProofKind", "ModelProofRequirement"]
