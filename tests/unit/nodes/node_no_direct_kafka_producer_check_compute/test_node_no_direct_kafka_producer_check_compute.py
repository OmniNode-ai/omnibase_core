# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Perturbation-corpus tests for node_no_direct_kafka_producer_check_compute (OMN-14659).

Every ``must_flag`` / ``must_pass`` case from the OMN-14659 WS8 spec is
exercised here, plus SyntaxError handling, allowlist-path exclusion (with a
real, non-commented-out AST hit, beyond the corpus given), and report
aggregation. Message fidelity is asserted against
``omniclaude/scripts/validation/validate_no_direct_kafka_producer.py`` — this
is the load-bearing perturbation-oracle contract.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.no_direct_kafka_producer_check.model_no_direct_kafka_producer_check_input import (
    ModelNoDirectKafkaProducerCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_no_direct_kafka_producer_check_compute.handler import (
    NodeNoDirectKafkaProducerCheckCompute,
)

pytestmark = pytest.mark.unit


def _report(path: str, source: str):
    handler = NodeNoDirectKafkaProducerCheckCompute()
    return handler.handle(
        ModelNoDirectKafkaProducerCheckInput(
            files=[ModelSourceFile(path=path, source=source)]
        )
    )


# =============================================================================
# must_flag corpus — every case MUST produce at least one FAIL finding
# =============================================================================


def test_must_flag_aiokafka_producer_import() -> None:
    report = _report("a.py", "from aiokafka import AIOKafkaProducer\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) >= 1
    assert all(f.severity == "FAIL" for f in report.findings)
    assert all(
        f.validator_id == "arch-no-direct-kafka-producer" for f in report.findings
    )


def test_must_flag_confluent_kafka_import() -> None:
    report = _report("a.py", "import confluent_kafka\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == (
        "a.py:1: import 'confluent_kafka' uses direct Kafka producer symbol 'confluent_kafka'"
    )


def test_must_flag_kafka_producer_bare_name() -> None:
    report = _report("a.py", "producer = KafkaProducer(bootstrap_servers=host)\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == (
        "a.py:1: direct usage of Kafka producer symbol 'KafkaProducer'"
    )


def test_must_flag_kafka_producer_attribute_access() -> None:
    report = _report("a.py", "client = kafka.KafkaProducer()\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == (
        "a.py:1: direct usage of Kafka producer symbol 'KafkaProducer' via attribute access"
    )


# =============================================================================
# must_pass corpus — every case MUST produce zero findings
# =============================================================================


def test_must_pass_shared_publisher_import() -> None:
    report = _report("a.py", "from omniclaude.publisher import Publisher\n")

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_emit_via_daemon_await() -> None:
    report = _report("a.py", "await emit_via_daemon(event)\n")

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_kafka_producer_utils_import() -> None:
    report = _report(
        "a.py",
        "from omniclaude.lib.kafka_producer_utils import emit_via_daemon\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_allowed_path_documentation_comment() -> None:
    """This corpus entry is a full-line Python comment — no AST nodes at all,
    so it passes trivially regardless of the path allowlist mechanism."""
    report = _report(
        "a.py",
        "# file src/omniclaude/lib/kafka_producer_utils.py (allowed publisher-layer path): "
        "producer = AIOKafkaProducer(bootstrap_servers=host)\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


# =============================================================================
# Path allowlist — real (non-commented) hit on a publisher-layer path,
# beyond the given corpus, proving is_allowed_publisher_path actually fires.
# =============================================================================


def test_publisher_layer_path_is_excluded_even_with_real_violation() -> None:
    report = _report(
        "src/omniclaude/lib/kafka_producer_utils.py",
        "from aiokafka import AIOKafkaProducer\n"
        "producer = AIOKafkaProducer(bootstrap_servers=host)\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_non_publisher_layer_path_is_not_excluded() -> None:
    report = _report(
        "src/omniclaude/handlers/handler_ingest.py",
        "from aiokafka import AIOKafkaProducer\n",
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) >= 1


# =============================================================================
# Per-line suppression marker (OMN-14665) — additive, opt-in exemption for a
# symbol that merely *contains* a forbidden substring (e.g. the check's own
# node/model class names, or a ProtocolKafkaProducer* health-check type).
# =============================================================================


def test_suppression_marker_on_finding_line_exempts_it() -> None:
    report = _report(
        "a.py",
        "from x import ProtocolKafkaProducerAio  # onex-allow-kafka-producer: type name only\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_suppression_marker_on_from_line_covers_multiline_import() -> None:
    # A multi-line ``from ... import (`` reports the finding at the ``from``
    # line (node.lineno), so the marker on that line must suppress it.
    report = _report(
        "a.py",
        "from x import (  # onex-allow-kafka-producer: type name only\n"
        "    ProtocolKafkaProducerAio,\n"
        ")\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_suppression_marker_does_not_exempt_a_real_violation_elsewhere() -> None:
    # The marker only exempts its own line — a genuine producer import on an
    # unmarked line still flags.
    report = _report(
        "a.py",
        "from x import ProtocolKafkaProducerAio  # onex-allow-kafka-producer: type name only\n"
        "from aiokafka import AIOKafkaProducer\n",
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) >= 1
    assert all(
        "aiokafka" in f.message or "AIOKafkaProducer" in f.message
        for f in report.findings
    )


# =============================================================================
# SyntaxError handling
# =============================================================================


def test_syntax_error_yields_single_error_finding() -> None:
    report = _report("broken.py", "def f(:\n    pass\n")

    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.severity == "ERROR"
    assert finding.message.startswith("broken.py: SyntaxError:")
    assert finding.remediation is None


# =============================================================================
# Aggregation across multiple files
# =============================================================================


def test_aggregate_metrics_and_provenance() -> None:
    handler = NodeNoDirectKafkaProducerCheckCompute()
    report = handler.handle(
        ModelNoDirectKafkaProducerCheckInput(
            files=[
                ModelSourceFile(path="a.py", source="import confluent_kafka\n"),
                ModelSourceFile(
                    path="b.py", source="from omniclaude.publisher import Publisher\n"
                ),
            ]
        )
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.metrics.total == 1
    assert report.metrics.fail_count == 1
    assert report.provenance.validators_run == ("arch-no-direct-kafka-producer",)


def test_empty_input_passes_trivially() -> None:
    handler = NodeNoDirectKafkaProducerCheckCompute()
    report = handler.handle(ModelNoDirectKafkaProducerCheckInput(files=[]))

    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert report.metrics.total == 0
