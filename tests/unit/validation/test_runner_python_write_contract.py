# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Durable runner Python write-contract guards (OMN-12565).

Merge-group Receipt Gate failed because the self-hosted runner user could not
write ``/usr/local/lib/python3.12/dist-packages``. All ``.201`` runner
containers were chowned in place — container state, not an image guarantee; a
restart reverts it.

The durable shape (preferred, per
``docs/plans/2026-06-01-infra-ci-durability-plan.md`` Task 1.2): remove
``uv pip install --system`` from the merge-group workflows entirely and install
into a uv-managed virtual environment inside ``$GITHUB_WORKSPACE`` (always
writable on a freshly recreated runner). The write contract no longer depends on
a mutable system path.

A preflight step asserts the write contract before the gate runs and fails fast
with a clear message if it is violated.

These tests pin that contract structurally so the ``--system`` install cannot
regress and the preflight cannot silently disappear.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_WORKFLOWS_DIR = Path(__file__).resolve().parents[3] / ".github" / "workflows"

RECEIPT_GATE_PATH = _WORKFLOWS_DIR / "receipt-gate.yml"
OCC_PREFLIGHT_PATH = _WORKFLOWS_DIR / "occ-preflight.yml"

# (workflow path, job name) pairs that run the system-Python installs that
# caused the merge-group Receipt Gate failure.
_GATED_WORKFLOWS = (
    (RECEIPT_GATE_PATH, "verify"),
    (OCC_PREFLIGHT_PATH, "eligibility"),
)


def _job_steps(workflow_path: Path, job_name: str) -> list[dict[str, object]]:
    data = yaml.safe_load(workflow_path.read_text())
    steps = data["jobs"][job_name]["steps"]
    assert isinstance(steps, list)
    return steps


def _step_by_name(workflow_path: Path, job_name: str, name: str) -> dict[str, object]:
    for step in _job_steps(workflow_path, job_name):
        if step.get("name") == name:
            return step
    raise AssertionError(f"{name!r} step not found in {workflow_path.name}")


def _all_run_scripts(workflow_path: Path, job_name: str) -> str:
    parts: list[str] = []
    for step in _job_steps(workflow_path, job_name):
        run = step.get("run")
        if isinstance(run, str):
            parts.append(run)
    return "\n".join(parts)


@pytest.mark.parametrize(
    ("workflow_path", "job_name"),
    _GATED_WORKFLOWS,
    ids=[p.name for p, _ in _GATED_WORKFLOWS],
)
def test_no_system_install_into_dist_packages(
    workflow_path: Path, job_name: str
) -> None:
    """No ``uv pip install --system`` survives — it writes the unwritable path."""
    script = _all_run_scripts(workflow_path, job_name)
    joined = re.sub(r"\\\n\s*", " ", script)
    offenders = [
        line.strip()
        for line in joined.splitlines()
        if "uv pip install" in line and "--system" in line
    ]
    assert not offenders, (
        f"{workflow_path.name} still runs `uv pip install --system`, which writes "
        f"/usr/local/lib/python3.12/dist-packages — the path a freshly recreated "
        f"self-hosted runner cannot write (OMN-12565). Install into a workspace "
        f"uv venv instead. Offenders: {offenders}"
    )


@pytest.mark.parametrize(
    ("workflow_path", "job_name"),
    _GATED_WORKFLOWS,
    ids=[p.name for p, _ in _GATED_WORKFLOWS],
)
def test_no_system_flag_on_any_uv_pip_call(workflow_path: Path, job_name: str) -> None:
    """Belt-and-suspenders: no ``--system`` flag on any uv pip call at all."""
    script = _all_run_scripts(workflow_path, job_name)
    joined = re.sub(r"\\\n\s*", " ", script)
    offenders = [
        line.strip()
        for line in joined.splitlines()
        if "uv pip" in line and "--system" in line
    ]
    assert not offenders, (
        f"{workflow_path.name} still passes `--system` to uv pip (OMN-12565). "
        f"The durable shape installs into a workspace venv, never the system "
        f"interpreter. Offenders: {offenders}"
    )


@pytest.mark.parametrize(
    ("workflow_path", "job_name"),
    _GATED_WORKFLOWS,
    ids=[p.name for p, _ in _GATED_WORKFLOWS],
)
def test_install_creates_workspace_uv_venv(workflow_path: Path, job_name: str) -> None:
    """The install must create a uv venv in the writable workspace."""
    script = _all_run_scripts(workflow_path, job_name)
    assert "uv venv" in script, (
        f"{workflow_path.name} must create a uv-managed virtual environment "
        f"(`uv venv`) inside $GITHUB_WORKSPACE so installs land on a writable "
        f"path instead of the system interpreter (OMN-12565)."
    )


@pytest.mark.parametrize(
    ("workflow_path", "job_name"),
    _GATED_WORKFLOWS,
    ids=[p.name for p, _ in _GATED_WORKFLOWS],
)
def test_install_targets_venv_python_explicitly(
    workflow_path: Path, job_name: str
) -> None:
    """uv pip installs must target the venv python via ``--python``."""
    script = _all_run_scripts(workflow_path, job_name)
    joined = re.sub(r"\\\n\s*", " ", script)
    install_lines = [
        line.strip()
        for line in joined.splitlines()
        if line.strip().startswith("uv pip install")
    ]
    assert install_lines, f"no `uv pip install` lines found in {workflow_path.name}"
    for line in install_lines:
        assert "--python" in line, (
            f"{workflow_path.name}: `uv pip install` must bind the workspace venv "
            f"explicitly via `--python` so it never falls back to the system "
            f"interpreter (OMN-12565). Offending line: {line!r}"
        )


@pytest.mark.parametrize(
    ("workflow_path", "job_name"),
    _GATED_WORKFLOWS,
    ids=[p.name for p, _ in _GATED_WORKFLOWS],
)
def test_write_contract_preflight_exists(workflow_path: Path, job_name: str) -> None:
    """A preflight step must assert the write contract before the gate runs."""
    names = [s.get("name", "") for s in _job_steps(workflow_path, job_name)]
    assert any(
        isinstance(n, str) and "Preflight" in n and "write contract" in n.lower()
        for n in names
    ), (
        f"{workflow_path.name} must include a runner preflight step that asserts "
        f"the Python write contract before the gate executes (OMN-12565). Steps "
        f"found: {names}"
    )


@pytest.mark.parametrize(
    ("workflow_path", "job_name", "gate_step"),
    [
        (RECEIPT_GATE_PATH, "verify", "Run Receipt-Gate"),
        (OCC_PREFLIGHT_PATH, "eligibility", "Run OCC eligibility check"),
    ],
    ids=["receipt-gate.yml", "occ-preflight.yml"],
)
def test_preflight_runs_before_the_gate(
    workflow_path: Path, job_name: str, gate_step: str
) -> None:
    """Preflight must run before both the install and the gate step."""
    names = [s.get("name", "") for s in _job_steps(workflow_path, job_name)]
    preflight_idx = next(
        (
            i
            for i, n in enumerate(names)
            if isinstance(n, str) and "Preflight" in n and "write contract" in n.lower()
        ),
        -1,
    )
    assert preflight_idx >= 0, (
        f"{workflow_path.name}: write-contract preflight step not found. Steps: {names}"
    )
    install_idx = names.index("Install omnibase_core")
    gate_idx = names.index(gate_step)
    assert preflight_idx < install_idx, (
        f"{workflow_path.name}: write-contract preflight must precede the install "
        f"step (fail fast before any write is attempted)."
    )
    assert preflight_idx < gate_idx, (
        f"{workflow_path.name}: write-contract preflight must precede the gate."
    )


@pytest.mark.parametrize(
    ("workflow_path", "job_name"),
    _GATED_WORKFLOWS,
    ids=[p.name for p, _ in _GATED_WORKFLOWS],
)
def test_preflight_fails_loud_on_unwritable_system_path(
    workflow_path: Path, job_name: str
) -> None:
    """The preflight must fail loudly (exit 1 + ::error::) when the contract breaks."""
    step = _step_by_name(
        workflow_path,
        job_name,
        _preflight_step_name(workflow_path, job_name),
    )
    script = step["run"]
    assert isinstance(script, str)
    assert "exit 1" in script, (
        f"{workflow_path.name}: preflight must `exit 1` when the write contract "
        f"is violated (OMN-12565)."
    )
    assert "::error::" in script, (
        f"{workflow_path.name}: preflight must emit a `::error::` annotation so the "
        f"failure is legible in the job log (OMN-12565)."
    )


@pytest.mark.parametrize(
    ("workflow_path", "job_name"),
    _GATED_WORKFLOWS,
    ids=[p.name for p, _ in _GATED_WORKFLOWS],
)
def test_preflight_asserts_workspace_writability(
    workflow_path: Path, job_name: str
) -> None:
    """Preflight must prove the venv path is writable, not just narrate it."""
    step = _step_by_name(
        workflow_path,
        job_name,
        _preflight_step_name(workflow_path, job_name),
    )
    script = step["run"]
    assert isinstance(script, str)
    # The preflight proves writability by attempting an actual write under the
    # workspace venv parent and asserting no --system/dist-packages path is used.
    assert "GITHUB_WORKSPACE" in script, (
        f"{workflow_path.name}: preflight must check writability of the "
        f"$GITHUB_WORKSPACE-rooted venv path (OMN-12565)."
    )
    assert "dist-packages" in script, (
        f"{workflow_path.name}: preflight must reference the dist-packages system "
        f"path it is guaranteeing is NOT required (OMN-12565)."
    )


def _preflight_step_name(workflow_path: Path, job_name: str) -> str:
    for step in _job_steps(workflow_path, job_name):
        name = step.get("name", "")
        if (
            isinstance(name, str)
            and "Preflight" in name
            and "write contract" in name.lower()
        ):
            return name
    raise AssertionError(
        f"write-contract preflight step not found in {workflow_path.name}"
    )
