# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for support assistant unit tests."""

import pytest


@pytest.fixture(scope="session")
def valid_categories() -> frozenset[str]:
    """Valid category values for SupportResponse.

    Uses session scope since these are constant values.
    """
    return frozenset({"billing", "technical", "general", "account"})


@pytest.fixture(scope="session")
def valid_sentiments() -> frozenset[str]:
    """Valid sentiment values for SupportResponse.

    Uses session scope since these are constant values.
    """
    return frozenset({"positive", "neutral", "negative"})


@pytest.fixture(scope="session")
def valid_urgencies() -> frozenset[str]:
    """Valid urgency values for SupportRequest.

    Uses session scope since these are constant values.
    """
    return frozenset({"low", "medium", "high"})
