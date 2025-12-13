"""
Shared fixtures for models/core tests.

Provides reusable fixtures for:
- CLI command definition creation
- Default version instances
- Model forward reference resolution
"""

from collections.abc import Callable

import pytest

from omnibase_core.models.configuration.model_resource_limits import ModelResourceLimits
from omnibase_core.models.core.model_cli_command_definition import (
    ModelCliCommandDefinition,
)
from omnibase_core.models.core.model_environment import ModelEnvironment
from omnibase_core.models.core.model_event_type import ModelEventType
from omnibase_core.models.core.model_node_reference import ModelNodeReference
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.security.model_security_level import ModelSecurityLevel


@pytest.fixture(scope="module", autouse=True)
def rebuild_model_environment() -> None:
    """Resolve forward references in ModelEnvironment for tests.

    ModelEnvironment uses TYPE_CHECKING imports which create forward references.
    This fixture rebuilds the model to resolve those references before tests run.

    The _types_namespace parameter provides the types that were imported under
    TYPE_CHECKING in the model module.

    Raises:
        RuntimeError: If model_rebuild fails, indicating forward references
            cannot be resolved (usually a missing type in _types_namespace).
    """
    try:
        ModelEnvironment.model_rebuild(
            _types_namespace={
                "ModelResourceLimits": ModelResourceLimits,
                "ModelSecurityLevel": ModelSecurityLevel,
            }
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to rebuild ModelEnvironment forward references: {e}. "
            "Check that all TYPE_CHECKING imports are included in _types_namespace."
        ) from e


@pytest.fixture
def default_version() -> ModelSemVer:
    """Provide default SemVer version for tests."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def create_test_command(
    default_version: ModelSemVer,
) -> Callable[[str, str, str], ModelCliCommandDefinition]:
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
