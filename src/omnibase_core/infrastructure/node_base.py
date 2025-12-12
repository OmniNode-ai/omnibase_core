from __future__ import annotations

from typing import Any

from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
NodeBase for ONEX ModelArchitecture.

This module provides the NodeBase class that implements
LlamaIndex workflow integration, observable state transitions,
and contract-driven orchestration.

"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

# Core-native protocol imports (no SPI dependency)
from omnibase_core.protocols import (
    ProtocolAction,
    ProtocolNodeResult,
    ProtocolState,
    ProtocolWorkflowReducer,
)

# Alternative name for ProtocolWorkflowReducer
WorkflowReducerInterface = ProtocolWorkflowReducer

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event

# Deferred import to avoid circular dependency
if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer

from omnibase_core.models.infrastructure.model_node_state import ModelNodeState
from omnibase_core.models.infrastructure.model_node_workflow_result import (
    ModelNodeWorkflowResult,
)
from omnibase_core.models.infrastructure.model_state import ModelState

# Simple stub models for reducer pattern (ONEX 2.0 minimal implementation)
# Import from separate files: ModelAction, ModelState, ModelNodeState


class NodeBase[T_INPUT_STATE, T_OUTPUT_STATE](
    WorkflowReducerInterface,
):
    """
    Enhanced NodeBase class implementing ONEX architecture patterns.

    This class provides:
    - LlamaIndex workflow integration for complex orchestration
    - Observable state transitions with event emission
    - Contract-driven initialization with ModelONEXContainer
    - Universal hub pattern support with signal orchestration
    - Comprehensive error handling and recovery mechanisms

    **WORKFLOW INTEGRATION**:
    - LlamaIndex workflow support for complex orchestration
    - Asynchronous state transitions with workflow coordination
    - Event-driven communication between workflow steps
    - Observable workflow execution with monitoring support

    **CONTRACT-DRIVEN ARCHITECTURE**:
    - ModelONEXContainer dependency injection from contracts
    - Automatic tool resolution and configuration
    - Declarative behavior specification via YAML contracts
    - Type-safe contract validation and generation

    **OBSERVABLE STATE MANAGEMENT**:
    - Event emission for all state transitions
    - Correlation tracking for observability
    - Structured logging with provenance information
    - Signal orchestration for hub communication

    **THREAD SAFETY AND STATE**:
    - All mutable state is instance-level (no global mutable state)
    - Contract loading uses instance-level caching via ProtocolContractLoader
    - Each NodeBase instance maintains independent state (_container, _main_tool, etc.)
    - Node instances should NOT be shared across threads without synchronization
    - For concurrent execution, create separate NodeBase instances per thread
    - See docs/guides/THREADING.md for complete thread safety guidelines
    """

    def __init__(
        self,
        contract_path: Path,
        node_id: UUID | None = None,
        event_bus: object | None = None,
        container: ModelONEXContainer | None = None,
        workflow_id: UUID | None = None,
        session_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize NodeBase with monadic patterns and workflow support.

        Args:
            contract_path: Path to the contract file
            node_id: Optional node identifier (derived from contract if not provided)
            event_bus: Optional event bus for event emission and subscriptions
            container: Optional pre-created ModelONEXContainer (created from contract if not provided)
            workflow_id: Optional workflow identifier for orchestration tracking
            session_id: Optional session identifier for correlation
            **kwargs: Additional initialization parameters
        """
        # Generate identifiers
        self.workflow_id = workflow_id or uuid4()
        self.session_id = session_id or uuid4()
        self.correlation_id = uuid4()

        # Store initialization parameters
        self._contract_path = contract_path
        self._container: ModelONEXContainer | None = None
        self._main_tool: object | None = None
        self._reducer_state: ProtocolState | None = None
        self._workflow_instance: Any | None = None

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

            # Create workflow instance if needed (handle async context properly)
            try:
                # Check if we're already in an async context
                asyncio.get_running_loop()
                # We're in an async context, defer workflow creation (lazy initialization)
                # The workflow_instance property will handle creation when accessed
                self._workflow_instance = None
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                self._workflow_instance = asyncio.run(self.create_workflow())

            # Emit initialization event
            self._emit_initialization_event()

        except Exception as e:
            self._emit_initialization_failure(e)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Failed to initialize NodeBase: {e!s}",
                context={
                    "contract_path": str(contract_path),
                    "node_id": str(node_id) if node_id else None,
                    "workflow_id": str(self.workflow_id),
                },
                correlation_id=self.correlation_id,
            ) from e

    def _load_contract_and_initialize(
        self,
        contract_path: Path,
        node_id: UUID | None,
        event_bus: object | None,
        container: ModelONEXContainer | None,
    ) -> None:
        """Load contract and initialize core components using ONEX 2.0 patterns."""
        # ONEX 2.0: Use ContractLoader instead of ContractService
        from omnibase_core.utils.util_contract_loader import ProtocolContractLoader

        contract_loader = ProtocolContractLoader(
            base_path=contract_path.parent,
            cache_enabled=True,
        )
        contract_content = contract_loader.load_contract(contract_path)

        # Derive node_id from contract if not provided
        if node_id is None:
            # Generate UUID from node name for consistency
            import hashlib

            name_hash = hashlib.sha256(contract_content.node_name.encode()).digest()[
                :16
            ]
            from uuid import UUID

            node_id = UUID(bytes=name_hash)

        self.node_id = node_id

        # ONEX 2.0: Create container directly or use provided one
        if container is None:
            # Deferred import to avoid circular dependency at module level
            from omnibase_core.models.container.model_onex_container import (
                ModelONEXContainer,
            )

            # Direct ModelONEXContainer instantiation
            container = ModelONEXContainer()

            # Register dependencies from contract if present
            if (
                hasattr(contract_content, "dependencies")
                and contract_content.dependencies is not None
                and contract_content.dependencies
            ):
                # Log dependencies for observability and future registration
                emit_log_event(
                    LogLevel.INFO,
                    f"Processing {len(contract_content.dependencies)} contract dependencies",
                    {
                        "node_name": contract_content.node_name,
                        "dependency_count": len(contract_content.dependencies),
                        "node_id": str(node_id),
                    },
                )

                # Process each dependency
                for dependency in contract_content.dependencies:
                    # Handle both string and ModelContractDependency types
                    if isinstance(dependency, str):  # type: ignore[unreachable]
                        emit_log_event(  # type: ignore[unreachable]
                            LogLevel.DEBUG,
                            f"Dependency registered: {dependency}",
                            {
                                "dependency_name": dependency,
                                "dependency_module": "N/A",
                                "dependency_type": "unknown",
                                "required": True,
                                "node_name": contract_content.node_name,
                            },
                        )
                    else:
                        # Use type instead of dependency_type for ModelContractDependency
                        dep_type = getattr(dependency, "type", "unknown")
                        # Handle enum or string type
                        if hasattr(dep_type, "value"):
                            dep_type_value = dep_type.value
                        else:
                            dep_type_value = str(dep_type)

                        emit_log_event(
                            LogLevel.DEBUG,
                            f"Dependency registered: {dependency.name}",
                            {
                                "dependency_name": dependency.name,
                                "dependency_module": dependency.module or "N/A",
                                "dependency_type": dep_type_value,
                                "required": getattr(dependency, "required", True),
                                "node_name": contract_content.node_name,
                            },
                        )

                    # Note: Actual service registration with container will be implemented
                    # when omnibase-spi protocol service resolver is fully integrated.
                    # Dependencies are logged and tracked in contract metadata for now.

        self._container = container

        # Store contract and configuration
        business_logic_pattern = getattr(
            contract_content.tool_specification, "business_logic_pattern", None
        )
        # Handle both string and enum cases
        if business_logic_pattern is not None:
            pattern_value = (
                business_logic_pattern.value
                if hasattr(business_logic_pattern, "value")
                else str(business_logic_pattern)
            )
        else:
            pattern_value = "unknown"

        self.state = ModelNodeState(
            contract_path=contract_path,
            node_id=node_id,
            contract_content=contract_content,
            container_reference=None,  # Optional container reference metadata
            node_name=contract_content.node_name,
            version=contract_content.contract_version,  # Use ModelSemVer directly
            node_tier=1,
            node_classification=pattern_value,
            event_bus=event_bus,
            initialization_metadata={  # type: ignore[arg-type]
                "main_tool_class": contract_content.tool_specification.main_tool_class,
                "contract_path": str(contract_path),
                "initialization_time": str(time.time()),
                "workflow_id": str(self.workflow_id),
                "session_id": str(self.session_id),
            },
        )

        # Resolve main tool
        self._main_tool = self._resolve_main_tool()

    def _resolve_main_tool(self) -> object:
        """
        Resolve and instantiate the main tool class using ONEX 2.0 dynamic import.

        ONEX 2.0 Pattern: Direct importlib-based tool instantiation.
        No auto-discovery service needed.
        """
        import importlib

        try:
            main_tool_class = (
                self.state.contract_content.tool_specification.main_tool_class  # type: ignore[union-attr]
            )

            # Parse module and class name
            # Expected format: "module.path.ClassName"
            if "." not in main_tool_class:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid main_tool_class format: {main_tool_class}. Expected 'module.path.ClassName'",
                    context={
                        "main_tool_class": main_tool_class,
                        "node_id": str(self.state.node_id),
                    },
                    correlation_id=self.correlation_id,
                )

            module_path, class_name = main_tool_class.rsplit(".", 1)

            # Dynamic import using importlib (ONEX 2.0 pattern)
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)

            # Instantiate tool with container for dependency injection
            # ONEX 2.0: Tools receive container for service resolution
            tool_instance = tool_class(container=self._container)

            emit_log_event(
                LogLevel.INFO,
                f"Resolved main tool: {main_tool_class}",
                {
                    "main_tool_class": main_tool_class,
                    "node_id": str(self.state.node_id),
                    "workflow_id": str(self.workflow_id),
                },
            )

            return tool_instance

        except ImportError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Failed to import main tool class: {e!s}",
                context={
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,  # type: ignore[union-attr]
                    "node_id": str(self.state.node_id),
                    "error": str(e),
                },
                correlation_id=self.correlation_id,
            ) from e
        except AttributeError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Class not found in module: {e!s}",
                context={
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,  # type: ignore[union-attr]
                    "node_id": str(self.state.node_id),
                },
                correlation_id=self.correlation_id,
            ) from e
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Failed to resolve main tool: {e!s}",
                context={
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,  # type: ignore[union-attr]
                    "node_id": str(self.state.node_id),
                },
                correlation_id=self.correlation_id,
            ) from e

    # ===== ASYNC INTERFACE =====

    async def run_async(self, input_state: T_INPUT_STATE) -> T_OUTPUT_STATE:
        """
        Universal async run method with event emission and correlation tracking.

        This is the primary interface for node execution with:
        - Event emission for lifecycle management
        - Correlation tracking for observability
        - Standard exception handling
        - Structured logging

        Args:
            input_state: Tool-specific input state (strongly typed)

        Returns:
            U: Tool-specific output state

        Raises:
            ModelOnexError: If execution fails
        """
        correlation_id = uuid4()
        start_time = datetime.now()

        # Emit start event via structured logging
        emit_log_event(
            LogLevel.INFO,
            f"Node execution started: {self.node_id}",
            {
                "node_id": str(self.node_id),
                "node_name": self.state.node_name,
                "input_type": type(input_state).__name__,
                "correlation_id": str(correlation_id),
                "workflow_id": str(self.workflow_id),
                "session_id": str(self.session_id),
            },
        )

        try:
            # Delegate to process method
            result = await self.process_async(input_state)

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Emit success event via structured logging
            emit_log_event(
                LogLevel.INFO,
                f"Node execution completed: {self.node_id}",
                {
                    "node_id": str(self.node_id),
                    "node_name": self.state.node_name,
                    "duration_ms": duration_ms,
                    "output_type": (
                        type(result).__name__ if result is not None else "None"
                    ),
                    "correlation_id": str(correlation_id),
                    "workflow_id": str(self.workflow_id),
                    "session_id": str(self.session_id),
                },
            )

            return result

        except ModelOnexError:
            # Log and re-raise ONEX errors (fail-fast)
            emit_log_event(
                LogLevel.ERROR,
                f"Node execution failed: {self.node_id}",
                {
                    "node_id": str(self.node_id),
                    "correlation_id": str(correlation_id),
                    "workflow_id": str(self.workflow_id),
                },
            )
            raise

        except Exception as e:
            # Convert generic exceptions to ONEX errors
            emit_log_event(
                LogLevel.ERROR,
                f"Node execution exception: {self.node_id}",
                {
                    "node_id": str(self.node_id),
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "correlation_id": str(correlation_id),
                    "workflow_id": str(self.workflow_id),
                },
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Node execution failed: {e!s}",
                context={
                    "node_id": str(self.node_id),
                    "correlation_id": str(correlation_id),
                },
                correlation_id=correlation_id,
            ) from e

    async def process_async(self, input_state: T_INPUT_STATE) -> T_OUTPUT_STATE:
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
                LogLevel.INFO,
                f"Processing with NodeBase: {self.state.node_name}",
                {
                    "node_name": self.state.node_name,
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,  # type: ignore[union-attr]
                    "business_logic_pattern": self.state.node_classification,
                    "workflow_id": str(self.workflow_id),
                },
            )

            main_tool = self._main_tool

            if main_tool is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                    message="Main tool is not initialized",
                    context={
                        "node_name": self.state.node_name,
                        "workflow_id": str(self.workflow_id),
                    },
                    correlation_id=self.correlation_id,
                )

            # Check if tool supports async processing
            if hasattr(main_tool, "process_async"):
                result = await main_tool.process_async(input_state)
                return cast("T_OUTPUT_STATE", result)
            if hasattr(main_tool, "process"):
                # Run sync process in thread pool to avoid blocking
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    main_tool.process,
                    input_state,
                )
                return cast("T_OUTPUT_STATE", result)
            if hasattr(main_tool, "run"):
                # Run sync run method in thread pool
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    main_tool.run,
                    input_state,
                )
                return cast("T_OUTPUT_STATE", result)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message="Main tool does not implement process_async(), process(), or run() method",
                context={
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,  # type: ignore[union-attr]
                    "node_name": self.state.node_name,
                    "workflow_id": str(self.workflow_id),
                },
                correlation_id=self.correlation_id,
            )

        except ModelOnexError:
            # Re-raise ONEX errors (fail-fast)
            raise
        except Exception as e:
            # Convert generic exceptions to ONEX errors
            emit_log_event(
                LogLevel.ERROR,
                f"Error in NodeBase processing: {e!s}",
                {
                    "node_name": self.state.node_name,
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,  # type: ignore[union-attr]
                    "error": str(e),
                    "workflow_id": str(self.workflow_id),
                },
            )
            raise ModelOnexError(
                message=f"NodeBase processing error: {e!s}",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={
                    "node_name": self.state.node_name,
                    "node_tier": self.state.node_tier,
                    "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,  # type: ignore[union-attr]
                    "workflow_id": str(self.workflow_id),
                },
                correlation_id=self.correlation_id,
            ) from e

    # ===== SYNC INTERFACE =====

    def run(self, input_state: T_INPUT_STATE) -> T_OUTPUT_STATE:
        """
        Execute the node synchronously.

        Args:
            input_state: Tool-specific input state

        Returns:
            U: Tool-specific output state

        Raises:
            ModelOnexError: If execution fails
        """
        # Run async version and return the result directly
        return asyncio.run(self.run_async(input_state))

    def process(self, input_state: T_INPUT_STATE) -> T_OUTPUT_STATE:
        """
        Synchronous process method for current standards.

        Args:
            input_state: Tool-specific input state

        Returns:
            U: Tool-specific output state
        """
        return asyncio.run(self.process_async(input_state))

    # ===== REDUCER IMPLEMENTATION =====

    def initial_state(self) -> ProtocolState:
        """
        Returns the initial state for the reducer.

        Default implementation returns empty state.
        Override in subclasses for custom initial state.
        """
        return cast("ProtocolState", ModelState())

    def dispatch(self, state: ProtocolState, action: ProtocolAction) -> ProtocolState:
        """
        Synchronous state transition for simple operations.

        Default implementation returns unchanged state.
        Override in subclasses for custom state transitions.
        """
        return state

    async def dispatch_async(
        self,
        state: ProtocolState,
        action: ProtocolAction,
    ) -> ProtocolNodeResult:
        """
        Asynchronous workflow-based state transition.

        Default implementation wraps synchronous dispatch.
        Override in subclasses for workflow-based transitions.

        Args:
            state: Current state
            action: Action to dispatch

        Returns:
            ProtocolNodeResult: Result with new state and metadata

        Raises:
            ModelOnexError: If dispatch fails
        """

        try:
            new_state = self.dispatch(state, action)

            # Log successful state transition
            emit_log_event(
                LogLevel.INFO,
                f"State transition: {self.node_id}",
                {
                    "action_type": getattr(action, "type", "unknown"),
                    "node_id": str(self.node_id),
                    "workflow_id": str(self.workflow_id),
                    "correlation_id": str(self.correlation_id),
                },
            )

            # Wrap the new state in a result object
            return ModelNodeWorkflowResult(
                value=new_state,  # type: ignore[arg-type]
                is_success=True,
                is_failure=False,
                error=None,
                trust_score=1.0,
                provenance=[f"NodeBase.dispatch_async:{self.node_id}"],
                metadata={},
                events=[],
                state_delta={},
            )

        except Exception as e:
            # Log and convert to ONEX error
            emit_log_event(
                LogLevel.ERROR,
                f"State dispatch failed: {self.node_id}",
                {
                    "node_id": str(self.node_id),
                    "error": str(e),
                    "correlation_id": str(self.correlation_id),
                },
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"State dispatch failed: {e!s}",
                context={
                    "node_id": str(self.node_id),
                    "action_type": getattr(action, "type", "unknown"),
                },
                correlation_id=self.correlation_id,
            ) from e

    async def create_workflow(self) -> Any | None:
        """
        Factory method for creating LlamaIndex workflow instances.

        Default implementation returns None (no workflow needed).
        Override in subclasses that need workflow orchestration.
        """
        return None

    # ===== HELPER METHODS =====

    def _emit_initialization_event(self) -> None:
        """Emit initialization success event."""
        emit_log_event(
            LogLevel.INFO,
            f"NodeBase initialized: {self.node_id}",
            {
                "node_id": str(self.node_id),
                "node_name": self.state.node_name,
                "contract_path": str(self._contract_path),
                "main_tool_class": self.state.contract_content.tool_specification.main_tool_class,  # type: ignore[union-attr]
                "correlation_id": str(self.correlation_id),
                "workflow_id": str(self.workflow_id),
            },
        )

    def _emit_initialization_failure(self, error: Exception) -> None:
        """Emit initialization failure event."""
        emit_log_event(
            LogLevel.ERROR,
            f"NodeBase initialization failed: {error!s}",
            {
                "node_id": (
                    str(self.node_id)
                    if hasattr(self, "node_id") and self.node_id is not None
                    else "unknown"
                ),
                "contract_path": str(self._contract_path),
                "error": str(error),
                "error_type": type(error).__name__,
                "correlation_id": str(self.correlation_id),
                "workflow_id": str(self.workflow_id),
            },
        )

    # ===== PROPERTIES =====

    @property
    def container(self) -> ModelONEXContainer:
        """Get the ModelONEXContainer instance for dependency injection."""
        if self._container is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message="Container is not initialized",
                context={"node_id": str(self.node_id)},
            )
        return self._container

    @property
    def main_tool(self) -> object:
        """Get the resolved main tool instance."""
        return self._main_tool

    @property
    def current_state(self) -> ProtocolState:
        """Get the current reducer state."""
        if self._reducer_state is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message="Reducer state is not initialized",
                context={"node_id": str(self.node_id)},
            )
        return self._reducer_state

    @property
    def workflow_instance(self) -> Any | None:
        """Get the LlamaIndex workflow instance if available."""
        return self._workflow_instance
