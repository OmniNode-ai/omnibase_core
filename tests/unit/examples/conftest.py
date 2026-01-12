# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for example tests."""

import pytest


@pytest.fixture
def example_fixture() -> str:
    """Fixture for example tests."""
    return "example"
