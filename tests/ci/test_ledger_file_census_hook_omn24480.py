# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The ledger file census ratchet is wired as a pre-commit hook (OMN-24480).

The census counts the files in this repository that read or write the ledger
file. Its ratchet row is shrink-only: a count above the recorded number fails
the hook, and the only legitimate direction for the row is down. The hook runs
the shared omnimarket census node against a packaged overlay, registered for
``omnibase_core``, with the row carried in
``config/ledger_file_census_ratchet.yaml``. This module pins the wiring:

* the hook is present in ``.pre-commit-config.yaml`` and its entry names the
  registration, the ratchet file and a pinned omnimarket commit;
* the ratchet file parses and its ``omnibase_core`` row is a non-negative int;
* the check refuses a config from which the hook has been removed (the
  failing control).
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
RATCHET_FILE = REPO_ROOT / "config" / "ledger_file_census_ratchet.yaml"

CENSUS_HOOK_ID = "ledger-file-census-ratchet"
REGISTER_FLAG = "--register omnibase_core"
RATCHET_FLAG = "--ratchet-file config/ledger_file_census_ratchet.yaml"
# The omnimarket dependency must be pinned to one exact 40-hex commit.
OMNIMARKET_PIN_RE = re.compile(
    r"omnimarket @ git\+https://github\.com/OmniNode-ai/omnimarket@([0-9a-f]{40})\b"
)


def _check_census_hook_wired(config: dict[str, Any]) -> None:
    """Assert the parsed pre-commit config wires the census ratchet hook.

    Takes the parsed ``.pre-commit-config.yaml`` so the failing control can
    hand it a modified copy.
    """
    hooks: list[dict[str, Any]] = [
        hook
        for repo in config.get("repos", [])
        for hook in repo.get("hooks", [])
        if hook.get("id") == CENSUS_HOOK_ID
    ]
    assert len(hooks) == 1, (
        f"expected exactly one {CENSUS_HOOK_ID!r} hook in .pre-commit-config.yaml, "
        f"found {len(hooks)}: the census ratchet must stay wired"
    )
    entry = str(hooks[0].get("entry", ""))
    assert REGISTER_FLAG in entry, (
        f"the census hook entry must register omnibase_core ({REGISTER_FLAG!r} "
        f"missing):\n{entry}"
    )
    assert RATCHET_FLAG in entry, (
        f"the census hook entry must name the ratchet file ({RATCHET_FLAG!r} "
        f"missing):\n{entry}"
    )
    pin = OMNIMARKET_PIN_RE.search(entry)
    assert pin is not None, (
        "the census hook entry must pin omnimarket to one exact 40-hex commit:\n"
        f"{entry}"
    )
    assert len(pin.group(1)) == 40


def test_the_census_ratchet_hook_is_wired() -> None:
    config: dict[str, Any] = yaml.safe_load(
        PRECOMMIT_CONFIG.read_text(encoding="utf-8")
    )
    _check_census_hook_wired(config)


def test_the_ratchet_row_is_a_non_negative_int() -> None:
    ratchet: dict[str, Any] = yaml.safe_load(RATCHET_FILE.read_text(encoding="utf-8"))
    row = ratchet["ratchet"]["omnibase_core"]
    assert isinstance(row, int) and not isinstance(row, bool), (
        f"the omnibase_core ratchet row must be an int, got {type(row).__name__}"
    )
    assert row >= 0, f"the omnibase_core ratchet row must be >= 0, got {row}"


def test_a_config_without_the_hook_fails_the_check() -> None:
    """The failing control: the same check must refuse a hook-less config."""
    config: dict[str, Any] = yaml.safe_load(
        PRECOMMIT_CONFIG.read_text(encoding="utf-8")
    )
    stripped = copy.deepcopy(config)
    for repo in stripped.get("repos", []):
        repo["hooks"] = [
            hook for hook in repo.get("hooks", []) if hook.get("id") != CENSUS_HOOK_ID
        ]
    with pytest.raises(AssertionError, match="found 0"):
        _check_census_hook_wired(stripped)
