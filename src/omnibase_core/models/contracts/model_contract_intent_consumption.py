# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract-declared intent consumption block.

Schema for the top-level ``intent_consumption:`` section of a node
``contract.yaml``. The intent routing loader reads ``intent_routing_table``
to decide which effect node executes each intent type an orchestrator emits.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractIntentConsumption(BaseModel):
    """Intent-to-effect routing declared in a contract YAML ``intent_consumption:`` block."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    intent_routing_table: dict[str, str] = Field(
        ...,
        min_length=1,
        description="Map of intent_type (e.g. 'postgres.upsert_registration') to the "
        "effect node name that executes it.",
    )
