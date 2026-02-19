# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pytest configuration for example integration tests."""

import pytest


@pytest.fixture(scope="session")
def integration_example_fixture() -> str:
    """Constant fixture for integration example tests.

    Uses session scope since this returns an immutable constant value.
    """
    return "integration-example"
