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

OMN-17554 — this module is the *only* environment read in core product code
--------------------------------------------------------------------------
Every config model, resolver and secret loop that previously performed its own
``os.environ.get(<computed key>)`` now declares a typed
:class:`~omnibase_core.models.configuration.model_env_overlay_binding.ModelEnvOverlayBinding`
and asks :func:`resolve_overlay_binding` for the value. Callers that resolve a
name carried in a contract string (the ``${env.VAR}`` template syntax itself)
use :func:`resolve_env_value`. Both funnel into :func:`_read_env`, the single
process-environment read this package sanctions.

The split matters because a *declared* binding is enumerable and assertable — a
test can pin the exact binding table a model owns — while a computed key inside
a loop body is invisible to every static gate.
"""

from __future__ import annotations

import os
import re

from omnibase_core.models.configuration.model_env_overlay_binding import (
    ModelEnvOverlayBinding,
)

# ``${env.VAR}`` / ``${env.VAR:default}`` — the same env-overlay convention
# the infra runtime overlay and node_contract_loader_effect use for endpoints.
_ENV_REF = re.compile(
    r"\$\{env\.(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::(?P<default>[^}]*))?\}"
)


def _read_env(name: str) -> str | None:
    """The single sanctioned process-environment read in ``omnibase_core``.

    Returns ``None`` when the variable is unset, so every caller decides its own
    fail-closed behaviour explicitly rather than inheriting an empty string it
    cannot distinguish from a deliberately blank value.
    """
    return os.environ.get(name)


def resolve_env_value(name: str, default: str | None = None) -> str | None:
    """Resolve one contract-declared ``${env.NAME}`` reference.

    Args:
        name: The variable named by the contract template.
        default: The inline ``${env.NAME:default}`` fallback, or ``None`` when
            the template declared none.

    Returns:
        The operator-supplied value; otherwise ``default``; otherwise ``None``.
        A variable that is set to the empty string resolves to the empty
        string, never to the default — an operator blanking a value is a
        deliberate act, not an absence.
    """
    value = _read_env(name)
    if value is not None:
        return value
    return default


def resolve_overlay_binding(binding: ModelEnvOverlayBinding) -> str | None:
    """Resolve one typed, declared binding to its operator-supplied value.

    Returns ``None`` when the declared variable is unset, so the caller leaves
    the model's own typed default in place instead of overriding it.
    """
    return _read_env(binding.env_var)


def has_env_prefix(prefix: str) -> bool:
    """Report whether the operator environment carries any name under ``prefix``.

    The one structural probe over the environment *namespace* rather than a
    single declared name: a credential loader uses it to decide whether a whole
    prefixed family is present before attempting to load it.
    """
    return any(name.startswith(prefix) for name in os.environ)


def expand_contract_env_refs(value: str) -> str:
    """Expand ``${env.VAR}`` / ``${env.VAR:default}`` references in ``value``.

    Resolves each reference from the operator environment; an unset var with no
    inline default expands to the empty string (so the caller fails closed rather
    than passing a literal ``${env.…}`` placeholder downstream or defaulting to
    localhost).
    """

    def _sub(match: re.Match[str]) -> str:
        resolved = resolve_env_value(match.group("name"), match.group("default"))
        return resolved if resolved is not None else ""

    return _ENV_REF.sub(_sub, value)


__all__: list[str] = [
    "expand_contract_env_refs",
    "has_env_prefix",
    "resolve_env_value",
    "resolve_overlay_binding",
]
