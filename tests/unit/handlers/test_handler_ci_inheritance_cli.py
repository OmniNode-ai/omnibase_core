# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ci-inheritance handler CLI (OMN-17427)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.handlers.handler_ci_inheritance_cli import (
    main,
)

pytestmark = pytest.mark.unit

_OTHER = (
    "jobs:\n  a:\n"
    "    uses: OmniNode-ai/omniclaude/.github/workflows/x-reusable.yml@abc\n"
)
_CORE = (
    "jobs:\n  a:\n"
    "    uses: OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml@abc\n"
)


def _dirs(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path / "base"
    head = tmp_path / "head"
    base.mkdir()
    head.mkdir()
    return base, head


def test_main_fails_on_added_non_host_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_CORE)
    (head / "ci.yml").write_text(_CORE)
    (head / "new.yaml").write_text(_OTHER)

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: 1 new reusable CI reference(s)" in out
    assert "OmniNode-ai/omniclaude/.github/workflows/x-reusable.yml" in out


def test_main_passes_with_existing_debt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_OTHER)
    (head / "ci.yml").write_text(_OTHER.replace("@abc", "@def"))

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK: no new reusable CI reference" in out
    assert "1 existing reference(s)" in out


def test_main_errors_when_head_dir_is_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 1
    assert "ERROR" in capsys.readouterr().out


def test_main_errors_when_base_dir_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, head = _dirs(tmp_path)
    (head / "ci.yml").write_text(_CORE)

    exit_code = main(["--base-dir", str(tmp_path / "absent"), "--head-dir", str(head)])

    assert exit_code == 1
    assert "ERROR" in capsys.readouterr().out


_CI_LINT = (
    "on:\n  pull_request:\njobs:\n  lint:\n    runs-on: ubuntu-latest\n"
    "    steps:\n      - run: ruff check\n"
)
_NEW_JOB = "  typecheck:\n    runs-on: ubuntu-latest\n    steps:\n      - run: mypy\n"


def test_main_fails_on_added_repository_specific_job(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_CI_LINT)
    (head / "ci.yml").write_text(_CI_LINT + _NEW_JOB)

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: 1 new repository-specific CI job(s)" in out
    assert "ci.yml:jobs.typecheck" in out


def test_main_passes_with_existing_repository_specific_jobs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_CI_LINT)
    (head / "ci.yml").write_text(_CI_LINT.replace("ruff check", "ruff check --fix"))

    exit_code = main(["--base-dir", str(base), "--head-dir", str(head)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "1 existing repository-specific job(s)" in out


def test_main_repository_flag_judges_a_non_host_reusable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, head = _dirs(tmp_path)
    reusable = _CI_LINT.replace("on:\n  pull_request:\n", "on:\n  workflow_call:\n")
    (head / "lint-reusable.yml").write_text(reusable)

    host_exit = main(["--base-dir", str(base), "--head-dir", str(head)])
    other_exit = main(
        [
            "--base-dir",
            str(base),
            "--head-dir",
            str(head),
            "--repository",
            "omnibase_spi",
        ]
    )

    assert host_exit == 0
    assert other_exit == 1
    assert "lint-reusable.yml:jobs.lint" in capsys.readouterr().out


_BASELINE = (
    "repository: omnibase_core\nrepository_type: python\nentries:\n"
    "  - ci.yml:jobs.lint\n"
)


def test_main_with_baseline_refuses_an_unlisted_job_the_base_carried(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """OMN-21277 AC1: with a baseline, only the baseline excuses an inline job."""
    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_CI_LINT + _NEW_JOB)
    (head / "ci.yml").write_text(_CI_LINT + _NEW_JOB)
    baseline = tmp_path / "ci_inheritance_baseline.yaml"
    baseline.write_text(_BASELINE)

    exit_code = main(
        [
            "--base-dir",
            str(base),
            "--head-dir",
            str(head),
            "--baseline",
            str(baseline),
            "--base-baseline",
            str(baseline),
        ]
    )

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "ci.yml:jobs.typecheck" in out


def test_main_with_baseline_and_no_base_dir_passes_listed_jobs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, head = _dirs(tmp_path)
    (head / "ci.yml").write_text(_CI_LINT)
    baseline = tmp_path / "ci_inheritance_baseline.yaml"
    baseline.write_text(_BASELINE)

    exit_code = main(["--head-dir", str(head), "--baseline", str(baseline)])

    assert exit_code == 0
    assert "1 baselined repository-specific job(s)" in capsys.readouterr().out


def test_main_errors_when_baseline_is_missing_or_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, head = _dirs(tmp_path)
    (head / "ci.yml").write_text(_CI_LINT)
    invalid = tmp_path / "ci_inheritance_baseline.yaml"
    invalid.write_text("repository: omnibase_core\nentries: [\n")

    missing_exit = main(
        ["--head-dir", str(head), "--baseline", str(tmp_path / "absent.yaml")]
    )
    invalid_exit = main(["--head-dir", str(head), "--baseline", str(invalid)])

    assert missing_exit == 1
    assert invalid_exit == 1
    assert capsys.readouterr().out.count("ERROR") >= 2


def test_main_errors_without_base_dir_or_baseline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, head = _dirs(tmp_path)
    (head / "ci.yml").write_text(_CI_LINT)

    assert main(["--head-dir", str(head)]) == 1
    assert "ERROR" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_main_emitting_publishes_one_event_per_triggered_validator(
    tmp_path: Path,
) -> None:
    """OMN-21277 AC3: both CI validators fail, so two events reach the bus."""
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.handlers.handler_ci_inheritance_cli import main_emitting
    from omnibase_core.models.validation.model_validator_triggered_event import (
        ModelValidatorTriggeredEvent,
    )
    from omnibase_core.topics import TopicBase

    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_CI_LINT)
    (head / "ci.yml").write_text(_CI_LINT + _NEW_JOB)
    (head / "new.yaml").write_text(_OTHER)
    bus = EventBusInmemory()
    await bus.start()

    exit_code = await main_emitting(
        ["--base-dir", str(base), "--head-dir", str(head)], bus.publish
    )

    assert exit_code == 1
    history = await bus.get_event_history(topic=TopicBase.VALIDATOR_TRIGGERED)
    events = [
        ModelValidatorTriggeredEvent.model_validate_json(message.value)
        for message in history
    ]
    assert sorted(e.validator_name for e in events) == [
        "ci_inheritance_check",
        "ci_repository_jobs_check",
    ]
    assert all(e.repository == "omnibase_core" for e in events)


@pytest.mark.asyncio
async def test_main_emitting_publishes_nothing_on_pass(tmp_path: Path) -> None:
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.handlers.handler_ci_inheritance_cli import main_emitting

    base, head = _dirs(tmp_path)
    (base / "ci.yml").write_text(_CORE)
    (head / "ci.yml").write_text(_CORE)
    bus = EventBusInmemory()
    await bus.start()

    assert (
        await main_emitting(
            ["--base-dir", str(base), "--head-dir", str(head)], bus.publish
        )
        == 0
    )
    assert await bus.get_event_history() == []
