"""
Contract Profile Factory.

Provides typed default profile factories that produce fully valid contract
objects for each node type (orchestrator, reducer, effect, compute).

Design Decisions:
    - Generic factory returns ModelContractBase (simple, honest)
    - Specific factories return concrete models (precise, ergonomic)
    - Inheritance already matches reality - no unions or protocols needed

Usage:
    >>> from omnibase_core.factories import get_default_contract_profile
    >>> from omnibase_core.enums import EnumNodeType
    >>> contract = get_default_contract_profile(
    ...     node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
    ...     profile="orchestrator_safe",
    ... )
"""

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums import EnumNodeKind, EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import OnexError
from omnibase_core.models.contracts import (
    ModelContractBase,
    ModelContractCompute,
    ModelContractEffect,
    ModelContractOrchestrator,
    ModelContractReducer,
)


def _get_node_kind(node_type: EnumNodeType) -> EnumNodeKind | None:
    """
    Map EnumNodeType to EnumNodeKind for profile lookup.

    Args:
        node_type: The node type to classify.

    Returns:
        The corresponding EnumNodeKind, or None if unknown.
    """
    node_type_str = node_type.value.lower()
    if "orchestrator" in node_type_str:
        return EnumNodeKind.ORCHESTRATOR
    elif "reducer" in node_type_str:
        return EnumNodeKind.REDUCER
    elif "effect" in node_type_str:
        return EnumNodeKind.EFFECT
    elif "compute" in node_type_str:
        return EnumNodeKind.COMPUTE
    return None


# Node kind to kind name mapping
# Thread Safety: This mapping is immutable after module load.
_NODE_KIND_NAMES: dict[EnumNodeKind, str] = {
    EnumNodeKind.ORCHESTRATOR: "orchestrator",
    EnumNodeKind.REDUCER: "reducer",
    EnumNodeKind.EFFECT: "effect",
    EnumNodeKind.COMPUTE: "compute",
}


def get_default_contract_profile(
    node_type: EnumNodeType,
    profile: str,
    version: str = "1.0.0",
) -> ModelContractBase:
    """
    Get a default contract profile for any node type.

    Generic factory that returns ModelContractBase. Use specific factory
    functions for type-safe returns.

    Args:
        node_type: The node type to get a profile for.
        profile: The profile name (e.g., "orchestrator_safe").
        version: The version to apply to the contract (default: "1.0.0").

    Returns:
        A fully valid contract with safe defaults.

    Raises:
        OnexError: If the profile is unknown for the node type.

    Example:
        >>> contract = get_default_contract_profile(
        ...     node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
        ...     profile="orchestrator_safe",
        ... )
    """
    return _get_default_contract_profile_impl(node_type, profile, version)


@standard_error_handling("Contract profile resolution")
def _get_default_contract_profile_impl(
    node_type: EnumNodeType,
    profile: str,
    version: str = "1.0.0",
) -> ModelContractBase:
    """Internal implementation of get_default_contract_profile."""
    # Import profile modules lazily to avoid circular imports
    from omnibase_core.factories.profiles import (
        COMPUTE_PROFILES,
        EFFECT_PROFILES,
        ORCHESTRATOR_PROFILES,
        REDUCER_PROFILES,
    )

    node_kind = _get_node_kind(node_type)
    if node_kind is None:
        raise OnexError(
            message=f"Unknown node type '{node_type}'. "
            "Expected orchestrator, reducer, effect, or compute.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    # Get the appropriate registry based on node kind
    # Thread Safety: Registries are immutable after module load.
    kind_name = _NODE_KIND_NAMES[node_kind]

    if node_kind == EnumNodeKind.ORCHESTRATOR:
        if profile not in ORCHESTRATOR_PROFILES:
            available = ", ".join(ORCHESTRATOR_PROFILES.keys())
            raise OnexError(
                message=f"Unknown profile '{profile}' for {kind_name}. "
                f"Available profiles: {available}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return ORCHESTRATOR_PROFILES[profile](version)

    if node_kind == EnumNodeKind.REDUCER:
        if profile not in REDUCER_PROFILES:
            available = ", ".join(REDUCER_PROFILES.keys())
            raise OnexError(
                message=f"Unknown profile '{profile}' for {kind_name}. "
                f"Available profiles: {available}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return REDUCER_PROFILES[profile](version)

    if node_kind == EnumNodeKind.EFFECT:
        if profile not in EFFECT_PROFILES:
            available = ", ".join(EFFECT_PROFILES.keys())
            raise OnexError(
                message=f"Unknown profile '{profile}' for {kind_name}. "
                f"Available profiles: {available}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return EFFECT_PROFILES[profile](version)

    # Must be COMPUTE at this point
    if profile not in COMPUTE_PROFILES:
        available = ", ".join(COMPUTE_PROFILES.keys())
        raise OnexError(
            message=f"Unknown profile '{profile}' for {kind_name}. "
            f"Available profiles: {available}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return COMPUTE_PROFILES[profile](version)


def get_default_orchestrator_profile(
    profile: str,
    version: str = "1.0.0",
) -> ModelContractOrchestrator:
    """
    Get a default orchestrator contract profile.

    Specific factory with precise return type.

    Args:
        profile: The profile name (e.g., "orchestrator_safe").
        version: The version to apply to the contract (default: "1.0.0").

    Returns:
        A fully valid orchestrator contract with safe defaults.

    Raises:
        OnexError: If the profile is unknown.

    Example:
        >>> contract = get_default_orchestrator_profile("orchestrator_safe")
    """
    return _get_default_orchestrator_profile_impl(profile, version)


@standard_error_handling("Orchestrator profile resolution")
def _get_default_orchestrator_profile_impl(
    profile: str,
    version: str = "1.0.0",
) -> ModelContractOrchestrator:
    """Internal implementation of get_default_orchestrator_profile."""
    from omnibase_core.factories.profiles import ORCHESTRATOR_PROFILES

    if profile not in ORCHESTRATOR_PROFILES:
        available = ", ".join(ORCHESTRATOR_PROFILES.keys())
        raise OnexError(
            message=f"Unknown profile '{profile}' for orchestrator. "
            f"Available profiles: {available}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return ORCHESTRATOR_PROFILES[profile](version)


def get_default_reducer_profile(
    profile: str,
    version: str = "1.0.0",
) -> ModelContractReducer:
    """
    Get a default reducer contract profile.

    Specific factory with precise return type.

    Args:
        profile: The profile name (e.g., "reducer_fsm_basic").
        version: The version to apply to the contract (default: "1.0.0").

    Returns:
        A fully valid reducer contract with safe defaults.

    Raises:
        OnexError: If the profile is unknown.

    Example:
        >>> contract = get_default_reducer_profile("reducer_fsm_basic")
    """
    return _get_default_reducer_profile_impl(profile, version)


@standard_error_handling("Reducer profile resolution")
def _get_default_reducer_profile_impl(
    profile: str,
    version: str = "1.0.0",
) -> ModelContractReducer:
    """Internal implementation of get_default_reducer_profile."""
    from omnibase_core.factories.profiles import REDUCER_PROFILES

    if profile not in REDUCER_PROFILES:
        available = ", ".join(REDUCER_PROFILES.keys())
        raise OnexError(
            message=f"Unknown profile '{profile}' for reducer. "
            f"Available profiles: {available}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return REDUCER_PROFILES[profile](version)


def get_default_effect_profile(
    profile: str,
    version: str = "1.0.0",
) -> ModelContractEffect:
    """
    Get a default effect contract profile.

    Specific factory with precise return type.

    Args:
        profile: The profile name (e.g., "effect_idempotent").
        version: The version to apply to the contract (default: "1.0.0").

    Returns:
        A fully valid effect contract with safe defaults.

    Raises:
        OnexError: If the profile is unknown.

    Example:
        >>> contract = get_default_effect_profile("effect_idempotent")
    """
    return _get_default_effect_profile_impl(profile, version)


@standard_error_handling("Effect profile resolution")
def _get_default_effect_profile_impl(
    profile: str,
    version: str = "1.0.0",
) -> ModelContractEffect:
    """Internal implementation of get_default_effect_profile."""
    from omnibase_core.factories.profiles import EFFECT_PROFILES

    if profile not in EFFECT_PROFILES:
        available = ", ".join(EFFECT_PROFILES.keys())
        raise OnexError(
            message=f"Unknown profile '{profile}' for effect. "
            f"Available profiles: {available}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return EFFECT_PROFILES[profile](version)


def get_default_compute_profile(
    profile: str,
    version: str = "1.0.0",
) -> ModelContractCompute:
    """
    Get a default compute contract profile.

    Specific factory with precise return type.

    Args:
        profile: The profile name (e.g., "compute_pure").
        version: The version to apply to the contract (default: "1.0.0").

    Returns:
        A fully valid compute contract with safe defaults.

    Raises:
        OnexError: If the profile is unknown.

    Example:
        >>> contract = get_default_compute_profile("compute_pure")
    """
    return _get_default_compute_profile_impl(profile, version)


@standard_error_handling("Compute profile resolution")
def _get_default_compute_profile_impl(
    profile: str,
    version: str = "1.0.0",
) -> ModelContractCompute:
    """Internal implementation of get_default_compute_profile."""
    from omnibase_core.factories.profiles import COMPUTE_PROFILES

    if profile not in COMPUTE_PROFILES:
        available = ", ".join(COMPUTE_PROFILES.keys())
        raise OnexError(
            message=f"Unknown profile '{profile}' for compute. "
            f"Available profiles: {available}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return COMPUTE_PROFILES[profile](version)


def available_profiles(node_type: EnumNodeType) -> list[str]:
    """
    List available profiles for a node type.

    Args:
        node_type: The node type to get profiles for.

    Returns:
        List of available profile names.

    Example:
        >>> profiles = available_profiles(EnumNodeType.ORCHESTRATOR_GENERIC)
        >>> print(profiles)
        ['orchestrator_safe', 'orchestrator_parallel', 'orchestrator_resilient']
    """
    from omnibase_core.factories.profiles import (
        COMPUTE_PROFILES,
        EFFECT_PROFILES,
        ORCHESTRATOR_PROFILES,
        REDUCER_PROFILES,
    )

    node_kind = _get_node_kind(node_type)
    if node_kind is None:
        return []

    # Get the appropriate registry based on node kind
    # Thread Safety: Registries are immutable after module load.
    if node_kind == EnumNodeKind.ORCHESTRATOR:
        return list(ORCHESTRATOR_PROFILES.keys())
    elif node_kind == EnumNodeKind.REDUCER:
        return list(REDUCER_PROFILES.keys())
    elif node_kind == EnumNodeKind.EFFECT:
        return list(EFFECT_PROFILES.keys())
    else:
        return list(COMPUTE_PROFILES.keys())


class ContractProfileFactory:
    """
    Class-based factory implementing ContractProfileFactoryProtocol.

    Provides both get_profile and available_profiles methods.

    Example:
        >>> factory = ContractProfileFactory()
        >>> contract = factory.get_profile(
        ...     node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
        ...     profile="orchestrator_safe",
        ... )
    """

    def get_profile(
        self,
        node_type: EnumNodeType,
        profile: str,
        version: str = "1.0.0",
    ) -> ModelContractBase:
        """Get a default contract profile."""
        return get_default_contract_profile(node_type, profile, version)

    def available_profiles(self, node_type: EnumNodeType) -> list[str]:
        """List available profiles for a node type."""
        return available_profiles(node_type)
