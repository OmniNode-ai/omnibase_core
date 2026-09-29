# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The projection read of ``onex-work-ledger --source`` (OMN-20002, plan task M5).

The effect boundary of the projection read. It fetches the confirmed events of
the lab work ledger from the projection-api snapshot cache and picks the local
tail: the events in this host's buffer that the projection has not confirmed.
Both are folded by the one pure fold, ``node_work_ledger_state_compute``, so the
union is safe: the fold is a function of the event set.

The surface is the projection-api's ``GET /projection/<topic>`` route, chosen
over direct SQL by a probe (plan section 14, decision 4): it is bus-fed, needs no
database credential on the reading host, and reports a stream watermark. The
base URL is ``ONEX_WORK_LEDGER_PROJECTION_URL`` and has no default.

Every fault is a ``WorkLedgerProjectionError``: an unset URL, an unreachable or
slow host, a non-200 answer (an unserved topic is a 404), a body that is not the
documented page, a page loop that does not end, or a snapshot the service marks
stale. The caller never reads CLEAR from a fault.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Final, NamedTuple

from pydantic import ValidationError

from omnibase_core.errors.error_work_ledger_projection import (
    WorkLedgerProjectionError,
)
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_projection_row import (
    ModelWorkLedgerProjectionRow,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_projection_snapshot import (
    ModelWorkLedgerProjectionSnapshot,
)

__all__ = [
    "PROJECTION_TOPIC",
    "PROJECTION_URL_ENV",
    "fetch_projection_snapshot",
    "local_tail",
]

PROJECTION_URL_ENV: Final = "ONEX_WORK_LEDGER_PROJECTION_URL"
"""Base URL of the projection-api, for example ``http://host:3002``. No default."""

PROJECTION_TOPIC: Final = "onex.snapshot.projection.work.ledger.v1"  # onex-allow-topic-literal  # env-var-ok: constant definition, the snapshot name the projection node serves under
"""The snapshot topic the projection node serves the work ledger under."""

_PAGE_LIMIT: Final = 500
_TIMEOUT_SECONDS: Final = 5.0
_MAX_PAGES: Final = 400
_ERROR_BODY_CHARS: Final = 120


def _projection_base_url() -> str:
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=(PROJECTION_URL_ENV,)
    )
    raw = bootstrap.environment.optional(PROJECTION_URL_ENV)
    if raw is None or not raw.strip():
        raise WorkLedgerProjectionError(
            "unconfigured",
            f"projection URL not configured: {PROJECTION_URL_ENV} is not set; "
            "it names the projection-api and has no default",
        )
    base = raw.strip().rstrip("/")
    try:
        scheme = urllib.parse.urlsplit(base).scheme
    except ValueError:
        scheme = ""
    if scheme not in {"http", "https"}:
        raise WorkLedgerProjectionError(
            "unconfigured",
            f"projection URL not configured: {PROJECTION_URL_ENV} must be an "
            "http or https URL",
        )
    return base


class _Page(NamedTuple):
    """One parsed response page. The wire body carries more keys than these; the
    projection-api adds keys without a version bump, so it is read by name here
    rather than through a strict model, and every key read is checked."""

    rows: tuple[ModelWorkLedgerProjectionRow, ...]
    next_cursor: str | None
    truncated: bool
    stale: bool
    applied_offset: int
    end_offset: int
    lag_records: int


def _invalid(detail: str) -> WorkLedgerProjectionError:
    return WorkLedgerProjectionError(
        "invalid", f"projection response is not the documented page: {detail}"
    )


def _count(block: dict[str, object], key: str) -> int:
    value = block[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _invalid(f"staleness.{key} is not a non-negative integer")
    return value


def _parse_page(body: bytes) -> _Page:
    """Read one response body. Raises WorkLedgerProjectionError on a shape defect.

    ``next_cursor`` and ``truncated`` are both required: a body that omits
    pagination must not be read as a whole ledger.
    """
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise _invalid("body is not a JSON object")
    raw_rows = payload["rows"]
    if not isinstance(raw_rows, list):
        raise _invalid("rows is not a list")
    rows = tuple(
        ModelWorkLedgerProjectionRow(event_id=row["event_id"], record=row["record"])
        for row in raw_rows
    )
    next_cursor = payload["next_cursor"]
    if next_cursor is not None and not isinstance(next_cursor, str):
        raise _invalid("next_cursor is neither null nor a string")
    truncated = payload["truncated"]
    if not isinstance(truncated, bool):
        raise _invalid("truncated is not a boolean")
    block = payload["staleness"]
    if not isinstance(block, dict):
        raise _invalid("staleness is not an object")
    stale = block["stale"]
    if not isinstance(stale, bool):
        raise _invalid("staleness.stale is not a boolean")
    return _Page(
        rows=rows,
        next_cursor=next_cursor,
        truncated=truncated,
        stale=stale,
        applied_offset=_count(block, "applied_offset"),
        end_offset=_count(block, "end_offset"),
        lag_records=_count(block, "lag_records"),
    )


def _fetch_page(base: str, cursor: str | None) -> _Page:
    query = {"limit": str(_PAGE_LIMIT)}
    if cursor is not None:
        query["cursor"] = cursor
    url = f"{base}/projection/{PROJECTION_TOPIC}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(  # noqa: S310  # the scheme is checked in _projection_base_url
        url, headers={"Accept": "application/json"}, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:_ERROR_BODY_CHARS].decode("utf-8", errors="replace")
        raise WorkLedgerProjectionError(
            f"http-{exc.code}",
            f"projection answered HTTP {exc.code} for {PROJECTION_TOPIC}: "
            f"{' '.join(detail.split())}",
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WorkLedgerProjectionError(
            "unreachable", f"projection unreachable: {exc}"
        ) from exc
    try:
        return _parse_page(body)
    except WorkLedgerProjectionError:
        raise
    except (ValueError, KeyError, TypeError, ValidationError) as exc:
        raise WorkLedgerProjectionError(
            "invalid", f"projection response is not the documented page: {exc}"
        ) from exc


def fetch_projection_snapshot() -> ModelWorkLedgerProjectionSnapshot:
    """Read every confirmed event from the projection-api, following the cursor.

    The watermark is the last page's. A page the service marks stale, a page that
    says it is truncated with no next cursor, a repeated cursor and a loop past the
    page cap are all faults: a partial ledger must never fold as a whole one.
    """
    base = _projection_base_url()
    rows: list[ModelWorkLedgerProjectionRow] = []
    seen: set[str] = set()
    cursor: str | None = None
    for _ in range(_MAX_PAGES):
        page = _fetch_page(base, cursor)
        if page.stale:
            raise WorkLedgerProjectionError(
                "stale",
                f"projection is stale: lag_records={page.lag_records} "
                f"applied_offset={page.applied_offset} "
                f"end_offset={page.end_offset}",
            )
        rows.extend(page.rows)
        if page.next_cursor is None:
            if page.truncated:
                raise WorkLedgerProjectionError(
                    "invalid",
                    "projection response is truncated with no next cursor",
                )
            return ModelWorkLedgerProjectionSnapshot(
                rows=tuple(rows),
                applied_offset=page.applied_offset,
                end_offset=page.end_offset,
                lag_records=page.lag_records,
            )
        if page.next_cursor in seen:
            raise WorkLedgerProjectionError(
                "invalid", f"projection repeated cursor {page.next_cursor}"
            )
        seen.add(page.next_cursor)
        cursor = page.next_cursor
    raise WorkLedgerProjectionError(
        "invalid", f"projection did not end within {_MAX_PAGES} pages"
    )


def _event_id(line: str) -> uuid.UUID | None:
    """The event id a buffer line claims, or None when it cannot be read."""
    try:
        record = json.loads(line)
        event = record["event"]
        return uuid.UUID(event["event_id"])
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def local_tail(
    local_lines: tuple[str, ...], snapshot: ModelWorkLedgerProjectionSnapshot
) -> tuple[str, ...]:
    """The buffer lines the projection has not confirmed.

    A line is confirmed only when the projection holds the same event id with
    the byte-identical record. A line with an id the projection holds but with
    different content stays in the tail, so the fold sees the conflict and
    answers UNDECIDED; a line that names no readable id stays too, so the fold
    reports that it does not parse. Neither is ever dropped quietly.
    """
    confirmed = {row.event_id: row.record for row in snapshot.rows}
    return tuple(
        line
        for line in local_lines
        if (event_id := _event_id(line)) is None or confirmed.get(event_id) != line
    )
