# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Event-bus settings declared in ``~/.onex/config.yaml``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCliUserConfigKafka(BaseModel):
    """Event-bus connection settings."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        from_attributes=True,
        frozen=True,
    )

    bootstrap_servers: str = Field(
        default="localhost:19092",  # fallback-ok: scaffolded placeholder for a user-editable config template, not runtime endpoint resolution
        description="Kafka/Redpanda bootstrap servers",
    )


__all__ = ["ModelCliUserConfigKafka"]
