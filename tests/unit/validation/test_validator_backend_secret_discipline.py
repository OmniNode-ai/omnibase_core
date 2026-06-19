# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ValidatorBackendSecretDiscipline (OMN-13305, ported from OMN-12971).

Covers:
- scan_literal_credentials: detects all 7 literal-credential patterns
- scan_bifrost_backends: detects missing secret-ref and mutual-exclusion violations
- build_report_from_files: PASS on clean input, FAIL on violation
- HandlerBackendSecretDisciplineCompute handler: correct protocol properties + async handle
- ModelBackendSecretDisciplineInput / Output: frozen Pydantic models
- CLI entry-point: --json flag, exit codes
- Fail-closed proof: planted SA-JSON private_key → gate red; clean → green

Port equivalence note
---------------------
Pre-port source SHA-256 (omnimarket/scripts/ci/check_backend_secret_discipline.py):
    e2344b5cf9d696b7160ac3cbb9eca9380da4addc854fa5ccf1fd12f5da901aab
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.validation.validator_backend_secret_discipline import (
    HandlerBackendSecretDisciplineCompute,
    ModelBackendSecretDisciplineInput,
    ModelBackendSecretDisciplineOutput,
    build_report_from_files,
    scan_bifrost_backends,
    scan_literal_credentials,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLEAN_BIFROST_YAML = """\
backends:
  - backend_id: cloud-gemini-flash
    tier: cheap_cloud
    secret_ref: llm.gemini.api_key
    endpoint_url: null
  - backend_id: cloud-vertex-gemini
    tier: cheap_frontier
    secret_ref: llm.vertex.access_token
    endpoint_url: null
  - backend_id: local-llm
    tier: local
    endpoint_url: http://localhost:8080/v1/chat/completions
"""

_LEAKED_PEM_YAML = (
    "backends:\n"
    "  - backend_id: cloud-bad\n"
    "    tier: cheap_cloud\n"
    '    private_key: "-----BEGIN PRIVATE KEY-----MIIABC"\n'  # pragma: allowlist secret
)

_LEAKED_SA_PRIVATE_KEY_YAML = (
    "backends:\n"
    "  - backend_id: cloud-bad\n"
    "    tier: cheap_cloud\n"
    '    config: \'"private_key": "-----BEGIN PRIVATE KEY-----ABC"\'\n'  # pragma: allowlist secret
)

_LEAKED_CLIENT_EMAIL_YAML = """\
value: '"client_email": "svc@proj.iam.gserviceaccount.com"'
"""

_LEAKED_BEARER_YAML = """\
config:
  auth_header: "Bearer ya29.LONG_TOKEN_HERE_ABCDEFGHIJKLMNOPQRSTU"
"""

_LEAKED_OPENAI_KEY_YAML = 'api_key: "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrst"\n'  # pragma: allowlist secret

_LEAKED_GOOGLE_KEY_YAML = (
    'api_key: "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ012345678"\n'  # pragma: allowlist secret
)

_LEAKED_GCP_OAUTH_YAML = """\
token: "ya29.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrst"
"""

_MISSING_REF_BIFROST_YAML = """\
backends:
  - backend_id: cloud-rogue
    tier: cheap_cloud
    endpoint_url: https://example.com/v1/chat/completions
"""

_MUTUAL_EXCLUSION_BIFROST_YAML = """\
backends:
  - backend_id: cloud-both
    tier: cheap_cloud
    credential_ref: llm.vertex.adc
    secret_ref: llm.gemini.api_key
"""

_NO_SECRET_BACKEND_YAML = """\
backends:
  - backend_id: cli-claude
    tier: cheap_frontier
"""

_LOCAL_BACKEND_YAML = """\
backends:
  - backend_id: local-llm
    tier: local
    endpoint_url: http://localhost:8080/v1/chat/completions
"""


# ---------------------------------------------------------------------------
# scan_literal_credentials — positive (violation) cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detects_pem_private_key() -> None:
    violations = scan_literal_credentials("fake.yaml", _LEAKED_PEM_YAML)
    assert any("pem-private-key" in v.kind for v in violations)


@pytest.mark.unit
def test_detects_service_account_private_key() -> None:
    violations = scan_literal_credentials("fake.yaml", _LEAKED_SA_PRIVATE_KEY_YAML)
    assert any("service-account-private-key" in v.kind for v in violations)


@pytest.mark.unit
def test_detects_service_account_client_email() -> None:
    violations = scan_literal_credentials("fake.yaml", _LEAKED_CLIENT_EMAIL_YAML)
    assert any("service-account-client-email" in v.kind for v in violations)


@pytest.mark.unit
def test_detects_bearer_token() -> None:
    violations = scan_literal_credentials("fake.yaml", _LEAKED_BEARER_YAML)
    assert any("bearer-token" in v.kind for v in violations)


@pytest.mark.unit
def test_detects_openai_style_key() -> None:
    violations = scan_literal_credentials("fake.yaml", _LEAKED_OPENAI_KEY_YAML)
    assert any("openai-style-key" in v.kind for v in violations)


@pytest.mark.unit
def test_detects_google_api_key() -> None:
    violations = scan_literal_credentials("fake.yaml", _LEAKED_GOOGLE_KEY_YAML)
    assert any("google-api-key" in v.kind for v in violations)


@pytest.mark.unit
def test_detects_gcp_oauth_token() -> None:
    violations = scan_literal_credentials("fake.yaml", _LEAKED_GCP_OAUTH_YAML)
    assert any("gcp-oauth-token" in v.kind for v in violations)


# ---------------------------------------------------------------------------
# scan_literal_credentials — negative (clean) cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_clean_yaml_no_literal_violations() -> None:
    violations = scan_literal_credentials("clean.yaml", _CLEAN_BIFROST_YAML)
    assert violations == []


@pytest.mark.unit
def test_secret_ref_names_not_flagged() -> None:
    """A secret_ref NAME (not value) must not be detected as a credential."""
    text = "secret_ref: llm.gemini.api_key\n"
    violations = scan_literal_credentials("ok.yaml", text)
    assert violations == []


# ---------------------------------------------------------------------------
# scan_bifrost_backends — positive (violation) cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_cloud_backend_missing_ref_detected() -> None:
    import yaml

    data = yaml.safe_load(_MISSING_REF_BIFROST_YAML)
    violations = scan_bifrost_backends("fake.yaml", data)
    assert any("requires a logical secret reference" in v.message for v in violations)


@pytest.mark.unit
def test_mutual_exclusion_detected() -> None:
    import yaml

    data = yaml.safe_load(_MUTUAL_EXCLUSION_BIFROST_YAML)
    violations = scan_bifrost_backends("fake.yaml", data)
    assert any("mutually exclusive" in v.message for v in violations)


@pytest.mark.unit
def test_backends_not_list_error() -> None:
    violations = scan_bifrost_backends("fake.yaml", {"backends": "not-a-list"})
    assert len(violations) == 1
    assert "must be a list" in violations[0].message


# ---------------------------------------------------------------------------
# scan_bifrost_backends — negative (clean) cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_clean_bifrost_no_backend_violations() -> None:
    import yaml

    data = yaml.safe_load(_CLEAN_BIFROST_YAML)
    violations = scan_bifrost_backends("clean.yaml", data)
    assert violations == []


@pytest.mark.unit
def test_no_secret_backend_ids_exempt() -> None:
    """cli-claude / cli-opencode are exempt from the secret-ref requirement."""
    import yaml

    data = yaml.safe_load(_NO_SECRET_BACKEND_YAML)
    violations = scan_bifrost_backends("ok.yaml", data)
    assert violations == []


@pytest.mark.unit
def test_local_tier_exempt() -> None:
    import yaml

    data = yaml.safe_load(_LOCAL_BACKEND_YAML)
    violations = scan_bifrost_backends("ok.yaml", data)
    assert violations == []


@pytest.mark.unit
def test_api_key_env_counts_as_logical_ref() -> None:
    import yaml

    data = yaml.safe_load(
        "backends:\n  - backend_id: cloud-x\n    tier: cheap_cloud\n    api_key_env: SOME_ENV_VAR\n"
    )
    violations = scan_bifrost_backends("ok.yaml", data)
    assert violations == []


@pytest.mark.unit
def test_credential_ref_alone_counts_as_logical_ref() -> None:
    import yaml

    data = yaml.safe_load(
        "backends:\n  - backend_id: cloud-x\n    tier: cheap_cloud\n    credential_ref: llm.vertex.adc\n"
    )
    violations = scan_bifrost_backends("ok.yaml", data)
    assert violations == []


# ---------------------------------------------------------------------------
# build_report_from_files — integration-level
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_report_passes_on_clean_input() -> None:
    report = build_report_from_files({"bifrost_delegation.yaml": _CLEAN_BIFROST_YAML})
    assert report.passed is True
    assert report.literal_credential_violations == []
    assert report.backend_ref_violations == []
    assert report.errors == []


@pytest.mark.unit
def test_report_fails_on_leaked_credential() -> None:
    """Fail-closed proof: literal SA private_key → gate red."""
    report = build_report_from_files(
        {"routing_tiers.yaml": _LEAKED_SA_PRIVATE_KEY_YAML}
    )
    assert report.passed is False
    assert len(report.literal_credential_violations) >= 1


@pytest.mark.unit
def test_report_fails_on_missing_backend_ref() -> None:
    """Fail-closed proof: cloud backend without secret-ref → gate red."""
    report = build_report_from_files(
        {"bifrost_delegation.yaml": _MISSING_REF_BIFROST_YAML}
    )
    assert report.passed is False
    assert len(report.backend_ref_violations) >= 1


@pytest.mark.unit
def test_report_fails_on_mutual_exclusion() -> None:
    report = build_report_from_files(
        {"bifrost_delegation.yaml": _MUTUAL_EXCLUSION_BIFROST_YAML}
    )
    assert report.passed is False
    assert any("mutually exclusive" in v.message for v in report.backend_ref_violations)


@pytest.mark.unit
def test_report_empty_config_contents_passes() -> None:
    """No files to check → trivially passed (no violations possible)."""
    report = build_report_from_files({})
    assert report.passed is True


@pytest.mark.unit
def test_report_yaml_parse_error_recorded() -> None:
    report = build_report_from_files({"bifrost_delegation.yaml": "backends: ["})
    assert report.passed is False
    assert len(report.errors) >= 1


# ---------------------------------------------------------------------------
# COMPUTE handler — protocol properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_protocol_properties() -> None:
    handler = HandlerBackendSecretDisciplineCompute()
    assert handler.handler_id == "node.backend-secret-discipline.compute"
    assert handler.node_kind == EnumNodeKind.COMPUTE
    assert "BackendSecretDisciplineCheck" in handler.message_types


@pytest.mark.unit
def test_handler_handle_returns_compute_output() -> None:
    """Handler returns a ModelHandlerOutput with a ModelBackendSecretDisciplineOutput result."""
    from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

    handler = HandlerBackendSecretDisciplineCompute()

    payload = ModelBackendSecretDisciplineInput(
        config_contents={"bifrost_delegation.yaml": _CLEAN_BIFROST_YAML}
    )
    envelope = MagicMock()
    envelope.payload = payload
    envelope.envelope_id = uuid4()
    envelope.correlation_id = uuid4()

    output: ModelHandlerOutput[ModelBackendSecretDisciplineOutput] = asyncio.run(
        handler.handle(envelope)
    )

    assert output.node_kind == EnumNodeKind.COMPUTE
    assert output.result is not None
    assert isinstance(output.result, ModelBackendSecretDisciplineOutput)
    assert output.result.passed is True


@pytest.mark.unit
def test_handler_handle_fail_closed_on_violation() -> None:
    """Handler result.passed=False when payload contains a literal credential."""
    from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

    handler = HandlerBackendSecretDisciplineCompute()
    payload = ModelBackendSecretDisciplineInput(
        config_contents={"routing.yaml": _LEAKED_SA_PRIVATE_KEY_YAML}
    )
    envelope = MagicMock()
    envelope.payload = payload
    envelope.envelope_id = uuid4()
    envelope.correlation_id = uuid4()

    output: ModelHandlerOutput[ModelBackendSecretDisciplineOutput] = asyncio.run(
        handler.handle(envelope)
    )
    assert output.result is not None
    assert output.result.passed is False
    assert len(output.result.literal_credential_violations) >= 1


# ---------------------------------------------------------------------------
# Pydantic model — frozen / extra=forbid
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_input_model_frozen() -> None:
    inp = ModelBackendSecretDisciplineInput(config_contents={"a.yaml": "x: 1"})
    with pytest.raises(Exception):
        inp.config_contents = {}  # type: ignore[misc]


@pytest.mark.unit
def test_output_model_is_json_ledger_safe() -> None:
    from omnibase_core.models.dispatch.model_handler_output import _is_json_ledger_safe

    output = ModelBackendSecretDisciplineOutput(passed=True)
    assert _is_json_ledger_safe(output)


# ---------------------------------------------------------------------------
# CLI entry-point — exit codes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_cli_passes_on_clean_tree(tmp_path: Path) -> None:
    """CLI exits 0 when no YAML violations in supplied files."""
    config = tmp_path / "clean.yaml"
    config.write_text("key: value\n", encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_backend_secret_discipline",
            str(config),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Expected 0, got {result.returncode}\n{result.stdout}\n{result.stderr}"
    )


@pytest.mark.unit
def test_cli_fails_on_leaked_credential(tmp_path: Path) -> None:
    """Fail-closed proof: planted literal private_key → CLI exits 1."""
    config = tmp_path / "leaked.yaml"
    config.write_text(
        'service_account: \'"private_key": "-----BEGIN PRIVATE KEY-----MIIABC"\'\n',  # pragma: allowlist secret
        encoding="utf-8",
    )

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_backend_secret_discipline",
            str(config),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, (
        f"Expected 1, got {result.returncode}\n{result.stdout}\n{result.stderr}"
    )
    assert "FAIL" in result.stdout or "literal-credential" in result.stdout


@pytest.mark.unit
def test_cli_json_flag_clean(tmp_path: Path) -> None:
    config = tmp_path / "ok.yaml"
    config.write_text("key: value\n", encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_backend_secret_discipline",
            "--json",
            str(config),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["passed"] is True


@pytest.mark.unit
def test_cli_json_flag_violation(tmp_path: Path) -> None:
    config = tmp_path / "bad.yaml"
    config.write_text(
        'value: "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ012345678"\n',  # pragma: allowlist secret
        encoding="utf-8",
    )

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_backend_secret_discipline",
            "--json",
            str(config),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["passed"] is False
    assert len(data["literal_credential_violations"]) >= 1


@pytest.mark.unit
def test_cli_no_yaml_files_passes(tmp_path: Path) -> None:
    """No YAML files in staged set → trivially PASS."""
    py_file = tmp_path / "module.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_backend_secret_discipline",
            str(py_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
