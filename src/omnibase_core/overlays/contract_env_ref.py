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

Two surfaces, one boundary
--------------------------

:func:`expand_contract_env_refs` substitutes references inside a larger string
(an endpoint template, a path). :func:`resolve_contract_env_binding` resolves a
single reference and returns a typed
:class:`~omnibase_core.models.configuration.model_contract_env_binding.ModelContractEnvBinding`
that preserves whether the variable was *declared* at all — the distinction
substitution throws away, and the one every configuration override in this repo
turns on. Product code declares its bindings as ``${env.NAME}`` references and
resolves them here (OMN-17554); it does not read the environment itself.
"""

from __future__ import annotations

import os
import re

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.configuration.model_contract_env_binding import (
    ModelContractEnvBinding,
)

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


# A bare variable name, i.e. what goes between ``${env.`` and ``}``.
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# A string that is exactly one reference and nothing else.
_ENV_REF_EXACT = re.compile(f"^{_ENV_REF.pattern}$")


def contract_env_reference(name: str, default: str | None = None) -> str:
    """Render the canonical ``${env.NAME}`` / ``${env.NAME:default}`` reference.

    Fails closed on a name that is not a legal environment variable identifier,
    so a caller that derives reference names from a declared field set cannot
    silently emit an unresolvable reference.
    """
    if not _ENV_NAME.match(name):
        raise ModelOnexError(
            f"{name!r} is not a legal environment variable name; a contract env "
            "reference must name an identifier.",
            EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    if default is None:
        return f"${{env.{name}}}"
    if "}" in default:
        raise ModelOnexError(
            "a contract env reference default must not contain '}'.",
            EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return f"${{env.{name}:{default}}}"


def resolve_contract_env_binding(reference: str) -> ModelContractEnvBinding:
    """Resolve exactly one ``${env.VAR}`` / ``${env.VAR:default}`` reference.

    Fails closed: a malformed, unclosed, or non-reference string raises rather
    than being passed through as a literal. An unset variable with no inline
    default resolves to ``bound=False, value=None`` so the caller can leave its
    typed default in place instead of overriding it with an empty string.
    """
    match = _ENV_REF_EXACT.match(reference)
    if match is None:
        raise ModelOnexError(
            f"{reference!r} is not a single ${{env.VAR}} contract reference.",
            EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    name = match.group("name")
    default = match.group("default")
    declared = os.environ.get(name)
    return ModelContractEnvBinding(
        name=name,
        reference=reference,
        bound=declared is not None,
        value=declared if declared is not None else default,
    )


__all__: list[str] = [
    "contract_env_reference",
    "expand_contract_env_refs",
    "resolve_contract_env_binding",
]
