from abc import abstractmethod
from typing import Any, Protocol

from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.registry.model_registry_health_report import (
    ModelRegistryHealthReport,
)


class ProtocolModelRegistryValidator(Protocol):
    """Protocol for validating dynamic model registries and detecting conflicts"""

    @abstractmethod
    def validate_action_registry(self) -> ModelValidationResult:
        """Validate action registry for conflicts and compliance"""
        ...

    @abstractmethod
    def validate_event_type_registry(self) -> ModelValidationResult:
        """Validate event type registry for conflicts and compliance"""
        ...

    @abstractmethod
    def validate_capability_registry(self) -> ModelValidationResult:
        """Validate capability registry for conflicts and compliance"""
        ...

    @abstractmethod
    def validate_node_reference_registry(self) -> ModelValidationResult:
        """Validate node reference registry for conflicts and compliance"""
        ...

    @abstractmethod
    def validate_all_registries(self) -> ModelValidationResult:
        """Validate all dynamic registries comprehensively"""
        ...

    @abstractmethod
    def detect_conflicts(self) -> list[str]:
        """Detect conflicts across all registries"""
        ...

    @abstractmethod
    def verify_contract_compliance(self, contract_path: str) -> ModelValidationResult:
        """Verify a contract file complies with schema requirements"""
        ...

    @abstractmethod
    def lock_verified_models(self) -> dict[str, Any]:
        """Lock verified models with version/timestamp/trust tags"""
        ...

    @abstractmethod
    def get_registry_health(self) -> ModelRegistryHealthReport:
        """Get overall health status of all registries"""
        ...

    @abstractmethod
    def audit_model_integrity(self) -> ModelValidationResult:
        """Audit integrity of all registered models"""
        ...
