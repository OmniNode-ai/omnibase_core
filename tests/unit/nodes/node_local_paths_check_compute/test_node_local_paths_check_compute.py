# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct matcher parity and typed pure handler checks."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.local_paths_check.model_local_paths_check_input import (
    ModelLocalPathsCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_local_paths_check_compute.handler import (
    NodeLocalPathsCheckCompute,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("source", "rules"),
    [
        ('"/' + 'Volumes/Disk/a"', ("macOS volume mount",)),
        ('"/' + 'Users/_alice/a"', ("macOS user home",)),
        ('"/' + 'home/runner/a"', ("Linux user home",)),
        ('"C:/' + 'Users/bob/a"', ("Windows user path", "macOS user home")),
        (r'"c:' + r'\users\bob\a"', ("Windows user path",)),
    ],
)
def test_parity_node_rules(source: str, rules: tuple[str, ...]) -> None:
    report = NodeLocalPathsCheckCompute().handle(
        ModelLocalPathsCheckInput(files=[ModelSourceFile(path="a.txt", source=source)])
    )
    assert report.overall_status == "FAIL"
    assert report.provenance.validators_run == ("validator-local-paths-compute",)
    assert tuple(finding.rule_id for finding in report.findings) == rules
    assert all(finding.location == "a.txt:1" for finding in report.findings)
    assert all(finding.severity == "FAIL" for finding in report.findings)


def test_parity_node_empty_and_deterministic() -> None:
    handler = NodeLocalPathsCheckCompute()
    request = ModelLocalPathsCheckInput()
    assert handler.handle(request).overall_status == "PASS"
    assert handler.handle(request).findings == handler.handle(request).findings


def test_parity_node_input_frozen_forbid() -> None:
    with pytest.raises(ValidationError):
        ModelLocalPathsCheckInput.model_validate({"unknown": []})
    request = ModelLocalPathsCheckInput()
    with pytest.raises(ValidationError):
        request.files = []
