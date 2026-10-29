# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ValidatorParentTicketCitation: the ValidatorBase entry of the T-Q1 checker (OMN-21504).

The entry reads a PR-facts document (``*.pr_citation_facts.yaml``) and the
``dod_verify`` overlay document it names, then runs the pure checker. The
contract ``parent_ticket_citation.validation.yaml`` is loaded as a
``ModelValidatorSubcontract`` like every other generic validator.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.handlers.handler_parent_ticket_citation import (
    RULE_EXEMPTION_CITES_TASK_TICKET,
    RULE_PARENT_ONLY_CITATION,
)
from omnibase_core.handlers.handler_parent_ticket_citation_validator import (
    RULE_PR_CITATION_FACTS_INVALID,
    ValidatorParentTicketCitation,
)

pytestmark = pytest.mark.unit


def _overlay(path: Path, parents: str, tasks: str = "[OMN-21504]") -> Path:
    path.write_text(
        f"dod_verify:\n  parent_tickets: {parents}\n  factory_task_tickets: {tasks}\n",
        encoding="utf-8",
    )
    return path


def _facts(tmp_path: Path, cited: str, *, exemption: str | None = None) -> Path:
    lines = [f"cited_tickets: {cited}", "overlay: overlay.yaml"]
    if exemption:
        lines.append(f"exemption: {exemption}")
    path = tmp_path / "fixture.pr_citation_facts.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _codes(tmp_path: Path) -> list[str]:
    result = ValidatorParentTicketCitation().validate(tmp_path)
    return [issue.code or "" for issue in result.issues]


def test_the_contract_loads_as_a_validator_subcontract() -> None:
    contract = ValidatorParentTicketCitation().contract
    assert contract.validator_id == "parent_ticket_citation"
    assert {rule.rule_id for rule in contract.rules} == {
        RULE_PARENT_ONLY_CITATION,
        RULE_EXEMPTION_CITES_TASK_TICKET,
        RULE_PR_CITATION_FACTS_INVALID,
    }


def test_a_fixture_pr_citing_only_the_parent_is_refused(tmp_path: Path) -> None:
    _overlay(tmp_path / "overlay.yaml", "[OMN-21433]")
    _facts(tmp_path, "[OMN-21433]")
    result = ValidatorParentTicketCitation().validate(tmp_path)
    assert [issue.code for issue in result.issues] == [RULE_PARENT_ONLY_CITATION]
    assert "OMN-21433" in result.issues[0].message
    assert not result.is_valid


def test_control_a_fixture_pr_citing_a_task_ticket_passes(tmp_path: Path) -> None:
    _overlay(tmp_path / "overlay.yaml", "[OMN-21433]")
    _facts(tmp_path, "[OMN-21504]")
    assert _codes(tmp_path) == []
    assert ValidatorParentTicketCitation().validate(tmp_path).is_valid


def test_the_same_pr_is_verified_under_an_overlay_that_omits_the_ticket(
    tmp_path: Path,
) -> None:
    _facts(tmp_path, "[OMN-21433]")
    _overlay(tmp_path / "overlay.yaml", "[OMN-21433]")
    assert _codes(tmp_path) == [RULE_PARENT_ONLY_CITATION]
    _overlay(tmp_path / "overlay.yaml", "[OMN-21400]")
    assert _codes(tmp_path) == []


@pytest.mark.parametrize(
    "exemption", ["dependency_bot", "writer_app_pin_only", "docs_only_zone"]
)
def test_an_exemption_citing_a_task_ticket_is_refused(
    tmp_path: Path, exemption: str
) -> None:
    _overlay(tmp_path / "overlay.yaml", "[OMN-21433]")
    _facts(tmp_path, "[OMN-21504]", exemption=exemption)
    assert _codes(tmp_path) == [RULE_EXEMPTION_CITES_TASK_TICKET]


@pytest.mark.parametrize(
    "facts_body",
    [
        "cited_tickets: not-a-list\noverlay: overlay.yaml\n",
        "cited_tickets: [OMN-1]\noverlay: missing.yaml\n",
        "cited_tickets: [OMN-1]\n",
        "cited_tickets: [OMN-1]\noverlay: overlay.yaml\nexemption: unknown_kind\n",
        "cited_tickets: [OMN-1]\noverlay: overlay.yaml\nsurprise: 1\n",
    ],
)
def test_unreadable_facts_fail_closed(tmp_path: Path, facts_body: str) -> None:
    _overlay(tmp_path / "overlay.yaml", "[OMN-21433]")
    (tmp_path / "bad.pr_citation_facts.yaml").write_text(facts_body, encoding="utf-8")
    assert _codes(tmp_path) == [RULE_PR_CITATION_FACTS_INVALID]


def test_an_overlay_without_a_dod_verify_section_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "overlay.yaml").write_text("other: {}\n", encoding="utf-8")
    _facts(tmp_path, "[OMN-21433]")
    assert _codes(tmp_path) == [RULE_PR_CITATION_FACTS_INVALID]
