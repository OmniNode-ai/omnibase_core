"""
Tool discovery service for ONEX tool class discovery and instantiation operations.

This service extracts tool discovery operations from ModelNodeBase as part of
NODEBASE-001 Phase 3 deconstruction, providing centralized tool class
discovery, module resolution, instantiation, and error handling.

Key Features:
- Tool class discovery from module paths and contracts
- Dynamic module import with security validation
- Tool instantiation with DI containers
- Legacy registry pattern support for current standards
- Module caching for performance
- Comprehensive error handling and logging

Author: ONEX Framework Team
"""

import importlib
import re
import time
from pathlib import Path
from typing import Any

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.decorators import allow_any_type
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.core.model_contract_content import ModelContractContent

from .models.model_tool_discovery_config import ModelToolDiscoveryConfig
from .models.model_tool_discovery_result import ModelToolDiscoveryResult


@allow_any_type(
    "Service interfaces require Any types for generic tool and registry handling",
)
class ToolDiscoveryService:
    """
    Tool discovery service for tool class discovery and instantiation extracted from ModelNodeBase.

    Provides centralized operations for:
    - Resolving tool classes from contract specifications
    - Building module paths from contract file locations
    - Dynamic module import with security validation
    - Tool instantiation with DI containers
    - Legacy registry pattern fallback support
    - Module and tool instance caching for performance

    This service implements the ProtocolToolDiscoveryService interface for duck typing.
    """

    def __init__(self, config: ModelToolDiscoveryConfig | None = None):
        """
        Initialize tool discovery service with configuration.

        Args:
            config: Optional configuration for tool discovery operations
        """
        self._config = config or ModelToolDiscoveryConfig()
        self._module_cache: dict[str, Any] = {}
        self._tool_cache: dict[str, Any] = {}
        self._validation_cache: dict[str, bool] = {}

    @allow_any_type("Registry parameter must accept any registry type for duck typing")
    def resolve_tool_from_contract(
        self,
        contract_content: ModelContractContent,
        registry: Any,
        contract_path: Path,
    ) -> ModelToolDiscoveryResult:
        """
        Resolve and instantiate tool from contract specification.

        This method extracts the main tool resolution logic from ModelNodeBase,
        providing centralized tool discovery and instantiation.

        Args:
            contract_content: Loaded contract with tool specification
            registry: Registry/container for tool instantiation
            contract_path: Path to contract file for module resolution

        Returns:
            ModelToolDiscoveryResult: Complete tool discovery and instantiation result

        Raises:
            OnexError: If tool resolution or instantiation fails
        """
        start_time = time.time()

        try:
            main_tool_class_name = contract_content.tool_specification.main_tool_class

            emit_log_event(
                LogLevel.INFO,
                f"ToolDiscoveryService: Resolving tool {main_tool_class_name}",
                {
                    "tool_class": main_tool_class_name,
                    "contract_path": str(contract_path),
                    "registry_type": type(registry).__name__,
                },
            )

            # Try Phase 0 pattern first (direct module import)
            if (
                hasattr(registry, "_is_phase_0_container")
                and registry._is_phase_0_container
            ):
                result = self._resolve_tool_from_module(
                    main_tool_class_name,
                    registry,
                    contract_path,
                )
                result.total_time_ms = (time.time() - start_time) * 1000
                return result

            # Try legacy registry pattern
            if hasattr(registry, "get_tool"):
                result = self._resolve_tool_from_registry(
                    main_tool_class_name,
                    registry,
                    contract_path,
                )
                result.total_time_ms = (time.time() - start_time) * 1000
                return result

            raise OnexError(
                code=CoreErrorCode.TOOL_NOT_FOUND,
                message=f"No resolution method available for tool '{main_tool_class_name}'",
                details={
                    "tool_class": main_tool_class_name,
                    "registry_type": type(registry).__name__,
                    "available_methods": [
                        (
                            "phase_0_container"
                            if hasattr(registry, "_is_phase_0_container")
                            else None
                        ),
                        ("legacy_registry" if hasattr(registry, "get_tool") else None),
                    ],
                },
            )

        except Exception as e:
            if isinstance(e, OnexError):
                raise
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to resolve tool from contract: {e!s}",
                context={
                    "tool_class": getattr(
                        contract_content.tool_specification,
                        "main_tool_class",
                        "unknown",
                    ),
                    "contract_path": str(contract_path),
                },
            ) from e

    @allow_any_type("Registry parameter must accept any registry type for duck typing")
    def _resolve_tool_from_module(
        self,
        main_tool_class_name: str,
        registry: Any,
        contract_path: Path,
    ) -> ModelToolDiscoveryResult:
        """
        Resolve tool using Phase 0 pattern (direct module import).

        Args:
            main_tool_class_name: Name of tool class to resolve
            registry: Registry with container for instantiation
            contract_path: Path to contract file

        Returns:
            ModelToolDiscoveryResult: Tool discovery result with Phase 0 method
        """
        module_import_start = time.time()

        # Build module path from contract location
        module_path = self.build_module_path_from_contract(contract_path)

        # Validate module path for security
        self.validate_module_path(module_path)

        # Import module and get tool class
        tool_class = self.discover_tool_class_from_module(
            module_path,
            main_tool_class_name,
        )

        module_import_time = (time.time() - module_import_start) * 1000

        # Instantiate tool with container
        instantiation_start = time.time()
        tool_instance = self.instantiate_tool_with_container(
            tool_class,
            registry._container,
        )
        instantiation_time = (time.time() - instantiation_start) * 1000

        return ModelToolDiscoveryResult(
            tool_instance=tool_instance,
            tool_class=tool_class,
            module_path=module_path,
            tool_class_name=main_tool_class_name,
            contract_path=contract_path,
            discovery_method="module",
            instantiation_method="container",
            module_import_time_ms=module_import_time,
            tool_instantiation_time_ms=instantiation_time,
            validation_results={
                "module_path_valid": True,
                "tool_class_found": True,
                "instantiation_successful": True,
            },
            tool_metadata={
                "tool_class_module": getattr(tool_class, "__module__", "unknown"),
                "tool_class_qualname": getattr(tool_class, "__qualname__", "unknown"),
            },
            fallback_used=False,
            cache_hit=module_path in self._module_cache,
        )

    def _resolve_tool_from_registry(
        self,
        main_tool_class_name: str,
        registry: Any,
        contract_path: Path,
    ) -> ModelToolDiscoveryResult:
        """
        Resolve tool using legacy registry pattern.

        Args:
            main_tool_class_name: Name of tool class to resolve
            registry: Legacy registry with get_tool method
            contract_path: Path to contract file

        Returns:
            ModelToolDiscoveryResult: Tool discovery result with registry method
        """
        instantiation_start = time.time()

        # Convert class name to registry key
        registry_key = self.convert_class_name_to_registry_key(main_tool_class_name)

        emit_log_event(
            LogLevel.INFO,
            f"Resolving tool via registry: {main_tool_class_name} -> {registry_key}",
            {
                "class_name": main_tool_class_name,
                "registry_key": registry_key,
                "registry_type": type(registry).__name__,
            },
        )

        # Debug: Check available tools if possible
        if hasattr(registry, "list_tools"):
            try:
                available_tools = registry.list_tools()
                emit_log_event(
                    LogLevel.DEBUG,
                    f"Available tools in registry: {available_tools}",
                    {
                        "available_tools": available_tools,
                        "looking_for": registry_key,
                    },
                )
            except Exception as e:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Failed to list available tools: {e!s}",
                    {"error": str(e)},
                )

        # Get tool from registry
        tool_instance = registry.get_tool(registry_key)
        if tool_instance is None:
            raise OnexError(
                code=CoreErrorCode.TOOL_NOT_FOUND,
                message=f"Tool '{main_tool_class_name}' not found in registry",
                details={
                    "tool_class": main_tool_class_name,
                    "registry_key": registry_key,
                    "registry_type": type(registry).__name__,
                },
            )

        instantiation_time = (time.time() - instantiation_start) * 1000

        return ModelToolDiscoveryResult(
            tool_instance=tool_instance,
            tool_class=type(tool_instance),
            module_path="registry_managed",
            tool_class_name=main_tool_class_name,
            contract_path=contract_path,
            discovery_method="registry",
            instantiation_method="registry",
            registry_key=registry_key,
            tool_instantiation_time_ms=instantiation_time,
            validation_results={
                "registry_key_resolved": True,
                "tool_found_in_registry": True,
            },
            tool_metadata={
                "registry_type": type(registry).__name__,
                "tool_instance_type": type(tool_instance).__name__,
            },
            fallback_used=True,
            cache_hit=False,
        )

    def discover_tool_class_from_module(
        self,
        module_path: str,
        tool_class_name: str,
    ) -> type:
        """
        Discover tool class from module path.

        Args:
            module_path: Python module path (e.g., 'omnibase.tools.xyz.node')
            tool_class_name: Name of tool class to find

        Returns:
            Tool class type

        Raises:
            OnexError: If module import or class discovery fails
        """
        try:
            # Check module cache first if caching is enabled
            if self._config.enable_module_caching and module_path in self._module_cache:
                module = self._module_cache[module_path]
                emit_log_event(
                    LogLevel.DEBUG,
                    f"Using cached module: {module_path}",
                    {"module_path": module_path, "cache_hit": True},
                )
            else:
                # Import module dynamically
                emit_log_event(
                    LogLevel.DEBUG,
                    f"Importing module: {module_path}",
                    {"module_path": module_path},
                )

                module = importlib.import_module(module_path)

                # Cache module if caching is enabled
                if self._config.enable_module_caching:
                    self._module_cache[module_path] = module

            # Get tool class from module
            if not hasattr(module, tool_class_name):
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Tool class '{tool_class_name}' not found in module",
                    details={
                        "module_path": module_path,
                        "tool_class": tool_class_name,
                        "available_attributes": [
                            attr for attr in dir(module) if not attr.startswith("_")
                        ],
                    },
                )

            tool_class = getattr(module, tool_class_name)

            # Validate tool class if validation is enabled
            if self._config.enable_tool_validation:
                if not callable(tool_class):
                    raise OnexError(
                        code=CoreErrorCode.VALIDATION_ERROR,
                        message=f"Tool class '{tool_class_name}' is not callable",
                        details={
                            "module_path": module_path,
                            "tool_class": tool_class_name,
                            "type": type(tool_class).__name__,
                        },
                    )

            emit_log_event(
                LogLevel.DEBUG,
                f"Successfully discovered tool class: {tool_class_name}",
                {
                    "module_path": module_path,
                    "tool_class": tool_class_name,
                    "tool_class_type": type(tool_class).__name__,
                },
            )

            return tool_class

        except ImportError as e:
            raise OnexError(
                code=CoreErrorCode.MODULE_NOT_FOUND,
                message=f"Failed to import module: {module_path}",
                details={
                    "module_path": module_path,
                    "tool_class": tool_class_name,
                    "import_error": str(e),
                },
            ) from e
        except AttributeError as e:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Tool class '{tool_class_name}' not found in module",
                details={
                    "module_path": module_path,
                    "tool_class": tool_class_name,
                    "attribute_error": str(e),
                },
            ) from e

    def instantiate_tool_with_container(
        self,
        tool_class: type,
        container: Any,
    ) -> Any:
        """
        Instantiate tool with DI container.

        Args:
            tool_class: Tool class to instantiate
            container: DI container for tool dependencies

        Returns:
            Instantiated tool instance

        Raises:
            OnexError: If tool instantiation fails
        """
        try:
            # Check tool cache if caching is enabled
            cache_key = f"{tool_class.__module__}.{tool_class.__name__}"
            if self._config.cache_tool_instances and cache_key in self._tool_cache:
                emit_log_event(
                    LogLevel.DEBUG,
                    f"Using cached tool instance: {tool_class.__name__}",
                    {"tool_class": tool_class.__name__, "cache_hit": True},
                )
                return self._tool_cache[cache_key]

            emit_log_event(
                LogLevel.DEBUG,
                f"Instantiating tool with container: {tool_class.__name__}",
                {
                    "tool_class": tool_class.__name__,
                    "container_type": type(container).__name__,
                },
            )

            # Instantiate tool with container
            tool_instance = tool_class(container)

            # Cache tool instance if caching is enabled
            if self._config.cache_tool_instances:
                self._tool_cache[cache_key] = tool_instance

            emit_log_event(
                LogLevel.DEBUG,
                f"Successfully instantiated tool: {tool_class.__name__}",
                {
                    "tool_class": tool_class.__name__,
                    "tool_instance_type": type(tool_instance).__name__,
                },
            )

            return tool_instance

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.INITIALIZATION_FAILED,
                message=f"Failed to instantiate tool '{tool_class.__name__}'",
                context={
                    "tool_class": tool_class.__name__,
                    "tool_module": getattr(tool_class, "__module__", "unknown"),
                    "container_type": type(container).__name__,
                    "instantiation_error": str(e),
                },
            ) from e

    def build_module_path_from_contract(
        self,
        contract_path: Path,
    ) -> str:
        """
        Build module path from contract file path.

        Args:
            contract_path: Path to contract.yaml file

        Returns:
            Python module path for tool's node.py file

        Raises:
            OnexError: If module path construction fails
        """
        try:
            # Get the directory path and convert to module path
            node_dir = contract_path.parent

            # Find the relative path from src/
            src_index = -1
            for i, part in enumerate(node_dir.parts):
                if part == "src":
                    src_index = i + 1
                    break

            if src_index > 0:
                # Build module path from parts after 'src/'
                module_parts = [*list(node_dir.parts[src_index:]), "node"]
                module_path = ".".join(module_parts)
            else:
                # Fallback to trying to construct from full path
                module_path = f"omnibase.tools.{node_dir.parts[-3]}.{node_dir.parts[-2]}.{node_dir.parts[-1]}.node"

            emit_log_event(
                LogLevel.DEBUG,
                f"Built module path from contract: {module_path}",
                {
                    "contract_path": str(contract_path),
                    "node_dir": str(node_dir),
                    "module_path": module_path,
                },
            )

            return module_path

        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to build module path from contract: {e!s}",
                details={
                    "contract_path": str(contract_path),
                    "error": str(e),
                },
            ) from e

    def validate_module_path(
        self,
        module_path: str,
    ) -> bool:
        """
        Validate module path for security and correctness.

        Args:
            module_path: Python module path to validate

        Returns:
            bool: True if module path is valid

        Raises:
            OnexError: If module path is invalid or insecure
        """
        # Check validation cache first
        if module_path in self._validation_cache:
            return self._validation_cache[module_path]

        try:
            # Basic validation
            if not module_path:
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message="Module path cannot be empty",
                    details={"module_path": module_path},
                )

            # Security validation for strict mode
            if self._config.module_path_validation_strict:
                # Check for potentially dangerous characters
                if not module_path.replace(".", "").replace("_", "").isalnum():
                    raise OnexError(
                        code=CoreErrorCode.VALIDATION_ERROR,
                        message=f"Invalid module path contains unsafe characters: {module_path}",
                        details={
                            "module_path": module_path,
                            "reason": "Module path must only contain alphanumeric characters, dots, and underscores",
                        },
                    )

                # Check for path traversal attempts
                if ".." in module_path or "/" in module_path or "\\" in module_path:
                    raise OnexError(
                        code=CoreErrorCode.VALIDATION_ERROR,
                        message=f"Module path contains path traversal characters: {module_path}",
                        details={
                            "module_path": module_path,
                            "reason": "Module path cannot contain path traversal sequences",
                        },
                    )

            # Cache validation result
            self._validation_cache[module_path] = True

            emit_log_event(
                LogLevel.DEBUG,
                f"Module path validation passed: {module_path}",
                {
                    "module_path": module_path,
                    "strict_mode": self._config.module_path_validation_strict,
                },
            )

            return True

        except OnexError:
            # Cache negative result
            self._validation_cache[module_path] = False
            raise

    def convert_class_name_to_registry_key(
        self,
        class_name: str,
    ) -> str:
        """
        Convert tool class name to registry key format.

        Args:
            class_name: Tool class name (e.g., ToolContractValidator)

        Returns:
            Registry key in snake_case format (e.g., contract_validator)
        """
        # Remove "Tool" prefix if present
        if class_name.startswith("Tool"):
            name = class_name[4:]  # Remove "Tool"
        else:
            name = class_name

        # Convert from CamelCase to snake_case
        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

        emit_log_event(
            LogLevel.DEBUG,
            f"Converted class name to registry key: {class_name} -> {snake_case}",
            {"class_name": class_name, "registry_key": snake_case},
        )

        return snake_case
