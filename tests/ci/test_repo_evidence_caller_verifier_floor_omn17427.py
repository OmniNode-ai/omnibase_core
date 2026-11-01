# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427, OMN-21859: the repo-evidence caller installs a verifier that refuses a partly bound contract.

Ruling 2026-10-10T11:04:11Z: the hosted `repo-evidence / dod-verify` context must
refuse a contract whose acceptance criteria are only partly bound, in every
repository. The refusal is delivered by the verifier the reusable installs
(omnimarket#3511 and later). Ruling 2026-10-31T21:49:54Z (OMN-21676): that
verifier is installed from an omnimarket dev-merge tag, which the reusable
resolves to a commit and refuses unless it descends from its floor commit, so
the floor is an ancestry fact the reusable enforces, not a version number the
caller carries. The caller therefore passes `with.verifier-tag` and no
`verifier-version`. This is the caller-side twin of the reusable's own floor
check (tests/ci/test_receipt_gate_verifier_tag_omn21676.py).
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

_DEV_MERGE_TAG = r"dev-[0-9]{14}-[0-9a-f]{12}"
_RECEIPT_GATE_USES = re.compile(
    rf"OmniNode-ai/omnibase_core/\.github/workflows/receipt-gate\.yml@{_DEV_MERGE_TAG}"
)
_VERIFIER_TAG = re.compile(_DEV_MERGE_TAG)


def _admits(tag: object) -> bool:
    return isinstance(tag, str) and _VERIFIER_TAG.fullmatch(tag) is not None


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


def _verifier_tag(job: dict[str, Any]) -> str:
    tag = job["with"]["verifier-tag"]
    assert isinstance(tag, str), "verifier-tag must be a string"
    return tag


def test_caller_repo_evidence_job_calls_the_receipt_gate_reusable() -> None:
    uses = _job()["uses"]
    assert isinstance(uses, str)
    assert _RECEIPT_GATE_USES.fullmatch(uses), (
        "the repo-evidence job must call omnibase_core's receipt-gate reusable by dev-merge tag"
    )


def test_caller_verifier_tag_is_an_omnimarket_dev_merge_tag() -> None:
    tag = _verifier_tag(_job())
    assert _admits(tag), (
        f"verifier-tag {tag} is not an omnimarket dev-merge tag "
        "(dev-<14 digits>-<12 lowercase hex digits>)"
    )


def test_caller_does_not_pass_verifier_version() -> None:
    assert "verifier-version" not in _job()["with"], (
        "verifier-version is the reusable's warned fallback; the caller passes verifier-tag"
    )


def test_a_caller_with_a_version_instead_of_a_tag_is_caught(tmp_path: Path) -> None:
    """Negative control: the same assertions fail on a caller copy that names a release."""
    text = CALLER_PATH.read_text(encoding="utf-8")
    real = _verifier_tag(_job())
    copy = tmp_path / "call-repo-evidence-gate.yml"
    copy.write_text(
        text.replace(f"verifier-tag: {real}", "verifier-version: 0.4.305"),
        encoding="utf-8",
    )
    job = _job(copy)
    assert "verifier-tag" not in job["with"]
    assert "verifier-version" in job["with"]


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("0.4.305", False),
        ("dev-20261101000200", False),
        ("dev-20261101000200-949993EDF3B7", False),
        ("dev-2026110100020-949993edf3b7", False),
        ("dev-20261101000200-949993edf3b", False),
        ("dev-20261101000200-949993edf3b7", True),
    ],
)
def test_tag_shape_has_a_refusing_and_an_admitting_case(
    tag: str, expected: bool
) -> None:
    assert _admits(tag) is expected


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
