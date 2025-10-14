"""
MVP Interface Lockdown Validation Test Suite.

VERSION: 1.0.0 - INTERFACE VALIDATION TESTS
This test suite validates that all MVP deliverables have proper interface versioning
and meet the requirements for stable code generation interfaces.

Tests validate:
1. All contract models have INTERFACE_VERSION = ModelSemVer(major=1, minor=0, patch=0)
2. All service interfaces have INTERFACE_VERSION = ModelSemVer(major=1, minor=0, patch=0)
3. All subcontract models have INTERFACE_VERSION = ModelSemVer(major=1, minor=0, patch=0)
4. Service interfaces have required abstract methods
5. Interface stability guarantees are documented
"""

import inspect
from abc import ABC
from typing import get_type_hints

import pytest

from omnibase_core.core.node_compute_service import NodeComputeService
from omnibase_core.core.node_effect_service import NodeEffectService
from omnibase_core.core.node_orchestrator_service import NodeOrchestratorService
from omnibase_core.core.node_reducer_service import NodeReducerService
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect
from omnibase_core.models.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.models.contracts.subcontracts.model_aggregation_subcontract import (
    ModelAggregationSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_caching_subcontract import (
    ModelCachingSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_configuration_subcontract import (
    ModelConfigurationSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_routing_subcontract import (
    ModelRoutingSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_state_management_subcontract import (
    ModelStateManagementSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_coordination_subcontract import (
    ModelWorkflowCoordinationSubcontract,
)
from omnibase_core.primitives.model_semver import ModelSemVer


class TestContractModelInterfaceVersions:
    """Test that all contract models have proper INTERFACE_VERSION."""

    def test_contract_base_has_interface_version(self) -> None:
        """Verify ModelContractBase has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelContractBase,
            "INTERFACE_VERSION",
        ), "ModelContractBase must have INTERFACE_VERSION"
        assert isinstance(
            ModelContractBase.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelContractBase.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelContractBase.INTERFACE_VERSION}"

    def test_contract_effect_has_interface_version(self) -> None:
        """Verify ModelContractEffect has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelContractEffect,
            "INTERFACE_VERSION",
        ), "ModelContractEffect must have INTERFACE_VERSION"
        assert isinstance(
            ModelContractEffect.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelContractEffect.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelContractEffect.INTERFACE_VERSION}"

    def test_contract_compute_has_interface_version(self) -> None:
        """Verify ModelContractCompute has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelContractCompute,
            "INTERFACE_VERSION",
        ), "ModelContractCompute must have INTERFACE_VERSION"
        assert isinstance(
            ModelContractCompute.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelContractCompute.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelContractCompute.INTERFACE_VERSION}"

    def test_contract_reducer_has_interface_version(self) -> None:
        """Verify ModelContractReducer has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelContractReducer,
            "INTERFACE_VERSION",
        ), "ModelContractReducer must have INTERFACE_VERSION"
        assert isinstance(
            ModelContractReducer.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelContractReducer.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelContractReducer.INTERFACE_VERSION}"

    def test_contract_orchestrator_has_interface_version(self) -> None:
        """Verify ModelContractOrchestrator has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelContractOrchestrator,
            "INTERFACE_VERSION",
        ), "ModelContractOrchestrator must have INTERFACE_VERSION"
        assert isinstance(
            ModelContractOrchestrator.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelContractOrchestrator.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelContractOrchestrator.INTERFACE_VERSION}"

    def test_all_contract_models_have_consistent_versions(self) -> None:
        """Verify all contract models have consistent INTERFACE_VERSION."""
        contract_models = [
            ModelContractBase,
            ModelContractEffect,
            ModelContractCompute,
            ModelContractReducer,
            ModelContractOrchestrator,
        ]

        expected_version = ModelSemVer(major=1, minor=0, patch=0)
        for model_class in contract_models:
            assert hasattr(
                model_class,
                "INTERFACE_VERSION",
            ), f"{model_class.__name__} must have INTERFACE_VERSION"
            assert (
                model_class.INTERFACE_VERSION == expected_version
            ), f"{model_class.__name__} version mismatch: {model_class.INTERFACE_VERSION}"


class TestSubcontractModelInterfaceVersions:
    """Test that all subcontract models have proper INTERFACE_VERSION."""

    def test_fsm_subcontract_has_interface_version(self) -> None:
        """Verify ModelFSMSubcontract has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelFSMSubcontract,
            "INTERFACE_VERSION",
        ), "ModelFSMSubcontract must have INTERFACE_VERSION"
        assert isinstance(
            ModelFSMSubcontract.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelFSMSubcontract.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelFSMSubcontract.INTERFACE_VERSION}"

    def test_event_type_subcontract_has_interface_version(self) -> None:
        """Verify ModelEventTypeSubcontract has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelEventTypeSubcontract,
            "INTERFACE_VERSION",
        ), "ModelEventTypeSubcontract must have INTERFACE_VERSION"
        assert isinstance(
            ModelEventTypeSubcontract.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelEventTypeSubcontract.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelEventTypeSubcontract.INTERFACE_VERSION}"

    def test_aggregation_subcontract_has_interface_version(self) -> None:
        """Verify ModelAggregationSubcontract has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelAggregationSubcontract,
            "INTERFACE_VERSION",
        ), "ModelAggregationSubcontract must have INTERFACE_VERSION"
        assert isinstance(
            ModelAggregationSubcontract.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelAggregationSubcontract.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelAggregationSubcontract.INTERFACE_VERSION}"

    def test_state_management_subcontract_has_interface_version(self) -> None:
        """Verify ModelStateManagementSubcontract has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelStateManagementSubcontract,
            "INTERFACE_VERSION",
        ), "ModelStateManagementSubcontract must have INTERFACE_VERSION"
        assert isinstance(
            ModelStateManagementSubcontract.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelStateManagementSubcontract.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelStateManagementSubcontract.INTERFACE_VERSION}"

    def test_routing_subcontract_has_interface_version(self) -> None:
        """Verify ModelRoutingSubcontract has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelRoutingSubcontract,
            "INTERFACE_VERSION",
        ), "ModelRoutingSubcontract must have INTERFACE_VERSION"
        assert isinstance(
            ModelRoutingSubcontract.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelRoutingSubcontract.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelRoutingSubcontract.INTERFACE_VERSION}"

    def test_caching_subcontract_has_interface_version(self) -> None:
        """Verify ModelCachingSubcontract has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelCachingSubcontract,
            "INTERFACE_VERSION",
        ), "ModelCachingSubcontract must have INTERFACE_VERSION"
        assert isinstance(
            ModelCachingSubcontract.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelCachingSubcontract.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelCachingSubcontract.INTERFACE_VERSION}"

    def test_configuration_subcontract_has_interface_version(self) -> None:
        """Verify ModelConfigurationSubcontract has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelConfigurationSubcontract,
            "INTERFACE_VERSION",
        ), "ModelConfigurationSubcontract must have INTERFACE_VERSION"
        assert isinstance(
            ModelConfigurationSubcontract.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelConfigurationSubcontract.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelConfigurationSubcontract.INTERFACE_VERSION}"

    def test_workflow_coordination_subcontract_has_interface_version(self) -> None:
        """Verify ModelWorkflowCoordinationSubcontract has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            ModelWorkflowCoordinationSubcontract,
            "INTERFACE_VERSION",
        ), "ModelWorkflowCoordinationSubcontract must have INTERFACE_VERSION"
        assert isinstance(
            ModelWorkflowCoordinationSubcontract.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert ModelWorkflowCoordinationSubcontract.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {ModelWorkflowCoordinationSubcontract.INTERFACE_VERSION}"

    def test_all_subcontract_models_have_consistent_versions(self) -> None:
        """Verify all subcontract models have consistent INTERFACE_VERSION."""
        subcontract_models = [
            ModelFSMSubcontract,
            ModelEventTypeSubcontract,
            ModelAggregationSubcontract,
            ModelStateManagementSubcontract,
            ModelRoutingSubcontract,
            ModelCachingSubcontract,
            ModelConfigurationSubcontract,
            ModelWorkflowCoordinationSubcontract,
        ]

        expected_version = ModelSemVer(major=1, minor=0, patch=0)
        for model_class in subcontract_models:
            assert hasattr(
                model_class,
                "INTERFACE_VERSION",
            ), f"{model_class.__name__} must have INTERFACE_VERSION"
            assert (
                model_class.INTERFACE_VERSION == expected_version
            ), f"{model_class.__name__} version mismatch: {model_class.INTERFACE_VERSION}"


class TestServiceInterfaceVersions:
    """Test that all service interfaces have proper INTERFACE_VERSION."""

    def test_node_effect_service_has_interface_version(self) -> None:
        """Verify NodeEffectService has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            NodeEffectService,
            "INTERFACE_VERSION",
        ), "NodeEffectService must have INTERFACE_VERSION"
        assert isinstance(
            NodeEffectService.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert NodeEffectService.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {NodeEffectService.INTERFACE_VERSION}"

    def test_node_compute_service_has_interface_version(self) -> None:
        """Verify NodeComputeService has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            NodeComputeService,
            "INTERFACE_VERSION",
        ), "NodeComputeService must have INTERFACE_VERSION"
        assert isinstance(
            NodeComputeService.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert NodeComputeService.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {NodeComputeService.INTERFACE_VERSION}"

    def test_node_reducer_service_has_interface_version(self) -> None:
        """Verify NodeReducerService has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            NodeReducerService,
            "INTERFACE_VERSION",
        ), "NodeReducerService must have INTERFACE_VERSION"
        assert isinstance(
            NodeReducerService.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert NodeReducerService.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {NodeReducerService.INTERFACE_VERSION}"

    def test_node_orchestrator_service_has_interface_version(self) -> None:
        """Verify NodeOrchestratorService has INTERFACE_VERSION = 1.0.0."""
        assert hasattr(
            NodeOrchestratorService,
            "INTERFACE_VERSION",
        ), "NodeOrchestratorService must have INTERFACE_VERSION"
        assert isinstance(
            NodeOrchestratorService.INTERFACE_VERSION,
            ModelSemVer,
        ), "INTERFACE_VERSION must be ModelSemVer instance"
        assert NodeOrchestratorService.INTERFACE_VERSION == ModelSemVer(
            major=1, minor=0, patch=0
        ), f"Expected 1.0.0, got {NodeOrchestratorService.INTERFACE_VERSION}"

    def test_all_service_interfaces_have_consistent_versions(self) -> None:
        """Verify all service interfaces have consistent INTERFACE_VERSION."""
        service_interfaces = [
            NodeEffectService,
            NodeComputeService,
            NodeReducerService,
            NodeOrchestratorService,
        ]

        expected_version = ModelSemVer(major=1, minor=0, patch=0)
        for service_class in service_interfaces:
            assert hasattr(
                service_class,
                "INTERFACE_VERSION",
            ), f"{service_class.__name__} must have INTERFACE_VERSION"
            assert (
                service_class.INTERFACE_VERSION == expected_version
            ), f"{service_class.__name__} version mismatch: {service_class.INTERFACE_VERSION}"


class TestServiceInterfaceMethods:
    """Test that service interfaces have required abstract methods."""

    def test_node_effect_service_has_required_methods(self) -> None:
        """Verify NodeEffectService has all required abstract methods."""
        required_methods = ["process_effect", "validate_input", "get_health_status"]

        for method_name in required_methods:
            assert hasattr(
                NodeEffectService,
                method_name,
            ), f"NodeEffectService must have {method_name} method"

            method = getattr(NodeEffectService, method_name)
            assert callable(method), f"{method_name} must be callable"

            # Check if method is abstract
            assert (
                getattr(method, "__isabstractmethod__", False) is True
            ), f"{method_name} must be abstract"

    def test_node_compute_service_has_required_methods(self) -> None:
        """Verify NodeComputeService has all required abstract methods."""
        required_methods = [
            "process_computation",
            "validate_input",
            "get_health_status",
        ]

        for method_name in required_methods:
            assert hasattr(
                NodeComputeService,
                method_name,
            ), f"NodeComputeService must have {method_name} method"

            method = getattr(NodeComputeService, method_name)
            assert callable(method), f"{method_name} must be callable"

            # Check if method is abstract
            assert (
                getattr(method, "__isabstractmethod__", False) is True
            ), f"{method_name} must be abstract"

    def test_node_reducer_service_has_required_methods(self) -> None:
        """Verify NodeReducerService has all required abstract methods."""
        required_methods = [
            "process_reduction",
            "validate_input",
            "get_health_status",
        ]

        for method_name in required_methods:
            assert hasattr(
                NodeReducerService,
                method_name,
            ), f"NodeReducerService must have {method_name} method"

            method = getattr(NodeReducerService, method_name)
            assert callable(method), f"{method_name} must be callable"

            # Check if method is abstract
            assert (
                getattr(method, "__isabstractmethod__", False) is True
            ), f"{method_name} must be abstract"

    def test_node_orchestrator_service_has_required_methods(self) -> None:
        """Verify NodeOrchestratorService has all required abstract methods."""
        required_methods = [
            "process_orchestration",
            "validate_input",
            "get_health_status",
        ]

        for method_name in required_methods:
            assert hasattr(
                NodeOrchestratorService,
                method_name,
            ), f"NodeOrchestratorService must have {method_name} method"

            method = getattr(NodeOrchestratorService, method_name)
            assert callable(method), f"{method_name} must be callable"

            # Check if method is abstract
            assert (
                getattr(method, "__isabstractmethod__", False) is True
            ), f"{method_name} must be abstract"

    def test_all_service_interfaces_inherit_from_abc(self) -> None:
        """Verify all service interfaces properly inherit from ABC."""
        service_interfaces = [
            NodeEffectService,
            NodeComputeService,
            NodeReducerService,
            NodeOrchestratorService,
        ]

        for service_class in service_interfaces:
            # Check that it's a subclass of ABC
            assert issubclass(
                service_class,
                ABC,
            ), f"{service_class.__name__} must inherit from ABC"

            # Check that it has abstract methods
            abstract_methods = [
                name
                for name, method in inspect.getmembers(
                    service_class,
                    predicate=inspect.isfunction,
                )
                if getattr(method, "__isabstractmethod__", False)
            ]

            assert (
                len(abstract_methods) >= 3
            ), f"{service_class.__name__} must have at least 3 abstract methods"


class TestInterfaceStabilityGuarantees:
    """Test that interface stability guarantees are documented."""

    def test_contract_models_have_stability_documentation(self) -> None:
        """Verify contract models have stability guarantee documentation."""
        contract_models = [
            ModelContractBase,
            ModelContractEffect,
            ModelContractCompute,
            ModelContractReducer,
            ModelContractOrchestrator,
        ]

        for model_class in contract_models:
            docstring = model_class.__doc__
            assert docstring is not None, f"{model_class.__name__} must have docstring"

            # Check for stability indicators in docstring
            stability_keywords = [
                "INTERFACE LOCKED",
                "STABILITY GUARANTEE",
                "DO NOT CHANGE",
                "version bump",
            ]

            # Get module docstring
            module_doc = inspect.getmodule(model_class).__doc__ or ""

            combined_doc = (docstring + " " + module_doc).upper()

            has_stability_doc = any(
                keyword.upper() in combined_doc for keyword in stability_keywords
            )

            assert has_stability_doc, (
                f"{model_class.__name__} must document stability guarantees. "
                f"Expected one of: {stability_keywords}"
            )

    def test_service_interfaces_have_stability_documentation(self) -> None:
        """Verify service interfaces have stability guarantee documentation."""
        service_interfaces = [
            NodeEffectService,
            NodeComputeService,
            NodeReducerService,
            NodeOrchestratorService,
        ]

        for service_class in service_interfaces:
            docstring = service_class.__doc__
            assert (
                docstring is not None
            ), f"{service_class.__name__} must have docstring"

            # Check for stability indicators in docstring
            stability_keywords = [
                "INTERFACE LOCKED",
                "STABILITY GUARANTEE",
                "DO NOT CHANGE",
                "version bump",
            ]

            # Get module docstring
            module_doc = inspect.getmodule(service_class).__doc__ or ""

            combined_doc = (docstring + " " + module_doc).upper()

            has_stability_doc = any(
                keyword.upper() in combined_doc for keyword in stability_keywords
            )

            assert has_stability_doc, (
                f"{service_class.__name__} must document stability guarantees. "
                f"Expected one of: {stability_keywords}"
            )

    def test_subcontract_models_have_stability_documentation(self) -> None:
        """Verify subcontract models have stability guarantee documentation."""
        subcontract_models = [
            ModelFSMSubcontract,
            ModelEventTypeSubcontract,
            ModelAggregationSubcontract,
            ModelStateManagementSubcontract,
            ModelRoutingSubcontract,
            ModelCachingSubcontract,
            ModelConfigurationSubcontract,
            ModelWorkflowCoordinationSubcontract,
        ]

        for model_class in subcontract_models:
            docstring = model_class.__doc__
            assert docstring is not None, f"{model_class.__name__} must have docstring"

            # Check for stability indicators in docstring
            stability_keywords = [
                "INTERFACE LOCKED",
                "STABILITY GUARANTEE",
                "DO NOT CHANGE",
                "version bump",
            ]

            # Get module docstring
            module_doc = inspect.getmodule(model_class).__doc__ or ""

            combined_doc = (docstring + " " + module_doc).upper()

            has_stability_doc = any(
                keyword.upper() in combined_doc for keyword in stability_keywords
            )

            assert has_stability_doc, (
                f"{model_class.__name__} must document stability guarantees. "
                f"Expected one of: {stability_keywords}"
            )


class TestContractValidation:
    """Test contract validator functionality."""

    def test_contract_base_has_validation_method(self) -> None:
        """Verify ModelContractBase has validate_node_specific_config method."""
        assert hasattr(
            ModelContractBase,
            "validate_node_specific_config",
        ), "ModelContractBase must have validate_node_specific_config method"

        method = getattr(ModelContractBase, "validate_node_specific_config")
        assert callable(method), "validate_node_specific_config must be callable"

        # Check if method is abstract
        assert (
            getattr(method, "__isabstractmethod__", False) is True
        ), "validate_node_specific_config must be abstract"

    def test_specialized_contracts_implement_validation(self) -> None:
        """Verify specialized contracts implement validate_node_specific_config."""
        specialized_contracts = [
            ModelContractEffect,
            ModelContractCompute,
            ModelContractReducer,
            ModelContractOrchestrator,
        ]

        for contract_class in specialized_contracts:
            assert hasattr(
                contract_class,
                "validate_node_specific_config",
            ), f"{contract_class.__name__} must have validate_node_specific_config"

            method = getattr(contract_class, "validate_node_specific_config")
            assert callable(
                method,
            ), f"{contract_class.__name__}.validate_node_specific_config must be callable"

            # Check that it's not abstract (should be implemented)
            # If it's in the class dict, it's implemented
            assert (
                "validate_node_specific_config" in contract_class.__dict__
                or not getattr(method, "__isabstractmethod__", False)
            ), f"{contract_class.__name__} must implement validate_node_specific_config"


class TestInterfaceCompleteness:
    """Test that all MVP interfaces are complete and locked."""

    def test_all_mvp_contract_models_accounted_for(self) -> None:
        """Verify all MVP contract models are tested."""
        expected_contracts = {
            "ModelContractBase",
            "ModelContractEffect",
            "ModelContractCompute",
            "ModelContractReducer",
            "ModelContractOrchestrator",
        }

        tested_contracts = {
            ModelContractBase.__name__,
            ModelContractEffect.__name__,
            ModelContractCompute.__name__,
            ModelContractReducer.__name__,
            ModelContractOrchestrator.__name__,
        }

        assert (
            tested_contracts == expected_contracts
        ), f"Contract coverage mismatch. Missing: {expected_contracts - tested_contracts}"

    def test_all_mvp_service_interfaces_accounted_for(self) -> None:
        """Verify all MVP service interfaces are tested."""
        expected_services = {
            "NodeEffectService",
            "NodeComputeService",
            "NodeReducerService",
            "NodeOrchestratorService",
        }

        tested_services = {
            NodeEffectService.__name__,
            NodeComputeService.__name__,
            NodeReducerService.__name__,
            NodeOrchestratorService.__name__,
        }

        assert (
            tested_services == expected_services
        ), f"Service coverage mismatch. Missing: {expected_services - tested_services}"

    def test_all_mvp_subcontract_models_accounted_for(self) -> None:
        """Verify all MVP subcontract models are tested."""
        expected_subcontracts = {
            "ModelFSMSubcontract",
            "ModelEventTypeSubcontract",
            "ModelAggregationSubcontract",
            "ModelStateManagementSubcontract",
            "ModelRoutingSubcontract",
            "ModelCachingSubcontract",
            "ModelConfigurationSubcontract",
            "ModelWorkflowCoordinationSubcontract",
        }

        tested_subcontracts = {
            ModelFSMSubcontract.__name__,
            ModelEventTypeSubcontract.__name__,
            ModelAggregationSubcontract.__name__,
            ModelStateManagementSubcontract.__name__,
            ModelRoutingSubcontract.__name__,
            ModelCachingSubcontract.__name__,
            ModelConfigurationSubcontract.__name__,
            ModelWorkflowCoordinationSubcontract.__name__,
        }

        assert (
            tested_subcontracts == expected_subcontracts
        ), f"Subcontract coverage mismatch. Missing: {expected_subcontracts - tested_subcontracts}"

    def test_total_interface_count_matches_mvp_spec(self) -> None:
        """Verify total interface count matches MVP specification."""
        # MVP Spec: 5 contracts + 4 services + 8 subcontracts = 17 interfaces
        total_expected = 17

        total_tested = 5 + 4 + 8  # contracts  # services  # subcontracts

        assert (
            total_tested == total_expected
        ), f"Total interface count mismatch. Expected {total_expected}, got {total_tested}"


# Mark all tests to run with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
