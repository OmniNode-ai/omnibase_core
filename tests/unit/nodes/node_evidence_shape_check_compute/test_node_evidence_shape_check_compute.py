# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the evidence-shape check node (OMN-21520)."""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.evidence_shape_check.model_evidence_shape_check_input import (
    ModelEvidenceShapeCheckInput,
)
from omnibase_core.nodes.node_evidence_shape_check_compute.handler import (
    NodeEvidenceShapeCheckCompute,
)
from omnibase_core.nodes.node_evidence_shape_check_compute.runtime_evidence_shape_check import (
    main,
)

pytestmark = pytest.mark.unit

_PASSING_BODY = "Evidence-Source: OCC#1234\nEvidence-Ticket: OMN-1"
_FAILING_BODY = "```\nEvidence-Source: OCC#1234\n```"


def test_handle_passes_canonical_stamp() -> None:
    result = NodeEvidenceShapeCheckCompute().handle(
        ModelEvidenceShapeCheckInput(pr_body=_PASSING_BODY)
    )
    assert result.passed is True


def test_handle_fails_fenced_only_stamp() -> None:
    result = NodeEvidenceShapeCheckCompute().handle(
        ModelEvidenceShapeCheckInput(pr_body=_FAILING_BODY)
    )
    assert result.passed is False
    assert result.message


def test_main_exit_codes_and_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--pr-body", _PASSING_BODY]) == 0
    assert capsys.readouterr().out.startswith("::notice::")
    assert main(["--pr-body", _FAILING_BODY]) == 1
    assert capsys.readouterr().out.startswith("::error::")
