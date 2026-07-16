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
