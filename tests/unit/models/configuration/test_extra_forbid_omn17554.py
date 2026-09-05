# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-17554 — the four models this migration touched now reject unknown fields.

The extra-forbid ratchet fires on any *baselined* model whose body a change
touches: migrating the environment loops in these four meant closing their
silent-drop hole in the same PR rather than leaving it for a later one.

Pydantic's default is ``extra="ignore"``. Before this change a caller that
misspelled a field name got a model built entirely from defaults, no error, and
— on the two credential models — a silently dropped password. That is the
failure class the ratchet exists to retire, so each of the four gets a real
rejection test rather than a config-inspection assertion.

The last test here is the consequence the reviewers of the earlier attempt
caught: once ``ModelSecureCredentials`` forbids extras, its concrete subclass's
own environment loader stops being able to smuggle a payload key that is not a
declared field.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from omnibase_core.models.configuration.model_database_connection_config import (
    ModelDatabaseConnectionConfig,
)
from omnibase_core.models.configuration.model_database_secure_config import (
    ModelDatabaseSecureConfig,
)
from omnibase_core.models.configuration.model_rest_api_connection_config import (
    ModelRestApiConnectionConfig,
)
from omnibase_core.models.security.model_secret_backend import ModelSecretBackend

pytestmark = pytest.mark.unit


def test_database_connection_config_rejects_an_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ModelDatabaseConnectionConfig(
            host="db.example",
            database="onex",
            username="onex",
            password=SecretStr("pw"),  # pragma: allowlist secret
            hostt="typo.example",  # type: ignore[call-arg]
        )


def test_rest_api_connection_config_rejects_an_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ModelRestApiConnectionConfig(
            base_url="https://api.example",
            base_urll="https://typo.example",  # type: ignore[call-arg]
        )


def test_secret_backend_rejects_an_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ModelSecretBackend(backend_typ="environment")  # type: ignore[call-arg]


def test_secure_credentials_base_rejects_an_unknown_field() -> None:
    """The base is abstract, so its policy is proven through a concrete subclass."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ModelDatabaseSecureConfig(
            host="db.example",
            port=5432,
            database="onex",
            username="onex",
            password=SecretStr("pw"),  # pragma: allowlist secret
            not_a_declared_field="x",  # type: ignore[call-arg]
        )


def test_canonical_db_schema_binding_reaches_its_declared_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``ONEX_DB_SCHEMA`` must land on ``db_schema``, the field that exists.

    ``load_from_env`` built its payload with the key ``"schema"`` while the
    declared field is ``db_schema`` (``schema`` shadows a BaseModel member).
    Under the old ``extra="ignore"`` default that mismatch was invisible — the
    value was dropped and the config loaded looking fine. Under the inherited
    ``extra="forbid"`` it becomes a hard ValidationError, so the mismatch has to
    be fixed rather than tolerated.
    """
    for name in (
        "ONEX_DB_HOST",
        "ONEX_DB_PASSWORD",
        "ONEX_DB_SCHEMA",
        "ONEX_DB_PORT",
        "ONEX_DB_DATABASE",
        "ONEX_DB_USERNAME",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ONEX_DB_HOST", "db.example")
    monkeypatch.setenv("ONEX_DB_PASSWORD", "pw")  # pragma: allowlist secret
    monkeypatch.setenv("ONEX_DB_SCHEMA", "tenant_schema")

    config = ModelDatabaseSecureConfig.load_from_env()

    assert config.db_schema == "tenant_schema"
    assert config.host == "db.example"
