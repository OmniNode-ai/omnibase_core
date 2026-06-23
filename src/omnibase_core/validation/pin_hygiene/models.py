# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed payload + verdict models for the sibling-pin-hygiene COMPUTE validator (OMN-13509).

These are the envelope ``payload`` (input), one finding, and the ``result``
(verdict) for ``HandlerPinHygieneCompute``. A scan input rides as a typed
``payload`` on ``ModelEventEnvelope`` — the handler is a pure function over its
envelope payload: it reads the dependency-pin *content text* (each sibling git
pin already annotated by the EFFECT runner with its resolved git ancestry) and
never touches the filesystem or runs git. The trio is co-located as the scan I/O
contract (mirrors the sibling ``validation/private_ip/models.py`` /
``validation/no_faked_boundary/models.py``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelPinHygieneFinding",
    "ModelPinHygieneScanInput",
    "ModelPinHygieneScanResult",
]


class ModelPinHygieneScanInput(BaseModel):
    """One unit of dependency-pin source text to scan for non-ancestor sibling pins.

    ``content`` is the raw pin text (a ``pyproject.toml`` / ``uv.lock`` slice) in
    which the EFFECT runner has already annotated each sibling git pin with its
    resolved git ancestry (``# pin-ancestry: ancestor|orphan|unknown``). ``path``
    is the file's path used only to label findings — the EFFECT boundary has
    already loaded ``content`` and resolved the git facts. ``path`` is a plain
    label string, not a filesystem handle.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    content: str = Field(description="Raw dependency-pin source text to scan")
    path: str = Field(
        default="<input>",
        description="Label for the source (e.g. file path) used in findings",
    )


class ModelPinHygieneFinding(BaseModel):
    """A single non-ancestor sibling-pin violation found in the scanned text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the source the violation was found in")
    line: int = Field(ge=1, description="1-based line number of the violation")
    sibling: str = Field(description="Which sibling distribution the pin names")
    pin_type: str = Field(
        description="Pin syntax: rev / pep-508 / uv-lock-rev / branch"
    )
    verdict: str = Field(
        description="Resolved ancestry verdict that failed the gate: orphan / unknown"
    )
    matched_text: str = Field(description="The stripped source line that matched")


class ModelPinHygieneScanResult(BaseModel):
    """COMPUTE verdict: the findings for one scanned input.

    ``flagged`` is the boolean gate verdict (``True`` iff any finding). Carried
    explicitly so the runner and the corpus gate read one authoritative field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the scanned source")
    flagged: bool = Field(description="True iff one or more violations were found")
    findings: tuple[ModelPinHygieneFinding, ...] = Field(
        default=(), description="All violations found in the scanned text"
    )
