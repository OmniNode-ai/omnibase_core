# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``ticket_create_route`` rule in the generic validator format (OMN-23770).

A direct Linear create (``issueCreate``) outside the ticket node's handler is refused; the same text
inside the handler, a docstring, a comment and a test file are admitted. The checker is pure; the validator
has no baseline, so a planted site fails on its first run. Every token, path pattern and text is a
``parameters`` entry of the rule row of ``ticket_create_route.validation.yaml``, and these tests load that
contract, so the values that gate the repository are the values under test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.validation.checker_ticket_create_route import (
    RULE_TICKET_CREATE_ROUTE,
    check_ticket_create_route,
)
from omnibase_core.validation.validator_ticket_create_route import (
    ValidatorTicketCreateRoute,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/ticket_create_route.validation.yaml"
)
_HANDLER_PATH = Path(
    "src/omnimarket/nodes/node_create_ticket/handlers/handler_create_ticket.py"
)
_ELSEWHERE = Path("src/omnimarket/nodes/node_other/handlers/handler_other.py")
_MUTATION = "mutation Create($input: IssueCreateInput!) { issueCreate(input: $input) { success } }"
_PLANTED = f'QUERY = """{_MUTATION}"""\n'
_PLANTED_FSTRING = (
    "def create(client, title):\n"
    '    return client.post(f"mutation {{ issueCreate(title: {title}) {{ success }} }}")\n'
)
_PLANTED_SHELL = f"curl -s -d '{_MUTATION}' https://api.linear.app/graphql\n"


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _rules(
    contract: ModelValidatorSubcontract | None = None,
) -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in (contract or _contract()).rules}


def _lines(path: Path, source: str) -> list[int]:
    return [
        i.line_number or 0 for i in check_ticket_create_route(path, source, _rules())
    ]


def test_ticket_create_route_planted_site_fails_outside_the_handler() -> None:
    assert _lines(_ELSEWHERE, _PLANTED) == [1]
    assert _lines(Path("src/pkg/adapters/linear.py"), _PLANTED_FSTRING) == [2]
    assert _lines(Path("scripts/file_ticket.sh"), _PLANTED_SHELL) == [1]


def test_ticket_create_route_planted_site_fails_in_the_validator_run(
    tmp_path: Path,
) -> None:
    target = tmp_path / "src/pkg/planted.py"
    target.parent.mkdir(parents=True)
    target.write_text(_PLANTED, encoding="utf-8")

    exit_code = main(
        ValidatorTicketCreateRoute,
        [str(target), "--report-json", str(tmp_path / "report.json")],
        build_validator_container,
    )

    assert exit_code == 1


def test_ticket_create_route_allowed_path_passes_inside_the_nodes_handler() -> None:
    assert _lines(_HANDLER_PATH, _PLANTED) == []
    assert (
        _lines(Path("nodes/node_create_ticket/handlers/handler_x.py"), _PLANTED) == []
    )


def test_ticket_create_route_allowed_path_passes_in_the_validator_run(
    tmp_path: Path,
) -> None:
    target = tmp_path / _HANDLER_PATH
    target.parent.mkdir(parents=True)
    target.write_text(_PLANTED, encoding="utf-8")

    exit_code = main(
        ValidatorTicketCreateRoute,
        [str(target), "--report-json", str(tmp_path / "report.json")],
        build_validator_container,
    )

    assert exit_code == 0


@pytest.mark.parametrize(
    "source",
    [
        '"""A note on issueCreate."""\n\nVALUE = 1\n',
        "# issueCreate is called by the node\nVALUE = 1\n",
        "def f() -> None:\n    '''issueCreate'''\n",
        "VALUE = 1\n",
        "def broken(:\n    issueCreate\n",
    ],
)
def test_ticket_create_route_admits_prose_and_unrelated_modules(source: str) -> None:
    assert _lines(_ELSEWHERE, source) == []


def test_ticket_create_route_admits_a_shell_comment() -> None:
    assert _lines(Path("scripts/note.sh"), "# issueCreate lives in the node\n") == []


def test_ticket_create_route_the_planted_site_and_its_handler_twin_differ_only_by_path() -> (
    None
):
    assert _lines(_ELSEWHERE, _PLANTED) == [1]
    assert _lines(_HANDLER_PATH, _PLANTED) == []


def test_ticket_create_route_the_contract_has_no_baseline_and_no_annotation() -> None:
    contract = _contract()
    assert [r.rule_id for r in contract.rules] == [RULE_TICKET_CREATE_ROUTE]
    parameters = _rules()[RULE_TICKET_CREATE_ROUTE].parameters or {}
    assert not any("baseline" in key or "annotation" in key for key in parameters)
    assert ValidatorTicketCreateRoute().validator_id == "ticket_create_route"


def test_ticket_create_route_mutating_the_token_changes_the_verdict() -> None:
    mutated = _contract()
    row = _rules(mutated)[RULE_TICKET_CREATE_ROUTE]
    assert row.parameters is not None
    row.parameters["create_tokens"] = ["somethingElse"]
    issues = check_ticket_create_route(_ELSEWHERE, _PLANTED, _rules(mutated))
    assert issues == ()


def test_ticket_create_route_a_missing_parameter_fails_the_load() -> None:
    broken = _contract()
    row = _rules(broken)[RULE_TICKET_CREATE_ROUTE]
    assert row.parameters is not None
    del row.parameters["allowed_path_patterns"]
    with pytest.raises(ModelOnexError):
        check_ticket_create_route(_ELSEWHERE, "", _rules(broken))
