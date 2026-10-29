# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The canonical handle(request) entry of the handlers bound into nodes (OMN-21515)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_ledger_write_target import EnumLedgerWriteTarget
from omnibase_core.handlers.handler_ledger_write_guard import HandlerLedgerWriteGuard
from omnibase_core.models.ledger_write_guard.model_ledger_write_guard_request import (
    ModelLedgerWriteGuardRequest,
)
from omnibase_core.models.nodes.contract_evidence_check.model_contract_check_values_lint_request import (
    ModelContractCheckValuesLintRequest,
)
from omnibase_core.models.nodes.contract_evidence_check.model_contract_compliance_check_request import (
    ModelContractComplianceCheckRequest,
)
from omnibase_core.models.nodes.contract_evidence_check.model_contract_substance_floor_request import (
    ModelContractSubstanceFloorRequest,
)
from omnibase_core.models.ticket.model_done_write_receipt_request import (
    ModelDoneWriteReceiptRequest,
)
from omnibase_core.models.validation.model_shape_gate_independence_request import (
    ModelShapeGateIndependenceRequest,
)
from omnibase_core.models.validation.model_todo_format_request import (
    ModelTodoFormatRequest,
)
from omnibase_core.nodes.node_contract_evidence_check_effect.handler_contract_check_values_lint import (
    HandlerContractCheckValuesLint,
)
from omnibase_core.nodes.node_contract_evidence_check_effect.handler_contract_compliance_check import (
    HandlerContractComplianceCheck,
)
from omnibase_core.nodes.node_contract_evidence_check_effect.handler_contract_substance_floor import (
    HandlerContractSubstanceFloor,
)
from omnibase_core.nodes.node_done_write_receipt_gate_compute.handler_done_write_receipt_gate import (
    HandlerDoneWriteReceiptGate,
)
from omnibase_core.nodes.node_shape_gate_independence_check_effect.handler_shape_gate_independence import (
    HandlerShapeGateIndependence,
)
from omnibase_core.nodes.node_todo_format_check_effect.handler_todo_format import (
    HandlerTodoFormat,
)

pytestmark = pytest.mark.unit


def _contract(tmp_path: Path, check_type: str, check_value: str) -> Path:
    path = tmp_path / "OMN-1.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "ticket_id": "OMN-1",
                "dod_evidence": [
                    {
                        "id": "dod-001",
                        "checks": [
                            {"check_type": check_type, "check_value": check_value}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_ledger_write_guard_refuses_a_canonical_topic_under_a_test_runner() -> None:
    decision = HandlerLedgerWriteGuard().handle(
        ModelLedgerWriteGuardRequest(
            target_kind=EnumLedgerWriteTarget.TOPIC,
            target="onex.evt.omnimarket.work-ledger-row-appended.v1",
        )
    )
    assert decision.refused
    assert decision.signal is not None


def test_ledger_write_guard_admits_a_tmp_file_and_a_loopback_dsn(
    tmp_path: Path,
) -> None:
    guard = HandlerLedgerWriteGuard()
    for kind, target in (
        (EnumLedgerWriteTarget.FILE, str(tmp_path / "ledger.md")),
        (EnumLedgerWriteTarget.DSN, "postgresql://u@localhost/db"),
    ):
        decision = guard.handle(
            ModelLedgerWriteGuardRequest(target_kind=kind, target=target)
        )
        assert not decision.refused


def test_done_write_receipt_gate_refuses_a_ticket_with_no_verdict() -> None:
    decision = HandlerDoneWriteReceiptGate().handle(
        ModelDoneWriteReceiptRequest(
            ticket_id="OMN-1", description="- [ ] AC1: x", verdict=None
        )
    )
    assert not decision.allowed
    assert "no dod_verify verdict" in decision.reason


def test_todo_format_reports_a_bare_marker_and_passes_a_clean_file(
    tmp_path: Path,
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("x = 1  # " + "TO" + "DO fix this\n", encoding="utf-8")
    good = tmp_path / "good.py"
    good.write_text("x = 1\n", encoding="utf-8")
    report = HandlerTodoFormat().handle(
        ModelTodoFormatRequest(paths=(str(bad), str(good)))
    )
    assert [finding.path for finding in report.findings] == [str(bad)]


def test_shape_gate_independence_refuses_a_detector_behind_the_preflight(
    tmp_path: Path,
) -> None:
    workflow = tmp_path / "gate.yml"
    workflow.write_text(
        "name: gate\non: [pull_request]\njobs:\n"
        "  occ-preflight:\n    uses: ./.github/workflows/occ-preflight.yml\n"
        "  canonical-inference-gate:\n    needs: occ-preflight\n"
        "    runs-on: ubuntu-latest\n    steps:\n      - run: echo detector\n",
        encoding="utf-8",
    )
    report = HandlerShapeGateIndependence().handle(
        ModelShapeGateIndependenceRequest(paths=(workflow,))
    )
    assert len(report.findings) == 1


def test_contract_check_values_lint_flags_an_always_true_tail(tmp_path: Path) -> None:
    path = _contract(tmp_path, "command", "uv run pytest tests/x.py || true")
    report = HandlerContractCheckValuesLint().handle(
        ModelContractCheckValuesLintRequest(paths=(path,))
    )
    assert report.findings


def test_contract_check_values_lint_passes_a_fail_closed_check(tmp_path: Path) -> None:
    path = _contract(tmp_path, "command", "uv run pytest tests/x.py")
    report = HandlerContractCheckValuesLint().handle(
        ModelContractCheckValuesLintRequest(paths=(path,))
    )
    assert not report.findings


def test_contract_substance_floor_fails_an_existence_probe_only(tmp_path: Path) -> None:
    path = _contract(
        tmp_path,
        "command",
        "gh pr view ${PR_NUMBER} --repo ${REPO} --json number,state",
    )
    report = HandlerContractSubstanceFloor().handle(
        ModelContractSubstanceFloorRequest(paths=(path,))
    )
    assert [verdict.passed for verdict in report.verdicts] == [False]
    assert "SUBSTANCE FLOOR FAILED" in report.verdicts[0].failure_message


def test_contract_substance_floor_passes_a_test_check(tmp_path: Path) -> None:
    path = _contract(tmp_path, "command", "uv run pytest tests/unit/nodes/x/ -v")
    report = HandlerContractSubstanceFloor().handle(
        ModelContractSubstanceFloorRequest(paths=(path,))
    )
    assert [verdict.passed for verdict in report.verdicts] == [True]


def test_contract_compliance_check_names_a_non_hermetic_command() -> None:
    verdict = HandlerContractComplianceCheck().handle(
        ModelContractComplianceCheckRequest(check_value="ssh host uptime")
    )
    assert verdict.non_hermetic_reason is not None
    hermetic = HandlerContractComplianceCheck().handle(
        ModelContractComplianceCheckRequest(check_value="uv run pytest tests/x.py")
    )
    assert hermetic.non_hermetic_reason is None
