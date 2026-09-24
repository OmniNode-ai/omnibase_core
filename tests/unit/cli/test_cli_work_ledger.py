# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The read CLI ``onex-work-ledger`` (OMN-19405, typed work ledger plan T5).

The acceptance tests run the installed console script in a subprocess, the way
a skill runs it, against a fixture JSON-lines ledger named by
``ONEX_WORK_LEDGER_PATH``. Edge cases that need no installed script call
``main`` in-process.

- AC1: exit codes 0/3/2 for CLEAR/HELD-or-FOUND/UNDECIDED on ``held``,
  ``pauses``, ``claims``, ``inbox`` and ``surface``; an unset
  ``ONEX_WORK_LEDGER_PATH`` exits 2 and names the variable.
- AC2: every output starts with
  ``ledger=<path> sha256=<hex> lines=<n> epoch=<uuid|none>``.
- AC3: ``--runtime-affecting`` with no value, or with ``unknown``, behaves as
  ``yes``.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.models.events.work import (
    WORK_LEDGER_SCHEMA,
    ModelHoldScope,
    ModelPrKey,
    ModelRecipients,
    ModelSessionActor,
    ModelWorkClaimRequested,
    ModelWorkEvent,
    ModelWorkHoldPlaced,
    ModelWorkLedgerEpochOpened,
    ModelWorkLedgerRecord,
    ModelWorkMessageSent,
    dump_work_ledger_line,
)
from omnibase_core.nodes.node_work_ledger_state_compute.runtime_work_ledger import (
    main,
)

pytestmark = pytest.mark.unit

ENV_VAR = "ONEX_WORK_LEDGER_PATH"
SCRIPT = Path(sys.executable).with_name("onex-work-ledger")
HEADER = re.compile(
    r"^ledger=(?P<path>\S+) sha256=(?P<sha>[0-9a-f]{64}|none) "
    r"lines=(?P<lines>\d+) epoch=(?P<epoch>[0-9a-f-]{36}|none)$"
)

T0 = datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC)
EPOCH_ID = uuid.UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
PR_HOLD_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
PAUSE_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")
LEASE_ID = uuid.UUID("00000000-0000-4000-8000-000000000003")
CLAIM_ID = uuid.UUID("00000000-0000-4000-8000-000000000004")
MESSAGE_ID = uuid.UUID("00000000-0000-4000-8000-000000000005")


def _actor(lane: str) -> ModelSessionActor:
    return ModelSessionActor(session_handle=lane, agent_kind="build-lane")


def _line(event: ModelWorkEvent) -> str:
    return dump_work_ledger_line(
        ModelWorkLedgerRecord.model_validate(
            {"schema": WORK_LEDGER_SCHEMA, "event": event}
        )
    )


def _epoch() -> ModelWorkLedgerEpochOpened:
    return ModelWorkLedgerEpochOpened(
        event_id=EPOCH_ID,
        emitted_at=T0,
        actor=_actor("ledger-tool"),
        summary="cutover epoch",
        reason="cutover",
        epoch_seq=0,
        archived_path="docs/tracking/archive/ROLLING_WORK_LEDGER_PRE_TYPED.md",
        archived_sha256="0" * 64,
        archived_line_count=10,
        review_list_ref="beta/tracking/typed-ledger-cutover-review.md",
    )


def _claim() -> ModelWorkClaimRequested:
    return ModelWorkClaimRequested(
        event_id=CLAIM_ID,
        emitted_at=T0,
        actor=_actor("lane-a"),
        summary="claim",
        ticket_id="OMN-1",
        prs=frozenset({ModelPrKey(repo="omnibase_infra", number=4005)}),
    )


def _events() -> list[ModelWorkEvent]:
    return [
        _epoch(),
        # A hold on one PR, blocking merge, addressed to nobody.
        ModelWorkHoldPlaced(
            event_id=PR_HOLD_ID,
            emitted_at=T0,
            actor=_actor("lane-a"),
            summary="hold one PR",
            scope=ModelHoldScope(
                prs=frozenset({ModelPrKey(repo="omnibase_infra", number=4005)})
            ),
            blocks=frozenset({EnumHoldBlock.MERGE}),
        ),
        # A runtime-only merge pause on a whole repo.
        ModelWorkHoldPlaced(
            event_id=PAUSE_ID,
            emitted_at=T0,
            actor=_actor("lane-a"),
            summary="runtime merge pause",
            scope=ModelHoldScope(repos=frozenset({"omnimarket"})),
            blocks=frozenset({EnumHoldBlock.MERGE, EnumHoldBlock.ARM}),
            runtime_only=True,
        ),
        # A surface lease that has not expired.
        ModelWorkHoldPlaced(
            event_id=LEASE_ID,
            emitted_at=T0,
            actor=_actor("lane-a"),
            summary="lease",
            scope=ModelHoldScope(surfaces=frozenset({"dogfood-105"})),
            blocks=frozenset({EnumHoldBlock.DISPATCH}),
            expires_at=datetime.now(UTC) + timedelta(days=365),
        ),
        _claim(),
        ModelWorkMessageSent(
            event_id=MESSAGE_ID,
            emitted_at=T0,
            actor=_actor("lane-a"),
            summary="message",
            to=ModelRecipients(lanes=frozenset({"lane-c"})),
        ),
    ]


def _write(path: Path, lines: list[str]) -> Path:
    path.write_text("".join(f"{text}\n" for text in lines), encoding="utf-8")
    return path


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    """A decidable ledger holding one of everything the queries answer about."""
    return _write(tmp_path / "ledger.jsonl", [_line(e) for e in _events()])


@pytest.fixture
def no_epoch_ledger(tmp_path: Path) -> Path:
    """A ledger with no epoch event: the cutover is not done, so UNDECIDED."""
    return _write(tmp_path / "no-epoch.jsonl", [_line(_claim())])


_Runner = Callable[[list[str], Path | None], "subprocess.CompletedProcess[str]"]


@pytest.fixture
def run(monkeypatch: pytest.MonkeyPatch) -> _Runner:
    """Run the installed script with ``ONEX_WORK_LEDGER_PATH`` set, or unset for None."""

    def _run(
        args: list[str], ledger_path: Path | None
    ) -> subprocess.CompletedProcess[str]:
        if ledger_path is None:
            monkeypatch.delenv(ENV_VAR, raising=False)
        else:
            monkeypatch.setenv(ENV_VAR, str(ledger_path))
        return subprocess.run(
            [str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=50,
        )

    return _run


def _call(
    args: list[str],
    ledger_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str]:
    """Run ``main`` in-process; for the cases that need no installed script."""
    monkeypatch.setenv(ENV_VAR, str(ledger_path))
    code = main(args)
    return code, capsys.readouterr().out


def test_console_script_is_installed() -> None:
    assert SCRIPT.is_file(), f"console script missing at {SCRIPT}"


# (command args, expected exit on the fixture ledger)
DECIDED_CASES: list[tuple[list[str], int]] = [
    (["held", "--repo", "omnibase_infra", "--pr", "4005", "--action", "merge"], 3),
    (["held", "--repo", "omnibase_infra", "--pr", "4005", "--action", "arm"], 0),
    (["held", "--repo", "omnibase_infra", "--pr", "1", "--action", "merge"], 0),
    (["pauses", "--repo", "omnimarket"], 3),
    (["pauses", "--repo", "omnibase_spi"], 0),
    (["claims", "--ticket", "OMN-1"], 3),
    (["claims", "--repo", "omnibase_infra", "--pr", "4005"], 3),
    (["claims", "--lane", "lane-a"], 3),
    (["claims", "--ticket", "OMN-2"], 0),
    (["inbox", "--lane", "lane-c"], 3),
    (["inbox", "--lane", "lane-z"], 0),
    (["surface", "--surface", "dogfood-105"], 3),
    (["surface", "--surface", "dogfood-101"], 0),
]

COMMANDS: list[list[str]] = [
    ["held", "--repo", "omnibase_infra", "--pr", "1", "--action", "merge"],
    ["pauses", "--repo", "omnibase_spi"],
    ["claims", "--ticket", "OMN-2"],
    ["inbox", "--lane", "lane-z"],
    ["surface", "--surface", "dogfood-101"],
]


@pytest.mark.parametrize(("args", "expected"), DECIDED_CASES)
def test_header_or_runtime_exit_code_and_header_on_a_decidable_ledger(
    run: _Runner, ledger: Path, args: list[str], expected: int
) -> None:
    proc = run(args, ledger)
    assert proc.returncode == expected, proc.stdout + proc.stderr
    header, verdict = proc.stdout.splitlines()[:2]
    match = HEADER.match(header)
    assert match is not None, proc.stdout
    assert match["path"] == str(ledger)
    assert match["sha"] == hashlib.sha256(ledger.read_bytes()).hexdigest()
    assert int(match["lines"]) == len(_events())
    assert match["epoch"] == str(EPOCH_ID)
    found = "held" if args[0] in {"held", "pauses", "surface"} else "found"
    assert verdict.startswith(f"verdict={'clear' if expected == 0 else found} ")


def test_held_cites_the_hold(
    ledger: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _call(
        ["held", "--repo", "OmniBase_Infra", "--pr", "4005", "--action", "merge"],
        ledger,
        monkeypatch,
        capsys,
    )
    assert code == 3, out
    assert f"hold event={PR_HOLD_ID}" in out
    assert str(PAUSE_ID) not in out


@pytest.mark.parametrize("args", COMMANDS + [["health"]])
def test_no_epoch_is_undecided_never_clear(
    run: _Runner, no_epoch_ledger: Path, args: list[str]
) -> None:
    proc = run(args, no_epoch_ledger)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "verdict=undecided" in proc.stdout
    assert "work.ledger.epoch.opened" in proc.stdout


@pytest.mark.parametrize("args", COMMANDS)
def test_unparseable_line_is_undecided(
    tmp_path: Path,
    args: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path / "bad.jsonl", [_line(e) for e in _events()] + ["{not json"])
    code, out = _call(args, path, monkeypatch, capsys)
    assert code == 2, out
    assert "verdict=undecided" in out
    assert "line 7 does not parse" in out
    reasons = [text for text in out.splitlines() if text.startswith("reason=")]
    assert len(reasons) == len(out.splitlines()) - 2, out


@pytest.mark.parametrize("args", COMMANDS)
def test_missing_file_is_undecided(
    tmp_path: Path,
    args: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out = _call(args, tmp_path / "absent.jsonl", monkeypatch, capsys)
    assert code == 2, out
    assert "verdict=undecided" in out
    assert HEADER.match(out.splitlines()[0])


def test_bad_pr_number_is_undecided(
    ledger: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _call(
        ["held", "--repo", "omnibase_infra", "--pr", "0", "--action", "merge"],
        ledger,
        monkeypatch,
        capsys,
    )
    assert code == 2, out
    assert "verdict=undecided" in out


def test_claims_refuses_half_a_pr_filter(
    ledger: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_VAR, str(ledger))
    with pytest.raises(SystemExit) as exc:
        main(["claims", "--repo", "omnibase_infra"])
    assert exc.value.code == 2


@pytest.mark.parametrize("args", COMMANDS + [["health"]])
def test_unset_variable_exits_2_naming_it(run: _Runner, args: list[str]) -> None:
    proc = run(args, None)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert ENV_VAR in proc.stdout
    assert HEADER.match(proc.stdout.splitlines()[0])


def test_unterminated_tail_is_ignored(
    ledger: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write('{"schema": "half-written')
    code, out = _call(
        ["surface", "--surface", "dogfood-101"], ledger, monkeypatch, capsys
    )
    assert code == 0, out
    assert "lines=6 " in out.splitlines()[0]


def test_health_on_a_decidable_ledger(
    ledger: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _call(["health"], ledger, monkeypatch, capsys)
    assert code == 0, out
    assert "holds_in_force=3" in out


def test_header_or_runtime_header_without_epoch(
    run: _Runner, no_epoch_ledger: Path
) -> None:
    proc = run(["claims", "--ticket", "OMN-1"], no_epoch_ledger)
    match = HEADER.match(proc.stdout.splitlines()[0])
    assert match is not None, proc.stdout
    assert match["epoch"] == "none"
    assert match["lines"] == "1"


PAUSED_PR = ["held", "--repo", "omnimarket", "--pr", "7", "--action", "merge"]


@pytest.mark.parametrize(
    ("runtime_args", "expected"),
    [
        (["--runtime-affecting"], 3),
        (["--runtime-affecting", "unknown"], 3),
        (["--runtime-affecting=unknown"], 3),
        (["--runtime-affecting", "yes"], 3),
        ([], 3),
        (["--runtime-affecting", "no"], 0),
    ],
)
def test_header_or_runtime_missing_or_unknown_is_yes(
    run: _Runner, ledger: Path, runtime_args: list[str], expected: int
) -> None:
    proc = run(PAUSED_PR + runtime_args, ledger)
    assert proc.returncode == expected, proc.stdout + proc.stderr


@pytest.mark.parametrize(
    ("runtime_args", "expected"),
    [
        (["--runtime-affecting"], 3),
        (["--runtime-affecting", "unknown"], 3),
        (["--runtime-affecting", "no"], 0),
    ],
)
def test_header_or_runtime_applies_to_pauses(
    run: _Runner, ledger: Path, runtime_args: list[str], expected: int
) -> None:
    proc = run(["pauses", "--repo", "omnimarket", *runtime_args], ledger)
    assert proc.returncode == expected, proc.stdout + proc.stderr
