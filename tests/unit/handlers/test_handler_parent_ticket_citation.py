# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""checker_parent_ticket_citation: a PR citing only a parent ticket is refused (OMN-21504).

T-Q1 of the factory plan. The parent-ticket list and the factory task-ticket
list are the ``dod_verify`` overlay: every case below builds its own fixture
overlay and changes it to move the verdict, so no ticket id is a module constant
of the checker.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_receipt_gate_exemption import EnumReceiptGateExemption
from omnibase_core.handlers.handler_parent_ticket_citation import (
    RULE_EXEMPTION_CITES_TASK_TICKET,
    RULE_PARENT_ONLY_CITATION,
    check_parent_ticket_citation,
)
from omnibase_core.models.validation.model_dod_verify_overlay import (
    ModelDodVerifyOverlay,
)
from omnibase_core.models.validation.model_parent_ticket_citation_facts import (
    ModelParentTicketCitationFacts,
)

pytestmark = pytest.mark.unit

PARENT = "OMN-21433"
TASK = "OMN-21504"
OTHER_TASK = "OMN-21505"


def _overlay(
    parents: tuple[str, ...] = (PARENT,), tasks: tuple[str, ...] = (TASK,)
) -> ModelDodVerifyOverlay:
    return ModelDodVerifyOverlay(parent_tickets=parents, factory_task_tickets=tasks)


def _facts(
    *cited: str, exemption: EnumReceiptGateExemption | None = None
) -> ModelParentTicketCitationFacts:
    return ModelParentTicketCitationFacts(cited_tickets=cited, exemption=exemption)


def test_a_pr_citing_only_the_parent_is_refused_naming_the_ticket() -> None:
    issues = check_parent_ticket_citation(_facts(PARENT), _overlay())
    assert [issue.code for issue in issues] == [RULE_PARENT_ONLY_CITATION]
    assert PARENT in issues[0].message


def test_control_a_pr_citing_a_task_ticket_is_not_refused() -> None:
    assert check_parent_ticket_citation(_facts(TASK), _overlay()) == ()


def test_a_pr_citing_the_parent_and_a_task_ticket_is_not_refused() -> None:
    assert check_parent_ticket_citation(_facts(PARENT, TASK), _overlay()) == ()


def test_every_cited_ticket_in_the_list_is_named() -> None:
    overlay = _overlay(parents=(PARENT, "OMN-21400"))
    issues = check_parent_ticket_citation(_facts(PARENT, "OMN-21400"), overlay)
    assert len(issues) == 1
    assert PARENT in issues[0].message and "OMN-21400" in issues[0].message


def test_a_pr_that_cites_no_ticket_is_not_this_checkers_business() -> None:
    # The gate's "Resolve the cited tickets" step owns the no-citation refusal.
    assert check_parent_ticket_citation(_facts(), _overlay()) == ()


def test_the_same_pr_is_refused_under_one_overlay_and_verified_under_another() -> None:
    facts = _facts(PARENT)
    refused = check_parent_ticket_citation(facts, _overlay(parents=(PARENT,)))
    verified = check_parent_ticket_citation(facts, _overlay(parents=("OMN-21400",)))
    assert [issue.code for issue in refused] == [RULE_PARENT_ONLY_CITATION]
    assert verified == ()


def test_an_empty_parent_list_refuses_nothing() -> None:
    assert check_parent_ticket_citation(_facts(PARENT), _overlay(parents=())) == ()


def test_the_list_is_the_overlays_and_not_the_checkers() -> None:
    # A ticket nobody hard-coded is refused the moment the overlay lists it.
    assert check_parent_ticket_citation(_facts("OMN-99999"), _overlay()) == ()
    refused = check_parent_ticket_citation(
        _facts("OMN-99999"), _overlay(parents=("OMN-99999",))
    )
    assert [issue.code for issue in refused] == [RULE_PARENT_ONLY_CITATION]


@pytest.mark.parametrize("exemption", list(EnumReceiptGateExemption))
def test_no_exemption_admits_a_pr_that_cites_a_factory_task_ticket(
    exemption: EnumReceiptGateExemption,
) -> None:
    issues = check_parent_ticket_citation(_facts(TASK, exemption=exemption), _overlay())
    assert [issue.code for issue in issues] == [RULE_EXEMPTION_CITES_TASK_TICKET]
    assert TASK in issues[0].message and exemption.value in issues[0].message


@pytest.mark.parametrize("exemption", list(EnumReceiptGateExemption))
def test_control_an_exemption_stands_when_no_factory_task_ticket_is_cited(
    exemption: EnumReceiptGateExemption,
) -> None:
    assert check_parent_ticket_citation(_facts(exemption=exemption), _overlay()) == ()
    assert (
        check_parent_ticket_citation(
            _facts(OTHER_TASK, exemption=exemption), _overlay(tasks=(TASK,))
        )
        == ()
    )


def test_the_exemption_verdict_moves_with_the_overlays_task_list() -> None:
    facts = _facts(OTHER_TASK, exemption=EnumReceiptGateExemption.DEPENDENCY_BOT)
    assert check_parent_ticket_citation(facts, _overlay(tasks=(TASK,))) == ()
    refused = check_parent_ticket_citation(facts, _overlay(tasks=(OTHER_TASK,)))
    assert [issue.code for issue in refused] == [RULE_EXEMPTION_CITES_TASK_TICKET]


def test_citation_is_compared_case_insensitively() -> None:
    issues = check_parent_ticket_citation(_facts("omn-21433"), _overlay())
    assert [issue.code for issue in issues] == [RULE_PARENT_ONLY_CITATION]


def test_models_are_frozen_and_forbid_extra_fields() -> None:
    facts = _facts(TASK)
    field = "cited_tickets"
    with pytest.raises(ValidationError):
        setattr(facts, field, ())
    with pytest.raises(ValidationError):
        ModelDodVerifyOverlay.model_validate(
            {"parent_tickets": (PARENT,), "unexpected": 1}
        )


@pytest.mark.parametrize("bad", ["21433", "OMN-", "OMN-12 34", "PROJ-1"])
def test_a_malformed_ticket_id_in_the_overlay_is_refused(bad: str) -> None:
    with pytest.raises(ValidationError):
        ModelDodVerifyOverlay(parent_tickets=(bad,))


def test_the_checker_module_does_no_io() -> None:
    # Bindings (AC5): the checker takes the PR's facts and reads nothing itself.
    import omnibase_core.handlers.handler_parent_ticket_citation as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not imported & {"os", "subprocess", "socket", "urllib", "requests", "yaml"}
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "open" not in called
    assert not any(
        isinstance(node, ast.Attribute) and node.attr in {"read_text", "open"}
        for node in ast.walk(tree)
    )
    assert not any(
        "protocol" in (alias.name.lower())
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ), "the checker depends on no protocol"
