# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for backend_secret_discipline validator (OMN-13290).

Ported from omnimarket tests/ci/test_check_backend_secret_discipline.py
(OMN-12971) and extended for the repo-agnostic core port. Covers:

Positive (clean) cases:
- a clean config with a logical secret_ref → PASS
- a clean config with credential_ref (ADC) → PASS
- a local-tier backend with no ref → PASS
- a no-secret backend id (cli-claude) with no ref → PASS
- a non-backends config file scanned for literals only → PASS
- the suppression token on a literal line → suppressed

Negative (violation) cases:
- literal PEM private key → FAIL
- literal Google API key → FAIL
- literal bearer token → FAIL
- service-account JSON markers → FAIL
- cloud backend missing a logical ref → FAIL
- mutually exclusive ADC + api-key auth on one backend → FAIL
- a non-mapping `backends:` value → FAIL
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators import backend_secret_discipline as mod

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Pure literal-credential scan
# ---------------------------------------------------------------------------


def test_literal_pem_credential_detected() -> None:
    leaked = 'endpoint_url: null\n  service_account: "-----BEGIN PRIVATE KEY-----MIIabc"\n'  # pragma: allowlist secret
    findings = mod.scan_literal_credentials("fake.yaml", leaked)
    assert any("pem-private-key" in f.message for f in findings)


def test_literal_google_api_key_detected() -> None:
    leaked = 'api_key: "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"\n'  # pragma: allowlist secret
    findings = mod.scan_literal_credentials("fake.yaml", leaked)
    assert any("google-api-key" in f.message for f in findings)


def test_literal_bearer_token_detected() -> None:
    leaked = 'authorization: "Bearer abcdef0123456789ABCDEF"\n'
    findings = mod.scan_literal_credentials("fake.yaml", leaked)
    assert any("bearer-token" in f.message for f in findings)


def test_service_account_json_markers_detected() -> None:
    leaked = '{"private_key": "x", "client_email": "y@z.iam"}\n'
    findings = mod.scan_literal_credentials("fake.yaml", leaked)
    labels = {f.message for f in findings}
    assert any("service-account-private-key" in m for m in labels)
    assert any("service-account-client-email" in m for m in labels)


def test_clean_literal_scan_passes() -> None:
    clean = 'secret_ref: "llm.vertex.access_token"\nendpoint_url: null\n'  # pragma: allowlist secret
    assert mod.scan_literal_credentials("fake.yaml", clean) == []


def test_suppression_token_suppresses_literal() -> None:
    leaked = (
        'api_key: "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"  '  # pragma: allowlist secret
        "# backend-secret-ok: synthetic test fixture\n"
    )
    assert mod.scan_literal_credentials("fake.yaml", leaked) == []


# ---------------------------------------------------------------------------
# Pure backend-ref scan
# ---------------------------------------------------------------------------


def test_cloud_backend_missing_ref_detected() -> None:
    data = {
        "backends": [
            {
                "backend_id": "cloud-rogue",
                "tier": "cheap_cloud",
                "endpoint_url": "https://example.com/v1/chat/completions",
            }
        ]
    }
    findings = mod.scan_backends("fake.yaml", data)
    assert any("requires a logical secret reference" in f.message for f in findings)


def test_mutually_exclusive_auth_detected() -> None:
    data = {
        "backends": [
            {
                "backend_id": "cloud-both",
                "tier": "cheap_cloud",
                "credential_ref": "llm.vertex.adc",
                "secret_ref": "llm.gemini.api_key",  # pragma: allowlist secret
            }
        ]
    }
    findings = mod.scan_backends("fake.yaml", data)
    assert any("mutually exclusive" in f.message for f in findings)


def test_cloud_backend_with_secret_ref_passes() -> None:
    data = {
        "backends": [
            {
                "backend_id": "cloud-gemini-flash",
                "tier": "cheap_cloud",
                "secret_ref": "llm.gemini.api_key",  # pragma: allowlist secret
            }
        ]
    }
    assert mod.scan_backends("fake.yaml", data) == []


def test_cloud_backend_with_credential_ref_passes() -> None:
    data = {
        "backends": [
            {
                "backend_id": "cloud-vertex-gemini",
                "tier": "cheap_cloud",
                "credential_ref": "llm.vertex.adc",
            }
        ]
    }
    assert mod.scan_backends("fake.yaml", data) == []


def test_local_backend_no_ref_passes() -> None:
    data = {"backends": [{"backend_id": "local-qwen", "tier": "local"}]}
    assert mod.scan_backends("fake.yaml", data) == []


def test_no_secret_backend_id_passes() -> None:
    data = {
        "backends": [
            {"backend_id": "cli-claude", "tier": "frontier_api"},
            {"backend_id": "cloud-sonnet", "tier": "cheap_cloud"},
        ]
    }
    assert mod.scan_backends("fake.yaml", data) == []


def test_non_mapping_backends_detected() -> None:
    data = {"backends": "not-a-list"}
    findings = mod.scan_backends("fake.yaml", data)
    assert any("backends must be a list" in f.message for f in findings)


# ---------------------------------------------------------------------------
# Path boundary + build_report (I/O)
# ---------------------------------------------------------------------------


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_build_report_clean_bifrost_config_passes(tmp_path: Path) -> None:
    cfg = _write(
        tmp_path / "bifrost_delegation.yaml",
        "backends:\n"
        "  - backend_id: cloud-gemini-flash\n"
        "    tier: cheap_cloud\n"
        "    secret_ref: llm.gemini.api_key\n"
        "  - backend_id: local-qwen\n"
        "    tier: local\n",
    )
    report = mod.build_report([cfg], cwd=tmp_path)
    assert report["passed"], report


def test_build_report_leaked_credential_fails(tmp_path: Path) -> None:
    cfg = _write(
        tmp_path / "leaked.yaml",
        "backends:\n"
        "  - backend_id: cloud-gemini-flash\n"
        "    tier: cheap_cloud\n"
        '    api_key: "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"\n',  # pragma: allowlist secret
    )
    report = mod.build_report([cfg], cwd=tmp_path)
    assert not report["passed"]
    assert report["literal_credential_violations"]


def test_build_report_missing_ref_fails(tmp_path: Path) -> None:
    cfg = _write(
        tmp_path / "delegation.yaml",
        "backends:\n  - backend_id: cloud-rogue\n    tier: frontier_api\n",
    )
    report = mod.build_report([cfg], cwd=tmp_path)
    assert not report["passed"]
    assert report["backend_ref_violations"]


def test_non_backends_config_scanned_for_literals_only(tmp_path: Path) -> None:
    # A plain config file without a `backends:` key is literal-scanned and
    # passes when clean; the backend-ref scan does not apply.
    cfg = _write(
        tmp_path / "routing_tiers.yaml",
        "tiers:\n  - name: local\n  - name: cheap_cloud\n",
    )
    report = mod.build_report([cfg], cwd=tmp_path)
    assert report["passed"], report


def test_non_config_file_ignored(tmp_path: Path) -> None:
    src = _write(
        tmp_path / "module.py",
        'KEY = "AIzaSy0123456789abcdefghijklmnopqrstuvwx"\n',  # pragma: allowlist secret
    )
    report = mod.build_report([src], cwd=tmp_path)
    # .py is not a scanned config suffix → no findings.
    assert report["passed"], report


def test_main_exit_codes(tmp_path: Path) -> None:
    clean = _write(
        tmp_path / "clean.yaml",
        "backends:\n  - backend_id: local-qwen\n    tier: local\n",
    )
    dirty = _write(
        tmp_path / "dirty.yaml",
        "backends:\n  - backend_id: cloud-rogue\n    tier: cheap_cloud\n",
    )
    assert mod.main([str(clean)]) == 0
    assert mod.main([str(dirty)]) == 1
    # No files → scan nothing → pass.
    assert mod.main([]) == 0
