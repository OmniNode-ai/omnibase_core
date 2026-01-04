"""
Contract Profile Factory Module.

Provides typed default profile factories that produce fully valid contract
objects for each node type (orchestrator, reducer, effect, compute).

Design Principle:
    "Contracts are serialized inputs to typed runtime models. Defaults live in code, not YAML."

Usage:
    >>> from omnibase_core.factories import get_default_contract_profile
    >>> from omnibase_core.enums import EnumNodeType
    >>> contract = get_default_contract_profile(
    ...     node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
    ...     profile="orchestrator_safe",
    ... )

    # Or use specific factory for type safety:
    >>> from omnibase_core.factories import get_default_orchestrator_profile
    >>> contract = get_default_orchestrator_profile(
    ...     profile="orchestrator_safe",
    ...     version="1.0.0",
    ... )
"""

from omnibase_core.factories.factory_contract_profile import (
    ContractProfileFactory,
    available_profiles,
    get_default_compute_profile,
    get_default_contract_profile,
    get_default_effect_profile,
    get_default_orchestrator_profile,
    get_default_reducer_profile,
)
from omnibase_core.protocols.protocol_contract_profile_factory import (
    ProtocolContractProfileFactory,
)

__all__ = [
    # Factory class
    "ContractProfileFactory",
    # Protocol
    "ProtocolContractProfileFactory",
    # Generic factory function
    "get_default_contract_profile",
    # Specific factory functions
    "get_default_orchestrator_profile",
    "get_default_reducer_profile",
    "get_default_effect_profile",
    "get_default_compute_profile",
    # Utility functions
    "available_profiles",
]
