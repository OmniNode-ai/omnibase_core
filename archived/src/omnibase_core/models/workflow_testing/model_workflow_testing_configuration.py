#!/usr/bin/env python3
"""
ONEX Workflow Testing Configuration Models

This module provides Pydantic models for workflow testing configuration,
supporting flexible dependency accommodation and comprehensive test workflows.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_workflow_testing import (
    EnumAccommodationLevel,
    EnumAccommodationStrategy,
    EnumAccommodationType,
    EnumDependencyType,
    EnumFallbackStrategy,
    EnumTestContext,
    EnumTestWorkflowPriority,
    EnumValidationRule,
)
from omnibase_core.models.core.model_generic_value import ModelGenericValue
from omnibase_core.models.core.model_semver import ModelSemVer


class ModelDependencyFlexibility(BaseModel):
    """Model for dependency flexibility configuration"""

    accommodation_levels: list[EnumAccommodationLevel] = Field(
        description="Available accommodation levels for dependencies",
    )
    default_accommodation_strategy: EnumAccommodationStrategy = Field(
        description="Default strategy for dependency accommodation",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "accommodation_levels": [
                        "full_real",
                        "full_mock",
                        "hybrid_smart",
                        "selective",
                    ],
                    "default_accommodation_strategy": "hybrid_smart",
                },
            ],
        }
    )


class ModelRealDependencyConfig(BaseModel):
    """Configuration for real dependency usage"""

    available_when: str | None = Field(
        default=None,
        description="Condition when real dependency is available",
    )
    always_available: bool | None = Field(
        default=None,
        description="Whether real dependency is always available",
    )
    implementation_class: str = Field(
        description="Full class path for real implementation",
    )
    setup_requirements: list[str] | None = Field(
        default_factory=list,
        description="Setup requirements for real dependency",
    )
    connection_timeout_ms: int | None = Field(
        default=5000,
        description="Connection timeout",
    )
    health_check_endpoint: str | None = Field(
        default=None,
        description="Health check endpoint",
    )


class ModelMockDependencyConfig(BaseModel):
    """Configuration for mock dependency usage"""

    always_available: bool = Field(
        default=True,
        description="Whether mock is always available",
    )
    implementation_class: str = Field(
        description="Full class path for mock implementation",
    )
    behavior_configuration_file: str | None = Field(
        default=None,
        description="Path to behavior config YAML",
    )
    deterministic_responses: bool = Field(
        default=True,
        description="Whether responses are deterministic",
    )


class ModelAccommodationOptions(BaseModel):
    """Model for dependency accommodation options"""

    real: ModelRealDependencyConfig | None = Field(
        default=None,
        description="Configuration for real dependency usage",
    )
    mock: ModelMockDependencyConfig | None = Field(
        default=None,
        description="Configuration for mock dependency usage",
    )
    fallback_strategy: EnumFallbackStrategy = Field(
        description="Strategy to use when primary option fails",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "real": {
                        "available_when": "registry_service_running",
                        "implementation_class": "RegistryCanaryPureTool",
                        "setup_requirements": ["tool_registry_initialized"],
                    },
                    "mock": {
                        "always_available": True,
                        "implementation_class": "MockRegistryCanaryPureTool",
                        "behavior_configuration_file": "registry_mock_behaviors.yaml",
                    },
                    "fallback_strategy": "mock_if_real_unavailable",
                },
            ],
        }
    )


class ModelDependencyAccommodation(BaseModel):
    """Model for individual dependency accommodation configuration"""

    interface_protocol: str = Field(
        description="Protocol interface that this dependency must implement",
    )
    dependency_type: EnumDependencyType = Field(
        description="Type of dependency for categorization",
    )
    accommodation_options: ModelAccommodationOptions = Field(
        description="Available accommodation options for this dependency",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "interface_protocol": "ProtocolRegistryCanaryPure",
                    "dependency_type": "registry",
                    "accommodation_options": {
                        "real": {
                            "available_when": "registry_service_running",
                            "implementation_class": "RegistryCanaryPureTool",
                        },
                        "mock": {
                            "always_available": True,
                            "implementation_class": "MockRegistryCanaryPureTool",
                        },
                        "fallback_strategy": "mock_if_real_unavailable",
                    },
                },
            ],
        }
    )


class ModelExpectedOutcome(BaseModel):
    """Model for expected test outcome validation"""

    outcome_field: str = Field(description="Field name in the result to validate")
    validation_rule: EnumValidationRule = Field(
        description="Rule to apply for validation",
    )
    expected_value: ModelGenericValue = Field(
        description="Expected value for comparison (automatically converted to ModelGenericValue)",
    )
    validation_message: str | None = Field(
        default=None,
        description="Custom message for validation failure",
    )

    @field_validator("expected_value", mode="before")
    @classmethod
    def convert_expected_value_to_generic(cls, v):
        """Convert primitive values to ModelGenericValue automatically."""
        if isinstance(v, ModelGenericValue):
            return v
        # Convert primitive values using ModelGenericValue factory method
        return ModelGenericValue.from_python_value(v)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "outcome_field": "transformed_text",
                    "validation_rule": "equals",
                    "expected_value": "HELLO WORLD",
                    "validation_message": "Text transformation should convert to uppercase",
                },
            ],
        }
    )


class ModelStepParameters(BaseModel):
    """Model for test step parameters"""

    input_text: str | None = Field(
        default=None,
        description="Input text for processing",
    )
    transformation_type: str | None = Field(
        default=None,
        description="Type of transformation",
    )
    accommodation_strategy: str | None = Field(
        default=None,
        description="Accommodation strategy",
    )
    failure_injection: dict[str, ModelGenericValue] | None = Field(
        default=None,
        description="Failure injection config",
    )
    execution_count: int | None = Field(
        default=None,
        description="Number of executions for performance tests",
    )
    repetition_count: int | None = Field(
        default=None,
        description="Number of repetitions for validation",
    )

    @field_validator("failure_injection", mode="before")
    @classmethod
    def convert_failure_injection_to_generic(cls, v):
        """Convert primitive values in failure_injection to ModelGenericValue automatically."""
        if v is None:
            return v
        if isinstance(v, dict):
            converted = {}
            for key, value in v.items():
                if isinstance(value, ModelGenericValue):
                    converted[key] = value
                elif isinstance(value, dict):
                    # Handle nested dict by creating a single ModelGenericValue from the entire dict
                    # This is because failure_injection[key] should be a ModelGenericValue containing dict data
                    converted[key] = ModelGenericValue.from_python_value(value)
                else:
                    converted[key] = ModelGenericValue.from_python_value(value)
            return converted
        return v

    model_config = ConfigDict(
        extra="allow"  # Allow additional parameters for extensibility
    )


class ModelTestExecutionStep(BaseModel):
    """Model for individual test execution step"""

    step_id: str = Field(description="Unique identifier for this test step")
    step_action: str = Field(description="Action to perform in this step")
    step_parameters: ModelStepParameters = Field(
        default_factory=ModelStepParameters,
        description="Parameters for the step action",
    )
    expected_outcomes: list[ModelExpectedOutcome] = Field(
        default_factory=list,
        description="Expected outcomes to validate for this step",
    )
    timeout_ms: int | None = Field(
        default=30000,
        description="Timeout for step execution in milliseconds",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "step_id": "execute_pure_transformation",
                    "step_action": "run_node_process",
                    "step_parameters": {
                        "input_text": "hello world",
                        "transformation_type": "uppercase",
                    },
                    "expected_outcomes": [
                        {
                            "outcome_field": "transformed_text",
                            "validation_rule": "equals",
                            "expected_value": "HELLO WORLD",
                        },
                    ],
                    "timeout_ms": 5000,
                },
            ],
        }
    )


class ModelTestWorkflow(BaseModel):
    """Model for complete test workflow definition"""

    workflow_id: str = Field(description="Unique identifier for this test workflow")
    workflow_description: str = Field(
        description="Human-readable description of what this workflow tests",
    )
    workflow_priority: EnumTestWorkflowPriority = Field(
        description="Priority level for this test workflow",
    )
    accommodation_strategy: EnumAccommodationStrategy = Field(
        description="Strategy to use for dependency accommodation",
    )
    accommodation_overrides: dict[str, EnumAccommodationType] = Field(
        default_factory=dict,
        description="Explicit overrides for specific dependencies",
    )
    test_execution_steps: list[ModelTestExecutionStep] = Field(
        description="Steps to execute for this test workflow",
    )
    setup_requirements: list[str] = Field(
        default_factory=list,
        description="Requirements that must be met before running this workflow",
    )
    cleanup_actions: list[str] = Field(
        default_factory=list,
        description="Actions to perform after workflow completion",
    )

    @field_validator("test_execution_steps")
    @classmethod
    def validate_test_steps_not_empty(cls, v):
        """Validate that test workflows have at least one execution step."""
        if not v:
            msg = "Test workflows must have at least one execution step"
            raise ValueError(msg)
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "workflow_id": "pure_functional_transformation_with_adaptive_accommodation",
                    "workflow_description": "Test text transformation with adaptive dependency accommodation",
                    "workflow_priority": "high",
                    "accommodation_strategy": "hybrid_smart",
                    "accommodation_overrides": {"llm_response_service": "mock"},
                    "test_execution_steps": [
                        {
                            "step_id": "setup_accommodated_dependencies",
                            "step_action": "accommodate_dependencies",
                            "step_parameters": {"strategy": "hybrid_smart"},
                        },
                    ],
                },
            ],
        }
    )


class ModelWorkflowTestingConfiguration(BaseModel):
    """Main configuration model for workflow testing"""

    workflow_testing_version: ModelSemVer = Field(
        description="Version of the workflow testing configuration",
    )
    tool_name: str = Field(description="Name of the tool being tested")
    tool_version: ModelSemVer = Field(description="Version of the tool being tested")
    description: str = Field(
        description="Description of the workflow testing configuration",
    )
    dependency_flexibility: ModelDependencyFlexibility = Field(
        description="Configuration for dependency flexibility",
    )
    dependency_accommodation: dict[str, ModelDependencyAccommodation] = Field(
        description="Configuration for individual dependency accommodations",
    )
    test_workflows: list[ModelTestWorkflow] = Field(
        description="List of test workflows to execute",
    )
    test_contexts: list[EnumTestContext] = Field(
        default_factory=lambda: [EnumTestContext.LOCAL_DEVELOPMENT],
        description="Contexts in which these tests should run",
    )

    @field_validator("test_workflows")
    @classmethod
    def validate_workflows_not_empty(cls, v):
        """Validate that there is at least one test workflow."""
        if not v:
            msg = (
                "Workflow testing configuration must include at least one test workflow"
            )
            raise ValueError(
                msg,
            )
        return v

    @field_validator("test_workflows")
    @classmethod
    def validate_unique_workflow_ids(cls, v):
        """Validate that all workflow IDs are unique."""
        workflow_ids = [workflow.workflow_id for workflow in v]
        if len(workflow_ids) != len(set(workflow_ids)):
            msg = "All test workflow IDs must be unique"
            raise ValueError(msg)
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "workflow_testing_version": {"major": 1, "minor": 0, "patch": 0},
                    "tool_name": "canary_pure_tool",
                    "tool_version": {"major": 1, "minor": 0, "patch": 0},
                    "description": "Comprehensive workflow testing for canary pure functional tool",
                    "dependency_flexibility": {
                        "accommodation_levels": [
                            "full_real",
                            "full_mock",
                            "hybrid_smart",
                        ],
                        "default_accommodation_strategy": "hybrid_smart",
                    },
                    "dependency_accommodation": {},
                    "test_workflows": [],
                    "test_contexts": ["local_development", "ci_cd_environment"],
                },
            ],
        }
    )
