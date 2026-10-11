# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: a skip token is always rejected; no receipt-id comment rescues it.

The approvals registry and the comment form that cited it are retired. The
pre-commit hook scans a file, a commit message and the hook self-test, and each
must reject a skip token whatever comment accompanies it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _hook() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".pre-commit-hooks" / "reject-deploy-gate-skip-token.sh"
        if candidate.is_file():
            return candidate
    raise AssertionError("reject-deploy-gate-skip-token.sh not found above the tests")


def _run(*args: str) -> int:
    return subprocess.run(
        ["/bin/bash", str(_hook()), *args],
        capture_output=True,
        check=False,
        text=True,
    ).returncode


@pytest.mark.unit
@pytest.mark.parametrize(
    "body",
    [
        "[skip-receipt-gate: x]\n",
        "[skip-deploy-gate: x]\n# skip-token-allowed: R-1\n",
        "[Skip-Anything: x]\n#   SKIP-TOKEN-ALLOWED: R-2\n",
    ],
)
def test_a_skip_token_in_a_file_is_rejected_with_or_without_a_receipt_comment(
    tmp_path: Path, body: str
) -> None:
    target = tmp_path / "body.md"
    target.write_text(body, encoding="utf-8")
    assert _run(str(target)) == 1


@pytest.mark.unit
def test_a_receipt_comment_without_a_token_is_inert(tmp_path: Path) -> None:
    target = tmp_path / "body.md"
    target.write_text("# skip-token-allowed: R-3\n", encoding="utf-8")
    assert _run(str(target)) == 0


@pytest.mark.unit
def test_a_commit_message_with_a_receipt_comment_is_rejected(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text(
        "fix: x [skip-receipt-gate: y]\n\n# skip-token-allowed: R-9\n",
        encoding="utf-8",
    )
    assert _run(str(message)) == 1


@pytest.mark.unit
def test_the_hook_self_test_passes() -> None:
    assert _run("--self-test") == 0
