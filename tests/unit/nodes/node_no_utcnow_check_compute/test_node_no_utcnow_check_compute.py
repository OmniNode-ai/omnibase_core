# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Perturbation-corpus tests for node_no_utcnow_check_compute (OMN-14656).

Every ``must_flag`` / ``must_pass`` case from the OMN-14656 Characterize
spec is exercised here, plus SyntaxError handling and report aggregation.
Message fidelity (including the literal U+2014 em dash) is asserted
byte-for-byte against ``omniclaude/scripts/validation/validate_no_utcnow.py``
— this is the load-bearing perturbation-oracle contract and is unaffected by
the canonical-report-type remediation below.

Report/finding shapes are the canonical OMN-2362 generic validator types
(:mod:`omnibase_core.models.validation.model_validation_report`), not a
per-node fork: ``findings`` is a tuple of ``ModelValidationFindingEmbed``,
``severity``/``overall_status`` are uppercase ``Literal`` strings (not the
generated, lowercase-valued ``EnumValidationStatus``), and
``overall_status`` is computed by the canonical precedence engine
(ERROR > FAIL > WARN > PASS) rather than a bespoke FAIL-for-either rule —
see handler.py module docstring for why a report containing only an ERROR
finding now aggregates to ``overall_status == "ERROR"`` rather than
``"FAIL"``.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_no_utcnow_check_input import (
    ModelNoUtcnowCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_no_utcnow_check_compute.handler import (
    NodeNoUtcnowCheckCompute,
)

pytestmark = pytest.mark.unit

_EM_DASH = "—"


def _report(path: str, source: str):
    handler = NodeNoUtcnowCheckCompute()
    return handler.handle(
        ModelNoUtcnowCheckInput(files=[ModelSourceFile(path=path, source=source)])
    )


# =============================================================================
# must_flag corpus — every case MUST produce exactly one FAIL finding
# =============================================================================


def test_must_flag_bare_datetime_utcnow_call() -> None:
    report = _report("a.py", "import datetime\nts = datetime.utcnow()\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.severity == "FAIL"
    assert finding.validator_id == "arch-no-utcnow"
    assert finding.location == "a.py:2"
    assert finding.message == (
        f"a.py:2: use of datetime.utcnow() {_EM_DASH} use datetime.now(tz=timezone.utc) instead"
    )


def test_must_flag_dt_alias_call() -> None:
    report = _report("a.py", "import datetime as dt\nts = dt.utcnow()\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.location == "a.py:2"
    assert finding.message == (
        f"a.py:2: use of dt.utcnow() {_EM_DASH} use datetime.now(tz=timezone.utc) instead"
    )


def test_must_flag_aliased_import_generic_branch() -> None:
    """`d = datetime` alias: id 'd' is NOT in {datetime, dt} -> generic branch (c), MUST still flag."""
    report = _report("a.py", "from datetime import datetime as d\nts = d.utcnow()\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.location == "a.py:2"
    assert finding.message == (
        f"a.py:2: use of .utcnow() {_EM_DASH} use .now(tz=timezone.utc) instead"
    )


def test_must_flag_datetime_datetime_utcnow() -> None:
    report = _report("a.py", "import datetime\nts = datetime.datetime.utcnow()\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.location == "a.py:2"
    assert finding.message == (
        f"a.py:2: use of datetime.datetime.utcnow() {_EM_DASH} "
        "use datetime.datetime.now(tz=timezone.utc) instead"
    )


def test_must_flag_attribute_access_without_call() -> None:
    """Bare attribute access (no call) — visit_Attribute fires regardless of ast.Call."""
    report = _report(
        "a.py", "from datetime import datetime\nhandler = datetime.utcnow\n"
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.location == "a.py:2"
    assert finding.message == (
        f"a.py:2: use of datetime.utcnow() {_EM_DASH} use datetime.now(tz=timezone.utc) instead"
    )


def test_must_flag_chained_call() -> None:
    report = _report(
        "a.py",
        "from datetime import datetime\nstamp = datetime.utcnow().isoformat()\n",
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.location == "a.py:2"
    assert finding.message == (
        f"a.py:2: use of datetime.utcnow() {_EM_DASH} use datetime.now(tz=timezone.utc) instead"
    )


def test_must_flag_over_broad_receiver_is_not_resolved() -> None:
    """The oracle intentionally over-flags ANY `.utcnow` attribute access,
    including on receivers that are not `datetime` at all. The COMPUTE must
    reproduce this over-broad match, not "improve" it."""
    report = _report("a.py", "foo = object()\nts = foo.utcnow()\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].message == (
        f"a.py:2: use of .utcnow() {_EM_DASH} use .now(tz=timezone.utc) instead"
    )


# =============================================================================
# must_pass corpus — every case MUST produce zero findings
# =============================================================================


def test_must_pass_timezone_aware_now() -> None:
    report = _report(
        "a.py",
        "from datetime import datetime, timezone\nts = datetime.now(timezone.utc)\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_utc_constant() -> None:
    report = _report(
        "a.py", "from datetime import datetime, UTC\nts = datetime.now(UTC)\n"
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_fully_qualified_now() -> None:
    report = _report(
        "a.py",
        "import datetime\nts = datetime.datetime.now(tz=datetime.timezone.utc)\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_comment_and_string_literal_not_flagged() -> None:
    report = _report(
        "a.py",
        '# datetime.utcnow() in a comment\nx = "datetime.utcnow"\n',
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_unrelated_clock_call() -> None:
    report = _report("a.py", "import time\nnow = time.time()\n")

    assert report.overall_status == "PASS"
    assert report.findings == ()


# =============================================================================
# SyntaxError handling (validate_no_utcnow.py:63-72)
# =============================================================================


def test_syntax_error_yields_single_error_finding() -> None:
    report = _report("broken.py", "def f(:\n    pass\n")

    # ERROR outranks FAIL in the canonical precedence engine (ERROR > FAIL >
    # WARN > PASS), so a report containing only an ERROR finding aggregates
    # to overall_status == "ERROR" — see module docstring above.
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
    handler = NodeNoUtcnowCheckCompute()
    report = handler.handle(
        ModelNoUtcnowCheckInput(
            files=[
                ModelSourceFile(
                    path="a.py", source="import datetime\nts = datetime.utcnow()\n"
                ),
                ModelSourceFile(
                    path="b.py",
                    source="from datetime import datetime, UTC\nts = datetime.now(UTC)\n",
                ),
            ]
        )
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.metrics.total == 1
    assert report.metrics.fail_count == 1
    assert report.metrics.pass_count == 0
    assert report.metrics.error_count == 0
    assert report.provenance.validators_run == ("arch-no-utcnow",)


def test_empty_input_passes_trivially() -> None:
    handler = NodeNoUtcnowCheckCompute()
    report = handler.handle(ModelNoUtcnowCheckInput(files=[]))

    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert report.metrics.total == 0
