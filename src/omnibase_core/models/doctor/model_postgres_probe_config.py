# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Overlay-resolved endpoint config for the Postgres doctor probe.

OMN-13559 (Wave 1 endpoint→overlay) — the ``postgres`` doctor check no longer
reads ``os.environ["POSTGRES_HOST"]`` / ``os.environ["POSTGRES_PORT"]`` directly.
The probe endpoint resolves through the sanctioned overlay boundary
(``expand_contract_env_refs`` against the contract references
``${env.POSTGRES_HOST}`` / ``${env.POSTGRES_PORT}``); a per-lane overlay binds
those vars to the dev/stability/prod value. Resolution fails closed (raises)
when the active overlay does not bind them, rather than silently defaulting to
localhost.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.overlays.contract_env_ref import expand_contract_env_refs

__all__ = ["ModelPostgresProbeConfig"]

# Contract-declared endpoint references. The Postgres host/port for the doctor
# probe resolve through the sanctioned overlay boundary
# (``expand_contract_env_refs``, the one core-resident env-reading surface) — a
# per-lane overlay binds these to the dev/stability/prod value. The check must
# NOT read ``os.environ`` directly (OMN-13559 endpoint-overlay migration).
_HOST_CONTRACT_REF = "${env.POSTGRES_HOST}"
_PORT_CONTRACT_REF = "${env.POSTGRES_PORT}"


class ModelPostgresProbeConfig(BaseModel):
    """Endpoint config for the Postgres doctor probe.

    Construct via :meth:`from_overlay`, which resolves ``host`` / ``port`` from
    the contract + per-lane overlay through the sanctioned overlay boundary. If
    the active overlay does not bind ``${env.POSTGRES_HOST}`` /
    ``${env.POSTGRES_PORT}``, resolution fails closed with a ``ValueError``
    rather than silently falling back to localhost.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: str = Field(
        default=...,
        description=(
            "Postgres host for the doctor probe "
            "(contract ${env.POSTGRES_HOST}, resolved via overlay)"
        ),
    )
    port: int = Field(
        default=...,
        ge=1,
        le=65535,
        description=(
            "Postgres port for the doctor probe "
            "(contract ${env.POSTGRES_PORT}, resolved via overlay)"
        ),
    )

    @classmethod
    def from_overlay(cls) -> ModelPostgresProbeConfig:
        """Resolve host/port through the overlay seam — fail closed if unbound.

        The contract declares the endpoint as ``${env.POSTGRES_HOST}`` /
        ``${env.POSTGRES_PORT}``; the overlay resolver expands each reference
        against the lane environment. An unset var expands to the empty string,
        which fails the explicit guards below rather than silently falling back
        to localhost.
        """
        host = expand_contract_env_refs(_HOST_CONTRACT_REF)
        if not host:
            raise ValueError(
                "POSTGRES_HOST is not bound by the active overlay; declare it in "
                "the per-lane overlay so the contract reference "
                f"{_HOST_CONTRACT_REF!r} resolves to a Postgres host."
            )
        port_str = expand_contract_env_refs(_PORT_CONTRACT_REF)
        if not port_str:
            raise ValueError(
                "POSTGRES_PORT is not bound by the active overlay; declare it in "
                "the per-lane overlay so the contract reference "
                f"{_PORT_CONTRACT_REF!r} resolves to a Postgres port."
            )
        try:
            port = int(port_str)
        except ValueError as exc:
            raise ValueError(
                f"POSTGRES_PORT overlay value {port_str!r} is not a valid port integer."
            ) from exc
        return cls(host=host, port=port)
