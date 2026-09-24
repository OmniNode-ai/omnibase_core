# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical JSON-line parse and dump for the work ledger (OMN-16177, T3).

Each line of the JSONL work ledger is one ``ModelWorkLedgerRecord`` written by
``dump_work_ledger_line`` and read by ``parse_work_ledger_line``.

The dump is byte-deterministic: keys sorted, no whitespace, ASCII only, every
timestamp in UTC with a ``Z`` suffix, set-valued fields in sorted order, and no
trailing newline. So one event always has exactly one line, and an appender can
compare bytes to decide whether a retried event is already present.

The parse refuses every defect with ``WorkLedgerParseError``. It never skips a
line and never returns a partial record: an unknown ``schema`` or ``kind`` is an
error, because an older reader must not decide anything from a newer file.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

from pydantic import BaseModel, ValidationError

from omnibase_core.errors.error_work_ledger_parse import WorkLedgerParseError
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.events.work.model_work_ledger_record import (
    ModelWorkLedgerRecord,
)

__all__ = [
    "WORK_LEDGER_EVENTS_PATH_ENV",
    "dump_work_ledger_line",
    "events_path_from_env",
    "parse_work_ledger_line",
]

WORK_LEDGER_EVENTS_PATH_ENV: Final = "ONEX_WORK_LEDGER_PATH"
"""The one required variable naming the JSONL events file. It has no default."""


def events_path_from_env() -> Path:
    """Return the JSONL events file named by ``ONEX_WORK_LEDGER_PATH``.

    Reads the variable through the typed bootstrap boundary (OMN-17744).
    Raises ``KeyError`` naming the variable when it is unset or blank. There is
    no fallback path: a wrong default would put the ledger where no reader looks.
    """
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=(WORK_LEDGER_EVENTS_PATH_ENV,)
    )
    raw = bootstrap.environment.optional(WORK_LEDGER_EVENTS_PATH_ENV)
    if raw is None:
        # error-ok: the contract of this function is os.environ[...] semantics, a KeyError naming the variable
        raise KeyError(WORK_LEDGER_EVENTS_PATH_ENV)
    if not raw.strip():
        # error-ok: a blank value is the same failure as an unset one, and callers catch KeyError for both
        raise KeyError(f"{WORK_LEDGER_EVENTS_PATH_ENV} is set but blank")
    return Path(raw)


def _in_utc[T](value: T) -> tuple[T, bool]:
    """Return ``value`` with every nested timestamp converted to UTC.

    The second element says whether anything changed, so a model is rebuilt
    (and re-validated) only when it actually holds a non-UTC timestamp.
    """
    if isinstance(value, datetime):
        if value.tzinfo is UTC:
            return value, False
        return value.astimezone(UTC), True
    if isinstance(value, BaseModel):
        fields: dict[str, object] = {}
        changed = False
        for name in type(value).model_fields:
            field_value, field_changed = _in_utc(getattr(value, name))
            fields[name] = field_value
            changed = changed or field_changed
        if not changed:
            return value, False
        return type(value).model_validate(fields, by_name=True), True
    if isinstance(value, tuple | frozenset):
        items = [_in_utc(item) for item in value]
        if not any(item_changed for _, item_changed in items):
            return value, False
        return cast("T", type(value)(item for item, _ in items)), True
    return value, False


def dump_work_ledger_line(record: ModelWorkLedgerRecord) -> str:
    """Write ``record`` as its one canonical JSON line, with no trailing newline."""
    event, _ = _in_utc(record.event)
    canonical = ModelWorkLedgerRecord.model_validate(
        {"schema": record.ledger_schema, "event": event}
    )
    payload = canonical.model_dump(mode="json", by_alias=True)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            raise WorkLedgerParseError(f"duplicate key {key!r}")
        obj[key] = value
    return obj


def _reject_constant(name: str) -> object:
    raise WorkLedgerParseError(f"non-standard JSON constant {name}")


def parse_work_ledger_line(line: str) -> ModelWorkLedgerRecord:
    """Read one ledger line as a ``ModelWorkLedgerRecord``.

    ``line`` may end with one ``\\n`` (as read from a file) and must otherwise be
    exactly one JSON object with nothing before or after it. Validation is
    strict, so a value of the wrong JSON type (a quoted number, say) is refused
    rather than coerced. Raises ``WorkLedgerParseError`` on any defect.
    """
    body = line.removesuffix("\n")
    if not body:
        raise WorkLedgerParseError("empty line")
    if "\n" in body or "\r" in body:
        raise WorkLedgerParseError("line break inside the line")
    if not (body.startswith("{") and body.endswith("}")):
        raise WorkLedgerParseError(
            "not exactly one JSON object with nothing before or after it"
        )
    try:
        json.loads(
            body,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise WorkLedgerParseError(f"not valid JSON: {exc}") from exc
    try:
        return ModelWorkLedgerRecord.model_validate_json(body, strict=True)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or '<record>'}: {error['msg']}"
            for error in exc.errors(include_url=False)
        )
        raise WorkLedgerParseError(
            f"not a valid work-ledger record: {details}"
        ) from exc
