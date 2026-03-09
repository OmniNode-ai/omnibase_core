# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelRequirement criterion-level proof linkage (OMN-4340)."""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_proof_kind import EnumProofKind
from omnibase_core.models.ticket.model_acceptance_criterion import (
    ModelAcceptanceCriterion,
)
from omnibase_core.models.ticket.model_proof_requirement import ModelProofRequirement
from omnibase_core.models.ticket.model_requirement import ModelRequirement


def _make_criterion(
    criterion_id: str, statement: str = "Some criterion"
) -> ModelAcceptanceCriterion:
    return ModelAcceptanceCriterion(id=criterion_id, statement=statement)


def _make_proof(
    criterion_id: str,
    kind: EnumProofKind = EnumProofKind.UNIT_TEST,
    ref: str = "tests/t.py::test_x",
) -> ModelProofRequirement:
    return ModelProofRequirement(criterion_id=criterion_id, kind=kind, ref=ref)


@pytest.mark.unit
def test_requirement_acceptance_default_empty() -> None:
    """acceptance and proof_requirements default to empty lists."""
    r = ModelRequirement(id="R1", statement="Some requirement")
    assert r.acceptance == []
    assert r.proof_requirements == []


@pytest.mark.unit
def test_is_proof_complete_no_criteria_returns_true() -> None:
    """is_proof_complete() is vacuously True when acceptance is empty."""
    r = ModelRequirement(id="R1", statement="s")
    assert r.is_proof_complete() is True


@pytest.mark.unit
def test_is_proof_complete_criterion_without_proof_returns_false() -> None:
    """is_proof_complete() returns False when a criterion has no proof."""
    r = ModelRequirement(
        id="R1",
        statement="s",
        acceptance=[_make_criterion("ac_1")],
    )
    assert r.is_proof_complete() is False


@pytest.mark.unit
def test_is_proof_complete_all_criteria_covered_returns_true() -> None:
    """is_proof_complete() returns True when all criteria have proofs."""
    r = ModelRequirement(
        id="R1",
        statement="s",
        acceptance=[_make_criterion("ac_1"), _make_criterion("ac_2")],
        proof_requirements=[
            _make_proof("ac_1"),
            _make_proof("ac_2"),
        ],
    )
    assert r.is_proof_complete() is True


@pytest.mark.unit
def test_is_proof_complete_partial_coverage_returns_false() -> None:
    """is_proof_complete() returns False when only some criteria have proofs."""
    r = ModelRequirement(
        id="R1",
        statement="s",
        acceptance=[_make_criterion("ac_1"), _make_criterion("ac_2")],
        proof_requirements=[_make_proof("ac_1")],
    )
    assert r.is_proof_complete() is False


@pytest.mark.unit
def test_duplicate_acceptance_ids_fail() -> None:
    """Duplicate acceptance criterion IDs raise a validation error."""
    with pytest.raises(Exception, match="Duplicate"):
        ModelRequirement(
            id="R1",
            statement="s",
            acceptance=[
                ModelAcceptanceCriterion(id="ac_1", statement="First"),
                ModelAcceptanceCriterion(id="ac_1", statement="Duplicate"),
            ],
        )


@pytest.mark.unit
def test_proof_with_unknown_criterion_id_fails() -> None:
    """A proof referencing an unknown criterion_id raises a validation error."""
    with pytest.raises(Exception, match="unknown criterion_id"):
        ModelRequirement(
            id="R1",
            statement="s",
            acceptance=[_make_criterion("ac_1")],
            proof_requirements=[_make_proof("ac_999")],
        )


@pytest.mark.unit
def test_is_machine_provable_false_when_all_manual() -> None:
    """is_machine_provable() is False when all proofs are MANUAL."""
    r = ModelRequirement(
        id="R1",
        statement="s",
        acceptance=[_make_criterion("ac_1")],
        proof_requirements=[
            _make_proof("ac_1", kind=EnumProofKind.MANUAL, ref="Verify manually"),
        ],
    )
    assert r.is_machine_provable() is False


@pytest.mark.unit
def test_is_machine_provable_true_when_at_least_one_non_manual() -> None:
    """is_machine_provable() is True when at least one proof is non-manual."""
    r = ModelRequirement(
        id="R1",
        statement="s",
        acceptance=[_make_criterion("ac_1"), _make_criterion("ac_2")],
        proof_requirements=[
            _make_proof("ac_1", kind=EnumProofKind.MANUAL, ref="Manual check"),
            _make_proof("ac_2", kind=EnumProofKind.UNIT_TEST),
        ],
    )
    assert r.is_machine_provable() is True


@pytest.mark.unit
def test_legacy_acceptance_string_coercion() -> None:
    """Legacy list[str] acceptance entries are coerced to ModelAcceptanceCriterion."""
    r = ModelRequirement(
        id="R1",
        statement="s",
        acceptance=["First criterion", "Second criterion"],  # type: ignore[list-item]
    )
    assert len(r.acceptance) == 2
    assert r.acceptance[0].id == "ac_1"
    assert r.acceptance[0].statement == "First criterion"
    assert r.acceptance[1].id == "ac_2"
    assert r.acceptance[1].statement == "Second criterion"
