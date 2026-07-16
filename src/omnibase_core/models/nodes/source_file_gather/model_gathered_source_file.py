# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A single eligible file gathered by the source_file_gather EFFECT node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelGatheredSourceFile"]


class ModelGatheredSourceFile(BaseModel):
    """An eligible file discovered under ``root``, with its content inline.

    The file content is carried on the model (rather than only the path) so
    that a paired COMPUTE node can consume it without performing its own
    filesystem I/O.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-path-ok: filesystem path to the gathered file, not a UUID
    path: str
    size_bytes: int
    source: str
