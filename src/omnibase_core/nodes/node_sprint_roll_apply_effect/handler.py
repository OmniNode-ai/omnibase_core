# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeSprintRollApplyEffect — applies a sprint roll plan to Linear.

Architecture: EFFECT node. It writes, and it is the only half of the roll that does; the
placement arithmetic is the paired COMPUTE node's (OMN-20396) and arrives here already
decided, on :class:`ModelSprintRollApplyRequest`.

Two properties this handler exists to guarantee:

* A dry run sends nothing. It is the default, and it is provable from the transport
  rather than from anything this class reports about itself.
* Every mutation is journalled before it is sent, so a run interrupted halfway still
  leaves a manifest that reverses what it managed to do. The operator's rule for this
  roll is best guess now, audit after the sprint starts, and an audit with no undo is
  just a record of damage.

A sprint move is three fields, not one (OMN-21085). Linear clears `projectMilestoneId`
when `projectId` changes and leaves `dueDate` where it was, so a project-only move lands
every ticket with no milestone -- which drops it from the board -- and a due date outside
its new window. Each moved ticket is therefore one `issueUpdate` carrying the project, the
destination's milestone and the destination's end date, read back afterwards.

Ticket: OMN-20397 (parent OMN-20395); three-field move OMN-21085.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_apply_request import (
    ModelSprintRollApplyRequest,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_apply_result import (
    ModelSprintRollApplyResult,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_write import (
    ModelSprintRollWrite,
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
    GraphQLPayload,
    GraphQLTransport,
    node_rows,
    readback_mismatches,
)

if TYPE_CHECKING:
    from pydantic import JsonValue

    from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_plan import (
        ModelSprintRollPlan,
    )

__all__ = ["NodeSprintRollApplyEffect"]

#: Linear's issue read, for the facts a placement plan does not carry: the issue's own
#: uuid (the plan speaks in identifiers), and what its project and state hold now, which
#: is what an undo restores.
#:
#: FILTERED BY `number`, NOT `identifier`. `IssueFilter` has no `identifier` field --
#: Linear answers `Field "identifier" is not defined by type "IssueFilter"` with HTTP
#: 400 -- so an earlier version of this query made `handle` fail on every plan that
#: moved anything. No test caught it: a recorded transport answers whatever query it is
#: handed, so a unit suite can prove the ORDER of calls but never their validity against
#: the live schema. `test_the_issue_query_filters_by_number_not_identifier` asserts the
#: shape instead.
ISSUE_QUERY = (
    'query($nums:[Float!]!){issues(filter:{team:{key:{eq:"OMN"}},'
    "number:{in:$nums}},first:250){nodes{id identifier "
    "project{id} projectMilestone{id name} dueDate state{id} labels{nodes{id}}}}}"
)

#: The destination sprints: each one's end date, which becomes the moved ticket's due
#: date, and its milestones, one of which the moved ticket joins.
PROJECT_QUERY = (
    "query($ids:[ID!]!){projects(filter:{id:{in:$ids}},first:50)"
    "{nodes{id targetDate projectMilestones{nodes{id name}}}}}"
)


def _text(row: JsonValue, key: str) -> str | None:
    value = row.get(key) if isinstance(row, dict) else None
    return value if isinstance(value, str) and value else None


def destination_milestone(
    current_name: str | None, milestones: list[GraphQLPayload]
) -> str | None:
    """The milestone a ticket joins in the sprint it moves into.

    The one with the SAME NAME as the milestone it leaves, because the sprints carry the
    same milestone forward week to week ("M4 -- Delegation and customer pass proven") and
    some declare a second one beside it. Failing a name match, the sprint's only
    milestone. Failing that, none: guessing between two would file work under a goal it
    was never part of, and a blank is at least visible.
    """
    if current_name is not None:
        for milestone in milestones:
            if _text(milestone, "name") == current_name:
                return _text(milestone, "id")
    if len(milestones) == 1:
        return _text(milestones[0], "id")
    return None


def issue_numbers(identifiers: list[str]) -> list[float]:
    """`OMN-20395` -> `20395.0`, the only form `IssueFilter.number` accepts.

    An identifier that does not carry a number is dropped rather than guessed: it cannot
    name a Linear issue, so sending it would widen the filter rather than narrow it.
    """
    numbers: list[float] = []
    for identifier in identifiers:
        _, _, tail = identifier.rpartition("-")
        if tail.isdigit():
            numbers.append(float(tail))
    return sorted(set(numbers))


class NodeSprintRollApplyEffect:
    """EFFECT handler that turns a roll plan into Linear mutations."""

    def __init__(self, transport: GraphQLTransport) -> None:
        self._transport = transport
        self._reads = 0
        self._writes = 0

    def _read(self, query: str, variables: GraphQLPayload) -> GraphQLPayload:
        self._reads += 1
        return self._transport(query, variables)

    def _destinations(
        self, plan: ModelSprintRollPlan
    ) -> dict[str, tuple[str, list[GraphQLPayload]]]:
        """Each destination sprint's end date and milestones, keyed by project id.

        Read before anything is written, and a sprint that is missing or has no end date
        refuses the whole plan: a due date cannot be derived from it, and a refusal now
        leaves nothing half applied.
        """
        ids: list[JsonValue] = list(
            sorted({str(p.sprint_id) for p in plan.placements if p.moved_in})
        )
        if not ids:
            return {}
        rows = node_rows(self._read(PROJECT_QUERY, {"ids": ids}), "projects")
        found: dict[str, tuple[str, list[GraphQLPayload]]] = {}
        for row in rows:
            project_id = _text(row, "id")
            target_date = _text(row, "targetDate")
            if project_id is None or target_date is None:
                continue
            holder = row.get("projectMilestones")
            milestones = node_rows(row, "projectMilestones") if holder else []
            found[project_id] = (target_date, milestones)
        missing = [str(i) for i in ids if str(i) not in found]
        if missing:
            raise NodeLinearTransportError(
                "no target date could be read for destination sprint(s) "
                + ", ".join(missing)
                + ", so no due date can be set and nothing was written"
            )
        return found

    def handle(
        self, request: ModelSprintRollApplyRequest
    ) -> ModelSprintRollApplyResult:
        """Definition-B canonical entry-point."""
        plan = request.plan
        wanted = [t for p in plan.placements for t in p.moved_in]
        wanted += list(plan.backlog_ticket_ids)
        if not wanted:
            return ModelSprintRollApplyResult(
                dry_run=request.dry_run, read_calls=0, write_calls=0
            )

        nums: list[JsonValue] = list(issue_numbers(wanted))
        if not nums:
            raise NodeLinearTransportError(
                "no plan ticket carries a Linear issue number, so nothing can be read"
            )
        current = self._read(ISSUE_QUERY, {"nums": nums})
        by_identifier = {
            str(node.get("identifier")): node for node in node_rows(current, "issues")
        }

        destinations = self._destinations(plan)
        updates: list[list[ModelSprintRollWrite]] = []
        for placement in plan.placements:
            for identifier in placement.moved_in:
                node = by_identifier.get(identifier)
                if node is None:
                    continue
                before = _text(node.get("project"), "id")
                after = str(placement.sprint_id)
                if before == after:
                    continue
                target_date, milestones = destinations[after]
                held_milestone = node.get("projectMilestone")
                milestone_before = _text(held_milestone, "id")
                milestone_after = destination_milestone(
                    _text(held_milestone, "name"),
                    milestones,
                )
                due_before = _text(node, "dueDate")
                batch = uuid.uuid4().hex
                issue_uuid = str(node.get("id"))
                updates.append(
                    [
                        ModelSprintRollWrite(
                            issue_uuid=issue_uuid,
                            identifier=identifier,
                            field=field,
                            before=(was,) if was else None,
                            after=(now,) if now else None,
                            batch=batch,
                        )
                        for field, was, now in (
                            ("projectId", before, after),
                            ("projectMilestoneId", milestone_before, milestone_after),
                            ("dueDate", due_before, target_date),
                        )
                    ]
                )
        planned = [write for update in updates for write in update]

        if request.dry_run:
            # Nothing is sent and nothing is journalled: a dry run that wrote a manifest
            # would leave an undo record for writes that never happened.
            return ModelSprintRollApplyResult(
                dry_run=True,
                writes=tuple(planned),
                manifest_path=None,
                read_calls=self._reads,
                write_calls=0,
            )

        journal = NodeSprintRollJournal(request.manifest_path)
        for update in updates:
            journal.send_together(self._transport, update)
            self._writes += 1
            self._reads += 1
            mismatches = readback_mismatches(self._transport, update)
            if mismatches:
                raise NodeSprintRollReadbackError(
                    "Linear does not hold what the roll wrote, so the roll stops here "
                    "and the manifest undoes it: " + "; ".join(mismatches)
                )
        return ModelSprintRollApplyResult(
            dry_run=False,
            writes=tuple(journal.writes),
            manifest_path=request.manifest_path,
            read_calls=self._reads,
            write_calls=self._writes,
        )
