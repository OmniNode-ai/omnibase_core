# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Cases for the sprint_roll apply EFFECT node (OMN-20397).

The transport is a recorder, so every case is judged by what was SENT rather than by what
the node reports about itself. That distinction is the whole point of AC3: a dry run that
merely says it sent nothing is not evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from omnibase_core.models.nodes.sprint_roll.model_sprint_placement import (
    ModelSprintPlacement,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_apply_request import (
    ModelSprintRollApplyRequest,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_plan import (
    ModelSprintRollPlan,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_write import (
    ModelSprintRollWrite,
)
from omnibase_core.nodes.node_sprint_roll_apply_effect import NodeSprintRollApplyEffect
from omnibase_core.nodes.node_sprint_roll_apply_effect.runtime_sprint_roll_apply import (
    LinearTransportError,
    SprintRollJournal,
    label_uuid,
    state_uuid,
    undo_from_manifest,
)

P_OLD = UUID(int=10)
P_NEW = UUID(int=11)


class Recorder:
    """A transport that records every call and answers from a canned issue set."""

    def __init__(self, *, fail_after: int | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_after = fail_after

    @property
    def mutations(self) -> list[dict[str, Any]]:
        return [v for q, v in self.calls if q.lstrip().startswith("mutation")]

    @property
    def reads(self) -> list[dict[str, Any]]:
        return [v for q, v in self.calls if not q.lstrip().startswith("mutation")]

    def __call__(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((query, variables))
        if self.fail_after is not None and len(self.mutations) > self.fail_after:
            raise LinearTransportError("transport refused")
        if query.lstrip().startswith("mutation"):
            return {"issueUpdate": {"success": True}}
        if "issueLabels" in query:
            return {"issueLabels": {"nodes": [{"id": "label-uuid"}]}}
        if "workflowStates" in query:
            return {"workflowStates": {"nodes": [{"id": "state-uuid"}]}}
        return {
            "issues": {
                "nodes": [
                    {
                        "id": f"uuid-{ident}",
                        "identifier": ident,
                        "project": {"id": str(P_OLD)},
                        "state": {"id": "state-old"},
                        "labels": {"nodes": [{"id": "keep-me"}]},
                    }
                    for ident in variables.get("ids", [])
                ]
            }
        }


def _plan(moved: tuple[str, ...] = ("OMN-1", "OMN-2")) -> ModelSprintRollPlan:
    return ModelSprintRollPlan(
        source_sprint_id=P_OLD,
        source_sprint_name="source",
        cap=21,
        cap_basis="caller override",
        median_estimate=3,
        rolling_ticket_ids=moved,
        placements=(
            ModelSprintPlacement(
                sprint_id=P_NEW,
                name="next",
                load_before=0,
                load_after=len(moved),
                ticket_ids=moved,
                moved_in=moved,
            ),
        ),
    )


# -- AC3: a dry run sends nothing --------------------------------------------


def test_a_dry_run_issues_no_mutation() -> None:
    recorder = Recorder()
    result = NodeSprintRollApplyEffect(recorder).handle(
        ModelSprintRollApplyRequest(plan=_plan())
    )
    assert recorder.mutations == []
    assert result.write_calls == 0
    assert result.dry_run is True
    assert len(result.writes) == 2  # what it WOULD send, still reported


def test_a_dry_run_writes_no_manifest(tmp_path: Path) -> None:
    """A manifest from a dry run would be an undo record for writes never made."""
    manifest = tmp_path / "m.jsonl"
    recorder = Recorder()
    result = NodeSprintRollApplyEffect(recorder).handle(
        ModelSprintRollApplyRequest(plan=_plan(), manifest_path=manifest)
    )
    assert not manifest.exists()
    assert result.manifest_path is None


def test_dry_run_is_the_default() -> None:
    assert ModelSprintRollApplyRequest(plan=_plan()).dry_run is True


# -- AC4: journal before send -------------------------------------------------


def test_every_mutation_is_journalled_before_it_is_sent(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    recorder = Recorder()
    result = NodeSprintRollApplyEffect(recorder).handle(
        ModelSprintRollApplyRequest(plan=_plan(), dry_run=False, manifest_path=manifest)
    )
    assert len(recorder.mutations) == 2
    lines = manifest.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert {json.loads(line)["identifier"] for line in lines} == {"OMN-1", "OMN-2"}
    assert result.write_calls == 2


def test_a_run_interrupted_after_the_first_write_still_leaves_its_undo(
    tmp_path: Path,
) -> None:
    """The ordering guarantee: journal, then mutate. A crash between them leaves an
    entry for a write that never happened, and undoing that is a no-op. The reverse
    ordering leaves a write nothing can undo."""
    manifest = tmp_path / "m.jsonl"
    recorder = Recorder(fail_after=1)
    with pytest.raises(LinearTransportError):
        NodeSprintRollApplyEffect(recorder).handle(
            ModelSprintRollApplyRequest(
                plan=_plan(), dry_run=False, manifest_path=manifest
            )
        )
    lines = manifest.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert len(recorder.mutations) == 2


def test_the_journal_records_the_prior_value_not_the_new_one(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    NodeSprintRollApplyEffect(Recorder()).handle(
        ModelSprintRollApplyRequest(
            plan=_plan(("OMN-1",)), dry_run=False, manifest_path=manifest
        )
    )
    record = json.loads(manifest.read_text(encoding="utf-8").strip())
    assert record["before"] == str(P_OLD)
    assert record["after"] == str(P_NEW)


def test_a_ticket_already_in_the_target_sprint_is_not_written(tmp_path: Path) -> None:
    plan = _plan(("OMN-1",)).model_copy(
        update={
            "placements": (
                ModelSprintPlacement(
                    sprint_id=P_OLD,
                    name="same",
                    load_before=1,
                    load_after=1,
                    ticket_ids=("OMN-1",),
                    moved_in=("OMN-1",),
                ),
            )
        }
    )
    recorder = Recorder()
    NodeSprintRollApplyEffect(recorder).handle(
        ModelSprintRollApplyRequest(plan=plan, dry_run=False)
    )
    assert recorder.mutations == []


def test_a_plan_that_moves_nothing_reads_nothing() -> None:
    recorder = Recorder()
    result = NodeSprintRollApplyEffect(recorder).handle(
        ModelSprintRollApplyRequest(plan=_plan(()))
    )
    assert recorder.calls == []
    assert result.read_calls == 0


# -- AC5: undo ---------------------------------------------------------------


def test_undo_restores_prior_values_newest_write_first(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    journal = SprintRollJournal(manifest)
    for n in (1, 2, 3):
        journal.record(
            ModelSprintRollWrite(
                issue_uuid=f"uuid-{n}",
                identifier=f"OMN-{n}",
                field="projectId",
                before=str(P_OLD),
                after=str(P_NEW),
            )
        )
    recorder = Recorder()
    reversed_writes, skipped = undo_from_manifest(recorder, manifest)
    assert [w.identifier for w in reversed_writes] == ["OMN-3", "OMN-2", "OMN-1"]
    assert skipped == []
    assert [v["in"]["projectId"] for v in recorder.mutations] == [str(P_OLD)] * 3


def test_undo_reports_a_state_with_no_prior_value_rather_than_guessing(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "m.jsonl"
    SprintRollJournal(manifest).record(
        ModelSprintRollWrite(
            issue_uuid="uuid-1",
            identifier="OMN-1",
            field="stateId",
            before=None,
            after="state-new",
        )
    )
    recorder = Recorder()
    reversed_writes, skipped = undo_from_manifest(recorder, manifest)
    assert reversed_writes == []
    assert [w.identifier for w in skipped] == ["OMN-1"]
    assert recorder.mutations == []


def test_undo_restores_an_empty_project_because_no_sprint_is_a_real_prior_state(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "m.jsonl"
    SprintRollJournal(manifest).record(
        ModelSprintRollWrite(
            issue_uuid="uuid-1",
            identifier="OMN-1",
            field="projectId",
            before=None,
            after=str(P_NEW),
        )
    )
    recorder = Recorder()
    reversed_writes, skipped = undo_from_manifest(recorder, manifest)
    assert [w.identifier for w in reversed_writes] == ["OMN-1"]
    assert skipped == []
    assert recorder.mutations[0]["in"] == {"projectId": None}


def test_undo_restores_the_whole_prior_label_set(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    SprintRollJournal(manifest).record(
        ModelSprintRollWrite(
            issue_uuid="uuid-1",
            identifier="OMN-1",
            field="labelIds",
            before=("keep-me",),
            after=("keep-me", "label-uuid"),
        )
    )
    recorder = Recorder()
    undo_from_manifest(recorder, manifest)
    assert recorder.mutations[0]["in"] == {"labelIds": ["keep-me"]}


def test_undo_on_an_empty_manifest_is_a_no_op(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    manifest.write_text("", encoding="utf-8")
    recorder = Recorder()
    assert undo_from_manifest(recorder, manifest) == ([], [])
    assert recorder.calls == []


# -- lookups and refusals ----------------------------------------------------


def test_a_missing_label_is_a_refusal_not_a_silent_skip() -> None:
    def no_label(query: str, variables: dict[str, Any]) -> dict[str, Any]:
        return {"issueLabels": {"nodes": []}}

    with pytest.raises(LinearTransportError, match="no label named"):
        label_uuid(no_label, "beta-critical")


def test_a_missing_state_is_a_refusal() -> None:
    def no_state(query: str, variables: dict[str, Any]) -> dict[str, Any]:
        return {"workflowStates": {"nodes": []}}

    with pytest.raises(LinearTransportError, match="no state named"):
        state_uuid(no_state, "OMN", "Backlog")


def test_the_label_and_state_lookups_read_by_exact_name() -> None:
    recorder = Recorder()
    assert label_uuid(recorder, "beta-critical") == "label-uuid"
    assert state_uuid(recorder, "OMN", "Backlog") == "state-uuid"
    assert recorder.reads[0]["n"] == "beta-critical"
    assert recorder.reads[1] == {"t": "OMN", "s": "Backlog"}
