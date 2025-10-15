import uuid
from typing import Dict

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
NodeCoreBase - Foundation for 4-Node ModelArchitecture.

Abstract foundation providing minimal essential functionality for the 4-node
architecture: NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator.

This base class implements only the core functionality needed by all node types:
- Contract loading and validation
- Basic lifecycle management (initialize → process → complete → cleanup)
- Dependency injection through ModelONEXContainer
- Protocol compliance with duck typing
- Error handling with ModelOnexError exception chaining
- Event emission for lifecycle transitions
- Metadata tracking and introspection support

Author: ONEX Framework Team
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

# Removed: EnumCoreErrorCode doesn't exist in enums module
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeCoreBase(ABC):
    """
    Abstract foundation for 4-node architecture with ModelONEXContainer integration.

    Provides minimal essential functionality required by all specialized node types.
    Each node type inherits from this base and adds only the specific capabilities
    it needs for its architectural role.

    ZERO TOLERANCE: No Any types allowed in implementation.

    EnumLifecycle: initialize → process → complete → cleanup

    Core Capabilities:
    - Container-based dependency injection
    - Registry protocol resolution without isinstance checks
    - Event emission for lifecycle transitions
    - Metadata tracking and introspection support
    - Performance monitoring and metrics collection
    - Contract loading and validation
    - Version tracking and migration support
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize NodeCoreBase with ModelONEXContainer dependency injection.

        Args:
            container: ONEX container for modern dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        if container is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Container cannot be None for NodeCoreBase initialization",
                context={"node_type": self.__class__.__name__},
            )

        self.container = container
        self.node_id: UUID = uuid4()
        self.created_at: datetime = datetime.now()

        # Core state tracking
        self.state: dict[str, str] = {"status": "initialized"}
        self.metrics: dict[str, float] = {
            "initialization_time_ms": 0.0,
            "total_operations": 0.0,
            "avg_processing_time_ms": 0.0,
            "error_count": 0.0,
            "success_count": 0.0,
        }

        # Contract and configuration
        self.contract_data: dict[str, str] | None = None
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
            ModelOnexError: If processing fails or validation errors occur
        """
        msg = "Subclasses must implement process method"
        raise NotImplementedError(msg)  # stub-ok: abstract method

    async def initialize(self) -> None:
        """
        EnumLifecycle initialization with dependency resolution.

        Performs startup tasks common to all node types:
        - Validates container dependencies
        - Loads and validates contracts
        - Sets up performance monitoring
        - Initializes event emission capabilities

        Raises:
            ModelOnexError: If initialization fails or dependencies unavailable
        """
        try:
            start_time = time.time()

            # Validate container
            if not hasattr(self.container, "get_service"):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
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
                LogLevel.INFO,
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

            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Node initialization failed: {e!s}",
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
                LogLevel.INFO,
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
                LogLevel.ERROR,
                f"Node cleanup failed: {e!s}",
                {
                    "node_id": self.node_id,
                    "node_type": self.__class__.__name__,
                    "error": str(e),
                },
            )

            # Don't raise exception in cleanup to prevent resource leaks

    async def get_performance_metrics(self) -> dict[str, float]:
        """
        Get node performance and quality metrics.

        Returns:
            Performance metrics dict[str, Any]ionary with timing and success metrics
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

    async def get_introspection_data(self) -> dict[str, Any]:
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

    def get_node_id(self) -> UUID:
        """Get unique node identifier."""
        return self.node_id

    def get_node_type(self) -> str:
        """Get node type classification."""
        return self.__class__.__name__

    def get_version(self) -> str:
        """Get node version."""
        return self.version

    def get_state(self) -> dict[str, str]:
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
            contract_service: Any = None
            try:
                contract_service = self.container.get_service("contract_service")  # type: ignore[arg-type]
            except Exception:
                # Contract service not available - that's OK
                contract_service = None

            if contract_service is not None and hasattr(
                contract_service, "get_node_contract"
            ):
                # Load contract for this node type
                contract_data_raw = contract_service.get_node_contract(
                    self.__class__.__name__,
                )
                if contract_data_raw:
                    # Store raw contract data (specialized nodes override with their own validation)
                    self.contract_data = contract_data_raw

                    # Extract version if present
                    if (
                        isinstance(contract_data_raw, dict)
                        and "version" in contract_data_raw
                    ):
                        self.version = contract_data_raw["version"]

                    emit_log_event(
                        LogLevel.INFO,
                        f"Contract loaded for {self.__class__.__name__}",
                        {
                            "node_id": self.node_id,
                            "contract_keys": (
                                list[Any](contract_data_raw.keys())
                                if isinstance(contract_data_raw, dict)
                                else []
                            ),
                        },
                    )

        except Exception as e:
            # Contract loading failure is not fatal
            emit_log_event(
                LogLevel.WARNING,
                f"Contract loading failed (continuing without): {e!s}",
                {"node_id": self.node_id, "node_type": self.__class__.__name__},
            )

    async def _initialize_node_resources(self) -> None:
        """
        Initialize node-specific resources.

        Override in subclasses to add node-type-specific initialization.
        Base implementation does nothing.
        """

    async def _cleanup_node_resources(self) -> None:
        """
        Cleanup node-specific resources.

        Override in subclasses to add node-type-specific cleanup.
        Base implementation does nothing.
        """

    async def _emit_lifecycle_event(
        self,
        event_type: str,
        metadata: dict[str, Any],
    ) -> None:
        """
        Emit lifecycle transition events.

        Args:
            event_type: Type of lifecycle event
            metadata: Additional event metadata
        """
        try:
            # Try to get event bus from container
            event_bus: Any = None
            try:
                event_bus = self.container.get_service("event_bus")  # type: ignore[arg-type]
            except Exception:
                # Event bus not available - that's OK
                event_bus = None

            if event_bus is not None and hasattr(event_bus, "emit_event"):
                # node_id is already a UUID, use it directly
                correlation_id = self.node_id
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
                LogLevel.WARNING,
                f"Event emission failed: {e!s}",
                {"node_id": self.node_id, "event_type": event_type},
            )

    def _get_node_capabilities(self) -> dict[str, bool]:
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
        self,
        processing_time_ms: float,
        success: bool,
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
            ModelOnexError: If validation fails
        """
        if input_data is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Input data cannot be None",
                context={"node_id": self.node_id, "node_type": self.__class__.__name__},
            )

    # ========================================================================
    # ENHANCED BOILERPLATE METHODS - EXTRACTED FROM ARCHIVED NODE TYPES
    # Agent 1 Extraction: These methods eliminate ~600 lines of duplication
    # across node_effect.py, node_compute.py, node_orchestrator.py, node_reducer.py
    # ========================================================================

    def _find_contract_path_unified(self) -> "Path":
        """
        Find contract.yaml file using stack frame inspection.

        EXTRACTED BOILERPLATE: This method was duplicated across all 4 node types
        (Effect, Compute, Orchestrator, Reducer) with identical implementations.

        Uses Python inspect to traverse the call stack and locate the contract.yaml
        file in the same directory as the calling node class module.

        Returns:
            Path: Absolute path to contract.yaml file

        Raises:
            ModelOnexError: If contract file cannot be found
        """
        import inspect
        from pathlib import Path

        from omnibase_core.constants.contract_constants import CONTRACT_FILENAME

        try:
            # Traverse call stack to find the calling class module
            frame = inspect.currentframe()
            while frame:
                frame = frame.f_back
                if frame and "self" in frame.f_locals:
                    caller_self = frame.f_locals["self"]
                    if hasattr(caller_self, "__module__"):
                        module = inspect.getmodule(caller_self)
                        if module and hasattr(module, "__file__") and module.__file__:
                            module_path = Path(module.__file__)
                            contract_path = module_path.parent / CONTRACT_FILENAME
                            if contract_path.exists():
                                return contract_path

            # Contract file not found in any stack frame
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Could not find {CONTRACT_FILENAME} for {self.__class__.__name__}",
                context={
                    "node_type": self.__class__.__name__,
                    "contract_filename": CONTRACT_FILENAME,
                },
            )

        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Error finding contract path: {e!s}",
                context={
                    "node_id": self.node_id,
                    "node_type": self.__class__.__name__,
                },
            ) from e

    def _resolve_contract_references_unified(
        self,
        data: Any,
        base_path: "Path",
        reference_resolver: Any,
    ) -> Any:
        """
        Recursively resolve all $ref references in contract data.

        EXTRACTED BOILERPLATE: This method was duplicated across all 4 node types
        with identical core logic for $ref resolution.

        Handles JSON Pointer-style references ($ref) in YAML contracts,
        supporting relative paths, absolute paths, and internal references.

        Args:
            data: Contract data structure (dict, list, or primitive)
            base_path: Base directory for resolving relative references
            reference_resolver: Reference resolver utility instance

        Returns:
            Resolved contract data with all $ref references loaded

        Raises:
            ModelOnexError: If reference resolution fails critically
        """
        try:
            if isinstance(data, dict):
                if "$ref" in data:
                    # Resolve reference to another file
                    ref_file = data["$ref"]
                    if ref_file.startswith(("./", "../")):
                        # Relative path reference
                        from pathlib import Path

                        ref_path = (base_path / ref_file).resolve()
                    else:
                        # Absolute or root-relative reference
                        from pathlib import Path

                        ref_path = Path(ref_file)

                    return reference_resolver.resolve_reference(
                        str(ref_path),
                        base_path,
                    )

                # Recursively resolve nested dictionaries
                return {
                    key: self._resolve_contract_references_unified(
                        value,
                        base_path,
                        reference_resolver,
                    )
                    for key, value in data.items()
                }

            if isinstance(data, list):
                # Recursively resolve lists
                return [
                    self._resolve_contract_references_unified(
                        item,
                        base_path,
                        reference_resolver,
                    )
                    for item in data
                ]

            # Return primitives as-is
            return data

        except Exception as e:
            # fallback-ok: graceful degradation for contract references
            # Log error but don't stop processing - use original data
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to resolve contract reference: {e!s}",
                {
                    "node_id": self.node_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return data

    def _update_specialized_metrics(
        self,
        metrics_dict: dict[str, dict[str, float]],
        metric_type: str,
        processing_time_ms: float,
        success: bool,
        items_count: int = 1,
    ) -> None:
        """
        Update specialized node-type metrics with rolling averages.

        EXTRACTED BOILERPLATE: This pattern was duplicated across all 4 node types
        (_update_effect_metrics, _update_computation_metrics, etc.)

        Maintains running statistics for each metric type including:
        - Total operations and success/error counts
        - Processing time statistics (avg, min, max)
        - Rolling average calculation
        - Items processed tracking

        Args:
            metrics_dict: Target metrics dictionary to update
            metric_type: Type key for this metric (e.g., "file_operation", "rsd_priority")
            processing_time_ms: Time taken for this operation
            success: Whether operation succeeded
            items_count: Number of items processed (default 1)
        """
        # Initialize metric structure if needed
        if metric_type not in metrics_dict:
            metrics_dict[metric_type] = {
                "total_operations": 0.0,
                "success_count": 0.0,
                "error_count": 0.0,
                "total_items_processed": 0.0,
                "avg_processing_time_ms": 0.0,
                "min_processing_time_ms": float("inf"),
                "max_processing_time_ms": 0.0,
            }

        metrics = metrics_dict[metric_type]
        metrics["total_operations"] += 1
        metrics["total_items_processed"] += items_count

        # Update success/error counters
        if success:
            metrics["success_count"] += 1
        else:
            metrics["error_count"] += 1

        # Update timing statistics
        metrics["min_processing_time_ms"] = min(
            metrics["min_processing_time_ms"],
            processing_time_ms,
        )
        metrics["max_processing_time_ms"] = max(
            metrics["max_processing_time_ms"],
            processing_time_ms,
        )

        # Calculate rolling average of processing time
        total_ops = metrics["total_operations"]
        current_avg = metrics["avg_processing_time_ms"]
        metrics["avg_processing_time_ms"] = (
            current_avg * (total_ops - 1) + processing_time_ms
        ) / total_ops

    def _get_health_status_comprehensive(
        self,
        health_checks: dict[str, bool],
    ) -> dict[str, Any]:
        """
        Aggregate health status from multiple component checks.

        EXTRACTED BOILERPLATE: This pattern was duplicated across all 4 node types
        with similar health aggregation logic.

        Args:
            health_checks: Dictionary of component names to health status

        Returns:
            Comprehensive health status with details
        """
        all_healthy = all(health_checks.values())
        failing_components = [
            component for component, healthy in health_checks.items() if not healthy
        ]

        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "component_checks": health_checks,
            "failing_components": failing_components,
            "healthy_count": sum(1 for h in health_checks.values() if h),
            "total_components": len(health_checks),
            "timestamp": datetime.now().isoformat(),
        }
