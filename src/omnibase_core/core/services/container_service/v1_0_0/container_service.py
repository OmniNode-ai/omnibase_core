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
        self._validation_cache_max_size = (
            self._config.interface_validation_cache_size
            if self._config and hasattr(self._config, "interface_validation_cache_size")
            else 100
        )

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

            # Enhanced dependency interface validation if enabled
            interface_validation_results = {}
            if self._config and getattr(
                self._config, "enable_interface_validation", True
            ):
                try:
                    interface_validation_results = self.validate_dependency_interfaces(
                        container, contract_content
                    )

                    valid_count = sum(
                        1
                        for is_valid, _ in interface_validation_results.values()
                        if is_valid
                    )
                    total_count = len(interface_validation_results)

                    emit_log_event(
                        LogLevel.INFO,
                        f"Interface validation completed for {total_count} dependencies",
                        {
                            "node_id": node_id,
                            "validated_dependencies": total_count,
                            "valid_interfaces": valid_count,
                            "validation_success_rate": f"{valid_count}/{total_count}",
                        },
                    )

                    # Check for strict validation mode
                    if (
                        self._config
                        and getattr(self._config, "strict_interface_validation", False)
                        and valid_count < total_count
                    ):

                        failed_deps = [
                            dep_name
                            for dep_name, (
                                is_valid,
                                _,
                            ) in interface_validation_results.items()
                            if not is_valid
                        ]

                        raise OnexError(
                            error_code=CoreErrorCode.VALIDATION_ERROR,
                            message=f"Strict interface validation failed for dependencies: {failed_deps}",
                            context={
                                "node_id": node_id,
                                "failed_dependencies": failed_deps,
                                "valid_dependencies": valid_count,
                                "total_dependencies": total_count,
                                "strict_validation": True,
                            },
                        )

                except OnexError:
                    # Re-raise validation errors in strict mode
                    raise
                except Exception as e:
                    emit_log_event(
                        LogLevel.WARNING,
                        f"Interface validation failed, continuing without interface checks: {e}",
                        {"node_id": node_id, "error": str(e)},
                    )

            # Create result with comprehensive metadata
            container_metadata = {
                "node_id": node_id,
                "creation_method": "from_contract_dependencies",
                "total_dependencies": len(dep_list),
                "successful_registrations": len(registered_services),
                "failed_registrations": len(failed_services),
                "container_type": type(container).__name__,
                "interface_validation_enabled": self._config
                and getattr(self._config, "enable_interface_validation", True),
                "interface_validation_results": len(interface_validation_results),
            }

            if self._config:
                container_metadata.update(
                    {
                        "validation_enabled": self._config.enable_service_validation,
                        "lifecycle_logging_enabled": self._config.enable_lifecycle_logging,
                        "interface_validation_enabled": getattr(
                            self._config, "enable_interface_validation", True
                        ),
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

            # Add interface validation results to result if available
            if interface_validation_results:
                # Store interface validation results in the result metadata
                result.container_metadata["interface_validation_details"] = {
                    dep_name: {"valid": is_valid, "error_count": len(errors)}
                    for dep_name, (
                        is_valid,
                        errors,
                    ) in interface_validation_results.items()
                }

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

    def validate_service_interface_compliance(
        self,
        service: Any,
        expected_protocol: str,
        dependency_name: str,
    ) -> tuple[bool, list[str]]:
        """
        Enhanced interface validation to ensure service complies with expected protocol.

        This method provides runtime protocol compliance checking to validate that
        services implement the expected interface methods and attributes.

        Args:
            service: Service instance to validate
            expected_protocol: Expected protocol interface path (e.g., 'package.protocol.ProtocolName')
            dependency_name: Dependency name for logging context

        Returns:
            tuple[bool, list[str]]: (is_valid, validation_errors)
        """
        validation_errors = []

        try:
            if service is None:
                validation_errors.append(f"Service {dependency_name} is None")
                return False, validation_errors

            # Cache validation results for performance
            cache_key = (
                f"{dependency_name}:{expected_protocol}:{type(service).__name__}"
            )
            if cache_key in self._validation_cache:
                cached_result = self._validation_cache[cache_key]
                return cached_result, (
                    []
                    if cached_result
                    else [f"Cached validation failed for {dependency_name}"]
                )

            # Import and validate protocol interface
            try:
                module_parts = expected_protocol.split(".")
                if len(module_parts) < 2:
                    validation_errors.append(
                        f"Invalid protocol path: {expected_protocol}"
                    )
                    return False, validation_errors

                protocol_name = module_parts[-1]
                module_path = ".".join(module_parts[:-1])

                # Import protocol module
                protocol_module = importlib.import_module(module_path)
                protocol_class = getattr(protocol_module, protocol_name, None)

                if protocol_class is None:
                    validation_errors.append(
                        f"Protocol {protocol_name} not found in {module_path}"
                    )
                    return False, validation_errors

                # Check if protocol is actually a Protocol class
                if not hasattr(protocol_class, "__protocol__"):
                    validation_errors.append(
                        f"{expected_protocol} is not a valid Protocol"
                    )
                    return False, validation_errors

            except ImportError as e:
                validation_errors.append(
                    f"Cannot import protocol {expected_protocol}: {e}"
                )
                return False, validation_errors
            except Exception as e:
                validation_errors.append(
                    f"Protocol validation error for {expected_protocol}: {e}"
                )
                return False, validation_errors

            # Validate service implements protocol methods
            protocol_methods = self._extract_protocol_methods(protocol_class)
            service_methods = self._extract_service_methods(service)

            missing_methods = []
            for method_name, method_signature in protocol_methods.items():
                if method_name not in service_methods:
                    missing_methods.append(f"Missing method: {method_name}")
                else:
                    # Validate method signature compatibility (basic check)
                    service_method = service_methods[method_name]
                    if not self._validate_method_signature(
                        service_method, method_signature
                    ):
                        validation_errors.append(
                            f"Method signature mismatch for {method_name}"
                        )

            if missing_methods:
                validation_errors.extend(missing_methods)

            # Validate service has required attributes (if any)
            protocol_attributes = self._extract_protocol_attributes(protocol_class)
            service_attributes = self._extract_service_attributes(service)

            missing_attributes = []
            for attr_name in protocol_attributes:
                if attr_name not in service_attributes:
                    missing_attributes.append(f"Missing attribute: {attr_name}")

            if missing_attributes:
                validation_errors.extend(missing_attributes)

            # Cache result with size management
            is_valid = len(validation_errors) == 0
            self._manage_validation_cache()
            self._validation_cache[cache_key] = is_valid

            if is_valid:
                emit_log_event(
                    LogLevel.DEBUG,
                    f"Service interface validation passed: {dependency_name}",
                    {
                        "dependency_name": dependency_name,
                        "protocol": expected_protocol,
                        "service_type": type(service).__name__,
                        "methods_validated": len(protocol_methods),
                        "attributes_validated": len(protocol_attributes),
                    },
                )
            else:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Service interface validation failed: {dependency_name}",
                    {
                        "dependency_name": dependency_name,
                        "protocol": expected_protocol,
                        "service_type": type(service).__name__,
                        "validation_errors": validation_errors,
                    },
                )

            return is_valid, validation_errors

        except Exception as e:
            error_msg = f"Interface validation exception for {dependency_name}: {e}"
            validation_errors.append(error_msg)
            emit_log_event(
                LogLevel.ERROR,
                error_msg,
                {
                    "dependency_name": dependency_name,
                    "protocol": expected_protocol,
                    "error": str(e),
                },
            )
            return False, validation_errors

    def _extract_protocol_methods(self, protocol_class: Any) -> dict[str, Any]:
        """Extract method signatures from protocol class."""
        methods = {}
        try:
            # Get protocol annotations/methods
            if hasattr(protocol_class, "__annotations__"):
                for name, annotation in protocol_class.__annotations__.items():
                    if callable(annotation) or str(annotation).startswith(
                        "typing.Callable"
                    ):
                        methods[name] = annotation

            # Also check for methods defined directly on the protocol
            for attr_name in dir(protocol_class):
                if not attr_name.startswith("_"):
                    attr = getattr(protocol_class, attr_name)
                    if callable(attr):
                        methods[attr_name] = attr

        except Exception as e:
            emit_log_event(
                LogLevel.DEBUG,
                f"Error extracting protocol methods: {e}",
                {"protocol": str(protocol_class)},
            )

        return methods

    def _extract_service_methods(self, service: Any) -> dict[str, Any]:
        """Extract callable methods from service instance."""
        methods = {}
        try:
            for attr_name in dir(service):
                if not attr_name.startswith("_"):
                    attr = getattr(service, attr_name)
                    if callable(attr):
                        methods[attr_name] = attr
        except Exception as e:
            emit_log_event(
                LogLevel.DEBUG,
                f"Error extracting service methods: {e}",
                {"service_type": type(service).__name__},
            )

        return methods

    def _extract_protocol_attributes(self, protocol_class: Any) -> set[str]:
        """Extract non-callable attributes from protocol class."""
        attributes = set()
        try:
            if hasattr(protocol_class, "__annotations__"):
                for name, annotation in protocol_class.__annotations__.items():
                    if not callable(annotation) and not str(annotation).startswith(
                        "typing.Callable"
                    ):
                        attributes.add(name)
        except Exception as e:
            emit_log_event(
                LogLevel.DEBUG,
                f"Error extracting protocol attributes: {e}",
                {"protocol": str(protocol_class)},
            )

        return attributes

    def _extract_service_attributes(self, service: Any) -> set[str]:
        """Extract non-callable attributes from service instance."""
        attributes = set()
        try:
            for attr_name in dir(service):
                if not attr_name.startswith("_"):
                    attr = getattr(service, attr_name)
                    if not callable(attr):
                        attributes.add(attr_name)
        except Exception as e:
            emit_log_event(
                LogLevel.DEBUG,
                f"Error extracting service attributes: {e}",
                {"service_type": type(service).__name__},
            )

        return attributes

    def _validate_method_signature(
        self, service_method: Any, protocol_signature: Any
    ) -> bool:
        """
        Basic method signature validation.

        This is a simplified validation - in production, you might want to use
        more sophisticated signature comparison using inspect module.
        """
        try:
            # Basic validation - check if method is callable
            if not callable(service_method):
                return False

            # For more sophisticated validation, you could use:
            # import inspect
            # service_sig = inspect.signature(service_method)
            # protocol_sig = inspect.signature(protocol_signature)
            # return service_sig.parameters == protocol_sig.parameters

            # For now, just ensure it's callable
            return True

        except Exception:
            return False

    def validate_dependency_interfaces(
        self,
        container: Any,
        contract_dependencies: Any,
    ) -> dict[str, tuple[bool, list[str]]]:
        """
        Comprehensive validation of all dependency interfaces in container.

        This method validates that all services registered in the container
        comply with their expected protocol interfaces as specified in the contract.

        Args:
            container: Container instance with registered services
            contract_dependencies: Contract dependencies specification

        Returns:
            dict[str, tuple[bool, list[str]]]: Validation results per dependency
        """
        validation_results = {}

        try:
            if (
                not hasattr(contract_dependencies, "dependencies")
                or not contract_dependencies.dependencies
            ):
                emit_log_event(
                    LogLevel.INFO,
                    "No contract dependencies to validate interfaces",
                    {"container_type": type(container).__name__},
                )
                return validation_results

            # Validate each dependency
            for dependency in contract_dependencies.dependencies:
                dep_name = getattr(dependency, "name", "unknown")

                # Get expected protocol interface
                expected_protocol = getattr(dependency, "interface", None)
                if not expected_protocol:
                    # Try alternative attribute names
                    expected_protocol = getattr(dependency, "protocol", None)

                if not expected_protocol:
                    validation_results[dep_name] = (
                        False,
                        ["No protocol interface specified"],
                    )
                    continue

                # Get service from container
                service_attr = f"_service_{dep_name}"
                if not hasattr(container, service_attr):
                    validation_results[dep_name] = (
                        False,
                        [f"Service not found in container: {service_attr}"],
                    )
                    continue

                service = getattr(container, service_attr)

                # Validate interface compliance
                is_valid, errors = self.validate_service_interface_compliance(
                    service, expected_protocol, dep_name
                )
                validation_results[dep_name] = (is_valid, errors)

            # Log summary
            total_deps = len(validation_results)
            valid_deps = sum(
                1 for is_valid, _ in validation_results.values() if is_valid
            )

            emit_log_event(
                LogLevel.INFO,
                f"Dependency interface validation complete: {valid_deps}/{total_deps} valid",
                {
                    "total_dependencies": total_deps,
                    "valid_dependencies": valid_deps,
                    "failed_dependencies": total_deps - valid_deps,
                    "validation_summary": {
                        dep_name: "valid" if is_valid else "invalid"
                        for dep_name, (is_valid, _) in validation_results.items()
                    },
                },
            )

        except Exception as e:
            error_msg = f"Dependency interface validation failed: {e}"
            emit_log_event(
                LogLevel.ERROR,
                error_msg,
                {"error": str(e)},
            )
            # Return empty results to indicate validation failure
            return {}

        return validation_results

    def _manage_validation_cache(self) -> None:
        """
        Manage validation cache size to prevent unlimited growth.

        Uses LRU-style cache management by removing oldest entries when cache size exceeds limit.
        """
        try:
            if len(self._validation_cache) >= self._validation_cache_max_size:
                # Remove oldest 20% of entries to make room for new ones
                removal_count = max(1, self._validation_cache_max_size // 5)
                keys_to_remove = list(self._validation_cache.keys())[:removal_count]

                for key in keys_to_remove:
                    del self._validation_cache[key]

                emit_log_event(
                    LogLevel.DEBUG,
                    f"Validation cache size managed: removed {removal_count} entries",
                    {
                        "cache_size": len(self._validation_cache),
                        "max_size": self._validation_cache_max_size,
                        "entries_removed": removal_count,
                    },
                )

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Validation cache management failed: {e}",
                {"error": str(e)},
            )

    def clear_validation_cache(self) -> None:
        """Clear all validation cache entries."""
        cache_size = len(self._validation_cache)
        self._validation_cache.clear()
        emit_log_event(
            LogLevel.INFO,
            f"Validation cache cleared: {cache_size} entries removed",
            {"cleared_entries": cache_size},
        )

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
