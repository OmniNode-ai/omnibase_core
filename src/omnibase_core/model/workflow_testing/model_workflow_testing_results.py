#!/usr/bin/env python3
"""
ONEX Workflow Testing Results Models

This module provides Pydantic models for workflow testing results,
capturing comprehensive test execution outcomes and metrics.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_testing import (
    EnumAccommodationStrategy,
    EnumAccommodationType,
    EnumTestExecutionStatus,
    EnumTestWorkflowPriority,
)
from omnibase_core.model.core.model_generic_value import ModelGenericValue
from omnibase_core.model.core.model_semver import ModelSemVer


class ModelValidationResult(BaseModel):
    """Model for individual validation result"""

    validation_id: str = Field(description="Unique identifier for this validation")
    field_name: str = Field(description="Name of the field that was validated")
    validation_rule: str = Field(description="Rule that was applied for validation")
    expected_value: ModelGenericValue = Field(
        description="Expected value for the validation",
    )
    actual_value: ModelGenericValue = Field(
        description="Actual value encountered during validation",
    )
    validation_passed: bool = Field(description="Whether the validation passed")
    validation_message: str | None = Field(
        default=None,
        description="Detailed message about the validation result",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "validation_id": "transformed_text_validation",
                    "field_name": "transformed_text",
                    "validation_rule": "equals",
                    "expected_value": "HELLO WORLD",
                    "actual_value": "HELLO WORLD",
                    "validation_passed": True,
                    "validation_message": "Text transformation successful",
                },
            ],
        }


class ModelStepOutput(BaseModel):
    """Model for test step output data"""

    transformed_text: str | None = Field(
        default=None,
        description="Transformed text output",
    )
    status: str | None = Field(default=None, description="Step execution status")
    processing_time_ms: float | None = Field(
        default=None,
        description="Processing time",
    )
    exception_raised: bool | None = Field(
        default=None,
        description="Whether exception was raised",
    )
    fail_fast_behavior: bool | None = Field(
        default=None,
        description="Whether fail-fast behavior occurred",
    )
    accommodation_successful: bool | None = Field(
        default=None,
        description="Whether accommodation succeeded",
    )
    accommodation_strategy: str | None = Field(
        default=None,
        description="Accommodation strategy used",
    )
    dependencies_accommodated: int | None = Field(
        default=None,
        description="Number of dependencies accommodated",
    )
    failure_injection_configured: int | None = Field(
        default=None,
        description="Number of failure injections configured",
    )
    dependencies_with_failure: list[str] | None = Field(
        default=None,
        description="Dependencies with failure injection",
    )
    node_start_event_emitted: bool | None = Field(
        default=None,
        description="Whether start event was emitted",
    )
    node_success_event_emitted: bool | None = Field(
        default=None,
        description="Whether success event was emitted",
    )
    correlation_id_propagated: bool | None = Field(
        default=None,
        description="Whether correlation ID was propagated",
    )
    average_execution_time_ms: float | None = Field(
        default=None,
        description="Average execution time",
    )
    p95_execution_time_ms: float | None = Field(
        default=None,
        description="95th percentile execution time",
    )
    all_executions_successful: bool | None = Field(
        default=None,
        description="Whether all executions succeeded",
    )
    successful_executions: int | None = Field(
        default=None,
        description="Number of successful executions",
    )
    total_executions: int | None = Field(
        default=None,
        description="Total number of executions",
    )
    all_results_identical: bool | None = Field(
        default=None,
        description="Whether all results are identical",
    )
    deterministic_hash_consistent: bool | None = Field(
        default=None,
        description="Whether hash is consistent",
    )
    repetition_count: int | None = Field(
        default=None,
        description="Number of repetitions",
    )
    results: list[ModelGenericValue] | None = Field(
        default=None,
        description="Detailed results list",
    )
    error: str | None = Field(
        default=None,
        description="Error message if step failed",
    )
    exception_type: str | None = Field(
        default=None,
        description="Type of exception raised",
    )
    error_code: str | None = Field(default=None, description="ONEX error code")

    class Config:
        extra = "allow"  # Allow additional fields for extensibility


class ModelErrorDetails(BaseModel):
    """Model for error details when step execution fails"""

    exception: str | None = Field(default=None, description="Exception message")
    validation_exception: str | None = Field(
        default=None,
        description="Validation exception message",
    )
    failed_validations: int | None = Field(
        default=None,
        description="Number of failed validations",
    )
    validation_errors: list[str] | None = Field(
        default=None,
        description="List of validation error messages",
    )

    class Config:
        extra = "allow"  # Allow additional error fields


class ModelTestStepResult(BaseModel):
    """Model for individual test step execution result"""

    step_id: str = Field(description="Identifier of the executed test step")
    step_action: str = Field(description="Action that was performed")
    execution_status: EnumTestExecutionStatus = Field(
        description="Status of the step execution",
    )
    execution_time_ms: float = Field(
        description="Time taken to execute this step in milliseconds",
    )
    step_output: ModelStepOutput | None = Field(
        default=None,
        description="Output data from the step execution",
    )
    validation_results: list[ModelValidationResult] = Field(
        default_factory=list,
        description="Results of validations performed on this step",
    )
    error_details: ModelErrorDetails | None = Field(
        default=None,
        description="Error details if the step failed",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "step_id": "execute_pure_transformation",
                    "step_action": "run_node_process",
                    "execution_status": "success",
                    "execution_time_ms": 25.5,
                    "step_output": {
                        "transformed_text": "HELLO WORLD",
                        "status": "success",
                    },
                    "validation_results": [],
                    "error_details": None,
                },
            ],
        }


class ModelAccommodationResult(BaseModel):
    """Model for dependency accommodation result"""

    dependency_name: str = Field(
        description="Name of the dependency that was accommodated",
    )
    requested_accommodation: EnumAccommodationType = Field(
        description="Type of accommodation that was requested",
    )
    actual_accommodation: EnumAccommodationType = Field(
        description="Type of accommodation that was actually used",
    )
    accommodation_reason: str = Field(
        description="Reason for the accommodation decision",
    )
    accommodation_successful: bool = Field(
        description="Whether the accommodation was successful",
    )
    setup_time_ms: float = Field(
        description="Time taken to set up the accommodation in milliseconds",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "dependency_name": "registry_canary_pure_tool",
                    "requested_accommodation": "real",
                    "actual_accommodation": "mock",
                    "accommodation_reason": "Registry service not running",
                    "accommodation_successful": True,
                    "setup_time_ms": 15.2,
                },
            ],
        }


class ModelTestingMetrics(BaseModel):
    """Model for comprehensive testing metrics"""

    total_steps_executed: int = Field(description="Total number of test steps executed")
    successful_steps: int = Field(
        description="Number of steps that executed successfully",
    )
    failed_steps: int = Field(description="Number of steps that failed")
    skipped_steps: int = Field(description="Number of steps that were skipped")
    total_execution_time_ms: float = Field(
        description="Total time for workflow execution in milliseconds",
    )
    average_step_time_ms: float = Field(
        description="Average time per step in milliseconds",
    )
    total_validations: int = Field(description="Total number of validations performed")
    passed_validations: int = Field(description="Number of validations that passed")
    failed_validations: int = Field(description="Number of validations that failed")
    accommodation_setup_time_ms: float = Field(
        description="Time spent setting up dependency accommodations",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "total_steps_executed": 5,
                    "successful_steps": 5,
                    "failed_steps": 0,
                    "skipped_steps": 0,
                    "total_execution_time_ms": 125.7,
                    "average_step_time_ms": 25.14,
                    "total_validations": 8,
                    "passed_validations": 8,
                    "failed_validations": 0,
                    "accommodation_setup_time_ms": 45.3,
                },
            ],
        }


class ModelTestWorkflowResult(BaseModel):
    """Model for complete test workflow execution result"""

    workflow_id: str = Field(description="Identifier of the executed test workflow")
    workflow_priority: EnumTestWorkflowPriority = Field(
        description="Priority level of the executed workflow",
    )
    execution_status: EnumTestExecutionStatus = Field(
        description="Overall status of the workflow execution",
    )
    accommodation_strategy_used: EnumAccommodationStrategy = Field(
        description="Accommodation strategy that was used",
    )
    accommodation_results: list[ModelAccommodationResult] = Field(
        description="Results of dependency accommodations",
    )
    step_results: list[ModelTestStepResult] = Field(
        description="Results of individual test step executions",
    )
    metrics: ModelTestingMetrics = Field(
        description="Comprehensive metrics for this workflow",
    )
    start_time: datetime = Field(description="When the workflow execution started")
    end_time: datetime = Field(description="When the workflow execution completed")
    error_summary: str | None = Field(
        default=None,
        description="Summary of errors if the workflow failed",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "workflow_id": "pure_functional_transformation_with_adaptive_accommodation",
                    "workflow_priority": "high",
                    "execution_status": "success",
                    "accommodation_strategy_used": "hybrid_smart",
                    "accommodation_results": [],
                    "step_results": [],
                    "metrics": {
                        "total_steps_executed": 3,
                        "successful_steps": 3,
                        "failed_steps": 0,
                        "total_execution_time_ms": 85.4,
                    },
                    "start_time": "2025-07-29T12:00:00Z",
                    "end_time": "2025-07-29T12:00:01Z",
                },
            ],
        }


class ModelWorkflowTestingResults(BaseModel):
    """Model for complete workflow testing execution results"""

    tool_name: str = Field(description="Name of the tool that was tested")
    tool_version: ModelSemVer = Field(description="Version of the tool that was tested")
    testing_configuration_version: ModelSemVer = Field(
        description="Version of the testing configuration used",
    )
    execution_context: str = Field(
        description="Context in which the tests were executed",
    )
    workflow_results: list[ModelTestWorkflowResult] = Field(
        description="Results of individual test workflow executions",
    )
    overall_execution_status: EnumTestExecutionStatus = Field(
        description="Overall status of the entire workflow testing run",
    )
    total_workflows_executed: int = Field(
        description="Total number of workflows that were executed",
    )
    successful_workflows: int = Field(
        description="Number of workflows that executed successfully",
    )
    failed_workflows: int = Field(description="Number of workflows that failed")
    skipped_workflows: int = Field(description="Number of workflows that were skipped")
    total_execution_time_ms: float = Field(
        description="Total time for all workflow testing in milliseconds",
    )
    start_time: datetime = Field(description="When the workflow testing started")
    end_time: datetime = Field(description="When the workflow testing completed")
    summary_report: str = Field(
        description="Human-readable summary of the testing results",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "tool_name": "canary_pure_tool",
                    "tool_version": {"major": 1, "minor": 0, "patch": 0},
                    "testing_configuration_version": {
                        "major": 1,
                        "minor": 0,
                        "patch": 0,
                    },
                    "execution_context": "local_development",
                    "workflow_results": [],
                    "overall_execution_status": "success",
                    "total_workflows_executed": 5,
                    "successful_workflows": 5,
                    "failed_workflows": 0,
                    "skipped_workflows": 0,
                    "total_execution_time_ms": 425.8,
                    "start_time": "2025-07-29T12:00:00Z",
                    "end_time": "2025-07-29T12:00:01Z",
                    "summary_report": "All 5 test workflows executed successfully",
                },
            ],
        }
