# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for demo handler tests."""

import pytest


@pytest.fixture
def handler_fixture() -> str:
    """Fixture for handler tests."""
    return "handler"
