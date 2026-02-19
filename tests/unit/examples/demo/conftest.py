# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pytest configuration for demo example tests."""

import pytest


@pytest.fixture(scope="session")
def demo_fixture() -> str:
    """Constant fixture for demo tests.

    Uses session scope since this returns an immutable constant value.
    """
    return "demo"
