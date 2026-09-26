# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A runtime lane, as the deployment's overlay declares it (OMN-19746).

Operator ruling 2026-09-26 (firm): the set of runtime lanes and what each is
for must not be compiled into a package and must not be read from our own
lab's files, because this architecture ships to customers who have no access to
our lab. Whoever runs a runtime declares its lane in a ``runtime.lane`` overlay
document; this module is the typed body of that document and the rules a
runtime applies to it at startup. It names no lane.

Resolution is pure. The runtime reads its lane id from the bootstrap variable
``ONEX_RUNTIME_LANE`` and the document from its one config overlay source at
the scope ``(environment, lane)``, then calls :meth:`resolve`. Every way that
can fail raises, and the runtime refuses to start: a runtime that cannot name
its lane never runs DEGRADED with its lane-scoped contracts silently dropped
(the failure OMN-19408 measured on two lab hosts).
"""

from __future__ import annotations

import re
from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from omnibase_core.enums.enum_config_overlay_key import EnumConfigOverlayKey
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_runtime_lane_role import EnumRuntimeLaneRole
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.config_overlay.model_config_overlay_document import (
    ModelConfigOverlayDocument,
)

#: The bootstrap variable a deployment sets to name its runtime's lane
#: (OMN-18769). Identity only: what the lane is for comes from the overlay.
RUNTIME_LANE_ENV_VAR: Final[str] = "ONEX_RUNTIME_LANE"

#: The schema_version of a ``runtime.lane`` document this model reads.
RUNTIME_LANE_SCHEMA_VERSION: Final[str] = "runtime_lane.v1"

# Same shape as one ModelConfigOverlayScope segment: the lane id is the scope
# segment the document is stored under.
_LANE_ID_PATTERN: Final[str] = r"^[a-z0-9][a-z0-9-]*$"
_LANE_ID_MAX: Final[int] = 64
_LANE_ID_RE: Final[re.Pattern[str]] = re.compile(_LANE_ID_PATTERN)
_ROLE_VALUES: Final[frozenset[str]] = frozenset(
    role.value for role in EnumRuntimeLaneRole
)


def normalize_runtime_lane_roles(
    value: object, *, allow_empty: bool = False
) -> tuple[EnumRuntimeLaneRole, ...]:
    """Parse a role list (or one role) into roles, de-duplicated in order.

    Raises ``ValueError`` on a non-string entry, a role outside
    :class:`EnumRuntimeLaneRole` (naming the vocabulary), or an empty list
    unless ``allow_empty``.
    """
    problem: str | None = None
    raw_values: tuple[object, ...] = ()
    if isinstance(value, str):
        raw_values = (value,)
    elif isinstance(value, (list, tuple)):
        raw_values = tuple(value)
    else:
        problem = "roles must be a role name or a list of role names"
    if problem is None and not raw_values and not allow_empty:
        problem = "roles must name at least one role"
    roles: list[EnumRuntimeLaneRole] = []
    for raw in raw_values if problem is None else ():
        if isinstance(raw, EnumRuntimeLaneRole):
            roles.append(raw)
        elif not isinstance(raw, str):
            problem = f"role {raw!r} is not a string"
            break
        elif raw.strip() in _ROLE_VALUES:
            roles.append(EnumRuntimeLaneRole(raw.strip()))
        else:
            known = ", ".join(sorted(_ROLE_VALUES))
            problem = f"{raw!r} is not a runtime lane role; the roles are: {known}"
            break
    if problem is not None:
        raise ValueError(problem)  # error-ok: Pydantic validator needs ValueError
    return tuple(dict.fromkeys(roles))


class ModelRuntimeLaneDeclaration(BaseModel):
    """The body of a ``runtime.lane`` overlay document."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal["runtime_lane.v1"] = (
        Field(  # string-version-ok: overlay schema discriminator, not SemVer
            ..., description="Version tag of this document's schema."
        )
    )
    lane_id: str = Field(  # string-id-ok: a lane id is an operator-chosen slug and a store path segment, not a UUID
        ...,
        min_length=1,
        max_length=_LANE_ID_MAX,
        pattern=_LANE_ID_PATTERN,
        description=(
            "The lane's id: the value its runtime declares in ONEX_RUNTIME_LANE "
            "and the scope segment the document is stored under."
        ),
    )
    roles: tuple[EnumRuntimeLaneRole, ...] = Field(
        ...,
        description=(
            "What the lane is for, de-duplicated in declaration order. Empty is "
            "valid and means no role-gated contract attaches on this lane."
        ),
    )
    description: str = Field(
        ..., min_length=1, description="What this deployment is, for a reader."
    )

    @field_validator("roles", mode="before")
    @classmethod
    def _parse_roles(cls, value: object) -> tuple[EnumRuntimeLaneRole, ...]:
        return normalize_runtime_lane_roles(value, allow_empty=True)

    def has_roles(self, required: tuple[EnumRuntimeLaneRole, ...]) -> bool:
        """Return whether this lane holds every role in ``required``."""
        return set(required).issubset(self.roles)

    @classmethod
    def resolve(
        cls,
        *,
        declared_lane_id: str | None,
        document: ModelConfigOverlayDocument | None,
        where: str,
    ) -> Self:
        """Return the declaration for the lane this runtime says it is.

        Args:
            declared_lane_id: The value of ``ONEX_RUNTIME_LANE``, or ``None``.
            document: The ``runtime.lane`` document the runtime's one overlay
                source returned at ``(environment, declared lane)``, or ``None``
                when the source holds none there.
            where: The source and scope the document was looked for, named in
                every refusal (for example the store path or local file path).

        Raises:
            ModelOnexError: the lane is unset or not a lane id, the overlay
                does not declare it, the document is for another key or fails
                validation, or it declares a different lane. The runtime must
                refuse to start on any of them.
        """
        key = EnumConfigOverlayKey.RUNTIME_LANE
        lane = (declared_lane_id or "").strip()
        context = {"variable": RUNTIME_LANE_ENV_VAR, "key": key.value, "where": where}
        if not lane:
            raise ModelOnexError(
                message=(
                    f"{RUNTIME_LANE_ENV_VAR} is not set, so this runtime cannot "
                    "name its lane and refuses to start. Set it in the deployment "
                    f"that runs this process to the lane_id of a {key.value} "
                    f"overlay document ({where})."
                ),
                error_code=EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
                context=context,
            )
        if len(lane) > _LANE_ID_MAX or not _LANE_ID_RE.match(lane):
            raise ModelOnexError(
                message=(
                    f"{RUNTIME_LANE_ENV_VAR}={declared_lane_id!r} is not a lane id "
                    f"(lowercase letters, digits and hyphens, at most {_LANE_ID_MAX}); "
                    "this runtime refuses to start."
                ),
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                context={**context, "lane": lane},
            )
        context = {**context, "lane": lane}
        if document is None:
            raise ModelOnexError(
                message=(
                    f"runtime lane {lane!r} is not declared: no {key.value} "
                    f"overlay document at {where}. Whoever runs this runtime "
                    f"supplies that document (schema {key.schema_ref}, "
                    f"schema_version {RUNTIME_LANE_SCHEMA_VERSION}) declaring "
                    "lane_id, roles (may be empty) and description; this runtime refuses to "
                    "start without it."
                ),
                error_code=EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
                context=context,
            )
        if document.key is not key:
            raise ModelOnexError(
                message=(
                    f"runtime lane {lane!r}: the document read at {where} is a "
                    f"{document.key.value} document, not {key.value}."
                ),
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                context=context,
            )
        try:
            declaration = cls.model_validate(document.content)
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(part) for part in error['loc']) or '<document>'}: "
                f"{error['msg']}"
                for error in exc.errors()
            )
            raise ModelOnexError(
                message=(
                    f"runtime lane {lane!r}: the {key.value} document at {where} "
                    f"(sha256 {document.sha256}) is invalid: {problems}"
                ),
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                context={**context, "sha256": document.sha256},
            ) from exc
        if declaration.lane_id != lane:
            raise ModelOnexError(
                message=(
                    f"{RUNTIME_LANE_ENV_VAR}={lane!r} but the {key.value} "
                    f"document at {where} declares lane_id "
                    f"{declaration.lane_id!r}; one of them is wrong and this "
                    "runtime refuses to start."
                ),
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                context={**context, "document_lane_id": declaration.lane_id},
            )
        return declaration


__all__ = [
    "RUNTIME_LANE_ENV_VAR",
    "RUNTIME_LANE_SCHEMA_VERSION",
    "ModelRuntimeLaneDeclaration",
    "normalize_runtime_lane_roles",
]
