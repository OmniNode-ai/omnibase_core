# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Inventory and ratchet for the ticket, definition-of-done and completion models.

OMN-22969. The ticket model, the DoD item models and the completion predicate
are listed here from a scan of ``src/omnibase_core``. A second ``ModelTicketContract``
definition, or any path the scan finds that this inventory does not list, fails.

The scan discovers model classes by name pattern (``Ticket`` or a DoD item) and
``is_done`` methods by definition, not from this inventory, so a class or a
completion method nobody listed is found. Every discovered class is either a
ticket model or a DoD item model (``INVENTORY_CLASSES``) or is named as neither
(``EXCLUDED_CLASSES``); every ``is_done`` is either a ticket completion that
returns ``is_ticket_complete`` (``INVENTORY_COMPLETION_CALLERS``) or is named as
another policy (``OTHER_IS_DONE``). Ticket creation paths are not scanned.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "omnibase_core"

CANONICAL_TICKET_MODEL = "ModelTicketContract"
CANONICAL_TICKET_MODEL_PATH = "models/ticket/model_ticket_contract.py"
COMPLETION_PREDICATE_PATH = "models/ticket/model_ticket_completion_predicate.py"

# A class whose name carries ``Ticket`` or is a DoD item is a candidate; the
# scan does not take its names from the inventory below.
TICKET_MODEL_PATTERN = re.compile(r"^Model\w*(Ticket|Do[dD]\w*Item)")

# Every class the scan treats as a ticket model or a DoD item model: path -> role.
# ``flagged`` rows are known second definitions or duplicates awaiting their
# cross-repo migration; the scan lists them and the ratchet pins them.
INVENTORY_CLASSES: dict[tuple[str, str], str] = {
    (
        "models/ticket/model_ticket_contract.py",
        "ModelTicketContract",
    ): "canonical ticket model",
    (
        "models/ticket/model_ticket_workflow_state.py",
        "ModelTicketWorkflowState",
    ): "workflow FSM state, distinct from the contract",
    (
        "models/ticket/model_ticket_business_brief.py",
        "ModelTicketBusinessBrief",
    ): "the five-heading business brief embedded in the canonical ticket model",
    (
        "models/ticket/model_ticket_standard_form_fields.py",
        "ModelTicketStandardFormFields",
    ): "the schema 1.1.0 fields the canonical ticket model inherits",
    (
        "models/ticket/model_ticket_draft.py",
        "ModelTicketDraft",
    ): "the canonical ticket model before the tracker assigns an id (from_draft)",
    (
        "models/ticket/model_contract_dod_item.py",
        "ModelContractDodItem",
    ): "DoD item embedded in the canonical ticket model",
    (
        "models/contracts/ticket/model_dod_evidence_item.py",
        "ModelDodEvidenceItem",
    ): "FLAGGED duplicate DoD item: receipt-gate path, migrates to ModelContractDodItem",
    (
        "models/plan/model_dod_item.py",
        "ModelDoDItem",
    ): "FLAGGED duplicate DoD item: flat plan success criterion",
}
# Classes the name pattern finds that are neither a ticket model nor a DoD item model.
EXCLUDED_CLASSES: dict[tuple[str, str], str] = {
    (
        "models/epic/model_epic_ticket_status.py",
        "ModelEpicTicketStatus",
    ): "status of one ticket within an epic execution",
    (
        "models/ticket_creation/model_ticket_creation_check_result.py",
        "ModelTicketCreationCheckResult",
    ): "result of the ticket-creation gate",
    (
        "models/ticket_creation/model_ticket_creation_finding.py",
        "ModelTicketCreationFinding",
    ): "one refusal of the ticket-creation gate",
    (
        "models/ticket_creation/model_ticket_creation_document.py",
        "ModelTicketCreationDocument",
    ): "payload the ticket-creation gate checks",
    (
        "models/plan/model_plan_ticket_link.py",
        "ModelPlanTicketLink",
    ): "link from a plan entry to a ticket",
    (
        "models/governance/model_dod_sweep_ticket_result.py",
        "ModelDodSweepTicketResult",
    ): "DoD sweep result for one ticket",
    (
        "models/ticket/model_ticket_context_bundle.py",
        "ModelTicketContextBundle",
    ): "context bundle assembled for a ticket",
    (
        "models/demo/model_validate/model_support_ticket.py",
        "ModelSupportTicket",
    ): "customer support ticket demo input",
    (
        "models/scope/model_ticket_filter.py",
        "ModelTicketFilter",
    ): "predicate filter over tickets",
    (
        "models/nodes/sprint_roll/model_sprint_ticket.py",
        "ModelSprintTicket",
    ): "placement facts of a ticket for sprint roll",
}
# Every ``is_done`` in a ticket model: (path, class), each must return the one predicate.
INVENTORY_COMPLETION_CALLERS: frozenset[tuple[str, str]] = frozenset(
    {
        ("models/ticket/model_ticket_contract.py", "ModelTicketContract"),
        ("models/ticket/model_ticket_workflow_state.py", "ModelTicketWorkflowState"),
    }
)
# Every other ``is_done`` in core: not a ticket completion, so not the shared policy.
OTHER_IS_DONE: dict[tuple[str, str], str] = {
    (
        "models/plan/model_plan_contract.py",
        "ModelPlanContract",
    ): "plan lifecycle terminal state",
    (
        "models/governance/model_dod_eval_verdict.py",
        "ModelDodEvalVerdict",
    ): "DoD verification verdict outcome",
}


def scan_classes(root: Path) -> dict[tuple[str, str], int]:
    """Return (relative path, class name) -> count for every class the pattern finds."""
    found: dict[tuple[str, str], int] = {}
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and TICKET_MODEL_PATTERN.match(node.name):
                found[(rel, node.name)] = found.get((rel, node.name), 0) + 1
    return found


def second_definitions(found: dict[tuple[str, str], int]) -> list[str]:
    """List every ModelTicketContract definition other than the canonical one."""
    return sorted(
        f"{rel}:{name}"
        for (rel, name) in found
        if name == CANONICAL_TICKET_MODEL and rel != CANONICAL_TICKET_MODEL_PATH
    )


def _returns_shared_predicate(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the body, past its docstring, is only ``return is_ticket_complete(...)``."""
    body = list(func.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return False
    value = body[0].value
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "is_ticket_complete"
    )


def scan_is_done(root: Path) -> dict[tuple[str, str], list[bool]]:
    """Return (relative path, class name) -> one flag per ``is_done`` definition.

    The flag says whether that definition returns ``is_ticket_complete`` and
    nothing else. Every ``is_done`` is found, whether or not it mentions the
    predicate; a module-level one has the empty class name.
    """
    found: dict[tuple[str, str], list[bool]] = {}
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(root).as_posix()
        scopes: list[tuple[str, ast.AST]] = [("", tree)]
        scopes.extend(
            (node.name, node)
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        )
        for class_name, scope in scopes:
            for node in ast.iter_child_nodes(scope):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "is_done"
                ):
                    found.setdefault((rel, class_name), []).append(
                        _returns_shared_predicate(node)
                    )
    return found


def completion_problems(found: dict[tuple[str, str], list[bool]]) -> list[str]:
    """List every ``is_done`` that is unlisted, duplicated or not the shared policy."""
    listed = INVENTORY_COMPLETION_CALLERS | set(OTHER_IS_DONE)
    problems = [
        f"unlisted is_done: {rel}:{cls}" for (rel, cls) in sorted(set(found) - listed)
    ]
    problems += [
        f"stale is_done entry: {rel}:{cls}"
        for (rel, cls) in sorted(listed - set(found))
    ]
    problems += [
        f"{len(flags)} is_done definitions: {rel}:{cls}"
        for (rel, cls), flags in sorted(found.items())
        if len(flags) != 1
    ]
    problems += [
        f"is_done does not return is_ticket_complete: {rel}:{cls}"
        for (rel, cls) in sorted(INVENTORY_COMPLETION_CALLERS & set(found))
        if found[(rel, cls)] != [True]
    ]
    return problems


@pytest.mark.unit
def test_every_path_listed() -> None:
    """Every ticket model class the scan finds is in the inventory, and back."""
    found = scan_classes(SRC_ROOT)
    listed = set(INVENTORY_CLASSES) | set(EXCLUDED_CLASSES)
    assert not set(INVENTORY_CLASSES) & set(EXCLUDED_CLASSES)
    assert set(found) == listed, (
        f"unlisted: {sorted(set(found) - listed)}; stale: {sorted(listed - set(found))}"
    )
    assert all(count == 1 for count in found.values())
    assert (SRC_ROOT / COMPLETION_PREDICATE_PATH).is_file()


@pytest.mark.unit
def test_completion_predicate_is_one_function() -> None:
    """Every is_done is listed, and both ticket models only return is_ticket_complete."""
    assert completion_problems(scan_is_done(SRC_ROOT)) == []
    defs = [
        p
        for p in SRC_ROOT.rglob("*.py")
        if "def is_ticket_complete(" in p.read_text(encoding="utf-8")
    ]
    assert [p.relative_to(SRC_ROOT).as_posix() for p in defs] == [
        COMPLETION_PREDICATE_PATH
    ]


@pytest.mark.unit
def test_no_second_definition_in_tree() -> None:
    """The real tree has exactly one ModelTicketContract, at the canonical path."""
    found = scan_classes(SRC_ROOT)
    assert second_definitions(found) == []
    assert (CANONICAL_TICKET_MODEL_PATH, CANONICAL_TICKET_MODEL) in found


@pytest.mark.unit
def test_only_one_ticket_contract_model() -> None:
    """ModelTicketContract is the only ticket contract model in the tree (OMN-23780).

    The inventory lists no other ticket *contract* class, and the scan of the
    real tree finds exactly the canonical one.
    """
    canonical = [f"{CANONICAL_TICKET_MODEL_PATH}:{CANONICAL_TICKET_MODEL}"]
    listed = sorted(
        f"{rel}:{name}"
        for (rel, name) in INVENTORY_CLASSES
        if name.endswith("TicketContract")
    )
    scanned = sorted(
        f"{rel}:{name}"
        for (rel, name) in scan_classes(SRC_ROOT)
        if name.endswith("TicketContract")
    )
    assert listed == canonical
    assert scanned == canonical


@pytest.mark.unit
def test_only_one_ticket_contract_model_rejects_a_planted_second(
    tmp_path: Path,
) -> None:
    """A planted second ticket contract model is unlisted, so the inventory fails."""
    _write(
        tmp_path,
        "models/contracts/ticket/model_other_ticket_contract.py",
        "class ModelOtherTicketContract:\n    pass\n",
    )

    found = scan_classes(tmp_path)

    assert set(found) - set(INVENTORY_CLASSES) - set(EXCLUDED_CLASSES) == {
        (
            "models/contracts/ticket/model_other_ticket_contract.py",
            "ModelOtherTicketContract",
        )
    }


@pytest.mark.unit
def test_second_definition_fails(tmp_path: Path) -> None:
    """A planted second ModelTicketContract is found by the ratchet."""
    planted = tmp_path / "models" / "contracts" / "ticket"
    planted.mkdir(parents=True)
    (planted / "model_other_ticket_contract.py").write_text(
        "class ModelTicketContract:\n    pass\n", encoding="utf-8"
    )
    canonical = tmp_path / CANONICAL_TICKET_MODEL_PATH
    canonical.parent.mkdir(parents=True)
    canonical.write_text("class ModelTicketContract:\n    pass\n", encoding="utf-8")

    found = scan_classes(tmp_path)

    assert second_definitions(found) == [
        "models/contracts/ticket/model_other_ticket_contract.py:ModelTicketContract"
    ]


def _write(root: Path, rel: str, source: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")


_SHARED_IS_DONE = (
    "class ModelTicketContract:\n"
    "    def is_done(self) -> bool:\n"
    '        """Done."""\n'
    "        return is_ticket_complete(phase_done=True)\n"
)


@pytest.mark.unit
def test_differently_named_ticket_model_fails(tmp_path: Path) -> None:
    """A ticket model whose name is in no list is found and reported as unlisted."""
    _write(
        tmp_path, "models/ticket/model_other.py", "class ModelOtherTicket:\n    pass\n"
    )

    found = scan_classes(tmp_path)

    assert ("models/ticket/model_other.py", "ModelOtherTicket") in found
    assert set(found) - set(INVENTORY_CLASSES) - set(EXCLUDED_CLASSES) == {
        ("models/ticket/model_other.py", "ModelOtherTicket")
    }


@pytest.mark.unit
def test_shared_is_done_passes_the_completion_scan(tmp_path: Path) -> None:
    """The control: a lone is_done that returns the predicate is not a problem."""
    _write(tmp_path, "models/ticket/model_ticket_contract.py", _SHARED_IS_DONE)

    found = scan_is_done(tmp_path)

    assert found == {
        ("models/ticket/model_ticket_contract.py", "ModelTicketContract"): [True]
    }
    assert not [
        p
        for p in completion_problems(found)
        if p.startswith(("unlisted", "2 ", "is_done does not"))
    ]


@pytest.mark.unit
def test_independent_is_done_in_an_inventoried_file_fails(tmp_path: Path) -> None:
    """A second class with its own is_done in a listed file is an unlisted completion."""
    _write(
        tmp_path,
        "models/ticket/model_ticket_contract.py",
        _SHARED_IS_DONE + "\n\nclass ModelTicketView:\n"
        "    def is_done(self) -> bool:\n"
        "        return True\n",
    )

    problems = completion_problems(scan_is_done(tmp_path))

    assert (
        "unlisted is_done: models/ticket/model_ticket_contract.py:ModelTicketView"
        in problems
    )


@pytest.mark.unit
def test_second_is_done_in_the_same_class_fails(tmp_path: Path) -> None:
    """A redefinition inside the listed class is counted, not merged into one file entry."""
    _write(
        tmp_path,
        "models/ticket/model_ticket_contract.py",
        _SHARED_IS_DONE + "    def is_done(self) -> bool:\n        return True\n",
    )

    problems = completion_problems(scan_is_done(tmp_path))

    assert (
        "2 is_done definitions: models/ticket/model_ticket_contract.py:ModelTicketContract"
        in problems
    )


@pytest.mark.unit
def test_is_done_that_discards_the_predicate_fails(tmp_path: Path) -> None:
    """Calling the predicate and returning an independent result is not the policy."""
    _write(
        tmp_path,
        "models/ticket/model_ticket_contract.py",
        "class ModelTicketContract:\n"
        "    def is_done(self) -> bool:\n"
        "        is_ticket_complete(phase_done=True)\n"
        "        return True\n",
    )

    problems = completion_problems(scan_is_done(tmp_path))

    assert (
        "is_done does not return is_ticket_complete: models/ticket/model_ticket_contract.py:ModelTicketContract"
        in problems
    )
