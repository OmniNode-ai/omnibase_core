# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Executable pins for the writer-app pin-only exemption (OMN-20161).

The ``bot_exempt`` step of ``occ-preflight.yml`` and ``receipt-gate.yml`` is
extracted from the YAML and run under ``bash`` with a ``gh`` shim that reports
the author login and a stub ``occ_preflight_wait.py`` whose exit status and
call record the test controls. The assertion is on the ``exempt=`` line the step
writes to ``$GITHUB_OUTPUT``.

Design rules under test:

* ``DEPENDENCY_BOT_AUTHORS`` is exempt unconditionally; the probe never runs.
* ``OCC_WRITER_BOT_AUTHORS`` is exempt only when the existing probe
  (``--check-no-companion-required``) exits 0.
* Anyone else (humans, near-miss logins) never reaches the probe.
* Every probe failure, including a missing probe file, is NOT exempt.
"""

from __future__ import annotations

import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.validation.validator_receipt_gate import (
    DEPENDENCY_BOT_AUTHORS,
    OCC_WRITER_BOT_AUTHORS,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = {
    "occ-preflight": (
        REPO_ROOT / ".github" / "workflows" / "occ-preflight.yml",
        "eligibility",
        ".occ-preflight-deps/omnibase_core_wait",
    ),
    "receipt-gate": (
        REPO_ROOT / ".github" / "workflows" / "receipt-gate.yml",
        None,
        ".receipt-gate-deps/omnibase_core_wait",
    ),
}
PROBE_REL = "scripts/ci/occ_preflight_wait.py"
WRITER_LOGINS = (
    "onexbot-occ-writer[bot]",
    "app/onexbot-occ-writer",
    "onexbot-occ-writer",
)
NEAR_MISSES = (
    "onexbot-occ-writer-fork",
    "app/onexbot-occ-writerx",
    "xonexbot-occ-writer",
)
HUMANS = ("jonah", "jonahgabriel")


def _steps(name: str) -> list[dict[str, Any]]:
    path, job, _ = WORKFLOWS[name]
    jobs = yaml.safe_load(path.read_text())["jobs"]
    if job is None:
        job = next(
            k
            for k, v in jobs.items()
            if any(s.get("id") == "bot_exempt" for s in v["steps"])
        )
    steps = jobs[job]["steps"]
    assert isinstance(steps, list)
    return steps


def _bot_exempt(name: str) -> dict[str, Any]:
    return next(s for s in _steps(name) if s.get("id") == "bot_exempt")


def _run(
    tmp_path: Path,
    name: str,
    *,
    author: str,
    probe: str,  # "in-tree" | "checkout" | "absent"
    probe_exit: int,
    pr_number: str = "7",
    merge_group_head_ref: str = "",
) -> tuple[str, list[str]]:
    step = _bot_exempt(name)
    script = str(step["run"]).replace("${{ github.repository }}", "o/r")
    assert "${{" not in script, "unexpected expression left in the bot_exempt script"

    workspace = tmp_path / "ws"
    workspace.mkdir()
    probe_path: Path | None = None
    if probe == "in-tree":
        probe_path = workspace / PROBE_REL
    elif probe == "checkout":
        probe_path = workspace / WORKFLOWS[name][2] / PROBE_REL
    if probe_path is not None:
        probe_path.parent.mkdir(parents=True)
        probe_path.write_text(
            "import sys\n"
            f"with open({str(tmp_path / 'probe_calls.txt')!r}, 'a') as fh:\n"
            "    fh.write(' '.join(sys.argv[1:]) + '\\n')\n"
            f"sys.exit({probe_exit})\n"
        )

    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    gh = shim_dir / "gh"
    gh.write_text(
        "#!/bin/bash\n"
        'if [ "$1 $2" = "pr view" ]; then printf "%s\\n" "$FAKE_AUTHOR"; exit 0; fi\n'
        "exit 1\n"
    )
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)

    record = tmp_path / "probe_calls.txt"
    output = tmp_path / "github_output.txt"
    values = {
        "GH_TOKEN": "t",
        "PR_NUMBER": pr_number,
        "PR_EVENT_AUTHOR": author,
        "MERGE_GROUP_HEAD_REF": merge_group_head_ref,
        "GH_REPO": "o/r",
    }
    declared = step.get("env", {})
    assert set(declared) <= set(values), f"unmodelled step env: {set(declared)}"
    env = {
        "PATH": f"{shim_dir}:{Path(sys.executable).parent}:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(output),
        "FAKE_AUTHOR": author,
        **{k: values[k] for k in declared},
    }
    result = subprocess.run(
        ["bash", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    lines = [ln for ln in output.read_text().splitlines() if ln.startswith("exempt=")]
    assert len(lines) == 1, output.read_text()
    calls = record.read_text().splitlines() if record.exists() else []
    return lines[0], calls


@pytest.mark.parametrize("name", WORKFLOWS)
@pytest.mark.parametrize("probe", ["in-tree", "checkout"])
@pytest.mark.parametrize("login", WRITER_LOGINS)
def test_writer_with_pin_only_proof_is_exempt(
    tmp_path: Path, name: str, probe: str, login: str
) -> None:
    line, calls = _run(tmp_path, name, author=login, probe=probe, probe_exit=0)
    assert line == "exempt=true"
    assert calls == ["--check-no-companion-required --repo o/r --pr-number 7"]


@pytest.mark.parametrize("name", WORKFLOWS)
@pytest.mark.parametrize("probe_exit", [1, 2, 124])
@pytest.mark.parametrize("login", WRITER_LOGINS)
def test_writer_without_pin_only_proof_is_not_exempt(
    tmp_path: Path, name: str, probe_exit: int, login: str
) -> None:
    line, calls = _run(
        tmp_path, name, author=login, probe="in-tree", probe_exit=probe_exit
    )
    assert line == "exempt=false"
    assert len(calls) == 1


@pytest.mark.parametrize("name", WORKFLOWS)
def test_writer_with_no_probe_file_is_not_exempt(tmp_path: Path, name: str) -> None:
    line, calls = _run(
        tmp_path, name, author=WRITER_LOGINS[1], probe="absent", probe_exit=0
    )
    assert line == "exempt=false"
    assert calls == []


@pytest.mark.parametrize("name", WORKFLOWS)
def test_the_probe_receives_the_pr_number_resolved_from_a_merge_group(
    tmp_path: Path, name: str
) -> None:
    line, calls = _run(
        tmp_path,
        name,
        author=WRITER_LOGINS[0],
        probe="in-tree",
        probe_exit=0,
        pr_number="",
        merge_group_head_ref="refs/heads/gh-readonly-queue/dev/pr-42-abc123",
    )
    assert line == "exempt=true"
    assert calls == ["--check-no-companion-required --repo o/r --pr-number 42"]


@pytest.mark.parametrize("name", WORKFLOWS)
@pytest.mark.parametrize("login", [*HUMANS, *NEAR_MISSES])
def test_humans_and_near_misses_never_reach_the_probe(
    tmp_path: Path, name: str, login: str
) -> None:
    line, calls = _run(tmp_path, name, author=login, probe="in-tree", probe_exit=0)
    assert line == "exempt=false"
    assert calls == []


@pytest.mark.parametrize("name", WORKFLOWS)
@pytest.mark.parametrize("login", sorted(DEPENDENCY_BOT_AUTHORS))
def test_dependency_bots_stay_exempt_and_skip_the_probe(
    tmp_path: Path, name: str, login: str
) -> None:
    line, calls = _run(tmp_path, name, author=login, probe="in-tree", probe_exit=1)
    assert line == "exempt=true"
    assert calls == []


_ARM_RE = re.compile(r'^\s*((?:"[^"\n]+"\|)*"[^"\n]+")\)\s*$', re.MULTILINE)


@pytest.mark.parametrize("name", WORKFLOWS)
def test_case_arms_match_the_python_sets(name: str) -> None:
    arms = [
        frozenset(re.findall(r'"([^"]+)"', m.group(1)))
        for m in _ARM_RE.finditer(str(_bot_exempt(name)["run"]))
    ]
    assert arms == [DEPENDENCY_BOT_AUTHORS, OCC_WRITER_BOT_AUTHORS]


@pytest.mark.parametrize("name", WORKFLOWS)
def test_probe_token_is_not_respelled_in_the_step(name: str) -> None:
    run = str(_bot_exempt(name)["run"])
    assert "DEPENDENCY_PIN_ONLY" not in run
    assert "--check-no-companion-required" in run


@pytest.mark.parametrize("name", WORKFLOWS)
def test_the_probe_checkout_precedes_bot_exempt_and_is_not_gated_on_it(
    name: str,
) -> None:
    steps = _steps(name)
    ids = [s.get("id") for s in steps]
    exempt_idx = ids.index("bot_exempt")
    checkouts = [
        i
        for i, s in enumerate(steps)
        if s.get("name") == "Check out omnibase_core (for occ_preflight_wait.py)"
    ]
    assert len(checkouts) == 1
    assert checkouts[0] < exempt_idx
    condition = str(steps[checkouts[0]]["if"])
    assert "bot_exempt" not in condition
    assert "github.repository != 'OmniNode-ai/onex_change_control'" in condition
    assert f"! hashFiles('{PROBE_REL}')" in condition
    assert steps[checkouts[0]]["with"]["path"] == WORKFLOWS[name][2]
