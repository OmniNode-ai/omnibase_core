# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-22969 AC2: a ticket contract without the integration item is refused, and
the completion predicate is one function.

The ticket validator this criterion first named was deleted by OMN-23780. The
integration-item rule now lives in ``ModelTicketContract`` (OMN-23758), so the
refusal is exercised through the model's YAML entry point, the way a contract
file is read. The completion half checks that ``is_ticket_complete`` is the one
definition and that ``ModelTicketContract.is_done`` answers through it.
"""

from __future__ import annotations

import ast
import copy
import itertools
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket import EnumTicketPhase
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.ticket.model_ticket_completion_predicate import (
    is_ticket_complete,
)
from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

INTEGRATION_RULE = "DOD_EVIDENCE_INTEGRATION_ITEM_MISSING"

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "ticket_standard_form"
    / "ticket_contract_1_1_0.yaml"
)
_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "omnibase_core"


def _fixture_data() -> dict:
    """The 1.1.0 fixture as plain data, freshly parsed for each test."""
    return copy.deepcopy(yaml.safe_load(_FIXTURE.read_text(encoding="utf-8")))


def _validate(data: dict) -> ModelTicketContract:
    return ModelTicketContract.from_yaml(yaml.safe_dump(data, sort_keys=False))


@pytest.mark.unit
def test_contract_with_the_integration_item_is_accepted() -> None:
    """The positive control: the fixture, integration item intact, validates."""
    contract = _validate(_fixture_data())
    assert contract.schema_version == "1.1.0"
    assert any(
        check.check_type == "endpoint"
        for item in contract.dod_evidence
        for check in item.checks
    )


@pytest.mark.unit
def test_contract_without_the_integration_item_is_refused() -> None:
    """Swapping the integration check for a unit check makes the contract refused."""
    data = _fixture_data()
    data["dod_evidence"][1]["checks"] = [
        {"check_type": "test_passes", "check_value": "tests/x.py", "cwd": None}
    ]
    with pytest.raises(ModelOnexError, match=INTEGRATION_RULE):
        _validate(data)


@pytest.mark.unit
def test_contract_with_the_integration_item_dropped_is_refused() -> None:
    """Dropping the dod_evidence item bound to the integrated criterion is refused."""
    data = _fixture_data()
    data["dod_evidence"] = [data["dod_evidence"][0]]
    with pytest.raises(ModelOnexError, match=INTEGRATION_RULE):
        _validate(data)


@pytest.mark.unit
def test_integration_item_bound_to_the_wrong_criterion_is_refused() -> None:
    """An integration check that is not bound to the integrated criterion does not count."""
    data = _fixture_data()
    data["dod_evidence"][1]["binds_ac"] = ["AC1"]
    with pytest.raises(ModelOnexError, match=INTEGRATION_RULE):
        _validate(data)


@pytest.mark.unit
@pytest.mark.parametrize(
    "flags",
    list(itertools.product([True, False], repeat=5)),
)
def test_completion_predicate_is_true_only_when_every_input_is(
    flags: tuple[bool, bool, bool, bool, bool],
) -> None:
    """The predicate is the conjunction of its five inputs."""
    phase_done, questions, spec, verification, gates = flags
    assert is_ticket_complete(
        phase_done=phase_done,
        questions_complete=questions,
        spec_complete=spec,
        verification_complete=verification,
        gates_complete=gates,
    ) is all(flags)


@pytest.mark.unit
def test_completion_predicate_is_defined_once() -> None:
    """Exactly one ``def is_ticket_complete`` exists in core."""
    defs = [
        path.relative_to(_SRC_ROOT).as_posix()
        for path in sorted(_SRC_ROOT.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef) and node.name == "is_ticket_complete"
    ]
    assert defs == ["models/ticket/model_ticket_completion_predicate.py"]


@pytest.mark.unit
def test_ticket_contract_is_done_answers_through_the_predicate() -> None:
    """A contract not in phase DONE is not done; the phase flips only the phase input."""
    contract = _validate(_fixture_data())
    assert contract.phase != EnumTicketPhase.DONE
    assert contract.is_done() is False
    done = contract.model_copy(update={"phase": EnumTicketPhase.DONE})
    assert done.is_done() is is_ticket_complete(
        phase_done=True,
        questions_complete=done.is_questions_complete(),
        spec_complete=done.is_spec_complete(),
        verification_complete=done.is_verification_complete(),
        gates_complete=done.is_gates_complete(),
    )
