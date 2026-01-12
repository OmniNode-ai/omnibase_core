# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for demo integration tests."""

import pytest


@pytest.fixture
def demo_integration_fixture() -> str:
    """Fixture for demo integration tests."""
    return "demo-integration"
