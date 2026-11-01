# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for ``no_raw_sqlite3``: one ``(path, source)`` pair into the COMPUTE node's handler.

The checker has no ``.validation.yaml``; its pure ``handle`` is called the way the node's
runtime calls it, and each finding of its report is returned as a validation issue under
the validator id and rule id the finding carries.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.nodes.no_raw_sqlite3_check.model_no_raw_sqlite3_check_input import (
    ModelNoRawSqlite3CheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_no_raw_sqlite3_check_compute.handler import (
    NodeNoRawSqlite3CheckCompute,
)
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun

_SEVERITY = {"WARN": EnumSeverity.WARNING}


def _judge(path: str, text: str) -> Sequence[ModelValidationIssue]:
    report = NodeNoRawSqlite3CheckCompute().handle(
        ModelNoRawSqlite3CheckInput(files=[ModelSourceFile(path=path, source=text)])
    )
    issues: list[ModelValidationIssue] = []
    for finding in report.findings:
        where, _, line = (finding.location or "").rpartition(":")
        located = where if line.isdigit() else finding.location
        issues.append(
            ModelValidationIssue(
                severity=_SEVERITY.get(finding.severity, EnumSeverity.ERROR),
                message=finding.message,
                code=finding.rule_id,
                file_path=Path(located) if located else None,
                line_number=int(line) if line.isdigit() else None,
                rule_name=finding.validator_id,
                suggestion=finding.remediation,
            )
        )
    return issues


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    text = source.text(source.path)
    return () if text is None else _judge(source.path, text)


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """A fixture is one module judged under its own file name."""
    return _judge(fixture.name, fixture.read_text(encoding="utf-8"))
