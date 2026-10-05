# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Port the retired private-IP handler's acceptance and suppression tests."""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.private_ip_check.model_private_ip_check_input import (
    ModelPrivateIpCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_private_ip_check_compute.handler import (
    NodePrivateIpCheckCompute,
)

pytestmark = pytest.mark.unit

_VIOLATION_FIXTURES: tuple[str, ...] = (
    'HOST = "192.' + '168.86.201"',
    'BROKER = "10.' + '0.0.42"',
    'DB = "172.' + '16.5.10"',
    'HOST = "192.' + '168.99.250"',
    'ADDR = "172.' + '31.255.254"',
    'ENDPOINT = "https://192.' + '168.86.201:8000/v1/chat/completions"',
    "REDIS = '10." + "10.10.10'",
)
_CLEAN_FIXTURES: tuple[str, ...] = (
    'DNS = "8.8.8.8"',
    'endpoint_ref = resolve_endpoint("local-coder")',
    'VERSION = "1.10.172.0"',
    'HOST = "172.' + '15.0.1"',
    'HOST = "192.' + '168.86.201"  # onex-' + "allow-internal-ip approved test fixture",
)


def _scan(source: str, path: str = "<input>") -> ModelValidationReport:
    return NodePrivateIpCheckCompute().handle(
        ModelPrivateIpCheckInput(files=[ModelSourceFile(path=path, source=source)])
    )


@pytest.mark.parametrize("source", _VIOLATION_FIXTURES)
def test_every_violation_fixture_is_flagged(source: str) -> None:
    report = _scan(source)
    assert report.overall_status == "FAIL", f"violation fixture not flagged: {source!r}"
    assert report.findings, "a flagged result must carry at least one finding"


@pytest.mark.parametrize("source", _CLEAN_FIXTURES)
def test_every_clean_fixture_passes(source: str) -> None:
    report = _scan(source)
    assert report.overall_status == "PASS", f"clean fixture false-flagged: {source!r}"
    assert report.findings == ()


def test_finding_carries_block_line_column_context() -> None:
    address = "192." + "168.86.201"
    source = f'  HOST = "{address}"'
    report = _scan(source)
    assert report.overall_status == "FAIL"
    (finding,) = report.findings
    assert finding.rule_id == "192.168/16"
    assert finding.evidence["matched_text"] == address
    assert finding.location == "<input>:1"
    column = finding.evidence["column"]
    assert isinstance(column, int)
    assert column >= 1
    assert address in str(finding.evidence["context"])
    assert finding.message == f"<input>:1:{column}: [192.168/16] {address!r}"


def test_all_three_rfc1918_blocks_are_labelled() -> None:
    assert _scan('x = "10.' + '1.2.3"').findings[0].rule_id == "10/8"
    assert _scan('x = "172.' + '20.0.1"').findings[0].rule_id == "172.16/12"
    assert _scan('x = "192.' + '168.0.1"').findings[0].rule_id == "192.168/16"


def test_octet_over_255_is_not_a_valid_ip() -> None:
    assert _scan('x = "192.' + '168.300.1"').overall_status == "PASS"


def test_handler_returns_compute_result() -> None:
    report = _scan('H = "10.' + '0.0.1"', path="f.py")
    assert report is not None
    assert report.overall_status == "FAIL"
    assert report.findings[0].location == "f.py:1"


def test_findings_are_order_independent() -> None:
    source = 'A = "10.' + '0.0.1"\nB = "192.' + '168.1.1"'
    findings = _scan(source).findings
    assert [finding.location for finding in findings] == ["<input>:1", "<input>:2"]


def test_line_marker_suppresses_only_that_line() -> None:
    first = "10." + "0.0.1"
    second = "192." + "168.1.1"
    marker = "onex-" + "allow-internal-ip"
    source = f'A = "{first}"  # {marker} approved\nB = "{second}"'
    findings = _scan(source).findings
    assert [finding.location for finding in findings] == ["<input>:2"]


def test_file_marker_suppresses_the_whole_file() -> None:
    first = "10." + "0.0.1"
    second = "192." + "168.1.1"
    third = "172." + "20.0.1"
    marker = "onex-" + "allow-file-internal-ip"
    source = f'# {marker} doc fixture\nA = "{first}"\nB = "{second}"\nC = "{third}"'
    report = _scan(source)
    assert report.overall_status == "PASS"
    assert report.findings == ()
