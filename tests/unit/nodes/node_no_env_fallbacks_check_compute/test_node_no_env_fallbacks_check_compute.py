# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Perturbation-corpus tests for node_no_env_fallbacks_check_compute (OMN-14659).

Every ``must_flag`` / ``must_pass`` case from the OMN-14659 WS8 spec is
exercised here, plus shell-file dispatch, the skip-directory exclusion, and
report aggregation. Message fidelity is asserted byte-for-byte against
``omniclaude/scripts/validate_no_env_fallbacks.py`` — this is the
load-bearing perturbation-oracle contract.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.no_env_fallbacks_check.model_no_env_fallbacks_check_input import (
    ModelNoEnvFallbacksCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_no_env_fallbacks_check_compute.handler import (
    NodeNoEnvFallbacksCheckCompute,
)

pytestmark = pytest.mark.unit


def _report(path: str, source: str):
    handler = NodeNoEnvFallbacksCheckCompute()
    return handler.handle(
        ModelNoEnvFallbacksCheckInput(files=[ModelSourceFile(path=path, source=source)])
    )


# =============================================================================
# must_flag corpus — every case MUST produce exactly one FAIL finding
# =============================================================================


def test_must_flag_environ_get_localhost_default() -> None:
    report = _report("a.py", 'host = os.environ.get("PG_HOST", "localhost")\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.severity == "FAIL"
    assert finding.validator_id == "arch-no-env-fallbacks"
    assert finding.location == "a.py:1"
    assert finding.message == 'a.py:1: host = os.environ.get("PG_HOST", "localhost")'


def test_must_flag_getenv_http_localhost_default() -> None:
    report = _report("a.py", 'url = os.getenv("API_URL", "http://localhost:8080")\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == (
        'a.py:1: url = os.getenv("API_URL", "http://localhost:8080")'
    )


def test_must_flag_priv_ip_str_annotation_default() -> None:
    report = _report("a.py", 'broker: str = "192.168.86.201"\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == 'a.py:1: broker: str = "192.168.86.201"'


def test_must_flag_field_default_localhost() -> None:
    report = _report("a.py", 'endpoint = Field(default="redis://localhost:6379")\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == (
        'a.py:1: endpoint = Field(default="redis://localhost:6379")'
    )


# =============================================================================
# must_pass corpus — every case MUST produce zero findings
# =============================================================================


def test_must_pass_no_default_fail_fast() -> None:
    report = _report("a.py", 'host = os.environ["PG_HOST"]\n')

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_exempt_marker() -> None:
    report = _report(
        "a.py",
        'host = os.environ.get("PG_HOST", "localhost")  # fallback-ok: unit test only\n',
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_non_localhost_default() -> None:
    report = _report("a.py", 'name = os.environ.get("APP_NAME", "myapp")\n')

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_pure_comment_line() -> None:
    report = _report(
        "a.py",
        "# comment: defaults to localhost when unset (pure comment line, skipped)\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


# =============================================================================
# Shell-file dispatch
# =============================================================================


def test_shell_flags_localhost_parameter_expansion() -> None:
    report = _report("deploy.sh", 'HOST="${PG_HOST:-localhost}"\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == 'deploy.sh:1: HOST="${PG_HOST:-localhost}"'


def test_shell_exempt_marker_passes() -> None:
    report = _report(
        "deploy.sh", 'HOST="${PG_HOST:-localhost}"  # fallback-ok: local dev script\n'
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


# =============================================================================
# Unscanned suffix / skip-directory exclusion
# =============================================================================


def test_unscanned_suffix_is_ignored() -> None:
    report = _report("notes.md", 'host = os.environ.get("PG_HOST", "localhost")\n')

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_tests_directory_is_skipped() -> None:
    report = _report(
        "tests/fixtures/bad.py", 'host = os.environ.get("PG_HOST", "localhost")\n'
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


# =============================================================================
# Aggregation across multiple files
# =============================================================================


def test_aggregate_metrics_and_provenance() -> None:
    handler = NodeNoEnvFallbacksCheckCompute()
    report = handler.handle(
        ModelNoEnvFallbacksCheckInput(
            files=[
                ModelSourceFile(
                    path="a.py",
                    source='host = os.environ.get("PG_HOST", "localhost")\n',
                ),
                ModelSourceFile(path="b.py", source='host = os.environ["PG_HOST"]\n'),
            ]
        )
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.metrics.total == 1
    assert report.metrics.fail_count == 1
    assert report.provenance.validators_run == ("arch-no-env-fallbacks",)


def test_empty_input_passes_trivially() -> None:
    handler = NodeNoEnvFallbacksCheckCompute()
    report = handler.handle(ModelNoEnvFallbacksCheckInput(files=[]))

    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert report.metrics.total == 0
