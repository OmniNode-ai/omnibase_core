# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed payload + verdict models for the private-IP COMPUTE validator (OMN-13294).

These are the envelope ``payload`` (input) and ``result`` (verdict) for
``HandlerPrivateIpCompute``. A scan input rides as a typed ``payload`` on
``ModelEventEnvelope`` — the handler is a pure function over its envelope payload
(§1A): it reads the file *content text* and never touches the filesystem.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelPrivateIpFinding",
    "ModelPrivateIpScanInput",
    "ModelPrivateIpScanResult",
]


class ModelPrivateIpScanInput(BaseModel):
    """One unit of source text to scan for hardcoded RFC1918 private-IP literals.

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


class ModelPrivateIpFinding(BaseModel):
    """A single hardcoded private-IP violation found in the scanned text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the source the violation was found in")
    line: int = Field(ge=1, description="1-based line number of the violation")
    column: int = Field(ge=1, description="1-based column of the matched IP literal")
    matched_text: str = Field(description="The exact RFC1918 IPv4 literal that matched")
    rfc1918_block: str = Field(
        description="Which private block the IP falls in (10/8, 172.16/12, 192.168/16)"
    )
    context: str = Field(description="The full source line (stripped), for triage")


class ModelPrivateIpScanResult(BaseModel):
    """COMPUTE verdict: the findings for one scanned input.

    ``flagged`` is the boolean gate verdict (``True`` iff any finding). Carried
    explicitly so the runner and the corpus gate read one authoritative field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the scanned source")
    flagged: bool = Field(description="True iff one or more violations were found")
    findings: tuple[ModelPrivateIpFinding, ...] = Field(
        default=(), description="All violations found in the scanned text"
    )
