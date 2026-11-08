# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Each external check declares advisory or blocking, as overlay data (OMN-23029).

Operator ruling 2026-11-08: a ``neutral`` conclusion from a check declared advisory does
not fail CI Summary and its findings still show; a blocking check's ``neutral`` still
fails; an undeclared check is still denied by default. The declaration is data, the
contract ``ci_summary_external_check_modes.contract.json`` plus the overlay
``ci_summary_external_check_modes.json``, so adding an advisory reviewer is one overlay
line and no code change.

Each control below fails without the change it names: the shipped overlay is what turns
the ``Tessl Reviewer`` neutral green, and an unreadable overlay is what turns it red.

Ticket: OMN-23029
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.ci import ci_summary_gate as gate
from scripts.ci.ci_summary_gate import EXIT_FAILURE, EXIT_SUCCESS

from .test_ci_summary_gate import _ALL_EXTERNAL_GREEN, _all_good, _check_run

pytestmark = pytest.mark.unit

TESSL = "Tessl Reviewer"
NOW = datetime(2026, 11, 8, 5, tzinfo=UTC)
CONTRACT = {
    "contract": "ci_summary_external_check_modes",
    "version": 1,
    "modes": {"advisory": ["neutral"], "blocking": []},
    "entry_fields": ["mode", "reason"],
}


def _row(name: str, conclusion: str | None) -> dict:
    return _check_run(
        name,
        conclusion,
        started_at="2026-11-08T04:13:29Z",
        completed_at="2026-11-08T04:14:29Z",
    )


def _verdict(*rows: dict) -> tuple[int, str]:
    return gate.evaluate(
        _all_good(),
        external_check_runs=[*_ALL_EXTERNAL_GREEN, *rows],
        now=NOW,
    )


def _declare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    overlay: object,
    contract: object = CONTRACT,
) -> None:
    contract_file, overlay_file = tmp_path / "c.json", tmp_path / "o.json"
    contract_file.write_text(json.dumps(contract), encoding="utf-8")
    overlay_file.write_text(json.dumps(overlay), encoding="utf-8")
    monkeypatch.setattr(gate, "CHECK_MODES_FILES", [contract_file, overlay_file])


def _entry(mode: str) -> dict[str, str]:
    return {"mode": mode, "reason": "declared for this test"}


def test_shipped_overlay_declares_the_reviewer_advisory_and_the_sweep_passes_it() -> (
    None
):
    admitted, refusals = gate.load_check_modes(*gate.CHECK_MODES_FILES)
    assert refusals == []
    assert admitted[TESSL] == frozenset({"neutral"})
    assert TESSL not in gate.EXTERNAL_SWEEP_EXCLUSIONS
    assert TESSL not in gate.EXPECTED_EXTERNAL_CONTEXTS
    code, report = _verdict(_row(TESSL, "neutral"), _row("Some Other Gate", "success"))
    assert code == EXIT_SUCCESS, report
    assert f"{TESSL} (neutral, declared advisory)" in report


def test_declared_advisory_neutral_passes_and_still_shows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(tmp_path, monkeypatch, {"New Reviewer": _entry("advisory")})
    code, report = _verdict(_row("New Reviewer", "neutral"))
    assert code == EXIT_SUCCESS, report
    assert "New Reviewer (neutral, declared advisory)" in report


def test_control_undeclared_neutral_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(tmp_path, monkeypatch, {"New Reviewer": _entry("advisory")})
    code, report = _verdict(_row("Unlisted Reviewer", "neutral"))
    assert code == EXIT_FAILURE, report
    assert "Unlisted Reviewer (neutral)" in report


def test_control_blocking_neutral_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(tmp_path, monkeypatch, {"Strict Check": _entry("blocking")})
    code, report = _verdict(_row("Strict Check", "neutral"))
    assert code == EXIT_FAILURE, report
    assert "Strict Check (neutral)" in report


@pytest.mark.parametrize("conclusion", ["failure", "timed_out", "action_required"])
def test_control_advisory_failure_is_still_reported_as_a_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conclusion: str
) -> None:
    _declare(tmp_path, monkeypatch, {"New Reviewer": _entry("advisory")})
    code, report = _verdict(_row("New Reviewer", conclusion))
    assert code == EXIT_FAILURE, report
    assert f"New Reviewer ({conclusion})" in report


@pytest.mark.parametrize(
    ("overlay", "needle"),
    [
        (
            {"X": {"mode": "advisory"}},
            "X: needs non-empty text mode, reason and a declared mode",
        ),
        (
            {"X": {"mode": "advisory", "reason": "  "}},
            "X: needs non-empty text mode, reason and a declared mode",
        ),
        (
            {"X": {"mode": "advisory", "reason": 7}},
            "X: needs non-empty text mode, reason and a declared mode",
        ),
        (
            {"X": {"mode": "optional", "reason": "r"}},
            "X: needs non-empty text mode, reason and a declared mode",
        ),
        (
            {"X": {"mode": ["advisory"], "reason": "r"}},
            "X: needs non-empty text mode, reason and a declared mode",
        ),
        ({"X": "advisory"}, "X: needs non-empty text mode, reason and a declared mode"),
    ],
)
def test_control_a_malformed_overlay_entry_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, overlay: object, needle: str
) -> None:
    _declare(tmp_path, monkeypatch, overlay)
    code, report = _verdict(_row("Some Other Gate", "success"))
    assert code == EXIT_FAILURE, report
    assert "check-mode registry " in report
    assert needle in report


def test_control_a_missing_overlay_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(tmp_path, monkeypatch, {})
    monkeypatch.setattr(
        gate, "CHECK_MODES_FILES", [tmp_path / "c.json", tmp_path / "absent.json"]
    )
    code, report = _verdict(_row("Some Other Gate", "success"))
    assert code == EXIT_FAILURE, report
    assert "check-mode registry " in report


def test_control_a_missing_contract_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(tmp_path, monkeypatch, {})
    monkeypatch.setattr(
        gate, "CHECK_MODES_FILES", [tmp_path / "absent.json", tmp_path / "o.json"]
    )
    code, report = _verdict(_row("Some Other Gate", "success"))
    assert code == EXIT_FAILURE, report
    assert "check-mode registry " in report


@pytest.mark.parametrize(
    "contract",
    [
        {"entry_fields": ["mode"]},
        {"modes": ["advisory"], "entry_fields": ["mode"]},
        {"modes": {"advisory": 5}, "entry_fields": ["mode"]},
        {"modes": {"advisory": ["neutral"]}},
        [],
    ],
)
def test_control_a_malformed_contract_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contract: object
) -> None:
    _declare(tmp_path, monkeypatch, {}, contract=contract)
    code, report = _verdict(_row("Some Other Gate", "success"))
    assert code == EXIT_FAILURE, report
    assert "check-mode registry " in report


@pytest.mark.parametrize("raw", ["{not json", "[]", "null"])
def test_control_an_unparsable_overlay_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    _declare(tmp_path, monkeypatch, {})
    (tmp_path / "o.json").write_text(raw, encoding="utf-8")
    code, report = _verdict(_row("Some Other Gate", "success"))
    assert code == EXIT_FAILURE, report
    assert "check-mode registry " in report


def test_control_the_reviewer_neutral_fails_when_the_overlay_does_not_declare_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(tmp_path, monkeypatch, {})
    code, report = _verdict(_row(TESSL, "neutral"))
    assert code == EXIT_FAILURE, report
    assert f"{TESSL} (neutral)" in report
