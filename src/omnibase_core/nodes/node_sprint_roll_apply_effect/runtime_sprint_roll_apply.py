# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
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
callable and re-calls it when the callable raises :class:`NodeLinearTransportError` (``node_linear_transport_error``) carrying a
retryable status. The adapter that knows what a 503 is lives with the client, outside this
package, and raises that typed error.
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import JsonValue

from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_write import (
    ModelSprintRollWrite,
)
from omnibase_core.nodes.node_sprint_roll_apply_effect.node_linear_transport_error import (
    NodeLinearTransportError,
)

__all__ = [
    "MAX_ATTEMPTS",
    "MUTATION",
    "RETRYABLE_STATUS",
    "GraphQLTransport",
    "label_uuid",
    "node_rows",
    "resolve_source_start",
    "state_uuid",
    "undo_from_manifest",
    "write_payload",
    "with_retries",
]

#: Linear answers 503 routinely under load and 429 on burst. Both are transient and the
#: roll is read-heavy enough to meet them; a persistent one must surface, not be
#: swallowed into a half-applied plan.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 6

#: A GraphQL variables map, and the `data` object a query answers with. Typed as
#: pydantic's JsonValue rather than Any: the shape genuinely is arbitrary JSON -- that is
#: what GraphQL returns -- but `GraphQLPayload` is an anti-pattern here and would also
#: let a caller pass something unserialisable without a word.
GraphQLPayload = dict[str, JsonValue]

#: (query, variables) -> the `data` object.
GraphQLTransport = Callable[[str, GraphQLPayload], GraphQLPayload]

MUTATION = (
    "mutation($id:String!,$in:IssueUpdateInput!)"
    "{issueUpdate(id:$id,input:$in){success}}"
)

SPRINT_PROJECTS_QUERY = (
    'query{projects(first:100,filter:{name:{startsWith:"Sprint "}})'
    "{nodes{id name startDate targetDate}}}"
)


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

    def call(query: str, variables: GraphQLPayload) -> GraphQLPayload:
        for attempt in range(attempts):
            try:
                return transport(query, variables)
            except NodeLinearTransportError as exc:
                retryable = exc.status in RETRYABLE_STATUS
                if not retryable or attempt == attempts - 1:
                    raise
                sleep(3 * (attempt + 1))
        raise NodeLinearTransportError("transport exhausted without a result")

    return call


def node_rows(data: GraphQLPayload, collection: str) -> list[GraphQLPayload]:
    """The `nodes` list under one collection, narrowed from arbitrary JSON.

    The payload is typed as JsonValue rather than Any, so every access has to be
    narrowed. That is the point: a Linear response that does not have the shape the query
    asked for raises here, naming the collection, instead of surfacing as an
    AttributeError somewhere inside a loop over it.
    """
    holder = data.get(collection)
    if not isinstance(holder, dict):
        raise NodeLinearTransportError(f"Linear returned no {collection} object")
    rows = holder.get("nodes")
    if not isinstance(rows, list):
        raise NodeLinearTransportError(f"Linear returned no {collection}.nodes list")
    return [row for row in rows if isinstance(row, dict)]


def _text(row: GraphQLPayload, key: str) -> str:
    value = row.get(key)
    return value if isinstance(value, str) else ""


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
    projects = node_rows(transport(SPRINT_PROJECTS_QUERY, {}), "projects")
    dated = sorted(
        (p for p in projects if _text(p, "startDate") and _text(p, "targetDate")),
        key=lambda p: _text(p, "startDate"),
    )
    if not dated:
        raise NodeLinearTransportError("no dated sprint project exists")
    iso = as_of.isoformat()
    containing = next(
        (p for p in dated if _text(p, "startDate") <= iso <= _text(p, "targetDate")),
        None,
    )
    if containing is not None and _text(containing, "targetDate") == iso:
        return dt.date.fromisoformat(_text(containing, "startDate"))
    ended = [p for p in dated if _text(p, "targetDate") < iso]
    if not ended:
        raise NodeLinearTransportError(
            f"no sprint has ended before {iso} and {iso} is not the last day of any "
            "sprint window, so there is nothing to roll"
        )
    return dt.date.fromisoformat(_text(ended[-1], "startDate"))


def label_uuid(transport: GraphQLTransport, name: str) -> str:
    """The id of one label, by exact name. Absent is a refusal, not a silent skip."""
    data = transport(
        "query($n:String!){issueLabels(filter:{name:{eq:$n}},first:1){nodes{id}}}",
        {"n": name},
    )
    rows = node_rows(data, "issueLabels")
    if not rows:
        raise NodeLinearTransportError(f"no label named {name!r}")
    return _text(rows[0], "id")


def state_uuid(transport: GraphQLTransport, team_key: str, state_name: str) -> str:
    """The id of one workflow state on one team."""
    data = transport(
        "query($t:String!,$s:String!){workflowStates(filter:{team:{key:{eq:$t}},"
        "name:{eq:$s}},first:1){nodes{id}}}",
        {"t": team_key, "s": state_name},
    )
    rows = node_rows(data, "workflowStates")
    if not rows:
        raise NodeLinearTransportError(
            f"team {team_key} has no state named {state_name!r}"
        )
    return _text(rows[0], "id")


#: Fields Linear takes as a single id. Everything else is a set.
SCALAR_FIELDS = frozenset({"projectId", "stateId"})


def _value(field: str, ids: tuple[str, ...] | None) -> JsonValue:
    """Unwrap the stored tuple into the shape Linear's input expects."""
    if field in SCALAR_FIELDS:
        return ids[0] if ids else None
    return list(ids or ())


def write_payload(write: ModelSprintRollWrite) -> GraphQLPayload:
    return {write.field: _value(write.field, write.after)}


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
        if record.before is None and record.field == "stateId":
            # A workflow state cannot be empty, so there is nothing to restore and
            # guessing one would be worse than reporting it.
            skipped.append(record)
            continue
        payload: GraphQLPayload = {record.field: _value(record.field, record.before)}
        transport(MUTATION, {"id": record.issue_uuid, "in": payload})
        reversed_writes.append(record)
    return reversed_writes, skipped
