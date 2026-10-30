# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20413: the repo-evidence caller pins a receipt-gate carrying the fix-parent control.

omnibase_core#2158 (OMN-21556) taught the Binds-Merged-Fix control to run at the
fix's own parent when the fix's product changes no longer reverse-apply at the
merge base. The caller runs under pull_request_target and names the reusable by
a dev-merge tag, so the fallback reaches pull requests only once the pin names a
tag at or after that merge. A pin from before it refuses every binding to an
older merged fix with "do not revert cleanly at the merge base, so the control
cannot run" (omnibase_core#2157 on dev-20261018024445-b6ee996befa1).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

CALLER_PATH = (
    Path(__file__).resolve().parents[2]
    / ".github/workflows/call-repo-evidence-gate.yml"
)
# The dev-merge tag of omnibase_core#2158's squash commit 2f56afeb6dbf.
PARENT_CONTROL_TAG_STAMP = "20261030012703"
OLD_USES = (
    "OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml"
    "@dev-20261018024445-b6ee996befa1"
)


def _assert_pin_carries_parent_control(uses: str) -> None:
    match = re.fullmatch(
        r"OmniNode-ai/omnibase_core/\.github/workflows/receipt-gate\.yml"
        r"@dev-([0-9]{14})-[0-9a-f]{12}",
        uses,
    )
    assert match, f"receipt-gate must be pinned by a dev-merge tag: {uses}"
    assert match.group(1) >= PARENT_CONTROL_TAG_STAMP, (
        f"{uses} predates omnibase_core#2158; its Binds-Merged-Fix control cannot "
        "fall back to the fix's parent"
    )


def test_caller_pin_carries_the_fix_parent_control() -> None:
    caller = yaml.safe_load(CALLER_PATH.read_text(encoding="utf-8"))
    _assert_pin_carries_parent_control(caller["jobs"]["repo-evidence"]["uses"])


def test_pin_from_before_the_parent_control_is_refused() -> None:
    with pytest.raises(AssertionError):
        _assert_pin_carries_parent_control(OLD_USES)
