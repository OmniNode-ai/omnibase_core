# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Every protocol_binding baseline entry names a file the checkout holds (OMN-21533)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.checker_protocol_binding import parse_baseline

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_BASELINE = _ROOT / ".onex_ratchets/protocol_binding_baseline.txt"


def test_every_baseline_entry_names_a_file_the_checkout_holds() -> None:
    """A handler moved into a node leaves its old baseline line naming a missing file."""
    entries = parse_baseline(_BASELINE.read_text(encoding="utf-8"))
    assert [name for name in entries if not (_ROOT / name).is_file()] == []
