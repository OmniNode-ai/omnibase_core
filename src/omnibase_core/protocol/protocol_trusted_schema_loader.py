from abc import abstractmethod
from typing import Any, Protocol

from omnibase_core.models.common.model_validation_result import ModelValidationResult


class ProtocolTrustedSchemaLoader(Protocol):
    """Protocol for secure schema loading and validation"""

    @abstractmethod
    def is_path_safe(self, path_str: str) -> tuple[bool, str]:
        """Check if a path is safe for schema loading"""
        ...

    @abstractmethod
    def load_schema_safely(self, schema_path: str) -> ModelValidationResult:
        """Safely load a schema file with security validation"""
        ...

    @abstractmethod
    def resolve_ref_safely(self, ref_string: str) -> ModelValidationResult:
        """Safely resolve a $ref string with security validation"""
        ...

    @abstractmethod
    def get_security_audit(self) -> list[dict[str, Any]]:
        """Get security audit trail"""
        ...

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear schema cache"""
        ...

    @abstractmethod
    def get_approved_roots(self) -> list[str]:
        """Get list of approved schema root paths"""
        ...
