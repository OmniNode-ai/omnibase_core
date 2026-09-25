# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-19153: core no longer declares omniclaude's retired DoD-verify spelling.

The member had no importer anywhere on the fleet; omniclaude carried its own
declaration, now retired too. The surviving event is omnimarket
node_dod_verify's terminal. The retired literal is assembled from parts so
this test never matches itself.
"""

from __future__ import annotations

import pytest

from omnibase_core.topics import TopicBase

RETIRED = "onex.evt.omniclaude." + "dod-verify-completed.v1"


@pytest.mark.unit
def test_topic_base_declares_no_member_for_the_retired_spelling() -> None:
    assert RETIRED not in {member.value for member in TopicBase}
    assert "DOD_VERIFY_COMPLETED" not in TopicBase.__members__


@pytest.mark.unit
def test_the_sibling_dod_topics_are_still_declared() -> None:
    """Positive control: the membership scan reads the real enum."""
    assert TopicBase.DOD_GUARD_FIRED.value == "onex.evt.omniclaude.dod-guard-fired.v1"
