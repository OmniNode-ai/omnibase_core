# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Collection target for the OMN-14420 guard test; it only needs tests/conftest.py to load."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_probe_is_collectable() -> None:
    assert True
