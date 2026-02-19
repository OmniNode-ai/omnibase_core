# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pytest configuration for example tests."""

import pytest


@pytest.fixture(scope="session")
def example_fixture() -> str:
    """Constant fixture for example tests.

    Uses session scope since this returns an immutable constant value.
    """
    return "example"
