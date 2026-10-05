# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Direct handler parity on each corpus branch and suppression edge."""

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.private_ip_check.model_private_ip_check_input import (
    ModelPrivateIpCheckInput,
)
from omnibase_core.nodes.node_private_ip_check_compute.handler import (
    NodePrivateIpCheckCompute,
)

pytestmark = pytest.mark.unit


def test_parity_handler_each_corpus_source(parity_corpus: Path) -> None:
    golden_path = (
        Path(__file__).resolve().parents[3]
        / "fixtures/validator_parity/private_ip/golden.json"
    )
    expected = json.loads(golden_path.read_text())["scanner_findings"]
    for path in sorted(parity_corpus.rglob("*")):
        if not path.is_file():
            continue
        source = path.read_text()
        name = path.relative_to(parity_corpus).as_posix()
        rows = expected[name]
        report = NodePrivateIpCheckCompute().handle(
            ModelPrivateIpCheckInput(files=[ModelSourceFile(path=name, source=source)])
        )
        assert report.overall_status == ("FAIL" if rows else "PASS")
        assert [
            (f.location, f.rule_id, f.message, f.evidence) for f in report.findings
        ] == [
            (
                f"{name}:{row['line']}",
                row["rule_id"],
                row["message"],
                {
                    "column": row["column"],
                    "matched_text": row["matched_text"],
                    "context": row["context"],
                },
            )
            for row in rows
        ]
        assert all(f.severity == "FAIL" for f in report.findings)


def test_parity_handler_empty_request() -> None:
    report = NodePrivateIpCheckCompute().handle(ModelPrivateIpCheckInput())
    assert report.overall_status == "PASS"
    assert report.provenance.validators_run == ("validator-private-ip-compute",)
