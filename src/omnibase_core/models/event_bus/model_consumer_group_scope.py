# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Declared scope discriminators for a derived consumer group ID.

A consumer group's *identity* (env / service / node / purpose / version) says which
logical consumer it is. Its *scope* says which slice of that consumer it is: a single
process instance, a single one-shot correlation, or a single topic. Before OMN-15639
each of those slices was expressed by hand-writing a group-name string literal at the
call site (``f"runtime-local-{handler}"``, ``f"onex-run-node-{correlation_id}"``), which
is exactly how names outside the MSK IAM authorized pattern set got minted.

This model makes the scope a declared, typed input to the canonical derivation instead.

.. versionadded:: OMN-15639
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelConsumerGroupScope(BaseModel):
    """Optional discriminators applied on top of an identity-derived group ID.

    All fields are optional; an all-empty scope is meaningful and means "the shared,
    undiscriminated group for this identity". Rendering rules live in
    :mod:`omnibase_core.event_bus.util_consumer_group`:

    - ``topic`` is applied as a ``.__t.<topic>`` infix (topic-scoped subscription).
    - ``ephemeral_tag`` / ``correlation_id`` / ``instance_token`` collapse into a single
      ``.__i.<discriminator>`` infix, joined with ``-`` in declaration order.

    Both infixes preserve the leading environment token, so a scoped name stays inside
    whichever IAM pattern authorized the unscoped one.

    Attributes:
        ephemeral_tag: Short human-readable tag for a short-lived group
            (e.g. ``"terminal"``).
        correlation_id: Correlation UUID for a one-shot request/response consumer.
        instance_token: Container/pod instance discriminator, typically the value of
            ``KAFKA_INSTANCE_ID``. Named ``_token`` rather than ``_id`` because it is an
            opaque string (pod name, container id), not a UUID.
        topic: Topic name when the group is scoped to a single topic.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ephemeral_tag: str | None = Field(
        default=None,
        description="Short tag identifying a short-lived consumer (e.g. 'terminal').",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation UUID for a one-shot request/response consumer.",
    )
    instance_token: str | None = Field(
        default=None,
        description="Container/pod instance discriminator (e.g. KAFKA_INSTANCE_ID).",
    )
    topic: str | None = Field(
        default=None,
        description="Topic name when the consumer group is scoped to one topic.",
    )

    def discriminator_tokens(self) -> tuple[str, ...]:
        """Return the non-empty instance-discriminator tokens in declaration order.

        ``topic`` is deliberately excluded: it is rendered through a different infix
        (``.__t.``) so that topic scoping and instance scoping stay distinguishable in
        broker-side tooling.

        Example:
            >>> from uuid import UUID
            >>> ModelConsumerGroupScope(
            ...     ephemeral_tag="terminal",
            ...     correlation_id=UUID("9f2c0000-0000-4000-8000-000000000000"),
            ... ).discriminator_tokens()
            ('terminal', '9f2c0000-0000-4000-8000-000000000000')
        """
        tokens: list[str] = []
        for candidate in (
            self.ephemeral_tag,
            str(self.correlation_id) if self.correlation_id is not None else None,
            self.instance_token,
        ):
            if candidate is not None and candidate.strip():
                tokens.append(candidate.strip())
        return tuple(tokens)

    def is_empty(self) -> bool:
        """Return True when the scope carries no discriminator at all.

        Example:
            >>> ModelConsumerGroupScope().is_empty()
            True
            >>> ModelConsumerGroupScope(topic="example.evt.foo.v1").is_empty()
            False
        """
        return not self.discriminator_tokens() and not (
            self.topic is not None and self.topic.strip()
        )


__all__ = ["ModelConsumerGroupScope"]
