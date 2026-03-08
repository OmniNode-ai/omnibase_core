# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Pipeline State model for ticket-pipeline execution.

Represents the persistent state of a ``ticket-pipeline`` execution, written to
``~/.claude/pipelines/{ticket_id}/state.yaml``. Read by ``ticket-pipeline``
(resume) and ``crash-recovery`` (diagnostics).

**Mutability:** This model is mutable -- phase transitions update the model
during execution. ``ModelPhaseRecord`` (phase history entries) is frozen.

**Write safety:** Producers MUST use atomic write (temp file + ``os.rename()``)
to prevent consumers from reading partial files. Follow the pattern in
``_lib/run-state/helpers.md``. Consumers SHOULD retry once on
``yaml.YAMLError`` (transient partial-read during atomic rename window).

**Extra fields:** Uses ``extra="allow"`` because pipeline state files may
contain fields from newer or older schema versions. This is intentional
for forward/backward schema evolution -- not a compatibility shim.

.. versionadded:: 0.7.0
    Added as part of OMN-3870 to replace ad-hoc YAML schemas in
    ticket-pipeline and crash-recovery with a formal Pydantic model.
"""

from __future__ import annotations

from datetime import UTC, datetime

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_pipeline_phase import EnumPipelinePhase
from omnibase_core.models.pipeline.model_phase_record import ModelPhaseRecord

__all__ = ["ModelPipelineState", "PipelineState"]


class ModelPipelineState(BaseModel):
    """State of a ticket-pipeline execution.

    Written to ``~/.claude/pipelines/{ticket_id}/state.yaml``.
    Read by ticket-pipeline (resume) and crash-recovery (diagnostics).

    **Mutability:** Phase transitions update this model during execution.
    Callers must use atomic write (temp-then-rename) for persistence.

    **Extra fields:** Uses ``extra="allow"`` because pipeline state files may
    contain fields from newer or older schema versions. This is intentional
    for forward/backward schema evolution -- not a shim.

    **Write safety:** Producers MUST use atomic write (temp file +
    ``os.rename()``) to prevent consumers from reading partial files. Follow
    the pattern in ``_lib/run-state/helpers.md``. Consumers SHOULD retry once
    on ``yaml.YAMLError`` (transient partial-read during atomic rename window).
    """

    model_config = ConfigDict(
        extra="allow",  # Schema evolution: newer/older state files may have different fields
        from_attributes=True,
    )

    # Required fields
    # string-id-ok: Linear ticket IDs are string-typed (e.g. OMN-3795), not UUIDs
    ticket_id: str = Field(..., min_length=1)
    """Linear ticket ID (e.g., ``OMN-3795``)."""

    current_phase: EnumPipelinePhase
    """The current pipeline phase."""

    branch_name: str = Field(..., min_length=1)
    """Git branch name for this ticket's work."""

    title: str = Field(..., min_length=1)
    """Human-readable title for the ticket."""

    # Phase history
    phase_history: list[ModelPhaseRecord] = Field(default_factory=list)
    """Ordered list of completed phase records."""

    # Optional context
    # string-id-ok: opaque pipeline correlation ID, not a DB primary key
    run_id: str | None = Field(default=None)
    """Pipeline run identifier for correlation."""

    pr_url: str | None = Field(default=None)
    """GitHub PR URL if a PR has been opened."""

    pr_number: int | None = Field(default=None)
    """GitHub PR number if a PR has been opened."""

    repo: str | None = Field(default=None)
    """Repository name (e.g., ``omnibase_core``)."""

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """UTC timestamp when this pipeline state was first created."""

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """UTC timestamp of the last state update."""

    def to_yaml(self) -> str:
        """Serialize to YAML string for file I/O.

        Uses ``mode="json"`` to ensure datetime and enum serialization
        produces clean YAML output.

        Returns:
            YAML string representation of the pipeline state.
        """
        data = self.model_dump(mode="json")
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, data: str) -> ModelPipelineState:
        """Deserialize from YAML string.

        Args:
            data: YAML string to parse.

        Returns:
            ModelPipelineState instance.

        Raises:
            ValueError: If YAML parsing or validation fails.
        """
        parsed = yaml.safe_load(data)
        return cls.model_validate(parsed)


# Alias for convenience
PipelineState = ModelPipelineState
