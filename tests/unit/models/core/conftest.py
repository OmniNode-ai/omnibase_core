# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Shared fixtures for models/core tests.

Provides reusable fixtures for:
- CLI command definition creation
- Default version instances
"""

import pytest

from omnibase_core.models.core.model_cli_command_definition import (
    ModelCliCommandDefinition,
)
from omnibase_core.models.core.model_event_type import ModelEventType
from omnibase_core.models.core.model_node_reference import ModelNodeReference
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.fixture
def default_version():
    """Provide default SemVer version for tests."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def create_test_command(default_version):
    """Factory fixture to create test command definitions.

    Returns a factory function that creates ModelCliCommandDefinition instances.

    Usage:
        def test_example(create_test_command):
            command = create_test_command("my_cmd", "node_name")
            assert command.command_name == "my_cmd"
    """

    def _create(
        command_name: str, node_name: str, category: str = "general"
    ) -> ModelCliCommandDefinition:
        return ModelCliCommandDefinition(
            version=default_version,
            command_name=command_name,
            target_node=ModelNodeReference.create_local(node_name),
            action=command_name,
            description=f"Test command {command_name}",
            event_type=ModelEventType(
                schema_version=default_version,
                event_name="NODE_START",
                namespace="onex",
                description="Test event",
            ),
            category=category,
        )

    return _create
