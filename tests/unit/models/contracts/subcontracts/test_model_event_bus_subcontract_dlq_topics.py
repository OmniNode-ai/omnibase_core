# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``event_bus.dlq_topics`` is a declared subcontract field (OMN-16451).

The auto-wiring layer reads ``event_bus.dlq_topics`` to route unroutable
inbound messages; before this field existed, any contract declaring it
failed to parse as ``ModelEventBusSubcontract`` (``extra="forbid"``).
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.subcontracts.model_event_bus_subcontract import (
    ModelEventBusSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestEventBusSubcontractDlqTopics:
    def test_defaults_to_empty(self) -> None:
        sub = ModelEventBusSubcontract(version=_VERSION)
        assert sub.dlq_topics == []

    def test_accepts_declared_dlq_topics(self) -> None:
        sub = ModelEventBusSubcontract(
            version=_VERSION,
            subscribe_topics=["onex.evt.platform.node-introspection.v1"],
            dlq_topics=["onex.dlq.omnibase-infra.platform.v1"],
        )
        assert sub.dlq_topics == ["onex.dlq.omnibase-infra.platform.v1"]

    def test_rejects_non_string_entries(self) -> None:
        with pytest.raises(ValidationError):
            ModelEventBusSubcontract(version=_VERSION, dlq_topics=[42])  # type: ignore[list-item]
