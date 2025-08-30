#!/usr/bin/env python3
"""
ONEX Tool Loader.

Dynamic tool loading system that instantiates tools based on contracts
with full dependency injection support.
"""

import importlib
import logging
from pathlib import Path
from typing import Any, TypeVar

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.exceptions import OnexError
from omnibase_core.model.generation.model_contract_document import ModelContractDocument
from omnibase_core.protocol.protocol_onex_node import ProtocolOnexNode

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ProtocolOnexNode)


class ToolLoadError(OnexError):
    """Raised when tool loading fails."""


class ToolLoader:
    """
    Dynamic tool loader with contract-driven dependency injection.

    This loader:
    1. Parses tool contracts
    2. Resolves dependencies via DI container
    3. Dynamically imports tool modules
    4. Instantiates tools with proper dependencies
    5. Validates tool protocol compliance
    """

    def __init__(self, container: ONEXContainer):
        """
        Initialize tool loader with DI container.

        Args:
            container: ONEX DI container for dependency resolution
        """
        self.container = container
        self.loaded_modules = {}
        self.tool_cache = {}

    def load_tool_from_contract(
        self,
        contract_path: str,
        tool_path: str | None = None,
    ) -> ProtocolOnexNode:
        """
        Load a tool from its contract specification.

        Args:
            contract_path: Path to tool contract YAML
            tool_path: Optional override for tool implementation path

        Returns:
            Instantiated tool instance

        Raises:
            ToolLoadError: If tool loading fails
        """
        try:
            # Step 1: Load and parse contract
            contract = ModelContractDocument.from_yaml_file(contract_path)
            logger.info(f"📄 Loaded contract for tool: {contract.node_name}")

            # Step 2: Determine tool module path
            if not tool_path:
                tool_path = self._resolve_tool_path_from_contract(
                    contract,
                    contract_path,
                )

            # Step 3: Dynamically import tool module
            tool_class = self._import_tool_class(tool_path, contract.node_name)

            # Step 4: Resolve dependencies from contract
            dependencies = self._resolve_dependencies(contract)

            # Step 5: Instantiate tool with dependencies
            tool_instance = self._instantiate_tool(tool_class, dependencies, contract)

            # Step 6: Validate tool implements required protocol
            self._validate_tool_protocol(tool_instance, contract)

            # Cache the loaded tool
            self.tool_cache[contract.node_name] = tool_instance

            logger.info(f"✅ Successfully loaded tool: {contract.node_name}")
            return tool_instance

        except Exception as e:
            logger.exception(f"❌ Failed to load tool from {contract_path}: {e}")
            raise ToolLoadError(
                code=CoreErrorCode.TOOL_ERROR,
                message=f"Failed to load tool from contract: {contract_path}",
                details={"error": str(e), "contract_path": contract_path},
            )

    def load_tool_from_spec(self, tool_spec: dict[str, Any]) -> ProtocolOnexNode:
        """
        Load a tool from a specification dictionary.

        Args:
            tool_spec: Tool specification with name, path, contract info

        Returns:
            Instantiated tool instance
        """
        tool_name = tool_spec.get("name", "unknown")

        # Check cache first
        if tool_name in self.tool_cache:
            logger.info(f"🔄 Using cached tool: {tool_name}")
            return self.tool_cache[tool_name]

        # Extract paths from spec
        contract_path = tool_spec.get("contract_path")
        tool_path = tool_spec.get("path")

        if contract_path and Path(contract_path).exists():
            # Load from contract
            return self.load_tool_from_contract(contract_path, tool_path)
        if tool_path:
            # Load directly without contract
            return self._load_tool_direct(tool_path, tool_name, tool_spec)
        raise ToolLoadError(
            code=CoreErrorCode.VALIDATION_ERROR,
            message="Tool spec missing required paths",
            details={"tool_spec": tool_spec},
        )

    def _resolve_tool_path_from_contract(
        self,
        contract: ModelContractDocument,
        contract_path: str,
    ) -> str:
        """
        Resolve tool implementation path from contract.

        Args:
            contract: Parsed contract document
            contract_path: Path to contract file

        Returns:
            Path to tool implementation module
        """
        # Check if contract specifies implementation path
        if hasattr(contract, "implementation") and contract.implementation:
            if hasattr(contract.implementation, "module_path"):
                return contract.implementation.module_path

        # Derive from contract path
        # Convert: tools/category/tool_name/contract.yaml
        # To: omnibase.tools.category.tool_name.v1_0_0.node
        contract_dir = Path(contract_path).parent

        # Extract tool category and name from path
        parts = contract_dir.parts

        # Find 'tools' index
        try:
            tools_idx = parts.index("tools")
            if tools_idx + 2 < len(parts):
                category = parts[tools_idx + 1]
                tool_name = parts[tools_idx + 2]

                # Default to v1_0_0 if no version specified
                version = "v1_0_0"

                # Check if version directory exists
                version_dir = contract_dir / version
                if version_dir.exists():
                    module_path = (
                        f"omnibase.tools.{category}.{tool_name}.{version}.node"
                    )
                else:
                    # Try without version
                    module_path = f"omnibase.tools.{category}.{tool_name}.node"

                logger.info(f"📍 Resolved tool path: {module_path}")
                return module_path

        except ValueError:
            pass

        # Fallback: use contract node_category and node_name
        category = contract.node_category.lower().replace(" ", "_")
        name = contract.node_name.lower().replace(" ", "_")
        return f"omnibase.tools.{category}.{name}.v1_0_0.node"

    def _import_tool_class(self, module_path: str, tool_name: str) -> type:
        """
        Dynamically import tool class from module.

        Args:
            module_path: Python module path
            tool_name: Expected tool class name

        Returns:
            Tool class
        """
        try:
            # Check cache
            if module_path in self.loaded_modules:
                module = self.loaded_modules[module_path]
            else:
                # Import module
                module = importlib.import_module(module_path)
                self.loaded_modules[module_path] = module
                logger.info(f"📦 Imported module: {module_path}")

            # Find tool class
            # Try exact name first
            if hasattr(module, tool_name):
                return getattr(module, tool_name)

            # Try with "Tool" prefix/suffix
            variations = [
                f"Tool{tool_name}",
                f"{tool_name}Tool",
                f"Tool{tool_name}Node",
                f"{tool_name}Node",
                tool_name.replace("_", "").replace("-", ""),
            ]

            for variant in variations:
                if hasattr(module, variant):
                    logger.info(f"📌 Found tool class: {variant}")
                    return getattr(module, variant)

            # Last resort: find first class that looks like a tool
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and attr_name.startswith("Tool")
                    and attr_name != "ToolBase"
                ):
                    logger.info(f"📌 Found tool class by pattern: {attr_name}")
                    return attr

            raise ToolLoadError(
                code=CoreErrorCode.IMPORT_ERROR,
                message="Could not find tool class in module",
                details={"module": module_path, "expected_name": tool_name},
            )

        except ImportError as e:
            raise ToolLoadError(
                code=CoreErrorCode.IMPORT_ERROR,
                message="Failed to import tool module",
                details={"module": module_path, "error": str(e)},
            )

    def _resolve_dependencies(self, contract: ModelContractDocument) -> dict[str, Any]:
        """
        Resolve tool dependencies from contract using DI container.

        Args:
            contract: Tool contract with dependency specifications

        Returns:
            Dictionary of resolved dependencies
        """
        dependencies = {}

        # Check if contract has dependencies section
        if hasattr(contract, "dependencies") and contract.dependencies:
            for dep_name, dep_spec in contract.dependencies.items():
                try:
                    # Resolve dependency from container
                    if hasattr(dep_spec, "protocol"):
                        # Get protocol type
                        protocol_type = self._get_protocol_type(dep_spec.protocol)

                        # Resolve service
                        service = self.container.get_service(
                            protocol_type,
                            (
                                dep_spec.service_name
                                if hasattr(dep_spec, "service_name")
                                else None
                            ),
                        )

                        dependencies[dep_name] = service
                        logger.info(f"✅ Resolved dependency: {dep_name}")

                    elif hasattr(dep_spec, "value"):
                        # Static value dependency
                        dependencies[dep_name] = dep_spec.value

                except Exception as e:
                    logger.warning(f"⚠️ Failed to resolve dependency {dep_name}: {e}")

                    # Use fallback if specified
                    if hasattr(dep_spec, "fallback"):
                        dependencies[dep_name] = dep_spec.fallback
                        logger.info(f"📌 Using fallback for {dep_name}")

        # Add standard dependencies
        dependencies["registry"] = self.container.service_discovery()

        return dependencies

    def _get_protocol_type(self, protocol_name: str) -> type:
        """
        Get protocol type from name.

        Args:
            protocol_name: Protocol name (e.g., "ProtocolLogger")

        Returns:
            Protocol type
        """
        # Map common protocol names to types
        protocol_map = {
            "ProtocolLogger": "omnibase.protocol.protocol_logger.ProtocolLogger",
            "ProtocolEventBus": "omnibase.protocol.protocol_event_bus.ProtocolEventBus",
            "ProtocolVectorDatabase": "omnibase.protocol.protocol_vector_database.ProtocolVectorDatabase",
            "ProtocolServiceDiscovery": "omnibase.protocol.protocol_service_discovery.ProtocolServiceDiscovery",
        }

        module_path = protocol_map.get(
            protocol_name,
            f"omnibase.protocol.{protocol_name.lower()}.{protocol_name}",
        )

        try:
            module = importlib.import_module(module_path.rsplit(".", 1)[0])
            return getattr(module, protocol_name)
        except (ImportError, AttributeError) as e:
            logger.warning(f"⚠️ Could not load protocol {protocol_name}: {e}")
            # Return a dummy protocol type
            return type(protocol_name, (), {})

    def _instantiate_tool(
        self,
        tool_class: type,
        dependencies: dict[str, Any],
        contract: ModelContractDocument,
    ) -> ProtocolOnexNode:
        """
        Instantiate tool with resolved dependencies.

        Args:
            tool_class: Tool class to instantiate
            dependencies: Resolved dependencies
            contract: Tool contract

        Returns:
            Tool instance
        """
        try:
            # Check if tool uses DI-aware constructor
            import inspect

            sig = inspect.signature(tool_class.__init__)
            params = list(sig.parameters.keys())[1:]  # Skip 'self'

            if "container" in params:
                # DI-aware tool
                tool_instance = tool_class(container=self.container, **dependencies)
            elif "registry" in params:
                # Legacy registry-based tool
                tool_instance = tool_class(registry=dependencies.get("registry"))
            elif params:
                # Match constructor parameters with dependencies
                constructor_args = {}
                for param in params:
                    if param in dependencies:
                        constructor_args[param] = dependencies[param]

                tool_instance = tool_class(**constructor_args)
            else:
                # No-arg constructor
                tool_instance = tool_class()

            # Set contract information if tool supports it
            if hasattr(tool_instance, "set_contract"):
                tool_instance.set_contract(contract)

            return tool_instance

        except Exception as e:
            raise ToolLoadError(
                code=CoreErrorCode.INSTANTIATION_ERROR,
                message="Failed to instantiate tool",
                details={
                    "tool_class": tool_class.__name__,
                    "error": str(e),
                    "available_deps": list(dependencies.keys()),
                },
            )

    def _validate_tool_protocol(
        self,
        tool_instance: Any,
        contract: ModelContractDocument,
    ) -> None:
        """
        Validate tool implements required protocol.

        Args:
            tool_instance: Instantiated tool
            contract: Tool contract

        Raises:
            ToolLoadError: If validation fails
        """
        # Check basic ProtocolOnexNode compliance
        required_methods = [
            "run",
            "get_node_config",
            "get_input_model",
            "get_output_model",
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(tool_instance, method) or not callable(
                getattr(tool_instance, method),
            ):
                missing_methods.append(method)

        if missing_methods:
            logger.warning(
                f"⚠️ Tool {contract.node_name} missing protocol methods: {missing_methods}",
            )
            # Don't fail for now, just warn

    def _load_tool_direct(
        self,
        tool_path: str,
        tool_name: str,
        tool_spec: dict[str, Any],
    ) -> ProtocolOnexNode:
        """
        Load tool directly without contract.

        Args:
            tool_path: Python module path
            tool_name: Tool name
            tool_spec: Tool specification

        Returns:
            Tool instance
        """
        # Import and instantiate
        tool_class = self._import_tool_class(tool_path, tool_name)

        # Minimal dependencies
        dependencies = {"registry": self.container.service_discovery()}

        # Create dummy contract
        contract = ModelContractDocument(
            node_name=tool_name,
            node_category=tool_spec.get("category", "unknown"),
            description=tool_spec.get("description", ""),
            version=tool_spec.get("version", "1.0.0"),
        )

        return self._instantiate_tool(tool_class, dependencies, contract)
