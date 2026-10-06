# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validated hash-only entry used by the exposed identifier matcher."""

from pydantic import BaseModel, ConfigDict


class ModelExposedIdentifierEntry(BaseModel):
    """Diagnostic labels and digest; never contains the matched literal."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    label: str
    kind: str
    length: int
    sha256: str
    ticket: str
