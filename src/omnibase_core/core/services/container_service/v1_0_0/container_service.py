"""
Container service for ONEX DI container management and lifecycle operations.

This service extracts DI container operations from ModelNodeBase as part of
NODEBASE-001 Phase 2 deconstruction, providing centralized container
management, service registration, and registry lifecycle operations.

Key Features:
- ModelONEXContainer creation and configuration from contracts
- Dynamic service registration from dependency specifications
- Registry wrapper for current standards
- Container lifecycle and ModelNodeBase reference management
- Comprehensive validation and error handling

Author: ONEX Framework Team
"""

import importlib
from typing import Any

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.decorators import allow_any_type
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.core.model_contract_content import ModelContractContent

from .models.model_container_config import ModelContainerConfig
from .models.model_container_result import ModelContainerResult


@allow_any_type(
    "Service interfaces require Any types for generic container and service handling",
)
class ContainerService:
    """
    Container service for DI container management extracted from ModelNodeBase.

    Provides centralized operations for:
    - Creating ModelONEXContainer from contract dependencies
    - Registering services from dependency specifications
    - Managing registry wrapper for current standards
    - Handling container lifecycle with ModelNodeBase references
    - Validating dependencies and service availability

    This service implements the ProtocolContainerService interface for duck typing.
    """

    def __init__(self, config: ModelContainerConfig | None = None):
        """
        Initialize container service with configuration.

        Args:
            config: Optional configuration for container operations
        """
        self._config = config
        self._service_cache: dict[str, Any] = {}
        self._validation_cache: dict[str, bool] = {}

    def create_container_from_contract(
        self,
        contract_content: ModelContractContent,
        node_id: str,
        nodebase_ref: Any | None = None,
    ) -> ModelContainerResult:
        """
        Create and configure ModelONEXContainer from contract dependencies.

        This method extracts the container creation logic from ModelNodeBase
        initialization, providing centralized DI container management.

        Args:
            contract_content: Loaded contract with dependencies section
            node_id: Node identifier for logging and metadata
            nodebase_ref: Reference to ModelNodeBase instance for version access

        Returns:
            ModelContainerResult: Complete container setup with registry wrapper

        Raises:
            OnexError: If container creation or dependency registration fails
        """
        try:
            # Validate contract has dependencies
            if (
                not hasattr(contract_content, "dependencies")
                or contract_content.dependencies is None
            ):
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message="Contract must have 'dependencies' section for Phase 0 pattern",
                    context={
                        "node_id": node_id,
                        "has_dependencies": hasattr(contract_content, "dependencies"),
                    },
                )

            # Create ModelONEXContainer
            from omnibase_core.core.onex_container import ModelONEXContainer

            container = ModelONEXContainer()
            registered_services: list[str] = []
            failed_services: list[str] = []
            service_metadata: dict[str, dict] = {}
            validation_results: dict[str, bool] = {}

            # Register dependencies from contract
            dep_list = contract_content.dependencies

            emit_log_event(
                LogLevel.INFO,
                f"ContainerService: Creating services for {len(dep_list)} dependencies",
                {
                    "dependency_count": len(dep_list),
                    "node_id": node_id,
                    "service": "container_service",
                },
            )

            for dep in dep_list:
                try:
                    # Create service from dependency specification
                    service = self.create_service_from_dependency(dep)
                    dep_name = getattr(dep, "name", "unknown")

                    if service:
                        # Register service in container
                        service_attr = f"_service_{dep_name}"
                        setattr(container, service_attr, service)
                        registered_services.append(dep_name)

                        # Store service metadata
                        service_metadata[dep_name] = {
                            "service_type": type(service).__name__,
                            "module": getattr(dep, "module", "unknown"),
                            "class_name": getattr(
                                dep,
                                "class_name",
                                getattr(dep, "__dict__", {}).get("class", "unknown"),
                            ),
                            "registration_method": "setattr",
                        }

                        # Validate service was registered correctly
                        validation_results[dep_name] = hasattr(container, service_attr)

                        emit_log_event(
                            LogLevel.DEBUG,
                            f"Registered service: {dep_name}",
                            {
                                "service_name": dep_name,
                                "service_type": type(service).__name__,
                                "node_id": node_id,
                            },
                        )
                    else:
                        failed_services.append(dep_name)
                        validation_results[dep_name] = False

                except Exception as e:
                    dep_name = getattr(dep, "name", "unknown")
                    failed_services.append(dep_name)
                    validation_results[dep_name] = False

                    emit_log_event(
                        LogLevel.WARNING,
                        f"Failed to register service: {dep_name}",
                        {
                            "service_name": dep_name,
                            "error": str(e),
                            "node_id": node_id,
                        },
                    )

            # Add version information placeholder
            container._node_version = None

            # Create registry wrapper
            registry = self.get_registry_wrapper(container, nodebase_ref)

            # Create result with comprehensive metadata
            container_metadata = {
                "node_id": node_id,
                "creation_method": "from_contract_dependencies",
                "total_dependencies": len(dep_list),
                "successful_registrations": len(registered_services),
                "failed_registrations": len(failed_services),
                "container_type": type(container).__name__,
            }

            if self._config:
                container_metadata.update(
                    {
                        "validation_enabled": self._config.enable_service_validation,
                        "lifecycle_logging_enabled": self._config.enable_lifecycle_logging,
                    },
                )

            result = ModelContainerResult(
                container=container,
                registry=registry,
                registered_services=registered_services,
                failed_services=failed_services,
                service_metadata=service_metadata,
                validation_results=validation_results,
                container_metadata=container_metadata,
                lifecycle_state="created",
                node_reference_attached=nodebase_ref is not None,
            )

            emit_log_event(
                LogLevel.INFO,
                f"ContainerService: Successfully created container for {node_id}",
                {
                    "node_id": node_id,
                    "registered_services": len(registered_services),
                    "failed_services": len(failed_services),
                    "total_dependencies": len(dep_list),
                },
            )

            return result

        except OnexError:
            # Re-raise ONEX errors (fail-fast)
            raise
        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to create container from contract: {e!s}",
                context={
                    "node_id": node_id,
                    "has_dependencies": hasattr(contract_content, "dependencies"),
                },
            ) from e

    def create_service_from_dependency(self, dependency: Any) -> Any | None:
        """
        Create service instance from contract dependency specification.

        This method extracts the service creation logic from ModelNodeBase,
        providing centralized service instantiation with proper validation.

        Args:
            dependency: Dependency specification from contract with module/class info

        Returns:
            Service instance or None if creation fails

        Raises:
            OnexError: If dependency specification is invalid
        """
        try:
            dep_name = getattr(dependency, "name", "unknown")

            # Check cache first
            if dep_name in self._service_cache:
                return self._service_cache[dep_name]

            # Validate dependency has module information
            if not hasattr(dependency, "module"):
                return None

            # Pre-validate module path for security
            module_path = dependency.module
            if (
                not module_path
                or not module_path.replace(".", "").replace("_", "").isalnum()
            ):
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid dependency module path: {module_path}",
                    details={
                        "module_path": module_path,
                        "dependency_name": dep_name,
                        "reason": "Module path must be a valid Python module name",
                    },
                )

            # Import module
            module = importlib.import_module(module_path)

            # Get class name from dependency
            class_name = None
            if hasattr(dependency, "class_name"):
                class_name = dependency.class_name
            elif hasattr(dependency, "__dict__") and "class" in dependency.__dict__:
                # Use dict access to avoid keyword conflict
                class_name = dependency.__dict__["class"]

            if not class_name:
                emit_log_event(
                    LogLevel.WARNING,
                    f"No class name found for dependency: {dep_name}",
                    {
                        "dependency_name": dep_name,
                        "module_path": module_path,
                    },
                )
                return None

            # Get service class and create instance
            service_class = getattr(module, class_name)
            service_instance = service_class()

            # Cache successful creation
            self._service_cache[dep_name] = service_instance

            emit_log_event(
                LogLevel.DEBUG,
                f"Created service instance: {dep_name}",
                {
                    "dependency_name": dep_name,
                    "module_path": module_path,
                    "class_name": class_name,
                    "service_type": type(service_instance).__name__,
                },
            )

            return service_instance

        except Exception as e:
            dep_name = getattr(dependency, "name", "unknown")
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to create service from dependency: {dep_name}",
                {
                    "dependency_name": dep_name,
                    "error": str(e),
                    "module": getattr(dependency, "module", "unknown"),
                    "class": getattr(dependency, "__dict__", {}).get(
                        "class",
                        "unknown",
                    ),
                },
            )
            return None

    def validate_container_dependencies(self, container: Any) -> bool:
        """
        Validate container has all required dependencies registered.

        Args:
            container: Container instance to validate

        Returns:
            bool: True if all dependencies are available, False otherwise
        """
        try:
            # Check for service attributes
            service_attrs = [
                attr for attr in dir(container) if attr.startswith("_service_")
            ]

            if not service_attrs:
                emit_log_event(
                    LogLevel.WARNING,
                    "No services found in container",
                    {"container_type": type(container).__name__},
                )
                return False

            # Validate each service is accessible
            for service_attr in service_attrs:
                service = getattr(container, service_attr)
                if service is None:
                    emit_log_event(
                        LogLevel.WARNING,
                        f"Service is None: {service_attr}",
                        {"service_attr": service_attr},
                    )
                    return False

            emit_log_event(
                LogLevel.DEBUG,
                f"Container validation passed: {len(service_attrs)} services",
                {"service_count": len(service_attrs)},
            )

            return True

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Container validation failed: {e!s}",
                {"error": str(e)},
            )
            return False

    def get_registry_wrapper(
        self,
        container: Any,
        nodebase_ref: Any | None = None,
    ) -> Any:
        """
        Create registry wrapper around container for current standards.

        This method extracts the ContainerAsRegistry pattern from ModelNodeBase,
        providing a consistent registry interface over the container.

        Args:
            container: ModelONEXContainer instance
            nodebase_ref: Reference to ModelNodeBase for version access

        Returns:
            Registry wrapper with get_service and get_node_version methods
        """

        class ContainerAsRegistry:
            def __init__(self, container, nodebase_ref=None):
                self._container = container
                self._is_phase_0_container = True
                self._nodebase_ref = nodebase_ref

            def get_service(self, service_type, service_name=None):
                # First try to get from container attributes
                service_attr = f"_service_{service_name or service_type}"
                if hasattr(self._container, service_attr):
                    return getattr(self._container, service_attr)
                # Fallback to container's get_service method if it exists
                if hasattr(self._container, "get_service") and callable(
                    self._container.get_service,
                ):
                    return self._container.get_service(service_type, service_name)
                return None

            def get_node_version(self):
                """
                Get the node version from ModelNodeBase.

                This eliminates the need for tools to call get_tool_version()
                and reload the contract.

                Returns:
                    ModelSemVer: Version from the loaded contract
                """
                if self._nodebase_ref and hasattr(self._nodebase_ref, "node_version"):
                    return self._nodebase_ref.node_version
                if (
                    hasattr(self._container, "_node_version")
                    and self._container._node_version
                ):
                    return self._container._node_version
                msg = "Node version not available in container"
                raise OnexError(
                    msg,
                    CoreErrorCode.OPERATION_FAILED,
                )

            def validate_tool_dependencies(self):
                """Validate tool dependencies are available."""
                # Check if container has required services
                service_attrs = [
                    attr
                    for attr in dir(self._container)
                    if attr.startswith("_service_")
                ]
                return len(service_attrs) > 0

        return ContainerAsRegistry(container, nodebase_ref)

    def update_container_lifecycle(self, registry: Any, nodebase_ref: Any) -> None:
        """
        Update container lifecycle with ModelNodeBase reference and version info.

        This method extracts the container lifecycle management from ModelNodeBase,
        providing centralized lifecycle operations.

        Args:
            registry: Registry wrapper instance
            nodebase_ref: ModelNodeBase instance for version and metadata access
        """
        try:
            # Update registry with ModelNodeBase reference
            if (
                hasattr(registry, "_is_phase_0_container")
                and registry._is_phase_0_container
            ):
                registry._nodebase_ref = nodebase_ref

                # Add get_node_version method directly to the container
                def get_node_version():
                    """
                    Get the node version from ModelNodeBase.

                    This eliminates the need for tools to call get_tool_version()
                    and reload the contract.

                    Returns:
                        ModelSemVer: Version from the loaded contract
                    """
                    return nodebase_ref.node_version

                # Monkey patch the method onto the container
                registry._container.get_node_version = get_node_version

                emit_log_event(
                    LogLevel.DEBUG,
                    "Updated container lifecycle with ModelNodeBase reference",
                    {
                        "node_name": getattr(nodebase_ref, "node_name", "unknown"),
                        "registry_type": type(registry).__name__,
                    },
                )

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to update container lifecycle: {e!s}",
                {"error": str(e)},
            )
            # Non-critical operation, don't raise exception
