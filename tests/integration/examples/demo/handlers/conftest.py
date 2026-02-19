# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pytest configuration for demo handler integration tests."""

import pytest


@pytest.fixture(scope="session")
def handler_integration_fixture() -> str:
    """Constant fixture for handler integration tests.

    Uses session scope since this returns an immutable constant value.
    """
    return "handler-integration"
