# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ValidatorDemoPathTopicCoherence (OMN-12777).

TDD: these tests are written BEFORE the implementation to define the
contract for the demo-path topic coherence gate.

The gate asserts (fail on any):
  (a) no hand-authored topic literals on the demo path
      (generated artifacts allowed only if derived from the contract registry)
  (b) every demo-path publish_topics byte-matches some consumer subscribe_topics
      (no prefix drift)
  (c) no orphan producer/consumer on the demo path
  (d) every demo-visible widget topic has a producing node

Demo-path contracts are identified by a ``demo_path: true`` marker in their
contract.yaml metadata section. The validator scans contract files in a
configured set of repo roots.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.validator_demo_path_topic_coherence import (
    RULE_HAND_AUTHORED_LITERAL,
    RULE_ORPHAN_CONSUMER,
    RULE_ORPHAN_PRODUCER,
    RULE_PUBLISH_SUBSCRIBE_MISMATCH,
    RULE_WIDGET_TOPIC_NO_PRODUCER,
    DemoPathTopicRegistry,
    ValidatorDemoPathTopicCoherence,
    load_demo_path_contracts,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_contract(tmp_path: Path, subdir: str, content: dict) -> Path:  # type: ignore[type-arg]
    """Write a contract.yaml at tmp_path / subdir / contract.yaml."""
    node_dir = tmp_path / subdir
    node_dir.mkdir(parents=True, exist_ok=True)
    contract_path = node_dir / "contract.yaml"
    contract_path.write_text(yaml.dump(content))
    return contract_path


def _write_python(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content))
    return p


def _minimal_contract(
    *,
    subscribe: list[str] | None = None,
    publish: list[str] | None = None,
    widget_topics: list[str] | None = None,
    demo_path: bool = True,
) -> dict:  # type: ignore[type-arg]
    """Build a minimal valid contract dict for testing."""
    contract: dict = {  # type: ignore[type-arg]
        "name": "node_test_effect",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "node_type": "effect",
        "node_version": {"major": 1, "minor": 0, "patch": 0},
        "metadata": {"demo_path": demo_path},
        "event_bus": {},
    }
    if subscribe:
        contract["event_bus"]["subscribe_topics"] = subscribe
    if publish:
        contract["event_bus"]["publish_topics"] = publish
    if widget_topics:
        contract["metadata"]["widget_topics"] = widget_topics
    return contract


# ---------------------------------------------------------------------------
# load_demo_path_contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadDemoPathContracts:
    def test_loads_contracts_with_demo_path_true(self, tmp_path: Path) -> None:
        _write_contract(
            tmp_path,
            "node_a",
            _minimal_contract(
                subscribe=["onex.cmd.omnimarket.node-generation-requested.v1"]
            ),
        )
        _write_contract(
            tmp_path,
            "node_b",
            _minimal_contract(
                demo_path=False, subscribe=["onex.cmd.omnimarket.other.v1"]
            ),
        )

        contracts = load_demo_path_contracts([tmp_path])
        assert len(contracts) == 1
        assert "node_a" in contracts[0].name

    def test_returns_empty_when_no_demo_path_contracts(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "node_a", _minimal_contract(demo_path=False))
        contracts = load_demo_path_contracts([tmp_path])
        assert contracts == []

    def test_scans_multiple_repo_roots(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo_a"
        repo_b = tmp_path / "repo_b"
        _write_contract(repo_a, "node_a", _minimal_contract())
        _write_contract(repo_b, "node_b", _minimal_contract())

        contracts = load_demo_path_contracts([repo_a, repo_b])
        assert len(contracts) == 2


# ---------------------------------------------------------------------------
# DemoPathTopicRegistry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDemoPathTopicRegistry:
    def test_publish_subscribe_match_succeeds(self, tmp_path: Path) -> None:
        _write_contract(
            tmp_path,
            "producer_node",
            _minimal_contract(
                publish=["onex.evt.omnimarket.node-generation-completed.v1"]
            ),
        )
        _write_contract(
            tmp_path,
            "consumer_node",
            _minimal_contract(
                subscribe=["onex.evt.omnimarket.node-generation-completed.v1"]
            ),
        )

        contracts = load_demo_path_contracts([tmp_path])
        registry = DemoPathTopicRegistry.from_contracts(contracts)

        # Every published topic has a subscriber — no mismatches
        mismatches = registry.find_publish_subscribe_mismatches()
        assert mismatches == []

    def test_publish_subscribe_mismatch_detected(self, tmp_path: Path) -> None:
        """Producer publishes a topic that nobody subscribes to."""
        _write_contract(
            tmp_path,
            "producer_node",
            _minimal_contract(
                publish=["onex.evt.omnimarket.node-generation-completed.v1"]
            ),
        )

        contracts = load_demo_path_contracts([tmp_path])
        registry = DemoPathTopicRegistry.from_contracts(contracts)

        mismatches = registry.find_publish_subscribe_mismatches()
        assert len(mismatches) == 1
        assert "onex.evt.omnimarket.node-generation-completed.v1" in mismatches[0]

    def test_prefix_drift_detected(self, tmp_path: Path) -> None:
        """Producer uses omnibase-infra prefix; consumer expects omnimarket prefix."""
        _write_contract(
            tmp_path,
            "producer_node",
            _minimal_contract(
                publish=["onex.evt.omnibase-infra.delegation-completed.v1"]
            ),
        )
        _write_contract(
            tmp_path,
            "consumer_node",
            # Intentionally wrong prefix — this is the drift we detect
            _minimal_contract(
                subscribe=[
                    "onex.evt.omnimarket.delegation-completed.v1"
                ]  # onex-topic-test-fixture
            ),
        )

        contracts = load_demo_path_contracts([tmp_path])
        registry = DemoPathTopicRegistry.from_contracts(contracts)

        # The infra topic is published but no subscriber uses the same exact string
        mismatches = registry.find_publish_subscribe_mismatches()
        assert len(mismatches) >= 1

    def test_orphan_consumer_detected(self, tmp_path: Path) -> None:
        """Consumer subscribes to a topic that nobody produces."""
        _write_contract(
            tmp_path,
            "consumer_node",
            _minimal_contract(
                subscribe=["onex.cmd.omnimarket.node-generation-requested.v1"]
            ),
        )

        contracts = load_demo_path_contracts([tmp_path])
        registry = DemoPathTopicRegistry.from_contracts(contracts)

        orphans = registry.find_orphan_consumers()
        assert len(orphans) == 1
        assert "onex.cmd.omnimarket.node-generation-requested.v1" in orphans[0]

    def test_orphan_producer_detected(self, tmp_path: Path) -> None:
        """Producer emits a topic that nobody consumes (not in any subscribe_topics)."""
        _write_contract(
            tmp_path,
            "producer_node",
            _minimal_contract(
                publish=["onex.evt.omnimarket.node-generation-completed.v1"]
            ),
        )

        contracts = load_demo_path_contracts([tmp_path])
        registry = DemoPathTopicRegistry.from_contracts(contracts)

        orphans = registry.find_orphan_producers()
        assert len(orphans) == 1
        assert "onex.evt.omnimarket.node-generation-completed.v1" in orphans[0]

    def test_widget_topic_no_producer_detected(self, tmp_path: Path) -> None:
        """A widget_topics entry has no producer in publish_topics."""
        _write_contract(
            tmp_path,
            "dashboard_node",
            _minimal_contract(
                widget_topics=[
                    "onex.snapshot.projection.delegation.correlation-trace.v1"
                ]  # onex-topic-test-fixture
            ),
        )

        contracts = load_demo_path_contracts([tmp_path])
        registry = DemoPathTopicRegistry.from_contracts(contracts)

        missing = registry.find_widget_topics_without_producers()
        assert len(missing) == 1
        assert "onex.snapshot.projection.delegation.correlation-trace.v1" in missing[0]

    def test_widget_topic_with_producer_succeeds(self, tmp_path: Path) -> None:
        """Widget topic is satisfied by a matching publish_topics entry."""
        _write_contract(
            tmp_path,
            "producer_node",
            _minimal_contract(
                publish=[
                    "onex.snapshot.projection.delegation.correlation-trace.v1"
                ],  # onex-topic-test-fixture
                widget_topics=[
                    "onex.snapshot.projection.delegation.correlation-trace.v1"
                ],  # onex-topic-test-fixture
            ),
        )

        contracts = load_demo_path_contracts([tmp_path])
        registry = DemoPathTopicRegistry.from_contracts(contracts)

        missing = registry.find_widget_topics_without_producers()
        assert missing == []

    def test_fully_coherent_demo_path_passes_all(self, tmp_path: Path) -> None:
        """Full chain: producer → consumer, widget topic has producer."""
        _write_contract(
            tmp_path,
            "generation_node",
            _minimal_contract(
                subscribe=["onex.cmd.omnimarket.node-generation-requested.v1"],
                publish=["onex.evt.omnimarket.node-generation-completed.v1"],
            ),
        )
        _write_contract(
            tmp_path,
            "dashboard_node",
            _minimal_contract(
                publish=["onex.cmd.omnimarket.node-generation-requested.v1"],
                subscribe=["onex.evt.omnimarket.node-generation-completed.v1"],
                widget_topics=["onex.evt.omnimarket.node-generation-completed.v1"],
            ),
        )

        contracts = load_demo_path_contracts([tmp_path])
        registry = DemoPathTopicRegistry.from_contracts(contracts)

        assert registry.find_publish_subscribe_mismatches() == []
        assert registry.find_orphan_consumers() == []
        assert registry.find_orphan_producers() == []
        assert registry.find_widget_topics_without_producers() == []


# ---------------------------------------------------------------------------
# ValidatorDemoPathTopicCoherence
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatorDemoPathTopicCoherence:
    def test_clean_path_returns_valid(self, tmp_path: Path) -> None:
        _write_contract(
            tmp_path,
            "producer_node",
            _minimal_contract(
                subscribe=["onex.cmd.omnimarket.node-generation-requested.v1"],
                publish=["onex.evt.omnimarket.node-generation-completed.v1"],
            ),
        )
        _write_contract(
            tmp_path,
            "consumer_node",
            _minimal_contract(
                publish=["onex.cmd.omnimarket.node-generation-requested.v1"],
                subscribe=["onex.evt.omnimarket.node-generation-completed.v1"],
                widget_topics=["onex.evt.omnimarket.node-generation-completed.v1"],
            ),
        )

        validator = ValidatorDemoPathTopicCoherence(repo_roots=[tmp_path])
        result = validator.run()

        assert result.is_valid, f"Expected valid; issues: {result.issues}"

    def test_orphan_consumer_fails_gate(self, tmp_path: Path) -> None:
        _write_contract(
            tmp_path,
            "consumer_node",
            _minimal_contract(
                subscribe=["onex.cmd.omnimarket.node-generation-requested.v1"]
            ),
        )

        validator = ValidatorDemoPathTopicCoherence(repo_roots=[tmp_path])
        result = validator.run()

        assert not result.is_valid
        rule_codes = {i.code for i in result.issues}
        assert RULE_ORPHAN_CONSUMER in rule_codes

    def test_orphan_producer_fails_gate(self, tmp_path: Path) -> None:
        _write_contract(
            tmp_path,
            "producer_node",
            _minimal_contract(
                publish=["onex.evt.omnimarket.node-generation-completed.v1"]
            ),
        )

        validator = ValidatorDemoPathTopicCoherence(repo_roots=[tmp_path])
        result = validator.run()

        assert not result.is_valid
        rule_codes = {i.code for i in result.issues}
        assert RULE_ORPHAN_PRODUCER in rule_codes

    def test_publish_subscribe_mismatch_fails_gate(self, tmp_path: Path) -> None:
        _write_contract(
            tmp_path,
            "producer_node",
            _minimal_contract(
                publish=["onex.evt.omnimarket.node-generation-completed.v1"]
            ),
        )
        _write_contract(
            tmp_path,
            "consumer_node",
            # Subscribes to wrong prefix — drift
            _minimal_contract(
                subscribe=[
                    "onex.evt.omnibase-infra.node-generation-completed.v1"
                ]  # onex-topic-test-fixture
            ),
        )

        validator = ValidatorDemoPathTopicCoherence(repo_roots=[tmp_path])
        result = validator.run()

        assert not result.is_valid
        rule_codes = {i.code for i in result.issues}
        assert (
            RULE_PUBLISH_SUBSCRIBE_MISMATCH in rule_codes
            or RULE_ORPHAN_PRODUCER in rule_codes
        )

    def test_widget_topic_no_producer_fails_gate(self, tmp_path: Path) -> None:
        _write_contract(
            tmp_path,
            "dashboard_node",
            _minimal_contract(
                widget_topics=[
                    "onex.snapshot.projection.delegation.correlation-trace.v1"
                ]  # onex-topic-test-fixture
            ),
        )

        validator = ValidatorDemoPathTopicCoherence(repo_roots=[tmp_path])
        result = validator.run()

        assert not result.is_valid
        rule_codes = {i.code for i in result.issues}
        assert RULE_WIDGET_TOPIC_NO_PRODUCER in rule_codes

    def test_hand_authored_literal_in_python_fails_gate(self, tmp_path: Path) -> None:
        """A .py file on the demo path contains a bare topic string literal."""
        # The ValidatorHardcodedTopics already handles this, but we delegate to it
        # and surface the finding under our gate's RULE_HAND_AUTHORED_LITERAL code.
        _write_contract(
            tmp_path,
            "gen_consumer",
            _minimal_contract(
                subscribe=["onex.cmd.omnimarket.node-generation-requested.v1"],
                publish=["onex.evt.omnimarket.node-generation-completed.v1"],
            ),
        )
        _write_python(
            tmp_path,
            "gen_consumer/handler.py",
            """\
            # handler with hand-authored topic literal — should fail gate
            TOPIC = "onex.cmd.omnimarket.node-generation-requested.v1"
            """,
        )

        validator = ValidatorDemoPathTopicCoherence(repo_roots=[tmp_path])
        result = validator.run()

        assert not result.is_valid
        rule_codes = {i.code for i in result.issues}
        assert RULE_HAND_AUTHORED_LITERAL in rule_codes

    def test_no_demo_path_contracts_is_valid(self, tmp_path: Path) -> None:
        """No demo-path contracts → gate passes (nothing to check)."""
        _write_contract(
            tmp_path,
            "non_demo_node",
            _minimal_contract(
                demo_path=False, subscribe=["onex.cmd.omnimarket.other.v1"]
            ),
        )

        validator = ValidatorDemoPathTopicCoherence(repo_roots=[tmp_path])
        result = validator.run()

        assert result.is_valid

    def test_exit_code_nonzero_on_failure(self, tmp_path: Path) -> None:
        _write_contract(
            tmp_path,
            "consumer_node",
            _minimal_contract(
                subscribe=["onex.cmd.omnimarket.node-generation-requested.v1"]
            ),
        )

        validator = ValidatorDemoPathTopicCoherence(repo_roots=[tmp_path])
        result = validator.run()

        assert not result.is_valid
        # Exit code 1 = errors found
        assert validator.get_exit_code(result) == 1
