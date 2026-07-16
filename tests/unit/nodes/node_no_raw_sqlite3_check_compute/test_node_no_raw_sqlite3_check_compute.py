# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Perturbation-corpus tests for node_no_raw_sqlite3_check_compute (OMN-14659).

Every ``must_flag`` / ``must_pass`` case from the OMN-14659 WS8 spec is
exercised here, plus SyntaxError handling, the ``_adapter.py`` filename
exclusion (with a real, non-commented-out violation, beyond the corpus
given), ``# di-ok`` annotation on an actual import+call pair, and report
aggregation. Message fidelity is asserted against
``omniclaude/scripts/validation/validate_no_raw_sqlite3.py`` — this is the
load-bearing perturbation-oracle contract.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.no_raw_sqlite3_check.model_no_raw_sqlite3_check_input import (
    ModelNoRawSqlite3CheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_no_raw_sqlite3_check_compute.handler import (
    NodeNoRawSqlite3CheckCompute,
)

pytestmark = pytest.mark.unit


def _report(path: str, source: str):
    handler = NodeNoRawSqlite3CheckCompute()
    return handler.handle(
        ModelNoRawSqlite3CheckInput(files=[ModelSourceFile(path=path, source=source)])
    )


# =============================================================================
# must_flag corpus — every case MUST produce exactly one FAIL finding
# =============================================================================


def test_must_flag_sqlite3_connect_via_module_import() -> None:
    report = _report("a.py", 'import sqlite3\nconn = sqlite3.connect("db.sqlite")\n')

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.severity == "FAIL"
    assert finding.validator_id == "arch-no-raw-sqlite3"
    assert finding.location == "a.py:2"
    assert finding.message == (
        "a.py:2: raw sqlite3.connect() call — database access must go through an "
        "injected adapter, not a direct connection. Add '# di-ok' to suppress for "
        "legitimate adapter bootstrap."
    )


def test_must_flag_from_sqlite3_import_connect() -> None:
    report = _report("a.py", "from sqlite3 import connect\nconn = connect(path)\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].location == "a.py:2"


def test_must_flag_from_sqlite3_import_connect_as_alias() -> None:
    report = _report("a.py", "from sqlite3 import connect as c\nconn = c(path)\n")

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].location == "a.py:2"


# =============================================================================
# must_pass corpus — every case MUST produce zero findings
# =============================================================================


def test_must_pass_di_ok_annotation_without_import_in_same_file() -> None:
    """No `import sqlite3` in this single-line file, so the module alias set is
    empty and the Attribute-call branch never matches — passes regardless of
    the `# di-ok` annotation, matching the oracle's own per-file import
    tracking exactly."""
    report = _report("a.py", "conn = sqlite3.connect(path)  # di-ok\n")

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_adapter_path_documentation_comment() -> None:
    """This corpus entry is a full-line Python comment — no AST nodes at all,
    so it passes trivially regardless of the _adapter.py exclusion mechanism."""
    report = _report(
        "a.py",
        "# file src/omniclaude/db/session_adapter.py (*_adapter.py excluded): "
        "conn = sqlite3.connect(path)\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_injected_adapter_call() -> None:
    report = _report("a.py", "db = injected_adapter.connect()\n")

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_must_pass_import_only_no_call() -> None:
    report = _report(
        "a.py", "import sqlite3  # import only, no connect() call in this module\n"
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


# =============================================================================
# _adapter.py filename exclusion — real (non-commented) hit on an adapter
# path, beyond the given corpus, proving is_excluded_adapter_filename fires.
# =============================================================================


def test_adapter_suffixed_file_is_excluded_even_with_real_violation() -> None:
    report = _report(
        "src/omniclaude/db/session_adapter.py",
        'import sqlite3\nconn = sqlite3.connect("db.sqlite")\n',
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_non_adapter_file_is_not_excluded() -> None:
    report = _report(
        "src/omniclaude/db/session_store.py",
        'import sqlite3\nconn = sqlite3.connect("db.sqlite")\n',
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1


# =============================================================================
# # di-ok annotation on a real import+call pair
# =============================================================================


def test_di_ok_annotation_suppresses_real_violation() -> None:
    report = _report(
        "a.py",
        "import sqlite3\nconn = sqlite3.connect(path)  # di-ok\n",
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


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
    handler = NodeNoRawSqlite3CheckCompute()
    report = handler.handle(
        ModelNoRawSqlite3CheckInput(
            files=[
                ModelSourceFile(
                    path="a.py",
                    source='import sqlite3\nconn = sqlite3.connect("db.sqlite")\n',
                ),
                ModelSourceFile(
                    path="b.py", source="db = injected_adapter.connect()\n"
                ),
            ]
        )
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.metrics.total == 1
    assert report.metrics.fail_count == 1
    assert report.provenance.validators_run == ("arch-no-raw-sqlite3",)


def test_empty_input_passes_trivially() -> None:
    handler = NodeNoRawSqlite3CheckCompute()
    report = handler.handle(ModelNoRawSqlite3CheckInput(files=[]))

    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert report.metrics.total == 0
