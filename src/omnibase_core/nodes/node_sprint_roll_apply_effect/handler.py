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

Ticket: OMN-20397 (parent OMN-20395).
"""

from __future__ import annotations

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
from omnibase_core.nodes.node_sprint_roll_apply_effect.runtime_sprint_roll_apply import (
    GraphQLPayload,
    GraphQLTransport,
    node_rows,
)

if TYPE_CHECKING:
    from pydantic import JsonValue

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
    "project{id} state{id} labels{nodes{id}}}}}"
)


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

        planned: list[ModelSprintRollWrite] = []
        for placement in plan.placements:
            for identifier in placement.moved_in:
                node = by_identifier.get(identifier)
                if node is None:
                    continue
                project = node.get("project")
                before = project.get("id") if isinstance(project, dict) else None
                after = str(placement.sprint_id)
                if before == after:
                    continue
                planned.append(
                    ModelSprintRollWrite(
                        issue_uuid=str(node.get("id")),
                        identifier=identifier,
                        field="projectId",
                        before=(str(before),) if before else None,
                        after=(after,),
                    )
                )

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
        for write in planned:
            journal.send(self._transport, write)
            self._writes += 1
        return ModelSprintRollApplyResult(
            dry_run=False,
            writes=tuple(journal.writes),
            manifest_path=request.manifest_path,
            read_calls=self._reads,
            write_calls=self._writes,
        )
