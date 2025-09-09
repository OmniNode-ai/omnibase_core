"""
ReducerDocumentRegenerationSubreducer - Reference subreducer implementation.

Handles document regeneration workflows as a reference implementation
for the Reducer Pattern Engine Phase 1. Demonstrates the subreducer
contract and processing patterns.
"""

import time

from omnibase_core.core.common_types import ModelScalarValue
from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from ..v1_0_0.models import BaseSubreducer
from ..v1_0_0.models import ModelSubreducerResult as SubreducerResult
from ..v1_0_0.models import ModelWorkflowRequest as WorkflowRequest
from ..v1_0_0.models import ModelWorkflowResultData as WorkflowResultData
from ..v1_0_0.models import WorkflowType


class ReducerDocumentRegenerationSubreducer(BaseSubreducer):
    """
    Document regeneration workflow subreducer.

    Reference implementation for handling document regeneration workflows
    in the Reducer Pattern Engine Phase 1. Demonstrates:
    - Proper subreducer contract implementation
    - Structured logging and error handling
    - Workflow state management
    - Performance metrics collection
    - Correlation ID tracking

    Phase 1 Features:
    - Basic document regeneration processing
    - Error handling with structured responses
    - Processing time metrics
    - Comprehensive logging for observability
    """

    def __init__(self):
        """Initialize the document regeneration subreducer."""
        super().__init__("reducer_document_regeneration")
        self._processing_metrics = {
            "total_processed": 0,
            "successful_processes": 0,
            "failed_processes": 0,
            "average_processing_time_ms": 0.0,
        }

        emit_log_event(
            level=LogLevel.INFO,
            event="subreducer_initialized",
            message=f"Initialized {self.name} subreducer",
            context={"subreducer_name": self.name},
        )

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        """
        Check if this subreducer supports the given workflow type.

        Args:
            workflow_type: The workflow type to check

        Returns:
            bool: True if workflow_type is DOCUMENT_REGENERATION
        """
        return workflow_type == WorkflowType.DOCUMENT_REGENERATION

    async def process(self, request: WorkflowRequest) -> SubreducerResult:
        """
        Process a document regeneration workflow request.

        Main processing method that handles the document regeneration
        workflow from start to finish with proper error handling
        and metrics collection.

        Args:
            request: The workflow request to process

        Returns:
            SubreducerResult: The processing result with success/failure status
        """
        start_time = time.perf_counter()

        try:
            # Validate workflow type
            if not self.supports_workflow_type(request.workflow_type):
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Unsupported workflow type: {request.workflow_type.value}",
                    context={
                        "workflow_type": request.workflow_type.value,
                        "supported_types": [WorkflowType.DOCUMENT_REGENERATION.value],
                        "workflow_id": str(request.workflow_id),
                        "subreducer_name": self.name,
                    },
                )

            emit_log_event(
                level=LogLevel.INFO,
                event="document_regeneration_started",
                message=f"Started document regeneration for workflow {request.workflow_id}",
                context={
                    "workflow_id": str(request.workflow_id),
                    "instance_id": request.instance_id,
                    "correlation_id": str(request.correlation_id),
                    "subreducer_name": self.name,
                },
            )

            # Extract document regeneration parameters
            document_params = self._extract_document_params(request)

            # Perform document regeneration processing
            result_data = await self._process_document_regeneration(
                document_params,
                request,
            )

            # Calculate processing time
            processing_time_ms = (time.perf_counter() - start_time) * 1000

            # Update metrics
            self._update_success_metrics(processing_time_ms)

            # Create successful result
            result = SubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=True,
                result=result_data,
                processing_time_ms=processing_time_ms,
            )

            emit_log_event(
                level=LogLevel.INFO,
                event="document_regeneration_completed",
                message=f"Completed document regeneration for workflow {request.workflow_id}",
                context={
                    "workflow_id": str(request.workflow_id),
                    "instance_id": request.instance_id,
                    "correlation_id": str(request.correlation_id),
                    "subreducer_name": self.name,
                    "processing_time_ms": processing_time_ms,
                    "result_keys": list(result_data.keys()) if result_data else [],
                },
            )

            return result

        except Exception as e:
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            self._update_failure_metrics(processing_time_ms)

            # Create failure result
            result = SubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=False,
                error_message=str(e),
                error_details={
                    "error_type": type(e).__name__,
                    "workflow_type": request.workflow_type.value,
                    "instance_id": request.instance_id,
                },
                processing_time_ms=processing_time_ms,
            )

            emit_log_event(
                level=LogLevel.ERROR,
                event="document_regeneration_failed",
                message=f"Document regeneration failed for workflow {request.workflow_id}: {e!s}",
                context={
                    "workflow_id": str(request.workflow_id),
                    "instance_id": request.instance_id,
                    "correlation_id": str(request.correlation_id),
                    "subreducer_name": self.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time_ms": processing_time_ms,
                },
            )

            return result

    def get_metrics(self) -> dict[str, ModelScalarValue]:
        """
        Get processing metrics for this subreducer.

        Returns:
            Dict[str, ModelScalarValue]: Current processing metrics
        """
        success_rate = 0.0
        if self._processing_metrics["total_processed"] > 0:
            success_rate = (
                self._processing_metrics["successful_processes"]
                / self._processing_metrics["total_processed"]
                * 100.0
            )

        return {
            **self._processing_metrics,
            "success_rate_percent": success_rate,
            "subreducer_name": self.name,
        }

    def _extract_document_params(
        self,
        request: WorkflowRequest,
    ) -> dict[str, ModelScalarValue]:
        """
        Extract and validate document regeneration parameters.

        Args:
            request: The workflow request

        Returns:
            Dict[str, ModelScalarValue]: Validated document parameters

        Raises:
            OnexError: If required parameters are missing or invalid
        """
        payload = request.payload

        # Define required parameters for document regeneration
        required_params = ["document_id", "content_type"]
        missing_params = [param for param in required_params if param not in payload]

        if missing_params:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Missing required parameters: {missing_params}",
                context={
                    "missing_params": missing_params,
                    "required_params": required_params,
                    "workflow_id": str(request.workflow_id),
                },
            )

        # Extract and validate parameters
        document_params = {
            "document_id": payload["document_id"],
            "content_type": payload["content_type"],
            "template_id": payload.get("template_id", "default"),
            "regeneration_options": payload.get("regeneration_options", {}),
            "metadata": payload.get("metadata", {}),
        }

        emit_log_event(
            level=LogLevel.DEBUG,
            event="document_params_extracted",
            message="Extracted document regeneration parameters",
            context={
                "workflow_id": str(request.workflow_id),
                "document_id": document_params["document_id"],
                "content_type": document_params["content_type"],
                "template_id": document_params["template_id"],
            },
        )

        return document_params

    async def _process_document_regeneration(
        self,
        document_params: dict[str, ModelScalarValue],
        request: WorkflowRequest,
    ) -> WorkflowResultData:
        """
        Perform the actual document regeneration processing.

        This is a Phase 1 implementation that demonstrates the processing
        pattern. In a full implementation, this would integrate with actual
        document generation services.

        Args:
            document_params: Validated document parameters
            request: The original workflow request

        Returns:
            WorkflowResultData: The regenerated document result
        """
        # Phase 1: Simulate document regeneration processing
        # In a real implementation, this would integrate with document services
        start_time = time.time()

        emit_log_event(
            level=LogLevel.INFO,
            event="document_regeneration_processing",
            message="Processing document regeneration",
            context={
                "workflow_id": str(request.workflow_id),
                "document_id": document_params["document_id"],
                "content_type": document_params["content_type"],
            },
        )

        # Generate strongly typed result data
        result_data = WorkflowResultData(
            processed_content=f"Regenerated document content for ID: {document_params.get('document_id', 'unknown')}",
            document_url=f"/documents/{document_params.get('document_id', 'unknown')}/regenerated",
            document_size_bytes=1024,
            quality_score=0.95,
            validation_passed=True,
            processing_duration_ms=int((time.time() - start_time) * 1000),
            memory_used_mb=2.5,
        )

        return result_data

    def _update_success_metrics(self, processing_time_ms: float) -> None:
        """
        Update metrics for successful processing.

        Args:
            processing_time_ms: Time taken for processing
        """
        self._processing_metrics["total_processed"] += 1
        self._processing_metrics["successful_processes"] += 1

        # Update average processing time
        total = self._processing_metrics["total_processed"]
        current_avg = self._processing_metrics["average_processing_time_ms"]
        self._processing_metrics["average_processing_time_ms"] = (
            current_avg + (processing_time_ms - current_avg) / total
        )

    def _update_failure_metrics(self, processing_time_ms: float) -> None:
        """
        Update metrics for failed processing.

        Args:
            processing_time_ms: Time taken before failure
        """
        self._processing_metrics["total_processed"] += 1
        self._processing_metrics["failed_processes"] += 1

        # Update average processing time (includes failures)
        total = self._processing_metrics["total_processed"]
        current_avg = self._processing_metrics["average_processing_time_ms"]
        self._processing_metrics["average_processing_time_ms"] = (
            current_avg + (processing_time_ms - current_avg) / total
        )
