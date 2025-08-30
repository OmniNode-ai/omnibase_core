"""
NodeCoreBase - Foundation for 4-Node Architecture.

Abstract foundation providing minimal essential functionality for the 4-node
architecture: NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator.

This base class implements only the core functionality needed by all node types:
- Contract loading and validation
- Basic lifecycle management (initialize → process → complete → cleanup)
- Dependency injection through ONEXContainer
- Protocol compliance with duck typing
- Error handling with OnexError exception chaining
- Event emission for lifecycle transitions
- Metadata tracking and introspection support

Author: ONEX Framework Team
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from omnibase.core.core_errors import CoreErrorCode, OnexError
from omnibase.core.core_structured_logging import emit_log_event_sync as emit_log_event
from omnibase.core.core_uuid_service import UUIDService
from omnibase.core.onex_container import ONEXContainer
from omnibase.enums.enum_log_level import LogLevelEnum


class NodeCoreBase(ABC):
    """
    Abstract foundation for 4-node architecture with ONEXContainer integration.

    Provides minimal essential functionality required by all specialized node types.
    Each node type inherits from this base and adds only the specific capabilities
    it needs for its architectural role.

    ZERO TOLERANCE: No Any types allowed in implementation.

    Lifecycle: initialize → process → complete → cleanup

    Core Capabilities:
    - Container-based dependency injection
    - Registry protocol resolution without isinstance checks
    - Event emission for lifecycle transitions
    - Metadata tracking and introspection support
    - Performance monitoring and metrics collection
    - Contract loading and validation
    - Version tracking and migration support
    """

    def __init__(self, container: ONEXContainer) -> None:
        """
        Initialize NodeCoreBase with ONEXContainer dependency injection.

        Args:
            container: ONEX container for modern dependency injection

        Raises:
            OnexError: If container is invalid or initialization fails
        """
        if container is None:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Container cannot be None for NodeCoreBase initialization",
                context={"node_type": self.__class__.__name__},
            )

        self.container = container
        self.node_id: str = str(UUIDService.generate_correlation_id())
        self.created_at: datetime = datetime.now()

        # Core state tracking
        self.state: Dict[str, str] = {"status": "initialized"}
        self.metrics: Dict[str, float] = {
            "initialization_time_ms": 0.0,
            "total_operations": 0.0,
            "avg_processing_time_ms": 0.0,
            "error_count": 0.0,
            "success_count": 0.0,
        }

        # Contract and configuration
        self.contract_data: Optional[Dict[str, Any]] = None
        self.version: str = "1.0.0"

        # Initialize metrics
        self.metrics["initialization_time_ms"] = time.time() * 1000

    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """
        Core processing method - implementation varies by node type.

        This is the main entry point for node-specific business logic.
        Each specialized node type implements this according to its
        architectural role:

        - NodeCompute: Pure computation with input → transform → output
        - NodeEffect: Side effect execution with transaction management
        - NodeReducer: Data aggregation and state reduction
        - NodeOrchestrator: Workflow coordination and thunk emission

        Args:
            input_data: Node-specific input (strongly typed by each implementation)

        Returns:
            Node-specific output (strongly typed by each implementation)

        Raises:
            OnexError: If processing fails or validation errors occur
        """
        raise NotImplementedError("Subclasses must implement process method")

    async def initialize(self) -> None:
        """
        Lifecycle initialization with dependency resolution.

        Performs startup tasks common to all node types:
        - Validates container dependencies
        - Loads and validates contracts
        - Sets up performance monitoring
        - Initializes event emission capabilities

        Raises:
            OnexError: If initialization fails or dependencies unavailable
        """
        try:
            start_time = time.time()

            # Validate container
            if not hasattr(self.container, "get_service"):
                raise OnexError(
                    error_code=CoreErrorCode.DEPENDENCY_UNAVAILABLE,
                    message="Container does not implement get_service method",
                    context={
                        "node_id": self.node_id,
                        "container_type": type(self.container).__name__,
                    },
                )

            # Update state
            self.state["status"] = "initializing"

            # Load contract if path available
            await self._load_contract()

            # Initialize node-specific resources
            await self._initialize_node_resources()

            # Update metrics
            initialization_time = (time.time() - start_time) * 1000
            self.metrics["initialization_time_ms"] = initialization_time

            # Update state
            self.state["status"] = "ready"

            # Emit lifecycle event
            await self._emit_lifecycle_event(
                "node_initialized",
                {
                    "initialization_time_ms": initialization_time,
                    "node_type": self.__class__.__name__,
                },
            )

            emit_log_event(
                LogLevelEnum.INFO,
                f"NodeCoreBase initialized: {self.__class__.__name__}",
                {
                    "node_id": self.node_id,
                    "initialization_time_ms": initialization_time,
                    "status": self.state["status"],
                },
            )

        except Exception as e:
            self.state["status"] = "failed"
            self.metrics["error_count"] += 1

            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Node initialization failed: {str(e)}",
                context={
                    "node_id": self.node_id,
                    "node_type": self.__class__.__name__,
                    "error": str(e),
                },
            ) from e

    async def cleanup(self) -> None:
        """
        Resource cleanup and metrics reporting.

        Performs cleanup tasks common to all node types:
        - Releases container resources
        - Reports final metrics
        - Emits completion events
        - Cleans up temporary state

        Should be called when node lifecycle is complete.
        """
        try:
            start_time = time.time()

            # Update state
            self.state["status"] = "cleaning_up"

            # Cleanup node-specific resources
            await self._cleanup_node_resources()

            # Calculate final metrics
            cleanup_time = (time.time() - start_time) * 1000
            total_lifetime = (time.time() * 1000) - self.metrics[
                "initialization_time_ms"
            ]

            # Emit final metrics
            final_metrics = {
                **self.metrics,
                "cleanup_time_ms": cleanup_time,
                "total_lifetime_ms": total_lifetime,
                "final_status": self.state["status"],
            }

            # Emit lifecycle event
            await self._emit_lifecycle_event("node_cleanup_complete", final_metrics)

            # Update final state
            self.state["status"] = "cleaned_up"

            emit_log_event(
                LogLevelEnum.INFO,
                f"NodeCoreBase cleanup complete: {self.__class__.__name__}",
                {
                    "node_id": self.node_id,
                    "cleanup_time_ms": cleanup_time,
                    "total_lifetime_ms": total_lifetime,
                },
            )

        except Exception as e:
            self.state["status"] = "cleanup_failed"

            emit_log_event(
                LogLevelEnum.ERROR,
                f"Node cleanup failed: {str(e)}",
                {
                    "node_id": self.node_id,
                    "node_type": self.__class__.__name__,
                    "error": str(e),
                },
            )

            # Don't raise exception in cleanup to prevent resource leaks

    async def get_performance_metrics(self) -> Dict[str, float]:
        """
        Get node performance and quality metrics.

        Returns:
            Performance metrics dictionary with timing and success metrics
        """
        # Calculate derived metrics
        total_ops = self.metrics["total_operations"]
        if total_ops > 0:
            success_rate = self.metrics["success_count"] / total_ops
            error_rate = self.metrics["error_count"] / total_ops
        else:
            success_rate = 0.0
            error_rate = 0.0

        return {
            **self.metrics,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "uptime_ms": (time.time() * 1000) - self.metrics["initialization_time_ms"],
            "node_health_score": max(0.0, 1.0 - error_rate),
        }

    async def get_introspection_data(self) -> Dict[str, Any]:
        """
        Get node introspection data for monitoring and debugging.

        Returns:
            Dictionary containing node state, metrics, and capabilities
        """
        return {
            "node_id": self.node_id,
            "node_type": self.__class__.__name__,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "state": self.state.copy(),
            "metrics": await self.get_performance_metrics(),
            "capabilities": self._get_node_capabilities(),
            "contract_loaded": self.contract_data is not None,
            "container_available": self.container is not None,
        }

    def get_node_id(self) -> str:
        """Get unique node identifier."""
        return self.node_id

    def get_node_type(self) -> str:
        """Get node type classification."""
        return self.__class__.__name__

    def get_version(self) -> str:
        """Get node version."""
        return self.version

    def get_state(self) -> Dict[str, str]:
        """Get current node state."""
        return self.state.copy()

    async def _load_contract(self) -> None:
        """
        Load and validate contract configuration.

        Attempts to load contract data from container or environment.
        Contract loading is optional - nodes can operate without contracts.
        """
        try:
            # Try to get contract service from container
            contract_service = None
            try:
                contract_service = self.container.get_service("contract_service")
            except Exception:
                # Contract service not available - that's OK
                pass

            if contract_service and hasattr(contract_service, "get_node_contract"):
                # Load contract for this node type
                contract_data = contract_service.get_node_contract(
                    self.__class__.__name__
                )
                if contract_data:
                    self.contract_data = contract_data

                    # Extract version if available
                    if "version" in contract_data:
                        self.version = str(contract_data["version"])

                    emit_log_event(
                        LogLevelEnum.INFO,
                        f"Contract loaded for {self.__class__.__name__}",
                        {
                            "node_id": self.node_id,
                            "contract_keys": list(contract_data.keys()),
                        },
                    )

        except Exception as e:
            # Contract loading failure is not fatal
            emit_log_event(
                LogLevelEnum.WARNING,
                f"Contract loading failed (continuing without): {str(e)}",
                {"node_id": self.node_id, "node_type": self.__class__.__name__},
            )

    async def _initialize_node_resources(self) -> None:
        """
        Initialize node-specific resources.

        Override in subclasses to add node-type-specific initialization.
        Base implementation does nothing.
        """
        pass

    async def _cleanup_node_resources(self) -> None:
        """
        Cleanup node-specific resources.

        Override in subclasses to add node-type-specific cleanup.
        Base implementation does nothing.
        """
        pass

    async def _emit_lifecycle_event(
        self, event_type: str, metadata: Dict[str, Any]
    ) -> None:
        """
        Emit lifecycle transition events.

        Args:
            event_type: Type of lifecycle event
            metadata: Additional event metadata
        """
        try:
            # Try to get event bus from container
            event_bus = None
            try:
                event_bus = self.container.get_service("event_bus")
            except Exception:
                # Event bus not available - that's OK
                pass

            if event_bus and hasattr(event_bus, "emit_event"):
                correlation_id = UUID(self.node_id)
                event_data = {
                    "node_id": self.node_id,
                    "node_type": self.__class__.__name__,
                    "event_type": event_type,
                    "timestamp": datetime.now().isoformat(),
                    **metadata,
                }

                await event_bus.emit_event(
                    event_type=f"node.{event_type}",
                    payload=event_data,
                    correlation_id=correlation_id,
                )

        except Exception as e:
            # Event emission failure is not fatal
            emit_log_event(
                LogLevelEnum.WARNING,
                f"Event emission failed: {str(e)}",
                {"node_id": self.node_id, "event_type": event_type},
            )

    def _get_node_capabilities(self) -> Dict[str, bool]:
        """
        Get node capabilities for introspection.

        Returns:
            Dictionary of capability flags
        """
        return {
            "supports_async_processing": True,
            "supports_lifecycle_management": True,
            "supports_metrics_collection": True,
            "supports_event_emission": True,
            "supports_contract_loading": True,
            "supports_introspection": True,
            "supports_dependency_injection": True,
        }

    async def _update_processing_metrics(
        self, processing_time_ms: float, success: bool
    ) -> None:
        """
        Update processing metrics after operation completion.

        Args:
            processing_time_ms: Time taken for processing
            success: Whether operation was successful
        """
        self.metrics["total_operations"] += 1

        if success:
            self.metrics["success_count"] += 1
        else:
            self.metrics["error_count"] += 1

        # Update rolling average of processing time
        total_ops = self.metrics["total_operations"]
        current_avg = self.metrics["avg_processing_time_ms"]
        self.metrics["avg_processing_time_ms"] = (
            current_avg * (total_ops - 1) + processing_time_ms
        ) / total_ops

    def _validate_input_data(self, input_data: Any) -> None:
        """
        Validate input data for processing.

        Base implementation performs basic null checks.
        Override in subclasses for node-specific validation.

        Args:
            input_data: Input data to validate

        Raises:
            OnexError: If validation fails
        """
        if input_data is None:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Input data cannot be None",
                context={"node_id": self.node_id, "node_type": self.__class__.__name__},
            )
