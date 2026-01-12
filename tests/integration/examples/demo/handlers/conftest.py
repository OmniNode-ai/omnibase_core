# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for demo handler integration tests."""

import pytest


@pytest.fixture
def handler_integration_fixture() -> str:
    """Fixture for handler integration tests."""
    return "handler-integration"
