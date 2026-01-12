# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for demo example tests."""

import pytest


@pytest.fixture(scope="session")
def demo_fixture() -> str:
    """Constant fixture for demo tests.

    Uses session scope since this returns an immutable constant value.
    """
    return "demo"
