"""The sprint roll's write journal, undo replay and Linear query shapes.

The placement arithmetic is the COMPUTE node's (OMN-20396) and is reached with data
gathered through the transport this module is handed.

THE TRANSPORT IS INJECTED AND NEVER CONSTRUCTED HERE. ADR-005 forbids a transport import
anywhere in omnibase_core -- no httpx, aiohttp, requests or urllib3 -- and the
url-authority gate forbids a URL literal, which must resolve from a contract rather than
from a constant in a module. Both refused an earlier version of this file that built its
own HTTP client. The caller owns the client and the endpoint; this module owns the write
ordering, the undo and the query text, and a test passes a recorder and asserts what was
sent.

`with_retries` is the retry POLICY, which is not a transport: it wraps an injected
callable and re-calls it when the callable raises :class:`LinearTransportError` carrying a
retryable status. The adapter that knows what a 503 is lives with the client, outside this
package, and raises that typed error.
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_write import (
    ModelSprintRollWrite,
)

__all__ = [
    "MAX_ATTEMPTS",
    "RETRYABLE_STATUS",
    "GraphQLTransport",
    "LinearTransportError",
    "SprintRollJournal",
    "label_uuid",
    "resolve_source_start",
    "state_uuid",
    "undo_from_manifest",
    "with_retries",
]

#: Linear answers 503 routinely under load and 429 on burst. Both are transient and the
#: roll is read-heavy enough to meet them; a persistent one must surface, not be
#: swallowed into a half-applied plan.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 6

#: (query, variables) -> the `data` object.
GraphQLTransport = Callable[[str, dict[str, Any]], dict[str, Any]]

MUTATION = (
    "mutation($id:String!,$in:IssueUpdateInput!)"
    "{issueUpdate(id:$id,input:$in){success}}"
)

SPRINT_PROJECTS_QUERY = (
    'query{projects(first:100,filter:{name:{startsWith:"Sprint "}})'
    "{nodes{id name startDate targetDate}}}"
)


class LinearTransportError(RuntimeError):
    """A Linear call failed.

    `status` is the HTTP status when the caller's adapter knows one, and None otherwise.
    It is the only thing this package needs to know about HTTP, and it arrives as data
    rather than as an imported client type.
    """

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def with_retries(
    transport: GraphQLTransport,
    *,
    attempts: int = MAX_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
) -> GraphQLTransport:
    """Retry an injected transport on a retryable status; surface anything else.

    A retry policy, not a transport: it knows nothing about sockets, TLS or URLs. A
    failure swallowed mid-plan would leave the board half rolled, so exhaustion re-raises
    the last error rather than returning anything.
    """

    def call(query: str, variables: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(attempts):
            try:
                return transport(query, variables)
            except LinearTransportError as exc:
                retryable = exc.status in RETRYABLE_STATUS
                if not retryable or attempt == attempts - 1:
                    raise
                sleep(3 * (attempt + 1))
        raise LinearTransportError("transport exhausted without a result")

    return call


def resolve_source_start(transport: GraphQLTransport, as_of: dt.date) -> dt.date:
    """The start date of the sprint to drain, read from the PROJECT list.

    This exists because the board's sprint read returns only the current and future
    sprints: a finished sprint is invisible to it. Asking the project list first -- which
    has no window -- gives the drained sprint, and loading the window from ITS start date
    puts both it and every later sprint in scope. Without this a Monday 07:00 run refuses
    with "nothing to roll" on a sprint that plainly ended on Sunday.

    The containing sprint is the source only on its last day; otherwise the source is the
    one that ended most recently.
    """
    projects = transport(SPRINT_PROJECTS_QUERY, {})["projects"]["nodes"]
    dated = sorted(
        (p for p in projects if p.get("startDate") and p.get("targetDate")),
        key=lambda p: str(p["startDate"]),
    )
    if not dated:
        raise LinearTransportError("no dated sprint project exists")
    iso = as_of.isoformat()
    containing = next(
        (p for p in dated if str(p["startDate"]) <= iso <= str(p["targetDate"])), None
    )
    if containing is not None and str(containing["targetDate"]) == iso:
        return dt.date.fromisoformat(str(containing["startDate"]))
    ended = [p for p in dated if str(p["targetDate"]) < iso]
    if not ended:
        raise LinearTransportError(
            f"no sprint has ended before {iso} and {iso} is not the last day of any "
            "sprint window, so there is nothing to roll"
        )
    return dt.date.fromisoformat(str(ended[-1]["startDate"]))


def label_uuid(transport: GraphQLTransport, name: str) -> str:
    """The id of one label, by exact name. Absent is a refusal, not a silent skip."""
    data = transport(
        "query($n:String!){issueLabels(filter:{name:{eq:$n}},first:1){nodes{id}}}",
        {"n": name},
    )
    nodes = data["issueLabels"]["nodes"]
    if not nodes:
        raise LinearTransportError(f"no label named {name!r}")
    return str(nodes[0]["id"])


def state_uuid(transport: GraphQLTransport, team_key: str, state_name: str) -> str:
    """The id of one workflow state on one team."""
    data = transport(
        "query($t:String!,$s:String!){workflowStates(filter:{team:{key:{eq:$t}},"
        "name:{eq:$s}},first:1){nodes{id}}}",
        {"t": team_key, "s": state_name},
    )
    nodes = data["workflowStates"]["nodes"]
    if not nodes:
        raise LinearTransportError(f"team {team_key} has no state named {state_name!r}")
    return str(nodes[0]["id"])


class SprintRollJournal:
    """Appends each write to a manifest BEFORE the transport is asked to send it.

    The ordering is the guarantee. A crash between the journal line and the mutation
    leaves a manifest entry for a write that never happened, and undoing that is a no-op;
    the reverse ordering would leave a write with no record, which nothing can undo.
    """

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.writes: list[ModelSprintRollWrite] = []

    def record(self, write: ModelSprintRollWrite) -> None:
        self.writes.append(write)
        if self.path is None:
            return
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(write.model_dump_json() + "\n")
            handle.flush()

    def send(self, transport: GraphQLTransport, write: ModelSprintRollWrite) -> None:
        """Journal, then mutate. Never the other way round."""
        self.record(write)
        transport(MUTATION, {"id": write.issue_uuid, "in": _payload(write)})


def _payload(write: ModelSprintRollWrite) -> dict[str, Any]:
    if write.field == "labelIds":
        after = write.after or ()
        return {"labelIds": list(after)}
    return {write.field: write.after}


def undo_from_manifest(
    transport: GraphQLTransport, path: Path
) -> tuple[list[ModelSprintRollWrite], list[ModelSprintRollWrite]]:
    """Replay a manifest's prior values, newest write first.

    Returns (reversed, skipped). A field whose `before` is null is REPORTED rather than
    guessed: null means the field held nothing, and for a project move that is a ticket
    which belonged to no sprint. Writing null back is a legitimate restore for a project
    but not for a workflow state, which cannot be empty, so the two are not treated
    alike.
    """
    records = [
        ModelSprintRollWrite.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    reversed_writes: list[ModelSprintRollWrite] = []
    skipped: list[ModelSprintRollWrite] = []
    for record in reversed(records):
        if record.field == "labelIds":
            payload: dict[str, Any] = {"labelIds": list(record.before or ())}
        elif record.before is None:
            if record.field == "projectId":
                payload = {"projectId": None}
            else:
                skipped.append(record)
                continue
        else:
            payload = {record.field: record.before}
        transport(MUTATION, {"id": record.issue_uuid, "in": payload})
        reversed_writes.append(record)
    return reversed_writes, skipped
