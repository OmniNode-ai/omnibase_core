# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pytest configuration for demo integration tests."""

import pytest


@pytest.fixture(scope="session")
def demo_integration_fixture() -> str:
    """Constant fixture for demo integration tests.

    Uses session scope since this returns an immutable constant value.
    """
    return "demo-integration"
