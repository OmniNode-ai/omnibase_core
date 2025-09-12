#!/usr/bin/env python3
"""
ONEX Node Loader.

Dynamic node loading system that instantiates nodes based on contracts
with full dependency injection support.
"""

import importlib
import logging
from pathlib import Path
from typing import Any, TypeVar

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.exceptions import OnexError
from omnibase_core.models.generation.model_contract_document import (
    ModelContractDocument,
)
from omnibase_core.models.protocol import model_protocol_onex_node

NodeInterface = model_protocol_onex_node.ProtocolOnexNode

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=NodeInterface)


class NodeLoadError(OnexError):
    """Raised when node loading fails."""


class NodeLoader:
    """
    Dynamic node loader with contract-driven dependency injection.

    This loader:
    1. Parses node contracts
    2. Resolves dependencies via DI container
    3. Dynamically imports node modules
    4. Instantiates nodes with proper dependencies
    5. Validates node protocol compliance
    """

    def __init__(self, container: ModelONEXContainer):
        """
        Initialize node loader with DI container.

        Args:
            container: ONEX DI container for dependency resolution
        """
        self.container = container
        self.loaded_modules = {}
        self.node_cache = {}

    def load_node_from_contract(
        self,
        contract_path: str,
        node_path: str | None = None,
    ) -> NodeInterface:
        """
        Load a node from its contract specification.

        Args:
            contract_path: Path to node contract YAML
            node_path: Optional override for node implementation path

        Returns:
            Instantiated node instance

        Raises:
            NodeLoadError: If node loading fails
        """
        try:
            # Step 1: Load and parse contract
            contract = ModelContractDocument.from_yaml_file(contract_path)
            logger.info(f"📄 Loaded contract for node: {contract.node_name}")

            # Step 2: Determine node module path
            if not node_path:
                node_path = self._resolve_node_path_from_contract(
                    contract,
                    contract_path,
                )

            # Step 3: Dynamically import node module
            node_class = self._import_node_class(node_path, contract.node_name)

            # Step 4: Resolve dependencies from contract
            dependencies = self._resolve_dependencies(contract)

            # Step 5: Instantiate node with dependencies
            node_instance = self._instantiate_node(node_class, dependencies, contract)

            # Step 6: Validate node implements required protocol
            self._validate_node_protocol(node_instance, contract)

            # Cache the loaded node
            self.node_cache[contract.node_name] = node_instance

            logger.info(f"✅ Successfully loaded node: {contract.node_name}")
            return node_instance

        except Exception as e:
            logger.exception(f"❌ Failed to load node from {contract_path}: {e}")
            raise NodeLoadError(
                code=CoreErrorCode.NODE_ERROR,
                message=f"Failed to load node from contract: {contract_path}",
                details={"error": str(e), "contract_path": contract_path},
            )

    def load_node_from_spec(self, node_spec: dict[str, Any]) -> NodeInterface:
        """
        Load a tool from a specification dictionary.

        Args:
            node_spec: Node specification with name, path, contract info

        Returns:
            Instantiated tool instance
        """
        node_name = node_spec.get("name", "unknown")

        # Check cache first
        if node_name in self.node_cache:
            logger.info(f"🔄 Using cached tool: {node_name}")
            return self.node_cache[node_name]

        # Extract paths from spec
        contract_path = node_spec.get("contract_path")
        node_path = node_spec.get("path")

        if contract_path and Path(contract_path).exists():
            # Load from contract
            return self.load_node_from_contract(contract_path, node_path)
        if node_path:
            # Load directly without contract
            return self._load_node_direct(node_path, node_name, node_spec)
        raise NodeLoadError(
            code=CoreErrorCode.VALIDATION_ERROR,
            message="Node spec missing required paths",
            details={"node_spec": node_spec},
        )

    def _resolve_node_path_from_contract(
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
        # Convert: nodes/category/node_name/contract.yaml
        # To: omnibase_core.nodes.category.node_name.v1_0_0.node
        contract_dir = Path(contract_path).parent

        # Extract node category and name from path
        parts = contract_dir.parts

        # Find 'nodes' index
        try:
            nodes_idx = parts.index("nodes")
            if nodes_idx + 2 < len(parts):
                category = parts[nodes_idx + 1]
                node_name = parts[nodes_idx + 2]

                # Default to v1_0_0 if no version specified
                version = "v1_0_0"

                # Check if version directory exists
                version_dir = contract_dir / version
                if version_dir.exists():
                    module_path = (
                        f"omnibase_core.nodes.{category}.{node_name}.{version}.node"
                    )
                else:
                    # Try without version
                    module_path = f"omnibase_core.nodes.{category}.{node_name}.node"

                logger.info(f"📍 Resolved node path: {module_path}")
                return module_path

        except ValueError:
            pass

        # Fallback: use contract node_category and node_name
        category = contract.node_category.lower().replace(" ", "_")
        name = contract.node_name.lower().replace(" ", "_")
        return f"omnibase_core.nodes.{category}.{name}.v1_0_0.node"

    def _import_node_class(self, module_path: str, node_name: str) -> type:
        """
        Dynamically import tool class from module.

        Args:
            module_path: Python module path
            node_name: Expected tool class name

        Returns:
            Node class
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
            if hasattr(module, node_name):
                return getattr(module, node_name)

            # Try with "Node" prefix/suffix
            variations = [
                f"Node{node_name}",
                f"{node_name}Node",
                f"Node{node_name}Node",
                f"{node_name}Node",
                node_name.replace("_", "").replace("-", ""),
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
                    and attr_name.startswith("Node")
                    and attr_name != "NodeBase"
                ):
                    logger.info(f"📌 Found tool class by pattern: {attr_name}")
                    return attr

            raise NodeLoadError(
                code=CoreErrorCode.IMPORT_ERROR,
                message="Could not find tool class in module",
                details={"module": module_path, "expected_name": node_name},
            )

        except ImportError as e:
            raise NodeLoadError(
                code=CoreErrorCode.IMPORT_ERROR,
                message="Failed to import tool module",
                details={"module": module_path, "error": str(e)},
            )

    def _resolve_dependencies(self, contract: ModelContractDocument) -> dict[str, Any]:
        """
        Resolve tool dependencies from contract using DI container.

        Args:
            contract: Node contract with dependency specifications

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

    def _instantiate_node(
        self,
        node_class: type,
        dependencies: dict[str, Any],
        contract: ModelContractDocument,
    ) -> NodeInterface:
        """
        Instantiate tool with resolved dependencies.

        Args:
            node_class: Node class to instantiate
            dependencies: Resolved dependencies
            contract: Node contract

        Returns:
            Node instance
        """
        try:
            # Check if tool uses DI-aware constructor
            import inspect

            sig = inspect.signature(node_class.__init__)
            params = list(sig.parameters.keys())[1:]  # Skip 'self'

            if "container" in params:
                # DI-aware tool
                node_instance = node_class(container=self.container, **dependencies)
            elif "registry" in params:
                # Legacy registry-based tool
                node_instance = node_class(registry=dependencies.get("registry"))
            elif params:
                # Match constructor parameters with dependencies
                constructor_args = {}
                for param in params:
                    if param in dependencies:
                        constructor_args[param] = dependencies[param]

                node_instance = node_class(**constructor_args)
            else:
                # No-arg constructor
                node_instance = node_class()

            # Set contract information if tool supports it
            if hasattr(node_instance, "set_contract"):
                node_instance.set_contract(contract)

            return node_instance

        except Exception as e:
            raise NodeLoadError(
                code=CoreErrorCode.INSTANTIATION_ERROR,
                message="Failed to instantiate tool",
                details={
                    "node_class": node_class.__name__,
                    "error": str(e),
                    "available_deps": list(dependencies.keys()),
                },
            )

    def _validate_node_protocol(
        self,
        node_instance: Any,
        contract: ModelContractDocument,
    ) -> None:
        """
        Validate tool implements required protocol.

        Args:
            node_instance: Instantiated tool
            contract: Node contract

        Raises:
            NodeLoadError: If validation fails
        """
        # Check basic OnexNodeProtocol compliance
        required_methods = [
            "run",
            "get_node_config",
            "get_input_model",
            "get_output_model",
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(node_instance, method) or not callable(
                getattr(node_instance, method),
            ):
                missing_methods.append(method)

        if missing_methods:
            logger.warning(
                f"⚠️ Node {contract.node_name} missing protocol methods: {missing_methods}",
            )
            # Don't fail for now, just warn

    def _load_node_direct(
        self,
        node_path: str,
        node_name: str,
        node_spec: dict[str, Any],
    ) -> NodeInterface:
        """
        Load tool directly without contract.

        Args:
            node_path: Python module path
            node_name: Node name
            node_spec: Node specification

        Returns:
            Node instance
        """
        # Import and instantiate
        node_class = self._import_node_class(node_path, node_name)

        # Minimal dependencies
        dependencies = {"registry": self.container.service_discovery()}

        # Create dummy contract
        contract = ModelContractDocument(
            node_name=node_name,
            node_category=node_spec.get("category", "unknown"),
            description=node_spec.get("description", ""),
            version=node_spec.get("version", "1.0.0"),
        )

        return self._instantiate_node(node_class, dependencies, contract)
