# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Doctor check that proves a real typed configuration binding (OMN-17554).

This check used to read ``os.environ`` for a hardcoded list of variable names.
That could only ever prove that some ambient string was non-empty — it proved
nothing about the configuration ONEX actually resolves, and an earlier repair
that let the caller inject the required set produced a doctor that asserted its
own health.

The authority is now the declared typed binding in ``~/.onex/config.yaml``, the
same file :mod:`omnibase_core.cli.cli_user_config` writes:

#. one bounded read of the source bytes;
#. one bounded decode;
#. one bounded YAML parse plus source-shape check;
#. one non-writing, recursive projection of the parsed mapping onto the
   declared :class:`ModelCliUserConfig` fields and their declared aliases, at
   every declared-model depth, omitting absent fields and sections;
#. exactly one ``ModelCliUserConfig`` validation over that projection.

Nothing here writes, migrates, normalizes or falls back. Unknown and unrelated
keys stay in the parsed source mapping and are simply absent from the strict
payload, so an ``aws:`` block or a hand-added credential key can never turn a
healthy install unhealthy.

Every failure is classified at the operation that has configuration provenance
and converted immediately into a fixed, secret-safe outcome: no exception text,
no source path, no parser detail and no configured value ever reaches a result
message, a renderer or a log. Programmer faults propagate.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ValidationError

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_doctor_config_load_code import EnumDoctorConfigLoadCode
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.cli.model_cli_user_config import ModelCliUserConfig
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult
from omnibase_core.types.type_serializable_value import (
    SerializableValue,
    SerializedDict,
)

# The public result vocabulary. Fixed strings, chosen so that no code path can
# interpolate a value, a path, or an exception into user-visible output.
_MESSAGE_MISSING_BINDING = "Missing: LINEAR_API_KEY"
_MESSAGE_HEALTHY = "All required configuration bindings present"

_FIXED_ERROR_MESSAGES: dict[EnumDoctorConfigLoadCode, str] = {
    EnumDoctorConfigLoadCode.MISSING: _MESSAGE_MISSING_BINDING,
    EnumDoctorConfigLoadCode.EMPTY: _MESSAGE_MISSING_BINDING,
    EnumDoctorConfigLoadCode.UNREADABLE: (
        "User configuration is unavailable; check configuration file access."
    ),
    EnumDoctorConfigLoadCode.INVALID_ENCODING: (
        "User configuration has invalid text encoding."
    ),
    EnumDoctorConfigLoadCode.INVALID_YAML: "User configuration contains invalid YAML.",
    EnumDoctorConfigLoadCode.INVALID_MODEL: "Managed user configuration is invalid.",
}


# The typed load outcome. A pair rather than a second class in this module:
# ``onex-single-class-per-file`` allows one non-enum class per file, and the
# doctor repair for OMN-17554 is bounded to a fixed six-path ceiling, so a
# separate model module is not available. The discriminant is the code; the
# model is present if and only if the code is ``VALID``, which is structural —
# only the VALID return path below supplies one, and every error return carries
# the code alone: no exception text, path, parser text, decoded content, value
# or copied credential.
DoctorConfigLoadOutcome = tuple[EnumDoctorConfigLoadCode, "ModelCliUserConfig | None"]


def default_user_config_path() -> Path:
    """The declared binding source: ``~/.onex/config.yaml``.

    Delegates to the shared resolver so the doctor can never read a different
    file from the one the CLI writers maintain. The import is function-local
    because ``omnibase_core.cli`` imports this package (``cli_doctor`` ->
    ``doctor.checks``), so a module-level ``doctor -> cli`` import closes a
    package cycle and fails at collection time.
    """
    from omnibase_core.cli.cli_user_config import user_config_path

    return user_config_path()


def _project_declared(
    model: type[BaseModel], source: Mapping[str, SerializableValue]
) -> SerializedDict:
    """Project ``source`` onto ``model``'s declared fields and aliases.

    Recurses into every declared ``BaseModel`` child using that child's own
    field names and declared aliases, so an unknown key nested beneath a
    declared section never reaches strict validation. Absent fields and
    sections are omitted rather than injected, so the model's own defaults
    apply. ``source`` is never mutated and never written back.

    A declared child whose source value is not a mapping is passed through
    unchanged so the single validation below rejects it, rather than being
    silently dropped or coerced here.
    """
    projected: SerializedDict = {}
    for name, field in model.model_fields.items():
        # ``populate_by_name=True`` on these models means either spelling
        # binds; prefer the alias, which is the on-disk key.
        for key in (field.alias, name):
            if key is None or key not in source:
                continue
            value = source[key]
            annotation = field.annotation
            if (
                isinstance(annotation, type)
                and issubclass(annotation, BaseModel)
                and isinstance(value, Mapping)
            ):
                projected[key] = _project_declared(annotation, value)
            else:
                projected[key] = value
            break
    return projected


def load_declared_user_config(path: Path) -> DoctorConfigLoadOutcome:
    """Resolve the declared typed binding at ``path``, fail-closed.

    Each catch is scoped to the single operation that owns that provenance.
    Anything else — a programmer fault, an unexpected runtime error — is
    allowed to propagate.
    """
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return (EnumDoctorConfigLoadCode.MISSING, None)
    except OSError:
        # PermissionError, IsADirectoryError and every other read failure.
        return (EnumDoctorConfigLoadCode.UNREADABLE, None)

    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return (EnumDoctorConfigLoadCode.INVALID_ENCODING, None)

    # Function-local for the same package-cycle reason as
    # default_user_config_path above.
    from omnibase_core.cli.cli_user_config import parse_user_config_text

    try:
        # The shared parser, and only the parser: it raises for invalid YAML
        # and for a non-mapping document, which are the same public outcome.
        # The normalizer that sits beside it is deliberately not called.
        parsed = parse_user_config_text(text, str(path))
    except ModelOnexError:
        return (EnumDoctorConfigLoadCode.INVALID_YAML, None)

    if parsed is None:
        return (EnumDoctorConfigLoadCode.EMPTY, None)

    projected = _project_declared(ModelCliUserConfig, parsed)

    try:
        config = ModelCliUserConfig.model_validate(projected)
    except ValidationError:
        return (EnumDoctorConfigLoadCode.INVALID_MODEL, None)

    return (EnumDoctorConfigLoadCode.VALID, config)


class CheckEnvVars(DoctorCheckBase):
    """Report whether the declared typed configuration binding resolves."""

    # Plain assignments, not re-annotations: DoctorCheckBase already declares
    # these as ClassVars, and the string-version AST gate reads an annotated
    # ``check_id: str`` as an unmigrated string identifier field (which is why
    # doctor_check_base.py itself is on that hook's exclude list).
    check_id = "env_vars"
    check_name = "env_vars"
    category = EnumDoctorCategory.ENVIRONMENT

    def __init__(self, config_path: Path | None = None) -> None:
        """Resolve the binding source.

        ``DoctorRegistry.list_all()`` constructs checks with no arguments, so
        the production route resolves the real user config file and this
        constructor must never raise for a configuration-origin failure — the
        failure becomes a typed outcome instead.
        """
        self.config_path = (
            config_path if config_path is not None else default_user_config_path()
        )
        self.outcome_code, self.config = load_declared_user_config(self.config_path)

    def run(self) -> ModelDoctorCheckResult:
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=self._status(),
            message=self._message(),
        )

    def _has_required_binding(self) -> bool:
        return self.config is not None and bool(self.config.credentials.linear_api_key)

    def _status(self) -> EnumHealthStatusValue:
        if self.outcome_code is EnumDoctorConfigLoadCode.VALID and (
            self._has_required_binding()
        ):
            return EnumHealthStatusValue.HEALTHY
        return EnumHealthStatusValue.UNHEALTHY

    def _message(self) -> str:
        if self.outcome_code is not EnumDoctorConfigLoadCode.VALID:
            return _FIXED_ERROR_MESSAGES[self.outcome_code]
        return (
            _MESSAGE_HEALTHY
            if self._has_required_binding()
            else _MESSAGE_MISSING_BINDING
        )


__all__ = [
    "CheckEnvVars",
    "DoctorConfigLoadOutcome",
    "default_user_config_path",
    "load_declared_user_config",
]
