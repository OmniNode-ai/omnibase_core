# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aggregated topic relationships across demo-path contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from omnibase_core.models.validation.model_demo_path_contract import (
    ModelDemoPathContract,
)


@dataclass
class DemoPathTopicRegistry:
    """Aggregated topic view across all demo-path contracts."""

    producers: dict[str, set[str]] = field(default_factory=dict)
    consumers: dict[str, set[str]] = field(default_factory=dict)
    widget_topics: set[str] = field(default_factory=set)

    @classmethod
    def from_contracts(
        cls, contracts: list[ModelDemoPathContract]
    ) -> DemoPathTopicRegistry:
        registry = cls()
        for contract in contracts:
            for topic in contract.publish_topics:
                registry.producers.setdefault(topic, set()).add(contract.name)
            for topic in contract.subscribe_topics:
                registry.consumers.setdefault(topic, set()).add(contract.name)
            registry.widget_topics.update(contract.widget_topics)
        return registry

    def find_publish_subscribe_mismatches(self) -> list[str]:
        """Describe published topics without any matching subscriber."""
        mismatches: list[str] = []
        for topic, publishers in sorted(self.producers.items()):
            if topic not in self.consumers:
                mismatches.append(
                    f"topic {topic!r} published by {sorted(publishers)} "
                    "but no demo-path consumer subscribes to it (byte mismatch or orphan)"
                )
        return mismatches

    def find_orphan_producers(self) -> list[str]:
        """Describe topics that are published but never consumed."""
        orphans: list[str] = []
        for topic, publishers in sorted(self.producers.items()):
            if topic not in self.consumers:
                orphans.append(
                    f"orphan producer: topic {topic!r} published by "
                    f"{sorted(publishers)} but has no demo-path subscriber"
                )
        return orphans

    def find_orphan_consumers(self) -> list[str]:
        """Describe topics that are subscribed to but never produced."""
        orphans: list[str] = []
        for topic, subscribers in sorted(self.consumers.items()):
            if topic not in self.producers:
                orphans.append(
                    f"orphan consumer: topic {topic!r} subscribed by "
                    f"{sorted(subscribers)} but has no demo-path producer"
                )
        return orphans

    def find_widget_topics_without_producers(self) -> list[str]:
        """Describe widget topics that have no producing node."""
        missing: list[str] = []
        for topic in sorted(self.widget_topics):
            if topic not in self.producers:
                missing.append(
                    f"widget topic {topic!r} has no producing node on the demo path"
                )
        return missing


__all__ = ["DemoPathTopicRegistry"]
