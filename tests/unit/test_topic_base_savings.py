# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TopicBase coverage for savings estimates."""

from __future__ import annotations

import pytest

from omnibase_core.topics import TopicBase

pytestmark = pytest.mark.unit


def test_savings_estimated_topic_value() -> None:
    assert TopicBase.SAVINGS_ESTIMATED == "onex.evt.omnibase-infra.savings-estimated.v1"
