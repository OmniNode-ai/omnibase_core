# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-rule parity, immutable facts, and absence of handler I/O."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.nodes.node_test_root_collection_check_compute.handler import (
    NodeTestRootCollectionCheckCompute,
)
from tests.unit.nodes.node_test_root_collection_check_compute.parity_support import (
    parity_request,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("name", "rule"),
    [
        ("stray", "uncollected-test-root"),
        ("missing_declared_root", "missing-testpath-directory"),
        ("positional_tests", "full-suite-positional-path"),
        ("collocated_unmapped", "selector-unmapped-root"),
        ("mapped_undeclared", "selector-undeclared-root"),
        ("standalone_missing_project", "standalone-project-wiring"),
    ],
)
def test_parity_handler_rule(name: str, rule: str, tmp_path: Path) -> None:
    report = NodeTestRootCollectionCheckCompute().handle(parity_request(tmp_path, name))
    assert any(finding.rule_id == rule for finding in report.findings)
    assert all(
        finding.validator_id == "arch-test-root-collection"
        for finding in report.findings
    )


def test_parity_handler_is_pure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = parity_request(tmp_path, "standalone_call_chain")

    def forbidden_read(
        path: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        pytest.fail("COMPUTE attempted filesystem access")

    monkeypatch.setattr(Path, "read_text", forbidden_read)
    assert NodeTestRootCollectionCheckCompute().handle(request).overall_status == "PASS"


def test_parity_input_frozen(tmp_path: Path) -> None:
    request = parity_request(tmp_path, "clean")
    with pytest.raises(ValidationError):
        request.root_label = "changed"
