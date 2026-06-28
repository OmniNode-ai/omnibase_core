# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for omnibase_core.gate.receipt_canonical."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import UTC, datetime

import pytest

from omnibase_core.gate.receipt_canonical import (
    _normalize_json,
    canonical_receipt_payload,
    compute_receipt_schema_fingerprint,
)
from omnibase_core.models.gate.model_omnigate_receipt import ModelOmniGateReceipt
from omnibase_core.models.primitives.model_semver import ModelSemVer

pytestmark = pytest.mark.unit

_FAKE_GIT_SHA = "a" * 40
_FAKE_SHA256 = "sha256:" + "b" * 64


def _make_receipt(**kwargs: object) -> ModelOmniGateReceipt:
    """Build a minimal valid ModelOmniGateReceipt for testing."""
    defaults: dict[str, object] = {
        "schema_version": ModelSemVer(major=1, minor=0, patch=0),
        "project_name": "omnibase_core",
        "project_url": "https://github.com/omninode-ai/omnibase_core",
        "repository_id": "OmniNode-ai/omnibase_core",
        "base_sha": _FAKE_GIT_SHA,
        "head_sha": _FAKE_GIT_SHA,
        "commit_sha": _FAKE_GIT_SHA,
        "diff_hash": _FAKE_SHA256,
        "config_hash": _FAKE_SHA256,
        "receipt_schema_fingerprint": _FAKE_SHA256,
        "branch": "main",
        "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return ModelOmniGateReceipt.model_validate(defaults)


class TestNormalizeJson:
    def test_str_nfc_passthrough(self) -> None:
        nfc_str = unicodedata.normalize("NFC", "café")
        result = _normalize_json(nfc_str)
        assert result == nfc_str
        assert unicodedata.is_normalized("NFC", str(result))

    def test_str_nfd_converted_to_nfc(self) -> None:
        nfd_str = unicodedata.normalize("NFD", "café")
        # NFD uses combining characters; NFC fuses them
        assert not unicodedata.is_normalized("NFC", nfd_str)
        result = _normalize_json(nfd_str)
        assert unicodedata.is_normalized("NFC", str(result))
        assert result == unicodedata.normalize("NFC", "café")

    def test_list_recursion_order_preserved(self) -> None:
        result = _normalize_json(["b", "a", 1, None])
        assert result == ["b", "a", 1, None]

    def test_list_nested_str_normalized(self) -> None:
        nfd = unicodedata.normalize("NFD", "résumé")
        result = _normalize_json([nfd])
        assert isinstance(result, list)
        assert result[0] == unicodedata.normalize("NFC", "résumé")

    def test_dict_keys_sorted(self) -> None:
        result = _normalize_json({"z": 1, "a": 2, "m": 3})
        assert isinstance(result, dict)
        assert list(result.keys()) == ["a", "m", "z"]

    def test_dict_values_recursed(self) -> None:
        nfd = unicodedata.normalize("NFD", "naïve")
        result = _normalize_json({"key": nfd})
        assert isinstance(result, dict)
        assert result["key"] == unicodedata.normalize("NFC", "naïve")

    def test_scalar_int_passthrough(self) -> None:
        assert _normalize_json(42) == 42

    def test_scalar_float_passthrough(self) -> None:
        assert _normalize_json(3.14) == 3.14

    def test_scalar_none_passthrough(self) -> None:
        assert _normalize_json(None) is None

    def test_scalar_bool_passthrough(self) -> None:
        assert _normalize_json(True) is True


class TestCanonicalReceiptPayload:
    def test_returns_bytes(self) -> None:
        receipt = _make_receipt()
        result = canonical_receipt_payload(receipt)
        assert isinstance(result, bytes)

    def test_deterministic(self) -> None:
        receipt = _make_receipt()
        r1 = canonical_receipt_payload(receipt)
        r2 = canonical_receipt_payload(receipt)
        assert r1 == r2

    def test_exclude_signature_true_omits_sigstore_bundle_json(self) -> None:
        receipt = _make_receipt(sigstore_bundle_json='{"sigstore": "bundle"}')
        payload = canonical_receipt_payload(receipt, exclude_signature=True)
        assert b"sigstore_bundle_json" not in payload

    def test_exclude_signature_false_includes_sigstore_bundle_json(self) -> None:
        receipt = _make_receipt(sigstore_bundle_json='{"sigstore": "bundle"}')
        payload = canonical_receipt_payload(receipt, exclude_signature=False)
        assert b"sigstore_bundle_json" in payload

    def test_default_exclude_signature_is_true(self) -> None:
        receipt = _make_receipt(sigstore_bundle_json='{"sigstore": "bundle"}')
        default_payload = canonical_receipt_payload(receipt)
        explicit_payload = canonical_receipt_payload(receipt, exclude_signature=True)
        assert default_payload == explicit_payload

    def test_valid_utf8_json_bytes(self) -> None:
        receipt = _make_receipt()
        payload = canonical_receipt_payload(receipt)
        parsed = json.loads(payload)
        assert isinstance(parsed, dict)

    def test_different_receipts_different_bytes(self) -> None:
        r1 = _make_receipt(branch="main")
        r2 = _make_receipt(branch="feature-branch")
        assert canonical_receipt_payload(r1) != canonical_receipt_payload(r2)


class TestComputeReceiptSchemaFingerprint:
    def test_returns_sha256_prefixed_string(self) -> None:
        result = compute_receipt_schema_fingerprint()
        assert result.startswith("sha256:")

    def test_hex_suffix_is_64_chars(self) -> None:
        result = compute_receipt_schema_fingerprint()
        assert re.match(r"^sha256:[0-9a-f]{64}$", result) is not None

    def test_deterministic_across_calls(self) -> None:
        r1 = compute_receipt_schema_fingerprint()
        r2 = compute_receipt_schema_fingerprint()
        assert r1 == r2

    def test_total_length(self) -> None:
        # "sha256:" (7 chars) + 64 hex chars = 71
        result = compute_receipt_schema_fingerprint()
        assert len(result) == 71
