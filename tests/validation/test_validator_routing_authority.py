# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the routing-authority COMPUTE handler (OMN-13306, W6b).

Covers:
  - Positive proof: contract with model_routing resolves from authority
  - Positive proof: contract missing model_routing → error
  - Negative audit: env read on demo-path source → violation
  - Negative audit: provider literal in string → violation
  - Negative audit: skip token suppresses violation
  - Residue ratchet: actual_count <= baseline → clean
  - Residue ratchet: actual_count > baseline → regression
  - Provider-endpoint shape audit: CLI backend → violation
  - Provider-endpoint shape audit: overlay backend with non-null endpoint_url → violation
  - Provider-endpoint shape audit: static backend with no URL → violation
  - Provider-endpoint shape audit: clean backends → pass
  - Fail-closed proof: gate exits non-zero on violation (planted-violation fixture)
  - Revert proof: gate passes on clean tree (clean-tree fixture)

OMN-13306 §7.2 (fail-closed proof, verifier ≠ runner).
"""

from __future__ import annotations

import pytest

from omnibase_core.nodes.node_routing_authority_check_compute.handler import (
    ModelResidueEntry,
    ModelRoutingAuthorityCheckInput,
    ModelRoutingContractEntry,
    NodeRoutingAuthorityCheckCompute,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_GOOD_CONTRACT_YAML = """\
name: node_generation_consumer
node_type: compute
model_routing:
  provider: "google"
  served_model_id: "gemini-1.5-pro"
  endpoint_ref: "gemini_pro"
  routing_source: "bifrost_delegation.yaml"
"""

_MISSING_MODEL_ROUTING_YAML = """\
name: node_bad
node_type: compute
"""

_GOOD_BIFROST_YAML = """\
backends:
  - backend_id: "gemini_pro"
    tier: "cloud"
    endpoint_url_env: "GEMINI_PRO_URL"
    endpoint_url: null
    api_key_env: "GEMINI_API_KEY"
"""

_CLEAN_SOURCE = """\
# Clean demo-path handler — no env reads, no provider literals.
from omnibase_core.dispatch.dispatch_bus_client import DispatchBusClient

def handle(payload):
    return DispatchBusClient().dispatch(payload)
"""

_VIOLATION_ENV_READ = """\
import os
from omnibase_core.dispatch.dispatch_bus_client import DispatchBusClient

def handle(payload):
    url = os.environ.get("LLM_CODER_URL")  # <-- violation: fallback endpoint env read
    return DispatchBusClient().dispatch(payload)
"""

_VIOLATION_PROVIDER_LITERAL = """\
from omnibase_core.dispatch.dispatch_bus_client import DispatchBusClient

def handle(payload):
    endpoint = "https://generativelanguage.googleapis.com/v1/chat/completions"
    return DispatchBusClient().dispatch(payload, endpoint=endpoint)
"""

_SKIP_TOKEN_SUPPRESSED = """\
import os

def handle(payload):
    url = os.environ.get("LLM_CODER_URL")  # contract-config-ok: overlay provides this
    return url
"""

_RESIDUE_CLEAN = """\
# Clean file — no env reads.
def load():
    return {}
"""

_RESIDUE_TWO_VIOLATIONS = """\
import os

def load(url_env, model_env):
    url = os.environ.get(url_env)
    model = os.environ.get(model_env)
    return url, model
"""

_RESIDUE_THREE_VIOLATIONS = """\
import os

def load(url_env, model_env, extra):
    url = os.environ.get(url_env)
    model = os.environ.get(model_env)
    extra_val = os.environ.get(extra)
    return url, model, extra_val
"""


def _make_handler() -> NodeRoutingAuthorityCheckCompute:
    return NodeRoutingAuthorityCheckCompute()


def _minimal_inp(**overrides: object) -> ModelRoutingAuthorityCheckInput:
    """Build a minimal clean input, applying any overrides."""
    defaults: dict[str, object] = {
        "demo_path_contracts": (
            ModelRoutingContractEntry(contract_rel="contract.yaml"),
        ),
        "contract_contents": {"contract.yaml": _GOOD_CONTRACT_YAML},
        "bifrost_config_rel": "bifrost.yaml",
        "bifrost_config_content": _GOOD_BIFROST_YAML,
        "demo_path_sources": ("handler.py",),
        "source_contents": {"handler.py": _CLEAN_SOURCE},
        "residue_entries": (),
        "residue_contents": {},
    }
    defaults.update(overrides)
    return ModelRoutingAuthorityCheckInput(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Positive proof tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_positive_proof_clean_contract_passes() -> None:
    h = _make_handler()
    result = h.check(_minimal_inp())
    assert result.positive_ok, result.positive_proof["errors"]
    assert result.passed, f"expected pass; errors={result.positive_proof['errors']}"


@pytest.mark.unit
def test_positive_proof_missing_model_routing_fails() -> None:
    h = _make_handler()
    inp = _minimal_inp(
        contract_contents={"contract.yaml": _MISSING_MODEL_ROUTING_YAML},
    )
    result = h.check(inp)
    assert not result.positive_ok
    errors = result.positive_proof["errors"]
    assert any("missing model_routing" in e for e in errors), errors


@pytest.mark.unit
def test_positive_proof_missing_routing_key_fails() -> None:
    """Contract missing served_model_id fails the positive proof."""
    contract = """\
name: node_x
node_type: compute
model_routing:
  provider: "google"
  endpoint_ref: "gemini_pro"
  routing_source: "bifrost"
"""
    h = _make_handler()
    inp = _minimal_inp(contract_contents={"contract.yaml": contract})
    result = h.check(inp)
    assert not result.positive_ok
    errors = result.positive_proof["errors"]
    assert any("served_model_id" in e for e in errors), errors


@pytest.mark.unit
def test_positive_proof_unknown_endpoint_ref_fails() -> None:
    """endpoint_ref not in bifrost_delegation.yaml fails the positive proof."""
    contract = """\
name: node_x
node_type: compute
model_routing:
  provider: "google"
  served_model_id: "gemini-1.5-pro"
  endpoint_ref: "nonexistent_backend"
  routing_source: "bifrost"
"""
    h = _make_handler()
    inp = _minimal_inp(contract_contents={"contract.yaml": contract})
    result = h.check(inp)
    assert not result.positive_ok
    errors = result.positive_proof["errors"]
    assert any("NOT DECLARED" in e for e in errors), errors


# ---------------------------------------------------------------------------
# Negative audit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_negative_audit_clean_source_passes() -> None:
    h = _make_handler()
    result = h.check(_minimal_inp())
    assert result.negative_ok, result.negative_audit


@pytest.mark.unit
def test_negative_audit_env_read_fails() -> None:
    """os.environ.get on a fallback-endpoint key fails the negative audit."""
    h = _make_handler()
    inp = _minimal_inp(
        source_contents={"handler.py": _VIOLATION_ENV_READ},
    )
    result = h.check(inp)
    assert not result.negative_ok
    all_violations = [
        v for fr in result.negative_audit["files"] for v in fr["violations"]
    ]
    assert len(all_violations) > 0, "expected at least one negative-audit violation"
    assert any("env-read" in v for v in all_violations), all_violations


@pytest.mark.unit
def test_negative_audit_provider_literal_fails() -> None:
    """A provider URL hardcoded in a string literal fails the negative audit."""
    h = _make_handler()
    inp = _minimal_inp(
        source_contents={"handler.py": _VIOLATION_PROVIDER_LITERAL},
    )
    result = h.check(inp)
    assert not result.negative_ok
    all_violations = [
        v for fr in result.negative_audit["files"] for v in fr["violations"]
    ]
    assert any("provider-literal" in v for v in all_violations), all_violations


@pytest.mark.unit
def test_negative_audit_skip_token_suppresses_violation() -> None:
    """# contract-config-ok inline annotation suppresses the env-read violation."""
    h = _make_handler()
    inp = _minimal_inp(
        source_contents={"handler.py": _SKIP_TOKEN_SUPPRESSED},
    )
    result = h.check(inp)
    assert result.negative_ok, result.negative_audit


@pytest.mark.unit
def test_negative_audit_missing_source_content_adds_error() -> None:
    """A demo-path source with no content entry is an error, not a pass."""
    h = _make_handler()
    inp = _minimal_inp(
        demo_path_sources=("handler.py", "handler_missing.py"),
        source_contents={"handler.py": _CLEAN_SOURCE},
        # handler_missing.py intentionally absent
    )
    result = h.check(inp)
    errors = result.negative_audit["errors"]
    assert any("handler_missing.py" in e for e in errors), errors


# ---------------------------------------------------------------------------
# Residue ratchet tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_residue_ratchet_within_baseline_passes() -> None:
    h = _make_handler()
    inp = _minimal_inp(
        residue_entries=(
            ModelResidueEntry(
                file_rel="residue.py",
                baseline_count=2,
                debt_ticket="OMN-12877",
                description="test residue",
            ),
        ),
        residue_contents={"residue.py": _RESIDUE_TWO_VIOLATIONS},
    )
    result = h.check(inp)
    assert result.residue_ok, result.residue_audit["new_violations"]


@pytest.mark.unit
def test_residue_ratchet_zero_violations_below_baseline_passes() -> None:
    h = _make_handler()
    inp = _minimal_inp(
        residue_entries=(
            ModelResidueEntry(
                file_rel="residue.py",
                baseline_count=2,
                debt_ticket="OMN-12877",
                description="test residue",
            ),
        ),
        residue_contents={"residue.py": _RESIDUE_CLEAN},
    )
    result = h.check(inp)
    assert result.residue_ok


@pytest.mark.unit
def test_residue_ratchet_exceeds_baseline_fails() -> None:
    """3 actual violations against a baseline of 2 → regression → gate red."""
    h = _make_handler()
    inp = _minimal_inp(
        residue_entries=(
            ModelResidueEntry(
                file_rel="residue.py",
                baseline_count=2,
                debt_ticket="OMN-12877",
                description="test residue",
            ),
        ),
        residue_contents={"residue.py": _RESIDUE_THREE_VIOLATIONS},
    )
    result = h.check(inp)
    assert not result.residue_ok
    new_violations = result.residue_audit["new_violations"]
    assert len(new_violations) > 0, "expected at least one new violation"
    assert any("residue.py" in v for v in new_violations), new_violations


# ---------------------------------------------------------------------------
# Provider-class endpoint shape tests
# ---------------------------------------------------------------------------

_CLEAN_BIFROST = """\
backends:
  - backend_id: "backend_a"
    tier: "cloud"
    endpoint_url_env: "BACKEND_A_URL"
    endpoint_url: null
  - backend_id: "backend_b"
    tier: "cloud"
    endpoint_url: "https://api.example.com/v1/chat/completions"
"""

_CLI_BIFROST = """\
backends:
  - backend_id: "cli-codex"
    tier: "cli_agents"
    endpoint_url: "cli://codex"
"""

_OVERLAY_WITH_STATIC_BIFROST = """\
backends:
  - backend_id: "backend_c"
    tier: "cloud"
    endpoint_url_env: "BACKEND_C_URL"
    endpoint_url: "https://api.example.com/v1/chat/completions"
"""

_STATIC_MISSING_URL_BIFROST = """\
backends:
  - backend_id: "backend_d"
    tier: "cloud"
    endpoint_url: null
"""


@pytest.mark.unit
def test_shape_audit_clean_backends_passes() -> None:
    h = _make_handler()
    inp = _minimal_inp(
        bifrost_config_content=_CLEAN_BIFROST,
        # Use a contract whose endpoint_ref is in the clean bifrost
        contract_contents={
            "contract.yaml": """\
name: node_x
node_type: compute
model_routing:
  provider: "google"
  served_model_id: "gemini-1.5-pro"
  endpoint_ref: "backend_a"
  routing_source: "bifrost"
"""
        },
    )
    result = h.check(inp)
    assert result.shape_ok, result.provider_endpoint_shape_audit["violations"]


@pytest.mark.unit
def test_shape_audit_cli_backend_fails() -> None:
    """A cli:// backend or cli_agents tier is forbidden (OMN-13215)."""
    h = _make_handler()
    inp = _minimal_inp(bifrost_config_content=_CLI_BIFROST)
    result = h.check(inp)
    assert not result.shape_ok
    violations = result.provider_endpoint_shape_audit["violations"]
    assert any("shelled-CLI" in v for v in violations), violations


@pytest.mark.unit
def test_shape_audit_overlay_with_static_url_fails() -> None:
    """endpoint_url_env set AND endpoint_url non-null is a misconfiguration."""
    h = _make_handler()
    inp = _minimal_inp(bifrost_config_content=_OVERLAY_WITH_STATIC_BIFROST)
    result = h.check(inp)
    assert not result.shape_ok
    violations = result.provider_endpoint_shape_audit["violations"]
    assert any("non-null" in v for v in violations), violations


@pytest.mark.unit
def test_shape_audit_static_backend_missing_url_fails() -> None:
    """Static backend with no endpoint_url and no endpoint_url_env is misconfigured."""
    h = _make_handler()
    inp = _minimal_inp(bifrost_config_content=_STATIC_MISSING_URL_BIFROST)
    result = h.check(inp)
    assert not result.shape_ok
    violations = result.provider_endpoint_shape_audit["violations"]
    assert any("absent/empty" in v for v in violations), violations


@pytest.mark.unit
def test_shape_audit_empty_bifrost_content_skips() -> None:
    """Empty bifrost content skips the shape audit (no-op, clean)."""
    h = _make_handler()
    inp = _minimal_inp(bifrost_config_content="")
    # positive proof may still fail (endpoint_ref NOT DECLARED), but shape is skipped
    result = h.check(inp)
    assert result.shape_ok
    assert result.provider_endpoint_shape_audit.get("skipped") is True


# ---------------------------------------------------------------------------
# Fail-closed proof (planted-violation — verifier ≠ runner)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fail_closed_planted_env_violation() -> None:
    """FAIL-CLOSED PROOF: planted env read on demo-path source → gate exits non-zero.

    This test acts as the fail-closed verifier. The runner (NodeRoutingAuthorityCheckCompute)
    is exercised; the assertion (verifier) is this test function — a different execution
    context. probe_stdout equivalent: result.passed is False.
    """
    h = _make_handler()
    # Plant the violation: env read for a fallback endpoint key
    planted_source = """\
import os
def run():
    return os.environ.get("LLM_CODER_URL")  # planted violation for fail-closed proof
"""
    inp = _minimal_inp(source_contents={"handler.py": planted_source})
    result = h.check(inp)

    # Gate must exit non-zero (fail closed)
    assert not result.passed, (
        "FAIL-CLOSED PROOF FAILED: gate passed with a planted violation"
    )
    assert not result.negative_ok
    all_violations = [
        v for fr in result.negative_audit["files"] for v in fr["violations"]
    ]
    assert any("LLM_CODER_URL" in v for v in all_violations), (
        f"Expected LLM_CODER_URL in violations; got {all_violations}"
    )


@pytest.mark.unit
def test_green_on_clean_tree() -> None:
    """REVERT PROOF: clean inputs → gate passes (fail-closed complement)."""
    h = _make_handler()
    result = h.check(_minimal_inp())
    assert result.passed, (
        f"Expected PASS on clean tree; "
        f"positive_errors={result.positive_proof['errors']} "
        f"negative_violations={result.negative_audit.get('violation_count', '?')} "
        f"residue_new={result.residue_audit.get('new_violations', [])} "
        f"shape_violations={result.provider_endpoint_shape_audit.get('violations', [])}"
    )


@pytest.mark.unit
def test_fail_closed_missing_contract_content() -> None:
    """FAIL-CLOSED PROOF: empty contract content → positive proof error → gate red."""
    h = _make_handler()
    inp = _minimal_inp(contract_contents={"contract.yaml": ""})
    result = h.check(inp)
    assert not result.passed
    assert not result.positive_ok
    errors = result.positive_proof["errors"]
    assert any("contract.yaml" in e for e in errors), errors


@pytest.mark.unit
def test_fail_closed_cli_backend_in_bifrost() -> None:
    """FAIL-CLOSED PROOF: cli:// backend in bifrost → shape audit fails → gate red."""
    h = _make_handler()
    inp = _minimal_inp(bifrost_config_content=_CLI_BIFROST)
    result = h.check(inp)
    assert not result.passed
    assert not result.shape_ok


# ---------------------------------------------------------------------------
# handler_id / protocol properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_properties() -> None:
    h = _make_handler()
    assert h.handler_id == "routing-authority-check-compute"
    assert "RoutingAuthorityCheckRequested" in h.message_types
    # node_kind and category resolve without error
    _ = h.node_kind
    _ = h.category
