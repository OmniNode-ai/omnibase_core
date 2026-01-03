from typing import TYPE_CHECKING, Any, TypeVar

from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Fast Import Module - Aggressive Performance Optimization

CRITICAL: This module provides zero-import-time loading for contract models.
NO imports are executed at module level to eliminate cascade effects.

Performance Target: Module import <5ms, contract loading <50ms total

Security:
    This module uses importlib.import_module() for dynamic imports, but with
    important security constraints:

    - **Hardcoded Import Paths**: All import paths are defined in the
      _import_paths dictionary within ModelFastContractFactory and point
      exclusively to internal omnibase_core contract modules.

    - **Validated Contract Types**: The _import_contract() method only accepts
      contract_type values that exist as keys in _import_paths. Unknown types
      raise ModelOnexError with VALIDATION_ERROR code.

    - **Internal-Only Resolution**: Only these modules can be imported:
        - omnibase_core.models.contracts.model_contract_base
        - omnibase_core.models.contracts.model_contract_compute
        - omnibase_core.models.contracts.model_contract_effect
        - omnibase_core.models.contracts.model_contract_reducer
        - omnibase_core.models.contracts.model_contract_orchestrator

    Trust Model:
        - Import paths are TRUSTED (hardcoded constants)
        - contract_type parameter is validated against known keys only
        - No user-controlled strings are used in import_module() calls
        - Module initialization code is trusted (internal ONEX modules)

    Comparison with ModelReference:
        This module differs from ModelReference.resolve() in that it does not
        accept arbitrary module paths. ModelReference uses ALLOWED_MODULE_PREFIXES
        to validate external input, while this module uses a closed set of
        hardcoded paths with no external input possible.

.. versionadded:: 0.4.0
"""

from typing import cast

# NO RUNTIME IMPORTS AT MODULE LEVEL
# All imports moved to function level to eliminate cascade

# Type variables for proper typing
ContractType = TypeVar("ContractType", bound="ModelContractBase")

from omnibase_core.models.contracts.model_performance_monitor import (
    ModelPerformanceMonitor,
)

if TYPE_CHECKING:
    # Type hints only - no runtime cost
    from .model_contract_base import ModelContractBase
    from .model_contract_compute import ModelContractCompute
    from .model_contract_effect import ModelContractEffect
    from .model_contract_orchestrator import ModelContractOrchestrator
    from .model_contract_reducer import ModelContractReducer


class ModelFastContractFactory:
    """
    Zero-import-time contract factory.

    All imports happen on-demand at runtime, not at module import time.
    Uses sophisticated caching to ensure imports only happen once.
    """

    def __init__(self) -> None:
        self._contract_cache: dict[str, type[ModelContractBase]] = {}
        self._import_paths = {
            "base": "omnibase_core.models.contracts.model_contract_base",
            "compute": "omnibase_core.models.contracts.model_contract_compute",
            "effect": "omnibase_core.models.contracts.model_contract_effect",
            "reducer": "omnibase_core.models.contracts.model_contract_reducer",
            "orchestrator": "omnibase_core.models.contracts.model_contract_orchestrator",
        }

    def _import_contract(
        self,
        contract_type: str,
        class_name: str,
    ) -> type["ModelContractBase"]:
        """Import a contract class on-demand with caching."""
        # Function-level imports to maintain zero-import-time loading
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.common.model_error_context import ModelErrorContext
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        cache_key = f"{contract_type}_{class_name}"

        if cache_key in self._contract_cache:
            return self._contract_cache[cache_key]

        # Dynamic import at runtime only
        module_path = self._import_paths.get(contract_type)
        if not module_path:
            raise ModelOnexError(
                message=f"Unknown contract type: {contract_type}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        # Import the module dynamically
        import importlib

        module = importlib.import_module(module_path)

        # Get the class from the module
        contract_class = cast("type[ModelContractBase]", getattr(module, class_name))

        # Cache for future use
        self._contract_cache[cache_key] = contract_class

        return contract_class

    def get_base(self) -> type["ModelContractBase"]:
        """Get ModelContractBase with zero-import-time loading."""
        return self._import_contract("base", "ModelContractBase")

    def get_compute(self) -> type["ModelContractCompute"]:
        """Get ModelContractCompute with zero-import-time loading."""
        return cast(
            "type[ModelContractCompute]",
            self._import_contract("compute", "ModelContractCompute"),
        )

    def get_effect(self) -> type["ModelContractEffect"]:
        """Get ModelContractEffect with zero-import-time loading."""
        return cast(
            "type[ModelContractEffect]",
            self._import_contract("effect", "ModelContractEffect"),
        )

    def get_reducer(self) -> type["ModelContractReducer"]:
        """Get ModelContractReducer with zero-import-time loading."""
        return cast(
            "type[ModelContractReducer]",
            self._import_contract("reducer", "ModelContractReducer"),
        )

    def get_orchestrator(self) -> type["ModelContractOrchestrator"]:
        """Get ModelContractOrchestrator with zero-import-time loading."""
        return cast(
            "type[ModelContractOrchestrator]",
            self._import_contract("orchestrator", "ModelContractOrchestrator"),
        )

    def get_all_contracts(self) -> dict[str, type["ModelContractBase"]]:
        """Get all contract types (triggers loading of all contracts)."""
        return {
            "base": self.get_base(),
            "compute": self.get_compute(),
            "effect": self.get_effect(),
            "reducer": self.get_reducer(),
            "orchestrator": self.get_orchestrator(),
        }

    def get_stats(self) -> dict[str, object]:
        """Get factory statistics."""
        return {
            "cached_contracts": list[Any](self._contract_cache.keys()),
            "cache_size": len(self._contract_cache),
            "available_contracts": list[Any](self._import_paths.keys()),
        }


# Global factory instance
_factory = ModelFastContractFactory()


# Fast access functions - NO imports at module level
def base() -> type["ModelContractBase"]:
    """Get ModelContractBase (ultra-fast)."""
    return _factory.get_base()


def compute() -> type["ModelContractCompute"]:
    """Get ModelContractCompute (ultra-fast)."""
    return _factory.get_compute()


def effect() -> type["ModelContractEffect"]:
    """Get ModelContractEffect (ultra-fast)."""
    return _factory.get_effect()


def reducer() -> type["ModelContractReducer"]:
    """Get ModelContractReducer (ultra-fast)."""
    return _factory.get_reducer()


def orchestrator() -> type["ModelContractOrchestrator"]:
    """Get ModelContractOrchestrator (ultra-fast)."""
    return _factory.get_orchestrator()


def all_contracts() -> dict[str, type["ModelContractBase"]]:
    """Get all contract types."""
    return _factory.get_all_contracts()


def factory_stats() -> dict[str, object]:
    """Get factory performance statistics."""
    return _factory.get_stats()


# Ultra-fast contract creation helpers
def create_compute_contract(**kwargs: Any) -> "ModelContractCompute":
    """Create ModelContractCompute instance with fast loading.

    Note: Any type allows arbitrary keyword arguments which are validated by Pydantic at runtime.
    """
    ComputeContract = compute()
    return ComputeContract(**kwargs)


def create_effect_contract(**kwargs: Any) -> "ModelContractEffect":
    """Create ModelContractEffect instance with fast loading.

    Note: Any type allows arbitrary keyword arguments which are validated by Pydantic at runtime.
    """
    EffectContract = effect()
    return EffectContract(**kwargs)


def create_base_contract(**kwargs: Any) -> "ModelContractBase":
    """Create ModelContractBase instance with fast loading.

    Note: Any type allows arbitrary keyword arguments which are validated by Pydantic at runtime.
    """
    BaseContract = base()
    return BaseContract(**kwargs)


# Preloading functionality for performance-critical scenarios
def preload_critical_contracts() -> None:
    """
    Preload most commonly used contracts.

    Call this during application startup if you want to control when
    the import penalty occurs rather than on first access.
    """
    # Load in order of likely usage frequency
    compute()  # Most commonly used
    effect()  # Second most common
    base()  # Base class


def preload_all_contracts() -> None:
    """
    Preload all contract types.

    Use this if you know you'll need all contracts and want predictable
    startup time rather than lazy loading.
    """
    all_contracts()


# Performance monitoring

__all__ = [
    # Fast contract access
    "base",
    "compute",
    "effect",
    "reducer",
    "orchestrator",
    "all_contracts",
    # Creation helpers
    "create_compute_contract",
    "create_effect_contract",
    "create_base_contract",
    # Preloading
    "preload_critical_contracts",
    "preload_all_contracts",
    # Utilities
    "factory_stats",
    "ModelFastContractFactory",
    "ModelPerformanceMonitor",
]
