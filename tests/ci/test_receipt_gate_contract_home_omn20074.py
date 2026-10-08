# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: missing caller contracts name their home for the OCC difference."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from textwrap import dedent
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
TICKET = "OMN-18983"
OWNER = "OmniNode-ai"
REPO_SHORT = "omniclaude"


def _step(step_id: str) -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    steps = cast(list[dict[str, Any]], data["jobs"]["dod-verify"]["steps"])
    return next(step for step in steps if step.get("id") == step_id)


def _contract_api_path(repo: str) -> str:
    return f"repos/{OWNER}/{repo}/contents/contracts/{TICKET}.yaml"


def _run_head_verify(
    tmp_path: Path, *, compare: str, found: str
) -> tuple[subprocess.CompletedProcess[str], Path, list[str]]:
    workspace = tmp_path / "workspace"
    (workspace / ".dod-verify" / "head_home" / REPO_SHORT).mkdir(parents=True)
    dod_dir = tmp_path / "runner" / "dod"
    dod_dir.mkdir(parents=True)
    (dod_dir / "tickets.txt").write_text(f"{TICKET}\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh.log"
    gh = bin_dir / "gh"
    gh.write_text(
        dedent("""\
            #!/bin/bash
            printf '%s\\n' "$*" >> "$FAKE_GH_LOG"
            for path in $FAKE_GH_FOUND; do
              if [ "$2" = "$path" ]; then
                exit 0
              fi
            done
            exit 1
            """)
    )
    gh.chmod(0o755)
    step = _step("head_verify")
    script = cast(str, step["run"])
    assert "${{" not in script
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "GITHUB_WORKSPACE": str(workspace),
        "RUNNER_TEMP": str(dod_dir.parent),
        "REPO_SHORT": REPO_SHORT,
        "REPO_OWNER": OWNER,
        "COMPARE_WITH_OCC": compare,
        "CONTRACT_HOME_REPOSITORIES": step["env"]["CONTRACT_HOME_REPOSITORIES"],
        "DOD_VERIFY_PY": "/bin/false",
        "FAKE_GH_FOUND": found,
        "FAKE_GH_LOG": str(log),
    }
    result = subprocess.run(
        [shutil.which("bash") or "bash", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    assert (
        f"::error::pull request cites {TICKET} but carries no contracts/{TICKET}.yaml"
        in result.stdout.splitlines()
    )
    assert result.stdout.splitlines()[-1] == (
        f"::notice::Include contracts/{TICKET}.yaml at this PR head; "
        "a later companion merge cannot supply evidence for this head."
    )
    calls = log.read_text().splitlines() if log.exists() else []
    return result, dod_dir / f"contract-home-{TICKET}.txt", calls


def test_occ_only_contract_writes_home_after_probing_product_repositories(
    tmp_path: Path,
) -> None:
    result, marker, calls = _run_head_verify(
        tmp_path, compare="true", found=_contract_api_path("onex_change_control")
    )
    assert marker.read_text() == f"{OWNER}/onex_change_control\n"
    assert calls == [
        f"api {_contract_api_path(repo)} --silent"
        for repo in (
            "omnibase_core",
            "omnibase_infra",
            "omnimarket",
            "omnidash",
            "onex_change_control",
        )
    ]
    assert (
        f"::notice::contracts/{TICKET}.yaml is on the default branch of "
        f"{OWNER}/onex_change_control; the OCC difference reports contract_in_another_repo"
        in result.stdout.splitlines()
    )


def test_product_contract_takes_precedence_over_occ(tmp_path: Path) -> None:
    _, marker, calls = _run_head_verify(
        tmp_path,
        compare="true",
        found=" ".join(
            _contract_api_path(repo) for repo in ("omnimarket", "onex_change_control")
        ),
    )
    assert marker.read_text() == f"{OWNER}/omnimarket\n"
    assert calls == [
        f"api {_contract_api_path(repo)} --silent"
        for repo in ("omnibase_core", "omnibase_infra", "omnimarket")
    ]


def test_missing_everywhere_leaves_no_marker(tmp_path: Path) -> None:
    _, marker, calls = _run_head_verify(tmp_path, compare="true", found="")
    assert not marker.exists()
    assert calls == [
        f"api {_contract_api_path(repo)} --silent"
        for repo in (
            "omnibase_core",
            "omnibase_infra",
            "omnimarket",
            "omnidash",
            "onex_change_control",
        )
    ]


def test_compare_false_never_probes_or_writes_marker(tmp_path: Path) -> None:
    _, marker, calls = _run_head_verify(
        tmp_path, compare="false", found=_contract_api_path("onex_change_control")
    )
    assert not marker.exists()
    assert calls == []


def test_head_env_and_difference_share_the_marker_directory() -> None:
    step = _step("head_verify")
    assert step["env"]["COMPARE_WITH_OCC"] == "${{ inputs.compare-with-occ }}"
    assert step["env"]["REPO_OWNER"] == "${{ github.repository_owner }}"
    assert step["env"]["CONTRACT_HOME_REPOSITORIES"] == (
        "omnibase_core omnibase_infra omniclaude omnimarket omnidash onex_change_control"
    )
    assert '--dod-dir "$RUNNER_TEMP/dod"' in _step("occ_difference")["run"]
