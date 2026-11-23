# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex-work-ledger render --check | --repair`` (OMN-16182, plan T6).

The first divergence check of the typed work ledger: the typed events are the
truth, the md view named by ``--md`` is their rendering, and the two are compared
by event id. The events come from the bus-backed projection client
(``--source projection``, the default; the caller fetches the snapshot and hands
this module its lines) or, with ``--source local``, from the JSON-lines buffer
(``ONEX_WORK_LEDGER_PATH``). The md view has no environment default: it is a file
the operator names, never the ledger of record (OMN-26514).

- ``md-ahead``: the md holds a typed row (an ``event=<uuid>`` cell followed by
  ``src=typed``) whose event is not in the JSONL. The md is never allowed to be
  ahead of the truth, and ``--repair`` cannot fix it.
- ``md-missing``: a JSONL event has no md row. An append that stopped between
  its JSONL write and its md write leaves this; ``--repair`` restores it.

``--check`` reads both files and writes nothing. ``--repair`` renders every
missing row first and, only if all of them render, appends them in JSONL order
in one write under the md's fcntl lock file (the OMN-19262 lock path of
``ledger_lock.py``), so a repair never interleaves with an md append. A second
repair finds nothing missing and changes nothing.

Exit codes follow the read CLI: 0 when the two agree (after a repair, when
nothing is still divergent), 3 when a divergence is found or remains, 2 when
the answer is undecided: a variable unset, a file unreadable, a JSONL line that
does not parse, a conflicting duplicate event id, a missing row that cannot be
rendered, or the md lock not taken in time.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import time
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Final

from omnibase_core.errors.error_work_ledger_parse import WorkLedgerParseError
from omnibase_core.errors.error_work_ledger_render import WorkLedgerRenderError
from omnibase_core.errors.error_work_ledger_undecided import WorkLedgerUndecidedError
from omnibase_core.handlers import handler_ledger_write_guard as write_guard
from omnibase_core.models.events.work.model_work_event_union import ModelWorkEvent
from omnibase_core.models.events.work.model_work_ledger_epoch_opened import (
    ModelWorkLedgerEpochOpened,
)
from omnibase_core.models.events.work.model_work_ledger_line import (
    WORK_LEDGER_EVENTS_PATH_ENV,
    complete_ledger_lines,
    events_path_from_env,
    parse_work_ledger_line,
)
from omnibase_core.models.events.work.model_work_ledger_render import (
    TYPED_SOURCE_CELL,
    index_events,
    render_ledger_row,
)
from omnibase_core.models.runtime.model_operational_timeouts import packaged_timeouts

__all__ = [
    "EXIT_CLEAR",
    "EXIT_FOUND",
    "EXIT_TEST_WRITE_REFUSED",
    "EXIT_UNDECIDED",
    "md_lock_path_for",
    "run_render",
]

EXIT_CLEAR: Final = 0
EXIT_FOUND: Final = 3
EXIT_UNDECIDED: Final = 2
EXIT_TEST_WRITE_REFUSED: Final = write_guard.EXIT_TEST_WRITE_REFUSED

# The md lock file, spelled as omnibase_infra scripts/ledger_lock.py spells it
# (OMN-19262 lock_path_for): <resolved parent>/.ledger_locks/<name>.<24-hex
# sha256 of the resolved path>.flock, in a directory that ignores its own
# contents. Every md writer takes this one file.
_LOCK_DIRNAME: Final = ".ledger_locks"
_LOCK_SUFFIX: Final = ".flock"
_LOCK_DIR_GITIGNORE: Final = (
    "# ledger_lock.py lock files, never tracked (OMN-19262)\n*\n"
)
_LOCK_POLL_SECONDS: Final = 0.05

_UUID: Final = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_EVENT_CELL_RE: Final = re.compile(rf"^event=(?P<id>{_UUID})$")
_ROW_START_RE: Final = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \|")


_JsonlRead = tuple[str, str, int, tuple[ModelWorkEvent, ...], str]
"""The JSON-lines ledger as read: path, sha256, line count, events, newest epoch id."""

_Projected = tuple[str, str | None, tuple[str, ...], str | None]
"""The bus-backed client's read: label, sha256, ledger lines and any doubt about them."""

_MdRead = tuple[str, str, int, str, tuple[str, ...]]
"""The md ledger as read: text, sha256, line count, header line, typed event ids."""


def md_lock_path_for(md: Path) -> Path:
    """The one fcntl lock file every writer of the md ledger ``md`` takes."""
    resolved = md.resolve()
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:24]
    return resolved.parent / _LOCK_DIRNAME / f"{resolved.name}.{digest}{_LOCK_SUFFIX}"


def run_render(
    mode: str, md_option: str | None, projected: _Projected | None = None
) -> tuple[int, list[str]]:
    """Run ``render --check`` (mode ``check``) or ``--repair`` (mode ``repair``).

    ``projected`` is the bus-backed client's read: its label, its ledger lines and
    any doubt about them (a doubt is undecided, never a fallback to the local file).
    Not given, the events are read from the JSON-lines buffer.

    Returns the exit code and the output lines. Never raises for a doubt about
    either file; every doubt is one ``reason=`` line and exit 2.
    """
    headers: list[str] = []
    try:
        path, sha256, line_count, read_events, epoch = _read_jsonl(projected)
        headers.append(
            f"ledger={path} sha256={sha256} lines={line_count} epoch={epoch}"
        )
        if md_option is None or not md_option.strip():
            raise WorkLedgerUndecidedError(  # error-ok: carried to a reason= line
                "--md is required and has no default"
            )
        md_path = Path(md_option)
        md = _read_md(md_path)
        headers.append(md[3])
        index = index_events(read_events)
        # An identical duplicate line counts once; index_events refused a conflicting one.
        events = tuple(index.values())
        if mode == "repair":
            write_guard.check_file(md_path)
            return _repair(headers[0], events, md_path, index)
        return _compare([*headers], "check", events, md[4], repaired=None)
    except write_guard.ModelLedgerTestWriteRefusedError as exc:
        return write_guard.EXIT_TEST_WRITE_REFUSED, [
            *headers,
            f"verdict=refused guard={write_guard.GUARD_NAME} mode={mode}",
            f"reason={_one_line(str(exc))}",
        ]
    except (WorkLedgerUndecidedError, WorkLedgerRenderError) as exc:
        reason = exc.reason
        if not headers:
            headers.append("ledger=<unread> sha256=none lines=0 epoch=none")
        return EXIT_UNDECIDED, [
            *headers,
            f"verdict=undecided query=render mode={mode}",
            f"reason={_one_line(reason)}",
        ]


# ------------------------------------------------------------------ compare


def _divergence(
    events: tuple[ModelWorkEvent, ...], md_event_ids: tuple[str, ...]
) -> tuple[list[str], list[str]]:
    truth = {str(event.event_id) for event in events}
    shown = set(md_event_ids)
    ahead = sorted(shown - truth)
    missing = [str(e.event_id) for e in events if str(e.event_id) not in shown]
    return ahead, missing


def _compare(
    headers: list[str],
    mode: str,
    events: tuple[ModelWorkEvent, ...],
    md_event_ids: tuple[str, ...],
    repaired: int | None,
) -> tuple[int, list[str]]:
    ahead, missing = _divergence(events, md_event_ids)
    status, code = ("found", EXIT_FOUND) if ahead or missing else ("clear", EXIT_CLEAR)
    summary = (
        f"verdict={status} query=render mode={mode} events={len(events)} "
        f"md_rows={len(set(md_event_ids))} md_ahead={len(ahead)} "
        f"md_missing={len(missing)}"
    )
    if repaired is not None:
        summary += f" repaired={repaired}"
    lines = [*headers, summary]
    lines.extend(f"divergence=md-ahead event={event_id}" for event_id in ahead)
    lines.extend(f"divergence=md-missing event={event_id}" for event_id in missing)
    return code, lines


def _repair(
    ledger_header: str,
    events: tuple[ModelWorkEvent, ...],
    md_path: Path,
    index: Mapping[uuid.UUID, ModelWorkEvent],
) -> tuple[int, list[str]]:
    with _md_lock(md_path):
        # Re-read under the lock: an md append may have landed since the first read.
        text, _, _, _, md_event_ids = _read_md(md_path)
        _, missing = _divergence(events, md_event_ids)
        wanted = set(missing)
        rows = [
            render_ledger_row(event, index)
            for event in events
            if str(event.event_id) in wanted
        ]
        if rows:
            separator = "" if not text or text.endswith("\n") else "\n"
            with md_path.open("a", encoding="utf-8") as handle:
                handle.write(separator + "".join(row + "\n" for row in rows))
                handle.flush()
                os.fsync(handle.fileno())
        after = _read_md(md_path)
    code, lines = _compare(
        [ledger_header, after[3]], "repair", events, after[4], repaired=len(rows)
    )
    return code, [*lines, *(f"repaired event={event_id}" for event_id in missing)]


# -------------------------------------------------------------------- reads


def _read_jsonl(projected: _Projected | None) -> _JsonlRead:
    if projected is not None:
        label, digest, projected_lines, doubt = projected
        if doubt is not None:
            raise WorkLedgerUndecidedError(doubt)  # error-ok: carried to a reason= line
        return _parse_events(label, digest or "none", projected_lines)
    try:
        path = events_path_from_env()
    except KeyError:
        raise WorkLedgerUndecidedError(  # error-ok: carried to a reason= line, never raised out of run_render
            f"{WORK_LEDGER_EVENTS_PATH_ENV} is not set; it names the JSON-lines ledger "
            "and has no default"
        ) from None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise WorkLedgerUndecidedError(
            f"ledger unreadable: {exc}"
        ) from exc  # error-ok: carried to a reason= line
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorkLedgerUndecidedError(
            f"ledger is not UTF-8: {exc}"
        ) from exc  # error-ok: carried to a reason= line
    lines = complete_ledger_lines(text)
    return _parse_events(str(path), hashlib.sha256(raw).hexdigest(), lines)


def _parse_events(path: str, sha256: str, lines: tuple[str, ...]) -> _JsonlRead:
    events: list[ModelWorkEvent] = []
    for number, line in enumerate(lines, start=1):
        try:
            events.append(parse_work_ledger_line(line).event)
        except WorkLedgerParseError as exc:
            raise WorkLedgerUndecidedError(
                f"ledger line {number}: {exc.reason}"
            ) from exc  # error-ok: carried to a reason= line
    epochs = [e for e in events if isinstance(e, ModelWorkLedgerEpochOpened)]
    epoch = str(max(epochs, key=lambda e: e.epoch_seq).event_id) if epochs else "none"
    return path, sha256, len(lines), tuple(events), epoch


def _read_md(path: Path) -> _MdRead:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise WorkLedgerUndecidedError(
            f"md ledger unreadable: {exc}"
        ) from exc  # error-ok: carried to a reason= line
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorkLedgerUndecidedError(
            f"md ledger is not UTF-8: {exc}"
        ) from exc  # error-ok: carried to a reason= line
    sha256 = hashlib.sha256(raw).hexdigest()
    line_count = len(text.splitlines())
    event_ids = tuple(
        event_id
        for line in complete_ledger_lines(text)
        if (event_id := _typed_event_id(line)) is not None
    )
    return (
        text,
        sha256,
        line_count,
        f"md={path} sha256={sha256} lines={line_count}",
        event_ids,
    )


def _typed_event_id(line: str) -> str | None:
    """The event id of a typed md row: the ``event=`` cell just before ``src=typed``."""
    if _ROW_START_RE.match(line) is None:
        return None
    cells = [cell.strip() for cell in line.split("|")]
    if TYPED_SOURCE_CELL not in cells:
        return None
    position = cells.index(TYPED_SOURCE_CELL)
    if position == 0:
        return None
    match = _EVENT_CELL_RE.match(cells[position - 1])
    return None if match is None else match.group("id")


# --------------------------------------------------------------------- lock


@contextmanager
def _md_lock(md: Path) -> Iterator[None]:
    lock_file = md_lock_path_for(md)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    ignore = lock_file.parent / ".gitignore"
    if not ignore.exists():
        ignore.write_text(_LOCK_DIR_GITIGNORE, encoding="utf-8")
    fd = os.open(lock_file, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        deadline = time.monotonic() + packaged_timeouts().work_ledger_lock_seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise WorkLedgerUndecidedError(  # error-ok: carried to a reason= line
                        f"md lock {lock_file} not taken within "
                        f"{packaged_timeouts().work_ledger_lock_seconds:.0f}s; another writer holds it"
                    ) from None
                time.sleep(_LOCK_POLL_SECONDS)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _one_line(text: str) -> str:
    return " ".join(text.split())
