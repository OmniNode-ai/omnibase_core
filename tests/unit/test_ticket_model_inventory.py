# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Inventory and ratchet for the ticket, definition-of-done and completion models.

OMN-22969. The ticket model, the DoD item models and the completion predicate
are listed here from a scan of ``src/omnibase_core``. A second ``ModelTicketContract``
definition, or any path the scan finds that this inventory does not list, fails.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "omnibase_core"

CANONICAL_TICKET_MODEL = "ModelTicketContract"
CANONICAL_TICKET_MODEL_PATH = "models/ticket/model_ticket_contract.py"
COMPLETION_PREDICATE_PATH = "models/ticket/model_ticket_completion_predicate.py"

# Every class the scan treats as a ticket model or a DoD item model: path -> role.
# ``flagged`` rows are known second definitions or duplicates awaiting their
# cross-repo migration; the scan lists them and the ratchet pins them.
TICKET_MODEL_NAMES = frozenset(
    {
        "ModelTicketContract",
        "ModelLinearTicketContract",
        "ModelTicketWorkflowState",
        "ModelContractDodItem",
        "ModelDodEvidenceItem",
        "ModelDoDItem",
    }
)
INVENTORY_CLASSES: dict[tuple[str, str], str] = {
    (
        "models/ticket/model_ticket_contract.py",
        "ModelTicketContract",
    ): "canonical ticket model",
    (
        "models/contracts/ticket/model_linear_ticket_contract.py",
        "ModelLinearTicketContract",
    ): "PR-gate input for the flat Linear dict (validate_ticket_contract)",
    (
        "models/ticket/model_ticket_workflow_state.py",
        "ModelTicketWorkflowState",
    ): "workflow FSM state, distinct from the contract",
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
# Every ``is_done`` in a ticket model: each must call the one predicate.
INVENTORY_COMPLETION_CALLERS: frozenset[str] = frozenset(
    {
        "models/ticket/model_ticket_contract.py",
        "models/ticket/model_ticket_workflow_state.py",
    }
)


def scan_classes(root: Path) -> dict[tuple[str, str], int]:
    """Return (relative path, class name) -> count for every ticket model class."""
    found: dict[tuple[str, str], int] = {}
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in TICKET_MODEL_NAMES:
                found[(rel, node.name)] = found.get((rel, node.name), 0) + 1
    return found


def second_definitions(found: dict[tuple[str, str], int]) -> list[str]:
    """List every ModelTicketContract definition other than the canonical one."""
    return sorted(
        f"{rel}:{name}"
        for (rel, name) in found
        if name == CANONICAL_TICKET_MODEL and rel != CANONICAL_TICKET_MODEL_PATH
    )


def completion_callers(root: Path) -> set[str]:
    """Return the files whose ``is_done`` calls ``is_ticket_complete``."""
    callers: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "is_done":
                calls = {
                    n.func.id
                    for n in ast.walk(node)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                }
                if "is_ticket_complete" in calls:
                    callers.add(path.relative_to(root).as_posix())
    return callers


@pytest.mark.unit
def test_every_path_listed() -> None:
    """Every ticket model class the scan finds is in the inventory, and back."""
    found = scan_classes(SRC_ROOT)
    assert set(found) == set(INVENTORY_CLASSES), (
        f"unlisted: {sorted(set(found) - set(INVENTORY_CLASSES))}; "
        f"stale: {sorted(set(INVENTORY_CLASSES) - set(found))}"
    )
    assert all(count == 1 for count in found.values())
    assert (SRC_ROOT / COMPLETION_PREDICATE_PATH).is_file()


@pytest.mark.unit
def test_completion_predicate_is_one_function() -> None:
    """Both ticket models reach completion only through is_ticket_complete."""
    assert completion_callers(SRC_ROOT) == INVENTORY_COMPLETION_CALLERS
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
