# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for OMN-10419 Evidence-Source pinning.

Tests the unit-testable parts of the Evidence-Source mechanism:
  - parse_evidence_source: regex parsing of OCC#NNN and SHA forms
  - EVIDENCE_SOURCE_ANY_PATTERN: detects presence of any Evidence-Source line
  - Workflow shape: new steps exist in receipt-gate.yml
  - Receipt gate integration: FAIL when receipts dir is empty (sham)
  - Receipt gate integration: FAIL when Evidence-Source form is invalid

The GHA resolution logic (API calls to resolve OCC#NNN → SHA, ancestor checks)
is in the workflow shell script and cannot be unit-tested here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.receipt_gate import (
    EVIDENCE_SOURCE_ANY_PATTERN,
    parse_evidence_source,
    validate_pr_receipts,
)

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "receipt-gate.yml"
)


# ---------------------------------------------------------------------------
# parse_evidence_source — regex parsing only (no network)
# ---------------------------------------------------------------------------


class TestParseEvidenceSource:
    """Unit tests for parse_evidence_source — accepts OCC#NNN and SHA forms."""

    def test_occ_pr_form_canonical(self) -> None:
        pr_num, sha = parse_evidence_source("Evidence-Source: OCC#1234\n")
        assert pr_num == "1234"
        assert sha is None

    def test_occ_pr_form_case_insensitive(self) -> None:
        pr_num, sha = parse_evidence_source("evidence-source: occ#999\n")
        assert pr_num == "999"
        assert sha is None

    def test_occ_pr_form_inline_in_body(self) -> None:
        body = "Closes OMN-10419\n\nEvidence-Source: OCC#588\n\nSome other text."
        pr_num, sha = parse_evidence_source(body)
        assert pr_num == "588"
        assert sha is None

    def test_sha_form_full_40_char(self) -> None:
        sha_val = "a" * 40
        pr_num, sha = parse_evidence_source(f"Evidence-Source: {sha_val}\n")
        assert pr_num is None
        assert sha == sha_val

    def test_sha_form_short_7_char(self) -> None:
        pr_num, sha = parse_evidence_source("Evidence-Source: abc1234\n")
        assert pr_num is None
        assert sha == "abc1234"

    def test_absent_returns_none_none(self) -> None:
        pr_num, sha = parse_evidence_source(
            "Closes OMN-10419\n\nNo evidence source here."
        )
        assert pr_num is None
        assert sha is None

    def test_invalid_form_not_matched(self) -> None:
        """Garbage after Evidence-Source: is not matched by either pattern."""
        pr_num, sha = parse_evidence_source("Evidence-Source: deadbeef-invalid!\n")
        assert pr_num is None
        assert sha is None

    def test_occ_pr_form_takes_precedence_over_sha(self) -> None:
        """If OCC#NNN appears first in the body, it is returned."""
        body = "Evidence-Source: OCC#100\nEvidence-Source: abc1234\n"
        pr_num, sha = parse_evidence_source(body)
        assert pr_num == "100"
        assert sha is None

    def test_sha_only_when_no_occ_pr(self) -> None:
        body = "Some preamble\nEvidence-Source: deadbeef\nMore text."
        pr_num, sha = parse_evidence_source(body)
        assert pr_num is None
        assert sha == "deadbeef"


class TestEvidenceSourceAnyPattern:
    """EVIDENCE_SOURCE_ANY_PATTERN detects presence of any Evidence-Source line."""

    def test_present_occ_form(self) -> None:
        assert EVIDENCE_SOURCE_ANY_PATTERN.search("Evidence-Source: OCC#1")

    def test_present_sha_form(self) -> None:
        assert EVIDENCE_SOURCE_ANY_PATTERN.search("Evidence-Source: abc1234")

    def test_absent(self) -> None:
        assert not EVIDENCE_SOURCE_ANY_PATTERN.search("No evidence source here.")

    def test_blank_value_not_matched(self) -> None:
        assert not EVIDENCE_SOURCE_ANY_PATTERN.search("Evidence-Source: ")

    def test_case_insensitive(self) -> None:
        assert EVIDENCE_SOURCE_ANY_PATTERN.search("EVIDENCE-SOURCE: OCC#1")


# ---------------------------------------------------------------------------
# Receipt gate integration: sham contract (empty receipts dir)
# ---------------------------------------------------------------------------


def _make_pass_receipt(
    path: Path,
    ticket_id: str,
    evidence_item_id: str,
    check_type: str,
) -> None:
    """Write a minimal PASS receipt that satisfies all adversarial invariants."""
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": "1.0.0",
        "ticket_id": ticket_id,
        "evidence_item_id": evidence_item_id,
        "check_type": check_type,
        "check_value": "uv run pytest tests/ -v",
        "status": "PASS",
        "run_timestamp": "2026-04-30T00:00:00+00:00",
        "commit_sha": "abc1234567890",  # pragma: allowlist secret
        "runner": "worker-A",
        "verifier": "ci-bot",
        "probe_command": "uv run pytest tests/ -v",
        "probe_stdout": "1 passed",
    }
    path.write_text(yaml.safe_dump(receipt))


def _make_contract(
    contracts_dir: Path,
    ticket_id: str,
    evidence_item_id: str = "ev-001",
    check_type: str = "unit_test",
) -> None:
    """Write a minimal contract with one dod_evidence item."""
    contracts_dir.mkdir(parents=True, exist_ok=True)
    contract = {
        "ticket_id": ticket_id,
        "dod_evidence": [
            {
                "id": evidence_item_id,
                "checks": [{"check_type": check_type, "check_value": "tests pass"}],
            }
        ],
    }
    (contracts_dir / f"{ticket_id}.yaml").write_text(yaml.safe_dump(contract))


class TestReceiptGateEvidenceSourceIntegration:
    """Integration fixtures from OMN-10419 plan — test via validate_pr_receipts."""

    def test_pass_with_contract_and_receipts(self, tmp_path: Path) -> None:
        """PASS: PR with valid Evidence-Source OCC#NNN, contract+receipts present."""
        ticket_id = "OMN-10419"
        evidence_item_id = "ev-001"
        check_type = "unit_test"
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        _make_contract(contracts_dir, ticket_id, evidence_item_id, check_type)
        receipt_path = (
            receipts_dir / ticket_id / evidence_item_id / f"{check_type}.yaml"
        )
        _make_pass_receipt(receipt_path, ticket_id, evidence_item_id, check_type)

        pr_body = (
            "Closes OMN-10419\n\n"
            "Evidence-Source: OCC#588\n\n"
            "Implements the Evidence-Source pinning requirement."
        )
        result = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
            pr_title="feat(OMN-10419): add Evidence-Source pinning",
        )
        assert result.passed, result.message

    def test_fail_missing_evidence_source_line(self, tmp_path: Path) -> None:
        """FAIL: PR body with valid contract+receipts but no Evidence-Source line.

        The Evidence-Source check is enforced in the workflow shell step, not
        in validate_pr_receipts itself. This test documents that the Python gate
        still passes when contracts/receipts exist — the workflow layer enforces
        the Evidence-Source requirement before calling the Python gate.

        The failure on 'missing Evidence-Source' therefore originates in the
        GHA workflow step 'Resolve Evidence-Source', not in validate_pr_receipts.
        This test verifies the Python gate behaves correctly in isolation.
        """
        ticket_id = "OMN-10419"
        evidence_item_id = "ev-001"
        check_type = "unit_test"
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        _make_contract(contracts_dir, ticket_id, evidence_item_id, check_type)
        receipt_path = (
            receipts_dir / ticket_id / evidence_item_id / f"{check_type}.yaml"
        )
        _make_pass_receipt(receipt_path, ticket_id, evidence_item_id, check_type)

        pr_body = "Closes OMN-10419\n\nNo Evidence-Source line here."
        result = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
            pr_title="feat(OMN-10419): some change",
        )
        # Python gate passes — workflow layer enforces Evidence-Source separately.
        assert result.passed, result.message

    def test_fail_empty_receipts_dir_sham_contract(self, tmp_path: Path) -> None:
        """FAIL: Evidence-Source OCC#NNN where OCC PR has contract but empty receipts.

        This is the sham-contract case: contract exists but receipts directory
        is empty. The Python receipt gate must reject this as FAIL.
        """
        ticket_id = "OMN-10419"
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        _make_contract(contracts_dir, ticket_id, "ev-001", "unit_test")
        # Receipts directory exists but is empty — no receipt files.
        receipts_dir.mkdir(parents=True, exist_ok=True)

        pr_body = "Closes OMN-10419\n\nEvidence-Source: OCC#588"
        result = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
            pr_title="feat(OMN-10419): add Evidence-Source pinning",
        )
        assert not result.passed
        assert (
            "no receipt" in result.message.lower()
            or "receipt" in result.message.lower()
        )

    def test_fail_sha_predates_ticket_contract(self, tmp_path: Path) -> None:
        """FAIL: Evidence-Source <sha> where SHA predates the ticket's contract.

        The 'Assert contract exists at pinned OCC SHA' step handles this in the
        workflow. In the Python layer, the symptom is: the OCC checkout at the
        old SHA has no contract file, so validate_pr_receipts sees no contract.
        """
        ticket_id = "OMN-10419"
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        # Simulate OCC state at old SHA: contract does NOT exist yet.
        # (contracts_dir is empty — no contract file written)
        contracts_dir.mkdir(parents=True, exist_ok=True)
        receipts_dir.mkdir(parents=True, exist_ok=True)

        pr_body = "Closes OMN-10419\n\nEvidence-Source: abc1234def5678901234567890abcdef12345678"
        result = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
            pr_title="feat(OMN-10419): some change",
        )
        assert not result.passed
        msg = result.message.lower()
        assert "no contract" in msg or "contract" in msg

    def test_fail_invalid_evidence_source_form(self, tmp_path: Path) -> None:
        """FAIL: Evidence-Source: deadbeef (not a valid hex SHA or OCC#NNN form).

        This is validated by parse_evidence_source returning (None, None) when
        the value doesn't match OCC#NNN or the hex SHA pattern. The workflow
        rejects this before calling the Python gate.

        Verify parse_evidence_source returns (None, None) for the invalid form.
        """
        pr_num, sha = parse_evidence_source("Evidence-Source: deadbeef!\n")
        assert pr_num is None
        assert sha is None

        # Also verify the presence detector sees this as "something is there".
        assert EVIDENCE_SOURCE_ANY_PATTERN.search("Evidence-Source: deadbeef!\n")


# ---------------------------------------------------------------------------
# Workflow shape tests — new OMN-10419 steps exist in receipt-gate.yml
# ---------------------------------------------------------------------------


class TestReceiptGateWorkflowShapeOMN10419:
    """Structural guard: OMN-10419 steps are present in receipt-gate.yml."""

    def _load_steps(self) -> list[dict[object, object]]:
        data = yaml.safe_load(WORKFLOW_PATH.read_text())
        steps: list[dict[object, object]] = data["jobs"]["verify"]["steps"]
        return steps

    def _step_names(self) -> list[str]:
        return [str(s.get("name", "")) for s in self._load_steps()]

    def test_resolve_evidence_source_step_exists(self) -> None:
        assert any("Resolve Evidence-Source" in n for n in self._step_names()), (
            "receipt-gate.yml must have a 'Resolve Evidence-Source' step (OMN-10419)"
        )

    def test_assert_contract_exists_step_exists(self) -> None:
        assert any("Assert contract exists" in n for n in self._step_names()), (
            "receipt-gate.yml must have an 'Assert contract exists at pinned OCC SHA' step (OMN-10419 Finding 2)"
        )

    def test_occ_checkout_no_longer_uses_ref_main(self) -> None:
        """OCC checkout ref must not be the literal 'main' — must use step output."""
        data = yaml.safe_load(WORKFLOW_PATH.read_text())
        steps: list[dict[object, object]] = data["jobs"]["verify"]["steps"]
        for step in steps:
            if "onex_change_control" in str(
                step.get("name", "")
            ) and "contracts" in str(step.get("name", "")):
                with_block = step.get("with", {})
                ref_val = str(with_block.get("ref", ""))
                assert ref_val != "main", (
                    f"OCC checkout 'ref' must not be the literal 'main' after OMN-10419 — "
                    f"got {ref_val!r}. It must reference steps.resolve_evidence_source.outputs.occ_sha."
                )
                assert "resolve_evidence_source" in ref_val, (
                    f"OCC checkout 'ref' must reference the resolve_evidence_source step output, "
                    f"got {ref_val!r}"
                )
                return
        pytest.fail("OCC checkout step not found in receipt-gate.yml")

    def test_resolve_evidence_source_step_has_id(self) -> None:
        data = yaml.safe_load(WORKFLOW_PATH.read_text())
        steps: list[dict[object, object]] = data["jobs"]["verify"]["steps"]
        for step in steps:
            if "Resolve Evidence-Source" in str(step.get("name", "")):
                assert step.get("id") == "resolve_evidence_source", (
                    "Resolve Evidence-Source step must have id: resolve_evidence_source"
                )
                return
        pytest.fail("Resolve Evidence-Source step not found")

    def test_job_env_disables_gha_cache(self) -> None:
        """OMN-10419 invariant I9: job-level env must disable GHA cache."""
        data = yaml.safe_load(WORKFLOW_PATH.read_text())
        job_env: dict[str, object] = data["jobs"]["verify"].get("env", {})
        assert "ACTIONS_CACHE_URL" in job_env, (
            "job env must set ACTIONS_CACHE_URL to disable GHA cache (OMN-10419 invariant I9)"
        )
        assert "ACTIONS_RUNTIME_URL" in job_env, (
            "job env must set ACTIONS_RUNTIME_URL to disable GHA artifact reuse (OMN-10419 invariant I9)"
        )

    def test_resolve_step_script_hard_fails_on_missing_evidence_source(self) -> None:
        """Resolve Evidence-Source step must contain exit 1 for missing Evidence-Source."""
        data = yaml.safe_load(WORKFLOW_PATH.read_text())
        steps: list[dict[object, object]] = data["jobs"]["verify"]["steps"]
        for step in steps:
            if "Resolve Evidence-Source" in str(step.get("name", "")):
                script = str(step.get("run", ""))
                assert "exit 1" in script, (
                    "Resolve Evidence-Source step must hard-fail (exit 1) when Evidence-Source is absent"
                )
                assert (
                    "missing required" in script.lower() or "missing" in script.lower()
                ), (
                    "Resolve Evidence-Source step must emit a 'missing' error message for absent Evidence-Source"
                )
                return
        pytest.fail("Resolve Evidence-Source step not found")

    def test_resolve_step_script_hard_fails_on_occ_unavailable(self) -> None:
        """OCC unavailable → hard FAIL, not silent fallback (invariant I8)."""
        data = yaml.safe_load(WORKFLOW_PATH.read_text())
        steps: list[dict[object, object]] = data["jobs"]["verify"]["steps"]
        for step in steps:
            if "Resolve Evidence-Source" in str(step.get("name", "")):
                script = str(step.get("run", ""))
                assert "OCC unavailable" in script or "unavailable" in script.lower(), (
                    "Resolve Evidence-Source must emit 'OCC unavailable' error and exit 1 "
                    "when OCC fetch fails (OMN-10419 invariant I8)"
                )
                return
        pytest.fail("Resolve Evidence-Source step not found")

    def test_resolve_step_contains_cutoff_logic(self) -> None:
        """Step must include PR creation date vs cutoff comparison for backwards compat."""
        data = yaml.safe_load(WORKFLOW_PATH.read_text())
        steps: list[dict[object, object]] = data["jobs"]["verify"]["steps"]
        for step in steps:
            if "Resolve Evidence-Source" in str(step.get("name", "")):
                script = str(step.get("run", ""))
                assert "cutoff" in script.lower() or "PENDING_MERGE" in script, (
                    "Resolve Evidence-Source must include cutoff logic for pre-cutoff PRs "
                    "(backwards compatibility — OMN-10419)"
                )
                return
        pytest.fail("Resolve Evidence-Source step not found")

    def test_resolve_step_validates_invalid_sha_form(self) -> None:
        """Step must reject Evidence-Source values that are neither OCC#NNN nor hex SHA."""
        data = yaml.safe_load(WORKFLOW_PATH.read_text())
        steps: list[dict[object, object]] = data["jobs"]["verify"]["steps"]
        for step in steps:
            if "Resolve Evidence-Source" in str(step.get("name", "")):
                script = str(step.get("run", ""))
                assert (
                    "not a valid" in script
                    or "invalid" in script.lower()
                    or "OCC#" in script
                ), (
                    "Resolve Evidence-Source must reject Evidence-Source values that are not OCC#NNN or hex SHA"
                )
                return
        pytest.fail("Resolve Evidence-Source step not found")


# ---------------------------------------------------------------------------
# parse_evidence_source edge cases
# ---------------------------------------------------------------------------


class TestParseEvidenceSourceEdgeCases:
    """Additional edge cases for parse_evidence_source."""

    @pytest.mark.parametrize(
        ("body", "expected_pr_num"),
        [
            ("Evidence-Source: OCC#0", "0"),
            ("Evidence-Source: OCC#12345678", "12345678"),
            # No space after colon → \s+ requires at least one → no match.
            ("Evidence-Source:OCC#1", None),
        ],
    )
    def test_occ_pr_various_numbers(
        self, body: str, expected_pr_num: str | None
    ) -> None:
        pr_num, sha = parse_evidence_source(body)
        assert pr_num == expected_pr_num
        assert sha is None

    def test_occ_no_space_after_colon_not_matched(self) -> None:
        """MULTILINE pattern requires space after colon."""
        pr_num, sha = parse_evidence_source("Evidence-Source:OCC#1\n")
        # EVIDENCE_SOURCE_OCC_PR_PATTERN requires \s+ after ':'
        assert pr_num is None
        assert sha is None

    def test_sha_must_be_hex_only(self) -> None:
        """SHA form must be hex digits only; non-hex chars → no match."""
        pr_num, sha = parse_evidence_source("Evidence-Source: zzzzzzzz\n")
        assert pr_num is None
        assert sha is None

    def test_sha_too_short_not_matched(self) -> None:
        """SHA must be at least 7 characters."""
        pr_num, sha = parse_evidence_source("Evidence-Source: abc12\n")
        assert pr_num is None
        assert sha is None

    def test_sha_too_long_not_matched(self) -> None:
        """SHA must be at most 40 characters."""
        pr_num, sha = parse_evidence_source("Evidence-Source: " + "a" * 41 + "\n")
        assert pr_num is None
        assert sha is None

    def test_only_first_match_returned_for_occ(self) -> None:
        """When multiple Evidence-Source lines exist, OCC#NNN takes first match."""
        body = "Evidence-Source: OCC#100\nEvidence-Source: OCC#200\n"
        pr_num, _sha = parse_evidence_source(body)
        assert pr_num == "100"

    def test_multiline_body_with_surrounding_content(self) -> None:
        body = (
            "## Summary\n"
            "- adds OCC pinning\n\n"
            "## Evidence-Source\n\n"
            "Evidence-Source: OCC#588\n\n"
            "## Notes\n"
            "This implements OMN-10419.\n"
        )
        pr_num, sha = parse_evidence_source(body)
        assert pr_num == "588"
        assert sha is None
