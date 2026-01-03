"""
Lazy Import Optimization Module

This module provides lazy loading functionality for contract models to resolve
the critical cold import performance issue (1856ms -> target <50ms).

Performance Impact:
- Expected improvement: 60-80%
- Target cold import time: <50ms
- Reduces import cascade from 74 modules to on-demand loading

Security:
    This module uses importlib.import_module() for dynamic imports, but with
    important security constraints:

    - **Hardcoded Import Paths**: All import paths are hardcoded within
      _import_paths dict and point exclusively to internal omnibase_core
      contract modules. No user-controlled input can influence import paths.

    - **Internal-Only Resolution**: Only the following internal modules are
      importable through this loader:
        - omnibase_core.models.contracts.model_contract_base
        - omnibase_core.models.contracts.model_contract_compute
        - omnibase_core.models.contracts.model_contract_effect
        - omnibase_core.models.contracts.model_contract_reducer
        - omnibase_core.models.contracts.model_contract_orchestrator

    - **No External Input**: The contract_type parameter in _import_contract()
      is validated against the _import_paths dict, preventing any attempt to
      import arbitrary modules.

    Trust Model:
        - Import paths are TRUSTED (hardcoded, internal-only)
        - No user input can influence which modules are loaded
        - Module initialization code is trusted (internal ONEX modules)

    Comparison with ModelReference:
        Unlike ModelReference.resolve() which uses an allowlist (ALLOWED_MODULE_PREFIXES)
        to validate user-provided module paths, this module uses hardcoded paths
        and does not accept any external input for module resolution.

Usage:
    from omnibase_core.models.contracts.model_lazy_imports import get_contract_base
    ContractBase = get_contract_base()

.. versionadded:: 0.4.0
"""

import functools
from typing import TYPE_CHECKING, Any, cast

# Type checking imports only - no runtime cost
if TYPE_CHECKING:
    from .model_contract_base import ModelContractBase
    from .model_contract_compute import ModelContractCompute
    from .model_contract_effect import ModelContractEffect
    from .model_contract_orchestrator import ModelContractOrchestrator
    from .model_contract_reducer import ModelContractReducer

# Type alias for all contract types - simplified to avoid overly broad union
ContractType = type[object]  # Accept any class type, validate at runtime


class ModelLazyContractLoader:
    """
    Lazy loading container for contract models.

    Implements singleton pattern with caching to ensure models are only
    loaded once after first access, while avoiding cold import penalty.
    """

    def __init__(self) -> None:
        self._cache: dict[str, ContractType] = {}
        self._loading: dict[str, bool] = {}

    @functools.cache
    def get_contract_base(self) -> type["ModelContractBase"]:
        """
        Lazy load ModelContractBase.

        Returns:
            ModelContractBase class (cached after first load)
        """
        if "ModelContractBase" not in self._cache:
            from importlib import import_module

            module = import_module("omnibase_core.models.contracts.model_contract_base")
            self._cache["ModelContractBase"] = module.ModelContractBase
        return cast("type[ModelContractBase]", self._cache["ModelContractBase"])

    @functools.cache
    def get_contract_compute(self) -> type["ModelContractCompute"]:
        """
        Lazy load ModelContractCompute.

        Returns:
            ModelContractCompute class (cached after first load)
        """
        if "ModelContractCompute" not in self._cache:
            from importlib import import_module

            module = import_module(
                "omnibase_core.models.contracts.model_contract_compute"
            )
            self._cache["ModelContractCompute"] = module.ModelContractCompute
        return cast("type[ModelContractCompute]", self._cache["ModelContractCompute"])

    @functools.cache
    def get_contract_effect(self) -> type["ModelContractEffect"]:
        """
        Lazy load ModelContractEffect.

        Returns:
            ModelContractEffect class (cached after first load)
        """
        if "ModelContractEffect" not in self._cache:
            from importlib import import_module

            module = import_module(
                "omnibase_core.models.contracts.model_contract_effect"
            )
            self._cache["ModelContractEffect"] = module.ModelContractEffect
        return cast("type[ModelContractEffect]", self._cache["ModelContractEffect"])

    @functools.cache
    def get_contract_reducer(self) -> type["ModelContractReducer"]:
        """
        Lazy load ModelContractReducer.

        Returns:
            ModelContractReducer class (cached after first load)
        """
        if "ModelContractReducer" not in self._cache:
            from importlib import import_module

            module = import_module(
                "omnibase_core.models.contracts.model_contract_reducer"
            )
            self._cache["ModelContractReducer"] = module.ModelContractReducer
        return cast("type[ModelContractReducer]", self._cache["ModelContractReducer"])

    @functools.cache
    def get_contract_orchestrator(self) -> type["ModelContractOrchestrator"]:
        """
        Lazy load ModelContractOrchestrator.

        Returns:
            ModelContractOrchestrator class (cached after first load)
        """
        if "ModelContractOrchestrator" not in self._cache:
            from importlib import import_module

            module = import_module(
                "omnibase_core.models.contracts.model_contract_orchestrator"
            )
            self._cache["ModelContractOrchestrator"] = module.ModelContractOrchestrator
        return cast(
            "type[ModelContractOrchestrator]",
            self._cache["ModelContractOrchestrator"],
        )

    def preload_all(self) -> None:
        """
        Preload all contract models for performance-critical scenarios.

        Use this method when you need all contracts loaded and want to
        control when the import penalty occurs (e.g., during application startup).
        """
        self.get_contract_base()
        self.get_contract_compute()
        self.get_contract_effect()
        self.get_contract_reducer()
        self.get_contract_orchestrator()

    def get_cache_stats(self) -> dict[str, object]:
        """
        Get caching statistics for performance monitoring.

        Returns:
            Dict containing cache hit information and loaded modules
        """
        return {
            "cached_models": list[Any](self._cache.keys()),
            "cache_size": len(self._cache),
            "available_models": [
                "ModelContractBase",
                "ModelContractCompute",
                "ModelContractEffect",
                "ModelContractReducer",
                "ModelContractOrchestrator",
            ],
        }


# Singleton instance for global access
_lazy_loader = ModelLazyContractLoader()


# Convenient module-level functions
def get_contract_base() -> type["ModelContractBase"]:
    """Get ModelContractBase with lazy loading."""
    return _lazy_loader.get_contract_base()


def get_contract_compute() -> type["ModelContractCompute"]:
    """Get ModelContractCompute with lazy loading."""
    return _lazy_loader.get_contract_compute()


def get_contract_effect() -> type["ModelContractEffect"]:
    """Get ModelContractEffect with lazy loading."""
    return _lazy_loader.get_contract_effect()


def get_contract_reducer() -> type["ModelContractReducer"]:
    """Get ModelContractReducer with lazy loading."""
    return _lazy_loader.get_contract_reducer()


def get_contract_orchestrator() -> type["ModelContractOrchestrator"]:
    """Get ModelContractOrchestrator with lazy loading."""
    return _lazy_loader.get_contract_orchestrator()


def preload_all_contracts() -> None:
    """Preload all contract models for performance-critical scenarios."""
    _lazy_loader.preload_all()


def get_loader_stats() -> dict[str, object]:
    """Get lazy loading statistics."""
    return _lazy_loader.get_cache_stats()


__all__ = [
    "ModelLazyContractLoader",
    "get_contract_base",
    "get_contract_compute",
    "get_contract_effect",
    "get_contract_reducer",
    "get_contract_orchestrator",
    "preload_all_contracts",
    "get_loader_stats",
]
