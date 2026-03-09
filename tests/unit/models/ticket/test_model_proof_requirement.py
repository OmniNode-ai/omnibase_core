# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelProofRequirement and EnumProofKind (OMN-4339)."""

from __future__ import annotations

import pytest

from omnibase_core.models.ticket.model_proof_requirement import (
    EnumProofKind,
    ModelProofRequirement,
)


@pytest.mark.unit
def test_proof_kind_values() -> None:
    assert EnumProofKind.UNIT_TEST.value == "unit_test"
    assert EnumProofKind.INTEGRATION_TEST.value == "integration_test"
    assert EnumProofKind.STATIC_CHECK.value == "static_check"
    assert EnumProofKind.ARTIFACT.value == "artifact"
    assert EnumProofKind.MANUAL.value == "manual"


@pytest.mark.unit
def test_proof_links_to_criterion_id() -> None:
    p = ModelProofRequirement(
        criterion_id="ac_1",
        kind=EnumProofKind.UNIT_TEST,
        ref="tests/unit/test_reducer.py::test_invalid_transition",
    )
    assert p.criterion_id == "ac_1"
    assert p.kind == EnumProofKind.UNIT_TEST


@pytest.mark.unit
def test_proof_is_frozen() -> None:
    p = ModelProofRequirement(
        criterion_id="ac_1", kind=EnumProofKind.STATIC_CHECK, ref="no_any_types"
    )
    with pytest.raises(Exception):
        p.ref = "other"  # type: ignore[misc]


@pytest.mark.unit
def test_manual_is_not_machine_verifiable() -> None:
    p = ModelProofRequirement(
        criterion_id="ac_1",
        kind=EnumProofKind.MANUAL,
        ref="Verify end-to-end in staging",
    )
    assert p.is_machine_verifiable() is False


@pytest.mark.unit
def test_unit_test_is_machine_verifiable() -> None:
    p = ModelProofRequirement(
        criterion_id="ac_1",
        kind=EnumProofKind.UNIT_TEST,
        ref="tests/unit/test_foo.py::test_bar",
    )
    assert p.is_machine_verifiable() is True


@pytest.mark.unit
def test_criterion_id_must_be_nonempty() -> None:
    with pytest.raises(Exception):
        ModelProofRequirement(
            criterion_id="", kind=EnumProofKind.UNIT_TEST, ref="tests/t.py::t"
        )


@pytest.mark.unit
def test_ref_must_be_nonempty() -> None:
    with pytest.raises(Exception):
        ModelProofRequirement(criterion_id="ac_1", kind=EnumProofKind.UNIT_TEST, ref="")


@pytest.mark.unit
def test_whitespace_only_criterion_id_fails() -> None:
    with pytest.raises(Exception):
        ModelProofRequirement(
            criterion_id="   ", kind=EnumProofKind.UNIT_TEST, ref="tests/t.py::t"
        )
