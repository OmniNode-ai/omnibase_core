"""
Hybrid Execution Mixin for ONEX Tool Nodes.

Provides automatic selection between direct execution and workflow modes.
Supports LlamaIndex workflow orchestration for complex operations.
"""

import json
from typing import Generic, Optional, TypeVar

from omnibase.enums.enum_log_level import LogLevelEnum

from omnibase_core.constants import constants_contract_fields as cf
from omnibase_core.core.core_structured_logging import \
    emit_log_event_sync as emit_log_event
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.model.core.model_workflow_metrics import \
    ModelWorkflowMetrics

# Type variables for input/output states
InputStateT = TypeVar("InputStateT")
OutputStateT = TypeVar("OutputStateT")


class ExecutionMode:
    """Execution mode constants."""

    DIRECT = "direct"
    WORKFLOW = "workflow"
    ORCHESTRATED = "orchestrated"
    AUTO = "auto"


class MixinHybridExecution(Generic[InputStateT, OutputStateT]):
    """
    Mixin that provides hybrid execution capabilities to tool nodes.

    Features:
    - Automatic mode selection based on complexity
    - Direct execution for simple operations
    - Workflow execution for complex multi-step operations
    - Hub orchestration for event-driven execution

    Usage:
        class MyTool(MixinHybridExecution, MixinContractMetadata, ProtocolReducer):
            def determine_execution_mode(self, input_state) -> str:
                # Override to customize mode selection
                if input_state.operation_count > 10:
                    return ExecutionMode.WORKFLOW
                return ExecutionMode.DIRECT

            def process(self, input_state):
                # Direct execution logic
                return output

            def create_workflow(self, input_state):
                # Create LlamaIndex workflow
                return MyWorkflow(input_state)
    """

    def __init__(self, **kwargs):
        """Initialize the hybrid execution mixin."""
        super().__init__(**kwargs)

        self._execution_mode: Optional[str] = None
        self._workflow_metrics: Optional[ModelWorkflowMetrics] = None

        emit_log_event(
            LogLevelEnum.DEBUG,
            "🏗️ MIXIN_INIT: Initializing MixinHybridExecution",
            {"mixin_class": self.__class__.__name__},
        )

    def process(self, input_state: InputStateT) -> OutputStateT:
        """Direct execution process method."""
        raise NotImplementedError("Tool must implement process method")

    def determine_execution_mode(self, input_state: InputStateT) -> str:
        """
        Determine execution mode based on input complexity.

        Override this method to customize mode selection logic.

        Args:
            input_state: Input state to analyze

        Returns:
            Execution mode (direct, workflow, orchestrated)
        """
        # Check contract for supported modes
        supported_modes = self._get_supported_modes()

        # Default logic - can be overridden
        complexity_score = self._calculate_complexity(input_state)

        emit_log_event(
            LogLevelEnum.DEBUG,
            "🔍 MODE_SELECTION: Calculating execution mode",
            {"complexity_score": complexity_score, "supported_modes": supported_modes},
        )

        # Select mode based on complexity
        if complexity_score > 0.7 and ExecutionMode.WORKFLOW in supported_modes:
            return ExecutionMode.WORKFLOW
        elif complexity_score > 0.5 and ExecutionMode.ORCHESTRATED in supported_modes:
            return ExecutionMode.ORCHESTRATED
        else:
            return ExecutionMode.DIRECT

    def execute(
        self, input_state: InputStateT, mode: Optional[str] = None
    ) -> OutputStateT:
        """
        Execute the tool with automatic mode selection.

        Args:
            input_state: Input state for processing
            mode: Override execution mode (optional)

        Returns:
            Output state from processing
        """
        # Determine execution mode
        if mode and mode != ExecutionMode.AUTO:
            self._execution_mode = mode
        else:
            self._execution_mode = self.determine_execution_mode(input_state)

        emit_log_event(
            LogLevelEnum.INFO,
            f"🚀 HYBRID_EXECUTION: Starting execution in {self._execution_mode} mode",
            {
                "node_class": self.__class__.__name__,
                "execution_mode": self._execution_mode,
                "manual_override": mode is not None,
            },
        )

        # Execute based on mode
        if self._execution_mode == ExecutionMode.DIRECT:
            return self._execute_direct(input_state)
        elif self._execution_mode == ExecutionMode.WORKFLOW:
            return self._execute_workflow(input_state)
        elif self._execution_mode == ExecutionMode.ORCHESTRATED:
            return self._execute_orchestrated(input_state)
        else:
            # Fallback to direct
            emit_log_event(
                LogLevelEnum.WARNING,
                f"Unknown execution mode '{self._execution_mode}', falling back to direct",
                {"mode": self._execution_mode},
            )
            return self._execute_direct(input_state)

    def _execute_direct(self, input_state: InputStateT) -> OutputStateT:
        """Execute in direct mode."""
        emit_log_event(
            LogLevelEnum.DEBUG,
            "⚡ DIRECT_EXECUTION: Starting direct processing",
            {"node_class": self.__class__.__name__},
        )

        # Simple direct execution
        result = self.process(input_state)

        emit_log_event(
            LogLevelEnum.INFO,
            "✅ DIRECT_EXECUTION: Processing completed",
            {
                "node_class": self.__class__.__name__,
                "output_type": type(result).__name__,
            },
        )

        return result

    def _execute_workflow(self, input_state: InputStateT) -> OutputStateT:
        """Execute in workflow mode using LlamaIndex."""
        emit_log_event(
            LogLevelEnum.INFO,
            "🔄 WORKFLOW_EXECUTION: Starting workflow processing",
            {"node_class": self.__class__.__name__},
        )

        try:
            # Check if workflow creation method exists
            if not hasattr(self, "create_workflow"):
                emit_log_event(
                    LogLevelEnum.WARNING,
                    "No create_workflow method found, falling back to direct execution",
                    {"node_class": self.__class__.__name__},
                )
                return self._execute_direct(input_state)

            # Import LlamaIndex workflow components
            try:
                from llama_index.core.workflow import (Event, StartEvent,
                                                       StopEvent, Workflow)
            except ImportError as e:
                emit_log_event(
                    LogLevelEnum.ERROR,
                    f"LlamaIndex not available: {e}",
                    {"error": str(e)},
                )
                # Fallback to direct execution
                return self._execute_direct(input_state)

            # Create workflow instance
            workflow = self.create_workflow(input_state)

            # Execute workflow
            import asyncio
            import time

            start_time = time.time()

            # Run workflow
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(workflow.run(input_data=input_state))
            finally:
                loop.close()

            # Record metrics
            end_time = time.time()
            self._workflow_metrics = ModelWorkflowMetrics(
                workflow_name=workflow.__class__.__name__,
                execution_time=end_time - start_time,
                steps_executed=getattr(workflow, "_steps_executed", 0),
                status=EnumOnexStatus.HEALTHY,
            )

            emit_log_event(
                LogLevelEnum.INFO,
                "✅ WORKFLOW_EXECUTION: Workflow completed successfully",
                {
                    "node_class": self.__class__.__name__,
                    "workflow_name": workflow.__class__.__name__,
                    "execution_time": self._workflow_metrics.execution_time,
                },
            )

            return result

        except Exception as e:
            emit_log_event(
                LogLevelEnum.ERROR,
                f"❌ WORKFLOW_EXECUTION: Workflow failed: {e}",
                {"node_class": self.__class__.__name__, "error": str(e)},
            )
            # Fallback to direct execution
            return self._execute_direct(input_state)

    def _execute_orchestrated(self, input_state: InputStateT) -> OutputStateT:
        """Execute in orchestrated mode via Generation Hub."""
        emit_log_event(
            LogLevelEnum.INFO,
            "🎭 ORCHESTRATED_EXECUTION: Starting hub-orchestrated processing",
            {"node_class": self.__class__.__name__},
        )

        # This would integrate with Generation Hub
        # For now, fallback to workflow mode
        emit_log_event(
            LogLevelEnum.WARNING,
            "Orchestrated mode not yet implemented, using workflow mode",
            {"node_class": self.__class__.__name__},
        )

        return self._execute_workflow(input_state)

    def _calculate_complexity(self, input_state: InputStateT) -> float:
        """
        Calculate complexity score for input state.

        Override this method to provide custom complexity calculation.

        Args:
            input_state: Input state to analyze

        Returns:
            Complexity score between 0.0 and 1.0
        """
        # Default complexity calculation
        score = 0.0

        # Check input size
        if hasattr(input_state, "model_dump"):
            data_size = len(json.dumps(input_state.model_dump()))
            if data_size > 10000:
                score += 0.3
            elif data_size > 1000:
                score += 0.2

        # Check for multiple operations
        if hasattr(input_state, "operations") and len(input_state.operations) > 5:
            score += 0.3

        # Check for dependencies
        if hasattr(input_state, "dependencies") and input_state.dependencies:
            score += 0.2

        # Check for iterative operations
        if hasattr(input_state, "iterations") and input_state.iterations > 1:
            score += 0.2

        return min(score, 1.0)

    def _get_supported_modes(self) -> list:
        """Get supported execution modes from contract."""
        # Try to get from contract data
        if hasattr(self, "contract_data") and self.contract_data:
            modes = self.contract_data.get(cf.EXECUTION_MODES, [])
            if modes:
                return modes

        # Default modes
        return [ExecutionMode.DIRECT, ExecutionMode.WORKFLOW]

    def create_workflow(self, input_state: InputStateT):
        """
        Create LlamaIndex workflow for complex operations.

        Override this method to provide custom workflow.

        Args:
            input_state: Input state for workflow

        Returns:
            LlamaIndex Workflow instance or None if not supported
        """
        emit_log_event(
            LogLevelEnum.WARNING,
            f"No workflow implementation provided for {self.__class__.__name__}",
            {"execution_will_fallback": "direct"},
        )
        return None

    @property
    def execution_mode(self) -> Optional[str]:
        """Get the current execution mode."""
        return self._execution_mode

    @property
    def workflow_metrics(self) -> Optional[ModelWorkflowMetrics]:
        """Get workflow execution metrics if available."""
        return self._workflow_metrics

    def supports_mode(self, mode: str) -> bool:
        """Check if a specific execution mode is supported."""
        return mode in self._get_supported_modes()
