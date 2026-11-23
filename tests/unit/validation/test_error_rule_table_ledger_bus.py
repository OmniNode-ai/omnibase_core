# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-26513: the error-rule table validator reads ledger sources from the bus, not from a file.

A row's ``ledger:<stamp>`` and ``ticket:<id>`` sources resolve against the ruling and
operator-consent events of the work ledger projection (the in-core bus read behind
``onex-work-ledger --source``). Every test here runs with ``ONEX_LEDGER_PATH`` unset and no
ledger file on disk, so a validator that still opens the file resolves nothing and fails.
"""

from __future__ import annotations

import builtins
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.errors.error_work_ledger_projection import (
    WorkLedgerProjectionError,
)
from omnibase_core.models.events.work import (
    ModelSessionActor,
    ModelWorkOperatorConsentRecorded,
    ModelWorkStatusRecorded,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_projection_snapshot import (
    ModelWorkLedgerProjectionSnapshot,
)
from omnibase_core.validation import validator_error_rule_table
from omnibase_core.validation.validator_error_rule_table import ValidatorErrorRuleTable
from tests.conftest import LEDGER_PATH_ENV
from tests.unit.validation.test_error_rule_table import (
    project_events,
    row,
    ruling_event,
)

pytestmark = pytest.mark.unit

PROJECTION_URL_ENV = "ONEX_WORK_LEDGER_PROJECTION_URL"
STAMP = "2026-11-04T17:10:13Z"


def _consent() -> ModelWorkOperatorConsentRecorded:
    return ModelWorkOperatorConsentRecorded(
        event_id=uuid.UUID("00000000-0000-4000-8000-000000000002"),
        emitted_at=datetime(2026, 11, 5, 8, 0, 0, tzinfo=UTC),
        actor=ModelSessionActor(session_handle="lane-a", agent_kind="build-lane"),
        summary="a fixture consent",
        ticket_id="OMN-16182",
        operator_words="go ahead",
        approved_by="operator",
        approved_scope=("restart the dev runtime",),
        out_of_scope=("prod",),
    )


def _status() -> ModelWorkStatusRecorded:
    return ModelWorkStatusRecorded(
        event_id=uuid.UUID("00000000-0000-4000-8000-000000000003"),
        emitted_at=datetime(2026, 11, 6, 8, 0, 0, tzinfo=UTC),
        actor=ModelSessionActor(session_handle="lane-a", agent_kind="build-lane"),
        summary="a fixture status",
        ticket_id="OMN-77777",
    )


@pytest.fixture
def no_ledger_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    for name in (
        LEDGER_PATH_ENV,
        "ONEX_ERROR_RULE_ACTION_REGISTRY",
        "ONEX_ERROR_RULE_MEASUREMENTS",
        "ONEX_ERROR_RULE_AUTHORIZED_MODES",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(PROJECTION_URL_ENV, "http://projection.invalid:3002")
    return tmp_path


def _table(tmp_path: Path, sources: list[str]) -> Path:
    value = row()
    value["sources"] = sources
    target = tmp_path / "error_rules.yaml"
    target.write_text(yaml.safe_dump({"error_rules": [value]}), encoding="utf-8")
    return target


def test_ledger_bus_sources_resolve_from_the_projection_client(
    monkeypatch: pytest.MonkeyPatch, no_ledger_file: Path
) -> None:
    calls: list[str] = []

    def client() -> ModelWorkLedgerProjectionSnapshot:
        calls.append("fetch_projection_snapshot")
        return project_events(ruling_event("OMN-19998"), _consent(), _status())

    monkeypatch.setattr(validator_error_rule_table, "fetch_projection_snapshot", client)
    opened: list[str] = []
    real_open = builtins.open

    def spy_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    target = _table(no_ledger_file, [f"ledger:{STAMP}", "ticket:OMN-19998"])
    assert ValidatorErrorRuleTable().validate(target).is_valid
    assert calls == ["fetch_projection_snapshot"]
    assert not [path for path in opened if "LEDGER" in path.upper()]


def test_ledger_bus_operator_consent_ticket_is_a_source(
    monkeypatch: pytest.MonkeyPatch, no_ledger_file: Path
) -> None:
    snapshot = project_events(_consent())
    monkeypatch.setattr(
        validator_error_rule_table, "fetch_projection_snapshot", lambda: snapshot
    )
    target = _table(no_ledger_file, ["ticket:OMN-16182"])
    assert ValidatorErrorRuleTable().validate(target).is_valid


def test_ledger_bus_only_ruling_and_consent_events_are_sources(
    monkeypatch: pytest.MonkeyPatch, no_ledger_file: Path
) -> None:
    snapshot = project_events(_status())
    monkeypatch.setattr(
        validator_error_rule_table, "fetch_projection_snapshot", lambda: snapshot
    )
    target = _table(no_ledger_file, ["ticket:OMN-77777"])
    result = ValidatorErrorRuleTable().validate(target)
    assert not result.is_valid
    assert any("unresolved primary source" in issue.message for issue in result.issues)


def test_ledger_bus_fault_is_reported_and_never_read_as_empty(
    monkeypatch: pytest.MonkeyPatch, no_ledger_file: Path
) -> None:
    def client() -> ModelWorkLedgerProjectionSnapshot:
        raise WorkLedgerProjectionError(
            "unreachable", "projection unreachable: fixture"
        )

    monkeypatch.setattr(validator_error_rule_table, "fetch_projection_snapshot", client)
    target = _table(no_ledger_file, [f"ledger:{STAMP}"])
    result = ValidatorErrorRuleTable().validate(target)
    assert not result.is_valid
    assert any("projection unreachable" in issue.message for issue in result.issues)


def test_ledger_bus_unconfigured_projection_resolves_no_source(
    monkeypatch: pytest.MonkeyPatch, no_ledger_file: Path
) -> None:
    """The real client refuses an unset URL as ``unconfigured``: no source resolves, no fault."""
    monkeypatch.delenv(PROJECTION_URL_ENV, raising=False)
    target = _table(no_ledger_file, [f"ledger:{STAMP}"])
    result = ValidatorErrorRuleTable().validate(target)
    assert not result.is_valid
    assert any("unresolved primary source" in issue.message for issue in result.issues)
    assert not any("projection" in issue.message for issue in result.issues)
