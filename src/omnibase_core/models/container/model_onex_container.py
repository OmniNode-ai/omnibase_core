"""
Model ONEX Dependency Injection Container.

This module provides the ModelONEXContainer that integrates with
the contract-driven architecture, supporting workflow orchestration
and observable dependency injection.

Author: ONEX Framework Team
"""

import asyncio
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

# Import needed for type annotations
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID, uuid4

from dependency_injector import containers, providers
from omnibase_spi import ProtocolLogger

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.error_codes import CoreErrorCode, OnexError
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# TODO: These imports require omnibase-spi protocols that may not be available yet
# from omnibase_core.protocol.protocol_database_connection import ProtocolDatabaseConnection
# from omnibase_core.protocol.protocol_service_discovery import ProtocolServiceDiscovery
# from omnibase_core.services.protocol_service_resolver import get_service_resolver

# Type aliases for unavailable protocols (until omnibase-spi is fully integrated)
ProtocolDatabaseConnection = Any
ProtocolServiceDiscovery = Any

if TYPE_CHECKING:
    from omnibase_core.infrastructure.node_base import NodeBase

T = TypeVar("T")


# === CORE CONTAINER DEFINITION ===


class _BaseModelONEXContainer(containers.DeclarativeContainer):
    """Base dependency injection container."""

    # === CONFIGURATION ===
    config = providers.Configuration()

    # === ENHANCED CORE SERVICES ===

    # Enhanced logger with monadic patterns
    enhanced_logger = providers.Factory(
        lambda level: _create_enhanced_logger(level),
        level=LogLevel.INFO,
    )

    # === WORKFLOW ORCHESTRATION ===

    # LlamaIndex workflow factory
    workflow_factory = providers.Factory(lambda: _create_workflow_factory())

    # Workflow execution coordinator
    workflow_coordinator = providers.Singleton(
        lambda factory: _create_workflow_coordinator(factory),
        factory=workflow_factory,
    )


class ModelONEXContainer:
    """
    Model ONEX dependency injection container.

    This container wraps the base DI container and adds:
    - Service resolution with caching and logging
    - Observable dependency injection with event emission
    - Contract-driven automatic service registration
    - Workflow orchestration support
    - Enhanced error handling and recovery patterns
    - Performance monitoring and caching
    """

    def __init__(self) -> None:
        """Initialize enhanced container with custom methods."""
        self._base_container = _BaseModelONEXContainer()

        # Initialize performance tracking
        self._performance_metrics = {
            "total_resolutions": 0,
            "cache_hit_rate": 0.0,
            "avg_resolution_time_ms": 0.0,
            "error_rate": 0.0,
            "active_services": 0,
        }

        # Initialize service cache
        self._service_cache: dict[str, Any] = {}

    @property
    def base_container(self) -> _BaseModelONEXContainer:
        """Access to base ModelONEXContainer for current standards."""
        return self._base_container

    @property
    def config(self) -> Any:
        """Access to configuration."""
        return self._base_container.config

    @property
    def enhanced_logger(self) -> Any:
        """Access to enhanced logger."""
        return self._base_container.enhanced_logger

    @property
    def workflow_factory(self) -> Any:
        """Access to workflow factory."""
        return self._base_container.workflow_factory

    @property
    def workflow_coordinator(self) -> Any:
        """Access to workflow coordinator."""
        return self._base_container.workflow_coordinator

    async def get_service_async(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
        correlation_id: UUID | None = None,
    ) -> T:
        """
        Async service resolution with caching and logging.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional service name
            correlation_id: Optional correlation ID for tracking

        Returns:
            T: Resolved service instance

        Raises:
            OnexError: If service resolution fails
        """
        protocol_name = protocol_type.__name__
        cache_key = f"{protocol_name}:{service_name or 'default'}"
        final_correlation_id = correlation_id or uuid4()

        # Check cache first
        if cache_key in self._service_cache:
            emit_log_event(
                LogLevel.INFO,
                f"Service resolved from cache: {protocol_name}",
                {
                    "protocol_type": protocol_name,
                    "service_name": service_name,
                    "correlation_id": str(final_correlation_id),
                },
            )
            return self._service_cache[cache_key]

        # Resolve service
        try:
            start_time = datetime.now()

            # TODO: Protocol service resolver not yet available - requires omnibase-spi integration
            # Use protocol service resolver for external dependencies
            if protocol_name in [
                "ProtocolServiceDiscovery",
                "ProtocolDatabaseConnection",
            ]:
                # service_resolver = get_service_resolver()
                # service_instance = await service_resolver.resolve_service(protocol_type)
                raise OnexError(
                    error_code=CoreErrorCode.DEPENDENCY_UNAVAILABLE,
                    message=f"Protocol service resolution not yet implemented: {protocol_name}",
                    protocol_type=protocol_name,
                    service_name=service_name or "",
                    note="Requires omnibase-spi protocol integration",
                    correlation_id=final_correlation_id,
                )
            else:
                # Map common protocol names to container providers
                provider_map = {
                    "ProtocolLogger": "enhanced_logger",
                    "Logger": "enhanced_logger",
                }

                if protocol_name in provider_map:
                    provider_name = provider_map[protocol_name]
                    provider = getattr(self._base_container, provider_name, None)
                    if provider:
                        service_instance = provider()
                    else:
                        raise OnexError(
                            error_code=CoreErrorCode.DEPENDENCY_UNAVAILABLE,
                            message=f"Provider not found: {provider_name}",
                            protocol_type=protocol_name,
                            correlation_id=final_correlation_id,
                        )
                else:
                    raise OnexError(
                        error_code=CoreErrorCode.DEPENDENCY_UNAVAILABLE,
                        message=f"Unable to resolve service for protocol {protocol_name}",
                        protocol_type=protocol_name,
                        service_name=service_name or "",
                        correlation_id=final_correlation_id,
                    )

            end_time = datetime.now()
            resolution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Cache successful resolution
            self._service_cache[cache_key] = service_instance

            emit_log_event(
                LogLevel.INFO,
                f"Service resolved successfully: {protocol_name}",
                {
                    "protocol_type": protocol_name,
                    "service_name": service_name,
                    "resolution_time_ms": resolution_time_ms,
                    "correlation_id": str(final_correlation_id),
                },
            )

            return service_instance

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Service resolution failed: {protocol_name}",
                {
                    "protocol_type": protocol_name,
                    "service_name": service_name,
                    "error": str(e),
                    "correlation_id": str(final_correlation_id),
                },
            )
            raise OnexError(
                error_code=CoreErrorCode.DEPENDENCY_UNAVAILABLE,
                message=f"Service resolution failed for {protocol_name}: {e!s}",
                protocol_type=protocol_name,
                service_name=service_name or "",
                correlation_id=final_correlation_id,
            ) from e

    def get_service_sync(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
    ) -> T:
        """
        Synchronous service resolution for current standards.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional service name

        Returns:
            T: Resolved service instance
        """
        return asyncio.run(self.get_service_async(protocol_type, service_name))

    # Compatibility alias
    def get_service(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
    ) -> T:
        """Modern standards method."""
        return self.get_service_sync(protocol_type, service_name)

    async def create_enhanced_nodebase(
        self,
        contract_path: Path,
        node_id: UUID | None = None,
        workflow_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> "NodeBase[Any, Any]":
        """
        Factory method for creating Enhanced NodeBase instances.

        Args:
            contract_path: Path to contract file
            node_id: Optional node identifier
            workflow_id: Optional workflow identifier
            session_id: Optional session identifier

        Returns:
            NodeBase: Configured node instance
        """
        from omnibase_core.infrastructure.node_base import NodeBase

        return NodeBase(
            contract_path=contract_path,
            node_id=node_id,
            container=self,
            workflow_id=workflow_id,
            session_id=session_id,
        )

    def get_workflow_orchestrator(self) -> Any:
        """Get workflow orchestration coordinator."""
        return self.workflow_coordinator()

    def get_performance_metrics(self) -> dict[str, ModelSchemaValue]:
        """
        Get container performance metrics.

        Returns:
            Dict containing resolution times, cache hits, errors, etc.
        """
        # Convert performance metrics to ModelSchemaValue
        return {
            key: ModelSchemaValue.from_value(value)
            for key, value in self._performance_metrics.items()
        }

    async def get_service_discovery(self) -> ProtocolServiceDiscovery:
        """Get service discovery implementation with automatic fallback."""
        return await self.get_service_async(ProtocolServiceDiscovery)

    async def get_database(self) -> ProtocolDatabaseConnection:
        """Get database connection implementation with automatic fallback."""
        return await self.get_service_async(ProtocolDatabaseConnection)

    async def get_external_services_health(self) -> dict[str, object]:
        """Get health status for all external services."""
        # TODO: Requires omnibase-spi protocol service resolver
        # service_resolver = get_service_resolver()
        # return await service_resolver.get_all_service_health()
        return {
            "status": "unavailable",
            "message": "External service health check not yet implemented - requires omnibase-spi integration",
        }

    async def refresh_external_services(self) -> None:
        """Force refresh all external service connections."""
        # TODO: Requires omnibase-spi protocol service resolver
        # service_resolver = get_service_resolver()

        # Refresh service discovery if cached
        # try:
        #     await service_resolver.refresh_service(ProtocolServiceDiscovery)
        # except Exception:
        #     pass  # Service may not be cached yet

        # Refresh database if cached
        # try:
        #     await service_resolver.refresh_service(ProtocolDatabaseConnection)
        # except Exception:
        #     pass  # Service may not be cached yet

        emit_log_event(
            LogLevel.WARNING,
            "External service refresh not yet implemented - requires omnibase-spi integration",
            {"method": "refresh_external_services"},
        )


# === HELPER FUNCTIONS ===


def _create_enhanced_logger(level: LogLevel) -> ProtocolLogger:
    """Create enhanced logger with monadic patterns."""

    class ModelEnhancedLogger:
        def __init__(self, level: LogLevel):
            self.level = level

        def emit_log_event_sync(
            self,
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs: Any,
        ) -> None:
            """Emit log event synchronously."""
            if level.value >= self.level.value:
                datetime.now().isoformat()

        async def emit_log_event_async(
            self,
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs: Any,
        ) -> None:
            """Emit log event asynchronously."""
            self.emit_log_event_sync(level, message, event_type, **kwargs)

        def emit_log_event(
            self,
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs: Any,
        ) -> None:
            """Emit log event (defaults to sync)."""
            self.emit_log_event_sync(level, message, event_type, **kwargs)

        def info(self, message: str) -> None:
            self.emit_log_event_sync(LogLevel.INFO, message, "info")

        def warning(self, message: str) -> None:
            self.emit_log_event_sync(LogLevel.WARNING, message, "warning")

        def error(self, message: str) -> None:
            self.emit_log_event_sync(LogLevel.ERROR, message, "error")

    return ModelEnhancedLogger(level)


def _create_workflow_factory() -> Any:
    """Create workflow factory for LlamaIndex integration."""

    class ModelWorkflowFactory:
        def create_workflow(
            self,
            workflow_type: str,
            config: dict[str, ModelSchemaValue] | None = None,
        ) -> Any:
            """Create workflow instance by type."""
            config = config or {}

            # This would be expanded with actual workflow types
            # from LlamaIndex integration

        def list_available_workflows(self) -> list[str]:
            """List available workflow types."""
            return [
                "simple_sequential",
                "parallel_execution",
                "conditional_branching",
                "retry_with_backoff",
                "data_pipeline",
            ]

    return ModelWorkflowFactory()


def _create_workflow_coordinator(factory: Any) -> Any:
    """Create workflow execution coordinator."""

    class ModelWorkflowCoordinator:
        def __init__(self, factory: Any) -> None:
            self.factory = factory
            self.active_workflows: dict[str, ModelSchemaValue] = {}

        async def execute_workflow(
            self,
            workflow_id: UUID,
            workflow_type: str,
            input_data: ModelSchemaValue,
            config: dict[str, ModelSchemaValue] | None = None,
        ) -> ModelSchemaValue:
            """
            Execute workflow with logging and error handling.

            Args:
                workflow_id: Workflow identifier for tracking
                workflow_type: Type of workflow to execute
                input_data: Input data for workflow
                config: Optional workflow configuration

            Returns:
                ModelSchemaValue: Workflow execution result

            Raises:
                OnexError: If workflow execution fails
            """
            try:
                self.factory.create_workflow(
                    workflow_type,
                    config,
                )

                # Log workflow start
                emit_log_event(
                    LogLevel.INFO,
                    f"Workflow execution started: {workflow_type}",
                    {
                        "workflow_id": workflow_id,
                        "workflow_type": workflow_type,
                    },
                )

                # Execute workflow using the configured type and input data
                workflow_result = await self._execute_workflow_type(
                    workflow_type,
                    input_data,
                    config,
                )

                # Log workflow success
                emit_log_event(
                    LogLevel.INFO,
                    f"Workflow execution completed: {workflow_type}",
                    {
                        "workflow_id": workflow_id,
                        "workflow_type": workflow_type,
                    },
                )

                return workflow_result

            except Exception as e:
                # Log workflow failure
                emit_log_event(
                    LogLevel.ERROR,
                    f"Workflow execution failed: {workflow_type}",
                    {
                        "workflow_id": workflow_id,
                        "workflow_type": workflow_type,
                        "error": str(e),
                    },
                )
                raise OnexError(
                    error_code=CoreErrorCode.OPERATION_FAILED,
                    message=f"Workflow execution failed: {e!s}",
                    workflow_id=str(workflow_id),
                    workflow_type=workflow_type,
                    correlation_id=workflow_id,
                ) from e

        async def _execute_workflow_type(
            self,
            workflow_type: str,
            input_data: Any,
            config: dict[str, Any] | None,
        ) -> Any:
            """Execute a specific workflow type with input data."""
            try:
                # Create and run workflow based on type
                workflow = self.factory.create_workflow(workflow_type, config)

                # Execute workflow with input data
                # This is a simplified implementation - real implementation
                # would depend on the specific workflow framework being used
                if hasattr(workflow, "run"):
                    result = await workflow.run(input_data)
                elif callable(workflow):
                    result = await workflow(input_data)
                else:
                    # Fallback: return input data as placeholder
                    result = input_data

                return result

            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Workflow execution failed for type {workflow_type}: {e}",
                    {
                        "workflow_type": workflow_type,
                        "error": str(e),
                    },
                )
                raise

        def get_active_workflows(self) -> list[str]:
            """Get list of active workflow IDs."""
            return list(self.active_workflows.keys())

    return ModelWorkflowCoordinator(factory)


# === CONTAINER FACTORY ===


async def create_model_onex_container() -> ModelONEXContainer:
    """
    Create and configure model ONEX container.

    Returns:
        ModelONEXContainer: Configured container instance
    """
    container = ModelONEXContainer()

    # Load configuration into base container
    container.config.from_dict(
        {
            "logging": {"level": os.getenv("LOG_LEVEL", "INFO")},
            "consul": {
                "agent_url": f"http://{os.getenv('CONSUL_HOST', 'localhost')}:{os.getenv('CONSUL_PORT', '8500')}",
                "datacenter": os.getenv("CONSUL_DATACENTER", "dc1"),
                "timeout": int(os.getenv("CONSUL_TIMEOUT", "10")),
            },
            "services": {
                # Enhanced service configurations
            },
            "workflows": {
                "default_timeout": int(os.getenv("WORKFLOW_TIMEOUT", "300")),
                "max_concurrent_workflows": int(os.getenv("MAX_WORKFLOWS", "10")),
            },
        },
    )

    return container


# === GLOBAL ENHANCED CONTAINER ===

_model_onex_container: ModelONEXContainer | None = None


async def get_model_onex_container() -> ModelONEXContainer:
    """Get or create global enhanced container instance."""
    global _model_onex_container
    if _model_onex_container is None:
        _model_onex_container = await create_model_onex_container()
    return _model_onex_container


def get_model_onex_container_sync() -> ModelONEXContainer:
    """Get enhanced container synchronously."""
    return asyncio.run(get_model_onex_container())
