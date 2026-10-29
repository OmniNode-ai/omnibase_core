# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the demo-path topic coherence check node (OMN-21520)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.nodes.demo_path_topic_coherence_check.model_demo_path_topic_coherence_check_input import (
    ModelDemoPathTopicCoherenceCheckInput,
)
from omnibase_core.nodes.node_demo_path_topic_coherence_check_compute.handler import (
    NodeDemoPathTopicCoherenceCheckCompute,
)
from omnibase_core.nodes.node_demo_path_topic_coherence_check_compute.runtime_demo_path_topic_coherence_check import (
    main,
)
from omnibase_core.validation.validator_demo_path_topic_coherence import (
    RULE_ORPHAN_PRODUCER,
)

pytestmark = pytest.mark.unit

_TOPIC = "onex.evt.omnimarket.node-generation-completed.v1"


def _write_contract(root: Path, name: str, event_bus: dict[str, list[str]]) -> None:
    node_dir = root / name
    node_dir.mkdir(parents=True)
    (node_dir / "contract.yaml").write_text(
        yaml.dump(
            {
                "name": name,
                "contract_version": {"major": 1, "minor": 0, "patch": 0},
                "node_type": "effect",
                "node_version": {"major": 1, "minor": 0, "patch": 0},
                "metadata": {"demo_path": True},
                "event_bus": event_bus,
            }
        )
    )


def _passing_root(tmp_path: Path) -> Path:
    root = tmp_path / "ok"
    _write_contract(root, "node_producer", {"publish_topics": [_TOPIC]})
    _write_contract(root, "node_consumer", {"subscribe_topics": [_TOPIC]})
    return root


def _failing_root(tmp_path: Path) -> Path:
    root = tmp_path / "bad"
    _write_contract(root, "node_producer", {"publish_topics": [_TOPIC]})
    return root


def test_handle_passes_on_coherent_topics(tmp_path: Path) -> None:
    result = NodeDemoPathTopicCoherenceCheckCompute().handle(
        ModelDemoPathTopicCoherenceCheckInput(repo_roots=(_passing_root(tmp_path),))
    )
    assert result.is_valid is True
    assert not result.issues


def test_handle_reports_orphan_producer(tmp_path: Path) -> None:
    result = NodeDemoPathTopicCoherenceCheckCompute().handle(
        ModelDemoPathTopicCoherenceCheckInput(repo_roots=(_failing_root(tmp_path),))
    )
    assert result.is_valid is False
    assert RULE_ORPHAN_PRODUCER in {i.rule_name for i in result.issues}


def test_main_exit_codes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["gate", str(_passing_root(tmp_path))])
    with pytest.raises(SystemExit) as ok:
        main()
    assert ok.value.code == 0
    capsys.readouterr()

    monkeypatch.setattr(sys, "argv", ["gate", str(_failing_root(tmp_path))])
    with pytest.raises(SystemExit) as bad:
        main()
    assert bad.value.code == 1
    assert "[ERROR]" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["gate"])
    with pytest.raises(SystemExit) as usage:
        main()
    assert usage.value.code == 2
    assert "Usage: onex-demo-path-topic-gate" in capsys.readouterr().err
