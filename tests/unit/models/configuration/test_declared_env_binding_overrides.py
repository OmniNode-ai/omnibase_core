# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Configured / unconfigured behaviour of the declared binding tables (OMN-17554).

Each migrated site declares its bindings as literal ``${env.VAR}`` contract
references and resolves them through the sanctioned overlay boundary. These
tests prove the three cases that matter for every one of them:

* **unconfigured** — the typed default survives; nothing is overridden;
* **configured** — the declared value is applied with its declared type;
* **secret-carrying** — a credential resolves into a ``SecretStr`` and its
  value does not appear in a repr or a serialization.

They also pin each declared table against the field set it claims to bind, so a
renamed field cannot leave a silently dead reference behind.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from omnibase_core.infrastructure.node_config_provider import NodeConfigProvider
from omnibase_core.models.configuration.model_database_connection_config import (
    ModelDatabaseConnectionConfig,
)
from omnibase_core.models.configuration.model_event_bus_config import (
    ModelEventBusConfig,
)
from omnibase_core.models.configuration.model_rest_api_connection_config import (
    ModelRestApiConnectionConfig,
)
from omnibase_core.models.security.model_secret_backend import (
    CI_INDICATOR_BINDINGS,
    ModelSecretBackend,
)
from omnibase_core.overlays.contract_env_ref import resolve_contract_env_binding

pytestmark = pytest.mark.unit

_MODEL_TABLES = (
    (ModelDatabaseConnectionConfig, ModelDatabaseConnectionConfig._ENV_BINDINGS),
    (ModelRestApiConnectionConfig, ModelRestApiConnectionConfig._ENV_BINDINGS),
    (ModelEventBusConfig, ModelEventBusConfig._ENV_BINDINGS),
)
_ALL_MODEL_REFERENCES = [
    reference for _model, table in _MODEL_TABLES for _field, reference in table
]
_ALL_BOUND_NAMES = [
    resolve_contract_env_binding(reference).name for reference in _ALL_MODEL_REFERENCES
]


@pytest.fixture
def unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    """No declared binding is set, for any migrated site."""
    for name in [
        *_ALL_BOUND_NAMES,
        *NodeConfigProvider._BINDINGS.values(),
        *CI_INDICATOR_BINDINGS,
    ]:
        variable = name if not name.startswith("${env.") else name[6:-1]
        monkeypatch.delenv(variable, raising=False)


def _db_config() -> ModelDatabaseConnectionConfig:
    return ModelDatabaseConnectionConfig(
        host="declared.host",
        port=5432,
        database="declared_db",
        username="declared_user",
        password=SecretStr("declared-password"),  # pragma: allowlist secret
    )


# ---------------------------------------------------------------------------
# Declared tables match the fields they claim to bind
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("model", "table"), _MODEL_TABLES)
def test_every_declared_binding_names_a_real_field(model, table) -> None:
    declared = [field for field, _reference in table]
    unknown = set(declared) - set(model.model_fields)
    assert unknown == set(), unknown
    assert len(declared) == len(set(declared)), declared


def test_every_declared_reference_is_resolvable() -> None:
    """A malformed reference in a table fails closed at resolution, not silently."""
    for reference in [
        *_ALL_MODEL_REFERENCES,
        *NodeConfigProvider._BINDINGS.values(),
        *CI_INDICATOR_BINDINGS,
    ]:
        assert resolve_contract_env_binding(reference).reference == reference


def test_node_config_provider_binds_every_default_key() -> None:
    assert set(NodeConfigProvider._BINDINGS) == set(NodeConfigProvider._DEFAULTS)


# ---------------------------------------------------------------------------
# Database connection config
# ---------------------------------------------------------------------------


def test_database_unconfigured_keeps_declared_values(unconfigured: None) -> None:
    config = _db_config()
    assert config.apply_environment_overrides() is config


def test_database_configured_applies_typed_overrides(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ONEX_DB_HOST", "override.host")
    monkeypatch.setenv("ONEX_DB_PORT", "6543")
    monkeypatch.setenv("ONEX_DB_SSL_ENABLED", "true")
    overridden = _db_config().apply_environment_overrides()
    assert overridden.host == "override.host"
    assert overridden.port == 6543
    assert overridden.ssl_enabled is True


def test_database_password_binding_stays_secret(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "ONEX_DB_PASSWORD", "override-secret"
    )  # pragma: allowlist secret
    overridden = _db_config().apply_environment_overrides()
    assert isinstance(overridden.password, SecretStr)
    assert overridden.password.get_secret_value() == "override-secret"
    assert "override-secret" not in repr(overridden)
    assert "override-secret" not in overridden.model_dump_json()


def test_database_invalid_numeric_binding_is_skipped(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-numeric declared value leaves the typed default in place."""
    monkeypatch.setenv("ONEX_DB_PORT", "not-a-port")
    assert _db_config().apply_environment_overrides().port == 5432


# ---------------------------------------------------------------------------
# REST API connection config
# ---------------------------------------------------------------------------


def test_rest_unconfigured_keeps_declared_values(unconfigured: None) -> None:
    config = ModelRestApiConnectionConfig(base_url="https://declared.example")
    assert config.apply_environment_overrides() is config


def test_rest_configured_applies_typed_overrides(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ONEX_API_BASE_URL", "https://override.example")
    monkeypatch.setenv("ONEX_API_MAX_RETRIES", "7")
    overridden = ModelRestApiConnectionConfig(
        base_url="https://declared.example"
    ).apply_environment_overrides()
    assert overridden.base_url == "https://override.example"
    assert overridden.max_retries == 7


def test_rest_api_key_binding_stays_secret(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ONEX_API_KEY", "override-api-key")  # pragma: allowlist secret
    overridden = ModelRestApiConnectionConfig(
        base_url="https://declared.example"
    ).apply_environment_overrides()
    assert isinstance(overridden.api_key, SecretStr)
    assert overridden.api_key.get_secret_value() == "override-api-key"
    assert "override-api-key" not in repr(overridden)
    assert "override-api-key" not in overridden.model_dump_json()


# ---------------------------------------------------------------------------
# Event bus config
# ---------------------------------------------------------------------------


def test_event_bus_unconfigured_keeps_declared_values(unconfigured: None) -> None:
    config = ModelEventBusConfig(
        bootstrap_servers=["declared:19092"], topics=["declared-topic"]
    )
    assert config.apply_environment_overrides() is config


def test_event_bus_configured_applies_typed_overrides(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ONEX_EVENT_BUS_BOOTSTRAP_SERVERS", "a:9092, b:9092")
    monkeypatch.setenv("ONEX_EVENT_BUS_PARTITIONS", "12")
    monkeypatch.setenv("ONEX_EVENT_BUS_ENABLE_AUTO_COMMIT", "false")
    overridden = ModelEventBusConfig(
        bootstrap_servers=["declared:19092"], topics=["declared-topic"]
    ).apply_environment_overrides()
    assert overridden.bootstrap_servers == ["a:9092", "b:9092"]
    assert overridden.partitions == 12
    assert overridden.enable_auto_commit is False


def test_event_bus_sasl_password_binding_stays_secret(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "ONEX_EVENT_BUS_SASL_PASSWORD",
        "override-sasl",  # pragma: allowlist secret
    )
    overridden = ModelEventBusConfig(
        bootstrap_servers=["declared:19092"], topics=["declared-topic"]
    ).apply_environment_overrides()
    assert isinstance(overridden.sasl_password, SecretStr)
    assert overridden.sasl_password.get_secret_value() == "override-sasl"
    assert "override-sasl" not in repr(overridden)


# ---------------------------------------------------------------------------
# Node config provider
# ---------------------------------------------------------------------------


def test_node_config_provider_unconfigured_uses_declared_defaults(
    unconfigured: None,
) -> None:
    provider = NodeConfigProvider()
    for key, default in NodeConfigProvider._DEFAULTS.items():
        assert provider._config_cache[key] == default


def test_node_config_provider_configured_applies_declared_types(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ONEX_COMPUTE_MAX_PARALLEL_WORKERS", "16")
    monkeypatch.setenv("ONEX_COMPUTE_PERFORMANCE_THRESHOLD_MS", "12.5")
    monkeypatch.setenv("ONEX_ORCHESTRATOR_ACTION_EMISSION_ENABLED", "no")
    provider = NodeConfigProvider()
    assert provider._config_cache["compute.max_parallel_workers"] == 16
    assert provider._config_cache["compute.performance_threshold_ms"] == 12.5
    assert provider._config_cache["orchestrator.action_emission_enabled"] is False


# ---------------------------------------------------------------------------
# Secret backend CI detection
# ---------------------------------------------------------------------------


def test_ci_detection_unconfigured_is_not_ci(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NODE_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    backend = ModelSecretBackend(backend_type="environment")
    assert backend.detect_environment_type() == "production"


@pytest.mark.parametrize(
    "indicator", ["CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS", "GITLAB_CI"]
)
def test_ci_detection_configured_is_ci(
    unconfigured: None, monkeypatch: pytest.MonkeyPatch, tmp_path, indicator: str
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NODE_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    monkeypatch.setenv(indicator, "1")
    backend = ModelSecretBackend(backend_type="environment")
    assert backend.detect_environment_type() == "ci"
