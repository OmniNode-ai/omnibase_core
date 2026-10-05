# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct canonical-handler matching and typed-input tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.hardcoded_topic_check.model_hardcoded_topic_check_input import (
    ModelHardcodedTopicCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_hardcoded_topic_check_compute.handler import (
    NodeHardcodedTopicCheckCompute,
)
from omnibase_core.nodes.node_hardcoded_topic_check_compute.matcher_hardcoded_topic import (
    VALIDATOR_ID,
)
from tests.unit.nodes.node_hardcoded_topic_check_compute.parity_helpers import (
    materialize_parity_corpus,
)

pytestmark = pytest.mark.unit


def test_parity_handler_match_order_and_context() -> None:
    topic = ".".join(("onex", "a", "b", "c"))
    context = f"  A = \"{topic}\"; B = '{topic}'  "
    report = NodeHardcodedTopicCheckCompute().handle(
        ModelHardcodedTopicCheckInput(
            files=[ModelSourceFile(path="f.txt", source=f"\n{context}\n")]
        )
    )
    assert report.overall_status == "FAIL"
    assert report.metrics.fail_count == 2
    assert [f.location for f in report.findings] == ["f.txt:2", "f.txt:2"]
    assert [f.message for f in report.findings] == [
        f"f.txt:2: [{topic}] {context.strip()}"
    ] * 2
    assert all(
        f.rule_id == "hardcoded-topic-literal" and f.validator_id == VALIDATOR_ID
        for f in report.findings
    )
    assert report.provenance.validators_run == (VALIDATOR_ID,)


@pytest.mark.parametrize(
    ("name", "count"),
    [
        ("generation.py", 1),
        ("publish.py", 1),
        ("single.py", 1),
        ("domain.py", 1),
        ("deep.py", 1),
        ("contract.py", 0),
        ("import.py", 0),
        ("short.py", 0),
        ("other.py", 0),
        ("mismatch.py", 0),
        ("missing_quote.py", 0),
        ("uppercase_prefix.py", 0),
        ("uppercase_segment.py", 0),
        ("underscore.py", 0),
        ("hyphen.py", 0),
        ("digits.py", 1),
        ("empty_segment.py", 0),
        ("short_cmd.py", 0),
        ("short_evt.py", 0),
        ("dlq_underscore.py", 0),
        ("prefix_probe.py", 1),
        ("dynamic.py", 0),
        ("static_fstring.py", 1),
        ("raw_string.py", 1),
        ("comment.py", 1),
        ("docstring.py", 1),
        ("triple_quote.py", 1),
        ("duplicate_order.py", 3),
        ("line_marker.py", 1),
        ("marker_string.py", 1),
        ("file_marker.py", 0),
        ("file_marker_string.py", 0),
        ("market_annotation.py", 1),
        ("empty.py", 0),
    ],
)
def test_parity_handler_corpus_rules(tmp_path: Path, name: str, count: int) -> None:
    files = materialize_parity_corpus(tmp_path)
    source = next(f for f in files if f.path == str(tmp_path / name))
    report = NodeHardcodedTopicCheckCompute().handle(
        ModelHardcodedTopicCheckInput(files=[source])
    )
    assert report.metrics.total == count
    assert report.overall_status == ("FAIL" if count else "PASS")


def test_parity_handler_empty_input() -> None:
    report = NodeHardcodedTopicCheckCompute().handle(ModelHardcodedTopicCheckInput())
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_parity_input_frozen_and_extra_forbidden() -> None:
    request = ModelHardcodedTopicCheckInput()
    with pytest.raises(ValidationError):
        request.files = []
    with pytest.raises(ValidationError):
        ModelHardcodedTopicCheckInput.model_validate({"files": [], "unexpected": True})
