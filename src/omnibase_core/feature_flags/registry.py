# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Feature flag registry (OMN-7776).

The single source of truth for every known ONEX feature flag. Declares each
flag with typed metadata and exposes a typed resolution API that replaces
scattered ``os.getenv("ENABLE_*")`` reads across the platform.

Resolution is pure: callers pass an explicit environment mapping (defaulting
to ``os.environ``). A flag's runtime state is the declared default unless the
environment provides a truthy/falsy override. Truthiness follows the platform
convention used by the omnidash endpoint: ``""``, ``"0"``, and ``"false"``
(case-insensitive) are off; any other non-empty value is on.

Unknown flag names are a hard error — fail fast rather than silently returning
a default, so typos surface immediately.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_feature_flag_category import EnumFeatureFlagCategory
from omnibase_core.enums.enum_feature_flag_gate_type import EnumFeatureFlagGateType
from omnibase_core.errors import OnexError
from omnibase_core.models.core.model_feature_flag_definition import (
    ModelFeatureFlagDefinition,
)
from omnibase_core.models.core.model_feature_flag_resolution import (
    ModelFeatureFlagResolution,
)

# Values (case-insensitive) that resolve a present env var to "off".
_FALSY_ENV_VALUES: frozenset[str] = frozenset({"", "0", "false"})

# Canonical flag declarations. This is the authoritative catalog.
_FLAG_DEFINITIONS: tuple[ModelFeatureFlagDefinition, ...] = (
    # --- omniclaude: infrastructure --------------------------------------
    ModelFeatureFlagDefinition(
        name="ENABLE_POSTGRES",
        description="Enables Postgres-backed session and pattern storage.",
        default=False,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.MIGRATION,
        category=EnumFeatureFlagCategory.INFRASTRUCTURE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_QDRANT",
        description="Enables Qdrant vector store for semantic pattern retrieval.",
        default=False,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.MIGRATION,
        category=EnumFeatureFlagCategory.INFRASTRUCTURE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_INTELLIGENCE_CACHE",
        description="Caches intelligence node results to reduce LLM calls.",
        default=False,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="USE_EVENT_ROUTING",
        description="Routes commands/events through the ONEX event bus.",
        default=False,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.MIGRATION,
        category=EnumFeatureFlagCategory.RUNTIME,
    ),
    ModelFeatureFlagDefinition(
        name="DUAL_PUBLISH_LEGACY_TOPICS",
        description="Publishes to both new and legacy topic names during migration.",
        default=False,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.MIGRATION,
        category=EnumFeatureFlagCategory.INFRASTRUCTURE,
    ),
    ModelFeatureFlagDefinition(
        name="USE_ONEX_ROUTING_NODES",
        description="Routes LLM calls through ONEX routing node graph.",
        default=False,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.MIGRATION,
        category=EnumFeatureFlagCategory.RUNTIME,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_PATTERN_QUALITY_FILTER",
        description="Filters patterns below quality threshold before storage.",
        default=True,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_DISABLED_PATTERN_FILTER",
        description="Excludes disabled patterns from retrieval results.",
        default=True,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_PHASE_1_VALIDATION",
        description="Phase 1 validation gate: structural contract checks.",
        default=True,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_PHASE_2_SEMANTIC",
        description="Phase 2 validation gate: semantic consistency checks.",
        default=True,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_PHASE_3_INTEGRATION",
        description="Phase 3 validation gate: cross-service integration checks.",
        default=False,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_PHASE_4_AI_QUORUM",
        description="Phase 4 validation gate: multi-model AI quorum review.",
        default=False,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_LOCAL_INFERENCE_PIPELINE",
        description="Routes inference to local GPU endpoints first.",
        default=True,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_PATTERN_ENFORCEMENT",
        description="Enforces pattern schema and lifecycle rules.",
        default=True,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="USE_LLM_ROUTING",
        description="Enables dynamic LLM routing via contract model_routing config.",
        default=True,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.MIGRATION,
        category=EnumFeatureFlagCategory.RUNTIME,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_DELEGATION",
        description="Enables the cheapest-first delegation chain of responders.",
        default=True,
        owning_repo="omniclaude",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    # --- omnibase_infra: runtime / infrastructure ------------------------
    ModelFeatureFlagDefinition(
        name="ENABLE_METRICS",
        description="Emits runtime metrics from the ONEX node runtime.",
        default=True,
        owning_repo="omnibase_infra",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.OBSERVABILITY,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_IDEMPOTENCE",
        description="Enforces idempotent envelope handling on the event bus.",
        default=True,
        owning_repo="omnibase_infra",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INFRASTRUCTURE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_RUNTIME_LOG_BRIDGE",
        description="Bridges runtime logs onto the structured log event topic.",
        default=False,
        owning_repo="omnibase_infra",
        gate_type=EnumFeatureFlagGateType.MIGRATION,
        category=EnumFeatureFlagCategory.OBSERVABILITY,
    ),
    # --- omnidash --------------------------------------------------------
    ModelFeatureFlagDefinition(
        name="ENABLE_EVENT_INTELLIGENCE",
        description="Enables event intelligence processing pipeline.",
        default=True,
        owning_repo="omnidash",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.INTELLIGENCE,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_KAFKA_LOGGING",
        description="Routes structured logs through Kafka.",
        default=True,
        owning_repo="omnidash",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.OBSERVABILITY,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_REAL_TIME_EVENTS",
        description="Opens WebSocket channel for live event stream.",
        default=True,
        owning_repo="omnidash",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.DASHBOARD,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_EVENT_PRELOAD",
        description="Pre-fetches events on dashboard mount.",
        default=False,
        owning_repo="omnidash",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.DASHBOARD,
    ),
    ModelFeatureFlagDefinition(
        name="ENABLE_RESPONSE_CACHE",
        description="Enables response-level projection cache.",
        default=False,
        owning_repo="omnidash",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.DASHBOARD,
    ),
    ModelFeatureFlagDefinition(
        name="ARCHON_ENABLE_EXTERNAL_GATEWAY",
        description="Routes inference through external Archon gateway.",
        default=False,
        owning_repo="omnidash",
        gate_type=EnumFeatureFlagGateType.MIGRATION,
        category=EnumFeatureFlagCategory.INFRASTRUCTURE,
    ),
    ModelFeatureFlagDefinition(
        name="VITE_USE_MOCK_DATA",
        description="Forces fixture data in place of live projections.",
        default=False,
        owning_repo="omnidash",
        gate_type=EnumFeatureFlagGateType.PERMANENT,
        category=EnumFeatureFlagCategory.DASHBOARD,
    ),
    ModelFeatureFlagDefinition(
        name="OMNIDASH_READ_MODEL_USE_CATALOG",
        description="Switches read model to catalog-based source.",
        default=False,
        owning_repo="omnidash",
        gate_type=EnumFeatureFlagGateType.MIGRATION,
        category=EnumFeatureFlagCategory.DASHBOARD,
    ),
)


class FeatureFlagRegistry:
    """Immutable registry of known feature flags with a typed resolution API.

    Construct from an explicit tuple of definitions, or use the module-level
    :data:`FEATURE_FLAG_REGISTRY` singleton built from the canonical catalog.
    """

    def __init__(
        self, definitions: tuple[ModelFeatureFlagDefinition, ...] = _FLAG_DEFINITIONS
    ) -> None:
        index: dict[str, ModelFeatureFlagDefinition] = {}
        for definition in definitions:
            if definition.name in index:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=(
                        "Duplicate feature flag declared in registry: "
                        f"{definition.name!r}"
                    ),
                )
            index[definition.name] = definition
        self._definitions: dict[str, ModelFeatureFlagDefinition] = index

    def names(self) -> tuple[str, ...]:
        """Return all registered flag names in declaration order."""
        return tuple(self._definitions.keys())

    def definitions(self) -> tuple[ModelFeatureFlagDefinition, ...]:
        """Return all flag definitions in declaration order."""
        return tuple(self._definitions.values())

    def definition(self, name: str) -> ModelFeatureFlagDefinition:
        """Return the definition for ``name`` or raise ``KeyError`` if unknown."""
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise OnexError(
                code=EnumCoreErrorCode.NOT_FOUND,
                message=f"Unknown feature flag: {name!r}",
            ) from exc

    def resolve(
        self, name: str, env: Mapping[str, str] | None = None
    ) -> ModelFeatureFlagResolution:
        """Resolve a single flag against ``env`` (defaults to ``os.environ``).

        Raises ``KeyError`` for an unknown flag name — fail fast, never silently
        default. The raw env value, the resolved boolean, and the provenance are
        all returned.
        """
        definition = self.definition(name)
        environment = os.environ if env is None else env
        raw = environment.get(name)
        if raw is None:
            return ModelFeatureFlagResolution(
                name=definition.name,
                enabled=definition.default,
                raw_value=None,
                source="default",
                description=definition.description,
                default=definition.default,
                owning_repo=definition.owning_repo,
                gate_type=definition.gate_type,
                category=definition.category,
            )
        enabled = raw.strip().lower() not in _FALSY_ENV_VALUES
        return ModelFeatureFlagResolution(
            name=definition.name,
            enabled=enabled,
            raw_value=raw,
            source="env",
            description=definition.description,
            default=definition.default,
            owning_repo=definition.owning_repo,
            gate_type=definition.gate_type,
            category=definition.category,
        )

    def is_enabled(self, name: str, env: Mapping[str, str] | None = None) -> bool:
        """Convenience wrapper returning only the resolved boolean for ``name``."""
        return self.resolve(name, env=env).enabled

    def resolve_all(
        self, env: Mapping[str, str] | None = None
    ) -> tuple[ModelFeatureFlagResolution, ...]:
        """Resolve every registered flag against ``env``."""
        return tuple(self.resolve(name, env=env) for name in self._definitions)

    def catalog(self, env: Mapping[str, str] | None = None) -> list[dict[str, object]]:
        """Return a JSON-serializable catalog of every resolved flag.

        This is the payload the omnidash ``/api/settings/feature-flags`` endpoint
        renders. Keys match the dashboard's ``FeatureFlagEntry`` shape.
        """
        return [
            {
                "name": resolution.name,
                "value": resolution.raw_value,
                "state": (
                    "migration"
                    if resolution.gate_type is EnumFeatureFlagGateType.MIGRATION
                    and not resolution.enabled
                    else ("on" if resolution.enabled else "off")
                ),
                "enabled": resolution.enabled,
                "source": resolution.source,
                "service": resolution.owning_repo,
                "description": resolution.description,
                "default": resolution.default,
                "gate_type": resolution.gate_type.value,
                "category": resolution.category.value,
            }
            for resolution in self.resolve_all(env=env)
        ]

    def static_catalog(self) -> list[dict[str, object]]:
        """Return the env-independent declaration catalog.

        This is the cross-language single-source-of-truth artifact: the omnidash
        Express server loads it to obtain the flag names, descriptions, owning
        repos, gate types, and defaults, then resolves live on/off state from its
        own ``process.env`` server-side. Contains no runtime/env-derived fields.
        """
        return [
            {
                "name": definition.name,
                "description": definition.description,
                "default": definition.default,
                "service": definition.owning_repo,
                "gate_type": definition.gate_type.value,
                "category": definition.category.value,
            }
            for definition in self.definitions()
        ]


# Canonical singleton built from the authoritative catalog.
FEATURE_FLAG_REGISTRY: FeatureFlagRegistry = FeatureFlagRegistry()
