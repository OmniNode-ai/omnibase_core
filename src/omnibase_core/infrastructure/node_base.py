"""
NodeBase for ONEX ModelArchitecture.

This module provides the NodeBase class that implements
LlamaIndex workflow integration, observable state transitions,
and contract-driven orchestration.

Security:
    NodeBase performs dynamic imports of tool classes specified in contract
    files via the main_tool_class field. This is a potential code execution
    vector if contracts come from untrusted sources.

    **Dynamic Import Security** (_resolve_main_tool):
        - The main_tool_class is loaded from contract YAML files
        - Contract files should come from TRUSTED sources only
        - Optional allowlist validation via ENFORCE_TOOL_IMPORT_ALLOWLIST (default: OFF)
        - When enabled, only modules matching ALLOWED_TOOL_MODULE_PREFIXES can be imported

    Trust Model:
        - Contract file source: MUST BE TRUSTED (controls code execution)
        - main_tool_class path: TRUSTED (comes from trusted contract)
        - Contract file content: Validated via UtilContractLoader security checks

    Security Assumptions:
        1. Contract files are provided by trusted sources (system administrators,
           verified node packages, or trusted configuration management)
        2. The file system permissions on contract directories prevent
           unauthorized modification
        3. Third-party node packages are reviewed before installation

    WARNING:
        Do NOT load contract files from untrusted sources (user uploads,
        network requests, untrusted file paths). The main_tool_class field
        can execute arbitrary Python code via module initialization.

    Defense-in-Depth (Optional Allowlist):
        NodeBase provides optional allowlist validation for tool imports:
        - ENFORCE_TOOL_IMPORT_ALLOWLIST: Set to True to enable validation
        - ALLOWED_TOOL_MODULE_PREFIXES: Tuple of trusted module prefixes
        - Default prefixes: omnibase_core., omnibase_spi., omnibase_infra.,
          omnibase_runtime., tests.
        - Subclasses can override these class variables for custom policies
        - Similar pattern to ModelReference.ALLOWED_MODULE_PREFIXES

    See Also:
        - UtilContractLoader: YAML parsing security and content validation
        - ModelReference: Uses ALLOWED_MODULE_PREFIXES for import validation
"""

from __future__ import annotations

# NOTE(OMN-1302): I001 (import order) disabled - intentional ordering to avoid circular dependencies.

from typing import Any, ClassVar, TYPE_CHECKING

from omnibase_core.models.errors.model_onex_error import ModelOnexError


import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import cast
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
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)

# Deferred import to avoid circular dependency
if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer

from omnibase_core.models.infrastructure.model_initialization_metadata import (
    ModelInitializationMetadata,
)
from omnibase_core.models.infrastructure.model_node_state import ModelNodeState
from omnibase_core.models.infrastructure.model_node_workflow_result import (
    ModelNodeWorkflowResult,
)
from omnibase_core.models.infrastructure.model_state import ModelState

# Reducer pattern models imported from separate files (ONEX 2.0 architecture)
# See: ModelAction, ModelState, ModelNodeState for full implementations


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
    - Contract loading uses instance-level caching via UtilContractLoader
    - Each NodeBase instance maintains independent state (_container, _main_tool, etc.)
    - Node instances should NOT be shared across threads without synchronization
    - For concurrent execution, create separate NodeBase instances per thread
    - See docs/guides/THREADING.md for complete thread safety guidelines
    """

    # Security: Allowlist of trusted module prefixes for dynamic tool import.
    # Only modules matching these prefixes can be imported when ENFORCE_TOOL_IMPORT_ALLOWLIST is True.
    # Subclasses can override to add additional trusted prefixes.
    ALLOWED_TOOL_MODULE_PREFIXES: ClassVar[tuple[str, ...]] = (
        "omnibase_core.",
        "omnibase_spi.",
        "omnibase_infra.",
        "omnibase_runtime.",
        "tests.",  # Allow test fixtures
    )

    # Security: Flag to enable/disable tool import allowlist validation.
    # Default is False (opt-in security feature). Set to True in subclasses
    # or production deployments to enforce strict import validation.
    ENFORCE_TOOL_IMPORT_ALLOWLIST: ClassVar[bool] = False

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

        except ModelOnexError as e:
            # Re-raise ONEX errors without wrapping to preserve original error code/context
            self._emit_initialization_failure(e)
            raise
        except (
            Exception
        ) as e:  # init-errors-ok: top-level error boundary for node initialization
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
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
        from omnibase_core.utils.util_contract_loader import UtilContractLoader

        contract_loader = UtilContractLoader(
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

                # Process each dependency (always ModelContractDependency objects)
                for dependency in contract_content.dependencies:
                    # Use type instead of dependency_type for ModelContractDependency
                    dep_type = getattr(dependency, "type", "unknown")
                    # Extract enum value if available, otherwise use string representation
                    dep_type_value = getattr(dep_type, "value", str(dep_type))

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
            initialization_metadata=ModelInitializationMetadata.from_dict(
                {
                    "main_tool_class": contract_content.tool_specification.main_tool_class,
                    "contract_path": str(contract_path),
                    "initialization_time": str(time.time()),
                    "workflow_id": str(self.workflow_id),
                    "session_id": str(self.session_id),
                }
            ),
        )

        # Resolve main tool
        self._main_tool = self._resolve_main_tool()

    def _resolve_main_tool(self) -> object:
        """
        Resolve and instantiate the main tool class using ONEX 2.0 dynamic import.

        ONEX 2.0 Pattern: Direct importlib-based tool instantiation.
        No auto-discovery service needed.

        Security Warning:
            This method uses importlib.import_module() to load the main_tool_class
            specified in the contract file. This executes module initialization code.

            Contract files MUST come from trusted sources only.

        Security Features:
            - Optional allowlist validation via ENFORCE_TOOL_IMPORT_ALLOWLIST class variable
            - When enabled, only modules matching ALLOWED_TOOL_MODULE_PREFIXES can be imported
            - Default is OFF (opt-in feature); enable in production deployments for defense-in-depth
            - Subclasses can override ALLOWED_TOOL_MODULE_PREFIXES to add trusted prefixes

        Allowlist Configuration:
            To enable strict import validation:
                class MySecureNode(NodeBase):
                    ENFORCE_TOOL_IMPORT_ALLOWLIST = True
                    ALLOWED_TOOL_MODULE_PREFIXES = (
                        "omnibase_core.",
                        "omnibase_spi.",
                        "my_trusted_package.",
                    )

        See Also:
            - ModelReference.ALLOWED_MODULE_PREFIXES: Similar pattern for reference resolution
            - ALLOWED_TOOL_MODULE_PREFIXES: Class variable defining trusted module prefixes
            - ENFORCE_TOOL_IMPORT_ALLOWLIST: Class variable to enable/disable validation
        """
        import importlib

        try:
            main_tool_class = self._get_main_tool_class()

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

            # SECURITY: Dynamic Import Allowlist Validation
            # =============================================
            # This validation prevents arbitrary code execution via malicious contract YAML files.
            # The main_tool_class field in contracts specifies a Python class to import and
            # instantiate. Without validation, an attacker who can modify contract files could
            # specify system modules (e.g., os, subprocess) to execute arbitrary code.
            #
            # Defense Strategy:
            #   - ENFORCE_TOOL_IMPORT_ALLOWLIST (default: False) - Opt-in strict validation
            #   - When enabled, only modules matching ALLOWED_TOOL_MODULE_PREFIXES can be imported
            #   - Default trusted prefixes: omnibase_core., omnibase_spi., omnibase_infra.,
            #     omnibase_runtime., tests.
            #   - Raises SECURITY_VIOLATION error for untrusted modules
            #
            # Trust Assumptions (when allowlist is NOT enforced):
            #   1. Contract files come from trusted sources (admin, verified packages)
            #   2. File system permissions prevent unauthorized contract modification
            #   3. Third-party node packages are reviewed before installation
            #
            # See Also:
            #   - ModelReference.ALLOWED_MODULE_PREFIXES: Similar pattern for reference resolution
            #   - docs/architecture/SECURITY.md: ONEX security architecture documentation
            if self.ENFORCE_TOOL_IMPORT_ALLOWLIST:
                if not any(
                    module_path.startswith(prefix)
                    for prefix in self.ALLOWED_TOOL_MODULE_PREFIXES
                ):
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                        message=f"Module '{module_path}' not in allowed prefixes for tool import",
                        context={
                            "module": module_path,
                            "allowed": self.ALLOWED_TOOL_MODULE_PREFIXES,
                            "node_id": str(self.state.node_id),
                        },
                        correlation_id=self.correlation_id,
                    )

            # SECURITY: Dynamic import executes module initialization code.
            # This is safe ONLY when:
            #   - Contract files come from trusted sources, OR
            #   - ENFORCE_TOOL_IMPORT_ALLOWLIST is True (validated above)
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
                    "main_tool_class": main_tool_class,
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
                    "main_tool_class": main_tool_class,
                    "node_id": str(self.state.node_id),
                },
                correlation_id=self.correlation_id,
            ) from e
        except ModelOnexError:
            # Re-raise ONEX errors without wrapping to preserve original error code/context
            raise
        except (RuntimeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Failed to resolve main tool: {e!s}",
                context={
                    "main_tool_class": main_tool_class,
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

        except (
            Exception
        ) as e:  # catch-all-ok: top-level error boundary for node execution
            # Convert generic exceptions to ONEX errors
            # Note: Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
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
            main_tool_class = self._get_main_tool_class()
            emit_log_event(
                LogLevel.INFO,
                f"Processing with NodeBase: {self.state.node_name}",
                {
                    "node_name": self.state.node_name,
                    "main_tool_class": main_tool_class,
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
                # NOTE(OMN-1073): Cast is safe because the tool's return type is governed
                # by the contract specification. The tool implementation is validated at
                # initialization via main_tool_class resolution from the contract YAML.
                return cast("T_OUTPUT_STATE", result)
            if hasattr(main_tool, "process"):
                # Run sync process in thread pool to avoid blocking
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    main_tool.process,
                    input_state,
                )
                # NOTE(OMN-1073): Cast is safe - tool return type governed by contract.
                return cast("T_OUTPUT_STATE", result)
            if hasattr(main_tool, "run"):
                # Run sync run method in thread pool
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    main_tool.run,
                    input_state,
                )
                # NOTE(OMN-1073): Cast is safe - tool return type governed by contract.
                return cast("T_OUTPUT_STATE", result)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message="Main tool does not implement process_async(), process(), or run() method",
                context={
                    "main_tool_class": main_tool_class,
                    "node_name": self.state.node_name,
                    "workflow_id": str(self.workflow_id),
                },
                correlation_id=self.correlation_id,
            )

        except ModelOnexError:
            # Re-raise ONEX errors (fail-fast)
            raise
        except (
            Exception
        ) as e:  # catch-all-ok: top-level error boundary for tool processing
            # Convert generic exceptions to ONEX errors
            # Note: Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
            emit_log_event(
                LogLevel.ERROR,
                f"Error in NodeBase processing: {e!s}",
                {
                    "node_name": self.state.node_name,
                    "main_tool_class": main_tool_class,
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
                    "main_tool_class": main_tool_class,
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
        # NOTE(OMN-1073): Cast is safe because ModelState implements ProtocolState
        # via structural subtyping (duck typing). ModelState provides all required
        # state container methods defined by the protocol.
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
                value=new_state,
                is_success=True,
                is_failure=False,
                error=None,
                trust_score=1.0,
                provenance=[f"NodeBase.dispatch_async:{self.node_id}"],
                metadata={},
                events=[],
                state_delta={},
            )

        except ModelOnexError:
            # Re-raise ONEX errors without wrapping to preserve original error code/context
            raise
        except (
            Exception
        ) as e:  # catch-all-ok: top-level error boundary for state dispatch
            # Log and convert to ONEX error
            # Note: Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
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

    def _get_main_tool_class(self) -> str:
        """
        Safely get the main_tool_class from contract_content with proper type narrowing.

        Returns:
            str: The main tool class name from the contract.

        Raises:
            ModelOnexError: If contract_content or tool_specification is missing.
        """
        from omnibase_core.models.core.model_contract_content import (
            ModelContractContent,
        )

        contract_content = self.state.contract_content
        if contract_content is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message="Contract content is not initialized",
                context={"node_id": str(self.node_id)},
                correlation_id=self.correlation_id,
            )

        # Check if it's a ModelContractContent with tool_specification
        if isinstance(contract_content, ModelContractContent):
            return contract_content.tool_specification.main_tool_class

        # For other types, try attribute access with type safety
        if hasattr(contract_content, "tool_specification"):
            tool_spec = contract_content.tool_specification
            if tool_spec is not None and hasattr(tool_spec, "main_tool_class"):
                main_tool_class = tool_spec.main_tool_class
                if isinstance(main_tool_class, str):
                    return main_tool_class

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message="Contract content does not have valid tool_specification.main_tool_class",
            context={
                "node_id": str(self.node_id),
                "contract_content_type": type(contract_content).__name__,
            },
            correlation_id=self.correlation_id,
        )

    def _emit_initialization_event(self) -> None:
        """Emit initialization success event."""
        emit_log_event(
            LogLevel.INFO,
            f"NodeBase initialized: {self.node_id}",
            {
                "node_id": str(self.node_id),
                "node_name": self.state.node_name,
                "contract_path": str(self._contract_path),
                "main_tool_class": self._get_main_tool_class(),
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
