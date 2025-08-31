#!/usr/bin/env python3
"""
ONEX Workflow Testing Protocol Interfaces

This module defines protocol interfaces for the ONEX workflow testing system,
ensuring consistent behavior across different implementations.
"""

from abc import abstractmethod
from typing import Protocol

from omnibase_core.enums.enum_workflow_testing import (
    EnumAccommodationStrategy,
    EnumTestContext,
)
from omnibase_core.model.core.model_generic_value import ModelGenericValue
from omnibase_core.model.workflow_testing.model_accommodation_override_map import (
    ModelAccommodationOverrideMap,
)
from omnibase_core.model.workflow_testing.model_dependency_accommodation_map import (
    ModelDependencyAccommodationMap,
)
from omnibase_core.model.workflow_testing.model_mock_event_bus import (
    ModelMockEventBusConfig,
)
from omnibase_core.model.workflow_testing.model_mock_registry import (
    ModelMockRegistryConfig,
)
from omnibase_core.model.workflow_testing.model_service_availability_map import (
    ModelServiceAvailabilityMap,
)
from omnibase_core.model.workflow_testing.model_workflow_testing_configuration import (
    ModelMockDependencyConfig,
    ModelTestWorkflow,
    ModelWorkflowTestingConfiguration,
)
from omnibase_core.model.workflow_testing.model_workflow_testing_results import (
    ModelAccommodationResult,
    ModelTestWorkflowResult,
    ModelWorkflowTestingResults,
)


class ProtocolWorkflowTestingExecutor(Protocol):
    """Protocol for workflow testing execution orchestration"""

    @abstractmethod
    def execute_workflow_testing(
        self,
        configuration: ModelWorkflowTestingConfiguration,
        test_context: EnumTestContext = EnumTestContext.LOCAL_DEVELOPMENT,
    ) -> ModelWorkflowTestingResults:
        """
        Execute complete workflow testing based on configuration.

        Args:
            configuration: Complete workflow testing configuration
            test_context: Context in which tests are being executed

        Returns:
            ModelWorkflowTestingResults: Comprehensive testing results

        Raises:
            OnexError: If workflow testing execution fails
        """
        ...

    @abstractmethod
    def execute_test_scenario(
        self,
        scenario: ModelTestWorkflow,
        accommodation_results: list[ModelAccommodationResult],
    ) -> ModelTestWorkflowResult:
        """
        Execute a single test scenario with accommodated dependencies.

        Args:
            scenario: Test scenario to execute
            accommodation_results: Results of dependency accommodation

        Returns:
            ModelTestWorkflowResult: Results of scenario execution

        Raises:
            OnexError: If scenario execution fails
        """
        ...

    @abstractmethod
    def validate_testing_configuration(
        self,
        configuration: ModelWorkflowTestingConfiguration,
    ) -> bool:
        """
        Validate workflow testing configuration for completeness and correctness.

        Args:
            configuration: Configuration to validate

        Returns:
            bool: True if configuration is valid

        Raises:
            OnexError: If configuration validation fails
        """
        ...


class ProtocolDependencyAccommodationManager(Protocol):
    """Protocol for managing flexible dependency accommodation"""

    @abstractmethod
    def determine_accommodation_strategy(
        self,
        test_context: EnumTestContext,
        available_services: ModelServiceAvailabilityMap,
        user_strategy: EnumAccommodationStrategy,
    ) -> EnumAccommodationStrategy:
        """
        Determine optimal accommodation strategy based on context and availability.

        Args:
            test_context: Context in which tests are running
            available_services: Map of service names to availability status
            user_strategy: User-requested accommodation strategy

        Returns:
            EnumAccommodationStrategy: Optimal strategy to use
        """
        ...

    @abstractmethod
    def accommodate_dependencies(
        self,
        tool_instance: object,
        dependency_accommodations: ModelDependencyAccommodationMap,
        accommodation_strategy: EnumAccommodationStrategy,
        accommodation_overrides: ModelAccommodationOverrideMap,
    ) -> list[ModelAccommodationResult]:
        """
        Accommodate dependencies for a tool instance based on strategy.

        Args:
            tool_instance: Tool instance to inject dependencies into
            dependency_accommodations: Available accommodation options
            accommodation_strategy: Strategy to use for accommodation
            accommodation_overrides: Explicit overrides for specific dependencies

        Returns:
            List[ModelAccommodationResult]: Results of accommodation process

        Raises:
            OnexError: If dependency accommodation fails
        """
        ...

    @abstractmethod
    def cleanup_accommodated_dependencies(
        self,
        accommodation_results: list[ModelAccommodationResult],
    ) -> None:
        """
        Clean up resources from accommodated dependencies.

        Args:
            accommodation_results: Results from previous accommodation

        Raises:
            OnexError: If cleanup fails
        """
        ...


class ProtocolMockServiceProvider(Protocol):
    """Protocol for providing mock service implementations"""

    @abstractmethod
    def create_mock_service(
        self,
        service_interface: str,
        mock_configuration: ModelMockDependencyConfig,
    ) -> object:
        """
        Create a mock service instance based on interface and configuration.

        Args:
            service_interface: Protocol interface the mock must implement
            mock_configuration: Configuration for mock behavior

        Returns:
            object: Mock service instance implementing the interface

        Raises:
            OnexError: If mock service creation fails
        """
        ...

    @abstractmethod
    def validate_mock_behavior(
        self,
        mock_instance: object,
        expected_interface: str,
    ) -> bool:
        """
        Validate that mock service implements expected interface correctly.

        Args:
            mock_instance: Mock service instance to validate
            expected_interface: Interface the mock should implement

        Returns:
            bool: True if mock implements interface correctly

        Raises:
            OnexError: If validation fails
        """
        ...

    @abstractmethod
    def configure_mock_responses(
        self,
        mock_instance: object,
        response_configuration: ModelMockRegistryConfig | ModelMockEventBusConfig,
    ) -> None:
        """
        Configure deterministic responses for mock service.

        Args:
            mock_instance: Mock service instance to configure
            response_configuration: Configuration for mock responses

        Raises:
            OnexError: If configuration fails
        """
        ...


class ProtocolDeterministicResponseService(Protocol):
    """Protocol for managing deterministic responses for consistent testing"""

    @abstractmethod
    def get_deterministic_response(
        self,
        service_type: str,
        request_hash: str,
        fallback_strategy: str = "generate_mock",
    ) -> ModelGenericValue:
        """
        Get a deterministic response for a given request.

        Args:
            service_type: Type of service making the request
            request_hash: Hash of the request for consistency
            fallback_strategy: Strategy if no response is configured

        Returns:
            ModelGenericValue: Deterministic response data

        Raises:
            OnexError: If response generation fails
        """
        ...

    @abstractmethod
    def register_response_template(
        self,
        service_type: str,
        request_pattern: str,
        response_template: ModelGenericValue,
    ) -> None:
        """
        Register a response template for a specific request pattern.

        Args:
            service_type: Type of service this template applies to
            request_pattern: Pattern to match incoming requests
            response_template: Template for generating responses

        Raises:
            OnexError: If template registration fails
        """
        ...

    @abstractmethod
    def validate_response_consistency(
        self,
        service_type: str,
        request_hash: str,
        expected_response: ModelGenericValue,
    ) -> bool:
        """
        Validate that responses are consistent for the same request.

        Args:
            service_type: Type of service to validate
            request_hash: Hash of the request
            expected_response: Expected response for validation

        Returns:
            bool: True if response is consistent
        """
        ...


class ProtocolTestAssertionEngine(Protocol):
    """Protocol for validating test assertions and outcomes"""

    @abstractmethod
    def validate_assertion(
        self,
        actual_value: ModelGenericValue,
        expected_value: ModelGenericValue,
        validation_rule: str,
    ) -> bool:
        """
        Validate a single assertion based on a validation rule.

        Args:
            actual_value: Actual value from test execution
            expected_value: Expected value for comparison
            validation_rule: Rule to apply for validation

        Returns:
            bool: True if assertion passes
        """
        ...

    @abstractmethod
    def generate_assertion_message(
        self,
        actual_value: ModelGenericValue,
        expected_value: ModelGenericValue,
        validation_rule: str,
        assertion_passed: bool,
    ) -> str:
        """
        Generate descriptive message for assertion result.

        Args:
            actual_value: Actual value from test execution
            expected_value: Expected value for comparison
            validation_rule: Rule that was applied
            assertion_passed: Whether the assertion passed

        Returns:
            str: Descriptive message about the assertion result
        """
        ...


class ProtocolWorkflowTestingRegistry(Protocol):
    """Protocol for registry of workflow testing services"""

    @abstractmethod
    def register_accommodation_manager(
        self,
        manager_name: str,
        manager_instance: ProtocolDependencyAccommodationManager,
    ) -> None:
        """Register accommodation manager in the registry"""
        ...

    @abstractmethod
    def get_accommodation_manager(
        self,
        manager_name: str,
    ) -> ProtocolDependencyAccommodationManager:
        """Get accommodation manager from registry"""
        ...

    @abstractmethod
    def register_mock_service_provider(
        self,
        provider_name: str,
        provider_instance: ProtocolMockServiceProvider,
    ) -> None:
        """Register mock service provider in the registry"""
        ...

    @abstractmethod
    def get_mock_service_provider(
        self,
        provider_name: str,
    ) -> ProtocolMockServiceProvider:
        """Get mock service provider from registry"""
        ...

    @abstractmethod
    def register_deterministic_response_service(
        self,
        service_name: str,
        service_instance: ProtocolDeterministicResponseService,
    ) -> None:
        """Register deterministic response service in the registry"""
        ...

    @abstractmethod
    def get_deterministic_response_service(
        self,
        service_name: str,
    ) -> ProtocolDeterministicResponseService:
        """Get deterministic response service from registry"""
        ...
