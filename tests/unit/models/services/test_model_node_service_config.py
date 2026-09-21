# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strict input coverage for the node service configuration contract."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.services.model_node_service_config import (
    ModelNodeServiceConfig,
)


@pytest.mark.unit
def test_node_registry_preserves_declared_dependency_and_rejects_unknown_input() -> (
    None
):
    """The registry factory passes its declared dependency through strict input."""
    config = ModelNodeServiceConfig.for_node_registry(
        node_version=ModelSemVer(major=1, minor=0, patch=0)
    )

    assert config.depends_on == ["event-bus"]
    with pytest.raises(ValidationError):
        ModelNodeServiceConfig(
            node_name="node",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            unexpected="rejected",
        )
