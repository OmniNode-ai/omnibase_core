# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for UtilProjectorPluginLoader — contract schema version validation.

Test coverage:
1. Load a valid contract from a dict (happy path).
2. validate_version passes for CURRENT_SCHEMA_VERSION.
3. validate_version passes for a deprecated version (with warning log).
4. validate_version raises ModelOnexError for unsupported version.
5. validate_version raises ModelOnexError for malformed version string.
6. load() raises ModelOnexError when Pydantic validation fails.
7. load_and_validate() combines load + validate in one call.
8. Custom supported_versions / deprecated_versions constructor overrides.
9. Version registry module-level constants are internally consistent.
10. validate_version error message lists supported versions.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_projector_plugin_loader import (
    CURRENT_SCHEMA_VERSION,
    DEPRECATED_SCHEMA_VERSIONS,
    SUPPORTED_SCHEMA_VERSIONS,
    UtilProjectorPluginLoader,
)

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _minimal_contract_data(version: str = "1.0.0") -> dict[str, object]:
    """Return the minimal dict required to build a valid ModelProjectorContract."""
    return {
        "projector_kind": "materialized_view",
        "projector_id": "test-projector",
        "name": "Test Projector",
        "version": version,
        "aggregate_type": "node",
        "consumed_events": ["node.created.v1"],
        "projection_schema": {
            "table": "nodes",
            "primary_key": "node_id",
            "columns": [
                {
                    "name": "node_id",
                    "type": "UUID",
                    "source": "event.payload.node_id",
                }
            ],
        },
        "behavior": {
            "mode": "upsert",
            "upsert_key": "node_id",
        },
    }


@pytest.fixture
def loader() -> UtilProjectorPluginLoader:
    """Default loader using module-level registry."""
    return UtilProjectorPluginLoader()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVersionRegistryConsistency:
    """Verify the module-level constants are internally consistent."""

    def test_current_version_in_supported_versions(self) -> None:
        """CURRENT_SCHEMA_VERSION must be in SUPPORTED_SCHEMA_VERSIONS."""
        assert CURRENT_SCHEMA_VERSION in SUPPORTED_SCHEMA_VERSIONS

    def test_deprecated_versions_subset_of_supported(self) -> None:
        """Every deprecated version must also be in SUPPORTED_SCHEMA_VERSIONS."""
        for v in DEPRECATED_SCHEMA_VERSIONS:
            assert v in SUPPORTED_SCHEMA_VERSIONS, (
                f"Deprecated version {v} not found in SUPPORTED_SCHEMA_VERSIONS"
            )

    def test_current_version_not_deprecated(self) -> None:
        """CURRENT_SCHEMA_VERSION must not be in DEPRECATED_SCHEMA_VERSIONS."""
        assert CURRENT_SCHEMA_VERSION not in DEPRECATED_SCHEMA_VERSIONS

    def test_current_version_is_semver(self) -> None:
        """CURRENT_SCHEMA_VERSION must be a proper ModelSemVer."""
        assert isinstance(CURRENT_SCHEMA_VERSION, ModelSemVer)

    def test_supported_versions_non_empty(self) -> None:
        """SUPPORTED_SCHEMA_VERSIONS must contain at least one entry."""
        assert len(SUPPORTED_SCHEMA_VERSIONS) >= 1


@pytest.mark.unit
class TestUtilProjectorPluginLoaderLoad:
    """Tests for UtilProjectorPluginLoader.load()."""

    def test_load_valid_contract_returns_model(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """load() on valid data returns a ModelProjectorContract."""
        from omnibase_core.models.projectors.model_projector_contract import (
            ModelProjectorContract,
        )

        data = _minimal_contract_data()
        contract = loader.load(data)
        assert isinstance(contract, ModelProjectorContract)

    def test_load_preserves_projector_id(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """load() preserves all contract fields."""
        data = _minimal_contract_data()
        contract = loader.load(data)
        assert contract.projector_id == "test-projector"
        assert contract.name == "Test Projector"
        assert contract.version == "1.0.0"
        assert contract.aggregate_type == "node"
        assert "node.created.v1" in contract.consumed_events

    def test_load_raises_onex_error_on_invalid_data(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """load() wraps Pydantic ValidationError in ModelOnexError."""
        bad_data: dict[str, object] = {
            "projector_kind": "materialized_view",
            # Missing required fields: projector_id, name, version, aggregate_type, etc.
        }
        with pytest.raises(ModelOnexError) as exc_info:
            loader.load(bad_data)
        assert "validation failed" in exc_info.value.message.lower()

    def test_load_raises_onex_error_on_invalid_event_pattern(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """load() raises ModelOnexError for events that fail the naming pattern."""
        data = _minimal_contract_data()
        data["consumed_events"] = ["INVALID_EVENT_NO_VERSION"]  # fails pattern
        with pytest.raises(ModelOnexError):
            loader.load(data)

    def test_load_raises_onex_error_on_unknown_field(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """load() raises ModelOnexError when extra fields are present (extra='forbid')."""
        data = _minimal_contract_data()
        data["unknown_field"] = "should_fail"
        with pytest.raises(ModelOnexError):
            loader.load(data)


@pytest.mark.unit
class TestUtilProjectorPluginLoaderValidateVersion:
    """Tests for UtilProjectorPluginLoader.validate_version()."""

    def test_current_version_passes_silently(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """validate_version passes without exception for CURRENT_SCHEMA_VERSION."""
        data = _minimal_contract_data(version=str(CURRENT_SCHEMA_VERSION))
        contract = loader.load(data)
        # Should not raise
        loader.validate_version(contract)

    def test_unsupported_version_raises_onex_error(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """validate_version raises ModelOnexError for a version not in the registry."""
        data = _minimal_contract_data(version="99.0.0")
        contract = loader.load(data)
        with pytest.raises(ModelOnexError) as exc_info:
            loader.validate_version(contract)
        err = exc_info.value
        assert "unsupported" in err.message.lower()
        assert "99.0.0" in err.message

    def test_unsupported_version_error_lists_supported(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """Error message for unsupported version includes the list of valid versions."""
        data = _minimal_contract_data(version="99.0.0")
        contract = loader.load(data)
        with pytest.raises(ModelOnexError) as exc_info:
            loader.validate_version(contract)
        err = exc_info.value
        for v in SUPPORTED_SCHEMA_VERSIONS:
            assert str(v) in err.message, (
                f"Expected supported version {v} to appear in error message"
            )

    def test_unsupported_version_error_context(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """Error context dict contains projector_id and contract_version.

        ModelOnexError stores non-standard context keys under
        context["additional_context"]["context"].
        """
        data = _minimal_contract_data(version="99.0.0")
        contract = loader.load(data)
        with pytest.raises(ModelOnexError) as exc_info:
            loader.validate_version(contract)
        # ModelOnexError puts arbitrary kwargs into additional_context
        err = exc_info.value
        additional = err.context.get("additional_context", {})
        inner: dict[str, object] = (
            additional.get("context", {}) if isinstance(additional, dict) else {}
        )
        assert inner.get("projector_id") == "test-projector"
        assert inner.get("contract_version") == "99.0.0"

    def test_malformed_version_raises_onex_error(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """validate_version raises ModelOnexError when version string is not valid SemVer."""
        data = _minimal_contract_data(version="not-a-semver")
        # load() accepts any non-empty string in the 'version' field (it's just str)
        contract = loader.load(data)
        with pytest.raises(ModelOnexError) as exc_info:
            loader.validate_version(contract)
        assert "invalid" in exc_info.value.message.lower()

    def test_deprecated_version_logs_warning(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """validate_version emits a WARNING log for deprecated versions."""
        deprecated_v = ModelSemVer(major=0, minor=9, patch=0)
        custom_loader = UtilProjectorPluginLoader(
            supported_versions=frozenset({CURRENT_SCHEMA_VERSION, deprecated_v}),
            deprecated_versions=frozenset({deprecated_v}),
        )
        data = _minimal_contract_data(version="0.9.0")
        contract = custom_loader.load(data)

        with patch(
            "omnibase_core.utils.util_projector_plugin_loader.emit_log_event"
        ) as mock_emit:
            custom_loader.validate_version(contract)

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        from omnibase_core.enums.enum_log_level import EnumLogLevel

        # First positional arg should be WARNING level
        assert call_args[0][0] == EnumLogLevel.WARNING
        # Message should mention the deprecated version
        assert "0.9.0" in call_args[0][1]

    def test_deprecated_version_does_not_raise(
        self,
    ) -> None:
        """A deprecated version passes validation without raising an exception."""
        deprecated_v = ModelSemVer(major=0, minor=9, patch=0)
        loader = UtilProjectorPluginLoader(
            supported_versions=frozenset({CURRENT_SCHEMA_VERSION, deprecated_v}),
            deprecated_versions=frozenset({deprecated_v}),
        )
        data = _minimal_contract_data(version="0.9.0")
        contract = loader.load(data)
        with patch("omnibase_core.utils.util_projector_plugin_loader.emit_log_event"):
            loader.validate_version(contract)  # must not raise

    def test_non_deprecated_supported_version_does_not_warn(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """CURRENT_SCHEMA_VERSION never triggers a warning log."""
        data = _minimal_contract_data(version=str(CURRENT_SCHEMA_VERSION))
        contract = loader.load(data)
        with patch(
            "omnibase_core.utils.util_projector_plugin_loader.emit_log_event"
        ) as mock_emit:
            loader.validate_version(contract)
        mock_emit.assert_not_called()


@pytest.mark.unit
class TestUtilProjectorPluginLoaderLoadAndValidate:
    """Tests for UtilProjectorPluginLoader.load_and_validate()."""

    def test_load_and_validate_happy_path(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """load_and_validate() returns a valid contract for supported version."""
        from omnibase_core.models.projectors.model_projector_contract import (
            ModelProjectorContract,
        )

        data = _minimal_contract_data()
        contract = loader.load_and_validate(data)
        assert isinstance(contract, ModelProjectorContract)
        assert contract.version == "1.0.0"

    def test_load_and_validate_unsupported_version_raises(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """load_and_validate() raises for unsupported version."""
        data = _minimal_contract_data(version="99.0.0")
        with pytest.raises(ModelOnexError) as exc_info:
            loader.load_and_validate(data)
        assert "unsupported" in exc_info.value.message.lower()

    def test_load_and_validate_invalid_contract_raises(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """load_and_validate() raises on structurally invalid contract data."""
        with pytest.raises(ModelOnexError):
            loader.load_and_validate({"projector_kind": "materialized_view"})

    def test_load_and_validate_returns_immutable_contract(
        self, loader: UtilProjectorPluginLoader
    ) -> None:
        """Returned contract is frozen (immutable)."""
        data = _minimal_contract_data()
        contract = loader.load_and_validate(data)
        with pytest.raises(Exception):
            contract.version = "2.0.0"  # type: ignore[misc]


@pytest.mark.unit
class TestUtilProjectorPluginLoaderCustomRegistry:
    """Tests for constructor-level registry overrides."""

    def test_custom_supported_versions_accepted(self) -> None:
        """A custom supported version set overrides the global registry."""
        custom_v = ModelSemVer(major=2, minor=0, patch=0)
        loader = UtilProjectorPluginLoader(
            supported_versions=frozenset({custom_v}),
            deprecated_versions=frozenset(),
        )
        data = _minimal_contract_data(version="2.0.0")
        contract = loader.load(data)
        # Should pass without error since 2.0.0 is in the custom set
        loader.validate_version(contract)

    def test_custom_supported_versions_rejects_global_current(self) -> None:
        """With custom registry, a globally-current version may be rejected."""
        custom_v = ModelSemVer(major=2, minor=0, patch=0)
        loader = UtilProjectorPluginLoader(
            supported_versions=frozenset({custom_v}),
            deprecated_versions=frozenset(),
        )
        # 1.0.0 is globally current but NOT in the custom registry
        data = _minimal_contract_data(version="1.0.0")
        contract = loader.load(data)
        with pytest.raises(ModelOnexError) as exc_info:
            loader.validate_version(contract)
        assert "unsupported" in exc_info.value.message.lower()

    def test_default_loader_uses_global_registry(self) -> None:
        """Default loader uses SUPPORTED_SCHEMA_VERSIONS from module."""
        loader = UtilProjectorPluginLoader()
        assert loader._supported == SUPPORTED_SCHEMA_VERSIONS
        assert loader._deprecated == DEPRECATED_SCHEMA_VERSIONS
