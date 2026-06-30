# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed payload + verdict models for the localhost-URL COMPUTE validator (OMN-13480).

These are the envelope ``payload`` (input) and ``result`` (verdict) for
``HandlerLocalhostUrlCompute``. A scan input rides as a typed ``payload`` on
``ModelEventEnvelope`` — the handler is a pure function over its envelope payload
(§1A): it reads the file *content text* and never touches the filesystem.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelLocalhostUrlFinding",
    "ModelLocalhostUrlScanInput",
    "ModelLocalhostUrlScanResult",
]


class ModelLocalhostUrlScanInput(BaseModel):
    """One unit of source text to scan for hardcoded localhost/loopback URL literals.

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


class ModelLocalhostUrlFinding(BaseModel):
    """A single hardcoded localhost/loopback URL violation found in the scanned text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the source the violation was found in")
    line: int = Field(ge=1, description="1-based line number of the violation")
    column: int = Field(ge=1, description="1-based column of the matched URL literal")
    matched_url: str = Field(
        description="The exact http(s)://localhost|127.0.0.1 URL literal that matched"
    )
    host: str = Field(description="The loopback host matched (localhost or 127.0.0.1)")
    context: str = Field(description="The full source line (stripped), for triage")


class ModelLocalhostUrlScanResult(BaseModel):
    """COMPUTE verdict: the findings for one scanned input.

    ``flagged`` is the boolean gate verdict (``True`` iff any finding). Carried
    explicitly so the runner and the corpus gate read one authoritative field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the scanned source")
    flagged: bool = Field(description="True iff one or more violations were found")
    findings: tuple[ModelLocalhostUrlFinding, ...] = Field(
        default=(), description="All violations found in the scanned text"
    )
