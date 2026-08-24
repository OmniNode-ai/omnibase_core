# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Work-event claimant union (OMN-16177).

``ModelActor`` is a discriminated union, not a session handle with node fields
bolted on. Both variants must be comparable as claimants — the claims reduction
treats them uniformly, so a node holding a claim and a session holding a claim
are the same kind of fact.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from omnibase_core.models.events.work.model_node_actor import ModelNodeActor
from omnibase_core.models.events.work.model_session_actor import ModelSessionActor

__all__ = ["ModelActor"]

ModelActor = Annotated[
    ModelSessionActor | ModelNodeActor,
    Field(discriminator="kind"),
]
