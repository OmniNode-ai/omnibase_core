# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# api-key-env-ok: OMN-12878 — fixtures ARE intentional api_key_env declarations
# the scanner-under-test must flag; the literals are the subject.
"""Unit tests for the api_key_ref_discipline COMPUTE validator (OMN-12878).

Acceptance criteria from the ticket DoD:
  1. Fixture with api_key_env trips the guard.
  2. Fixture with api_key_ref (logical ref) passes.
  3. Fixture with secret_ref passes.
  4. Fixture with suppression marker on the api_key_env line passes.
  5. check_routing_authority handler no longer exposes api_key_env as the
     resolved secret ref in _resolve_endpoint_for_ref.

Tests are parameterised to cover violation and clean cases explicitly so the
corpus acceptance evidence is machine-verifiable.
"""

from __future__ import annotations

import pytest

from omnibase_core.validation.api_key_ref_discipline.handler import (
    HandlerApiKeyRefDisciplineCompute,
    scan_bifrost_yaml,
)
from omnibase_core.validation.api_key_ref_discipline.models import (
    ModelApiKeyRefScanInput,
    ModelApiKeyRefScanResult,
)

# ---------------------------------------------------------------------------
# Corpus fixtures (violation)
# ---------------------------------------------------------------------------

_V_API_KEY_ENV_ONLY = """\
backends:
  - backend_id: "cloud-gemini"
    tier: "cheap_cloud"
    endpoint_url: "https://generativelanguage.googleapis.com/v1/chat/completions"
    api_key_env: "GEMINI_API_KEY"
"""

_V_API_KEY_ENV_WITH_URL_ENV = """\
backends:
  - backend_id: "cloud-glm"
    tier: "cheap_cloud"
    endpoint_url_env: "GLM_URL"
    endpoint_url: null
    api_key_env: "GLM_API_KEY"
"""

# ---------------------------------------------------------------------------
# Corpus fixtures (clean / passing)
# ---------------------------------------------------------------------------

_C_API_KEY_REF = """\
backends:
  - backend_id: "cloud-gemini"
    tier: "cheap_cloud"
    endpoint_url: "https://generativelanguage.googleapis.com/v1/chat/completions"
    api_key_ref: "gemini_api_key"
"""

_C_SECRET_REF = """\
backends:
  - backend_id: "cloud-openai"
    tier: "frontier_api"
    endpoint_url: "https://api.openai.com/v1/chat/completions"
    secret_ref: "openai_secret_key"
"""

_C_LOCAL_TIER_NO_REF = """\
backends:
  - backend_id: "local-coder"
    tier: "local"
    endpoint_url: "http://192.168.86.201:8000/v1/chat/completions"
"""

_C_SUPPRESSION_LINE = """\
backends:
  - backend_id: "cloud-legacy"
    tier: "cheap_cloud"
    endpoint_url: "https://api.legacy.ai/v1/chat/completions"
    api_key_env: "LEGACY_KEY"  # api-key-env-ok: OMN-12878 legacy entry under migration
"""

_C_NO_BACKENDS_KEY = """\
node_type: compute
model_routing:
  provider: google
  endpoint_ref: gemini_pro
"""

# ---------------------------------------------------------------------------
# Tests: scan_bifrost_yaml (pure function)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScanBifrostYaml:
    def test_api_key_env_only_trips_guard(self) -> None:
        findings = scan_bifrost_yaml("bifrost.yaml", _V_API_KEY_ENV_ONLY)
        assert len(findings) == 1
        assert findings[0].backend_id == "cloud-gemini"
        assert findings[0].deprecated_field == "api_key_env"

    def test_api_key_env_with_url_env_trips_guard(self) -> None:
        findings = scan_bifrost_yaml("bifrost.yaml", _V_API_KEY_ENV_WITH_URL_ENV)
        assert len(findings) == 1
        assert findings[0].backend_id == "cloud-glm"

    def test_api_key_ref_passes(self) -> None:
        findings = scan_bifrost_yaml("bifrost.yaml", _C_API_KEY_REF)
        assert findings == []

    def test_secret_ref_passes(self) -> None:
        findings = scan_bifrost_yaml("bifrost.yaml", _C_SECRET_REF)
        assert findings == []

    def test_local_tier_no_ref_passes(self) -> None:
        findings = scan_bifrost_yaml("bifrost.yaml", _C_LOCAL_TIER_NO_REF)
        assert findings == []

    def test_suppression_line_passes(self) -> None:
        findings = scan_bifrost_yaml("bifrost.yaml", _C_SUPPRESSION_LINE)
        assert findings == []

    def test_no_backends_key_passes(self) -> None:
        findings = scan_bifrost_yaml("bifrost.yaml", _C_NO_BACKENDS_KEY)
        assert findings == []

    def test_finding_contains_file_and_message(self) -> None:
        findings = scan_bifrost_yaml("path/to/bifrost.yaml", _V_API_KEY_ENV_ONLY)
        assert len(findings) == 1
        f = findings[0]
        assert f.file == "path/to/bifrost.yaml"
        assert "api_key_env" in f.message
        assert "api_key_ref" in f.message or "secret_ref" in f.message


# ---------------------------------------------------------------------------
# Tests: HandlerApiKeyRefDisciplineCompute
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandlerApiKeyRefDisciplineCompute:
    def _make_handler(self) -> HandlerApiKeyRefDisciplineCompute:
        return HandlerApiKeyRefDisciplineCompute()

    def _run(self, contents: dict[str, str]) -> ModelApiKeyRefScanResult:
        handler = self._make_handler()
        inp = ModelApiKeyRefScanInput(config_contents=contents)
        return handler.run(inp)

    def test_violation_fixture_fails(self) -> None:
        result = self._run({"bifrost.yaml": _V_API_KEY_ENV_ONLY})
        assert not result.passed
        assert len(result.findings) == 1

    def test_clean_fixture_api_key_ref_passes(self) -> None:
        result = self._run({"bifrost.yaml": _C_API_KEY_REF})
        assert result.passed
        assert result.findings == []

    def test_clean_fixture_secret_ref_passes(self) -> None:
        result = self._run({"bifrost.yaml": _C_SECRET_REF})
        assert result.passed

    def test_empty_contents_passes(self) -> None:
        result = self._run({})
        assert result.passed

    def test_non_yaml_content_returns_error(self) -> None:
        # Content must mention 'backends' to trigger the YAML parse attempt.
        result = self._run({"bifrost.yaml": "backends: [invalid yaml unclosed"})
        assert not result.passed
        assert len(result.errors) == 1

    def test_multiple_backends_one_violation(self) -> None:
        mixed = """\
backends:
  - backend_id: "cloud-gemini"
    tier: "cheap_cloud"
    endpoint_url: "https://generativelanguage.googleapis.com/v1"
    api_key_ref: "gemini_key"
  - backend_id: "cloud-glm"
    tier: "cheap_cloud"
    endpoint_url: "https://open.bigmodel.cn/api/v1"
    api_key_env: "GLM_KEY"
"""
        result = self._run({"bifrost.yaml": mixed})
        assert not result.passed
        assert len(result.findings) == 1
        assert result.findings[0].backend_id == "cloud-glm"


# ---------------------------------------------------------------------------
# Tests: routing authority handler no longer exposes api_key_env as preferred
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_routing_authority_resolve_prefers_api_key_ref_over_api_key_env() -> None:
    """_resolve_endpoint_for_ref must not return api_key_env as the key ref when
    api_key_ref or secret_ref is present. Covers the DoD requirement:
    'check_routing_authority no longer treats api_key_env as preferred authority'.
    """
    from omnibase_core.nodes.node_routing_authority_check_compute.handler import (
        NodeRoutingAuthorityCheckCompute,
    )

    bifrost_with_both = """\
backends:
  - backend_id: "cloud-gemini"
    tier: "cheap_cloud"
    endpoint_url: "https://generativelanguage.googleapis.com/v1/chat/completions"
    api_key_ref: "gemini_api_key"
    api_key_env: "GEMINI_API_KEY"
"""
    handler = NodeRoutingAuthorityCheckCompute()
    _endpoint_url, key_ref, _source = handler._resolve_endpoint_for_ref(
        "cloud-gemini", bifrost_with_both, "bifrost.yaml"
    )
    # The logical api_key_ref must be returned, not the env-var api_key_env.
    assert key_ref == "gemini_api_key", (
        f"Expected api_key_ref='gemini_api_key', got {key_ref!r}. "
        "check_routing_authority must prefer api_key_ref over api_key_env."
    )


@pytest.mark.unit
def test_routing_authority_resolve_prefers_secret_ref_over_api_key_env() -> None:
    """secret_ref must take priority over api_key_env."""
    from omnibase_core.nodes.node_routing_authority_check_compute.handler import (
        NodeRoutingAuthorityCheckCompute,
    )

    bifrost_secret_ref = """\
backends:
  - backend_id: "cloud-vertex"
    tier: "cheap_cloud"
    endpoint_url: "https://us-central1-aiplatform.googleapis.com/v1/projects/p/locations/us-central1/publishers/google/models/gemini-1.5-pro:streamGenerateContent"
    secret_ref: "vertex_service_account"
    api_key_env: "VERTEX_LEGACY_KEY"
"""
    handler = NodeRoutingAuthorityCheckCompute()
    _endpoint_url, key_ref, _source = handler._resolve_endpoint_for_ref(
        "cloud-vertex", bifrost_secret_ref, "bifrost.yaml"
    )
    assert key_ref == "vertex_service_account", (
        f"Expected secret_ref='vertex_service_account', got {key_ref!r}. "
        "check_routing_authority must prefer secret_ref over api_key_env."
    )


@pytest.mark.unit
def test_routing_authority_resolve_returns_api_key_env_when_only_option() -> None:
    """When api_key_env is the only ref present (legacy backend), return it for
    backward compatibility (will be flagged by the api_key_ref_discipline gate).
    """
    from omnibase_core.nodes.node_routing_authority_check_compute.handler import (
        NodeRoutingAuthorityCheckCompute,
    )

    bifrost_legacy_only = """\
backends:
  - backend_id: "cloud-legacy"
    tier: "cheap_cloud"
    endpoint_url: "https://api.legacy.ai/v1"
    api_key_env: "LEGACY_KEY"
"""
    handler = NodeRoutingAuthorityCheckCompute()
    _endpoint_url, key_ref, _source = handler._resolve_endpoint_for_ref(
        "cloud-legacy", bifrost_legacy_only, "bifrost.yaml"
    )
    # api_key_env is still returned when it's the only option (migration ratchet).
    assert key_ref == "LEGACY_KEY"
