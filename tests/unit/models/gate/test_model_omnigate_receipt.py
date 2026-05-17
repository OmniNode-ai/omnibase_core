# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for OmniGate receipt models."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.gate.receipt_canonical import (
    canonical_receipt_payload,
    compute_receipt_schema_fingerprint,
)
from omnibase_core.models.gate import (
    ModelOmniGateCheckResult,
    ModelOmniGateReceipt,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _receipt(
    *,
    checks: tuple[ModelOmniGateCheckResult, ...] = (),
    sigstore_bundle_json: str | None = None,
) -> ModelOmniGateReceipt:
    return ModelOmniGateReceipt(
        schema_version=ModelSemVer(major=1, minor=0, patch=0),
        project_name="my-project",
        project_url="https://github.com/org/repo",
        repository_id="123456789",
        base_sha="a" * 40,
        head_sha="b" * 40,
        commit_sha="b" * 40,
        diff_hash="sha256:" + "c" * 64,
        config_hash="sha256:" + "d" * 64,
        receipt_schema_fingerprint="sha256:" + "e" * 64,
        branch="fix/something",
        timestamp=datetime(2026, 5, 17, 12, 0, tzinfo=UTC),
        checks=checks,
        signer_identity="https://github.com/org/repo/.github/workflows/omnigate.yml@refs/heads/main",
        signer_issuer="https://token.actions.githubusercontent.com",
        sigstore_bundle_json=sigstore_bundle_json,
    )


@pytest.mark.unit
class TestModelOmniGateReceipt:
    def test_valid_receipt_with_authority_fields(self) -> None:
        receipt = _receipt(
            checks=(
                ModelOmniGateCheckResult(
                    name="lint",
                    command="npm run lint",
                    status=EnumReceiptStatus.PASS,
                    duration_ms=1200,
                    stdout_preview="All files pass linting",
                    stdout_hash="sha256:" + "f" * 64,
                ),
            ),
        )

        assert receipt.repository_identifier == "123456789"
        assert receipt.repository_id == "123456789"
        assert receipt.base_sha == "a" * 40
        assert receipt.head_sha == receipt.commit_sha
        assert receipt.diff_hash.startswith("sha256:")
        assert receipt.config_hash.startswith("sha256:")
        assert receipt.receipt_schema_fingerprint.startswith("sha256:")
        assert receipt.no_blocking_checks_failed(advisory_blocks=False) is True

    def test_failed_check_is_valid_model_but_blocks(self) -> None:
        receipt = _receipt(
            checks=(
                ModelOmniGateCheckResult(
                    name="test",
                    command="npm test",
                    status=EnumReceiptStatus.FAIL,
                    duration_ms=5000,
                ),
            ),
        )

        assert receipt.checks[0].status == EnumReceiptStatus.FAIL
        assert receipt.no_blocking_checks_failed(advisory_blocks=False) is False

    def test_advisory_check_respects_trusted_policy(self) -> None:
        receipt = _receipt(
            checks=(
                ModelOmniGateCheckResult(
                    name="license",
                    command="npm run license",
                    status=EnumReceiptStatus.ADVISORY,
                    duration_ms=100,
                ),
            ),
        )

        assert receipt.no_blocking_checks_failed(advisory_blocks=False) is True
        assert receipt.no_blocking_checks_failed(advisory_blocks=True) is False

    def test_pending_check_blocks(self) -> None:
        receipt = _receipt(
            checks=(
                ModelOmniGateCheckResult(
                    name="integration",
                    command="npm run integration",
                    status=EnumReceiptStatus.PENDING,
                    duration_ms=0,
                ),
            ),
        )

        assert receipt.no_blocking_checks_failed(advisory_blocks=False) is False

    def test_hash_fields_must_be_sha256_prefixed(self) -> None:
        with pytest.raises(ValidationError):
            ModelOmniGateReceipt(
                schema_version=ModelSemVer(major=1, minor=0, patch=0),
                project_name="test",
                project_url="https://github.com/org/repo",
                repository_id="123456789",
                base_sha="a" * 40,
                head_sha="b" * 40,
                commit_sha="b" * 40,
                diff_hash="not-a-hash",
                config_hash="sha256:" + "d" * 64,
                receipt_schema_fingerprint="sha256:" + "e" * 64,
                branch="main",
                timestamp=datetime(2026, 5, 17, 12, 0, tzinfo=UTC),
            )

    def test_git_sha_fields_must_be_full_hex_sha(self) -> None:
        with pytest.raises(ValidationError):
            ModelOmniGateReceipt(
                schema_version=ModelSemVer(major=1, minor=0, patch=0),
                project_name="test",
                project_url="https://github.com/org/repo",
                repository_id="123456789",
                base_sha="a" * 39,
                head_sha="b" * 40,
                commit_sha="b" * 40,
                diff_hash="sha256:" + "c" * 64,
                config_hash="sha256:" + "d" * 64,
                receipt_schema_fingerprint="sha256:" + "e" * 64,
                branch="main",
                timestamp=datetime(2026, 5, 17, 12, 0, tzinfo=UTC),
            )

    def test_stdout_hash_must_be_sha256_prefixed(self) -> None:
        with pytest.raises(ValidationError):
            ModelOmniGateCheckResult(
                name="lint",
                command="npm run lint",
                status=EnumReceiptStatus.PASS,
                duration_ms=100,
                stdout_hash="bad",
            )

    def test_sigstore_bundle_json_is_string(self) -> None:
        receipt = _receipt(sigstore_bundle_json='{"mediaType":"application/json"}')

        assert isinstance(receipt.sigstore_bundle_json, str)

    def test_frozen(self) -> None:
        receipt = _receipt()

        with pytest.raises(ValidationError):
            receipt.project_name = "changed"  # type: ignore[misc]

    def test_canonical_payload_excludes_signature_by_default(self) -> None:
        receipt = _receipt(sigstore_bundle_json='{"bundle":"signed"}')

        payload = canonical_receipt_payload(receipt)
        decoded = json.loads(payload.decode("utf-8"))

        assert "sigstore_bundle_json" not in decoded
        assert decoded["repository_id"] == "123456789"

    def test_canonical_payload_can_include_signature(self) -> None:
        receipt = _receipt(sigstore_bundle_json='{"bundle":"signed"}')

        payload = canonical_receipt_payload(receipt, exclude_signature=False)
        decoded = json.loads(payload.decode("utf-8"))

        assert decoded["sigstore_bundle_json"] == '{"bundle":"signed"}'

    def test_canonical_payload_is_deterministic(self) -> None:
        receipt = _receipt()

        assert canonical_receipt_payload(receipt) == canonical_receipt_payload(receipt)

    def test_schema_fingerprint_is_deterministic_sha256(self) -> None:
        fingerprint = compute_receipt_schema_fingerprint()

        assert fingerprint == compute_receipt_schema_fingerprint()
        assert fingerprint.startswith("sha256:")
        assert len(fingerprint) == len("sha256:") + 64
