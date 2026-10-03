# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The sprint roll's I/O: Linear reads, the writes, the journal and the undo.

Every network call in the roll lives here. The placement arithmetic is the COMPUTE
node's (OMN-20396) and is reached with data this module gathered, so the two halves can
be proven separately -- the arithmetic without an account, and the I/O against a recorded
transport.

THE TRANSPORT IS INJECTED, as a plain callable taking a query and variables. A test
passes a recorder and asserts what was sent; a dry run is then provable by what the
transport saw rather than by what this module claims it would have done.

TWO FACTS ABOUT THE BOARD shape this module and are easy to get wrong:

* The sprint window read returns only the current and future sprints, so a finished
  sprint is invisible to it. `resolve_source_window` asks the PROJECT list first, which
  has no window, and loads from the drained sprint's own start date. Without that a
  Monday run refuses with "nothing to roll" on a sprint that plainly ended on Sunday.
* The criterion carrier lists live in omninode_infra's `tools/beta_board`. They are read
  by the caller and passed in. A second copy here would disagree with the board the week
  one of them drifted.
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_write import (
    ModelSprintRollWrite,
)

__all__ = [
    "GraphQLTransport",
    "LinearTransportError",
    "SprintRollJournal",
    "http_transport",
    "label_uuid",
    "resolve_source_start",
    "state_uuid",
    "undo_from_manifest",
]

LINEAR_API = "https://api.linear.app/graphql"
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


class LinearTransportError(RuntimeError):
    """A Linear call failed in a way a retry will not fix."""


def http_transport(api_key: str, *, timeout: float = 120.0) -> GraphQLTransport:
    """A real transport over httpx, the client this package already depends on.

    httpx rather than `urllib.request.urlopen`: urlopen takes any scheme a caller can
    smuggle into the URL, which is what ruff's S310 is about, and it needs the certifi
    bundle wired in by hand. httpx verifies against certifi by default and only speaks
    HTTP.

    The key is passed as a header and never put in a URL, a log line or an exception
    message -- a transport error names the status and the attempt count, nothing else.
    """

    def call(query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = {"query": query, "variables": variables}
        headers = {"Authorization": api_key, "Content-Type": "application/json"}
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = httpx.post(
                    LINEAR_API, json=payload, headers=headers, timeout=timeout
                )
            except httpx.TransportError as exc:
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise LinearTransportError(
                    f"Linear unreachable after {attempt + 1} attempt(s)"
                ) from exc
            if response.status_code in RETRYABLE_STATUS and attempt < MAX_ATTEMPTS - 1:
                time.sleep(3 * (attempt + 1))
                continue
            if response.status_code >= 400:
                raise LinearTransportError(
                    f"Linear returned HTTP {response.status_code} after "
                    f"{attempt + 1} attempt(s)"
                )
            body = response.json()
            if "errors" in body:
                raise LinearTransportError(f"Linear API error: {body['errors']}")
            data = body.get("data")
            if not isinstance(data, dict):
                raise LinearTransportError("Linear returned no data object")
            return data
        raise LinearTransportError("Linear unreachable")

    return call


SPRINT_PROJECTS_QUERY = (
    'query{projects(first:100,filter:{name:{startsWith:"Sprint "}})'
    "{nodes{id name startDate targetDate}}}"
)


def resolve_source_start(transport: GraphQLTransport, as_of: dt.date) -> dt.date:
    """The start date of the sprint to drain, read from the PROJECT list.

    This exists because the board's sprint read returns only the current and future
    sprints: a finished sprint is invisible to it. Asking the project list first -- which
    has no window -- gives the drained sprint, and loading the window from ITS start date
    puts both it and every later sprint in scope. Without this a Monday 07:00 run refuses
    with "nothing to roll" on a sprint that plainly ended on Sunday.

    The containing sprint is the source only on its last day; otherwise the source is the
    one that ended most recently. Same rule as the COMPUTE node's, applied here to a
    different shape of data, because the window has to be fetched before the node that
    knows the rule can see it.
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
