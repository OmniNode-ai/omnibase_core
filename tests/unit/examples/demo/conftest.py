# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for demo example tests."""

import pytest


@pytest.fixture
def demo_fixture() -> str:
    """Fixture for demo tests."""
    return "demo"
