"""
Enhanced ONEX Dependency Injection Container for Monadic Architecture.

This module provides the next-generation ONEXContainer that integrates with
the contract-driven monadic architecture, supporting NodeResult composition,
workflow orchestration, and observable dependency injection.

Author: ONEX Framework Team
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

# Import needed for type annotations
from typing import TYPE_CHECKING, TypeVar
from uuid import uuid4

from dependency_injector import containers, providers

from omnibase_core.core.common_types import ModelStateValue
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.monadic.model_node_result import (
    ErrorInfo,
    ErrorType,
    Event,
    ExecutionContext,
    LogEntry,
    NodeResult,
)
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.protocol.protocol_logger import ProtocolLogger

if TYPE_CHECKING:
    from omnibase_core.core.node_base import ModelNodeBase

T = TypeVar("T")


class ContainerResolutionResult:
    """
    Result wrapper for container service resolution with monadic patterns.

    Provides observability and error handling for dependency injection
    operations within the ONEX monadic architecture.
    """

    def __init__(
        self,
        service_instance: T,
        resolution_time_ms: int,
        resolution_path: list[str],
        cache_hit: bool = False,
        fallback_used: bool = False,
        warnings: list[str] | None = None,
    ):
        self.service_instance = service_instance
        self.resolution_time_ms = resolution_time_ms
        self.resolution_path = resolution_path
        self.cache_hit = cache_hit
        self.fallback_used = fallback_used
        self.warnings = warnings or []
        self.timestamp = datetime.now()


class MonadicServiceProvider:
    """
    Service provider with monadic composition and observable resolution.

    Wraps service resolution in NodeResult for consistent error handling
    and observability throughout the dependency injection process.
    """

    def __init__(
        self,
        container: "EnhancedONEXContainer",
        correlation_id: str | None = None,
    ):
        self.container = container
        self.correlation_id = correlation_id or str(uuid4())
        self.resolution_cache: dict[str, ContainerResolutionResult] = {}

    async def resolve_async(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
        use_cache: bool = True,
    ) -> NodeResult[T]:
        """
        Resolve service with monadic composition and observable resolution.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional service name for specific resolution
            use_cache: Whether to use resolution cache

        Returns:
            NodeResult[T]: Monadic result with resolved service and context
        """
        start_time = datetime.now()
        protocol_name = protocol_type.__name__
        cache_key = f"{protocol_name}:{service_name or 'default'}"

        # Create execution context
        execution_context = ExecutionContext(
            provenance=[f"container.resolve.{protocol_name}"],
            logs=[],
            trust_score=1.0,
            timestamp=start_time,
            metadata={
                "protocol_type": protocol_name,
                "service_name": service_name,
                "correlation_id": self.correlation_id,
            },
            correlation_id=self.correlation_id,
        )

        try:
            # Check cache first if enabled
            if use_cache and cache_key in self.resolution_cache:
                cached_result = self.resolution_cache[cache_key]

                execution_context.logs.append(
                    LogEntry(
                        "INFO",
                        f"Service resolved from cache: {protocol_name}",
                        datetime.now(),
                    ),
                )

                return NodeResult.success(
                    value=cached_result.service_instance,
                    provenance=[*execution_context.provenance, "cache.hit"],
                    trust_score=0.95,  # Cached services have slightly lower trust
                    metadata={
                        **execution_context.metadata,
                        "resolution_time_ms": 0,  # Cache hit
                        "cache_hit": True,
                        "original_resolution_time": cached_result.resolution_time_ms,
                    },
                    events=[
                        Event(
                            type="container.service.resolved.cached",
                            payload={
                                "protocol_type": protocol_name,
                                "service_name": service_name,
                                "cache_key": cache_key,
                                "original_timestamp": cached_result.timestamp.isoformat(),
                            },
                            timestamp=datetime.now(),
                            correlation_id=self.correlation_id,
                        ),
                    ],
                    correlation_id=self.correlation_id,
                )

            # Resolve service from container
            resolution_result = await self._resolve_from_container(
                protocol_type,
                service_name,
            )

            end_time = datetime.now()
            resolution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Cache successful resolution
            if use_cache:
                self.resolution_cache[cache_key] = ContainerResolutionResult(
                    service_instance=resolution_result,
                    resolution_time_ms=resolution_time_ms,
                    resolution_path=execution_context.provenance,
                    cache_hit=False,
                    fallback_used=False,
                )

            execution_context.logs.append(
                LogEntry(
                    "INFO",
                    f"Service resolved successfully: {protocol_name}",
                    end_time,
                ),
            )
            execution_context.timestamp = end_time
            execution_context.metadata["resolution_time_ms"] = resolution_time_ms

            return NodeResult.success(
                value=resolution_result,
                provenance=execution_context.provenance,
                trust_score=1.0,
                metadata=execution_context.metadata,
                events=[
                    Event(
                        type="container.service.resolved",
                        payload={
                            "protocol_type": protocol_name,
                            "service_name": service_name,
                            "resolution_time_ms": resolution_time_ms,
                            "cache_miss": True,
                        },
                        timestamp=end_time,
                        correlation_id=self.correlation_id,
                    ),
                ],
                correlation_id=self.correlation_id,
            )

        except Exception as e:
            # Handle resolution failure
            error_info = ErrorInfo(
                error_type=ErrorType.DEPENDENCY,
                message=f"Service resolution failed for {protocol_name}: {e!s}",
                code="SERVICE_RESOLUTION_FAILED",
                context={
                    "protocol_type": protocol_name,
                    "service_name": service_name,
                    "correlation_id": self.correlation_id,
                },
                retryable=True,
                backoff_strategy="exponential",
                max_attempts=3,
                correlation_id=self.correlation_id,
            )

            execution_context.logs.append(
                LogEntry(
                    "ERROR",
                    f"Service resolution failed: {e!s}",
                    datetime.now(),
                ),
            )

            return NodeResult.failure(
                error=error_info,
                provenance=[*execution_context.provenance, "resolution.failed"],
                correlation_id=self.correlation_id,
            )

    async def _resolve_from_container(
        self,
        protocol_type: type[T],
        service_name: str | None,
    ) -> T:
        """
        Resolve service from underlying container implementation.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional service name

        Returns:
            T: Resolved service instance
        """
        # Check if container has get_service method (new enhanced container)
        if hasattr(self.container, "get_service_async"):
            return await self.container.get_service_async(protocol_type, service_name)
        if hasattr(self.container, "get_service"):
            # Fallback to synchronous method
            return self.container.get_service(protocol_type, service_name)
        # Try to resolve using protocol name
        protocol_name = protocol_type.__name__

        # Map common protocol names to container providers
        provider_map = {
            "ProtocolLogger": "basic_logger",
            "Logger": "basic_logger",
            "ConsulServiceDiscovery": "consul_client",
            "ServiceDiscovery": "service_discovery",
        }

        if protocol_name in provider_map:
            provider_name = provider_map[protocol_name]
            provider = getattr(self.container, provider_name, None)
            if provider:
                return provider()

        # Fallback error
        raise OnexError(
            error_code=CoreErrorCode.SERVICE_RESOLUTION_FAILED,
            message=f"Unable to resolve service for protocol {protocol_name}",
            context={
                "protocol_type": protocol_name,
                "service_name": service_name,
                "available_providers": dir(self.container),
            },
        )


# === CORE CONTAINER DEFINITION ===


class _BaseONEXContainer(containers.DeclarativeContainer):
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


class EnhancedONEXContainer:
    """
    Enhanced ONEX dependency injection container with monadic architecture.

    This container wraps the base DI container and adds:
    - Monadic service resolution through NodeResult
    - Observable dependency injection with event emission
    - Contract-driven automatic service registration
    - Workflow orchestration support
    - Enhanced error handling and recovery patterns
    - Performance monitoring and caching
    """

    def __init__(self):
        """Initialize enhanced container with custom methods."""
        self._base_container = _BaseONEXContainer()

        # Initialize performance tracking
        self._performance_metrics = {
            "total_resolutions": 0,
            "cache_hit_rate": 0.0,
            "avg_resolution_time_ms": 0.0,
            "error_rate": 0.0,
            "active_services": 0,
        }

        # Initialize service provider
        self._service_provider = None

    @property
    def base_container(self):
        """Access to base ONEXContainer for compatibility."""
        return self._base_container

    @property
    def config(self):
        """Access to configuration."""
        return self._base_container.config

    @property
    def enhanced_logger(self):
        """Access to enhanced logger."""
        return self._base_container.enhanced_logger

    @property
    def workflow_factory(self):
        """Access to workflow factory."""
        return self._base_container.workflow_factory

    @property
    def workflow_coordinator(self):
        """Access to workflow coordinator."""
        return self._base_container.workflow_coordinator

    @property
    def service_provider(self):
        """Access to monadic service provider."""
        if self._service_provider is None:
            self._service_provider = MonadicServiceProvider(self)
        return self._service_provider

    async def get_service_async(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
        correlation_id: str | None = None,
    ) -> T:
        """
        Async service resolution with monadic patterns.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional service name
            correlation_id: Optional correlation ID for tracking

        Returns:
            T: Resolved service instance

        Raises:
            OnexError: If service resolution fails
        """
        provider = MonadicServiceProvider(self, correlation_id)
        result = await provider.resolve_async(protocol_type, service_name)

        if result.is_failure:
            raise OnexError(
                error_code=CoreErrorCode.SERVICE_RESOLUTION_FAILED,
                message=result.error.message,
                context=result.error.context,
                correlation_id=result.error.correlation_id,
            )

        return result.value

    def get_service_sync(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
    ) -> T:
        """
        Synchronous service resolution for backward compatibility.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional service name

        Returns:
            T: Resolved service instance
        """
        return asyncio.run(self.get_service_async(protocol_type, service_name))

    # Backward compatibility alias
    def get_service(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
    ) -> T:
        """Backward compatibility method."""
        return self.get_service_sync(protocol_type, service_name)

    async def create_enhanced_nodebase(
        self,
        contract_path: Path,
        node_id: str | None = None,
        workflow_id: str | None = None,
        session_id: str | None = None,
    ) -> "ModelNodeBase":
        """
        Factory method for creating Enhanced ModelNodeBase instances.

        Args:
            contract_path: Path to contract file
            node_id: Optional node identifier
            workflow_id: Optional workflow identifier
            session_id: Optional session identifier

        Returns:
            ModelNodeBase: Configured node instance
        """
        from omnibase_core.core.node_base import ModelNodeBase

        return ModelNodeBase(
            contract_path=contract_path,
            node_id=node_id,
            container=self,
            workflow_id=workflow_id,
            session_id=session_id,
        )

    def get_workflow_orchestrator(self):
        """Get workflow orchestration coordinator."""
        return self.workflow_coordinator()

    def get_performance_metrics(self) -> dict[str, ModelStateValue]:
        """
        Get container performance metrics.

        Returns:
            Dict containing resolution times, cache hits, errors, etc.
        """
        # Convert performance metrics to ModelStateValue
        return {
            key: ModelStateValue.from_primitive(value)
            for key, value in self._performance_metrics.items()
        }


# === HELPER FUNCTIONS ===


def _create_enhanced_logger(level: LogLevel) -> ProtocolLogger:
    """Create enhanced logger with monadic patterns."""

    class EnhancedLogger:
        def __init__(self, level: LogLevel):
            self.level = level

        def emit_log_event_sync(
            self,
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs,
        ) -> None:
            """Emit log event synchronously."""
            if level.value >= self.level.value:
                datetime.now().isoformat()

        async def emit_log_event_async(
            self,
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs,
        ) -> None:
            """Emit log event asynchronously."""
            self.emit_log_event_sync(level, message, event_type, **kwargs)

        def emit_log_event(
            self,
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs,
        ) -> None:
            """Emit log event (defaults to sync)."""
            self.emit_log_event_sync(level, message, event_type, **kwargs)

        def info(self, message: str) -> None:
            self.emit_log_event_sync(LogLevel.INFO, message, "info")

        def warning(self, message: str) -> None:
            self.emit_log_event_sync(LogLevel.WARNING, message, "warning")

        def error(self, message: str) -> None:
            self.emit_log_event_sync(LogLevel.ERROR, message, "error")

    return EnhancedLogger(level)


def _create_workflow_factory():
    """Create workflow factory for LlamaIndex integration."""

    class WorkflowFactory:
        def create_workflow(
            self,
            workflow_type: str,
            config: dict[str, ModelStateValue] | None = None,
        ):
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

    return WorkflowFactory()


def _create_workflow_coordinator(factory):
    """Create workflow execution coordinator."""

    class WorkflowCoordinator:
        def __init__(self, factory):
            self.factory = factory
            self.active_workflows: dict[str, ModelStateValue] = {}

        async def execute_workflow(
            self,
            workflow_id: str,
            workflow_type: str,
            input_data: ModelStateValue,
            config: dict[str, ModelStateValue] | None = None,
        ) -> NodeResult[ModelStateValue]:
            """Execute workflow with monadic result."""
            try:
                self.factory.create_workflow(
                    workflow_type,
                    config,
                )
                # Execute workflow using the configured type and input data
                workflow_result = await self._execute_workflow_type(
                    workflow_type,
                    input_data,
                    config,
                )

                return NodeResult.success(
                    value=workflow_result,
                    provenance=[f"workflow.{workflow_type}"],
                    trust_score=0.9,
                    metadata={
                        "workflow_id": workflow_id,
                        "workflow_type": workflow_type,
                    },
                )

            except Exception as e:
                error_info = ErrorInfo(
                    error_type=ErrorType.PERMANENT,
                    message=f"Workflow execution failed: {e!s}",
                    correlation_id=workflow_id,
                    retryable=False,
                )

                return NodeResult.failure(
                    error=error_info,
                    provenance=[f"workflow.{workflow_type}.failed"],
                )

        async def _execute_workflow_type(
            self,
            workflow_type: str,
            input_data: Any,
            config: dict[str, Any],
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
                    source="enhanced_onex_container",
                    metadata={
                        "workflow_type": workflow_type,
                        "error": str(e),
                    },
                )
                raise

        def get_active_workflows(self) -> list[str]:
            """Get list of active workflow IDs."""
            return list(self.active_workflows.keys())

    return WorkflowCoordinator(factory)


# === CONTAINER FACTORY ===


async def create_enhanced_onex_container() -> EnhancedONEXContainer:
    """
    Create and configure enhanced ONEX container.

    Returns:
        EnhancedONEXContainer: Configured container instance
    """
    container = EnhancedONEXContainer()

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

_enhanced_container: EnhancedONEXContainer | None = None


async def get_enhanced_container() -> EnhancedONEXContainer:
    """Get or create global enhanced container instance."""
    global _enhanced_container
    if _enhanced_container is None:
        _enhanced_container = await create_enhanced_onex_container()
    return _enhanced_container


def get_enhanced_container_sync() -> EnhancedONEXContainer:
    """Get enhanced container synchronously."""
    return asyncio.run(get_enhanced_container())
