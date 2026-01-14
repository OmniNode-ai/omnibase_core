"""Service Registry - Implementation of ProtocolServiceRegistry."""

import asyncio
import time
from datetime import UTC, datetime
from typing import TypeVar, cast
from uuid import UUID, uuid4

from omnibase_core.enums import (
    EnumCoreErrorCode,
    EnumHealthStatus,
    EnumInjectionScope,
    EnumLogLevel,
    EnumOperationStatus,
    EnumServiceLifecycle,
)
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.container.model_injection_context import ModelInjectionContext
from omnibase_core.models.container.model_registry_config import (
    ModelServiceRegistryConfig,
)
from omnibase_core.models.container.model_registry_status import (
    ModelServiceRegistryStatus,
)
from omnibase_core.models.container.model_service_dependency_graph import (
    ModelServiceDependencyGraph,
)
from omnibase_core.models.container.model_service_health_validation_result import (
    ModelServiceHealthValidationResult,
)
from omnibase_core.models.container.model_service_instance import ModelServiceInstance
from omnibase_core.models.container.model_service_metadata import ModelServiceMetadata
from omnibase_core.models.container.model_service_registration import (
    ModelServiceRegistration,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols import (
    ProtocolServiceFactory,
    ProtocolServiceValidator,
)
from omnibase_core.types.type_serializable_value import SerializedDict
from omnibase_core.types.typed_dict_resolution_context import TypedDictResolutionContext

T = TypeVar("T")
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")


class ServiceRegistry:
    """
    Service Registry with Dependency Injection.

    Implements ProtocolServiceRegistry from omnibase_spi for omnibase_core.
    Provides comprehensive service management including registration, resolution,
    lifecycle management, and health monitoring.

    Features:
        - Service registration by interface, instance, or factory
        - Lifecycle management (singleton, transient, scoped)
        - Service resolution with caching
        - Health monitoring and status reporting
        - Performance metrics tracking

    Example:
        ```python
        from omnibase_core.enums import EnumInjectionScope

        # Create registry
        config = create_default_registry_config()
        registry = ServiceRegistry(config)

        # Register singleton service
        reg_id = await registry.register_instance(
            interface=ProtocolLogger,
            instance=logger,
            scope=EnumInjectionScope.GLOBAL,
        )

        # Resolve service
        logger = await registry.resolve_service(ProtocolLogger)

        # Check status
        status = await registry.get_registry_status()
        print(f"Active services: {status.total_registrations}")
        ```

    Attributes:
        config: Registry configuration
        validator: Optional service validator (None in v1.0)
        factory: Optional service factory (None in v1.0)
    """

    def __init__(self, config: ModelServiceRegistryConfig) -> None:
        """
        Initialize service registry.

        Args:
            config: Registry configuration
        """
        self._config = config
        self._registry_id = uuid4()  # Generate unique registry ID
        self._registrations: dict[UUID, ModelServiceRegistration] = {}
        self._instances: dict[UUID, list[ModelServiceInstance]] = {}
        self._interface_map: dict[str, list[UUID]] = {}
        self._name_map: dict[str, UUID] = {}
        self._performance_metrics: dict[str, float] = {}
        self._failed_registrations: int = 0

        emit_log_event(
            EnumLogLevel.INFO,
            f"ServiceRegistry initialized: {config.registry_name}",
            {"config": config.model_dump()},
        )

    @property
    def config(self) -> ModelServiceRegistryConfig:
        """Get registry configuration."""
        return self._config

    @property
    def validator(self) -> ProtocolServiceValidator | None:
        """Get service validator (not implemented in v1.0)."""
        return None

    @property
    def factory(self) -> ProtocolServiceFactory | None:
        """Get service factory (not implemented in v1.0)."""
        return None

    async def register_service(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation],
        lifecycle: EnumServiceLifecycle,
        scope: EnumInjectionScope,
        configuration: SerializedDict | None = None,
    ) -> UUID:
        """
        Register service by interface and implementation class.

        Args:
            interface: Interface protocol type
            implementation: Implementation class
            lifecycle: Lifecycle pattern (singleton, transient, etc.)
            scope: Injection scope (global, request, etc.)
            configuration: Optional configuration dict

        Returns:
            Registration ID

        Raises:
            ModelOnexError: If registration fails
        """
        try:
            registration_id = uuid4()
            interface_name = (
                interface.__name__ if hasattr(interface, "__name__") else str(interface)
            )
            impl_name = (
                implementation.__name__
                if hasattr(implementation, "__name__")
                else str(implementation)
            )

            # Create metadata
            from omnibase_core.models.primitives.model_semver import ModelSemVer

            metadata = ModelServiceMetadata(
                service_id=registration_id,
                service_name=impl_name,
                service_interface=interface_name,
                service_implementation=impl_name,
                version=ModelSemVer(major=1, minor=0, patch=0),
                tags=["core"],
                configuration=configuration or {},
            )

            # Create registration
            registration = ModelServiceRegistration(
                registration_id=registration_id,
                service_metadata=metadata,
                lifecycle=lifecycle,
                scope=scope,
            )

            # Store registration
            self._registrations[registration_id] = registration

            # Update interface mapping
            if interface_name not in self._interface_map:
                self._interface_map[interface_name] = []
            self._interface_map[interface_name].append(registration_id)

            # Update name mapping
            self._name_map[impl_name] = registration_id

            # For lazy loading, don't create instance yet
            if (
                not self._config.lazy_loading_enabled
                and lifecycle == EnumServiceLifecycle.SINGLETON
            ):
                # Create singleton instance immediately
                instance = implementation()
                await self._store_instance(registration_id, instance, lifecycle, scope)

            emit_log_event(
                EnumLogLevel.INFO,
                f"Service registered: {interface_name} -> {impl_name}",
                {
                    "registration_id": registration_id,
                    "lifecycle": lifecycle,
                    "scope": scope,
                },
            )

            return registration_id

        except (GeneratorExit, KeyboardInterrupt, SystemExit):
            # Never catch cancellation/exit signals
            raise
        except asyncio.CancelledError:
            # Never suppress async cancellation
            raise
        except ModelOnexError:
            # Re-raise ONEX errors as-is
            raise
        except Exception as e:
            # boundary-ok: wrap registration failures in structured ONEX error
            self._failed_registrations += 1
            msg = (
                f"Failed to register service '{interface.__name__ if hasattr(interface, '__name__') else str(interface)}'. "
                f"Error: {e}. "
                f"Check that the interface type is valid and metadata is properly formatted."
            )
            emit_log_event(EnumLogLevel.ERROR, msg, {"error": str(e)})
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
            ) from e

    async def register_instance(
        self,
        interface: type[TInterface],
        instance: TInterface,
        scope: EnumInjectionScope = EnumInjectionScope.GLOBAL,
        metadata: SerializedDict | None = None,
    ) -> UUID:
        """
        Register existing service instance.

        Args:
            interface: Interface protocol type
            instance: Existing service instance
            scope: Injection scope
            metadata: Optional metadata dict

        Returns:
            Registration ID

        Raises:
            ModelOnexError: If registration fails
        """
        try:
            registration_id = uuid4()
            interface_name = (
                interface.__name__ if hasattr(interface, "__name__") else str(interface)
            )
            instance_type = type(instance).__name__

            # Create metadata
            from omnibase_core.models.primitives.model_semver import ModelSemVer

            service_metadata = ModelServiceMetadata(
                service_id=registration_id,
                service_name=instance_type,
                service_interface=interface_name,
                service_implementation=instance_type,
                version=ModelSemVer(major=1, minor=0, patch=0),
                tags=["instance"],
                configuration=metadata or {},
            )

            # Create registration (instances are always singleton)
            registration = ModelServiceRegistration(
                registration_id=registration_id,
                service_metadata=service_metadata,
                lifecycle=EnumServiceLifecycle.SINGLETON,
                scope=scope,
            )

            # Store registration
            self._registrations[registration_id] = registration

            # Update interface mapping
            if interface_name not in self._interface_map:
                self._interface_map[interface_name] = []
            self._interface_map[interface_name].append(registration_id)

            # Update name mapping
            self._name_map[instance_type] = registration_id

            # Store instance
            await self._store_instance(
                registration_id, instance, EnumServiceLifecycle.SINGLETON, scope
            )

            emit_log_event(
                EnumLogLevel.INFO,
                f"Service instance registered: {interface_name}",
                {"registration_id": registration_id},
            )

            return registration_id

        except (GeneratorExit, KeyboardInterrupt, SystemExit):
            # Never catch cancellation/exit signals
            raise
        except asyncio.CancelledError:
            # Never suppress async cancellation
            raise
        except ModelOnexError:
            # Re-raise ONEX errors as-is
            raise
        except Exception as e:
            # boundary-ok: wrap instance registration failures in structured ONEX error
            self._failed_registrations += 1
            interface_name = (
                interface.__name__ if hasattr(interface, "__name__") else str(interface)
            )
            instance_type = type(instance).__name__
            msg = (
                f"Failed to register instance of type '{instance_type}' for interface '{interface_name}'. "
                f"Error: {e}. "
                f"Verify that the instance implements the interface protocol correctly."
            )
            emit_log_event(
                EnumLogLevel.ERROR,
                msg,
                {
                    "error": str(e),
                    "interface": interface_name,
                    "instance_type": instance_type,
                },
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
            ) from e

    async def register_factory(
        self,
        interface: type[TInterface],
        factory: ProtocolServiceFactory,
        lifecycle: EnumServiceLifecycle = EnumServiceLifecycle.TRANSIENT,
        scope: EnumInjectionScope = EnumInjectionScope.GLOBAL,
    ) -> UUID:
        """
        Register service factory (not fully implemented in v1.0).

        Args:
            interface: Interface protocol type
            factory: Service factory implementing ProtocolServiceFactory
            lifecycle: Lifecycle pattern
            scope: Injection scope

        Returns:
            Registration ID

        Raises:
            ModelOnexError: Not implemented in v1.0
        """
        msg = "Factory registration not yet implemented (planned for v2.0)"
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED,
        )

    async def unregister_service(self, registration_id: UUID) -> bool:
        """
        Unregister service by registration ID.

        Args:
            registration_id: Registration ID to remove

        Returns:
            True if service was unregistered
        """
        if registration_id not in self._registrations:
            return False

        registration = self._registrations[registration_id]

        # Dispose all instances
        if registration_id in self._instances:
            for instance in self._instances[registration_id]:
                instance.dispose()
            del self._instances[registration_id]

        # Remove from interface map
        interface_name = registration.service_metadata.service_interface
        if interface_name in self._interface_map:
            self._interface_map[interface_name].remove(registration_id)
            if not self._interface_map[interface_name]:
                del self._interface_map[interface_name]

        # Remove from name map
        service_name = registration.service_metadata.service_name
        if service_name in self._name_map:
            del self._name_map[service_name]

        # Remove registration
        del self._registrations[registration_id]

        emit_log_event(
            EnumLogLevel.INFO,
            f"Service unregistered: {registration_id}",
        )

        return True

    async def resolve_service(
        self,
        interface: type[TInterface],
        scope: EnumInjectionScope | None = None,
        context: TypedDictResolutionContext | None = None,
    ) -> TInterface:
        """
        Resolve service instance by interface.

        Args:
            interface: Interface protocol type to resolve
            scope: Optional injection scope override
            context: Optional resolution context

        Returns:
            Service instance

        Raises:
            ModelOnexError: If service cannot be resolved
        """
        start_time = time.perf_counter()

        try:
            interface_name = (
                interface.__name__ if hasattr(interface, "__name__") else str(interface)
            )

            # Find registrations for interface
            if interface_name not in self._interface_map:
                available_interfaces = sorted(self._interface_map.keys())
                msg = (
                    f"No service registered for interface '{interface_name}'. "
                    f"Available interfaces: {', '.join(available_interfaces) if available_interfaces else 'none'}. "
                    f"Register a service using register_service() or register_instance() before attempting resolution."
                )
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
                )

            registration_ids = self._interface_map[interface_name]
            if not registration_ids:
                msg = (
                    f"No active registrations for interface '{interface_name}'. "
                    f"The interface was previously registered but all registrations have been removed. "
                    f"Re-register a service implementation for this interface."
                )
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
                )

            # Get first registration (for now, no priority/ordering logic)
            registration_id = registration_ids[0]
            registration = self._registrations[registration_id]

            # Update access tracking
            registration.mark_accessed()

            # Resolve based on lifecycle
            instance_result = await self._resolve_by_lifecycle(
                registration_id, registration, scope or registration.scope, context
            )
            instance = cast(TInterface, instance_result)

            # Track performance
            end_time = time.perf_counter()
            resolution_time_ms = (end_time - start_time) * 1000
            self._performance_metrics[f"resolve_{interface_name}"] = resolution_time_ms

            emit_log_event(
                EnumLogLevel.DEBUG,
                f"Service resolved: {interface_name}",
                {
                    "registration_id": registration_id,
                    "resolution_time_ms": resolution_time_ms,
                },
            )

            return instance

        except (GeneratorExit, KeyboardInterrupt, SystemExit):
            # Never catch cancellation/exit signals
            raise
        except asyncio.CancelledError:
            # Never suppress async cancellation
            raise
        except ModelOnexError:
            raise
        except Exception as e:
            # boundary-ok: wrap service resolution failures in structured ONEX error
            interface_name = (
                interface.__name__ if hasattr(interface, "__name__") else str(interface)
            )
            msg = (
                f"Service resolution failed for interface '{interface_name}'. "
                f"Error: {e}. "
                f"Check that the service is properly registered and the interface type matches the registration."
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
            ) from e

    async def resolve_named_service(
        self,
        interface: type[TInterface],
        name: str,
        scope: EnumInjectionScope | None = None,
    ) -> TInterface:
        """
        Resolve service by name.

        Args:
            interface: Interface protocol type
            name: Service name
            scope: Optional scope override

        Returns:
            Service instance

        Raises:
            ModelOnexError: If service cannot be resolved
        """
        # Look up by name in name_map
        if name not in self._name_map:
            available_names = sorted(self._name_map.keys())
            msg = (
                f"No service registered with name '{name}'. "
                f"Available service names: {', '.join(available_names) if available_names else 'none'}. "
                f"Use the exact service name from the registration."
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
            )

        registration_id = self._name_map[name]
        registration = self._registrations[registration_id]

        result = await self._resolve_by_lifecycle(
            registration_id, registration, scope or registration.scope, None
        )
        return cast(TInterface, result)

    async def resolve_all_services(
        self,
        interface: type[TInterface],
        scope: EnumInjectionScope | None = None,
    ) -> list[TInterface]:
        """
        Resolve all services implementing interface.

        Args:
            interface: Interface protocol type
            scope: Optional scope override

        Returns:
            List of service instances
        """
        interface_name = (
            interface.__name__ if hasattr(interface, "__name__") else str(interface)
        )

        if interface_name not in self._interface_map:
            return []

        registration_ids = self._interface_map[interface_name]
        instances: list[TInterface] = []

        for registration_id in registration_ids:
            registration = self._registrations[registration_id]
            instance = await self._resolve_by_lifecycle(
                registration_id, registration, scope or registration.scope, None
            )
            instances.append(cast(TInterface, instance))

        return instances

    async def try_resolve_service(
        self,
        interface: type[TInterface],
        scope: EnumInjectionScope | None = None,
    ) -> TInterface | None:
        """
        Try to resolve service without raising exception.

        Args:
            interface: Interface protocol type
            scope: Optional scope override

        Returns:
            Service instance or None if not found
        """
        try:
            return await self.resolve_service(interface, scope)
        except ModelOnexError:
            return None

    async def get_registration(
        self, registration_id: UUID
    ) -> ModelServiceRegistration | None:
        """
        Get registration by ID.

        Args:
            registration_id: Registration ID

        Returns:
            Service registration or None if not found
        """
        return self._registrations.get(registration_id)

    async def get_registrations_by_interface(
        self, interface: type[T]
    ) -> list[ModelServiceRegistration]:
        """
        Get all registrations for interface.

        Args:
            interface: Interface protocol type

        Returns:
            List of service registrations
        """
        interface_name = (
            interface.__name__ if hasattr(interface, "__name__") else str(interface)
        )

        if interface_name not in self._interface_map:
            return []

        registration_ids = self._interface_map[interface_name]
        return [
            self._registrations[reg_id]
            for reg_id in registration_ids
            if reg_id in self._registrations
        ]

    async def get_all_registrations(self) -> list[ModelServiceRegistration]:
        """
        Get all service registrations.

        Returns:
            List of all registrations
        """
        return list(self._registrations.values())

    async def get_active_instances(
        self, registration_id: UUID | None = None
    ) -> list[ModelServiceInstance]:
        """
        Get active service instances.

        Args:
            registration_id: Optional registration ID to filter by

        Returns:
            List of active service instances
        """
        if registration_id:
            return self._instances.get(registration_id, [])

        # Return all instances
        all_instances: list[ModelServiceInstance] = []
        for instances in self._instances.values():
            all_instances.extend(instances)
        return all_instances

    async def dispose_instances(
        self, registration_id: UUID, scope: EnumInjectionScope | None = None
    ) -> int:
        """
        Dispose service instances.

        Args:
            registration_id: Registration ID
            scope: Optional scope to filter by

        Returns:
            Number of instances disposed
        """
        if registration_id not in self._instances:
            return 0

        instances = self._instances[registration_id]
        disposed_count = 0

        for instance in instances:
            if scope is None or instance.scope == scope:
                instance.dispose()
                disposed_count += 1

        # Remove disposed instances
        self._instances[registration_id] = [
            inst for inst in instances if not inst.is_disposed
        ]

        return disposed_count

    async def validate_registration(
        self, registration: ModelServiceRegistration
    ) -> bool:
        """
        Validate service registration.

        Args:
            registration: Service registration to validate

        Returns:
            True if registration is valid
        """
        return await registration.validate_registration()

    async def detect_circular_dependencies(
        self, registration: ModelServiceRegistration
    ) -> list[str]:
        """
        Detect circular dependencies (not implemented in v1.0).

        Args:
            registration: Service registration

        Returns:
            List of circular dependency service IDs (empty in v1.0)
        """
        # Not implemented in v1.0 - no dependency tracking yet
        return []

    async def get_dependency_graph(
        self, service_id: UUID
    ) -> ModelServiceDependencyGraph | None:
        """
        Get dependency graph for a service.

        Returns the dependency graph for the specified service, including
        its dependencies, dependents, and resolution order.

        Note: Dependency tracking is not fully implemented in v1.0.
        This method returns a minimal graph with only basic information.

        Args:
            service_id: Service registration ID

        Returns:
            ModelServiceDependencyGraph with dependency information,
            or None if service not found
        """
        # Check if service exists
        if service_id not in self._registrations:
            return None

        # In v1.0, we don't track dependencies, so return a minimal graph
        return ModelServiceDependencyGraph(
            service_id=service_id,
            dependencies=[],
            dependents=[],
            depth_level=0,
            circular_references=[],
            resolution_order=[service_id],
            metadata={"note": "Dependency tracking not implemented in v1.0"},
        )

    async def get_registry_status(self) -> ModelServiceRegistryStatus:
        """
        Get comprehensive registry status.

        Returns:
            Registry status information
        """
        # Calculate distributions
        lifecycle_dist: dict[EnumServiceLifecycle, int] = {}
        scope_dist: dict[EnumInjectionScope, int] = {}
        health_dist: dict[EnumHealthStatus, int] = {}

        for registration in self._registrations.values():
            # Lifecycle distribution
            lifecycle = registration.lifecycle
            lifecycle_dist[lifecycle] = lifecycle_dist.get(lifecycle, 0) + 1

            # Scope distribution
            scope = registration.scope
            scope_dist[scope] = scope_dist.get(scope, 0) + 1

            # Health distribution
            health = registration.health_status
            health_dist[health] = health_dist.get(health, 0) + 1

        # Count active instances
        total_instances = sum(len(instances) for instances in self._instances.values())

        # Calculate average resolution time
        avg_resolution_time = None
        if self._performance_metrics:
            avg_resolution_time = sum(self._performance_metrics.values()) / len(
                self._performance_metrics
            )

        # Determine overall status using helper method that returns both values
        # together to prevent incorrect overwrites from separate assignments
        overall_status, status_message = self._determine_overall_status()

        return ModelServiceRegistryStatus(
            registry_id=self._registry_id,
            status=overall_status,
            message=status_message,
            total_registrations=len(self._registrations),
            active_instances=total_instances,
            failed_registrations=self._failed_registrations,
            circular_dependencies=0,  # Not tracked in v1.0
            lifecycle_distribution=lifecycle_dist,
            scope_distribution=scope_dist,
            health_summary=health_dist,
            average_resolution_time_ms=avg_resolution_time,
            last_updated=datetime.now(UTC),
        )

    async def validate_service_health(
        self, registration_id: UUID
    ) -> ModelServiceHealthValidationResult:
        """
        Validate service health.

        Performs health validation on the specified service registration,
        checking instance availability and basic health metrics.

        Args:
            registration_id: Registration ID to validate

        Returns:
            ModelServiceHealthValidationResult with health information

        Raises:
            ModelOnexError: If registration not found
        """
        start_time = time.perf_counter()

        # Check if registration exists
        if registration_id not in self._registrations:
            return ModelServiceHealthValidationResult.unhealthy(
                registration_id=registration_id,
                error_message=f"Registration not found: {registration_id}",
                diagnostics={"available_registrations": len(self._registrations)},
            )

        registration = self._registrations[registration_id]
        instances = self._instances.get(registration_id, [])
        active_instances = [inst for inst in instances if inst.is_active()]

        end_time = time.perf_counter()
        response_time_ms = (end_time - start_time) * 1000

        # Check for issues
        warnings: list[str] = []

        if (
            not active_instances
            and registration.lifecycle == EnumServiceLifecycle.SINGLETON
        ):
            # Singleton with no instances might indicate a problem
            warnings.append("Singleton service has no active instances")

        # Check last access time
        last_access: datetime | None = None
        if active_instances:
            last_access = max(inst.last_accessed for inst in active_instances)

        # Determine health status
        if registration.health_status == EnumHealthStatus.UNHEALTHY:
            return ModelServiceHealthValidationResult.unhealthy(
                registration_id=registration_id,
                error_message="Service marked as unhealthy",
                diagnostics={
                    "registration_status": registration.registration_status,
                    "lifecycle": registration.lifecycle,
                },
            )

        if warnings:
            return ModelServiceHealthValidationResult.degraded(
                registration_id=registration_id,
                warnings=warnings,
                instance_count=len(active_instances),
            )

        result = ModelServiceHealthValidationResult.healthy(
            registration_id=registration_id,
            instance_count=len(active_instances),
            response_time_ms=response_time_ms,
        )
        result.last_access_time = last_access
        return result

    async def update_service_configuration(
        self, registration_id: UUID, configuration: SerializedDict
    ) -> bool:
        """
        Update service configuration.

        Args:
            registration_id: Registration ID
            configuration: New configuration

        Returns:
            True if configuration was updated
        """
        if registration_id not in self._registrations:
            return False

        registration = self._registrations[registration_id]
        registration.service_metadata.configuration.update(configuration)
        registration.service_metadata.last_modified_at = datetime.now(UTC)

        return True

    async def create_injection_scope(
        self, scope_name: str, parent_scope: UUID | None = None
    ) -> UUID:
        """
        Create injection scope (not implemented in v1.0).

        Args:
            scope_name: Scope name
            parent_scope: Optional parent scope

        Returns:
            Scope ID

        Raises:
            ModelOnexError: Not implemented in v1.0
        """
        msg = "Injection scope creation not yet implemented (planned for v2.0)"
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED,
        )

    async def dispose_injection_scope(self, scope_id: UUID) -> int:
        """
        Dispose injection scope (not implemented in v1.0).

        Args:
            scope_id: Scope ID

        Returns:
            Number of instances disposed

        Raises:
            ModelOnexError: Not implemented in v1.0
        """
        msg = "Injection scope disposal not yet implemented (planned for v2.0)"
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED,
        )

    async def get_injection_context(
        self, context_id: UUID
    ) -> ModelInjectionContext | None:
        """
        Get injection context by ID.

        Returns the injection context for the specified context ID,
        including resolution status and dependency path information.

        Note: Context tracking is not fully implemented in v1.0.
        This method currently returns None as contexts are not persisted.

        Args:
            context_id: Context ID to look up

        Returns:
            ModelInjectionContext if found, None otherwise
        """
        # In v1.0, we don't persist injection contexts
        # Full context tracking is planned for v2.0
        return None

    # Private helper methods

    def _determine_overall_status(self) -> tuple[EnumOperationStatus, str]:
        """
        Determine registry overall status with clear priority rules.

        Returns both status and message as a tuple to ensure they are always
        set together, preventing potential logic issues where one could be
        incorrectly overwritten without updating the other.

        Priority order (highest to lowest):
            1. FAILED - Any failed registrations indicate problems
            2. PENDING - No registrations yet (empty registry)
            3. SUCCESS - Registry is operational with services

        Returns:
            Tuple of (status, message) for the registry status.
        """
        if self._failed_registrations > 0:
            return (
                EnumOperationStatus.FAILED,
                f"Registry has {self._failed_registrations} failed registration(s) "
                f"and {len(self._registrations)} active service(s)",
            )
        if not self._registrations:
            return (
                EnumOperationStatus.PENDING,
                "Registry initialized, no services registered yet",
            )
        return (
            EnumOperationStatus.SUCCESS,
            f"Registry operational with {len(self._registrations)} services",
        )

    async def _store_instance(
        self,
        registration_id: UUID,
        instance: object,
        lifecycle: EnumServiceLifecycle,
        scope: EnumInjectionScope,
    ) -> ModelServiceInstance:
        """Store service instance."""
        instance_id = uuid4()

        service_instance = ModelServiceInstance(
            instance_id=instance_id,
            service_registration_id=registration_id,
            instance=instance,
            lifecycle=lifecycle,
            scope=scope,
        )

        if registration_id not in self._instances:
            self._instances[registration_id] = []

        self._instances[registration_id].append(service_instance)

        # Update registration instance count
        if registration_id in self._registrations:
            self._registrations[registration_id].increment_instance_count()

        return service_instance

    async def _resolve_by_lifecycle(
        self,
        registration_id: UUID,
        registration: ModelServiceRegistration,
        scope: EnumInjectionScope,
        context: TypedDictResolutionContext | None,
    ) -> object:
        """Resolve service based on lifecycle pattern."""
        lifecycle = registration.lifecycle

        if lifecycle == EnumServiceLifecycle.SINGLETON:
            # Return existing instance or create new one
            existing_instances = self._instances.get(registration_id, [])
            if existing_instances:
                # Mark accessed
                existing_instances[0].mark_accessed()
                return existing_instances[0].instance

            # Create new singleton instance
            # In v1.0, we don't have factory support, so this won't work for class-based registrations
            # Only instance-based registrations will work
            msg = (
                f"Singleton instance not found and cannot create (registration_id: {registration_id}). "
                f"In v1.0, only instance-based registrations are supported. "
                f"Use register_instance() instead of register_service() with a factory."
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
            )

        if lifecycle == EnumServiceLifecycle.TRANSIENT:
            # Always create new instance
            # In v1.0, we don't have factory support, so this is not implemented
            msg = (
                "Transient lifecycle not yet supported (requires factory support in v2.0). "
                "Use 'singleton' lifecycle with register_instance() or wait for v2.0 factory support."
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED,
            )

        supported_lifecycles = [
            EnumServiceLifecycle.SINGLETON.value,
            EnumServiceLifecycle.TRANSIENT.value,
        ]
        msg = (
            f"Unsupported lifecycle: '{lifecycle}'. "
            f"Supported lifecycles: {', '.join(supported_lifecycles)}. "
            f"Note: 'transient' requires v2.0 factory support."
        )
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED,
        )
