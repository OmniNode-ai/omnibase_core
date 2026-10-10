# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One lane's declared projection-readback DSN reference (OMN-18060).

Holds a NAME and never a value. There is deliberately no field on this model
that a DSN could be assigned to: what the lane overlay declares is *where to
look*, and the looking happens in the node against ``os.environ``.

Why a reference rather than the thing itself: ``config/ci_bus_lanes.yaml`` in
omnimarket is committed, diffable, CODEOWNERS-reviewed config -- which is
exactly what made it the right home for the broker and the transport
(OMN-14800, OMN-18012), and exactly what makes it the wrong home for a
credential. Declaring the NAME keeps the reviewable half reviewable and leaves
the secret half in the lab store, where a reader can check that the two agree
without either of them carrying the value.

``lane_transport.load_lane_projection_readback`` is the only thing that builds
one, and it refuses a ``dsn_env`` that parses as a connection string.

WHY THIS FILE SITS BESIDE ``lane_transport.py`` AND NOT UNDER ``models/``
------------------------------------------------------------------------
``models/__init__.py`` imports ``model_chain_canary_request``, which imports
``lane_transport`` for its refusal predicates. A lane model under ``models/``
would therefore make ``lane_transport`` import a package whose ``__init__``
imports ``lane_transport`` -- a genuine import cycle, not a style question.
``ModelLaneTransport`` lives in ``lane_transport.py`` for the same reason;
this is its sibling, split out only because one file may declare one model.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelLaneProjectionReadback(BaseModel):
    """A lane id and the NAME of the variable its projection DSN arrives in."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    lane: str = Field(description="Lane id this readback was declared under")
    dsn_env: str = Field(
        description="NAME of the environment variable carrying the DSN, never the DSN"
    )


__all__ = ["ModelLaneProjectionReadback"]
