# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Perturbation-corpus tests for node_no_hardcoded_ip_check_compute (OMN-14659).

Every ``must_flag`` / ``must_pass`` case from the OMN-14659 WS8 spec is
exercised here. Message fidelity is asserted byte-for-byte against
``omniclaude/scripts/validation/validate_no_hardcoded_ip.py`` — this is the
load-bearing perturbation-oracle contract.

Report/finding shapes are the canonical OMN-2362 generic validator types
(:mod:`omnibase_core.models.validation.model_validation_report`), not a
per-node fork — see ``node_no_utcnow_check_compute`` (OMN-14656) for the
established precedent this node mirrors.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.no_hardcoded_ip_check.model_no_hardcoded_ip_check_input import (
    ModelNoHardcodedIpCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_no_hardcoded_ip_check_compute.handler import (
    NodeNoHardcodedIpCheckCompute,
)

pytestmark = pytest.mark.unit


def _report(path: str, source: str):
    handler = NodeNoHardcodedIpCheckCompute()
    return handler.handle(
        ModelNoHardcodedIpCheckInput(files=[ModelSourceFile(path=path, source=source)])
    )


# =============================================================================
# must_flag corpus — every case MUST produce exactly one FAIL finding
# =============================================================================


def test_must_flag_192_168_literal() -> None:
    report = _report("a.py", 'BROKER = "192.168.86.201"\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.severity == "FAIL"
    assert finding.validator_id == "arch-no-hardcoded-ip"
    assert finding.location == "a.py:1"
    assert finding.message == 'a.py:1: BROKER = "192.168.86.201"'


def test_must_flag_10_x_with_scheme_and_port() -> None:
    report = _report("a.py", 'url = "http://10.0.0.5:8080"\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == 'a.py:1: url = "http://10.0.0.5:8080"'


def test_must_flag_172_16_range() -> None:
    report = _report("a.py", 'host = "172.16.0.1"\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == 'a.py:1: host = "172.16.0.1"'


def test_must_flag_https_with_port_and_path() -> None:
    report = _report("a.py", 'endpoint = "https://192.168.1.1:443/foo"\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == (
        'a.py:1: endpoint = "https://192.168.1.1:443/foo"'
    )


# =============================================================================
# must_pass corpus — every case MUST produce zero findings
# =============================================================================


def test_must_pass_env_var_lookup() -> None:
    report = _report("a.py", 'BROKER = os.environ["KAFKA_BOOTSTRAP_SERVERS"]\n')

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_suppression_marker() -> None:
    report = _report("a.py", 'ip = "192.168.86.201"  # onex-allow-internal-ip\n')

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_public_dns_ip() -> None:
    report = _report("a.py", 'public_dns = "8.8.8.8"\n')

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_loopback() -> None:
    report = _report("a.py", 'loopback = "127.0.0.1"\n')

    assert report.overall_status == "PASS"
    assert report.findings == ()


# =============================================================================
# OMN-14713 false-positive corpus — invalid octets and embedded literals
# must NOT flag (the matcher only narrows; the fail-closed gate is preserved).
# =============================================================================


@pytest.mark.parametrize(
    "source",
    [
        pytest.param('bad = "10.256.999.1"\n', id="octet-256-and-999"),
        pytest.param('bad = "10.999.0.0"\n', id="octet-999"),
        pytest.param('bad = "192.168.256.1"\n', id="192-168-third-octet-256"),
        pytest.param('bad = "172.16.300.1"\n', id="172-16-octet-300"),
    ],
)
def test_must_pass_invalid_octet_over_255(source: str) -> None:
    """Octets > 255 are not valid IPs and must not be flagged (OMN-14713)."""
    report = _report("a.py", source)

    assert report.overall_status == "PASS"
    assert report.findings == ()


@pytest.mark.parametrize(
    "source",
    [
        pytest.param('x = "210.0.0.55"\n', id="digit-prefixed-inner-10.0.0.55"),
        pytest.param('x = "x10.0.0.1"\n', id="word-prefixed-inner-10.0.0.1"),
        pytest.param('x = "10.0.0.55.5"\n', id="dot-suffixed-trailing-octet"),
        pytest.param('x = "192.168.1.1234"\n', id="digit-suffixed-last-octet"),
    ],
)
def test_must_pass_rfc1918_literal_embedded_in_longer_token(source: str) -> None:
    """RFC1918 literals embedded in a longer token must not flag (OMN-14713)."""
    report = _report("a.py", source)

    assert report.overall_status == "PASS"
    assert report.findings == ()


@pytest.mark.parametrize(
    ("source", "expected_message"),
    [
        pytest.param(
            'host = "10.255.255.255"\n',
            'a.py:1: host = "10.255.255.255"',
            id="max-valid-octet-255",
        ),
        pytest.param(
            'host = "172.16.0.255"\n',
            'a.py:1: host = "172.16.0.255"',
            id="172-16-boundary-octet-255",
        ),
    ],
)
def test_must_flag_valid_boundary_octet_255(source: str, expected_message: str) -> None:
    """The 0-255 tightening must still flag genuine 255-octet IPs (OMN-14713)."""
    report = _report("a.py", source)

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == expected_message


# =============================================================================
# Aggregation across multiple files
# =============================================================================


def test_aggregate_metrics_and_provenance() -> None:
    handler = NodeNoHardcodedIpCheckCompute()
    report = handler.handle(
        ModelNoHardcodedIpCheckInput(
            files=[
                ModelSourceFile(path="a.py", source='BROKER = "192.168.86.201"\n'),
                ModelSourceFile(
                    path="b.py",
                    source='BROKER = os.environ["KAFKA_BOOTSTRAP_SERVERS"]\n',
                ),
            ]
        )
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.metrics.total == 1
    assert report.metrics.fail_count == 1
    assert report.metrics.pass_count == 0
    assert report.provenance.validators_run == ("arch-no-hardcoded-ip",)


def test_empty_input_passes_trivially() -> None:
    handler = NodeNoHardcodedIpCheckCompute()
    report = handler.handle(ModelNoHardcodedIpCheckInput(files=[]))

    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert report.metrics.total == 0
