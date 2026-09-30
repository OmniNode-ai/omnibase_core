# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20130: Contract Compliance runs only the dod_evidence items of this PR.

A ticket contract is shared by every repo's PRs for that ticket. The pinned
change-control runner (onex_change_control 91f5b691) executes every item of it
in THIS product checkout, so an item generated for another repo's PR runs here.
The recurring case is the change-control admissibility validator minted for an
omnibase_infra PR (``uv run pytest tests/test_evidence_admissibility.py -q``,
a file that exists only in onex_change_control): it exits 5 in this tree and
BLOCKs every omnibase_core PR that cites the same ticket (omnibase_core#1809,
run 36665093126, "[SUMMARY] OMN-17427: 62/84 PASS, 21 WARN, 1 BLOCK"). OMN-19384
cleared six earlier copies by hand-appended supersessions.

The driver now scopes the run: an item whose generated id binds it to another
PR (``dod-<org>-<repo>-pr-<n>``, ``dod-occ-...-pr-<n>``, ``occ-self-bind-pr-<n>``)
is reported WARN and not executed; items bound to this PR, and items bound to
no PR, run exactly as before.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
DRIVER = REPO_ROOT / "scripts/ci/defer_test_passes_driver.py"

# The pinned runner's item loop and supersession rule, copied from
# onex_change_control 91f5b691 contract_compliance_check.py (_run_dod_checks,
# _superseded_dod_ids, _supersedes_marker and the summary/exit rule of
# run_compliance_check). _check_command keeps the one property these tests
# need: it executes check_value with ``sh -c`` in the product workspace.
_FAKE_CHECKER = r"""
import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

_RESULT_PASS = "PASS"
_RESULT_WARN = "WARN"
_RESULT_BLOCK = "BLOCK"


@dataclass(frozen=True)
class _CheckContext:
    pr_number: int
    repo: str
    ticket_id: str = ""
    contracts_dir: Path | None = None
    is_legacy: bool = False


def _check_command(check_value, workspace, pr_number=0, repo="", ticket_id="", contracts_dir=None):
    proc = subprocess.run(
        ["sh", "-c", str(check_value)], cwd=workspace, capture_output=True, text=True, check=False
    )
    if proc.returncode == 0:
        return _RESULT_PASS, f"Command succeeded: {check_value}"
    return _RESULT_BLOCK, f"Command failed (exit {proc.returncode}): {check_value}"


def _check_test_passes(check_value, workspace, pr_number, repo):
    return _RESULT_BLOCK, "not reached in these tests"


_CHECK_RUNNERS = {"command": _check_command, "test_passes": _check_test_passes}


def _run_single_check(check, workspace, context):
    check_type = check.get("check_type", "")
    runner = _CHECK_RUNNERS[check_type]
    result, detail = runner(
        check.get("check_value", ""), workspace, context.pr_number, context.repo
    )
    return check_type, result, detail


def _run_dod_checks(dod_evidence, workspace, context):
    results = []
    superseded = _superseded_dod_ids(dod_evidence)
    for dod_item in dod_evidence:
        item_id = dod_item.get("id", "?")
        item_desc = dod_item.get("description", "")
        if item_id in superseded:
            print(f"\n[DoD {item_id}] {item_desc[:80]}", flush=True)
            detail = "SUPERSEDED -- pinned runner"
            results.append((item_id, "superseded", _RESULT_WARN, detail))
            print(f"  [~] superseded: {detail}", flush=True)
            continue
        print(f"\n[DoD {item_id}] {item_desc[:80]}", flush=True)
        for check in dod_item.get("checks", []):
            check_type, result, detail = _run_single_check(check, workspace, context)
            results.append((item_id, check_type, result, detail))
            icon = {"PASS": "+", "WARN": "~", "BLOCK": "X"}.get(result, "?")
            print(f"  [{icon}] {check_type}: {detail}", flush=True)
    return results


def _superseded_dod_ids(dod_evidence):
    seen = set()
    superseded = set()
    for dod_item in dod_evidence:
        if not isinstance(dod_item, dict):
            continue
        item_id = dod_item.get("id")
        supersedes = _supersedes_marker(dod_item.get("evidence_artifact"))
        if supersedes in seen:
            superseded.add(supersedes)
        if isinstance(item_id, str):
            seen.add(item_id)
    return superseded


def _supersedes_marker(value):
    if not isinstance(value, str):
        return None
    prefix = "supersedes_dod_evidence:"
    if not value.startswith(prefix):
        return None
    superseded = value[len(prefix):].strip()
    return superseded or None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--contracts-dir", required=True)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    contract = json.loads((Path(args.contracts_dir) / "OMN-1.json").read_text())
    results = _run_dod_checks(
        contract["dod_evidence"], Path(args.workspace), _CheckContext(args.pr, args.repo, "OMN-1")
    )
    passes = sum(1 for _, _, r, _ in results if r == _RESULT_PASS)
    warns = sum(1 for _, _, r, _ in results if r == _RESULT_WARN)
    blocks = sum(1 for _, _, r, _ in results if r == _RESULT_BLOCK)
    print(f"\n[SUMMARY] OMN-1: {passes}/{len(results)} PASS, {warns} WARN, {blocks} BLOCK", flush=True)
    return 1 if blocks else 0
"""

REPO = "OmniNode-ai/omnibase_core"
PR = 1809

# The shape of the OMN-17427 contract that blocked omnibase_core#1809: a
# sibling repo's PR items, a change-control-only admissibility validator minted
# for that sibling PR, a companion self-bind, this PR's own items, and one
# hand-authored item bound to no PR.
_FOREIGN_ADMISSIBILITY = {
    "id": "dod-occ-evidence-admissibility-validator-pr-4325",
    "description": "Hosted OCC evidence admissibility validator (OMN-15247).",
    "source": "generated",
    "checks": [
        {"check_type": "command", "check_value": "echo foreign-ran >> ran.log; exit 5"}
    ],
}
_FOREIGN_SIBLING = {
    "id": "dod-OmniNode-ai-omnibase_infra-pr-4325",
    "description": "PR #4325 on OmniNode-ai/omnibase_infra",
    "source": "generated",
    "checks": [
        {"check_type": "command", "check_value": "echo sibling-ran >> ran.log; exit 1"}
    ],
}
_SAME_NUMBER_OTHER_REPO = {
    "id": f"dod-OmniNode-ai-omnimarket-pr-{PR}-ci",
    "description": "same PR number, another repo",
    "source": "generated",
    "checks": [
        {"check_type": "command", "check_value": "echo market-ran >> ran.log; exit 1"}
    ],
}
_SELF_BIND = {
    "id": "occ-self-bind-pr-11864",
    "description": "OCC companion PR #11864 self-bind",
    "source": "generated",
    "checks": [
        {"check_type": "command", "check_value": "echo bind-ran >> ran.log; exit 1"}
    ],
}
_OWN = {
    "id": f"dod-OmniNode-ai-omnibase_core-pr-{PR}",
    "description": "this PR",
    "source": "manual",
    "checks": [{"check_type": "command", "check_value": "echo own-ran >> ran.log"}],
}
_OWN_CI = {
    "id": f"dod-OmniNode-ai-omnibase_core-pr-{PR}-ci",
    "description": "this PR, diff scope",
    "source": "generated",
    "checks": [{"check_type": "command", "check_value": "echo own-ci-ran >> ran.log"}],
}
_UNBOUND = {
    "id": "dod-ac1-lockfile-pins-pyjwt",
    "description": "bound to no PR",
    "source": "manual",
    "checks": [{"check_type": "command", "check_value": "echo unbound-ran >> ran.log"}],
}


def _tool_path() -> str:
    tool_dirs = sorted(
        {
            str(Path(found).parent)
            for found in (shutil.which("bash"), shutil.which("env"), shutil.which("sh"))
            if found is not None
        }
    )
    return os.pathsep.join([*tool_dirs, "/usr/bin", "/bin"])


def _run_driver(
    tmp_path: Path, dod_evidence: list[dict[str, object]], *, pr: int = PR
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    src = tmp_path / "checker/src"
    module_dir = src / "onex_change_control/scripts"
    module_dir.mkdir(parents=True)
    (src / "onex_change_control/__init__.py").write_text("", encoding="utf-8")
    (module_dir / "__init__.py").write_text("", encoding="utf-8")
    (module_dir / "contract_compliance_check.py").write_text(
        _FAKE_CHECKER, encoding="utf-8"
    )
    contracts = tmp_path / "contracts"
    contracts.mkdir()
    (contracts / "OMN-1.json").write_text(
        json.dumps({"dod_evidence": dod_evidence}), encoding="utf-8"
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(DRIVER),
            "--deferred-record",
            str(tmp_path / "record.json"),
            "--",
            "--pr",
            str(pr),
            "--repo",
            REPO,
            "--contracts-dir",
            str(contracts),
            "--workspace",
            str(workspace),
        ],
        env={"PATH": _tool_path(), "PYTHONPATH": str(src)},
        capture_output=True,
        text=True,
        check=False,
    )
    log = workspace / "ran.log"
    ran = log.read_text(encoding="utf-8").split() if log.exists() else []
    return result, ran


def test_items_bound_to_other_prs_are_not_executed_in_this_tree(
    tmp_path: Path,
) -> None:
    """The omnibase_core#1809 shape passes and runs only its own and unbound items."""
    result, ran = _run_driver(
        tmp_path,
        [
            _FOREIGN_SIBLING,
            _FOREIGN_ADMISSIBILITY,
            _SELF_BIND,
            _SAME_NUMBER_OTHER_REPO,
            _OWN_CI,
            _OWN,
            _UNBOUND,
        ],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert ran == ["own-ci-ran", "own-ran", "unbound-ran"]
    assert "[SUMMARY] OMN-1: 3/7 PASS, 4 WARN, 0 BLOCK" in result.stdout
    assert (
        "[~] pr_scope: NOT RUN HERE -- bound to OmniNode-ai/omnibase_infra#4325"
        in result.stdout
    )
    assert "[~] pr_scope: NOT RUN HERE -- bound to PR #4325" in result.stdout
    assert "[~] pr_scope: NOT RUN HERE -- bound to PR #11864" in result.stdout
    assert (
        f"[~] pr_scope: NOT RUN HERE -- bound to OmniNode-ai/omnimarket#{PR}"
        in result.stdout
    )


def test_a_failing_item_of_this_pr_still_blocks(tmp_path: Path) -> None:
    own_red = {
        **_OWN,
        "checks": [
            {"check_type": "command", "check_value": "echo own-ran >> ran.log; exit 3"}
        ],
    }
    result, ran = _run_driver(tmp_path, [_FOREIGN_ADMISSIBILITY, own_red])
    assert result.returncode == 1, result.stdout + result.stderr
    assert ran == ["own-ran"]
    assert "[SUMMARY] OMN-1: 0/2 PASS, 1 WARN, 1 BLOCK" in result.stdout


def test_a_failing_unbound_item_still_blocks(tmp_path: Path) -> None:
    unbound_red = {
        **_UNBOUND,
        "checks": [{"check_type": "command", "check_value": "exit 2"}],
    }
    result, _ = _run_driver(tmp_path, [_SELF_BIND, unbound_red])
    assert result.returncode == 1, result.stdout + result.stderr


def test_an_admissibility_item_minted_for_this_pr_still_runs(tmp_path: Path) -> None:
    """dod-occ-...-pr-<this pr> names no repo, so it is not provably foreign."""
    own_admissibility = {
        **_FOREIGN_ADMISSIBILITY,
        "id": f"dod-occ-evidence-admissibility-validator-pr-{PR}",
    }
    result, ran = _run_driver(tmp_path, [own_admissibility])
    assert result.returncode == 1, result.stdout + result.stderr
    assert ran == ["foreign-ran"]


def test_supersession_by_an_out_of_scope_item_is_still_honoured(
    tmp_path: Path,
) -> None:
    """Scoping must not un-supersede an item: the full list decides supersession."""
    superseded_own = {
        **_OWN,
        "checks": [
            {
                "check_type": "command",
                "check_value": "echo stale-ran >> ran.log; exit 1",
            }
        ],
    }
    supersessor = {
        "id": "occ-admissibility-pr-4325-rb19384",
        "description": "supersedes the own item",
        "source": "manual",
        "status": "skipped",
        "evidence_artifact": f"supersedes_dod_evidence:{_OWN['id']}",
        "checks": [],
    }
    result, ran = _run_driver(tmp_path, [superseded_own, supersessor, _UNBOUND])
    assert result.returncode == 0, result.stdout + result.stderr
    assert ran == ["unbound-ran"]
    assert "[~] superseded: SUPERSEDED" in result.stdout


def test_driver_fails_closed_when_the_pinned_item_loop_is_absent(
    tmp_path: Path,
) -> None:
    src = tmp_path / "checker/src"
    module_dir = src / "onex_change_control/scripts"
    module_dir.mkdir(parents=True)
    (src / "onex_change_control/__init__.py").write_text("", encoding="utf-8")
    (module_dir / "__init__.py").write_text("", encoding="utf-8")
    (module_dir / "contract_compliance_check.py").write_text(
        _FAKE_CHECKER.replace("def _run_dod_checks(", "def _renamed_loop("),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(DRIVER),
            "--deferred-record",
            str(tmp_path / "record.json"),
            "--",
            "--pr",
            str(PR),
            "--repo",
            REPO,
        ],
        env={"PATH": _tool_path(), "PYTHONPATH": str(src)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "_run_dod_checks" in result.stderr
    assert not (tmp_path / "record.json").exists()
