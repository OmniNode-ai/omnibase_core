from typing import Any, Generic

"""
Action Registry for Dynamic CLI Action Discovery.

Provides centralized registry for CLI actions discovered from node contracts,
enabling third-party nodes to register their own actions dynamically.
"""

from pathlib import Path

from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model
from omnibase_core.utils.singleton_holders import _ActionRegistryHolder

from .model_cli_action import ModelCliAction


class ModelActionRegistry:
    """Registry for dynamically discovered CLI actions."""

    def __init__(self) -> None:
        self._actions: dict[str, ModelCliAction] = {}
        self._node_actions: dict[str, set[str]] = {}
        self._qualified_actions: dict[str, ModelCliAction] = {}

    def register_action(self, action: ModelCliAction) -> None:
        """Register a CLI action from a node contract."""
        self._actions[action.action_name] = action
        if action.node_name not in self._node_actions:
            self._node_actions[action.node_name] = set()
        self._node_actions[action.node_name].add(action.action_name)

        # Also register by qualified name for uniqueness
        qualified_name = action.get_qualified_name()
        self._qualified_actions[qualified_name] = action

    def get_action(self, action_name: str) -> ModelCliAction | None:
        """Get action by name."""
        return self._actions.get(action_name)

    def get_action_by_qualified_name(
        self,
        qualified_name: str,
    ) -> ModelCliAction | None:
        """Get action by qualified name (node:action)."""
        return self._qualified_actions.get(qualified_name)

    def get_all_actions(self) -> list[ModelCliAction]:
        """Get all registered actions."""
        return list(self._actions.values())

    def get_actions_for_node(self, node_name: str) -> list[ModelCliAction]:
        """Get all actions for a specific node."""
        if node_name not in self._node_actions:
            return []
        return [self._actions[action] for action in self._node_actions[node_name]]

    def is_valid_action(self, action_name: str) -> bool:
        """Check if action is valid."""
        return action_name in self._actions

    def is_valid_qualified_action(self, qualified_name: str) -> bool:
        """Check if qualified action is valid."""
        return qualified_name in self._qualified_actions

    def discover_from_contracts(self, contracts_dir: Path) -> int:
        """
        Discover actions from all node contracts.

        Args:
            contracts_dir: Directory containing node contracts

        Returns:
            Number of actions discovered
        """
        actions_discovered = 0

        # Find all contract.yaml files
        contract_files = list(contracts_dir.rglob("contract.yaml"))

        for contract_file in contract_files:
            try:
                actions_discovered += self._discover_from_contract(contract_file)
            except Exception:
                continue

        return actions_discovered

    def _discover_from_contract(self, contract_file: Path) -> int:
        """
        Discover actions from a single contract file.

        Args:
            contract_file: Path to contract.yaml file

        Returns:
            Number of actions discovered from this contract
        """
        actions_discovered = 0

        try:
            # Load and validate YAML using Pydantic model
            contract_model = load_and_validate_yaml_model(
                contract_file, ModelGenericYaml
            )
            contract = contract_model.model_dump()

            if not contract:
                return 0

            # Extract node name from contract or directory structure
            node_name = contract.get("node_name")
            if not node_name:
                # Try to infer from directory structure
                # e.g., /path/to/node_cli/v1_0_0/contract.yaml -> node_cli
                parts = contract_file.parts
                if len(parts) >= 3:
                    node_name = parts[-3]  # node directory name
                else:
                    node_name = "unknown"

            # Look for CLI interface section
            cli_interface = contract.get("cli_interface", {})
            commands = cli_interface.get("commands", [])

            for command in commands:
                action_name = command.get("action")
                if not action_name:
                    continue

                # Create ModelCliAction from contract data
                action = ModelCliAction.from_contract_action(
                    action_name=action_name,
                    node_name=node_name,
                    description=command.get(
                        "description",
                        f"{action_name} action for {node_name}",
                    ),
                    category=command.get("category", "cli"),
                )

                # Register the action
                self.register_action(action)
                actions_discovered += 1

            # Also check for action enums in input_state
            input_state = contract.get("input_state", {})
            properties = input_state.get("properties", {})
            action_property = properties.get("action", {})
            action_enum = action_property.get("enum", [])

            for action_name in action_enum:
                if action_name not in self._actions:
                    # Create action if not already registered from CLI interface
                    action = ModelCliAction.from_contract_action(
                        action_name=action_name,
                        node_name=node_name,
                        description=f"{action_name} action for {node_name}",
                        category="contract",
                    )
                    self.register_action(action)
                    actions_discovered += 1

        except Exception as e:
            from omnibase_core.errors.error_codes import EnumCoreErrorCode
            from omnibase_core.errors.model_onex_error import ModelOnexError

            raise ModelOnexError(
                error_code=EnumCoreErrorCode.FILE_OPERATION_ERROR,
                message=f"Failed to parse contract {contract_file}: {e}",
            ) from e

        return actions_discovered

    def bootstrap_core_actions(self) -> None:
        """Bootstrap core ONEX CLI actions for current standards."""
        core_actions = [
            ("get_active_nodes", "node_cli", "List all available ONEX nodes"),
            ("system_status", "node_cli", "Get system status and health"),
            ("node_info", "node_cli", "Get information about a specific node"),
            ("execute_node", "node_cli", "Execute a node with arguments"),
            ("generate_node", "node_manager", "Generate a new ONEX node"),
            ("validate_node", "node_manager", "Validate node structure"),
            ("fix_node", "node_manager", "Fix node validation issues"),
        ]

        for action_name, node_name, description in core_actions:
            if not self.is_valid_action(action_name):
                action = ModelCliAction(
                    action_name=action_name,
                    node_name=node_name,
                    description=description,
                    category="core",
                )
                self.register_action(action)

    def clear(self) -> None:
        """Clear all registered actions."""
        self._actions.clear()
        self._node_actions.clear()
        self._qualified_actions.clear()

    def get_stats(self) -> dict[str, int]:
        """Get registry statistics."""
        return {
            "total_actions": len(self._actions),
            "total_nodes": len(self._node_actions),
            "qualified_actions": len(self._qualified_actions),
        }


def get_action_registry() -> ModelActionRegistry:
    """Get the global action registry instance (now via DI container)."""
    # Try to get from container first
    try:
        from omnibase_core.models.container.model_onex_container import (
            get_model_onex_container_sync,
        )

        container = get_model_onex_container_sync()
        registry = container.action_registry()

        # Ensure core actions are bootstrapped (idempotent)
        if len(registry.get_all_actions()) == 0:
            registry.bootstrap_core_actions()

        return registry
    except (
        Exception
    ):  # fallback-ok: DI container unavailable during bootstrap or circular dependency scenarios
        # Fallback to singleton holder for edge cases
        registry = _ActionRegistryHolder.get()
        if registry is None:
            registry = ModelActionRegistry()
            registry.bootstrap_core_actions()
            _ActionRegistryHolder.set(registry)
        return registry


def reset_action_registry() -> None:
    """Reset the global action registry (for testing)."""
    _ActionRegistryHolder.set(None)
