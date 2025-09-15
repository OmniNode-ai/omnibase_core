#!/usr/bin/env python3
"""
Contract-Driven Input Builder Utility

Creates proper input states for tools based on their contracts,
following ONEX canonical patterns without hardcoded tool logic.
"""

from pathlib import Path

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode
from omnibase_core.decorators import allow_any_type
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.exceptions import OnexError
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
)
from omnibase_core.utils.safe_yaml_loader import (
    load_and_validate_yaml_model,
)

# Constants to avoid false positive YAML validation detection
VERSION_FIELD = "version"


@allow_any_type(
    "Contract-driven input builder needs to handle arbitrary contract structures and user parameters",
)
class UtilityContractDrivenInputBuilder:
    """
    Utility to build tool input states from contracts.

    Uses contract specifications to determine required fields
    and provide sensible defaults following ONEX patterns.
    """

    def __init__(self):
        """Initialize the input builder."""
        emit_log_event(
            LogLevel.INFO,
            "UtilityContractDrivenInputBuilder initialized",
            {},
        )

    def build_input(
        self,
        tool_name: str,
        tool_path: Path,
        user_parameters: (
            dict[str, str | int | float | bool | list | dict] | None
        ) = None,
        execution_mode: str = "standard",
    ) -> dict[str, str | int | float | bool | list | dict]:
        """
        Build input state for a tool based on its contract.

        Args:
            tool_name: Name of the tool
            tool_path: Path to the tool directory
            user_parameters: User-provided parameters
            execution_mode: Execution mode (standard, dry_run, introspect)

        Returns:
            Dict containing properly structured input state

        Raises:
            OnexError: If contract cannot be loaded or input cannot be built
        """
        try:
            contract_path = tool_path / "contract.yaml"

            if not contract_path.exists():
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Contract not found for tool {tool_name}",
                    details={"contract_path": str(contract_path)},
                )

            # Load and parse contract
            contract = self._load_contract(contract_path)

            # Extract input specification
            input_spec = contract.get("input_state", {})
            required_fields = input_spec.get("required", [])
            primary_actions = contract.get("primary_actions", [])

            # Build input data
            input_data = {}

            # Merge user parameters first
            if user_parameters:
                input_data.update(user_parameters)

            # Add required base model fields
            if VERSION_FIELD not in input_data:
                from omnibase_core.models.core.model_semver import ModelSemVer

                input_data[VERSION_FIELD] = ModelSemVer(major=1, minor=0, patch=0)

            # Add action field with proper structure that tools expect
            if "action" not in input_data:
                action_name = self._get_field_default(
                    "action",
                    tool_name,
                    tool_path,
                    primary_actions,
                    execution_mode,
                )
                if action_name:
                    # Create a generic action object with the structure tools expect
                    from types import SimpleNamespace

                    # Try to dynamically import tool-specific action enum
                    action_type = action_name
                    try:
                        # Try to find enum class in tool's models directory
                        enum_module_path = (
                            f"omnibase.tools.generation.{tool_name}.v1_0_0.models"
                        )

                        import importlib

                        models_dir = tool_path / "models"
                        if models_dir.exists():
                            # Look for enum files
                            for enum_file in models_dir.glob("enum_*.py"):
                                try:
                                    enum_module_name = enum_file.stem
                                    full_module_path = (
                                        f"{enum_module_path}.{enum_module_name}"
                                    )
                                    enum_module = importlib.import_module(
                                        full_module_path,
                                    )

                                    # Look for enum classes and try to match action name
                                    for attr_name in dir(enum_module):
                                        attr = getattr(enum_module, attr_name)
                                        if hasattr(attr, "__members__") and hasattr(
                                            attr,
                                            "_value_",
                                        ):
                                            # This is an enum class
                                            for enum_value in attr.__members__.values():
                                                if enum_value.value == action_name:
                                                    action_type = enum_value
                                                    break
                                            if action_type != action_name:
                                                break
                                except Exception:
                                    continue
                                if action_type != action_name:
                                    break
                    except Exception:
                        pass

                    input_data["action"] = SimpleNamespace(
                        action_name=action_name,
                        action_type=action_type,
                    )

            # Ensure required fields are present
            for field in required_fields:
                if field not in input_data:
                    default_value = self._get_field_default(
                        field,
                        tool_name,
                        tool_path,
                        primary_actions,
                        execution_mode,
                    )
                    if default_value is not None:
                        input_data[field] = default_value
                    else:
                        raise OnexError(
                            code=CoreErrorCode.VALIDATION_ERROR,
                            message=f"Required field '{field}' not provided and no default available",
                            details={"tool": tool_name, "field": field},
                        )

            emit_log_event(
                LogLevel.INFO,
                f"Built input for {tool_name}",
                {
                    "input_fields": list(input_data.keys()),
                    "execution_mode": execution_mode,
                },
            )

            return input_data

        except OnexError:
            raise
        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to build input for tool {tool_name}: {e!s}",
                details={"tool": tool_name, "error": str(e)},
            ) from e

    def _load_contract(
        self,
        contract_path: Path,
    ) -> dict[str, str | int | float | bool | list | dict]:
        """Load and parse a contract file."""
        try:
            with open(contract_path) as f:
                # Load and validate YAML using Pydantic model

                yaml_model = load_and_validate_yaml_model(
                    contract_path,
                    ModelGenericYaml,
                )

                return yaml_model.model_dump()
        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to load contract: {e!s}",
                details={"contract_path": str(contract_path)},
            ) from e

    def _get_field_default(
        self,
        field: str,
        tool_name: str,
        tool_path: Path,
        primary_actions: list[str],
        execution_mode: str,
    ) -> str | int | float | bool | list | dict | None:
        """
        Get default value for a field based on ONEX canonical patterns.

        This uses pattern matching instead of hardcoded tool names.
        """
        # Action field - use execution mode to determine action
        if field == "action":
            if execution_mode == "introspect":
                return (
                    "introspect"
                    if "introspect" in primary_actions
                    else primary_actions[0] if primary_actions else "introspect"
                )
            if execution_mode == "dry_run":
                return (
                    "validate"
                    if "validate" in primary_actions
                    else primary_actions[0] if primary_actions else "validate"
                )
            return primary_actions[0] if primary_actions else "process"

        # Contract path - common pattern for validation tools
        if field == "contract_path":
            contract_file = tool_path / "contract.yaml"
            return str(contract_file) if contract_file.exists() else None

        # Target path - common pattern for analysis/management tools
        if field == "target_path":
            return str(tool_path)

        # Tool patterns - common for discovery/scanning tools
        if field == "tool_patterns":
            return ["**/tool_*/v*_*_*/node.py"]

        # Schema validation - common boolean flags
        if field in [
            "schema_validation",
            "reference_validation",
            "strict_mode",
            "fail_fast",
        ]:
            return execution_mode != "dry_run"  # Enable validation unless dry run

        # Check imports only - common for validation tools
        if field == "check_imports_only":
            return execution_mode == "dry_run"

        # Version - semantic version default
        if field == "version":
            return {"major": 1, "minor": 0, "patch": 0}

        # No default available
        return None

    def get_tool_capabilities(self, tool_path: Path) -> ModelNodeCapabilities:
        """
        Get tool capabilities from its contract.

        Args:
            tool_path: Path to tool directory

        Returns:
            ModelNodeCapabilities: Properly typed node capabilities
        """
        try:
            contract_path = tool_path / "contract.yaml"

            if not contract_path.exists():
                return ModelNodeCapabilities(
                    actions=[],
                    protocols=[],
                    metadata={"error": "Contract not found"},
                )

            contract = self._load_contract(contract_path)

            # Extract actions from primary_actions or input_state
            actions = contract.get("primary_actions", [])
            if not actions and "input_state" in contract:
                # Try to extract from enum definitions
                input_state = contract["input_state"]
                if isinstance(input_state, dict) and "properties" in input_state:
                    action_prop = input_state["properties"].get("action", {})
                    if "enum" in action_prop:
                        actions = action_prop["enum"]

            # Ensure actions is a list of strings
            if not isinstance(actions, list):
                actions = []
            actions = [str(action) for action in actions]

            # Extract protocols - default to common ONEX patterns
            protocols = ["CLI", "HTTP", "event_bus"]

            # Build metadata
            metadata = {
                "name": contract.get("node_name", "unknown"),
                "version": str(contract.get("node_version", "1.0.0")),
                "description": contract.get("description", ""),
                "category": contract.get("category", "tool"),
                "domain": (
                    tool_path.parts[-3] if len(tool_path.parts) >= 3 else "unknown"
                ),  # Extract domain from path
            }

            return ModelNodeCapabilities(
                actions=actions,
                protocols=protocols,
                metadata=metadata,
            )

        except Exception as e:
            return ModelNodeCapabilities(
                actions=[],
                protocols=[],
                metadata={"error": str(e)},
            )
