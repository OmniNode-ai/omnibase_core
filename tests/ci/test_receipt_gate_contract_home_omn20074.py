# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: contracts must be at the caller head; no other repo is probed."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
TICKET = "OMN-18983"
REPO_SHORT = "omniclaude"


def _step() -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    return next(
        s for s in data["jobs"]["dod-verify"]["steps"] if s.get("id") == "head_verify"
    )


def _run_head_verify(
    tmp_path: Path, *, contract_present: bool, verdict: str = '{"status":"verified"}'
) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
    workspace = tmp_path / "workspace"
    head = workspace / ".dod-verify" / "head_home" / REPO_SHORT
    head.mkdir(parents=True)
    contract = head / "contracts" / f"{TICKET}.yaml"
    if contract_present:
        contract.parent.mkdir()
        contract.write_text(f"ticket_id: {TICKET}\n")
    dod_dir = tmp_path / "runner" / "dod"
    dod_dir.mkdir(parents=True)
    (dod_dir / "tickets.txt").write_text(f"{TICKET}\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh_log = tmp_path / "gh.log"
    gh = bin_dir / "gh"
    gh.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$FAKE_GH_LOG"\nexit 99\n')
    gh.chmod(0o755)
    verifier_log = tmp_path / "verifier.log"
    verifier = bin_dir / "verifier"
    verifier.write_text(
        '#!/bin/bash\nprintf "%s\\n" "$*" >> "$VERIFIER_LOG"\n'
        'printf "%s\\n" "$VERDICT"\n'
    )
    verifier.chmod(0o755)
    script = _step()["run"]
    assert "${{" not in script
    result = subprocess.run(
        [shutil.which("bash") or "bash", "-c", script],
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "GITHUB_WORKSPACE": str(workspace),
            "RUNNER_TEMP": str(dod_dir.parent),
            "REPO_SHORT": REPO_SHORT,
            "COMPARE_WITH_OCC": "false",
            "DOD_VERIFY_PY": str(verifier),
            "VERDICT": verdict,
            "VERIFIER_LOG": str(verifier_log),
            "FAKE_GH_LOG": str(gh_log),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert not gh_log.exists(), "head verification must never query another repository"
    assert not (dod_dir / f"contract-home-{TICKET}.txt").exists()
    return result, verifier_log, contract, dod_dir


def test_compare_false_missing_contract_refuses_without_probing(tmp_path: Path) -> None:
    result, verifier_log, _, _ = _run_head_verify(tmp_path, contract_present=False)
    assert result.returncode == 1, result.stderr
    assert result.stdout.splitlines() == [
        f"::error::pull request cites {TICKET} but carries no contracts/{TICKET}.yaml",
        f"::notice::Include contracts/{TICKET}.yaml at this PR head; "
        "a later companion merge cannot supply evidence for this head.",
    ]
    assert not verifier_log.exists()


def test_present_contract_runs_the_pinned_verifier_without_probing(
    tmp_path: Path,
) -> None:
    result, verifier_log, contract, dod_dir = _run_head_verify(
        tmp_path, contract_present=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [f"{TICKET} head: verified"]
    assert verifier_log.read_text().splitlines() == [
        f"-m omnimarket.nodes.node_dod_verify --ticket-id {TICKET} "
        f"--contract-path {contract} --execution-audience hosted "
        f"--output-path {dod_dir}/head-{TICKET}.receipt.json"
    ]


@pytest.mark.parametrize("verdict", ['{"status":"failed"}', "not-json"])
def test_present_contract_still_requires_a_verified_verdict(
    tmp_path: Path, verdict: str
) -> None:
    result, verifier_log, _, _ = _run_head_verify(
        tmp_path, contract_present=True, verdict=verdict
    )
    assert result.returncode == 1
    assert verifier_log.is_file()
    assert result.stdout.splitlines() == [
        f"::error::{TICKET} head verification did not return one verified JSON verdict"
    ]


def test_head_env_has_no_retired_contract_home_or_comparison_switch() -> None:
    step = _step()
    assert "CONTRACT_HOME_REPOSITORIES" not in step["env"]
    assert "COMPARE_WITH_OCC" not in step["env"]
    assert step["env"]["REPO_SHORT"] == "${{ github.event.repository.name }}"
    assert step["env"]["DOD_VERIFY_ALLOW_STALE_PRODUCT_CLONE"] == "1"
    assert "gh " not in step["run"]
    assert "contract-home-" not in step["run"]
