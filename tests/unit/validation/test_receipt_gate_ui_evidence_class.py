# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""UI evidence-class gate tests for the Receipt-Gate (OMN-13024, A-2).

UI / dashboard evidence cannot be proven by a direct HTTP probe (curl / wget /
httpx) against a backend port — that proves the API responds, not that the
dashboard renders the data through its proxy origin. UI-class receipts must
come from a Playwright run whose captured network trace originates from the
dashboard proxy origin, not a direct backend port.

These tests write a literal receipt YAML to disk and assert the literal gate
output, per the "literal command + literal stdout assertions" acceptance
criterion.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.governance.enum_evidence_class import EnumEvidenceClass
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.validation.validator_receipt_gate import (
    classify_evidence_class,
    validate_pr_receipts,
)

_UI_FAILURE_SUBSTRING = "ui-class evidence requires Playwright proxy-origin trace"

# A Playwright network trace whose /api request shares the page origin
# (localhost:3000) — i.e. proxied / same-origin, not a direct backend port.
_PROXY_ORIGIN_TRACE = (
    "Running 1 test using 1 worker\n"
    "[doc] GET http://localhost:3000/dashboard 200\n"
    "[xhr] GET http://localhost:3000/api/delegation/rows 200\n"
    "  1 passed (3.2s)\n"
)

# A trace whose /api request targets a different port (3001) than the page
# origin (3000) — a direct backend-port call that bypasses the proxy.
_DIRECT_BACKEND_TRACE = (
    "Running 1 test using 1 worker\n"
    "[doc] GET http://localhost:3000/dashboard 200\n"
    "[xhr] GET http://localhost:3001/api/delegation/rows 200\n"
    "  1 passed (3.2s)\n"
)


def _write_contract(contracts_dir: Path, ticket_id: str) -> None:
    contracts_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "ticket_id": ticket_id,
        "schema_version": "1.0.0",
        "summary": "test",
        "dod_evidence": [
            {
                "id": "dod-001",
                "description": "ui dashboard check",
                "checks": [
                    {"check_type": "command", "check_value": "render dashboard"}
                ],
            }
        ],
    }
    (contracts_dir / f"{ticket_id}.yaml").write_text(yaml.safe_dump(body))


def _receipt_dict(
    *,
    ticket_id: str = "OMN-13024",
    probe_command: str,
    probe_stdout: str,
    evidence_class: str | None = None,
    runner: str = "worker-A",
    verifier: str = "foreground-claude-X",
    status: str = "PASS",
) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": ticket_id,
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "render dashboard",
        "status": status,
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": runner,
        "verifier": verifier,
        "probe_command": probe_command,
        "probe_stdout": probe_stdout,
    }
    if evidence_class is not None:
        data["evidence_class"] = evidence_class
    return data


def _write_receipt(receipts_dir: Path, ticket_id: str, data: dict[str, object]) -> Path:
    p = receipts_dir / ticket_id / "dod-001" / "command.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data))
    return p


@pytest.mark.unit
class TestUiEvidenceClassModelField:
    """The receipt model carries an optional evidence_class field."""

    def test_evidence_class_defaults_to_none(self) -> None:
        receipt = ModelDodReceipt.model_validate(
            _receipt_dict(
                probe_command="echo ok",
                probe_stdout="ok\n",
            )
        )
        assert receipt.evidence_class is None

    def test_evidence_class_parses_ui_dashboard(self) -> None:
        receipt = ModelDodReceipt.model_validate(
            _receipt_dict(
                probe_command="npx playwright test",
                probe_stdout=_PROXY_ORIGIN_TRACE,
                evidence_class="ui_dashboard",
            )
        )
        assert receipt.evidence_class is EnumEvidenceClass.UI_DASHBOARD


@pytest.mark.unit
class TestClassifyEvidenceClass:
    """Classification precedence: explicit field wins, else infer from command."""

    def test_curl_without_playwright_infers_ui_dashboard(self) -> None:
        receipt = ModelDodReceipt.model_validate(
            _receipt_dict(
                probe_command="curl http://localhost:3001/api/delegation/rows",
                probe_stdout='{"rows": []}\n',
            )
        )
        assert classify_evidence_class(receipt) is EnumEvidenceClass.UI_DASHBOARD

    def test_playwright_command_is_unclassified_without_explicit_field(self) -> None:
        receipt = ModelDodReceipt.model_validate(
            _receipt_dict(
                probe_command="npx playwright test",
                probe_stdout=_PROXY_ORIGIN_TRACE,
            )
        )
        assert classify_evidence_class(receipt) is EnumEvidenceClass.UNCLASSIFIED

    def test_explicit_backend_overrides_curl_heuristic(self) -> None:
        receipt = ModelDodReceipt.model_validate(
            _receipt_dict(
                probe_command="curl http://localhost:8085/v1/introspection",
                probe_stdout='{"ok": true}\n',
                evidence_class="backend",
            )
        )
        assert classify_evidence_class(receipt) is EnumEvidenceClass.BACKEND


@pytest.mark.unit
class TestUiEvidenceClassGate:
    """The gate rejects UI-class evidence without a Playwright proxy-origin trace."""

    def test_curl_ui_class_evidence_fails(self, tmp_path: Path) -> None:
        """DoD: curl probe with no Playwright reference fails the gate."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-13024")
        _write_receipt(
            receipts,
            "OMN-13024",
            _receipt_dict(
                probe_command="curl http://localhost:3001/api/delegation/rows",
                probe_stdout='{"rows": [{"id": 1}]}\n',
            ),
        )

        result = validate_pr_receipts(
            pr_body="Closes OMN-13024",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert _UI_FAILURE_SUBSTRING in result.message

    def test_explicit_ui_class_curl_fails(self, tmp_path: Path) -> None:
        """An explicit evidence_class=ui_dashboard curl receipt fails the gate."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-13024")
        _write_receipt(
            receipts,
            "OMN-13024",
            _receipt_dict(
                probe_command="httpx http://localhost:3001/api/rows",
                probe_stdout='{"rows": []}\n',
                evidence_class="ui_dashboard",
            ),
        )

        result = validate_pr_receipts(
            pr_body="Closes OMN-13024",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert _UI_FAILURE_SUBSTRING in result.message

    def test_playwright_proxy_origin_trace_passes(self, tmp_path: Path) -> None:
        """DoD: Playwright probe with a proxy-origin trace passes the gate."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-13024")
        _write_receipt(
            receipts,
            "OMN-13024",
            _receipt_dict(
                probe_command="npx playwright test tests/dashboard/delegation.spec.ts",
                probe_stdout=_PROXY_ORIGIN_TRACE,
                evidence_class="ui_dashboard",
            ),
        )

        result = validate_pr_receipts(
            pr_body="Closes OMN-13024",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed, result.message

    def test_playwright_direct_backend_port_trace_fails(self, tmp_path: Path) -> None:
        """A Playwright run whose trace hits a direct backend port fails."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-13024")
        _write_receipt(
            receipts,
            "OMN-13024",
            _receipt_dict(
                probe_command="npx playwright test tests/dashboard/delegation.spec.ts",
                probe_stdout=_DIRECT_BACKEND_TRACE,
                evidence_class="ui_dashboard",
            ),
        )

        result = validate_pr_receipts(
            pr_body="Closes OMN-13024",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert _UI_FAILURE_SUBSTRING in result.message

    def test_backend_class_curl_escapes_ui_gate(self, tmp_path: Path) -> None:
        """An explicit evidence_class=backend curl receipt is not UI-gated."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-13024")
        _write_receipt(
            receipts,
            "OMN-13024",
            _receipt_dict(
                probe_command="curl http://localhost:8085/v1/introspection/manifest",
                probe_stdout='{"manifest": {"version": "0.37.0"}}\n',
                evidence_class="backend",
            ),
        )

        result = validate_pr_receipts(
            pr_body="Closes OMN-13024",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed, result.message

    def test_non_ui_command_receipt_unaffected(self, tmp_path: Path) -> None:
        """A plain command receipt (no HTTP client) is not UI-gated."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-13024")
        _write_receipt(
            receipts,
            "OMN-13024",
            _receipt_dict(
                probe_command="uv run pytest tests/unit -q",
                probe_stdout="120 passed\n",
            ),
        )

        result = validate_pr_receipts(
            pr_body="Closes OMN-13024",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed, result.message
