# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Prove the ONEX credential binding is real (OMN-17554).

What this check used to do
--------------------------
It read the process environment for a hardcoded list of names. That made the
doctor an observer of ambient process state rather than of ONEX configuration:
an exported shell variable reported healthy, and an operator whose
``~/.onex/config.yaml`` was empty could not tell. Worse, a version of this check
took its name list from
the caller that also supplied the values — so it asserted the health of a set it
had injected itself and reported "All 2 dependencies bound" with both real
values absent.

What it does now
----------------
It resolves the binding from the one typed authority that owns it:
``~/.onex/config.yaml``, validated as
:class:`~omnibase_core.models.cli.model_cli_user_config.ModelCliUserConfig`.
The file is read once, projected once, validated once, and never written.

Why this file does its own projection instead of calling
``cli_user_config.normalize_user_config``
-----------------------------------------------------------------------------
``normalize_user_config`` is the *writer's* surface. It resolves versions,
migrates legacy shapes, merges validated output back over the raw mapping and
reports whether the caller should rewrite the file. A diagnostic must not carry
any of that: it must not migrate, must not decide the file is out of date, and
must not hand back a mapping that a later writer could persist. It also
preserves unknown keys, which strict revalidation then rejects — the exact
failure that made a real user config (one carrying the ``aws:`` block ``onex
refresh-credentials`` writes) read as invalid.

So the read path here is deliberately one-directional and total:

    bytes -> utf-8 -> yaml -> recursive declared-field projection -> one
    ``ModelCliUserConfig`` validation -> the typed binding.

The projection is recursive because the managed section models are
``extra="forbid"``: a one-layer projection hands a declared section through
whole, so an unknown key *nested inside* ``credentials:`` still reaches strict
validation. Absent fields and sections are omitted rather than filled with
``{}``, so each model's own typed defaults apply.

Every failure is converted to a fixed, secret-safe message. No parser text, no
exception text, no filesystem path and no configured value ever reaches the
operator-facing output — a credential-shaped value in a malformed file is
exactly the thing a Pydantic ``ValidationError`` would otherwise print.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ValidationError

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.cli.model_cli_user_config import ModelCliUserConfig
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult

# The operator-facing name of the config file. A fixed display string, never the
# resolved path: the resolved path is machine-specific, leaks the user's home
# directory into shared output, and differs under test.
DISPLAY_CONFIG_PATH: Final[str] = "~/.onex/config.yaml"

# The dotted location of the binding this check proves, as an operator would
# write it in the file.
BINDING_LOCATION: Final[str] = "credentials.LINEAR_API_KEY"

_INIT_HINT: Final[str] = "run 'onex config init'"

_MSG_ABSENT: Final[str] = f"No ONEX config at {DISPLAY_CONFIG_PATH}; {_INIT_HINT}."
_MSG_EMPTY: Final[str] = f"{DISPLAY_CONFIG_PATH} is empty; {_INIT_HINT}."
_MSG_UNREADABLE: Final[str] = f"{DISPLAY_CONFIG_PATH} could not be read."
_MSG_INVALID_ENCODING: Final[str] = f"{DISPLAY_CONFIG_PATH} is not valid UTF-8."
_MSG_INVALID_YAML: Final[str] = (
    f"{DISPLAY_CONFIG_PATH} is not a valid YAML mapping; {_INIT_HINT}."
)
_MSG_INVALID_MODEL: Final[str] = (
    f"{DISPLAY_CONFIG_PATH} has an invalid managed section; {_INIT_HINT}."
)
_MSG_UNBOUND: Final[str] = (
    f"{BINDING_LOCATION} is not set in {DISPLAY_CONFIG_PATH}; {_INIT_HINT}."
)
_MSG_BOUND: Final[str] = f"{BINDING_LOCATION} is bound from {DISPLAY_CONFIG_PATH}."


def _project(
    model: type[BaseModel], section: Mapping[str, object]
) -> dict[str, object]:
    """Project ``section`` onto exactly the fields ``model`` declares.

    Recursive, non-writing, and keyed on both the declared field name and its
    alias (the file spells credentials in ``SCREAMING_CASE``; the model field is
    ``linear_api_key``). A key the model does not declare is dropped at whatever
    depth it appears. A field the file does not carry is omitted entirely, so
    the model's own default applies rather than an injected empty mapping.

    A declared sub-model whose value is not a mapping is passed through
    unchanged so the single validation below rejects it, rather than being
    silently coerced here.
    """
    projected: dict[str, object] = {}
    for name, field in model.model_fields.items():
        candidates = (name,) if field.alias is None else (field.alias, name)
        for key in candidates:
            if key not in section:
                continue
            value = section[key]
            annotation = field.annotation
            if (
                isinstance(annotation, type)
                and issubclass(annotation, BaseModel)
                and isinstance(value, Mapping)
            ):
                projected[name] = _project(annotation, value)
            elif (
                isinstance(annotation, type)
                and issubclass(annotation, BaseModel)
                and value is None
            ):
                # ``logging:`` with no children parses to None. It carries no
                # values, so the section takes its defaults.
                projected[name] = {}
            else:
                projected[name] = value
            break
    return projected


class CheckEnvVars(DoctorCheckBase):
    """Report whether the ONEX credential binding resolves to a real value."""

    check_id = "env_vars"
    check_name = "ONEX credentials"
    category = EnumDoctorCategory.ENVIRONMENT

    def __init__(self, config_path: Path) -> None:
        """Bind the check to a config location.

        Pure: it stores the path and touches nothing. ``DoctorRegistry`` builds
        every check before running any of them, so a constructor that read the
        filesystem would take the entire report down on one bad file.
        """
        self._config_path = config_path

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        status, message = self._evaluate()
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=status,
            message=message,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    def _evaluate(self) -> tuple[EnumHealthStatusValue, str]:
        """Resolve the binding, converting every config-origin fault to a message.

        Each ``except`` is bound to the one operation that can raise it, so a
        programmer fault (an ``AttributeError`` from a renamed field, say) still
        propagates and is caught by the registry as a crash rather than being
        laundered into a plausible-looking unhealthy result.
        """
        try:
            raw_bytes = self._config_path.read_bytes()
        except FileNotFoundError:
            return EnumHealthStatusValue.UNHEALTHY, _MSG_ABSENT
        except OSError:
            return EnumHealthStatusValue.UNHEALTHY, _MSG_UNREADABLE

        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return EnumHealthStatusValue.UNHEALTHY, _MSG_INVALID_ENCODING

        # ``cli_user_config.parse_user_config_text`` is the module-declared
        # single raw-YAML entry point for this file. Parsing it a second time
        # here would fork that entry point; it also already rejects a document
        # that is not a top-level mapping, which is the same fault class.
        #
        # Imported here rather than at module scope because
        # ``omnibase_core.cli.__init__`` eagerly builds the whole CLI, and
        # ``cli_commands`` imports ``cli_doctor``, which imports this package —
        # a module-level import closes that cycle and makes
        # ``import omnibase_core.doctor.checks`` fail on a cold interpreter.
        # ``test_doctor_checks_package_imports_on_a_cold_interpreter`` pins it.
        from omnibase_core.cli.cli_user_config import (
            parse_user_config_text,
        )

        try:
            document = parse_user_config_text(text, DISPLAY_CONFIG_PATH)
        except ModelOnexError:
            # Its message names the source and quotes the parser; neither is
            # safe to surface, so only the classification crosses this line.
            return EnumHealthStatusValue.UNHEALTHY, _MSG_INVALID_YAML

        if document is None:
            return EnumHealthStatusValue.UNHEALTHY, _MSG_EMPTY

        try:
            config = ModelCliUserConfig.model_validate(
                _project(ModelCliUserConfig, document)
            )
        except ValidationError:
            return EnumHealthStatusValue.UNHEALTHY, _MSG_INVALID_MODEL

        if not config.credentials.linear_api_key.strip():
            return EnumHealthStatusValue.UNHEALTHY, _MSG_UNBOUND
        return EnumHealthStatusValue.HEALTHY, _MSG_BOUND


__all__ = ["BINDING_LOCATION", "DISPLAY_CONFIG_PATH", "CheckEnvVars"]
