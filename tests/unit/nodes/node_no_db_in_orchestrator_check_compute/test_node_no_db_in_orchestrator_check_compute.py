# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Perturbation-corpus tests for node_no_db_in_orchestrator_check_compute (OMN-14694).

The load-bearing case is the RED-against-exists-but-wrong triad
(``test_red_*``): the same DB-doing handler source is FLAGGED when it lives in
an ORCHESTRATOR package, PASSED when it lives in a COMPUTE package, and the
clean orchestrator is PASSED. That triad proves the gate catches the actual
archetype-specific violation — it is not merely green because no DB code exists
anywhere (green-on-absence), and it is not a blind every-file scan.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.no_db_in_orchestrator_check.model_no_db_in_orchestrator_check_input import (
    ModelNoDbInOrchestratorCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_no_db_in_orchestrator_check_compute.handler import (
    NodeNoDbInOrchestratorCheckCompute,
)

pytestmark = pytest.mark.unit


# A minimal orchestrator contract (both archetype seam fields set).
_ORCHESTRATOR_CONTRACT = (
    "name: node_x\n"
    "node_type: orchestrator\n"
    "descriptor:\n"
    "  node_archetype: orchestrator\n"
)

# A minimal COMPUTE contract — same shape, different archetype.
_COMPUTE_CONTRACT = (
    "name: node_x\nnode_type: compute\ndescriptor:\n  node_archetype: compute\n"
)

# Handler source that performs real database I/O.
_DB_HANDLER = "import sqlite3\n\n\ndef run(path):\n    return sqlite3.connect(path)\n"

# Handler source with no database access.
_CLEAN_HANDLER = (
    "from __future__ import annotations\n\n\ndef run(intents):\n    return intents\n"
)


def _run(*files: tuple[str, str]) -> ModelValidationReport:
    return NodeNoDbInOrchestratorCheckCompute().handle(
        ModelNoDbInOrchestratorCheckInput(
            files=[ModelSourceFile(path=p, source=s) for p, s in files]
        )
    )


# =============================================================================
# RED-against-exists-but-wrong triad — the load-bearing proof
# =============================================================================


def test_red_orchestrator_handler_with_db_io_fails() -> None:
    """EXISTS-BUT-WRONG: an orchestrator whose handler imports a DB driver is
    FLAGGED at the exact import line — not silently green."""
    report = _run(
        ("nodes/node_x_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_x_orchestrator/handler.py", _DB_HANDLER),
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.severity == "FAIL"
    assert finding.validator_id == "arch-no-db-in-orchestrator"
    assert finding.location == "nodes/node_x_orchestrator/handler.py:1"
    assert "DB access in ORCHESTRATOR node" in finding.message
    assert "sqlite3" in finding.message


def test_red_compute_handler_with_db_io_passes() -> None:
    """ARCHETYPE-KEYING: the SAME DB-doing handler in a COMPUTE package is NOT
    flagged. Proves the gate keys off the contract archetype, not a blind
    every-file scan — and that the orchestrator FAIL above is real, not an
    artefact of the DB source being present at all."""
    report = _run(
        ("nodes/node_x_compute/contract.yaml", _COMPUTE_CONTRACT),
        ("nodes/node_x_compute/handler.py", _DB_HANDLER),
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_red_clean_orchestrator_passes() -> None:
    """The clean orchestrator (no DB import) is PASSED — the gate is not a
    blanket 'orchestrator == fail'."""
    report = _run(
        ("nodes/node_x_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_x_orchestrator/handler.py", _CLEAN_HANDLER),
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


# =============================================================================
# Archetype seam — both fields are read independently
# =============================================================================


def test_orchestrator_via_descriptor_only_is_flagged() -> None:
    """A contract that declares orchestrator ONLY via descriptor.node_archetype
    (no top-level node_type) still arms the rule."""
    contract = "name: node_x\ndescriptor:\n  node_archetype: orchestrator\n"
    report = _run(
        ("nodes/node_x/contract.yaml", contract),
        ("nodes/node_x/handler.py", _DB_HANDLER),
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1


def test_orchestrator_via_node_type_only_is_flagged() -> None:
    """A contract that declares orchestrator ONLY via top-level node_type (no
    descriptor block) still arms the rule."""
    contract = "name: node_x\nnode_type: orchestrator\n"
    report = _run(
        ("nodes/node_x/contract.yaml", contract),
        ("nodes/node_x/handler.py", _DB_HANDLER),
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1


# =============================================================================
# Forbidden-module coverage — every driver / toolkit is caught
# =============================================================================


@pytest.mark.parametrize(
    ("import_line", "expected_module"),
    [
        ("import sqlite3", "sqlite3"),
        ("import aiosqlite", "aiosqlite"),
        ("import psycopg", "psycopg"),
        ("import psycopg2", "psycopg2"),
        ("import asyncpg", "asyncpg"),
        ("import sqlalchemy", "sqlalchemy"),
        ("import sqlalchemy.orm", "sqlalchemy"),
        ("from sqlalchemy import create_engine", "sqlalchemy"),
        ("from sqlalchemy.orm import Session", "sqlalchemy"),
        ("from psycopg.rows import dict_row", "psycopg"),
        ("import asyncpg as pg", "asyncpg"),
    ],
)
def test_each_forbidden_db_module_is_flagged(
    import_line: str, expected_module: str
) -> None:
    report = _run(
        ("nodes/node_x_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_x_orchestrator/handler.py", f"{import_line}\n"),
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert f"'{expected_module}'" in report.findings[0].message


# =============================================================================
# Non-violations
# =============================================================================


def test_relative_import_in_orchestrator_passes() -> None:
    """`from . import x` (node.module is None) must not trip the check."""
    report = _run(
        ("nodes/node_x_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_x_orchestrator/handler.py", "from . import sibling\n"),
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_non_db_import_in_orchestrator_passes() -> None:
    report = _run(
        ("nodes/node_x_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_x_orchestrator/handler.py", "import json\nimport pathlib\n"),
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_db_io_ok_annotation_suppresses_violation() -> None:
    report = _run(
        ("nodes/node_x_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        (
            "nodes/node_x_orchestrator/handler.py",
            "import sqlite3  # db-io-ok: bootstrap-only, no runtime connect\n",
        ),
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_db_import_outside_any_node_package_passes() -> None:
    """A .py file whose directory has NO contract is not a node package — even a
    real DB import there is out of scope (dir-scoping, not blind scan)."""
    report = _run(
        ("scripts/adhoc_backfill.py", _DB_HANDLER),
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_db_import_in_sibling_non_orchestrator_dir_passes() -> None:
    """DB import in an EFFECT package that is a *sibling* of the orchestrator is
    correct architecture — only the orchestrator dir's modules are scanned."""
    report = _run(
        ("nodes/node_x_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_x_orchestrator/handler.py", _CLEAN_HANDLER),
        (
            "nodes/node_db_effect/contract.yaml",
            _COMPUTE_CONTRACT.replace("compute", "effect"),
        ),
        ("nodes/node_db_effect/handler.py", _DB_HANDLER),
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()


# =============================================================================
# Error findings — fail loud, never silent-green
# =============================================================================


def test_unparseable_contract_yields_error_finding() -> None:
    report = _run(
        ("nodes/node_x/contract.yaml", "name: [unclosed\n"),
    )

    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.severity == "ERROR"
    assert "unparseable contract.yaml" in finding.message


def test_syntax_error_in_orchestrator_module_yields_error() -> None:
    report = _run(
        ("nodes/node_x_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_x_orchestrator/handler.py", "def f(:\n    pass\n"),
    )

    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    assert report.findings[0].message.startswith(
        "nodes/node_x_orchestrator/handler.py: SyntaxError:"
    )


# =============================================================================
# Aggregation
# =============================================================================


def test_two_orchestrators_aggregate_findings() -> None:
    report = _run(
        ("nodes/node_a_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_a_orchestrator/handler.py", "import sqlite3\n"),
        ("nodes/node_b_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_b_orchestrator/handler.py", "import asyncpg\n"),
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 2
    assert report.metrics.fail_count == 2
    assert report.provenance.validators_run == ("arch-no-db-in-orchestrator",)


def test_empty_input_passes_trivially() -> None:
    report = NodeNoDbInOrchestratorCheckCompute().handle(
        ModelNoDbInOrchestratorCheckInput(files=[])
    )

    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert report.metrics.total == 0


def test_multiple_db_imports_in_one_orchestrator_module() -> None:
    source = "import sqlite3\nimport asyncpg\nimport json\n"
    report = _run(
        ("nodes/node_x_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_x_orchestrator/handler.py", source),
    )

    assert report.overall_status == "FAIL"
    assert len(report.findings) == 2
    assert report.findings[0].location == "nodes/node_x_orchestrator/handler.py:1"
    assert report.findings[1].location == "nodes/node_x_orchestrator/handler.py:2"
