# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed payload + verdict models for the doc-content COMPUTE validator (OMN-13569).

These are the envelope ``payload`` (input) and ``result`` (verdict) for
``HandlerDocContentScanCompute``. A scan input rides as a typed ``payload`` on
``ModelEventEnvelope`` — the handler is a pure function over its envelope payload
(§1A): it reads the documentation file *content text* (and the path *label*, used
only for the path-based exemptions) and never touches the filesystem.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper

__all__ = [
    "EnumDocViolationType",
    "ModelDocContentFinding",
    "ModelDocContentScanInput",
    "ModelDocContentScanResult",
]


class EnumDocViolationType(UtilStrValueHelper, str, Enum):
    """The kind of doc-content violation a finding reports.

    External contract surface (carried on a typed result), so an enum, not a bare
    string (CLAUDE.md Enum vs Literal policy).
    """

    LAN_IP = "lan_ip"
    HOST_SHORTHAND = "host_shorthand"
    PERSONAL_PATH = "personal_path"
    SSH_INVOCATION = "ssh_invocation"
    PERSONAL_EMAIL = "personal_email"
    TICKET_REFERENCE = "ticket_reference"


class ModelDocContentScanInput(BaseModel):
    """One documentation file to scan for local-environment traces + ticket refs.

    ``content`` is the raw file text; ``path`` is the file's path. ``path`` is used
    for two pure decisions only — selecting the docs-only glob is the EFFECT
    boundary's job, but the path also drives the ``OMN-<digits>`` exemptions
    (files under ``onex_change_control/`` or ``contracts/`` keep ticket refs) — and
    to label findings. It is a plain label string, not a filesystem handle; the
    handler never opens it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    content: str = Field(description="Raw documentation source text to scan")
    path: str = Field(
        default="<input>",
        description=(
            "Label for the source (e.g. file path) used in findings AND for the "
            "OMN-<digits> path exemptions (onex_change_control/ and contracts/)"
        ),
    )


class ModelDocContentFinding(BaseModel):
    """A single doc-content violation found in the scanned text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the source the violation was found in")
    line: int = Field(ge=1, description="1-based line number of the violation")
    column: int = Field(ge=1, description="1-based column of the matched text")
    violation_type: EnumDocViolationType = Field(
        description="Which class of doc-content violation this finding reports"
    )
    matched_text: str = Field(description="The exact text that matched")
    context: str = Field(description="The full source line (stripped), for triage")


class ModelDocContentScanResult(BaseModel):
    """COMPUTE verdict: the findings for one scanned documentation file.

    ``flagged`` is the boolean gate verdict (``True`` iff any finding). Carried
    explicitly so the runner and the corpus gate read one authoritative field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Label of the scanned source")
    flagged: bool = Field(description="True iff one or more violations were found")
    findings: tuple[ModelDocContentFinding, ...] = Field(
        default=(), description="All violations found in the scanned text"
    )
