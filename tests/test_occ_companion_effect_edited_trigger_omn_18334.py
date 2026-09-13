# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-18334: this repo's companion-effect caller listens for a description edit.

A pull-request description is a surface a lane overwrites wholesale, with no
compare-and-swap, and the change-control evidence line went with it on four of
the last five misses -- twice after the pull request had already merged. The
repair lives in the omnimarket effect; this caller is what lets the repair be
reached at all, because without the description-edited activity type the effect
never runs on the event that caused the loss.

Asserted over the PARSED trigger list rather than over a diff, so a later edit
that drops the type fails here instead of passing review unnoticed.

The precondition was answered by observation, not assumed: a description edit on
an ALREADY-MERGED pull request DOES dispatch workflow runs (probe recorded on
OMN-18334), so this trigger covers the post-merge case as well as the open one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "call-occ-companion-effect.yml"

pytestmark = pytest.mark.unit


def _pull_request_types() -> list[str]:
    """The caller's parsed ``pull_request`` activity types.

    YAML 1.1 reads a bare ``on`` as the boolean ``True``, so the trigger block
    is looked up under both spellings rather than under the one that happens to
    win on this parser version.
    """
    assert WORKFLOW.is_file(), f"caller workflow is missing at {WORKFLOW}"
    doc: dict[Any, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = doc.get("on", doc.get(True))
    assert isinstance(triggers, dict), f"unreadable trigger block: {triggers!r}"
    pull_request = triggers.get("pull_request")
    assert isinstance(pull_request, dict), (
        f"the caller has no pull_request trigger: {pull_request!r}"
    )
    types = pull_request.get("types")
    assert isinstance(types, list), (
        f"the pull_request trigger lists no types: {types!r}"
    )
    return [str(t) for t in types]


def test_the_caller_listens_for_a_description_edit() -> None:
    assert "edited" in _pull_request_types(), (
        "without the description-edited activity type the companion effect "
        "never runs on the event that drops the evidence line, so the "
        "OMN-18334 repair is unreachable in this repo"
    )


def test_the_trigger_types_it_already_had_are_kept() -> None:
    """Positive control: the repair trigger is ADDITIVE, never a replacement."""
    types = _pull_request_types()
    for required in ("opened", "synchronize"):
        assert required in types, (
            f"{required!r} was dropped; the born path fires on it and this "
            "change is additive"
        )
