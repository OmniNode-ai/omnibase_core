# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract walker, report-only (OMN-19553, epic OMN-19546).

Fixture contracts are written to a temporary tree and walked. Each test names
what the golden-chain validation layer plan r4 Phase 3 asks the walker to
report: golden paths, error edges, illegal (state, trigger) pairs, unreachable
and dead states, uncovered transitions, the orchestrator-reducer product, the
NOT_ARMED path and a deterministic, report-only CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_contract_walk import (
    EnumContractWalkLinkEvidence,
    EnumContractWalkPathKind,
)
from omnibase_core.validation.validator_contract_walker import (
    find_unknown_fsm_keys,
    main,
    walk_contracts,
)

pytestmark = pytest.mark.unit

_V = {"major": 1, "minor": 0, "patch": 0}
_REPO = Path(__file__).resolve().parents[3]


def _state(name: str, *, terminal: bool = False) -> dict[str, object]:
    state: dict[str, object] = {
        "version": _V,
        "state_name": name,
        "state_type": "terminal" if terminal else "operational",
        "description": name,
    }
    if terminal:
        state["is_terminal"] = True
        state["is_recoverable"] = False
    return state


def _t(source: str, trigger: str, target: str) -> dict[str, object]:
    return {
        "version": _V,
        "transition_name": f"{source}_{trigger}_{target}".lower(),
        "from_state": source,
        "to_state": target,
        "trigger": trigger,
    }


def _machine(
    name: str,
    initial: str,
    states: list[dict[str, object]],
    transitions: list[dict[str, object]],
    *,
    terminal: list[str],
    error: list[str],
) -> dict[str, object]:
    return {
        "version": _V,
        "state_machine_name": name,
        "state_machine_version": _V,
        "description": name,
        "initial_state": initial,
        "terminal_states": terminal,
        "error_states": error,
        "states": states,
        "transitions": transitions,
    }


def _write(root: Path, node: str, contract: dict[str, object]) -> None:
    directory = root / node
    directory.mkdir(parents=True)
    (directory / "contract.yaml").write_text(yaml.safe_dump(contract), encoding="utf-8")


# A single orchestrator machine with one of everything the walker reports.
#   START -go-> WORK -finish-> DONE        golden path
#   WORK -crash-> FAILED                   error edge (FAILED is an error state)
#   WORK -stall-> STUCK -tick-> STUCK      STUCK is dead: reached, no way out
#   ORPHAN -go-> DONE                      ORPHAN unreachable, its edge uncovered
_SINGLE = _machine(
    "single",
    "START",
    [
        _state("START"),
        _state("WORK"),
        _state("STUCK"),
        _state("ORPHAN"),
        _state("DONE", terminal=True),
        _state("FAILED", terminal=True),
    ],
    [
        _t("START", "go", "WORK"),
        _t("WORK", "finish", "DONE"),
        _t("WORK", "crash", "FAILED"),
        _t("WORK", "stall", "STUCK"),
        _t("STUCK", "tick", "STUCK"),
        _t("ORPHAN", "go", "DONE"),
    ],
    terminal=["DONE", "FAILED"],
    error=["FAILED"],
)


def _single_tree(root: Path) -> None:
    _write(
        root,
        "node_single_orchestrator",
        {"node_type": "ORCHESTRATOR_GENERIC", "state_machine": _SINGLE},
    )


def test_single_machine_reports_every_finding_class(tmp_path: Path) -> None:
    _single_tree(tmp_path)
    report = walk_contracts([tmp_path])
    (workflow,) = report.workflows
    step = lambda p: [(s.from_state[0], s.trigger, s.to_state[0]) for s in p.steps]  # noqa: E731

    golden = [p for p in workflow.paths if p.kind is EnumContractWalkPathKind.GOLDEN]
    assert [step(p) for p in golden] == [
        [("START", "go", "WORK"), ("WORK", "finish", "DONE")]
    ]
    error = [p for p in workflow.paths if p.kind is EnumContractWalkPathKind.ERROR]
    assert [step(p) for p in error] == [
        [("START", "go", "WORK"), ("WORK", "crash", "FAILED")]
    ]
    opened = [p for p in workflow.paths if p.kind is EnumContractWalkPathKind.OPEN]
    assert {p.end_state for p in opened} == {("STUCK",)}

    assert [(e.from_state, e.trigger, e.to_state) for e in workflow.error_edges] == [
        ("WORK", "crash", "FAILED")
    ]
    assert [(u.node, u.state) for u in workflow.unreachable_states] == [
        ("node_single_orchestrator", "ORPHAN")
    ]
    assert workflow.dead_states == (("STUCK",),)
    assert [(u.from_state, u.trigger) for u in workflow.uncovered_transitions] == [
        ("ORPHAN", "go")
    ]
    illegal = {(p.state, p.trigger) for p in workflow.illegal_pairs}
    assert ("START", "finish") in illegal
    assert ("STUCK", "go") in illegal
    assert ("WORK", "go") in illegal
    # terminal states accept nothing and are not listed as illegal pairs
    assert not any(state in {"DONE", "FAILED"} for state, _ in illegal)

    assert workflow.cover_criterion == "all-edges"
    assert workflow.loop_bound == 1
    assert workflow.product_edge_count == 5
    assert workflow.product_state_count == 5
    assert workflow.cyclomatic_bound == 1
    assert workflow.selected_path_count == len(workflow.paths)
    assert workflow.components[
        0
    ].analyze_fsm_errors  # ORPHAN is also analyze_fsm's finding


# Orchestrator ORCH and reducer RED linked by a topic and sharing "reduce" and "ack".
#   ORCH: IDLE -start-> RUN -reduce-> WAIT -ack-> DONE ; RUN -abort-> DONE
#   RED:  r0 -reduce-> r1 -ack-> r2 ; r0 -ack-> r_bad
# r0 -ack-> r_bad is reachable in RED alone, but in the product ORCH can never
# take "ack" while RED is in r0, so the edge is blocked and must be uncovered.
def _product_tree(root: Path) -> None:
    orch = _machine(
        "orch",
        "IDLE",
        [_state("IDLE"), _state("RUN"), _state("WAIT"), _state("DONE", terminal=True)],
        [
            _t("IDLE", "start", "RUN"),
            _t("RUN", "reduce", "WAIT"),
            _t("WAIT", "ack", "DONE"),
            _t("RUN", "abort", "DONE"),
        ],
        terminal=["DONE"],
        error=[],
    )
    red = _machine(
        "red",
        "r0",
        [
            _state("r0"),
            _state("r1"),
            _state("r2", terminal=True),
            _state("r_bad", terminal=True),
        ],
        [_t("r0", "reduce", "r1"), _t("r1", "ack", "r2"), _t("r0", "ack", "r_bad")],
        terminal=["r2", "r_bad"],
        error=["r_bad"],
    )
    _write(
        root,
        "node_demo_orchestrator",
        {
            "node_type": "ORCHESTRATOR_GENERIC",
            "event_bus": {"publish_topics": ["onex.cmd.demo.reduce.v1"]},
            "state_machine": orch,
        },
    )
    _write(
        root,
        "node_demo_reducer",
        {
            "node_type": "REDUCER_GENERIC",
            "event_bus": {"subscribe_topics": ["onex.cmd.demo.reduce.v1"]},
            "state_machine": red,
        },
    )


def test_product_synchronises_shared_triggers_and_reports_blocked_edge(
    tmp_path: Path,
) -> None:
    _product_tree(tmp_path)
    report = walk_contracts([tmp_path])
    (workflow,) = report.workflows
    assert [c.node for c in workflow.components] == [
        "node_demo_orchestrator",
        "node_demo_reducer",
    ]
    reducer = workflow.components[1]
    assert reducer.link_evidence == (EnumContractWalkLinkEvidence.TOPIC,)
    assert reducer.link_detail == ("onex.cmd.demo.reduce.v1",)
    assert workflow.sync_triggers == ("ack", "reduce")
    uncovered = {
        (u.node, u.from_state, u.trigger, u.to_state)
        for u in workflow.uncovered_transitions
    }
    assert uncovered == {("node_demo_reducer", "r0", "ack", "r_bad")}
    assert {(u.node, u.state) for u in workflow.unreachable_states} == {
        ("node_demo_reducer", "r_bad")
    }
    golden_ends = {
        p.end_state for p in workflow.paths if p.kind is EnumContractWalkPathKind.GOLDEN
    }
    assert golden_ends == {("DONE", "r2"), ("DONE", "r0")}


def test_product_unknown_key_and_untyped_dialect_are_not_armed(tmp_path: Path) -> None:
    misspelt = dict(_SINGLE)
    transition = dict(misspelt["transitions"][0])  # type: ignore[index]
    transition["conditons"] = []
    misspelt["transitions"] = [transition, *misspelt["transitions"][1:]]  # type: ignore[index]
    _write(
        tmp_path,
        "node_misspelt_reducer",
        {"node_type": "reducer", "state_machine": misspelt},
    )
    _write(
        tmp_path,
        "node_legacy_orchestrator",
        {"node_type": "orchestrator", "fsm": {"states": []}},
    )
    unversioned = {k: v for k, v in _SINGLE.items() if k != "state_machine_version"}
    _write(
        tmp_path,
        "node_unversioned_reducer",
        {"node_type": "reducer", "state_machine": unversioned},
    )
    _write(tmp_path, "node_plain_compute", {"node_type": "compute"})

    report = walk_contracts([tmp_path])
    assert report.workflows == ()
    reasons = {n.node: n.reason for n in report.not_armed}
    assert "state_machine.transitions[0].conditons" in reasons["node_misspelt_reducer"]
    assert "fsm: dialect" in reasons["node_legacy_orchestrator"]
    assert "state_machine_version" in reasons["node_unversioned_reducer"]
    assert report.summary.contracts_scanned == 4
    assert report.summary.machine_contracts == 3
    assert report.summary.not_armed_contracts == 3


def test_state_that_can_only_fail_is_reported_as_no_golden_exit(tmp_path: Path) -> None:
    # RELEASE retries or fails but declares no way on to DONE: it is not dead
    # (FAILED is reachable), yet no run through it can succeed.
    machine = _machine(
        "release",
        "BUILD",
        [
            _state("BUILD"),
            _state("RELEASE"),
            _state("DONE", terminal=True),
            _state("FAILED", terminal=True),
        ],
        [
            _t("BUILD", "built", "DONE"),
            _t("BUILD", "built_full", "RELEASE"),
            _t("RELEASE", "retry", "RELEASE"),
            _t("RELEASE", "error", "FAILED"),
        ],
        terminal=["DONE", "FAILED"],
        error=["FAILED"],
    )
    _write(
        tmp_path,
        "node_release_orchestrator",
        {"node_type": "orchestrator", "state_machine": machine},
    )
    (workflow,) = walk_contracts([tmp_path]).workflows
    assert workflow.dead_states == ()
    assert workflow.no_golden_exit_states == (("RELEASE",),)
    assert (
        workflow.components[0].analyze_fsm_errors == ()
    )  # analyze_fsm does not see it


def test_find_unknown_fsm_keys_accepts_a_clean_block() -> None:
    assert find_unknown_fsm_keys(_SINGLE) == []
    assert find_unknown_fsm_keys({**_SINGLE, "error_state": []}) == [
        "state_machine.error_state"
    ]


def test_perpetual_reducer_has_open_paths_and_no_dead_states(tmp_path: Path) -> None:
    fold = _machine(
        "fold",
        "idle",
        [_state("idle"), _state("folding")],
        [_t("idle", "event", "folding"), _t("folding", "event", "folding")],
        terminal=[],
        error=[],
    )
    _write(
        tmp_path, "node_fold_reducer", {"node_type": "reducer", "state_machine": fold}
    )
    (workflow,) = walk_contracts([tmp_path]).workflows
    assert workflow.components[0].perpetual is True
    assert {p.kind for p in workflow.paths} == {EnumContractWalkPathKind.OPEN}
    assert workflow.dead_states == ()
    assert workflow.uncovered_transitions == ()


def test_deterministic_report_bytes(tmp_path: Path) -> None:
    _single_tree(tmp_path / "a")
    _product_tree(tmp_path / "b")
    first = walk_contracts([tmp_path]).model_dump_json()
    second = walk_contracts([tmp_path]).model_dump_json()
    assert first == second


def test_cli_is_report_only_and_writes_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _single_tree(tmp_path / "tree")
    out = tmp_path / "report.json"
    assert main([str(tmp_path / "tree"), "--json-out", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["report_kind"] == "contract_walk.v1"
    assert data["summary"]["dead_states"] == 1
    printed = capsys.readouterr().out
    assert "report-only" in printed
    assert "node_single_orchestrator" in printed


def test_cli_hook_is_exported() -> None:
    hooks = yaml.safe_load(
        (_REPO / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
    )
    (hook,) = [h for h in hooks if h["id"] == "report-contract-walk"]
    assert (
        hook["entry"] == "python -m omnibase_core.validation.validator_contract_walker"
    )
    assert hook["pass_filenames"] is False


def test_duplicate_key_machine_contract_is_not_armed(tmp_path: Path) -> None:
    directory = tmp_path / "node_dup_reducer"
    directory.mkdir()
    (directory / "contract.yaml").write_text(
        "node_type: reducer\nnode_type: reducer\nstate_machine:\n  initial_state: a\n",
        encoding="utf-8",
    )
    (tmp_path / "node_other").mkdir()
    (tmp_path / "node_other" / "contract.yaml").write_text(
        "a: 1\na: 2\n", encoding="utf-8"
    )
    report = walk_contracts([tmp_path])
    assert [n.node for n in report.not_armed] == ["node_dup_reducer"]
    assert "does not load" in report.not_armed[0].reason
