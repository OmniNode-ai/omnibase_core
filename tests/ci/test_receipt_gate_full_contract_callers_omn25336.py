# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-25336: the head dod-verify passes ``--full-contract-path`` only to a verifier that accepts it.

Callers pin the reusable gate and the omnimarket verifier separately. A caller that moves its gate
pin past the commit that added the flag while its verifier tag or version predates the verifier
that accepts it would exit 2 on every head verification. The failing control is a verifier whose
usage text does not list the flag: before this change the flag was passed to it anyway.
"""

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
_ACCEPTING_HELP = (
    "usage: node_dod_verify [--ticket-id ID] [--contract-path P] "
    "[--full-contract-path P] [--execution-audience A] [--output-path P]\n"
)
_OLDER_HELP = (
    "usage: node_dod_verify [--ticket-id ID] [--contract-path P] "
    "[--execution-audience A] [--output-path P]\n"
)


def _step() -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    return next(
        s for s in data["jobs"]["dod-verify"]["steps"] if s.get("id") == "head_verify"
    )


def _run_head_verify(
    tmp_path: Path, *, verifier_help: str, help_rc: int = 0
) -> tuple[subprocess.CompletedProcess[str], list[str], Path]:
    """Run the real head_verify script against a stub verifier with the given usage text."""
    workspace = tmp_path / "workspace"
    head = workspace / ".dod-verify" / "head_home" / REPO_SHORT
    contract = head / "contracts" / f"{TICKET}.yaml"
    contract.parent.mkdir(parents=True)
    contract.write_text(f"ticket_id: {TICKET}\n")
    dod_dir = tmp_path / "runner" / "dod"
    (dod_dir / "scope").mkdir(parents=True)
    (dod_dir / "scope" / f"head-{TICKET}.yaml").write_text(f"ticket_id: {TICKET}\n")
    (dod_dir / "tickets.txt").write_text(f"{TICKET}\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    verifier_log = tmp_path / "verifier.log"
    verifier = bin_dir / "verifier"
    verifier.write_text(
        "#!/bin/bash\n"
        'case " $* " in\n'
        '  *" --help "*) printf "%s" "$VERIFIER_HELP"; exit "${VERIFIER_HELP_RC:-0}";;\n'
        "esac\n"
        'case " $* " in\n'
        '  *" --full-contract-path "*) if ! printf "%s" "$VERIFIER_HELP" | '
        'grep -q -e "--full-contract-path"; then echo "unrecognized arguments" >&2; '
        "exit 2; fi;;\n"
        "esac\n"
        'printf "%s\\n" "$*" >> "$VERIFIER_LOG"\n'
        'printf "%s\\n" \'{"status":"verified"}\'\n'
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
            "DOD_VERIFY_PY": str(verifier),
            "VERIFIER_HELP": verifier_help,
            "VERIFIER_HELP_RC": str(help_rc),
            "VERIFIER_LOG": str(verifier_log),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    lines = verifier_log.read_text().splitlines() if verifier_log.exists() else []
    return result, lines, contract


def test_full_contract_path_callers_with_an_older_verifier_get_no_flag(
    tmp_path: Path,
) -> None:
    """Failing control: a caller whose verifier predates the flag still verifies, exit 0."""
    result, invocations, _ = _run_head_verify(tmp_path, verifier_help=_OLDER_HELP)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [
        f"::notice::{TICKET}: the installed verifier does not list --full-contract-path; "
        "verifying without it",
        f"{TICKET} head: verified",
    ]
    assert len(invocations) == 1
    assert "--full-contract-path" not in invocations[0]
    assert f"--ticket-id {TICKET}" in invocations[0]


def test_full_contract_path_callers_with_an_accepting_verifier_get_the_full_contract(
    tmp_path: Path,
) -> None:
    """Positive control: a verifier that lists the flag is handed the unscoped head contract."""
    result, invocations, contract = _run_head_verify(
        tmp_path, verifier_help=_ACCEPTING_HELP
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(invocations) == 1
    assert f"--full-contract-path {contract}" in invocations[0]


def test_full_contract_path_callers_probe_the_installed_verifier_not_a_version_string() -> (
    None
):
    """The probe reads the installed verifier's own usage text, so any caller pin is covered."""
    script = _step()["run"]
    assert "node_dod_verify --help" in script
    assert "--full-contract-path" in script


def test_full_contract_path_callers_log_a_verifier_whose_help_fails(
    tmp_path: Path,
) -> None:
    """OMN-25394: a failed ``--help`` drops the flag and says so, never silently."""
    result, invocations, _ = _run_head_verify(
        tmp_path, verifier_help=_ACCEPTING_HELP, help_rc=3
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"::warning::{TICKET}: the verifier's --help exited 3" in result.stdout
    assert len(invocations) == 1
