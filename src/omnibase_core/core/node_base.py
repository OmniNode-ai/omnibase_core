"""
ModelNodeBase for ONEX Monadic Architecture.

This module provides the ModelNodeBase class that implements
the full monadic architecture with LlamaIndex workflow integration,
observable state transitions, and contract-driven orchestration.

Author: ONEX Framework Team
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Generic, TypeVar
from uuid import uuid4

from omnibase.enums.enum_log_level import LogLevelEnum

from omnibase_core.core.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.core_uuid_service import UUIDService
from omnibase_core.core.models.model_node_base import ModelNodeBase
from omnibase_core.core.monadic.model_node_result import (
    ErrorInfo,
    ErrorType,
    Event,
    ExecutionContext,
    LogEntry,
    NodeResult,
)
from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.mixin.mixin_event_listener import MixinEventListener
from omnibase_core.mixin.mixin_introspection_publisher import (
    MixinIntrospectionPublisher,
)
from omnibase_core.mixin.mixin_node_id_from_contract import MixinNodeIdFromContract
from omnibase_core.mixin.mixin_request_response_introspection import (
    MixinRequestResponseIntrospection,
)
from omnibase_core.mixin.mixin_tool_execution import MixinToolExecution
from omnibase_core.model.core.model_reducer import ActionModel, ModelState
from omnibase_core.protocol.protocol_workflow_reducer import ProtocolWorkflowReducer

T = TypeVar("T")
U = TypeVar("U")


class ModelNodeBase(
    MixinEventListener,
    MixinIntrospectionPublisher,
    MixinRequestResponseIntrospection,
    MixinNodeIdFromContract,
    MixinToolExecution,
    ProtocolWorkflowReducer,
    Generic[T, U],
):
    """
    Enhanced ModelNodeBase class implementing monadic architecture patterns.

    This class provides:
    - Monadic NodeResult composition with bind operations
    - LlamaIndex workflow integration for complex orchestration
    - Observable state transitions with event emission
    - Contract-driven initialization with ONEXContainer
    - Universal hub pattern support with signal orchestration
    - Comprehensive error handling and recovery mechanisms

    **MONADIC COMPOSITION PATTERNS**:
    - All operations return NodeResult<T> for composability
    - Bind operations enable safe chaining with context propagation
    - Map operations for value transformations
    - Gather operations for parallel execution

    **WORKFLOW INTEGRATION**:
    - LlamaIndex workflow support for complex orchestration
    - Asynchronous state transitions with workflow coordination
    - Event-driven communication between workflow steps
    - Observable workflow execution with monitoring support

    **CONTRACT-DRIVEN ARCHITECTURE**:
    - ONEXContainer dependency injection from contracts
    - Automatic tool resolution and configuration
    - Declarative behavior specification via YAML contracts
    - Type-safe contract validation and generation

    **OBSERVABLE STATE MANAGEMENT**:
    - Event emission for all state transitions
    - Context propagation with trust and correlation tracking
    - Structured logging with provenance information
    - Signal orchestration for hub communication
    """

    def __init__(
        self,
        contract_path: Path,
        node_id: str | None = None,
        event_bus: object | None = None,
        container: ONEXContainer | None = None,
        workflow_id: str | None = None,
        session_id: str | None = None,
        **kwargs,
    ):
        """
        Initialize ModelNodeBase with monadic patterns and workflow support.

        Args:
            contract_path: Path to the contract file
            node_id: Optional node identifier (derived from contract if not provided)
            event_bus: Optional event bus for event emission and subscriptions
            container: Optional pre-created ONEXContainer (created from contract if not provided)
            workflow_id: Optional workflow identifier for orchestration tracking
            session_id: Optional session identifier for correlation
            **kwargs: Additional initialization parameters
        """
        # Initialize mixin chain in proper order with contract path
        super().__init__(contract_path=contract_path, **kwargs)

        # Generate identifiers
        self.workflow_id = workflow_id or str(uuid4())
        self.session_id = session_id or str(uuid4())
        self.correlation_id = str(uuid4())

        # Store initialization parameters
        self._contract_path = contract_path
        self._container: ONEXContainer | None = None
        self._main_tool = None
        self._reducer_state: ModelState | None = None
        self._workflow_instance = None

        try:
            # Load and validate contract
            self._load_contract_and_initialize(
                contract_path,
                node_id,
                event_bus,
                container,
            )

            # Initialize reducer state
            self._reducer_state = self.initial_state()

            # Create workflow instance if needed
            self._workflow_instance = self.create_workflow()

            # Emit initialization event
            self._emit_initialization_event()

        except Exception as e:
            self._emit_initialization_failure(e)
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to initialize ModelNodeBase: {e!s}",
                context={
                    "contract_path": str(contract_path),
                    "node_id": node_id,
                    "workflow_id": self.workflow_id,
                },
                correlation_id=self.correlation_id,
            ) from e

    def _load_contract_and_initialize(
        self,
        contract_path: Path,
        node_id: str | None,
        event_bus: object | None,
        container: ONEXContainer | None,
    ):
        """Load contract and initialize core components."""
        # Load contract service
        from omnibase_core.core.services.contract_service.v1_0_0.contract_service import (
            ContractService,
        )

        contract_service = ContractService(
            cache_enabled=True,
            cache_max_size=100,
            base_path=contract_path.parent,
        )
        contract_content = contract_service.load_contract(contract_path)

        # Derive node_id from contract if not provided
        if node_id is None:
            node_id = contract_content.node_name

        self.node_id = node_id

        # Create or use provided container
        if container is None:
            if (
                hasattr(contract_content, "dependencies")
                and contract_content.dependencies is not None
            ):

                # Create container from contract dependencies
                from omnibase_core.core.services.container_service.v1_0_0.container_service import (
                    ContainerService,
                )
                from omnibase_core.core.services.container_service.v1_0_0.models.model_container_config import (
                    ModelContainerConfig,
                )

                container_config = ModelContainerConfig(
                    node_id=node_id,
                    enable_service_validation=True,
                    enable_lifecycle_logging=True,
                    enable_registry_wrapper=True,
                )

                container_service = ContainerService(config=container_config)
                container_result = container_service.create_container_from_contract(
                    contract_content=contract_content,
                    node_id=node_id,
                    nodebase_ref=self,
                )

                container = container_result.registry

        self._container = container

        # Store contract and configuration
        self.state = ModelNodeBase(
            contract_path=contract_path,
            node_id=node_id,
            contract_content=contract_content,
            registry_reference=None,  # We use container instead
            node_name=contract_content.node_name,
            version=f"{contract_content.contract_version.major}.{contract_content.contract_version.minor}.{contract_content.contract_version.patch}",
            node_tier=1,
            node_classification=contract_content.tool_specification.business_logic_pattern.value,
            event_bus=event_bus,
            initialization_metadata={
                "main_tool_class": contract_content.tool_specification.main_tool_class,
                "contract_path": str(contract_path),
                "initialization_time": str(time.time()),
                "workflow_id": self.workflow_id,
                "session_id": self.session_id,
            },
        )

        # Resolve main tool
        self._main_tool = self._resolve_main_tool()

    def _resolve_main_tool(self) -> object:
        """Resolve and instantiate the main tool class from contract."""
        try:
            from omnibase_core.core.services.tool_discovery_service.v1_0_0.models.model_tool_discovery_config import (
                ModelToolDiscoveryConfig,
            )
            from omnibase_core.core.services.tool_discovery_service.v1_0_0.tool_discovery_service import (
                ToolDiscoveryService,
            )

            discovery_config = ModelToolDiscoveryConfig(
                enable_module_caching=True,
                enable_tool_validation=True,
                enable_legacy_registry_fallback=True,
                enable_security_validation=True,
            )

            tool_discovery_service = ToolDiscoveryService(config=discovery_config)

            discovery_result = tool_discovery_service.resolve_tool_from_contract(
                contract_content=self.state.contract_content,
                registry=self._container,
                contract_path=self.state.contract_path,
            )

            return discovery_result.tool_instance

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to resolve main tool: {e!s}",
                context={
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,
                    "node_id": self.state.node_id,
                    "workflow_id": self.workflow_id,
                },
                correlation_id=self.correlation_id,
            ) from e

    # ===== MONADIC INTERFACE =====

    async def run_async(self, input_state: T) -> NodeResult[U]:
        """
        Universal async run method with complete monadic composition.

        This is the primary interface for node execution with:
        - Complete event lifecycle management
        - Monadic error handling and composition
        - Observable state transitions
        - Context propagation and correlation tracking

        Args:
            input_state: Tool-specific input state (strongly typed)

        Returns:
            NodeResult[U]: Monadic result with output, context, and events
        """
        correlation_id = str(UUIDService.generate_correlation_id())
        start_time = datetime.now()

        # Create execution context
        execution_context = ExecutionContext(
            provenance=[f"node.{self.node_id}"],
            logs=[],
            trust_score=1.0,
            timestamp=start_time,
            metadata={
                "node_id": self.node_id,
                "node_name": self.state.node_name,
                "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,
                "input_type": type(input_state).__name__,
            },
            session_id=self.session_id,
            correlation_id=correlation_id,
            node_id=self.node_id,
            workflow_id=self.workflow_id,
        )

        # Emit start event
        start_event = Event(
            type="node.execution.started",
            payload={
                "node_id": self.node_id,
                "node_name": self.state.node_name,
                "input_type": type(input_state).__name__,
                "correlation_id": correlation_id,
            },
            timestamp=start_time,
            source=self.node_id,
            correlation_id=correlation_id,
            workflow_id=self.workflow_id,
            session_id=self.session_id,
        )

        try:
            # Delegate to process method
            result = await self.process_async(input_state)

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Emit success event
            success_event = Event(
                type="node.execution.completed",
                payload={
                    "node_id": self.node_id,
                    "node_name": self.state.node_name,
                    "duration_ms": duration_ms,
                    "output_type": (
                        type(result).__name__ if result is not None else "None"
                    ),
                    "correlation_id": correlation_id,
                },
                timestamp=end_time,
                source=self.node_id,
                correlation_id=correlation_id,
                workflow_id=self.workflow_id,
                session_id=self.session_id,
            )

            # Update execution context
            execution_context.logs.append(
                LogEntry("INFO", "Node execution completed successfully", end_time),
            )
            execution_context.metadata["duration_ms"] = duration_ms
            execution_context.timestamp = end_time

            return NodeResult(
                value=result,
                context=execution_context,
                state_delta={"last_execution": end_time.isoformat()},
                events=[start_event, success_event],
            )

        except OnexError as e:
            # Handle ONEX errors with structured failure
            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=e.message,
                code=e.error_code.value if e.error_code else None,
                context=e.context,
                correlation_id=correlation_id,
                retryable=False,
            )

            failure_event = Event(
                type="node.execution.failed",
                payload={
                    "node_id": self.node_id,
                    "error_type": error_info.error_type.value,
                    "error_message": error_info.message,
                    "error_code": error_info.code,
                    "correlation_id": correlation_id,
                },
                timestamp=datetime.now(),
                source=self.node_id,
                correlation_id=correlation_id,
                workflow_id=self.workflow_id,
                session_id=self.session_id,
            )

            execution_context.logs.append(
                LogEntry(
                    "ERROR", f"Node execution failed: {e.message}", datetime.now()
                ),
            )

            return NodeResult(
                value=None,
                context=execution_context,
                events=[start_event, failure_event],
                error=error_info,
            )

        except Exception as e:
            # Handle generic exceptions
            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=f"Node execution failed: {e!s}",
                trace=str(e.__traceback__) if e.__traceback__ else None,
                correlation_id=correlation_id,
                retryable=False,
            )

            failure_event = Event(
                type="node.execution.exception",
                payload={
                    "node_id": self.node_id,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "correlation_id": correlation_id,
                },
                timestamp=datetime.now(),
                source=self.node_id,
                correlation_id=correlation_id,
                workflow_id=self.workflow_id,
                session_id=self.session_id,
            )

            execution_context.logs.append(
                LogEntry("ERROR", f"Node execution exception: {e!s}", datetime.now()),
            )

            return NodeResult(
                value=None,
                context=execution_context,
                events=[start_event, failure_event],
                error=error_info,
            )

    async def process_async(self, input_state: T) -> U:
        """
        Process method that delegates to the main tool.

        This method handles the actual business logic delegation to the
        resolved main tool instance, following the contract-driven pattern.

        Args:
            input_state: Tool-specific input state

        Returns:
            U: Tool-specific output state
        """
        try:
            emit_log_event(
                LogLevelEnum.INFO,
                f"Processing with ModelNodeBase: {self.state.node_name}",
                {
                    "node_name": self.state.node_name,
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,
                    "business_logic_pattern": self.state.node_classification,
                    "workflow_id": self.workflow_id,
                },
            )

            main_tool = self._main_tool

            # Check if tool supports async processing
            if hasattr(main_tool, "process_async"):
                return await main_tool.process_async(input_state)
            if hasattr(main_tool, "process"):
                # Run sync process in thread pool to avoid blocking
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    main_tool.process,
                    input_state,
                )
            if hasattr(main_tool, "run"):
                # Run sync run method in thread pool
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    main_tool.run,
                    input_state,
                )
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message="Main tool does not implement process_async(), process(), or run() method",
                context={
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,
                    "node_name": self.state.node_name,
                    "workflow_id": self.workflow_id,
                },
                correlation_id=self.correlation_id,
            )

        except OnexError:
            # Re-raise ONEX errors (fail-fast)
            raise
        except Exception as e:
            # Convert generic exceptions to ONEX errors
            emit_log_event(
                LogLevelEnum.ERROR,
                f"Error in ModelNodeBase processing: {e!s}",
                {
                    "node_name": self.state.node_name,
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,
                    "error": str(e),
                    "workflow_id": self.workflow_id,
                },
            )
            raise OnexError(
                message=f"ModelNodeBase processing error: {e!s}",
                error_code=CoreErrorCode.OPERATION_FAILED,
                context={
                    "node_name": self.state.node_name,
                    "node_tier": self.state.node_tier,
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,
                    "workflow_id": self.workflow_id,
                },
                correlation_id=self.correlation_id,
            ) from e

    # ===== BACKWARD COMPATIBILITY =====

    def run(self, input_state: T) -> U:
        """
        Synchronous run method for backward compatibility.

        This method provides backward compatibility with existing code
        that expects synchronous execution patterns.

        Args:
            input_state: Tool-specific input state

        Returns:
            U: Tool-specific output state
        """
        # Run async version and return just the value
        result = asyncio.run(self.run_async(input_state))

        if result.is_failure:
            # Convert failure to exception for sync interface
            if result.error:
                raise OnexError(
                    message=result.error.message,
                    error_code=CoreErrorCode.OPERATION_FAILED,
                    context=result.error.context,
                    correlation_id=result.error.correlation_id,
                )
            raise OnexError(
                message="Node execution failed without error details",
                error_code=CoreErrorCode.OPERATION_FAILED,
                correlation_id=self.correlation_id,
            )

        return result.value

    def process(self, input_state: T) -> U:
        """
        Synchronous process method for backward compatibility.

        Args:
            input_state: Tool-specific input state

        Returns:
            U: Tool-specific output state
        """
        return asyncio.run(self.process_async(input_state))

    # ===== REDUCER IMPLEMENTATION =====

    def initial_state(self) -> ModelState:
        """
        Returns the initial state for the reducer.

        Default implementation returns empty state.
        Override in subclasses for custom initial state.
        """
        from omnibase_core.model.core.model_reducer import ModelState

        return ModelState()

    def dispatch(self, state: ModelState, action: ActionModel) -> ModelState:
        """
        Synchronous state transition for simple operations.

        Default implementation returns unchanged state.
        Override in subclasses for custom state transitions.
        """
        return state

    async def dispatch_async(
        self,
        state: ModelState,
        action: ActionModel,
    ) -> NodeResult[ModelState]:
        """
        Asynchronous workflow-based state transition.

        Default implementation wraps synchronous dispatch.
        Override in subclasses for workflow-based transitions.
        """
        try:
            new_state = self.dispatch(state, action)

            return NodeResult.success(
                value=new_state,
                provenance=[f"{self.node_id}.dispatch"],
                trust_score=1.0,
                metadata={
                    "action_type": getattr(action, "type", "unknown"),
                    "node_id": self.node_id,
                    "workflow_id": self.workflow_id,
                },
                state_delta={
                    "previous_state": (
                        state.__dict__ if hasattr(state, "__dict__") else str(state)
                    ),
                    "new_state": (
                        new_state.__dict__
                        if hasattr(new_state, "__dict__")
                        else str(new_state)
                    ),
                },
                session_id=self.session_id,
                correlation_id=self.correlation_id,
                node_id=self.node_id,
                workflow_id=self.workflow_id,
            )

        except Exception as e:
            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=f"State dispatch failed: {e!s}",
                trace=str(e.__traceback__) if e.__traceback__ else None,
                correlation_id=self.correlation_id,
                retryable=False,
            )

            return NodeResult.failure(
                error=error_info,
                provenance=[f"{self.node_id}.dispatch.failed"],
                session_id=self.session_id,
                correlation_id=self.correlation_id,
                node_id=self.node_id,
                workflow_id=self.workflow_id,
            )

    def create_workflow(self):
        """
        Factory method for creating LlamaIndex workflow instances.

        Default implementation returns None (no workflow needed).
        Override in subclasses that need workflow orchestration.
        """
        return

    # ===== HELPER METHODS =====

    def _emit_initialization_event(self):
        """Emit initialization success event."""
        event = Event(
            type="node.initialization.completed",
            payload={
                "node_id": self.node_id,
                "node_name": self.state.node_name,
                "contract_path": str(self._contract_path),
                "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,
            },
            timestamp=datetime.now(),
            source=self.node_id,
            correlation_id=self.correlation_id,
            workflow_id=self.workflow_id,
            session_id=self.session_id,
        )

        emit_log_event(
            LogLevelEnum.INFO,
            f"ModelNodeBase initialized: {self.node_id}",
            event.payload,
        )

    def _emit_initialization_failure(self, error: Exception):
        """Emit initialization failure event."""
        event = Event(
            type="node.initialization.failed",
            payload={
                "node_id": self.node_id if hasattr(self, "node_id") else "unknown",
                "contract_path": str(self._contract_path),
                "error": str(error),
                "error_type": type(error).__name__,
            },
            timestamp=datetime.now(),
            correlation_id=self.correlation_id,
            workflow_id=self.workflow_id,
            session_id=self.session_id,
        )

        emit_log_event(
            LogLevelEnum.ERROR,
            f"ModelNodeBase initialization failed: {error!s}",
            event.payload,
        )

    # ===== PROPERTIES =====

    @property
    def container(self) -> ONEXContainer:
        """Get the ONEXContainer instance for dependency injection."""
        return self._container

    @property
    def main_tool(self) -> object:
        """Get the resolved main tool instance."""
        return self._main_tool

    @property
    def current_state(self) -> ModelState:
        """Get the current reducer state."""
        return self._reducer_state

    @property
    def workflow_instance(self):
        """Get the LlamaIndex workflow instance if available."""
        return self._workflow_instance
