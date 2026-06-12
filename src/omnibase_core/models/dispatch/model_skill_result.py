# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed skill dispatch receipt envelope (OMN-13091).

``ModelSkillResult[T]`` is the skill-surface analogue of
:class:`~omnibase_core.models.dispatch.model_handler_output.ModelHandlerOutput`:
the single typed JSON object a receipt-mode dispatch (``onex node``/``onex run``
``--output receipt``) prints to stdout. It carries the FULL handler result —
never truncated, never size-limited — plus content-addressed
:class:`~omnibase_core.models.artifacts.model_artifact_ref.ModelArtifactRef`
handles for the captured intermediate context (runtime logs, envelopes,
progress) that is hidden from the dispatching agent.

Schema identity travels in the receipt: ``result_model`` is the fully
qualified name of the concrete ``T`` so consumers validate the CONCRETE
result type, never just the envelope structure. Every skill command declares
its concrete result model and the CLI validates against it before printing.

This is distinct from the legacy
:class:`~omnibase_core.models.skill.model_skill_result_file.ModelSkillResultFile`
(the ``skill-results/`` file contract from OMN-3867), which models a different
surface and is unrelated to receipt-mode dispatch.

See ``docs/plans/2026-06-12-skill-output-suppression-plan.md`` (Phase 0,
items 2-3) and epic OMN-13089.

.. versionadded:: OMN-13091
"""

from __future__ import annotations

import re
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_skill_result_status import EnumSkillResultStatus
from omnibase_core.models.artifacts.model_artifact_ref import ModelArtifactRef
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["SKILL_RESULT_SCHEMA_VERSION", "ModelSkillResult"]

T = TypeVar("T")

# Current schema version for skill dispatch receipts. The hook backstop
# (Layer C) sniffs this field to pass receipt-mode output through untouched.
SKILL_RESULT_SCHEMA_VERSION = ModelSemVer(major=1, minor=0, patch=0)

# Fully qualified dotted path: at least one dot, each segment a valid
# Python identifier (e.g. "omnimarket.models.ModelDelegateSkillResponse").
_RESULT_MODEL_FQN_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$"
)


class ModelSkillResult(BaseModel, Generic[T]):
    """Typed result envelope for one skill dispatch.

    Exactly one of these is printed to stdout per receipt-mode dispatch.
    The ``result`` field carries the skill's full typed result — the result
    is the result; intermediate context is captured behind ``artifact_refs``
    instead of flooding the dispatching agent.

    Example:
        >>> from uuid import uuid4
        >>> envelope = ModelSkillResult[dict[str, str]](
        ...     skill_name="delegate",
        ...     node_name="node_delegate_skill_orchestrator",
        ...     status=EnumSkillResultStatus.SUCCESS,
        ...     correlation_id=uuid4(),
        ...     run_id=uuid4(),
        ...     exit_code=0,
        ...     duration_ms=1250,
        ...     result={"answer": "42"},
        ...     result_model="builtins.dict",
        ... )
        >>> envelope.status.is_success_like
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    skill_name: str = Field(
        ...,
        min_length=1,
        description="Name of the dispatched skill (e.g. 'delegate').",
    )
    node_name: str = Field(
        ...,
        min_length=1,
        description="Name of the backing node the skill dispatched to.",
    )
    status: EnumSkillResultStatus = Field(
        ...,
        description="Canonical execution outcome of the dispatch.",
    )
    correlation_id: UUID = Field(
        ...,
        description="Correlation ID propagated from the dispatch envelope.",
    )
    run_id: UUID = Field(
        ...,
        description="Unique ID for this skill run.",
    )
    exit_code: int = Field(
        ...,
        description=(
            "Process exit code of the dispatch. 0 on success; negative "
            "values indicate signal termination (subprocess convention)."
        ),
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Wall-clock duration of the dispatch in milliseconds.",
    )
    result: T = Field(
        ...,
        description=(
            "The skill's FULL typed result. No size limits, no truncation — "
            "the result is the result. On failure this carries the full "
            "error output inline (errors are never hidden)."
        ),
    )
    result_model: str = Field(
        ...,
        description=(
            "Fully qualified name of the concrete result type T (e.g. "
            "'omnimarket.models.ModelDelegateSkillResponse'). Schema "
            "identity travels in the receipt so consumers validate the "
            "concrete type, never just the envelope structure."
        ),
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Dispatch-level metrics (e.g. token counts, retries).",
    )
    artifact_refs: list[ModelArtifactRef] = Field(
        default_factory=list,
        description=(
            "Content-addressed handles for captured intermediate context "
            "(runtime logs, full handler result, envelopes). Retrievable "
            "and hash-verified via the artifact store."
        ),
    )
    schema_version: ModelSemVer = Field(
        default_factory=lambda: SKILL_RESULT_SCHEMA_VERSION,
        description="Receipt schema version for format evolution.",
    )

    @field_validator("result_model")
    @classmethod
    def _validate_result_model_fqn(cls, value: str) -> str:
        if not _RESULT_MODEL_FQN_RE.match(value):
            msg = (
                "result_model must be a fully qualified dotted name "
                f"(e.g. 'pkg.module.ModelName'), got: {value!r}"
            )
            raise ValueError(msg)
        return value
