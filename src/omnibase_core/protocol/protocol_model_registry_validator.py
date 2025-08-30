from abc import abstractmethod
from typing import Any, Dict, List

from typing_extensions import Protocol

from omnibase_core.model.registry.model_registry_health_report import \
    ModelRegistryHealthReport
from omnibase_core.model.validation.model_validation_result import \
    ModelValidationResult


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
    def detect_conflicts(self) -> List[str]:
        """Detect conflicts across all registries"""
        ...

    @abstractmethod
    def verify_contract_compliance(self, contract_path: str) -> ModelValidationResult:
        """Verify a contract file complies with schema requirements"""
        ...

    @abstractmethod
    def lock_verified_models(self) -> Dict[str, Any]:
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
