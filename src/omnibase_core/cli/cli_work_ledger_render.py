# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex-work-ledger render --check | --repair`` (OMN-16182, plan T6).

The first divergence check of the typed work ledger: the JSON-lines ledger
(``ONEX_WORK_LEDGER_PATH``) is the truth, the md ledger (``--md`` or
``ONEX_LEDGER_PATH``) is its rendered view, and the two are compared by event id.

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
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
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

__all__ = [
    "EXIT_CLEAR",
    "EXIT_FOUND",
    "EXIT_UNDECIDED",
    "MD_LEDGER_PATH_ENV",
    "md_lock_path_for",
    "run_render",
]

EXIT_CLEAR: Final = 0
EXIT_FOUND: Final = 3
EXIT_UNDECIDED: Final = 2

MD_LEDGER_PATH_ENV: Final = "ONEX_LEDGER_PATH"
"""The variable naming the md ledger, as ``ledger_lock.py`` and the skills use it."""

# The md lock file, spelled as omnibase_infra scripts/ledger_lock.py spells it
# (OMN-19262 lock_path_for): <resolved parent>/.ledger_locks/<name>.<24-hex
# sha256 of the resolved path>.flock, in a directory that ignores its own
# contents. Every md writer takes this one file.
_LOCK_DIRNAME: Final = ".ledger_locks"
_LOCK_SUFFIX: Final = ".flock"
_LOCK_DIR_GITIGNORE: Final = (
    "# ledger_lock.py lock files, never tracked (OMN-19262)\n*\n"
)
_LOCK_TIMEOUT_SECONDS: Final = 30.0
_LOCK_POLL_SECONDS: Final = 0.05

_UUID: Final = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_EVENT_CELL_RE: Final = re.compile(rf"^event=(?P<id>{_UUID})$")
_ROW_START_RE: Final = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \|")


_JsonlRead = tuple[str, str, int, tuple[ModelWorkEvent, ...], str]
"""The JSON-lines ledger as read: path, sha256, line count, events, newest epoch id."""

_MdRead = tuple[str, str, int, str, tuple[str, ...]]
"""The md ledger as read: text, sha256, line count, header line, typed event ids."""


def md_lock_path_for(md: Path) -> Path:
    """The one fcntl lock file every writer of the md ledger ``md`` takes."""
    resolved = md.resolve()
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:24]
    return resolved.parent / _LOCK_DIRNAME / f"{resolved.name}.{digest}{_LOCK_SUFFIX}"


def run_render(mode: str, md_option: str | None) -> tuple[int, list[str]]:
    """Run ``render --check`` (mode ``check``) or ``--repair`` (mode ``repair``).

    Returns the exit code and the output lines. Never raises for a doubt about
    either file; every doubt is one ``reason=`` line and exit 2.
    """
    headers: list[str] = []
    try:
        path, sha256, line_count, read_events, epoch = _read_jsonl()
        headers.append(
            f"ledger={path} sha256={sha256} lines={line_count} epoch={epoch}"
        )
        md_path = _md_path(md_option)
        md = _read_md(md_path)
        headers.append(md[3])
        index = index_events(read_events)
        # An identical duplicate line counts once; index_events refused a conflicting one.
        events = tuple(index.values())
        if mode == "repair":
            return _repair(headers[0], events, md_path, index)
        return _compare([*headers], "check", events, md[4], repaired=None)
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


def _read_jsonl() -> _JsonlRead:
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
    return str(path), hashlib.sha256(raw).hexdigest(), len(lines), tuple(events), epoch


def _md_path(md_option: str | None) -> Path:
    if md_option is not None:
        if not md_option.strip():
            raise WorkLedgerUndecidedError(
                "--md is blank"
            )  # error-ok: carried to a reason= line
        return Path(md_option)
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=(MD_LEDGER_PATH_ENV,)
    )
    raw = bootstrap.environment.optional(MD_LEDGER_PATH_ENV)
    if raw is None or not raw.strip():
        raise WorkLedgerUndecidedError(  # error-ok: carried to a reason= line
            f"{MD_LEDGER_PATH_ENV} is not set and --md was not given; one names the md "
            "ledger and there is no default"
        )
    return Path(raw)


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
        deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise WorkLedgerUndecidedError(  # error-ok: carried to a reason= line
                        f"md lock {lock_file} not taken within "
                        f"{_LOCK_TIMEOUT_SECONDS:.0f}s; another writer holds it"
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
