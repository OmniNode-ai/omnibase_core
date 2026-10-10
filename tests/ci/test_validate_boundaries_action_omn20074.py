# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20074: the cross-repo boundary composite action moved into omnibase_core.

A consumer repoints by changing only its ``uses:`` line, so the input names and
defaults must equal those of the onex_change_control action, the job and context
names of the consumer stay its own, and the blocking semantics hold: with
``warn-only: "false"`` a failed check fails the step. The validators are the
core handlers; the action never checks out the onex_change_control repository
for them.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTION_PATH = REPO_ROOT / ".github" / "actions" / "validate-boundaries" / "action.yml"

# Verbatim from the onex_change_control action, so a drift in either direction fails here.
_INPUT_DEFAULTS = {
    "checks": "boundary-parity,migration-conflicts",
    "warn-only": "true",
    "repos": (
        "omniclaude,omnidash,omniintelligence,omnibase_infra,omnibase_core,"
        "omnimemory,omnimarket"
    ),
}
_FORBIDDEN_REFERENCE = "onex_change_control"
_FULL_SHA_USES = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
_PARITY_MODULE = "omnibase_core.handlers.handler_boundary_parity"
_MIGRATION_MODULE = "omnibase_core.handlers.handler_migration_conflicts"


def _load() -> dict[str, Any]:
    data = yaml.safe_load(ACTION_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _step(name: str) -> dict[str, Any]:
    steps = _load()["runs"]["steps"]
    (step,) = [s for s in steps if s.get("name") == name]
    return step


def test_action_is_composite_with_the_moved_inputs() -> None:
    data = _load()
    assert data["runs"]["using"] == "composite"
    inputs = data["inputs"]
    assert set(inputs) == set(_INPUT_DEFAULTS)
    for name, default in _INPUT_DEFAULTS.items():
        assert inputs[name]["required"] is False
        assert inputs[name]["default"] == default


def test_action_never_references_onex_change_control() -> None:
    assert _FORBIDDEN_REFERENCE not in ACTION_PATH.read_text(encoding="utf-8")


def test_every_action_use_is_pinned_by_full_sha() -> None:
    uses = [s["uses"] for s in _load()["runs"]["steps"] if "uses" in s]
    assert uses, "the action must check out the caller and set up Python and uv"
    for ref in uses:
        assert _FULL_SHA_USES.match(ref), ref


def test_checks_run_the_core_handlers_with_the_moved_flags() -> None:
    run = _step("Run boundary checks")["run"]
    assert f"python -m {_PARITY_MODULE} --repos-root /tmp/omni_repos" in run
    assert (
        f"python -m {_MIGRATION_MODULE} --repos-root /tmp/omni_repos"
        " --check-columns --warn-only"
    ) in run


def _render(script: str, values: dict[str, str]) -> str:
    def sub(match: re.Match[str]) -> str:
        return values[match.group(1).strip()]

    return re.sub(r"\$\{\{(.*?)\}\}", sub, script)


def _run_checks(
    tmp_path: Path,
    *,
    checks: str,
    warn_only: str,
    parity_exit: int,
    migration_exit: int = 0,
    migration_should_run: str = "true",
    degraded: str = "",
) -> tuple[int, str]:
    """Run the check step's script with a stub ``uv`` that exits as told."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "uv"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'echo "uv $*" >> "$STUB_LOG"\n'
        f'case "$*" in *{_PARITY_MODULE}*) exit {parity_exit};; esac\n'
        f'case "$*" in *{_MIGRATION_MODULE}*) exit {migration_exit};; esac\n'
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    script = _render(
        _step("Run boundary checks")["run"],
        {
            "inputs.checks": checks,
            "inputs.warn-only": warn_only,
            "steps.clone.outputs.degraded": degraded,
            "steps.scope.outputs.migration_conflicts_should_run": migration_should_run,
        },
    )
    log = tmp_path / "uv.log"
    log.touch()
    env = {
        "PATH": os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"]),
        "STUB_LOG": str(log),
        "OMNIBASE_CORE_ROOT": str(tmp_path),
    }
    proc = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, log.read_text(encoding="utf-8")


def test_blocking_mode_fails_on_a_parity_break(tmp_path: Path) -> None:
    code, calls = _run_checks(
        tmp_path, checks="boundary-parity", warn_only="false", parity_exit=1
    )
    assert code == 1
    assert _PARITY_MODULE in calls


def test_blocking_mode_passes_a_clean_parity_run(tmp_path: Path) -> None:
    code, _ = _run_checks(
        tmp_path, checks="boundary-parity", warn_only="false", parity_exit=0
    )
    assert code == 0


def test_warn_only_exits_zero_on_a_parity_break(tmp_path: Path) -> None:
    code, _ = _run_checks(
        tmp_path, checks="boundary-parity", warn_only="true", parity_exit=1
    )
    assert code == 0


def test_degraded_clone_fails_blocking_mode(tmp_path: Path) -> None:
    code, _ = _run_checks(
        tmp_path,
        checks="boundary-parity",
        warn_only="false",
        parity_exit=0,
        degraded="omnidash,",
    )
    assert code == 1


def test_migration_conflicts_skipped_when_no_sql_changed(tmp_path: Path) -> None:
    code, calls = _run_checks(
        tmp_path,
        checks="boundary-parity,migration-conflicts",
        warn_only="false",
        parity_exit=0,
        migration_exit=1,
        migration_should_run="false",
    )
    assert code == 0
    assert _MIGRATION_MODULE not in calls


def test_migration_conflicts_failure_counts_in_blocking_mode(tmp_path: Path) -> None:
    code, calls = _run_checks(
        tmp_path,
        checks="migration-conflicts",
        warn_only="false",
        parity_exit=0,
        migration_exit=1,
    )
    assert code == 1
    assert _MIGRATION_MODULE in calls
