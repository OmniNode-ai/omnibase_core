# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structured view of a parsed canonical ONEX topic name (OMN-12621).

A canonical ONEX topic has the form
``onex.<kind>.<service>.<event>[.<event>...].v<N>``. :class:`ModelCanonicalTopic`
is the structured decomposition of that name and exposes an :attr:`identity`
that ignores the ``.vN`` segment, so two versions of the same logical stream
share an identity while a namespace rename does not.

This is distinct from ``omnibase_core.models.dispatch.model_parsed_topic`` —
that model describes routing-standard detection for arbitrary topic strings;
this one is the strict canonical-topic decomposition used by the topic-migration
contract machinery.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCanonicalTopic(BaseModel):
    """Structured view of a parsed canonical ONEX topic name."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    namespace: str = Field(..., description="Top-level namespace, always 'onex'")
    kind: str = Field(
        ..., description="Topic kind: cmd | evt | dlq | snapshot | intent"
    )
    service: str = Field(..., description="Producing service segment")
    event: str = Field(..., description="Dotted event name segment(s)")
    topic_major: int = Field(..., ge=1, description="Topic .vN version segment")

    @property
    def identity(self) -> tuple[str, str, str, str]:
        """Namespace/kind/service/event identity, ignoring the .vN segment.

        Two topics with the same identity but different ``topic_major`` are the
        same logical stream at different versions; a different identity is a
        namespace rename (the OMN-12407 case).
        """
        return (self.namespace, self.kind, self.service, self.event)


__all__ = ["ModelCanonicalTopic"]
