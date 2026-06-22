# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the FeatureFlagRegistry (OMN-7776).

The registry is the single source of truth for known ONEX feature flags and the
typed resolution API that replaces scattered ``os.getenv("ENABLE_*")`` reads.
The ``catalog()`` payload tested here is what the omnidash
``/api/settings/feature-flags`` endpoint renders via ``registry.resolve()``.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_feature_flag_gate_type import EnumFeatureFlagGateType
from omnibase_core.errors import OnexError
from omnibase_core.feature_flags import (
    FEATURE_FLAG_REGISTRY,
    FeatureFlagRegistry,
    ModelFeatureFlagDefinition,
    ModelFeatureFlagResolution,
)


@pytest.mark.unit
class TestRegistryCatalog:
    """The registry declares the full known-flag catalog."""

    def test_declares_at_least_24_flags(self) -> None:
        assert len(FEATURE_FLAG_REGISTRY.names()) >= 24

    def test_flag_names_are_unique(self) -> None:
        names = FEATURE_FLAG_REGISTRY.names()
        assert len(names) == len(set(names))

    def test_known_flags_present(self) -> None:
        names = set(FEATURE_FLAG_REGISTRY.names())
        for required in (
            "ENABLE_POSTGRES",
            "ENABLE_QDRANT",
            "USE_EVENT_ROUTING",
            "ENABLE_PATTERN_QUALITY_FILTER",
        ):
            assert required in names

    def test_every_definition_is_strongly_typed(self) -> None:
        for definition in FEATURE_FLAG_REGISTRY.definitions():
            assert isinstance(definition, ModelFeatureFlagDefinition)
            assert isinstance(definition.gate_type, EnumFeatureFlagGateType)
            assert definition.owning_repo  # non-empty
            assert definition.description  # non-empty

    def test_duplicate_declaration_raises(self) -> None:
        dup = ModelFeatureFlagDefinition(
            name="ENABLE_POSTGRES",
            description="dup",
            default=False,
            owning_repo="omniclaude",
            gate_type=EnumFeatureFlagGateType.MIGRATION,
        )
        with pytest.raises(OnexError, match="Duplicate feature flag"):
            FeatureFlagRegistry((dup, dup))


@pytest.mark.unit
class TestRegistryResolve:
    """resolve() honors declared defaults and env overrides, and fails fast."""

    def test_default_when_env_absent(self) -> None:
        resolution = FEATURE_FLAG_REGISTRY.resolve("ENABLE_POSTGRES", env={})
        assert isinstance(resolution, ModelFeatureFlagResolution)
        assert resolution.enabled is False
        assert resolution.source == "default"
        assert resolution.raw_value is None

    def test_env_truthy_override(self) -> None:
        resolution = FEATURE_FLAG_REGISTRY.resolve(
            "ENABLE_POSTGRES", env={"ENABLE_POSTGRES": "1"}
        )
        assert resolution.enabled is True
        assert resolution.source == "env"
        assert resolution.raw_value == "1"

    @pytest.mark.parametrize("falsy", ["", "0", "false", "FALSE", "False"])
    def test_env_falsy_values(self, falsy: str) -> None:
        resolution = FEATURE_FLAG_REGISTRY.resolve(
            "ENABLE_PATTERN_QUALITY_FILTER",
            env={"ENABLE_PATTERN_QUALITY_FILTER": falsy},
        )
        assert resolution.enabled is False
        assert resolution.source == "env"

    def test_env_arbitrary_truthy_value(self) -> None:
        resolution = FEATURE_FLAG_REGISTRY.resolve(
            "USE_EVENT_ROUTING", env={"USE_EVENT_ROUTING": "yes"}
        )
        assert resolution.enabled is True

    def test_unknown_flag_fails_fast(self) -> None:
        with pytest.raises(OnexError, match="Unknown feature flag"):
            FEATURE_FLAG_REGISTRY.resolve("ENABLE_NONEXISTENT_FLAG", env={})

    def test_is_enabled_convenience(self) -> None:
        assert (
            FEATURE_FLAG_REGISTRY.is_enabled(
                "ENABLE_POSTGRES", env={"ENABLE_POSTGRES": "true"}
            )
            is True
        )

    def test_resolve_all_covers_every_flag(self) -> None:
        resolutions = FEATURE_FLAG_REGISTRY.resolve_all(env={})
        assert len(resolutions) == len(FEATURE_FLAG_REGISTRY.names())


@pytest.mark.unit
class TestCatalogPayload:
    """catalog() is the omnidash endpoint payload, sourced from resolve()."""

    def test_catalog_shape(self) -> None:
        catalog = FEATURE_FLAG_REGISTRY.catalog(env={})
        assert len(catalog) == len(FEATURE_FLAG_REGISTRY.names())
        entry = catalog[0]
        for key in (
            "name",
            "value",
            "state",
            "enabled",
            "source",
            "service",
            "description",
            "default",
            "gate_type",
            "category",
        ):
            assert key in entry

    def test_catalog_migration_state_when_off(self) -> None:
        catalog = FEATURE_FLAG_REGISTRY.catalog(env={})
        by_name = {e["name"]: e for e in catalog}
        # ENABLE_POSTGRES is a migration flag defaulting off -> "migration"
        assert by_name["ENABLE_POSTGRES"]["state"] == "migration"

    def test_catalog_on_state_when_enabled(self) -> None:
        catalog = FEATURE_FLAG_REGISTRY.catalog(env={"ENABLE_POSTGRES": "1"})
        by_name = {e["name"]: e for e in catalog}
        assert by_name["ENABLE_POSTGRES"]["state"] == "on"
        assert by_name["ENABLE_POSTGRES"]["enabled"] is True

    def test_catalog_is_json_serializable(self) -> None:
        import json

        payload = FEATURE_FLAG_REGISTRY.catalog(env={})
        # Must round-trip through JSON for the HTTP endpoint.
        assert json.loads(json.dumps(payload)) == payload
