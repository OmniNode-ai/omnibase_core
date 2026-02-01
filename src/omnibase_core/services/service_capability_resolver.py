"""
ServiceCapabilityResolver - Resolves capability dependencies to provider bindings.

This service implements the ProtocolCapabilityResolver protocol, providing the
core resolution engine for matching capability-based dependencies declared in
handler contracts to concrete provider bindings.

Resolution Algorithm:
    1. Query registry for providers where capability in provider.capabilities
    2. Filter by hard constraints (requirements.must, requirements.forbid)
    3. Score remaining candidates by requirements.prefer satisfaction
    4. Apply profile weights and tie-break rules
    5. Apply selection policy:
       - auto_if_unique: auto-bind only if exactly one candidate
       - best_score: bind top scoring candidate
       - require_explicit: fail unless pinned
    6. Produce ModelBinding with full audit trail

Determinism Requirements:
    - Resolver produces stable ordering (sorts by provider_id before scoring)
    - Resolver stores all candidates and their scores
    - Resolver records why non-chosen candidates were rejected

Design Pattern:
    The ServiceCapabilityResolver is stateless and thread-safe. Each resolution
    operation is independent and does not maintain any internal state between
    calls. This makes it safe for concurrent use from multiple threads.

Related:
    - OMN-1155: ServiceCapabilityResolver implementation
    - OMN-1152: ModelCapabilityDependency (Capability Dependencies)
    - OMN-1153: ModelProviderDescriptor (Provider Registry)
    - OMN-1157: ModelBinding (Resolution Bindings)

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ServiceCapabilityResolver"]

import hashlib
import json
import logging
import time
from datetime import UTC, datetime

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.bindings.model_binding import ModelBinding
from omnibase_core.models.bindings.model_resolution_result import ModelResolutionResult
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)
from omnibase_core.protocols.resolution.protocol_capability_resolver import (
    ProtocolProfile,
    ProtocolProviderRegistry,
)
from omnibase_core.types.type_json import JsonType
from omnibase_core.types.typed_dict_resolution_audit_data import (
    TypedDictResolutionAuditData,
)

logger = logging.getLogger(__name__)

# Type alias for profile parameter (optional)
ModelProfile = ProtocolProfile | None


class ServiceCapabilityResolver:
    """
    Implementation of ProtocolCapabilityResolver for capability-to-provider resolution.

    This service resolves capability dependencies declared in handler contracts to
    concrete provider bindings. It implements a deterministic resolution algorithm
    that produces stable, auditable results.

    Resolution Process:
        1. **Provider Discovery**: Query the registry for providers offering the
           requested capability.

        2. **Hard Filtering**: Apply must/forbid constraints to eliminate
           non-matching providers.

        3. **Scoring**: Score remaining candidates based on prefer constraints.
           Each satisfied preference adds to the provider's score.

        4. **Selection**: Apply the dependency's selection policy to choose
           a provider:

           - ``auto_if_unique``: Select automatically only if exactly one
             candidate remains after filtering. Fail if zero or multiple.

           - ``best_score``: Select the highest-scoring candidate. Ties are
             broken by provider_id (lexicographic, ascending) for determinism.

           - ``require_explicit``: Never auto-select. Fail unless an explicit
             binding is provided via profile pinning.

        5. **Binding Creation**: Create a ModelBinding with full audit trail
           including resolution notes and candidate count.

    Thread Safety:
        This service is stateless and thread-safe. Each resolve() and resolve_all()
        call operates independently without shared mutable state.

    Determinism:
        All operations produce deterministic results:
        - Providers are sorted by provider_id before scoring
        - Tie-breaking uses lexicographic ordering of provider_id
        - All candidates and their scores are recorded

    Example:
        .. code-block:: python

            from omnibase_core.services.service_capability_resolver import (
                ServiceCapabilityResolver,
            )
            from omnibase_core.models.capabilities import ModelCapabilityDependency

            resolver = ServiceCapabilityResolver()

            # Resolve a single dependency
            dep = ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
            )
            binding = resolver.resolve(dep, registry)

            # Resolve multiple dependencies
            deps = [
                ModelCapabilityDependency(alias="db", capability="database.relational"),
                ModelCapabilityDependency(alias="cache", capability="cache.distributed"),
            ]
            result = resolver.resolve_all(deps, registry)

    See Also:
        - :class:`ProtocolCapabilityResolver`: Protocol this service implements
        - :class:`ModelCapabilityDependency`: Capability dependency model
        - :class:`ModelBinding`: Resolved binding model
        - :class:`ModelResolutionResult`: Batch resolution result model

    .. versionadded:: 0.4.0
    """

    @standard_error_handling("Capability resolution")
    def resolve(
        self,
        dependency: ModelCapabilityDependency,
        registry: ProtocolProviderRegistry,
        profile: ModelProfile | None = None,
    ) -> ModelBinding:
        """
        Resolve a single capability dependency to a provider binding.

        Implements the full resolution algorithm:
        1. Query registry for matching providers
        2. Filter by must/forbid constraints
        3. Score by prefer constraints
        4. Apply selection policy
        5. Create binding with audit trail

        Args:
            dependency: The capability dependency to resolve. Must have a valid
                capability identifier and may include requirements.
            registry: The provider registry to search for matching providers.
            profile: Optional profile for resolution preferences. Can influence
                provider selection through explicit pinning or weight adjustments.

        Returns:
            A ModelBinding connecting the dependency to a resolved provider.

        Raises:
            ModelOnexError: Resolution failures with error code REGISTRY_RESOLUTION_FAILED:
                - No providers found for the capability
                - No providers pass must/forbid filters
                - Multiple providers match with auto_if_unique policy (ambiguous)
                - require_explicit policy without explicit binding

        Example:
            .. code-block:: python

                dep = ModelCapabilityDependency(
                    alias="db",
                    capability="database.relational",
                    requirements=ModelRequirementSet(
                        must={"supports_transactions": True},
                    ),
                )
                binding = resolver.resolve(dep, registry)
                print(f"Resolved to: {binding.provider_id}")

        .. versionadded:: 0.4.0
        """
        # Delegate to _resolve_with_audit and discard audit data
        binding, _ = self._resolve_with_audit(dependency, registry, profile)
        return binding

    def resolve_all(
        self,
        dependencies: list[ModelCapabilityDependency],
        registry: ProtocolProviderRegistry,
        profile: ModelProfile | None = None,
    ) -> ModelResolutionResult:
        """
        Resolve all capability dependencies, returning bindings and a report.

        Batch resolution method that attempts to resolve multiple dependencies
        in a single operation. Returns a result object containing successful
        bindings and information about any failures.

        Unlike resolve(), this method does not raise exceptions for individual
        resolution failures. Failures are captured in the result object, allowing
        partial success scenarios.

        Args:
            dependencies: List of capability dependencies to resolve. Each
                dependency is resolved independently.
            registry: The provider registry to search for matching providers.
            profile: Optional profile for resolution preferences.

        Returns:
            A ModelResolutionResult containing:
            - Successful bindings mapped by dependency alias
            - Failed resolutions with error information
            - Resolution statistics and diagnostics
            - Overall success/failure status

        Example:
            .. code-block:: python

                deps = [
                    ModelCapabilityDependency(
                        alias="db",
                        capability="database.relational",
                    ),
                    ModelCapabilityDependency(
                        alias="cache",
                        capability="cache.distributed",
                    ),
                ]
                result = resolver.resolve_all(deps, registry)

                if result.is_successful:
                    print("All dependencies resolved")
                else:
                    for error in result.errors:
                        print(f"Error: {error}")

        .. versionadded:: 0.4.0
        """
        return self._resolve_all_impl(dependencies, registry, profile)

    @standard_error_handling("Batch capability resolution")
    def _resolve_all_impl(
        self,
        dependencies: list[ModelCapabilityDependency],
        registry: ProtocolProviderRegistry,
        profile: ModelProfile | None = None,
    ) -> ModelResolutionResult:
        """Internal implementation of resolve_all."""
        start_time = time.perf_counter()

        bindings: dict[str, ModelBinding] = {}
        errors: list[str] = []
        candidates_by_alias: dict[str, list[str]] = {}
        scores_by_alias: dict[str, dict[str, float]] = {}
        rejection_reasons: dict[str, dict[str, str]] = {}

        for dep in dependencies:
            try:
                # Design Note: Use _resolve_with_audit() directly rather than resolve().
                # This avoids redundant work that would occur if calling resolve():
                # - resolve() discards audit data, requiring re-computation here
                # - Direct call captures audit data (candidates, scores, rejections)
                #   in a single pass through the resolution algorithm
                # Both resolve() and resolve_all() share _resolve_with_audit() for DRY.
                binding, audit = self._resolve_with_audit(dep, registry, profile)

                # Store the binding
                bindings[dep.alias] = binding

                # Extract audit data
                candidates_by_alias[dep.alias] = audit["candidates"]
                if audit["scores"]:
                    scores_by_alias[dep.alias] = audit["scores"]
                if audit["rejection_reasons"]:
                    rejection_reasons[dep.alias] = audit["rejection_reasons"]

            except ModelOnexError as e:
                error_msg = (
                    f"Failed to resolve '{dep.alias}' ({dep.capability}): {e.message}"
                )
                errors.append(error_msg)
                logger.warning("Resolution failed for '%s': %s", dep.alias, e.message)

        end_time = time.perf_counter()
        resolution_duration_ms = (end_time - start_time) * 1000

        success = len(errors) == 0
        profile_id = self._get_profile_id(profile)

        return ModelResolutionResult(
            bindings=bindings,
            success=success,
            candidates_by_alias=candidates_by_alias,
            scores_by_alias=scores_by_alias,
            rejection_reasons=rejection_reasons,
            resolved_at=datetime.now(UTC),
            resolution_duration_ms=resolution_duration_ms,
            resolution_profile=profile_id,
            errors=errors,
        )

    def _resolve_with_audit(
        self,
        dependency: ModelCapabilityDependency,
        registry: ProtocolProviderRegistry,
        profile: ModelProfile | None = None,
    ) -> tuple[ModelBinding, TypedDictResolutionAuditData]:
        """
        Internal method that resolves a dependency and returns audit data.

        This method performs the full resolution algorithm and captures detailed
        audit information about the resolution process. It is used by both
        resolve() and resolve_all() to avoid duplicating resolution logic.

        Args:
            dependency: The capability dependency to resolve.
            registry: The provider registry to search for matching providers.
            profile: Optional profile for resolution preferences.

        Returns:
            A tuple of (binding, audit_data) where:
            - binding: The resolved ModelBinding
            - audit_data: A dict containing:
                - candidates: List of all provider IDs considered
                - scores: Dict of provider_id -> score for filtered providers
                - rejection_reasons: Dict of provider_id -> reason for rejected providers

        Raises:
            ModelOnexError: Resolution failures (same as resolve()).
        """
        # Step 1: Query registry for providers offering this capability
        providers = registry.get_providers_for_capability(dependency.capability)

        if not providers:
            raise ModelOnexError(
                message=(
                    f"No providers found for capability '{dependency.capability}'. "
                    f"Ensure at least one provider is registered with this capability."
                ),
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
                context={
                    "alias": dependency.alias,
                    "capability": dependency.capability,
                },
            )

        # Sort providers by provider_id for deterministic ordering
        sorted_providers = sorted(providers, key=lambda p: p.provider_id)

        # Track candidates for audit
        candidates = [str(p.provider_id) for p in sorted_providers]

        # Step 2: Filter by hard constraints (must/forbid)
        filtered_providers: list[ModelProviderDescriptor] = []
        rejection_reasons: dict[str, str] = {}

        for provider in sorted_providers:
            rejection = self._check_hard_constraints(provider, dependency)
            if rejection:
                rejection_reasons[str(provider.provider_id)] = rejection
            else:
                filtered_providers.append(provider)

        if not filtered_providers:
            raise ModelOnexError(
                message=(
                    f"No providers for capability '{dependency.capability}' "
                    f"satisfy the required constraints. "
                    f"{len(sorted_providers)} provider(s) were rejected."
                ),
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
                context={
                    "alias": dependency.alias,
                    "capability": dependency.capability,
                    "candidates_considered": len(sorted_providers),
                    "rejection_reasons": rejection_reasons,
                },
            )

        # Step 3: Score remaining candidates by prefer satisfaction
        scored_providers = self._score_providers(
            filtered_providers, dependency, profile
        )

        # Track scores for audit
        scores = {str(p.provider_id): score for p, score in scored_providers}

        # Step 4: Apply selection policy
        selected_provider, resolution_notes = self._apply_selection_policy(
            scored_providers,
            dependency,
            profile,
            len(sorted_providers),
            rejection_reasons,
        )

        # Step 5: Create binding with audit trail
        requirements_hash = self._compute_requirements_hash(dependency)
        profile_id = self._get_profile_id(profile)

        binding = ModelBinding(
            dependency_alias=dependency.alias,
            capability=dependency.capability,
            resolved_provider=str(selected_provider.provider_id),
            adapter=selected_provider.adapter,
            connection_ref=selected_provider.connection_ref,
            requirements_hash=requirements_hash,
            resolution_profile=profile_id,
            resolved_at=datetime.now(UTC),
            resolution_notes=resolution_notes,
            candidates_considered=len(sorted_providers),
        )

        logger.debug(
            "Resolved '%s' -> '%s' to provider '%s' (%d candidates considered)",
            dependency.alias,
            dependency.capability,
            selected_provider.provider_id,
            len(sorted_providers),
        )

        audit_data: TypedDictResolutionAuditData = {
            "candidates": candidates,
            "scores": scores,
            "rejection_reasons": rejection_reasons,
        }

        return binding, audit_data

    def _check_hard_constraints(
        self,
        provider: ModelProviderDescriptor,
        dependency: ModelCapabilityDependency,
    ) -> str | None:
        """
        Check if provider satisfies hard constraints (must/forbid).

        Args:
            provider: The provider to check.
            dependency: The dependency with requirements.

        Returns:
            None if provider satisfies all constraints, or a rejection reason
            string explaining why the provider was rejected.
        """
        requirements = dependency.requirements
        effective_features = provider.get_effective_features()

        # Combine attributes and features for constraint checking
        # Attributes are static metadata, features are capabilities
        provider_values: dict[str, JsonType] = {
            **provider.attributes,
            **effective_features,
        }

        # Check must constraints - all must be satisfied
        for key, required_value in requirements.must.items():
            if key not in provider_values:
                return f"Missing required attribute '{key}'"
            if provider_values[key] != required_value:
                return (
                    f"Attribute '{key}' value '{provider_values[key]}' "
                    f"does not match required '{required_value}'"
                )

        # Check forbid constraints - none must match
        for key, forbidden_value in requirements.forbid.items():
            if key in provider_values and provider_values[key] == forbidden_value:
                return f"Has forbidden attribute '{key}' with value '{forbidden_value}'"

        return None

    def _score_providers(
        self,
        providers: list[ModelProviderDescriptor],
        dependency: ModelCapabilityDependency,
        profile: ModelProfile | None = None,
    ) -> list[tuple[ModelProviderDescriptor, float]]:
        """
        Score providers based on prefer constraints and profile weights.

        Each satisfied prefer constraint adds 1.0 to the score. Profile
        weights can adjust scores if provided.

        Args:
            providers: List of providers that passed hard constraint filtering.
            dependency: The dependency with prefer requirements.
            profile: Optional profile with weight adjustments.

        Returns:
            List of (provider, score) tuples sorted by score descending,
            then by provider_id ascending for determinism.
        """
        requirements = dependency.requirements
        scored: list[tuple[ModelProviderDescriptor, float]] = []

        for provider in providers:
            score = 0.0
            effective_features = provider.get_effective_features()
            provider_values: dict[str, JsonType] = {
                **provider.attributes,
                **effective_features,
            }

            # Score based on prefer constraints
            for key, preferred_value in requirements.prefer.items():
                if key in provider_values and provider_values[key] == preferred_value:
                    score += 1.0

            # Apply profile weights if available
            if profile is not None:
                profile_adjustment = self._get_profile_weight(
                    profile, str(provider.provider_id)
                )
                score += profile_adjustment

            scored.append((provider, score))

        # Sort by score descending, then provider_id ascending for determinism
        scored.sort(key=lambda x: (-x[1], str(x[0].provider_id)))

        return scored

    def _apply_selection_policy(
        self,
        scored_providers: list[tuple[ModelProviderDescriptor, float]],
        dependency: ModelCapabilityDependency,
        profile: ModelProfile | None,
        total_candidates: int,
        rejection_reasons: dict[str, str],
    ) -> tuple[ModelProviderDescriptor, list[str]]:
        """
        Apply selection policy to choose a provider from scored candidates.

        Args:
            scored_providers: List of (provider, score) tuples, sorted by score.
            dependency: The dependency with selection policy.
            profile: Optional profile for explicit bindings.
            total_candidates: Total number of candidates before filtering.
            rejection_reasons: Reasons for rejected candidates (for audit).

        Returns:
            Tuple of (selected_provider, resolution_notes).

        Raises:
            ModelOnexError: If selection policy cannot be satisfied.
        """
        policy = dependency.selection_policy
        resolution_notes: list[str] = []

        # Check for profile-pinned provider
        pinned_provider_id = self._get_pinned_provider(profile, dependency.alias)

        if pinned_provider_id:
            # Find the pinned provider in candidates
            for provider, score in scored_providers:
                if str(provider.provider_id) == pinned_provider_id:
                    resolution_notes.append(
                        f"Selected via profile pin: {pinned_provider_id}"
                    )
                    resolution_notes.append(f"Score: {score:.2f}")
                    return provider, resolution_notes

            # Pinned provider not in candidates
            raise ModelOnexError(
                message=(
                    f"Profile-pinned provider '{pinned_provider_id}' not found "
                    f"among eligible candidates for '{dependency.alias}'."
                ),
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
                context={
                    "alias": dependency.alias,
                    "capability": dependency.capability,
                    "pinned_provider_id": pinned_provider_id,
                    "available_candidates": [
                        str(p.provider_id) for p, _ in scored_providers
                    ],
                },
            )

        # Apply selection policy
        if policy == "require_explicit":
            raise ModelOnexError(
                message=(
                    f"Dependency '{dependency.alias}' requires explicit binding "
                    f"(selection_policy='require_explicit') but no profile pin was provided."
                ),
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
                context={
                    "alias": dependency.alias,
                    "capability": dependency.capability,
                    "candidates": [str(p.provider_id) for p, _ in scored_providers],
                },
            )

        if policy == "auto_if_unique":
            if len(scored_providers) == 1:
                provider, score = scored_providers[0]
                resolution_notes.append(
                    "Selected via auto_if_unique (single candidate)"
                )
                resolution_notes.append(f"Score: {score:.2f}")
                return provider, resolution_notes

            # Multiple candidates - ambiguous
            raise ModelOnexError(
                message=(
                    f"Ambiguous resolution for '{dependency.alias}': "
                    f"{len(scored_providers)} candidates match with "
                    f"selection_policy='auto_if_unique'. "
                    f"Use 'best_score' policy or provide explicit binding."
                ),
                error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
                context={
                    "alias": dependency.alias,
                    "capability": dependency.capability,
                    "candidates": [str(p.provider_id) for p, _ in scored_providers],
                    "scores": {str(p.provider_id): s for p, s in scored_providers},
                },
            )

        if policy == "best_score":
            # Select highest scoring (already sorted)
            provider, score = scored_providers[0]
            resolution_notes.append(
                "Selected via best_score (highest scoring candidate)"
            )
            resolution_notes.append(f"Score: {score:.2f}")

            # Note if there were ties
            tied_providers = [p for p, s in scored_providers if s == score]
            if len(tied_providers) > 1:
                resolution_notes.append(
                    f"Tie-breaker: selected by provider_id ordering "
                    f"({len(tied_providers)} providers with same score)"
                )

            # Add rejection summary
            if rejection_reasons:
                resolution_notes.append(
                    f"Rejected {len(rejection_reasons)} provider(s) "
                    f"(failed hard constraints)"
                )

            return provider, resolution_notes

        # Unknown policy (should not happen due to Pydantic validation)
        raise ModelOnexError(
            message=f"Unknown selection policy: {policy}",
            error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
            context={
                "alias": dependency.alias,
                "capability": dependency.capability,
                "policy": policy,
            },
        )

    def _compute_requirements_hash(self, dependency: ModelCapabilityDependency) -> str:
        """
        Compute a deterministic hash of the dependency requirements.

        The hash is used for cache invalidation - if requirements change,
        cached bindings become invalid.

        Args:
            dependency: The dependency with requirements.

        Returns:
            A SHA-256 hash string prefixed with "sha256:".
        """
        requirements = dependency.requirements

        # Create a deterministic JSON representation
        # Sort keys for determinism
        hashable_data = {
            "must": dict(sorted(requirements.must.items())),
            "prefer": dict(sorted(requirements.prefer.items())),
            "forbid": dict(sorted(requirements.forbid.items())),
            "hints": dict(sorted(requirements.hints.items())),
            "selection_policy": dependency.selection_policy,
            "strict": dependency.strict,
        }

        json_str = json.dumps(hashable_data, sort_keys=True, separators=(",", ":"))
        hash_value = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        return f"sha256:{hash_value}"

    def _get_profile_id(self, profile: ModelProfile | None) -> str:
        """
        Extract profile ID from profile, or return default.

        Args:
            profile: Optional profile object.

        Returns:
            Profile ID string, or "default" if no profile.
        """
        if profile is None:
            return "default"

        # Try to get profile_id attribute
        if hasattr(profile, "profile_id"):
            return str(profile.profile_id)
        if hasattr(profile, "id"):
            return str(profile.id)

        return "default"

    def _get_profile_weight(
        self, profile: ModelProfile | None, provider_id_str: str
    ) -> float:
        """
        Get profile weight adjustment for a provider.

        Args:
            profile: Optional profile with weight configuration.
            provider_id_str: The provider ID string to look up in weights dict.

        Returns:
            Weight adjustment (0.0 if no profile or no weights defined).
        """
        if profile is None:
            return 0.0

        # Try to get weights from profile
        weights = getattr(profile, "provider_weights", None)
        if weights is None:
            weights = getattr(profile, "weights", None)

        if weights and isinstance(weights, dict):
            return float(weights.get(provider_id_str, 0.0))

        return 0.0

    def _get_pinned_provider(
        self, profile: ModelProfile | None, alias: str
    ) -> str | None:
        """
        Get explicitly pinned provider for an alias from profile.

        Args:
            profile: Optional profile with explicit bindings.
            alias: The dependency alias to look up.

        Returns:
            Pinned provider ID, or None if not pinned.
        """
        if profile is None:
            return None

        # Try to get explicit bindings from profile
        bindings = getattr(profile, "explicit_bindings", None)
        if bindings is None:
            bindings = getattr(profile, "bindings", None)
        if bindings is None:
            bindings = getattr(profile, "pins", None)

        if bindings and isinstance(bindings, dict):
            pinned = bindings.get(alias)
            # Ensure we return str | None, not Any
            if pinned is None or isinstance(pinned, str):
                return pinned
            return str(pinned)

        return None

    def __repr__(self) -> str:
        """Return representation for debugging."""
        return "ServiceCapabilityResolver()"

    def __str__(self) -> str:
        """Return string representation."""
        return "ServiceCapabilityResolver"
