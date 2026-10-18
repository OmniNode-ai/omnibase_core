# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427: the repo-evidence caller pins a verifier that refuses a partly bound contract.

Ruling 2026-10-10T11:04:11Z: the hosted `repo-evidence / dod-verify` context must
refuse a contract whose acceptance criteria are only partly bound, in every
repository. The refusal is delivered by the pinned verifier: omnimarket#3511,
first released in omnimarket 0.4.303. A caller pinning an older verifier would
still admit a partly bound contract, so the caller's `with.verifier-version`
must stay at or above that release. This is the caller-side twin of the
reusable's own VERIFIER_FLOOR check (tests/ci/test_receipt_gate_verifier_floor_omn20032.py).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CALLER_PATH = REPO_ROOT / ".github" / "workflows" / "call-repo-evidence-gate.yml"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
HOOK_ID = "call-repo-evidence-gate-verifier-floor"

# omnimarket#3511: the first release that refuses a contract leaving an
# acceptance criterion unbound.
VERIFIER_FLOOR = (0, 4, 303)

_RECEIPT_GATE_USES = re.compile(
    r"OmniNode-ai/omnibase_core/\.github/workflows/receipt-gate\.yml@[0-9a-f]{40}"
)


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _admits(version: str) -> bool:
    return _version(version) >= VERIFIER_FLOOR


def _job(path: Path = CALLER_PATH) -> dict[str, Any]:
    caller = yaml.safe_load(path.read_text(encoding="utf-8"))
    jobs = caller["jobs"]
    assert "repo-evidence" in jobs, "the caller must declare a repo-evidence job"
    job: dict[str, Any] = jobs["repo-evidence"]
    return job


def _hook() -> dict[str, Any]:
    config = yaml.safe_load(PRECOMMIT_CONFIG.read_text(encoding="utf-8"))
    hooks = [
        hook
        for repo in config["repos"]
        for hook in repo.get("hooks", [])
        if hook.get("id") == HOOK_ID
    ]
    assert len(hooks) == 1, f"exactly one pre-commit hook must be declared as {HOOK_ID}"
    hook: dict[str, Any] = hooks[0]
    return hook


def _verifier_version(job: dict[str, Any]) -> str:
    version = job["with"]["verifier-version"]
    assert isinstance(version, str), "verifier-version must be a quoted or bare string"
    return version


def test_caller_repo_evidence_job_calls_the_receipt_gate_reusable() -> None:
    uses = _job()["uses"]
    assert isinstance(uses, str)
    assert _RECEIPT_GATE_USES.fullmatch(uses), (
        "the repo-evidence job must call omnibase_core's receipt-gate reusable by full SHA"
    )


def test_caller_verifier_version_is_at_or_above_the_floor() -> None:
    version = _verifier_version(_job())
    assert _admits(version), (
        f"verifier-version {version} is below {'.'.join(map(str, VERIFIER_FLOOR))}, "
        "the first omnimarket release that refuses a partly bound contract"
    )


def test_a_caller_below_the_floor_is_caught(tmp_path: Path) -> None:
    """Negative control: the same assertion fails on a caller copy with a lower pin."""
    text = CALLER_PATH.read_text(encoding="utf-8")
    real = _verifier_version(_job())
    copy = tmp_path / "call-repo-evidence-gate.yml"
    copy.write_text(
        text.replace(f"verifier-version: {real}", "verifier-version: 0.4.302"),
        encoding="utf-8",
    )
    assert _verifier_version(_job(copy)) == "0.4.302"
    assert not _admits(_verifier_version(_job(copy)))


@pytest.mark.parametrize(
    ("version", "expected"),
    [("0.4.280", False), ("0.4.302", False), ("0.4.303", True), ("0.4.305", True)],
)
def test_floor_comparison_has_a_refusing_and_an_admitting_case(
    version: str, expected: bool
) -> None:
    assert _admits(version) is expected


def test_a_pre_commit_hook_runs_this_check_on_the_caller() -> None:
    hook = _hook()
    this_test = Path(__file__).relative_to(REPO_ROOT).as_posix()
    assert this_test in hook["entry"], f"{HOOK_ID} must run {this_test}"
    assert hook.get("pass_filenames") is False
    assert hook.get("stages") == ["pre-commit"]
    files = re.compile(hook["files"])
    assert files.search(".github/workflows/call-repo-evidence-gate.yml"), (
        f"{HOOK_ID} must fire when the caller changes"
    )
