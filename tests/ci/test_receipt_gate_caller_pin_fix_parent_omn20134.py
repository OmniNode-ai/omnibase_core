# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20134: core's repo-evidence caller names a receipt-gate that has the fix-parent fallback.

The caller runs as ``pull_request_target``, so the receipt gate it names is the one
that judges every pull request. A pin older than the Binds-Merged-Fix fallback
(OMN-21556, omnibase_core#2158) refuses a bound fix that is already on dev.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CALLER_PATH = REPO_ROOT / ".github" / "workflows" / "call-repo-evidence-gate.yml"

# The first dev-merge tag cut at omnibase_core#2158's squash commit (OMN-21556).
FIX_PARENT_FALLBACK_TAG = "dev-20261030012703-2f56afeb6dbf"
FIX_PARENT_MARKER = "control_uses_fix_parent"

_PIN = re.compile(
    r"receipt-gate\.yml@(?P<tag>dev-(?P<stamp>\d{14})-(?P<sha>[0-9a-f]{12}))\b"
)


def _pinned_tag() -> re.Match[str]:
    match = _PIN.search(CALLER_PATH.read_text(encoding="utf-8"))
    assert match is not None, "caller must name receipt-gate.yml by a dev-merge tag"
    return match


def test_caller_pin_is_not_older_than_the_fix_parent_fallback() -> None:
    floor = _PIN.search(f"receipt-gate.yml@{FIX_PARENT_FALLBACK_TAG}")
    assert floor is not None
    assert _pinned_tag().group("stamp") >= floor.group("stamp"), (
        f"the caller pins {_pinned_tag().group('tag')}, which predates "
        f"{FIX_PARENT_FALLBACK_TAG}, the first tag with the OMN-21556 fix-parent fallback"
    )


def test_pinned_tag_carries_the_fix_parent_fallback() -> None:
    tag = _pinned_tag().group("tag")
    shown = subprocess.run(
        ["git", "show", f"{tag}:.github/workflows/receipt-gate.yml"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=scrub_git_location_env(),
    )
    if shown.returncode != 0:
        pytest.skip(f"tag {tag} is not in this checkout (shallow or tagless clone)")
    assert FIX_PARENT_MARKER in shown.stdout, (
        f"receipt-gate.yml at {tag} has no {FIX_PARENT_MARKER}"
    )
