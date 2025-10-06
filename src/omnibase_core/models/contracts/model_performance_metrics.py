from typing import Any, Dict, TypedDict, TypeVar

from omnibase_core.errors.error_codes import ModelOnexError

from omnibase_core.models.contracts.model_contract_base import ModelContractBase


"""
Fast Import Module - Aggressive Performance Optimization

CRITICAL: This module provides zero-import-time loading for contract models.
NO imports are executed at module level to eliminate cascade effects.

Performance Target: Module import <5ms, contract loading <50ms total
"""

from typing import TypedDict

# Type variables for proper typing
ContractType = TypeVar("ContractType", bound="ModelContractBase")


class ModelPerformanceMetrics(TypedDict):
    """Type-safe structure for performance measurement results."""

    module_load_time_ms: float
    factory_access_time_ms: float
    status: str
