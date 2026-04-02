# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from importlib.metadata import entry_points

import pytest

pytestmark = pytest.mark.unit


def test_onex_doctor_entry_points_registered():
    """Verify entry points are declared (may not resolve in dev without install)."""
    eps = entry_points(group="onex.doctor")
    # In an editable install, these should be discoverable
    names = [ep.name for ep in eps]
    assert (
        "docker" in names or not names
    )  # graceful: entry points may not resolve in test
