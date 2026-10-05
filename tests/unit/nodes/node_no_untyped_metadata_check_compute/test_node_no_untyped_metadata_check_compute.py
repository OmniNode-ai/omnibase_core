# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Direct handler parity, finding provenance and typed input checks."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.no_untyped_metadata_check.model_no_untyped_metadata_check_input import (
    ModelNoUntypedMetadataCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_no_untyped_metadata_check_compute.handler import (
    NodeNoUntypedMetadataCheckCompute,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "type_text",
    [
        "dict[str, Any]",
        "dict[str, object]",
        "Optional[dict[str, Any]]",
        "Optional[dict[str, object]]",
        "dict[str,\tAny]",
    ],
)
def test_parity_handler_types(type_text: str) -> None:
    source = "metadata: " + type_text + "\n"
    report = NodeNoUntypedMetadataCheckCompute().handle(
        ModelNoUntypedMetadataCheckInput(
            files=[ModelSourceFile(path="a.py", source=source)]
        )
    )
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.validator_id == "no-untyped-metadata"
    assert finding.rule_id == "no-untyped-metadata"
    assert finding.severity == "FAIL"
    assert finding.location == "a.py:1"
    assert (
        finding.message == "a.py:1: untyped metadata dict — use TypedDict or add ONEX_"
        "EXCLUDE comment"
    )
    assert report.provenance.validators_run == ("no-untyped-metadata",)


def test_parity_handler_same_line_only() -> None:
    marker = "ONEX_" + "EXCLUDE:"
    field = "metadata" + ": dict[str, Any]"
    report = NodeNoUntypedMetadataCheckCompute().handle(
        ModelNoUntypedMetadataCheckInput(
            files=[
                ModelSourceFile(
                    path="a.py",
                    source=f"# {marker}\n{field}\n{field} # {marker}\n{field}\n# {marker}\n",
                )
            ]
        )
    )
    assert [finding.location for finding in report.findings] == ["a.py:2", "a.py:4"]


def test_parity_handler_line_iteration_and_empty() -> None:
    field = "metadata" + ": dict[str, Any]"
    report = NodeNoUntypedMetadataCheckCompute().handle(
        ModelNoUntypedMetadataCheckInput(
            files=[
                ModelSourceFile(
                    path="a.py", source=f"x = '\u2028'; {field}\r\n{field}\r{field}"
                ),
                ModelSourceFile(path="a.txt", source=field),
            ]
        )
    )
    assert [finding.location for finding in report.findings] == [
        "a.py:1",
        "a.py:2",
        "a.py:3",
    ]
    assert (
        NodeNoUntypedMetadataCheckCompute()
        .handle(ModelNoUntypedMetadataCheckInput())
        .overall_status
        == "PASS"
    )


def test_parity_input_frozen_and_extra_forbidden() -> None:
    request = ModelNoUntypedMetadataCheckInput()
    with pytest.raises(ValidationError):
        request.files = []
    with pytest.raises(ValidationError):
        ModelNoUntypedMetadataCheckInput.model_validate(
            {"files": [], "unexpected": True}
        )
