#!/usr/bin/env python3
"""
Reducer Pattern Engine Contracts - Phase 1 Data Models and Interfaces.

Provides comprehensive Pydantic data models for workflow processing,
routing, and subcontract integration with full type safety.

Key Models:
- ModelWorkflowInput: Input data for workflow processing
- ModelWorkflowOutput: Output data with processing results
- ModelWorkflowContext: Internal workflow processing context
- ModelSubreducerResult: Results from subreducer processing
- ModelRoutingInfo: Workflow routing information

ZERO TOLERANCE: No Any types allowed in implementation.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ModelDocumentData(BaseModel):
    """
    Document data structure for document regeneration workflows.

    Provides validated document content with metadata for processing.
    """

    title: str = Field(..., description="Document title", min_length=1, max_length=500)

    content: str = Field(
        ...,
        description="Document content text",
        min_length=0,
        max_length=1000000,  # 1MB text limit for Phase 1
    )

    format: str = Field(
        default="text",
        description="Document format (text, markdown, html, etc.)",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )

    version: str = Field(
        default="1.0",
        description="Document version identifier",
        pattern=r"^\d+\.\d+(\.\d+)?$",
    )

    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional document metadata",
        max_length=50,  # Maximum 50 metadata keys
    )

    @field_validator("metadata")
    @classmethod
    def validate_metadata_values(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate that all metadata values are strings with reasonable length."""
        for key, value in v.items():
            if not isinstance(value, str):
                raise ValueError(f"Metadata value for key '{key}' must be string")
            if len(value) > 1000:
                raise ValueError(
                    f"Metadata value for key '{key}' too long (max 1000 chars)"
                )
        return v


class ModelWorkflowInput(BaseModel):
    """
    Input model for reducer pattern engine workflow processing.

    Validates all required fields for workflow execution with
    comprehensive type safety and business rule validation.
    """

    workflow_type: str = Field(
        ...,
        description="Type of workflow to process",
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$",
        min_length=1,
        max_length=100,
    )

    instance_id: str = Field(
        ...,
        description="Unique workflow instance identifier",
        min_length=1,
        max_length=100,
    )

    data: Dict[str, Dict[str, str]] = Field(
        ..., description="Workflow payload data containing document information"
    )

    priority: int = Field(
        default=5,
        description="Workflow priority (1-10, higher is more urgent)",
        ge=1,
        le=10,
    )

    timeout_ms: int = Field(
        default=300000,  # 5 minutes
        description="Workflow timeout in milliseconds",
        ge=1000,  # Minimum 1 second
        le=3600000,  # Maximum 1 hour
    )

    correlation_id: Optional[str] = Field(
        default=None,
        description="Optional correlation ID for request tracking",
        max_length=100,
    )

    created_at: datetime = Field(
        default_factory=datetime.now, description="Workflow creation timestamp"
    )

    @field_validator("workflow_type")
    @classmethod
    def validate_workflow_type(cls, v: str) -> str:
        """Validate workflow type against Phase 1 supported types."""
        supported_types = ["document_regeneration"]
        if v not in supported_types:
            raise ValueError(
                f"Unsupported workflow type '{v}'. Phase 1 supports: {supported_types}"
            )
        return v

    @field_validator("data")
    @classmethod
    def validate_data_structure(
        cls, v: Dict[str, Dict[str, str]]
    ) -> Dict[str, Dict[str, str]]:
        """Validate workflow data contains required document structure."""
        if "document" not in v:
            raise ValueError("Workflow data must contain 'document' field")

        document = v["document"]
        if not isinstance(document, dict):
            raise ValueError("Document data must be dictionary")

        # Validate required document fields
        if "title" not in document:
            raise ValueError("Document must contain 'title' field")
        if "content" not in document:
            raise ValueError("Document must contain 'content' field")

        return v

    def model_post_init(self, __context) -> None:
        """Post-initialization to set correlation_id if not provided."""
        if self.correlation_id is None:
            self.correlation_id = str(uuid4())


class ModelWorkflowOutput(BaseModel):
    """
    Output model for reducer pattern engine workflow processing.

    Provides comprehensive results with execution metadata,
    error information, and traceability data.
    """

    success: bool = Field(..., description="Whether workflow processing succeeded")

    result_data: Optional[Dict[str, Dict[str, str]]] = Field(
        default=None, description="Processed workflow results (if successful)"
    )

    error_message: Optional[str] = Field(
        default=None,
        description="Error message (if processing failed)",
        max_length=1000,
    )

    workflow_type: str = Field(
        ..., description="Type of workflow that was processed", min_length=1
    )

    instance_id: str = Field(
        ..., description="Workflow instance identifier", min_length=1
    )

    execution_time_ms: int = Field(
        ..., description="Processing time in milliseconds", ge=0
    )

    correlation_id: str = Field(
        ..., description="Request correlation identifier for tracing", min_length=1
    )

    processing_timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp when processing completed",
    )

    state_transitions: List[str] = Field(
        default_factory=list,
        description="FSM state transitions performed during processing",
    )

    events_emitted: List[str] = Field(
        default_factory=list, description="Events emitted during workflow processing"
    )

    @field_validator("result_data")
    @classmethod
    def validate_result_data_when_successful(
        cls, v, info
    ) -> Optional[Dict[str, Dict[str, str]]]:
        """Validate that result_data is present when success=True."""
        # Get success field from values
        success = info.data.get("success")
        if success and v is None:
            raise ValueError("result_data must be provided when success=True")
        return v

    @field_validator("error_message")
    @classmethod
    def validate_error_message_when_failed(cls, v, info) -> Optional[str]:
        """Validate that error_message is present when success=False."""
        # Get success field from values
        success = info.data.get("success")
        if not success and not v:
            raise ValueError("error_message must be provided when success=False")
        return v


class ModelWorkflowContext(BaseModel):
    """
    Internal workflow processing context for subreducers.

    Contains all information needed for workflow execution
    including state tracking and correlation data.
    """

    workflow_type: str = Field(
        ..., description="Type of workflow being processed", min_length=1
    )

    instance_id: str = Field(
        ..., description="Unique workflow instance identifier", min_length=1
    )

    data: Dict[str, Dict[str, str]] = Field(..., description="Workflow payload data")

    correlation_id: str = Field(
        ..., description="Request correlation identifier", min_length=1
    )

    start_time: float = Field(
        ..., description="Workflow start timestamp (Unix time)", gt=0
    )

    current_state: str = Field(
        default="initialized",
        description="Current FSM state of the workflow",
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$",
    )

    state_history: List[str] = Field(
        default_factory=lambda: ["initialized"],
        description="History of FSM states traversed",
    )

    processing_metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional processing metadata",
        max_length=20,
    )

    @field_validator("processing_metadata")
    @classmethod
    def validate_processing_metadata(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate processing metadata values are strings."""
        for key, value in v.items():
            if not isinstance(value, str):
                raise ValueError(
                    f"Processing metadata value for '{key}' must be string"
                )
        return v


class ModelSubreducerResult(BaseModel):
    """
    Result model for subreducer processing operations.

    Provides detailed results from subreducer execution including
    state management and event tracking information.
    """

    success: bool = Field(..., description="Whether subreducer processing succeeded")

    result_data: Dict[str, Dict[str, str]] = Field(
        ..., description="Processing result data from subreducer"
    )

    execution_time_ms: int = Field(
        ..., description="Subreducer processing time in milliseconds", ge=0
    )

    correlation_id: str = Field(
        ..., description="Processing correlation identifier", min_length=1
    )

    error_details: Optional[str] = Field(
        default=None,
        description="Detailed error information (if processing failed)",
        max_length=2000,
    )

    state_transitions_performed: List[str] = Field(
        default_factory=list,
        description="FSM state transitions performed by subreducer",
    )

    events_emitted_count: int = Field(
        default=0, description="Number of events emitted during processing", ge=0
    )

    processing_steps_completed: int = Field(
        default=0, description="Number of processing steps completed", ge=0
    )

    subcontract_usage: Dict[str, bool] = Field(
        default_factory=dict,
        description="Which subcontracts were utilized during processing",
    )


class ModelRoutingInfo(BaseModel):
    """
    Workflow routing information from WorkflowRouter.

    Contains routing decisions and metadata for workflow distribution.
    """

    workflow_type: str = Field(
        ..., description="Type of workflow being routed", min_length=1
    )

    instance_id: str = Field(
        ..., description="Workflow instance identifier", min_length=1
    )

    route_key: str = Field(
        ...,
        description="Calculated routing key for consistent distribution",
        pattern=r"^[a-f0-9]{16}$",  # 16-character hex hash
    )

    target_subreducer: str = Field(
        ...,
        description="Target subreducer class name",
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
    )

    routing_correlation_id: str = Field(
        ..., description="Routing correlation identifier", min_length=1
    )

    routing_timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp when routing decision was made",
    )

    routing_metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional routing metadata", max_length=10
    )


class ModelProcessingMetrics(BaseModel):
    """
    Processing metrics for monitoring and optimization.

    Tracks performance and success metrics across workflow processing.
    """

    workflow_type: str = Field(
        ..., description="Type of workflow for these metrics", min_length=1
    )

    total_count: int = Field(
        default=0, description="Total number of workflows processed", ge=0
    )

    success_count: int = Field(
        default=0, description="Number of successful workflow executions", ge=0
    )

    error_count: int = Field(
        default=0, description="Number of failed workflow executions", ge=0
    )

    avg_execution_time_ms: float = Field(
        default=0.0, description="Average execution time in milliseconds", ge=0.0
    )

    min_execution_time_ms: float = Field(
        default=0.0, description="Minimum execution time in milliseconds", ge=0.0
    )

    max_execution_time_ms: float = Field(
        default=0.0, description="Maximum execution time in milliseconds", ge=0.0
    )

    success_rate_percent: float = Field(
        default=0.0, description="Success rate as percentage", ge=0.0, le=100.0
    )

    last_updated: datetime = Field(
        default_factory=datetime.now, description="When these metrics were last updated"
    )

    @field_validator("success_count")
    @classmethod
    def validate_success_count_not_greater_than_total(cls, v, info) -> int:
        """Validate success count doesn't exceed total count."""
        total = info.data.get("total_count", 0)
        if v > total:
            raise ValueError("success_count cannot exceed total_count")
        return v

    @field_validator("error_count")
    @classmethod
    def validate_error_count_not_greater_than_total(cls, v, info) -> int:
        """Validate error count doesn't exceed total count."""
        total = info.data.get("total_count", 0)
        if v > total:
            raise ValueError("error_count cannot exceed total_count")
        return v

    def model_post_init(self, __context) -> None:
        """Calculate derived metrics after initialization."""
        if self.total_count > 0:
            self.success_rate_percent = (self.success_count / self.total_count) * 100.0


# Phase 1 contract validation functions


def validate_workflow_input(input_data: Dict) -> ModelWorkflowInput:
    """
    Validate and parse workflow input data.

    Args:
        input_data: Raw input data dictionary

    Returns:
        ModelWorkflowInput: Validated input model

    Raises:
        ValidationError: If input data is invalid
    """
    return ModelWorkflowInput(**input_data)


def validate_document_data(document_data: Dict) -> ModelDocumentData:
    """
    Validate and parse document data structure.

    Args:
        document_data: Raw document data dictionary

    Returns:
        ModelDocumentData: Validated document model

    Raises:
        ValidationError: If document data is invalid
    """
    return ModelDocumentData(**document_data)


def create_workflow_output(
    success: bool,
    result_data: Optional[Dict] = None,
    error_message: Optional[str] = None,
    **kwargs,
) -> ModelWorkflowOutput:
    """
    Create validated workflow output model.

    Args:
        success: Whether processing succeeded
        result_data: Processing results (if successful)
        error_message: Error message (if failed)
        **kwargs: Additional output fields

    Returns:
        ModelWorkflowOutput: Validated output model
    """
    output_data = {
        "success": success,
        "result_data": result_data,
        "error_message": error_message,
        **kwargs,
    }
    return ModelWorkflowOutput(**output_data)


def create_processing_metrics(workflow_type: str) -> ModelProcessingMetrics:
    """
    Create initial processing metrics for a workflow type.

    Args:
        workflow_type: Type of workflow to create metrics for

    Returns:
        ModelProcessingMetrics: Initialized metrics model
    """
    return ModelProcessingMetrics(workflow_type=workflow_type)
