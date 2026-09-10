# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the node service configuration boundary."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.configuration.model_event_bus_config import (
    ModelEventBusConfig,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.services.model_node_service_config import (
    ModelNodeServiceConfig,
)


def test_model_node_service_config_rejects_unknown_top_level_field() -> None:
    """Unknown service configuration keys fail at the typed boundary."""
    with pytest.raises(ValidationError, match="unexpected_field"):
        ModelNodeServiceConfig(
            node_name="node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            event_bus=ModelEventBusConfig(
                bootstrap_servers=["broker:9092"],
                topics=["topic"],
            ),
            unexpected_field="rejected",
        )
