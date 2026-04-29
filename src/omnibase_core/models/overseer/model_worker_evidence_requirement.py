# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelWorkerEvidenceRequirement — evidence requirement for worker contracts (OMN-10251).

Renamed from OCC's ModelEvidenceRequirement to avoid collision with
omnibase_core.models.ticket.model_evidence_requirement.ModelEvidenceRequirement.
The two are structurally distinct:
- ModelWorkerEvidenceRequirement: evidence_id, description, kind (Literal), pattern
- ModelEvidenceRequirement: kind (EnumEvidenceKind), description, command
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    reason=(
        "evidence_id is a named evidence slot identifier (e.g., 'pr-merged'), "
        "not a system UUID. Matcher reads named slots from TaskUpdate body."
    )
)
class ModelWorkerEvidenceRequirement(BaseModel):
    """A single piece of evidence required on a task-status transition.

    The matcher reads the TaskUpdate body and tests each requirement against it.
    ``kind`` chooses the comparison:

    - ``contains``: ``pattern`` is a substring the body must contain (case-sensitive).
    - ``regex``: ``pattern`` is a regular expression matched against the body.
    - ``fenced_block``: the body must contain a fenced code block whose language tag
      matches ``pattern`` (e.g. ``pattern="json"``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str  # string-id-ok: named evidence slot identifier, not a UUID
    description: str
    kind: Literal["contains", "regex", "fenced_block"]
    pattern: str


__all__ = ["ModelWorkerEvidenceRequirement"]
