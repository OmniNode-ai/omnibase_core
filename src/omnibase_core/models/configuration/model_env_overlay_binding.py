# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One contract-declared environment overlay binding (OMN-17554).

A binding is the typed declaration that "this model field is supplied by that
operator-environment variable". Before OMN-17554 the same information lived in
bare ``dict[str, str]`` literals inside each config model, and each model then
performed its own ``os.environ.get(env_var)`` read with a *computed* key — a
dynamic read no static gate can attribute to a declared name.

Splitting the declaration from the read is the whole point:

* the **declaration** is this model — validated, frozen, and enumerable, so a
  binding table can be asserted in a test and cannot acquire an undeclared name
  at runtime;
* the **read** happens in exactly one place,
  :func:`omnibase_core.overlays.contract_env_ref.resolve_overlay_binding`, the
  sanctioned ``${env.VAR}`` overlay boundary this package already owns.

No config model reads the process environment itself.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Operator environment variable names. Deliberately permissive about case so a
# caller-supplied prefix (``ONEX_``, a test's ``TEST_``) composes cleanly, but
# strict enough that a computed name carrying a path separator, a shell
# metacharacter, or an empty segment is rejected at declaration time.
_ENV_VAR_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*$"

# The field the value binds to on the receiving model: a Python identifier, or
# a dotted path where the receiving surface is keyed by one (the node config
# provider keys on "compute.max_parallel_workers").
_FIELD_NAME_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$"


class ModelEnvOverlayBinding(BaseModel):
    """A single declared ``environment variable -> typed field`` binding."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )

    env_var: str = Field(
        ...,
        pattern=_ENV_VAR_PATTERN,
        min_length=1,
        description="Operator environment variable that supplies this field.",
    )
    field_name: str = Field(
        ...,
        pattern=_FIELD_NAME_PATTERN,
        min_length=1,
        description="Field, or dotted field path, the variable binds to.",
    )


__all__ = ["ModelEnvOverlayBinding"]
