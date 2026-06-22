# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed payload + verdict models for the no-faked-boundary COMPUTE validator (OMN-13497).

These are the envelope ``payload`` (input), one finding, and the ``result``
(verdict) for ``HandlerNoFakedBoundaryCompute``. A scan input rides as a typed
``payload`` on ``ModelEventEnvelope`` — the handler is a pure function over its
envelope payload: it reads the file *content text* and never touches the
filesystem. The trio is co-located as the scan I/O contract (mirrors the sibling
``validation/private_ip/models.py``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelNoFakedBoundaryFinding",
    "ModelNoFakedBoundaryScanInput",
    "ModelNoFakedBoundaryScanResult",
]


class ModelNoFakedBoundaryScanInput(BaseModel):
    """One unit of source text to scan for fakes of an inference/routing/dispatch boundary.

    ``content`` is the raw file text; ``path`` is the file's path used only to
    label findings (the EFFECT boundary has already loaded ``content``). ``path``
    is a plain label string, not a filesystem handle.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    content: str = Field(description="Raw source text to scan")
    path: str = Field(
        default="<input>",
        description="Label for the source (e.g. file path) used in findings",
    )


class ModelNoFakedBoundaryFinding(BaseModel):
    """A single faked-boundary violation found in the scanned text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the source the violation was found in")
    line: int = Field(ge=1, description="1-based line number of the violation")
    pattern: str = Field(
        description="Which fake-boundary pattern matched (class/patch/mock/echo)"
    )
    matched_text: str = Field(description="The stripped source line that matched")


class ModelNoFakedBoundaryScanResult(BaseModel):
    """COMPUTE verdict: the findings for one scanned input.

    ``flagged`` is the boolean gate verdict (``True`` iff any finding). Carried
    explicitly so the runner and the corpus gate read one authoritative field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the scanned source")
    flagged: bool = Field(description="True iff one or more violations were found")
    findings: tuple[ModelNoFakedBoundaryFinding, ...] = Field(
        default=(), description="All violations found in the scanned text"
    )
