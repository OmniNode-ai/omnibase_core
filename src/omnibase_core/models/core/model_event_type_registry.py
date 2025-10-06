from typing import Any, Generic

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Event Type Registry for Dynamic Event Type Discovery.

Provides centralized registry for event types discovered from node contracts,
enabling third-party plugins to register their own event types dynamically.
"""

from pathlib import Path

from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model

from .model_event_type import ModelEventType


class ModelEventTypeRegistry:
    """Registry for dynamically discovered event types."""

    def __init__(self):
        self._event_types: dict[str, ModelEventType] = {}
        self._namespace_events: dict[str, set[str]] = {}
        self._qualified_events: dict[str, ModelEventType] = {}

    def register_event_type(self, event_type: ModelEventType) -> None:
        """Register an event type from a node contract."""
        self._event_types[event_type.event_name] = event_type
        if event_type.namespace not in self._namespace_events:
            self._namespace_events[event_type.namespace] = set()
        self._namespace_events[event_type.namespace].add(event_type.event_name)

        # Also register by qualified name for uniqueness
        qualified_name = event_type.qualified_name
        self._qualified_events[qualified_name] = event_type

    def get_event_type(self, event_name: str) -> ModelEventType | None:
        """Get event type by name."""
        return self._event_types.get(event_name)

    def get_event_type_by_qualified_name(
        self,
        qualified_name: str,
    ) -> ModelEventType | None:
        """Get event type by qualified name (namespace:event)."""
        return self._qualified_events.get(qualified_name)

    def get_all_event_types(self) -> list[ModelEventType]:
        """Get all registered event types."""
        return list(self._event_types.values())

    def get_events_for_namespace(self, namespace: str) -> list[ModelEventType]:
        """Get all event types for a specific namespace."""
        if namespace not in self._namespace_events:
            return []
        return [self._event_types[event] for event in self._namespace_events[namespace]]

    def is_valid_event_type(self, event_name: str) -> bool:
        """Check if event type is valid."""
        return event_name in self._event_types

    def is_valid_qualified_event_type(self, qualified_name: str) -> bool:
        """Check if qualified event type is valid."""
        return qualified_name in self._qualified_events

    def discover_from_contracts(self, contracts_dir: Path) -> int:
        """
        Discover event types from all node contracts.

        Args:
            contracts_dir: Directory containing node contracts

        Returns:
            Number of event types discovered
        """
        events_discovered = 0

        # Find all contract.yaml files
        contract_files = list(contracts_dir.rglob("contract.yaml"))

        for contract_file in contract_files:
            try:
                events_discovered += self._discover_from_contract(contract_file)
            except Exception:
                continue

        return events_discovered

    def _discover_from_contract(self, contract_file: Path) -> int:
        """
        Discover event types from a single contract file.

        Args:
            contract_file: Path to contract.yaml file

        Returns:
            Number of event types discovered from this contract
        """
        events_discovered = 0

        try:
            # Load and validate YAML using Pydantic model
            contract = load_and_validate_yaml_model(
                contract_file, ModelGenericYaml
            ).model_dump()

            if not contract:
                return 0

            # Extract node name for namespace
            node_name = contract.get("node_name")
            if not node_name:
                # Try to infer from directory structure
                parts = contract_file.parts
                if len(parts) >= 3:
                    node_name = parts[-3]  # node directory name
                else:
                    node_name = "unknown"

            # Look for event types in various sections

            # 1. Check for explicit event_types section
            event_types_section = contract.get("event_types", {})
            for event_name, event_config in event_types_section.items():
                event_type = ModelEventType.from_contract_data(
                    event_name=event_name,
                    namespace=event_config.get("namespace", node_name),
                    description=event_config.get(
                        "description",
                        f"{event_name} event from {node_name}",
                    ),
                    category=event_config.get("category", "contract"),
                    severity=event_config.get("severity", "info"),
                )
                self.register_event_type(event_type)
                events_discovered += 1

            # 2. Check CLI interface for event types
            cli_interface = contract.get("cli_interface", {})
            commands = cli_interface.get("commands", [])
            for command in commands:
                event_type_name = command.get("event_type")
                if event_type_name and not self.is_valid_event_type(event_type_name):
                    event_type = ModelEventType.from_contract_data(
                        event_name=event_type_name,
                        namespace=node_name,
                        description=f"Event type for {command.get('command_name', 'command')}",
                        category="cli",
                    )
                    self.register_event_type(event_type)
                    events_discovered += 1

        except Exception as e:
            msg = f"Failed to parse contract {contract_file}: {e}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INTERNAL_ERROR,
                message=msg,
            )

        return events_discovered

    def bootstrap_core_event_types(self) -> None:
        """Bootstrap core ONEX event types for current standards."""
        core_event_types = [
            ("NODE_START", "Node startup event", "lifecycle"),
            ("NODE_SUCCESS", "Node success event", "lifecycle"),
            ("NODE_FAILURE", "Node failure event", "lifecycle"),
            ("NODE_REGISTER", "Node registration event", "lifecycle"),
            ("TELEMETRY_OPERATION_START", "Telemetry operation start", "telemetry"),
            ("TELEMETRY_OPERATION_SUCCESS", "Telemetry operation success", "telemetry"),
            ("TELEMETRY_OPERATION_ERROR", "Telemetry operation error", "telemetry"),
            ("STRUCTURED_LOG", "Structured log event", "logging"),
            ("HEALTH_CHECK", "Health check event", "monitoring"),
            ("PERFORMANCE_METRIC", "Performance metric event", "monitoring"),
        ]

        for event_name, description, category in core_event_types:
            if not self.is_valid_event_type(event_name):
                event_type = ModelEventType(
                    event_name=event_name,
                    namespace="onex",
                    description=description,
                    category=category,
                )
                self.register_event_type(event_type)

    def clear(self) -> None:
        """Clear all registered event types."""
        self._event_types.clear()
        self._namespace_events.clear()
        self._qualified_events.clear()

    def get_stats(self) -> dict[str, int]:
        """Get registry statistics."""
        return {
            "total_event_types": len(self._event_types),
            "total_namespaces": len(self._namespace_events),
            "qualified_events": len(self._qualified_events),
        }


# Global registry instance
_global_event_type_registry: ModelEventTypeRegistry | None = None


def get_event_type_registry() -> ModelEventTypeRegistry:
    """Get the global event type registry instance."""
    global _global_event_type_registry
    if _global_event_type_registry is None:
        _global_event_type_registry = ModelEventTypeRegistry()
        # Bootstrap core event types
        _global_event_type_registry.bootstrap_core_event_types()
    return _global_event_type_registry


def reset_event_type_registry() -> None:
    """Reset the global event type registry (for testing)."""
    global _global_event_type_registry
    _global_event_type_registry = None
