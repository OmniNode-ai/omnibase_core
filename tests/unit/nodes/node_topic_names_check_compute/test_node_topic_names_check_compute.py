# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Direct matching assertions supplement the permanent script goldens."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.topic_names_check.model_topic_names_check_input import (
    ModelTopicNamesCheckInput,
)
from omnibase_core.nodes.node_topic_names_check_compute.handler import (
    NodeTopicNamesCheckCompute,
)
from omnibase_core.nodes.node_topic_names_check_compute.matcher_topic_names import (
    extract_topics,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("value", "rule"),
    [
        ("agent-actions", "flat-topic"),
        ("{env}." + "onex." + "evt.platform.event.v1", "env-prefix"),
        ("onex." + "events.platform.event.v1", "canonical-suffix"),
    ],
)
def test_parity_direct_rules(value: str, rule: str) -> None:
    report = NodeTopicNamesCheckCompute().handle(
        ModelTopicNamesCheckInput(
            files=[
                ModelSourceFile(path="topics.py", source=f"SUFFIX_CASE = {value!r}\n")
            ]
        )
    )
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.validator_id == "arch-topic-names"
    assert finding.severity == "FAIL"
    assert finding.rule_id == rule
    assert finding.location == "topics.py:1"


def test_parity_case_insensitive_extension_and_unsupported() -> None:
    source = 'TOPIC_CASE = "agent-actions"\n'
    assert extract_topics("topics.PY", source) == [(1, "agent-actions")]
    assert extract_topics("topics.yaml", source) == []


def test_parity_regex_does_not_require_parseable_python() -> None:
    source = 'bad syntax\nTOPIC_CASE = "agent-actions"\n'
    report = NodeTopicNamesCheckCompute().handle(
        ModelTopicNamesCheckInput(
            files=[ModelSourceFile(path="topics.py", source=source)]
        )
    )
    assert report.findings[0].location == "topics.py:2"
    assert report.overall_status == "FAIL"


def test_parity_request_is_frozen_and_forbids_extras() -> None:
    with pytest.raises(ValidationError):
        ModelTopicNamesCheckInput.model_validate({"files": [], "baseline": []})
    request = ModelTopicNamesCheckInput()
    with pytest.raises(ValidationError):
        request.files = []
    assert NodeTopicNamesCheckCompute().handle(request).overall_status == "PASS"
