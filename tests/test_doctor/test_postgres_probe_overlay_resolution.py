# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolution-equivalence tests for the Postgres-probe overlay migration.

OMN-13559 (Wave 1 endpoint→overlay) — the ``postgres`` doctor check no longer
reads ``os.environ["POSTGRES_HOST"]`` / ``os.environ["POSTGRES_PORT"]`` directly;
it resolves the probe endpoint through the sanctioned overlay boundary
(``expand_contract_env_refs`` against the contract references
``${env.POSTGRES_HOST}`` / ``${env.POSTGRES_PORT}``).

These tests assert:
1. The overlay-resolved values equal the values the prior direct env reads gave,
   for representative dev/stability/prod lane bindings (resolution equivalence).
2. The model fails closed (raises) when the overlay does not bind the var,
   rather than silently falling back to localhost.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.doctor.model_postgres_probe_config import (
    ModelPostgresProbeConfig,
)

pytestmark = pytest.mark.unit

# Representative per-lane (host, port) bindings the existing deployment env
# injects. Hostnames only (no LAN IP literals — the equivalence assertion is
# value-agnostic: the overlay must resolve whatever the lane binds, byte-for-byte).
_LANE_BINDINGS = (
    ("postgres", "5432"),  # dev (compose service DNS)
    ("postgres-stability", "25432"),  # stability-test lane host/port
    ("postgres-prod", "35432"),  # prod lane host/port
)


class TestPostgresProbeOverlayResolution:
    """Overlay resolution equivalence for POSTGRES_HOST / POSTGRES_PORT."""

    @pytest.mark.parametrize(("lane_host", "lane_port"), _LANE_BINDINGS)
    def test_overlay_resolves_same_value_as_env_read(
        self, lane_host: str, lane_port: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The overlay default_factory resolves the exact env-bound endpoint.

        Equivalent to what the prior ``os.environ["POSTGRES_HOST"]`` /
        ``int(os.environ["POSTGRES_PORT"])`` reads returned — same vars, same
        values, now via the sanctioned overlay seam.
        """
        monkeypatch.setenv("POSTGRES_HOST", lane_host)
        monkeypatch.setenv("POSTGRES_PORT", lane_port)
        config = ModelPostgresProbeConfig.from_overlay()
        assert config.host == lane_host
        assert config.port == int(lane_port)

    def test_explicit_values_bypass_overlay(self) -> None:
        """Explicitly constructed host/port do not invoke the overlay resolver."""
        config = ModelPostgresProbeConfig(host="explicit-host", port=15432)
        assert config.host == "explicit-host"
        assert config.port == 15432

    def test_host_fails_closed_when_overlay_unbound(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unset host binding fails closed instead of defaulting to localhost."""
        monkeypatch.delenv("POSTGRES_HOST", raising=False)
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        with pytest.raises(ValueError, match="POSTGRES_HOST is not bound"):
            ModelPostgresProbeConfig.from_overlay()

    def test_port_fails_closed_when_overlay_unbound(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unset port binding fails closed instead of defaulting."""
        monkeypatch.setenv("POSTGRES_HOST", "somehost")
        monkeypatch.delenv("POSTGRES_PORT", raising=False)
        with pytest.raises(ValueError, match="POSTGRES_PORT is not bound"):
            ModelPostgresProbeConfig.from_overlay()

    def test_port_fails_closed_on_non_integer_overlay_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-integer overlay-bound port fails closed with a clear error."""
        monkeypatch.setenv("POSTGRES_HOST", "somehost")
        monkeypatch.setenv("POSTGRES_PORT", "not-a-port")
        with pytest.raises(ValueError, match="not a valid port integer"):
            ModelPostgresProbeConfig.from_overlay()
