# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Core-resident ``${env.VAR}`` overlay expansion for contract string values.

This is the sanctioned overlay-resolution surface for the ``${env.VAR}`` /
``${env.VAR:default}`` convention that contract descriptors use to bind a
lane-specific value (an endpoint host, a port, a connection URI) from the
operator environment WITHOUT hardcoding the value in source.

``omnibase_core`` owns the resolver authority that every downstream repo imports
(OMN-13556 / OMN-13559: "core owns the resolver authority every other repo
imports"). The runtime overlay package in ``omnibase_infra``
(``omnibase_infra.runtime.overlay.contract_env_ref``) is the infra-layer mirror
of this surface; core cannot import infra (compat → core → spi → infra layering),
so the contract-env-ref expansion lives here for any core-resident consumer
(doctor probes, config models) that must resolve a contract-declared endpoint
reference without reaching upward into infra.

An unset var with no inline default expands to the empty string, so the caller's
fail-closed check rejects it (rather than leaving a literal ``${env.…}``
placeholder, or silently falling back to localhost).
"""

from __future__ import annotations

import os
import re

# ``${env.VAR}`` / ``${env.VAR:default}`` — the same env-overlay convention
# the infra runtime overlay and node_contract_loader_effect use for endpoints.
_ENV_REF = re.compile(
    r"\$\{env\.(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::(?P<default>[^}]*))?\}"
)


def expand_contract_env_refs(value: str) -> str:
    """Expand ``${env.VAR}`` / ``${env.VAR:default}`` references in ``value``.

    Resolves each reference from the operator environment; an unset var with no
    inline default expands to the empty string (so the caller fails closed rather
    than passing a literal ``${env.…}`` placeholder downstream or defaulting to
    localhost).
    """

    def _sub(match: re.Match[str]) -> str:
        name = match.group("name")
        default = match.group("default")
        return os.environ.get(name, default if default is not None else "")

    return _ENV_REF.sub(_sub, value)


__all__: list[str] = ["expand_contract_env_refs"]
