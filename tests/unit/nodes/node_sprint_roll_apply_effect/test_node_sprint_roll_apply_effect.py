# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Cases for the sprint_roll apply EFFECT node (OMN-20397).

The transport is a recorder, so every case is judged by what was SENT rather than by what
the node reports about itself. That distinction is the whole point of AC3: a dry run that
merely says it sent nothing is not evidence.
"""

from __future__ import annotations

import datetime as dt
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
from omnibase_core.nodes.node_sprint_roll_apply_effect.handler import (
    destination_milestone,
)
from omnibase_core.nodes.node_sprint_roll_apply_effect.node_linear_transport_error import (
    NodeLinearTransportError,
)
from omnibase_core.nodes.node_sprint_roll_apply_effect.node_sprint_roll_journal import (
    NodeSprintRollJournal,
)
from omnibase_core.nodes.node_sprint_roll_apply_effect.node_sprint_roll_readback_error import (
    NodeSprintRollReadbackError,
)
from omnibase_core.nodes.node_sprint_roll_apply_effect.runtime_sprint_roll_apply import (
    MAX_ATTEMPTS,
    READBACK_QUERY,
    RETRYABLE_STATUS,
    label_uuid,
    resolve_source_start,
    state_uuid,
    undo_from_manifest,
    with_retries,
)

P_OLD = UUID(int=10)
P_NEW = UUID(int=11)
MS_OLD = "ms-m4-old"
MS_FAST = "ms-m45"
DUE_OLD = "2026-10-11"
DUE_NEW = "2026-10-25"


class Recorder:
    """A transport that records every call and answers from a canned issue set.

    It also HOLDS what it is sent (OMN-21085): a mutation changes the issue it names, and
    a readback answers from that state, so a case can make Linear drop a field the way
    a real project move drops the milestone.
    """

    def __init__(
        self, *, fail_after: int | None = None, drops: frozenset[str] = frozenset()
    ) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_after = fail_after
        self.drops = drops
        self.held: dict[str, dict[str, Any]] = {}

    @property
    def mutations(self) -> list[dict[str, Any]]:
        return [v for q, v in self.calls if q.lstrip().startswith("mutation")]

    @property
    def reads(self) -> list[dict[str, Any]]:
        return [v for q, v in self.calls if not q.lstrip().startswith("mutation")]

    def _issue(self, uuid: str) -> dict[str, Any]:
        return self.held.setdefault(
            uuid,
            {
                "projectId": str(P_OLD),
                "projectMilestoneId": MS_OLD,
                "dueDate": DUE_OLD,
            },
        )

    def __call__(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((query, variables))
        if self.fail_after is not None and len(self.mutations) > self.fail_after:
            raise NodeLinearTransportError("transport refused")
        if query.lstrip().startswith("mutation"):
            issue = self._issue(variables["id"])
            for field, value in variables["in"].items():
                issue[field] = None if field in self.drops else value
            return {"issueUpdate": {"success": True}}
        if "issueLabels" in query:
            return {"issueLabels": {"nodes": [{"id": "label-uuid"}]}}
        if "workflowStates" in query:
            return {"workflowStates": {"nodes": [{"id": "state-uuid"}]}}
        if "projects(filter:{id:" in query:
            return {
                "projects": {
                    "nodes": [
                        {
                            "id": pid,
                            "targetDate": DUE_NEW,
                            "projectMilestones": {
                                "nodes": [
                                    {"id": MS_FAST, "name": "M4.5"},
                                    {"id": f"ms-m4-{pid}", "name": "M4"},
                                ]
                            },
                        }
                        for pid in variables["ids"]
                    ]
                }
            }
        if "issue(id:" in query:
            issue = self._issue(variables["id"])
            return {
                "issue": {
                    "id": variables["id"],
                    "project": {"id": issue["projectId"]},
                    "projectMilestone": (
                        {"id": issue["projectMilestoneId"]}
                        if issue["projectMilestoneId"]
                        else None
                    ),
                    "dueDate": issue["dueDate"],
                }
            }
        return {
            "issues": {
                "nodes": [
                    {
                        "id": f"uuid-{ident}",
                        "identifier": ident,
                        "project": {"id": str(P_OLD)},
                        "projectMilestone": {"id": MS_OLD, "name": "M4"},
                        "dueDate": DUE_OLD,
                        "state": {"id": "state-old"},
                        "labels": {"nodes": [{"id": "keep-me"}]},
                    }
                    for ident in (
                        [f"OMN-{int(n)}" for n in variables.get("nums", [])]
                        or variables.get("ids", [])
                    )
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
    # What it WOULD send, still reported: project, milestone and due date per ticket.
    assert len(result.writes) == 6


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
    assert len(lines) == 6  # three fields per ticket, one mutation per ticket
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
    with pytest.raises(NodeLinearTransportError):
        NodeSprintRollApplyEffect(recorder).handle(
            ModelSprintRollApplyRequest(
                plan=_plan(), dry_run=False, manifest_path=manifest
            )
        )
    lines = manifest.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 6
    assert len(recorder.mutations) == 2


def test_the_journal_records_the_prior_value_not_the_new_one(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    NodeSprintRollApplyEffect(Recorder()).handle(
        ModelSprintRollApplyRequest(
            plan=_plan(("OMN-1",)), dry_run=False, manifest_path=manifest
        )
    )
    record = json.loads(manifest.read_text(encoding="utf-8").splitlines()[0])
    assert record["field"] == "projectId"
    assert record["before"] == [str(P_OLD)]
    assert record["after"] == [str(P_NEW)]


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
    journal = NodeSprintRollJournal(manifest)
    for n in (1, 2, 3):
        journal.record(
            ModelSprintRollWrite(
                issue_uuid=f"uuid-{n}",
                identifier=f"OMN-{n}",
                field="projectId",
                before=(str(P_OLD),),
                after=(str(P_NEW),),
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
    NodeSprintRollJournal(manifest).record(
        ModelSprintRollWrite(
            issue_uuid="uuid-1",
            identifier="OMN-1",
            field="stateId",
            before=None,
            after=("state-new",),
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
    NodeSprintRollJournal(manifest).record(
        ModelSprintRollWrite(
            issue_uuid="uuid-1",
            identifier="OMN-1",
            field="projectId",
            before=None,
            after=(str(P_NEW),),
        )
    )
    recorder = Recorder()
    reversed_writes, skipped = undo_from_manifest(recorder, manifest)
    assert [w.identifier for w in reversed_writes] == ["OMN-1"]
    assert skipped == []
    assert recorder.mutations[0]["in"] == {"projectId": None}


def test_undo_restores_the_whole_prior_label_set(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    NodeSprintRollJournal(manifest).record(
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

    with pytest.raises(NodeLinearTransportError, match="no label named"):
        label_uuid(no_label, "beta-critical")


def test_a_missing_state_is_a_refusal() -> None:
    def no_state(query: str, variables: dict[str, Any]) -> dict[str, Any]:
        return {"workflowStates": {"nodes": []}}

    with pytest.raises(NodeLinearTransportError, match="no state named"):
        state_uuid(no_state, "OMN", "Backlog")


def test_the_label_and_state_lookups_read_by_exact_name() -> None:
    recorder = Recorder()
    assert label_uuid(recorder, "beta-critical") == "label-uuid"
    assert state_uuid(recorder, "OMN", "Backlog") == "state-uuid"
    assert recorder.reads[0]["n"] == "beta-critical"
    assert recorder.reads[1] == {"t": "OMN", "s": "Backlog"}


# -- AC2: the drained sprint is found from the project list -------------------

SPRINTS = [
    {"id": "p0", "name": "s0", "startDate": "2026-09-21", "targetDate": "2026-09-27"},
    {"id": "p1", "name": "s1", "startDate": "2026-09-28", "targetDate": "2026-10-04"},
    {"id": "p2", "name": "s2", "startDate": "2026-10-05", "targetDate": "2026-10-11"},
]


def _projects(rows: list[dict[str, Any]]):
    def transport(query: str, variables: dict[str, Any]) -> dict[str, Any]:
        return {"projects": {"nodes": rows}}

    return transport


def test_on_the_last_day_the_containing_sprint_is_the_one_drained() -> None:
    start = resolve_source_start(_projects(SPRINTS), dt.date(2026, 10, 4))
    assert start == dt.date(2026, 9, 28)


@pytest.mark.parametrize("day", ["2026-10-05", "2026-10-06", "2026-10-08"])
def test_after_the_boundary_the_sprint_that_ended_is_drained_not_the_new_one(
    day: str,
) -> None:
    """The regression this function exists for: on Monday the containing sprint is the
    one just beginning, and the board's own sprint read cannot even see the finished one.
    """
    start = resolve_source_start(_projects(SPRINTS), dt.date.fromisoformat(day))
    assert start == dt.date(2026, 9, 28)


def test_a_window_that_omits_the_finished_sprint_still_resolves_it() -> None:
    """The project list has no window, which is the whole reason it is asked first."""
    only_future = [SPRINTS[2]]
    with pytest.raises(NodeLinearTransportError, match="nothing to roll"):
        resolve_source_start(_projects(only_future), dt.date(2026, 10, 6))
    assert resolve_source_start(_projects(SPRINTS), dt.date(2026, 10, 6)) == dt.date(
        2026, 9, 28
    )


def test_a_date_before_every_sprint_is_refused() -> None:
    with pytest.raises(NodeLinearTransportError, match="nothing to roll"):
        resolve_source_start(_projects(SPRINTS), dt.date(2026, 9, 1))


def test_an_undated_project_is_ignored_rather_than_crashed_on() -> None:
    rows = [*SPRINTS, {"id": "px", "name": "no dates"}]
    assert resolve_source_start(_projects(rows), dt.date(2026, 10, 4)) == dt.date(
        2026, 9, 28
    )


def test_no_dated_sprint_project_at_all_is_refused() -> None:
    with pytest.raises(NodeLinearTransportError, match="no dated sprint project"):
        resolve_source_start(_projects([]), dt.date(2026, 10, 4))


# -- AC6: transient failures retry, persistent ones surface ------------------
#
# The retry POLICY is what core owns. ADR-005 forbids an HTTP client anywhere in
# omnibase_core and the url-authority gate forbids a URL literal, so the client and the
# endpoint belong to the caller; the adapter there raises NodeLinearTransportError with the
# status, and these cases prove what the policy does with it.


class Flaky:
    """A transport that fails with a scripted status then succeeds."""

    def __init__(self, statuses: list[int | None]) -> None:
        self.statuses = statuses
        self.attempts = 0

    def __call__(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        self.attempts += 1
        code = self.statuses[min(self.attempts - 1, len(self.statuses) - 1)]
        if code is None:
            return {"ok": True}
        raise NodeLinearTransportError(f"HTTP {code}", status=code)


@pytest.mark.parametrize("code", sorted(RETRYABLE_STATUS))
def test_a_transient_status_is_retried_and_then_succeeds(code: int) -> None:
    flaky = Flaky([code, None])
    assert with_retries(flaky, sleep=lambda _s: None)("query{}", {}) == {"ok": True}
    assert flaky.attempts == 2


def test_a_persistent_transient_status_surfaces_rather_than_being_swallowed() -> None:
    """A failure swallowed mid-plan would leave the board half rolled."""
    flaky = Flaky([503])
    with pytest.raises(NodeLinearTransportError, match="HTTP 503"):
        with_retries(flaky, sleep=lambda _s: None)("query{}", {})
    assert flaky.attempts == MAX_ATTEMPTS


def test_a_non_retryable_status_fails_on_the_first_attempt() -> None:
    flaky = Flaky([401])
    with pytest.raises(NodeLinearTransportError, match="HTTP 401"):
        with_retries(flaky, sleep=lambda _s: None)("query{}", {})
    assert flaky.attempts == 1


def test_an_error_with_no_status_is_not_retried() -> None:
    """A transport failure the adapter could not classify is not assumed transient."""
    calls = {"n": 0}

    def unclassified(query: str, variables: dict[str, Any]) -> dict[str, Any]:
        calls["n"] += 1
        raise NodeLinearTransportError("socket closed")

    with pytest.raises(NodeLinearTransportError, match="socket closed"):
        with_retries(unclassified, sleep=lambda _s: None)("query{}", {})
    assert calls["n"] == 1


def test_the_backoff_grows_and_is_injected_so_the_test_does_not_sleep() -> None:
    slept: list[float] = []
    flaky = Flaky([503, 503, None])
    with_retries(flaky, sleep=slept.append)("query{}", {})
    assert slept == [3, 6]


def test_a_transport_that_never_raises_is_called_once() -> None:
    flaky = Flaky([None])
    with_retries(flaky, sleep=lambda _s: None)("query{}", {})
    assert flaky.attempts == 1


def test_core_imports_no_http_client_and_names_no_url(tmp_path: Path) -> None:
    """ADR-005 and the url-authority gate, asserted here so a reintroduction fails a
    test rather than only a CI job somebody can rerun."""
    import omnibase_core.nodes.node_sprint_roll_apply_effect.runtime_sprint_roll_apply as rt

    lines = [
        line.strip()
        for line in Path(rt.__file__).read_text(encoding="utf-8").splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    banned = ("httpx", "requests", "aiohttp", "urllib3", "urllib.request", "socket")
    offending = [line for line in lines if any(name in line for name in banned)]
    assert offending == [], offending
    # A URL literal must come from a contract, not a module constant. Prose in a
    # docstring is not a literal, so only code lines are read.
    code = [
        line
        for line in Path(rt.__file__).read_text(encoding="utf-8").splitlines()
        if "://" in line and not line.lstrip().startswith(("#", '"""', "*"))
    ]
    assert code == [], code


# -- the invalid query the 2026-10-03 live dry run found ---------------------


def test_the_issue_query_filters_by_number_not_identifier() -> None:
    """`IssueFilter` has no `identifier` field. Linear answers HTTP 400 with
    `Field "identifier" is not defined by type "IssueFilter"`, so the earlier query made
    `handle` fail on every plan that moved anything -- and no test caught it, because a
    recorded transport answers whatever query it is handed. This asserts the shape that
    a fake cannot validate."""
    from omnibase_core.nodes.node_sprint_roll_apply_effect.handler import ISSUE_QUERY

    assert "number:{in:$nums}" in ISSUE_QUERY
    assert "identifier:{in:" not in ISSUE_QUERY
    assert "$nums:[Float!]!" in ISSUE_QUERY


def test_identifiers_become_the_float_numbers_the_filter_accepts() -> None:
    from omnibase_core.nodes.node_sprint_roll_apply_effect.handler import issue_numbers

    assert issue_numbers(["OMN-20395", "OMN-7"]) == [7.0, 20395.0]


def test_a_repeated_identifier_is_sent_once() -> None:
    from omnibase_core.nodes.node_sprint_roll_apply_effect.handler import issue_numbers

    assert issue_numbers(["OMN-1", "OMN-1", "OMN-2"]) == [1.0, 2.0]


def test_an_identifier_with_no_number_is_dropped_rather_than_guessed() -> None:
    """Sending it would widen the filter rather than narrow it."""
    from omnibase_core.nodes.node_sprint_roll_apply_effect.handler import issue_numbers

    assert issue_numbers(["OMN-20395", "not-a-ticket", "OMN-"]) == [20395.0]


def test_the_read_sends_numbers_for_the_tickets_the_plan_moves() -> None:
    recorder = Recorder()
    NodeSprintRollApplyEffect(recorder).handle(
        ModelSprintRollApplyRequest(plan=_plan(("OMN-1", "OMN-2")))
    )
    assert recorder.reads[0] == {"nums": [1.0, 2.0]}


def test_a_plan_whose_tickets_carry_no_number_refuses_rather_than_reading_everything() -> (
    None
):
    plan = _plan(("nope",))
    with pytest.raises(NodeLinearTransportError, match="no plan ticket carries"):
        NodeSprintRollApplyEffect(Recorder()).handle(
            ModelSprintRollApplyRequest(plan=plan)
        )


# -- OMN-21085: a move is project, milestone and due date, read back ----------


def _applied(recorder: Recorder, manifest: Path | None = None) -> None:
    NodeSprintRollApplyEffect(recorder).handle(
        ModelSprintRollApplyRequest(plan=_plan(), dry_run=False, manifest_path=manifest)
    )


def test_one_update_per_ticket_carries_project_milestone_and_due_date() -> None:
    """Linear clears the milestone on a project change and keeps the old due date, so
    a project-only update lands the ticket off the board and outside its window."""
    recorder = Recorder()
    _applied(recorder)
    assert len(recorder.mutations) == 2
    for mutation in recorder.mutations:
        assert mutation["in"] == {
            "projectId": str(P_NEW),
            "projectMilestoneId": f"ms-m4-{P_NEW}",
            "dueDate": DUE_NEW,
        }


def test_the_milestone_with_the_same_name_wins_over_a_second_one() -> None:
    milestones: list[Any] = [
        {"id": MS_FAST, "name": "M4.5"},
        {"id": "ms-m4", "name": "M4"},
    ]
    assert destination_milestone("M4", milestones) == "ms-m4"


def test_the_milestone_falls_back_to_the_destination_only_milestone() -> None:
    assert destination_milestone("Gone", [{"id": "ms-only", "name": "M4"}]) == (
        "ms-only"
    )
    assert destination_milestone(None, [{"id": "ms-only", "name": "M4"}]) == "ms-only"


def test_the_milestone_is_blank_rather_than_guessed_between_two() -> None:
    milestones: list[Any] = [
        {"id": MS_FAST, "name": "M4.5"},
        {"id": "ms-m4", "name": "M4"},
    ]
    assert destination_milestone("Gone", milestones) is None


def test_the_readback_reads_each_ticket_after_its_update() -> None:
    recorder = Recorder()
    _applied(recorder)
    kinds = [
        "mutation" if q.lstrip().startswith("mutation") else q.split("(")[0]
        for q, _v in recorder.calls
        if q.lstrip().startswith("mutation") or "issue(id:" in q
    ]
    assert kinds == ["mutation", "query", "mutation", "query"]
    assert READBACK_QUERY in [q for q, _v in recorder.calls]


def test_a_readback_mismatch_is_raised_not_reported_as_success(tmp_path: Path) -> None:
    """`issueUpdate` answers success and Linear blanks the milestone anyway. The node
    must stop on that, not count it as a write."""
    manifest = tmp_path / "m.jsonl"
    recorder = Recorder(drops=frozenset({"projectMilestoneId"}))
    with pytest.raises(NodeSprintRollReadbackError, match="projectMilestoneId"):
        _applied(recorder, manifest)
    assert len(recorder.mutations) == 1  # stopped at the first ticket
    assert len(manifest.read_text(encoding="utf-8").splitlines()) == 3


def test_a_readback_due_date_mismatch_is_raised_too() -> None:
    with pytest.raises(NodeSprintRollReadbackError, match="dueDate"):
        _applied(Recorder(drops=frozenset({"dueDate"})))


def test_a_readback_mismatch_is_still_a_transport_error_for_older_callers() -> None:
    assert issubclass(NodeSprintRollReadbackError, NodeLinearTransportError)


def test_a_destination_with_no_due_date_refuses_before_any_write() -> None:
    class NoTargetDate(Recorder):
        def __call__(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
            data = super().__call__(query, variables)
            if "projects(filter:{id:" in query:
                for row in data["projects"]["nodes"]:
                    row["targetDate"] = None
            return data

    recorder = NoTargetDate()
    with pytest.raises(NodeLinearTransportError, match="no due date"):
        _applied(recorder)
    assert recorder.mutations == []


def test_undo_restores_milestone_and_due_date_with_the_project_as_one_update(
    tmp_path: Path,
) -> None:
    """Restored field by field, the old milestone would be written while the ticket
    still sat in the new sprint, and the project restore after it would clear it."""
    manifest = tmp_path / "m.jsonl"
    _applied(Recorder(), manifest)
    undo = Recorder()
    reversed_writes, skipped = undo_from_manifest(undo, manifest)
    assert skipped == []
    assert len(reversed_writes) == 6
    assert [m["in"] for m in undo.mutations] == [
        {"projectId": str(P_OLD), "projectMilestoneId": MS_OLD, "dueDate": DUE_OLD}
    ] * 2
