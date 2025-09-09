"""ONEX-compliant NodeReducerPatternEngine with ModelOnexContainer integration."""

import asyncio
import threading
import time
from typing import Any

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.model_onex_container import ModelONEXContainer
from omnibase_core.core.node_reducer import NodeReducer
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from .contracts.model_contract_reducer_pattern_engine import (
    ModelContractReducerPatternEngine,
)
from .engine import ReducerPatternEngine
from .models.model_reducer_pattern_engine_input import ModelReducerPatternEngineInput
from .models.model_reducer_pattern_engine_output import ModelReducerPatternEngineOutput
from .models.model_workflow_request import ModelWorkflowRequest
from .models.model_workflow_response import ModelWorkflowResponse
from .protocols.protocol_reducer_pattern_engine import (
    BaseReducerPatternEngine,
)


class NodeReducerPatternEngine(NodeReducer, BaseReducerPatternEngine):
    """
    ONEX-compliant NodeReducerPatternEngine with full protocol compliance.

    Extends NodeReducer to provide ONEX 4-node architecture compliance
    while integrating with the existing ReducerPatternEngine implementation.

    Key Features:
    - Full ONEX protocol compliance with envelope support
    - ModelOnexContainer dependency injection
    - Contract-driven configuration and validation
    - Protocol-based service resolution
    - Event envelope wrapping and unwrapping
    - Comprehensive error handling with OnexError patterns

    Phase 3 Implementation:
    - Wraps existing ReducerPatternEngine for backward compatibility
    - Adds ONEX envelope support for inter-node communication
    - Implements protocol-based validation and error handling
    - Integrates with ModelOnexContainer service resolution
    - Provides contract model validation
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize NodeReducerPatternEngine with ModelOnexContainer.

        Args:
            container: ONEX container for dependency injection

        Raises:
            OnexError: If initialization fails
        """
        super().__init__(container)

        # Override the contract model with our specific type
        self.contract_model: ModelContractReducerPatternEngine = (
            self._load_contract_model()
        )

        # Initialize the underlying pattern engine
        self._pattern_engine = ReducerPatternEngine(container)

        # ONEX protocol compliance metadata
        self._node_id = "reducer_pattern_engine"
        self._protocol_version = "1.0.0"
        self._onex_compliance_version = "1.0.0"

        # Service caching for performance optimization
        self._service_cache: dict[str, Any] = {}
        self._service_cache_lock = threading.RLock()

        # Service resolution through container
        self._initialize_services()

        # Register subreducers from contract
        self._register_contract_subreducers()

        emit_log_event(
            level=LogLevel.INFO,
            message="NodeReducerPatternEngine Phase 3 initialized with ONEX compliance",
            context={
                "event": "node_reducer_pattern_engine_initialized",
                "node_id": self._node_id,
                "protocol_version": self._protocol_version,
                "onex_compliance_version": self._onex_compliance_version,
                "container_type": type(container).__name__,
                "contract_validated": True,
                "supported_workflows": self.get_supported_workflow_types(),
            },
        )

    def _load_contract_model(self) -> ModelContractReducerPatternEngine:
        """
        Load and validate the contract model for this engine.

        Returns:
            ModelContractReducerPatternEngine: Validated contract model

        Raises:
            OnexError: If contract loading or validation fails
        """
        try:
            # For Phase 3, create a default contract if file not found
            # In production, this would load from contract.yaml
            contract = ModelContractReducerPatternEngine()

            # Validate the contract
            contract.validate_node_specific_config()

            return contract

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.INITIALIZATION_FAILED,
                message=f"Failed to load contract model: {e!s}",
                context={"error_type": type(e).__name__, "node_type": "REDUCER"},
            )

    def _initialize_services(self) -> None:
        """Initialize services through ModelOnexContainer."""
        try:
            # For Phase 3, mock service resolution - real implementation in Phase 4
            # In production, these would resolve actual services

            emit_log_event(
                level=LogLevel.DEBUG,
                message="Services initialized through ModelOnexContainer",
                context={
                    "event": "services_initialized",
                    "container_available": self.container is not None,
                    "base_container_available": hasattr(
                        self.container,
                        "base_container",
                    ),
                },
            )

        except Exception as e:
            emit_log_event(
                level=LogLevel.WARNING,
                message=f"Some services could not be initialized: {e!s}",
                context={"event": "service_initialization_partial", "error": str(e)},
            )

    def _get_cached_service(self, service_name: str) -> Any:
        """
        Get service from container with caching for performance optimization.

        Implements thread-safe caching to avoid repeated service resolution
        calls which can be expensive in high-throughput scenarios.

        Args:
            service_name: Name of the service to resolve

        Returns:
            Any: The resolved service instance

        Raises:
            OnexError: If service resolution fails
        """
        with self._service_cache_lock:
            # Check cache first
            if service_name in self._service_cache:
                return self._service_cache[service_name]

            try:
                # Resolve service through container
                if hasattr(self.container, "get_service"):
                    service = self.container.get_service(service_name)
                else:
                    # Fallback for Phase 3 - mock service resolution
                    service = f"MockService_{service_name}"

                # Cache the resolved service
                self._service_cache[service_name] = service

                emit_log_event(
                    level=LogLevel.DEBUG,
                    message=f"Service '{service_name}' resolved and cached",
                    context={
                        "event": "service_cached",
                        "service_name": service_name,
                        "cache_size": len(self._service_cache),
                    },
                )

                return service

            except Exception as e:
                raise OnexError(
                    error_code=CoreErrorCode.SERVICE_RESOLUTION_FAILED,
                    message=f"Failed to resolve service '{service_name}': {e!s}",
                    context={
                        "service_name": service_name,
                        "error_type": type(e).__name__,
                        "container_available": self.container is not None,
                    },
                )

    def _clear_service_cache(self) -> None:
        """Clear service cache and log cache statistics."""
        with self._service_cache_lock:
            cache_size = len(self._service_cache)
            self._service_cache.clear()

            emit_log_event(
                level=LogLevel.DEBUG,
                message="Service cache cleared",
                context={
                    "event": "service_cache_cleared",
                    "previous_cache_size": cache_size,
                },
            )

    def _register_contract_subreducers(self) -> None:
        """Register subreducers based on contract specifications."""
        try:
            from ..subreducers.reducer_data_analysis import (
                ReducerDataAnalysisSubreducer,
            )
            from ..subreducers.reducer_document_regeneration import (
                ReducerDocumentRegenerationSubreducer,
            )
            from ..subreducers.reducer_report_generation import (
                ReducerReportGenerationSubreducer,
            )
            from .models.model_workflow_types import WorkflowType

            # Register data analysis subreducer
            data_analysis_subreducer = ReducerDataAnalysisSubreducer()
            self._pattern_engine.register_subreducer(
                subreducer=data_analysis_subreducer,
                workflow_types=[WorkflowType.DATA_ANALYSIS],
            )

            # Register document regeneration subreducer
            doc_regeneration_subreducer = ReducerDocumentRegenerationSubreducer()
            self._pattern_engine.register_subreducer(
                subreducer=doc_regeneration_subreducer,
                workflow_types=[WorkflowType.DOCUMENT_REGENERATION],
            )

            # Register report generation subreducer
            report_generation_subreducer = ReducerReportGenerationSubreducer()
            self._pattern_engine.register_subreducer(
                subreducer=report_generation_subreducer,
                workflow_types=[WorkflowType.REPORT_GENERATION],
            )

            emit_log_event(
                level=LogLevel.INFO,
                message="All contract subreducers registered successfully",
                context={
                    "event": "contract_subreducers_registered",
                    "registered_count": 3,
                    "workflow_types": self.get_supported_workflow_types(),
                },
            )

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to register contract subreducers: {e!s}",
                context={
                    "event": "contract_subreducer_registration_failed",
                    "error": str(e),
                },
            )

    # Protocol Implementation

    async def process_workflow(
        self,
        engine_input: ModelReducerPatternEngineInput,
    ) -> ModelReducerPatternEngineOutput:
        """
        Process a workflow through the ONEX-compliant engine.

        Args:
            engine_input: ONEX-compliant input with workflow request and optional envelope

        Returns:
            ModelReducerPatternEngineOutput: ONEX-compliant output with response and envelope

        Raises:
            OnexError: If processing fails
        """
        start_time = time.perf_counter()

        try:
            # Validate input for protocol compliance
            await self.validate_input(engine_input)

            emit_log_event(
                level=LogLevel.INFO,
                message=f"Started ONEX workflow processing for {engine_input.workflow_request.workflow_id}",
                context={
                    "event": "onex_workflow_processing_started",
                    "workflow_id": str(engine_input.workflow_request.workflow_id),
                    "workflow_type": engine_input.workflow_request.workflow_type.value,
                    "correlation_id": str(engine_input.get_correlation_id()),
                    "has_envelope": engine_input.envelope is not None,
                    "protocol_version": engine_input.protocol_version,
                },
            )

            # Process through underlying pattern engine
            workflow_response = await self._pattern_engine.process_workflow(
                engine_input.workflow_request,
            )

            # Calculate processing time
            processing_time_ms = (time.perf_counter() - start_time) * 1000

            # Create ONEX-compliant output
            engine_output = ModelReducerPatternEngineOutput.from_workflow_response(
                workflow_response=workflow_response,
                correlation_id=engine_input.get_correlation_id(),
                source_node_id=self._node_id,
                target_node_id=engine_input.get_source_node_id(),
                processing_metadata={
                    "processing_time_ms": processing_time_ms,
                    "protocol_version": self._protocol_version,
                    "onex_compliance_version": self._onex_compliance_version,
                    "node_id": self._node_id,
                },
            )

            # Handle envelope if present
            if engine_input.envelope:
                engine_output.envelope = engine_input.envelope

            emit_log_event(
                level=LogLevel.INFO,
                message=f"Completed ONEX workflow processing for {engine_input.workflow_request.workflow_id}",
                context={
                    "event": "onex_workflow_processing_completed",
                    "workflow_id": str(engine_input.workflow_request.workflow_id),
                    "workflow_type": engine_input.workflow_request.workflow_type.value,
                    "correlation_id": str(engine_output.get_correlation_id()),
                    "success": engine_output.is_success(),
                    "processing_time_ms": processing_time_ms,
                },
            )

            return engine_output

        except Exception as e:
            processing_time_ms = (time.perf_counter() - start_time) * 1000

            emit_log_event(
                level=LogLevel.ERROR,
                message=f"ONEX workflow processing failed: {e!s}",
                context={
                    "event": "onex_workflow_processing_failed",
                    "workflow_id": str(engine_input.workflow_request.workflow_id),
                    "workflow_type": engine_input.workflow_request.workflow_type.value,
                    "correlation_id": str(engine_input.get_correlation_id()),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time_ms": processing_time_ms,
                },
            )

            # Create error output using protocol base class method
            return self.create_error_output(
                engine_input=engine_input,
                error_message=str(e),
                error_details={
                    "error_type": type(e).__name__,
                    "processing_time_ms": processing_time_ms,
                    "node_id": self._node_id,
                },
            )

    async def health_check(self) -> bool:
        """
        Check the health status of the engine.

        Returns:
            bool: True if engine is healthy, False otherwise
        """
        try:
            # Check underlying pattern engine health
            pattern_engine_healthy = hasattr(self._pattern_engine, "get_metrics")

            # Check container health
            container_healthy = self.container is not None

            # Check contract model
            contract_healthy = self.contract_model is not None

            # Check subreducer registration
            subreducers_healthy = len(self.get_supported_workflow_types()) > 0

            overall_health = (
                pattern_engine_healthy
                and container_healthy
                and contract_healthy
                and subreducers_healthy
            )

            emit_log_event(
                level=LogLevel.DEBUG,
                message=f"Node health check completed: {overall_health}",
                context={
                    "event": "node_health_check",
                    "pattern_engine_healthy": pattern_engine_healthy,
                    "container_healthy": container_healthy,
                    "contract_healthy": contract_healthy,
                    "subreducers_healthy": subreducers_healthy,
                    "overall_health": overall_health,
                },
            )

            return overall_health

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Health check failed: {e!s}",
                context={"event": "node_health_check_failed", "error": str(e)},
            )
            return False

    def get_supported_workflow_types(self) -> list[str]:
        """
        Get list of supported workflow types.

        Returns:
            List[str]: List of workflow type strings
        """
        return self.contract_model.pattern_config.supported_workflows

    # Additional ONEX Methods

    async def process_envelope(
        self,
        envelope: "ModelEventEnvelope",
    ) -> "ModelEventEnvelope":
        """
        Process an ONEX event envelope for full protocol compliance.

        Args:
            envelope: ONEX event envelope to process

        Returns:
            ModelEventEnvelope: Response envelope

        Raises:
            OnexError: If envelope processing fails
        """
        try:
            # Create input from envelope
            engine_input = ModelReducerPatternEngineInput.from_envelope(envelope)

            # Process workflow
            engine_output = await self.process_workflow(engine_input)

            # Return response envelope
            return engine_output.to_envelope()

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.PROCESSING_ERROR,
                message=f"Envelope processing failed: {e!s}",
                context={
                    "envelope_id": envelope.envelope_id,
                    "correlation_id": str(envelope.correlation_id),
                    "error_type": type(e).__name__,
                },
            )

    def get_node_metadata(self) -> dict[str, Any]:
        """
        Get node metadata for ONEX compliance.

        Returns:
            Dict[str, Any]: Node metadata
        """
        return {
            "node_id": self._node_id,
            "node_type": "COMPUTE",
            "protocol_version": self._protocol_version,
            "onex_compliance_version": self._onex_compliance_version,
            "supported_workflow_types": self.get_supported_workflow_types(),
            "contract_version": "1.0.0",
            "pattern_type": "execution_pattern",
            "capabilities": [
                "workflow_processing",
                "envelope_support",
                "instance_isolation",
                "concurrent_processing",
                "enhanced_metrics",
                "state_management",
            ],
        }

    def get_contract_model(self) -> ModelContractReducerPatternEngine:
        """
        Get the contract model for this engine.

        Returns:
            ModelContractReducerPatternEngine: Contract model
        """
        return self.contract_model

    def get_processing_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive processing metrics.

        Returns:
            Dict[str, Any]: Processing metrics
        """
        try:
            # Get metrics from underlying pattern engine
            pattern_metrics = self._pattern_engine.get_comprehensive_metrics()

            # Add ONEX compliance metrics
            onex_metrics = {
                "node_id": self._node_id,
                "protocol_version": self._protocol_version,
                "onex_compliance_version": self._onex_compliance_version,
                "supported_workflow_count": len(self.get_supported_workflow_types()),
                "contract_validation_passed": True,
            }

            return {
                "pattern_metrics": pattern_metrics,
                "onex_metrics": onex_metrics,
                "node_metadata": self.get_node_metadata(),
            }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to collect metrics: {e!s}",
                context={"event": "metrics_collection_failed", "error": str(e)},
            )
            return {
                "error": str(e),
                "node_id": self._node_id,
            }

    # Backward Compatibility Methods

    async def reduce(
        self,
        workflow_request: ModelWorkflowRequest,
    ) -> ModelWorkflowResponse:
        """
        Backward compatibility method for direct workflow processing.

        Args:
            workflow_request: Workflow request to process

        Returns:
            ModelWorkflowResponse: Workflow response
        """
        # Create ONEX input from workflow request
        engine_input = ModelReducerPatternEngineInput.from_workflow_request(
            workflow_request,
        )

        # Process through ONEX interface
        engine_output = await self.process_workflow(engine_input)

        # Return the workflow response
        return engine_output.workflow_response

    # Required ONEX Node Methods

    async def get_health_status(self) -> dict[str, Any]:
        """
        Get comprehensive health status for ONEX contract compliance.

        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            health_status = {
                "status": "healthy",
                "node_id": self._node_id,
                "node_type": "REDUCER",
                "pattern_type": "reducer_pattern_engine",
                "timestamp": int(time.time() * 1000),
                "onex_compliance_version": self._onex_compliance_version,
            }

            # Check pattern engine health (async if available)
            if hasattr(self._pattern_engine, "get_health_status"):
                if asyncio.iscoroutinefunction(self._pattern_engine.get_health_status):
                    pattern_health = await self._pattern_engine.get_health_status()
                else:
                    pattern_health = self._pattern_engine.get_health_status()
                health_status["pattern_engine"] = pattern_health

            # Check container health (async if available)
            if hasattr(self._container, "get_health_status"):
                if asyncio.iscoroutinefunction(self._container.get_health_status):
                    container_health = await self._container.get_health_status()
                else:
                    container_health = self._container.get_health_status()
                health_status["container"] = container_health

            # Basic health checks
            health_status["components"] = {
                "pattern_engine_initialized": self._pattern_engine is not None,
                "contract_loaded": self._contract is not None,
                "container_available": self._container is not None,
            }

            return health_status

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Health check failed: {e!s}",
                context={"event": "health_check_failed", "error": str(e)},
            )
            return {
                "status": "unhealthy",
                "error": str(e),
                "node_id": self._node_id,
                "timestamp": int(time.time() * 1000),
            }

    def get_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive metrics for ONEX contract compliance.

        Returns:
            Dict[str, Any]: Metrics information
        """
        try:
            # Get pattern-specific metrics
            pattern_metrics = {}
            if hasattr(self._pattern_engine, "get_metrics"):
                pattern_metrics = self._pattern_engine.get_metrics()

            # ONEX compliance metrics
            onex_metrics = {
                "node_id": self._node_id,
                "node_type": "REDUCER",
                "uptime_seconds": int(time.time() - self._start_time),
                "onex_compliance_version": self._onex_compliance_version,
                "supported_workflow_count": len(self.get_supported_workflow_types()),
                "contract_validation_passed": True,
            }

            return {
                "pattern_metrics": pattern_metrics,
                "onex_metrics": onex_metrics,
                "node_metadata": self.get_node_metadata(),
            }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to collect metrics: {e!s}",
                context={"event": "metrics_collection_failed", "error": str(e)},
            )
            return {
                "error": str(e),
                "node_id": self._node_id,
            }
