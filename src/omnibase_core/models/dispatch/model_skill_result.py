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

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_skill_result_status import EnumSkillResultStatus
from omnibase_core.models.artifacts.model_artifact_ref import ModelArtifactRef
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_runtime_identity import ModelRuntimeIdentity

__all__ = [
    "RUNTIME_IDENTITY_REQUIRED_FROM",
    "SKILL_RESULT_SCHEMA_VERSION",
    "ModelSkillResult",
]

T = TypeVar("T")

# Current schema version for skill dispatch receipts. The hook backstop
# (Layer C) sniffs this field to pass receipt-mode output through untouched.
#
# 1.0.0 -> 1.1.0 (OMN-17308): ``runtime_identity`` became mandatory. The bump
# is what makes the requirement bite, because ``schema_version`` defaults to
# this constant: every receipt built from now on is a 1.1.0 receipt, and a
# 1.1.0 receipt without an identity fails construction.
SKILL_RESULT_SCHEMA_VERSION = ModelSemVer(major=1, minor=1, patch=0)

# The version at which ``runtime_identity`` became required. Receipts stamped
# below it are GRANDFATHERED -- they predate the requirement and are valid
# without an identity block.
#
# Grandfathering is by schema version rather than by date, path, or an
# allowlist, for one reason: it keeps the historical record honest. Back-filling
# an identity onto a 2026-08 receipt would manufacture a claim about a process
# nobody observed -- the exact fiction epic OMN-17306 exists to stop. "This
# receipt predates the requirement" is a true statement the receipt can make
# about itself, and the version field is how it makes it.
RUNTIME_IDENTITY_REQUIRED_FROM = ModelSemVer(major=1, minor=1, patch=0)

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

    Every receipt built at the current schema version carries a
    ``runtime_identity`` naming the process that produced it. Collect one with
    ``omnibase_infra.runtime_identity.collect_runtime_identity()``; it is built
    by hand here only to keep the example self-contained.

    Example:
        >>> from datetime import datetime, timezone
        >>> from uuid import uuid4
        >>> from omnibase_core.enums.enum_execution_locus_kind import (
        ...     EnumExecutionLocusKind,
        ... )
        >>> from omnibase_core.enums.enum_package_source_kind import (
        ...     EnumPackageSourceKind,
        ... )
        >>> from omnibase_core.models.runtime.model_package_identity import (
        ...     ModelPackageIdentity,
        ... )
        >>> from omnibase_core.models.runtime.model_runtime_identity import (
        ...     ModelRuntimeIdentity,
        ... )
        >>> identity = ModelRuntimeIdentity(
        ...     host="omninode-runtime",
        ...     locus_kind=EnumExecutionLocusKind.CONTAINER,
        ...     execution_locus="c0ffee123456",  # pragma: allowlist secret
        ...     interpreter="/app/.venv/bin/python",
        ...     packages={
        ...         "omnimarket": ModelPackageIdentity(
        ...             name="omnimarket",
        ...             version="0.4.13",
        ...             commit="2f123b4c01ea" + "0" * 28,  # pragma: allowlist secret
        ...             source=EnumPackageSourceKind.VCS,
        ...         )
        ...     },
        ...     stamped_at=datetime(2026, 8, 31, 10, 7, 45, tzinfo=timezone.utc),
        ... )
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
        ...     runtime_identity=identity,
        ... )
        >>> envelope.status.is_success_like
        True
        >>> envelope.runtime_identity.host
        'omninode-runtime'

    A receipt may omit ``runtime_identity`` only by explicitly declaring a
    pre-1.1.0 ``schema_version`` — the grandfathering path, which states
    honestly that the receipt predates the requirement:

        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> legacy = ModelSkillResult[dict[str, str]](
        ...     skill_name="delegate",
        ...     node_name="node_delegate_skill_orchestrator",
        ...     status=EnumSkillResultStatus.SUCCESS,
        ...     correlation_id=uuid4(),
        ...     run_id=uuid4(),
        ...     exit_code=0,
        ...     duration_ms=1250,
        ...     result={"answer": "42"},
        ...     result_model="builtins.dict",
        ...     schema_version=ModelSemVer(major=1, minor=0, patch=0),
        ... )
        >>> legacy.runtime_identity is None
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
    runtime_identity: ModelRuntimeIdentity | None = Field(
        default=None,
        description=(
            "Self-identification of the process that produced this receipt: "
            "per-package version AND commit, host, execution locus (venv path "
            "or container id), interpreter, and resolved config source. "
            "REQUIRED at schema_version >= 1.1.0; None only on grandfathered "
            "pre-1.1.0 receipts. Without it a receipt printed by a stale local "
            "venv is byte-indistinguishable from one printed by a deployed "
            "lane -- the OMN-16932/OMN-17295 defect."
        ),
    )
    schema_version: ModelSemVer = Field(
        default_factory=lambda: SKILL_RESULT_SCHEMA_VERSION,
        description="Receipt schema version for format evolution.",
    )

    @model_validator(mode="after")
    def _require_runtime_identity(self) -> ModelSkillResult[T]:
        """Refuse a current-schema receipt that does not say what produced it.

        This is the enforcement, not a detection: an unstamped receipt at or
        above :data:`RUNTIME_IDENTITY_REQUIRED_FROM` cannot be CONSTRUCTED, so
        there is no code path that emits one and no artifact that carries one.
        A later scanner could only have reported the problem after the
        misleading evidence had already been read.
        """
        if self.runtime_identity is not None:
            return self
        if self.schema_version >= RUNTIME_IDENTITY_REQUIRED_FROM:
            msg = (
                "runtime_identity is required at schema_version "
                f"{self.schema_version} (>= {RUNTIME_IDENTITY_REQUIRED_FROM}). "
                "A receipt that does not identify the process that produced it "
                "is a claim, not evidence: collect one with "
                "omnibase_infra.runtime_identity.collect_runtime_identity(). "
                "Only receipts stamped below "
                f"{RUNTIME_IDENTITY_REQUIRED_FROM} are grandfathered."
            )
            raise ValueError(msg)
        return self

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
