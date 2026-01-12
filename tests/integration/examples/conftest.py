# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for example integration tests."""

import pytest


@pytest.fixture
def integration_example_fixture() -> str:
    """Fixture for integration example tests."""
    return "integration-example"
