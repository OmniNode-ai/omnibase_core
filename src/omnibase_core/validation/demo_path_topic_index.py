# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aggregated topic index for demo-path contract coherence checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from omnibase_core.validation.demo_path_contract import DemoPathContract


@dataclass
class DemoPathTopicIndex:
    """Aggregated producer, consumer, and widget-topic view."""

    producers: dict[str, set[str]] = field(default_factory=dict)
    consumers: dict[str, set[str]] = field(default_factory=dict)
    widget_topics: set[str] = field(default_factory=set)

    @classmethod
    def from_contracts(cls, contracts: list[DemoPathContract]) -> DemoPathTopicIndex:
        """Build an index without changing any contract or topic ordering semantics."""
        index = cls()
        for contract in contracts:
            for topic in contract.publish_topics:
                index.producers.setdefault(topic, set()).add(contract.name)
            for topic in contract.subscribe_topics:
                index.consumers.setdefault(topic, set()).add(contract.name)
            index.widget_topics.update(contract.widget_topics)
        return index

    def find_publish_subscribe_mismatches(self) -> list[str]:
        """Return published topics that have no exact subscriber."""
        return [
            (
                f"topic {topic!r} published by {sorted(publishers)} "
                "but no demo-path consumer subscribes to it (byte mismatch or orphan)"
            )
            for topic, publishers in sorted(self.producers.items())
            if topic not in self.consumers
        ]

    def find_orphan_producers(self) -> list[str]:
        """Return published topics that are never consumed."""
        return [
            (
                f"orphan producer: topic {topic!r} published by "
                f"{sorted(publishers)} but has no demo-path subscriber"
            )
            for topic, publishers in sorted(self.producers.items())
            if topic not in self.consumers
        ]

    def find_orphan_consumers(self) -> list[str]:
        """Return subscribed topics that are never produced."""
        return [
            (
                f"orphan consumer: topic {topic!r} subscribed by "
                f"{sorted(subscribers)} but has no demo-path producer"
            )
            for topic, subscribers in sorted(self.consumers.items())
            if topic not in self.producers
        ]

    def find_widget_topics_without_producers(self) -> list[str]:
        """Return widget topics that have no producing node."""
        return [
            f"widget topic {topic!r} has no producing node on the demo path"
            for topic in sorted(self.widget_topics)
            if topic not in self.producers
        ]


__all__ = ["DemoPathTopicIndex"]
