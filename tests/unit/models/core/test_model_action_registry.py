# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for DI-backed action registry helpers."""

from unittest.mock import patch
from uuid import UUID

import pytest

from omnibase_core.models.cli.model_cli_action import ModelCliAction
from omnibase_core.models.core.model_action_registry import (
    ModelActionRegistry,
    discover_actions_from_contracts,
    get_action_registry,
    get_registered_action,
    get_registered_action_by_qualified_name,
)


@pytest.mark.serial
@pytest.mark.unit
class TestActionRegistryGlobalHelpers:
    """Test module-level action registry helpers resolve through DI."""

    @pytest.fixture(autouse=True)
    def reset_container_context(self):
        """Reset container context so each test gets an isolated DI registry."""
        from omnibase_core.context.context_application import _current_container

        context_token = _current_container.set(None)

        yield

        _current_container.reset(context_token)

    def test_get_action_registry_creates_di_registry(self) -> None:
        """The canonical getter creates and bootstraps the DI action registry."""
        from omnibase_core.context.context_application import get_current_container

        assert get_current_container() is None

        registry = get_action_registry()

        assert isinstance(registry, ModelActionRegistry)
        assert registry.is_valid_action("execute_node")
        assert get_current_container() is not None

    def test_registered_action_helpers_use_di_registry(self) -> None:
        """Action lookup helpers read from the DI-resolved registry instance."""
        registry = get_action_registry()
        action = ModelCliAction.from_contract_action(
            action_name="sync_contract",
            node_id=UUID("4cc66c36-cdf5-4e9f-81c8-5eb8bfce1956"),
            node_name="node_contract",
            description="Synchronize a contract",
            category="execution",
        )
        registry.register_action(action)

        assert get_registered_action("sync_contract") is action
        assert (
            get_registered_action_by_qualified_name("node_contract:sync_contract")
            is action
        )

    def test_discover_actions_from_contracts_uses_di_registry(self, tmp_path) -> None:
        """Contract discovery helper delegates to the DI-resolved registry."""
        with patch.object(
            ModelActionRegistry,
            "discover_from_contracts",
            return_value=1,
        ) as mock_discover:
            count = discover_actions_from_contracts(tmp_path)

        assert count == 1
        mock_discover.assert_called_once_with(tmp_path)
