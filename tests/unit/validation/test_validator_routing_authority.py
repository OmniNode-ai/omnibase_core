# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ValidatorRoutingAuthority (OMN-13285).

Positive (clean corpus -> passed) and negative (planted violation -> FAIL) cases
for each audit pass: positive-proof, negative-audit, residue ratchet,
provider-class endpoint shape, and the folded-in delegation-profile rules.
"""

from __future__ import annotations

import asyncio

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.validation.model_routing_authority_input import (
    ModelRoutingAuthorityFile,
    ModelRoutingAuthorityInput,
    ModelRoutingResidueFile,
)
from omnibase_core.validation.validator_routing_authority import (
    ValidatorRoutingAuthority,
    evaluate,
)

pytestmark = pytest.mark.unit


_CLEAN_CONTRACT = """
model_routing:
  provider: glm
  served_model_id: glm-4.5
  endpoint_ref: glm_local
  routing_source: bifrost_delegation.yaml
"""

_CLEAN_SOURCE = '''
"""Handler that resolves routing from the contract."""
def call(routing):
    return routing.provider
'''

_CLEAN_BIFROST = """
backends:
  - backend_id: glm_local
    tier: cheap
    endpoint_url_env: LLM_GLM_URL
    endpoint_url: null
  - backend_id: static_backend
    tier: ceiling
    endpoint_url: https://example.test/v1/chat/completions
"""


def _clean_input() -> ModelRoutingAuthorityInput:
    return ModelRoutingAuthorityInput(
        repo="omnimarket",
        demo_path_contracts=(
            ModelRoutingAuthorityFile(path="contract.yaml", text=_CLEAN_CONTRACT),
        ),
        demo_path_sources=(
            ModelRoutingAuthorityFile(path="handler.py", text=_CLEAN_SOURCE),
        ),
        provider_literal_tokens=("openrouter.ai", "api.openai.com"),
        fallback_endpoint_env_tokens=("LLM_BASE_URL",),
        skip_tokens=("contract-config-ok",),
        residue_files=(
            ModelRoutingResidueFile(
                path="residue.py",
                text="import os\nx = os.environ.get('LLM_GLM_URL')\n",
                kind="python",
                baseline_count=1,
                debt_ticket="OMN-12877",
                description="grandfathered debt",
            ),
        ),
        bifrost_config=ModelRoutingAuthorityFile(
            path="bifrost.yaml", text=_CLEAN_BIFROST
        ),
    )


def test_handler_is_compute_kind() -> None:
    handler = ValidatorRoutingAuthority()
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.handler_id == "routing-authority-compute"


def test_clean_corpus_passes() -> None:
    report = evaluate(_clean_input())
    assert report.passed, [f.message for f in report.findings]
    assert report.findings == ()


def test_handle_returns_compute_result() -> None:
    handler = ValidatorRoutingAuthority()
    envelope: ModelEventEnvelope[ModelRoutingAuthorityInput] = ModelEventEnvelope(
        payload=_clean_input()
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.node_kind is EnumNodeKind.COMPUTE
    assert output.result is not None
    assert output.result.passed is True


def test_missing_routing_key_fails() -> None:
    payload = _clean_input().model_copy(
        update={
            "demo_path_contracts": (
                ModelRoutingAuthorityFile(
                    path="contract.yaml",
                    text="model_routing:\n  provider: glm\n  served_model_id: glm-4.5\n  endpoint_ref: glm_local\n",
                ),
            )
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any(f.rule_id == "positive-proof" for f in report.findings)
    assert any("routing_source" in f.message for f in report.findings)


def test_endpoint_ref_not_authority_backed_fails() -> None:
    payload = _clean_input().model_copy(
        update={
            "demo_path_contracts": (
                ModelRoutingAuthorityFile(
                    path="contract.yaml",
                    text=_CLEAN_CONTRACT.replace("glm_local", "ghost_backend"),
                ),
            )
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any(
        "not map to a declared bifrost backend" in f.message for f in report.findings
    )


def test_env_read_on_demo_source_fails() -> None:
    payload = _clean_input().model_copy(
        update={
            "demo_path_sources": (
                ModelRoutingAuthorityFile(
                    path="handler.py",
                    text="import os\nmodel = os.environ['GLM_MODEL']\n",
                ),
            )
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any(f.rule_id == "negative-audit" for f in report.findings)


def test_api_key_env_read_is_exempt() -> None:
    payload = _clean_input().model_copy(
        update={
            "demo_path_sources": (
                ModelRoutingAuthorityFile(
                    path="handler.py",
                    text="import os\nkey = os.environ['OPENROUTER_API_KEY']\n",
                ),
            )
        }
    )
    report = evaluate(payload)
    assert report.passed, [f.message for f in report.findings]


def test_provider_literal_on_demo_source_fails() -> None:
    payload = _clean_input().model_copy(
        update={
            "demo_path_sources": (
                ModelRoutingAuthorityFile(
                    path="handler.py",
                    text='url = "https://openrouter.ai/api/v1"\n',
                ),
            )
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any("provider-literal" in f.message for f in report.findings)


def test_skip_token_suppresses_negative_violation() -> None:
    payload = _clean_input().model_copy(
        update={
            "demo_path_sources": (
                ModelRoutingAuthorityFile(
                    path="handler.py",
                    text="import os\nx = os.environ['LLM_BASE_URL']  # contract-config-ok: bootstrap\n",
                ),
            )
        }
    )
    report = evaluate(payload)
    assert report.passed, [f.message for f in report.findings]


def test_residue_regression_fails() -> None:
    payload = _clean_input().model_copy(
        update={
            "residue_files": (
                ModelRoutingResidueFile(
                    path="residue.py",
                    text="import os\na = os.environ.get('LLM_GLM_URL')\nb = os.getenv('LLM_X_MODEL')\n",
                    kind="python",
                    baseline_count=1,
                    debt_ticket="OMN-12877",
                    description="now exceeds baseline",
                ),
            )
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any(f.rule_id == "residue-audit" for f in report.findings)


def test_yaml_policy_residue_within_baseline_passes() -> None:
    payload = _clean_input().model_copy(
        update={
            "residue_files": (
                ModelRoutingResidueFile(
                    path="model_policy.yaml",
                    text="policies:\n  coder:\n    env_var: LLM_CODER_URL\n",
                    kind="yaml_policy",
                    baseline_count=1,
                    debt_ticket="OMN-12877",
                    description="one env_var, within baseline",
                ),
            )
        }
    )
    report = evaluate(payload)
    assert report.passed, [f.message for f in report.findings]


def test_cli_backend_shape_fails() -> None:
    payload = _clean_input().model_copy(
        update={
            "bifrost_config": ModelRoutingAuthorityFile(
                path="bifrost.yaml",
                text="backends:\n  - backend_id: cli-codex\n    tier: cli_agents\n    endpoint_url: cli://codex\n",
            )
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any(
        "shelled-CLI backends are forbidden" in f.message for f in report.findings
    )


def test_overlay_backend_with_nonnull_url_fails() -> None:
    payload = _clean_input().model_copy(
        update={
            "bifrost_config": ModelRoutingAuthorityFile(
                path="bifrost.yaml",
                text="backends:\n  - backend_id: glm_local\n    endpoint_url_env: LLM_GLM_URL\n    endpoint_url: https://x.test/v1\n",
            ),
            "demo_path_contracts": (),
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any("only one URL source is allowed" in f.message for f in report.findings)


def test_static_backend_missing_url_fails() -> None:
    payload = _clean_input().model_copy(
        update={
            "bifrost_config": ModelRoutingAuthorityFile(
                path="bifrost.yaml",
                text="backends:\n  - backend_id: static_x\n    tier: ceiling\n",
            ),
            "demo_path_contracts": (),
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any(
        "must carry a complete static endpoint_url" in f.message
        for f in report.findings
    )


# --- folded-in delegation-profile rules ------------------------------------

_VALID_PROFILE = """
name: default-profile
version: 1
runtime_profile: local
event_bus:
  provider: kafka
  bootstrap_servers:
    - localhost:9092
  topic_policy_ref: topic_policy_local
  consumer_groups:
    - delegation
llm_backends:
  default:
    bifrost_endpoint_ref: glm_local_ref
    default_task_model_ref: glm-4.5
    max_tokens_default: 1024
    max_tokens_hard_limit: 4096
    timeout_ms: 30000
"""


def test_valid_delegation_profile_passes() -> None:
    payload = _clean_input().model_copy(
        update={
            "delegation_profiles": (
                ModelRoutingAuthorityFile(path="profile.yaml", text=_VALID_PROFILE),
            )
        }
    )
    report = evaluate(payload)
    assert report.passed, [f.message for f in report.findings]


def test_delegation_profile_raw_url_ref_fails() -> None:
    bad = _VALID_PROFILE.replace("glm_local_ref", "https://example.test/v1")
    payload = _clean_input().model_copy(
        update={
            "delegation_profiles": (
                ModelRoutingAuthorityFile(path="profile.yaml", text=bad),
            )
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any(f.rule_id == "delegation-profile" for f in report.findings)
    assert any("symbolic ref" in f.message for f in report.findings)


def test_delegation_profile_bootstrap_url_fails() -> None:
    bad = _VALID_PROFILE.replace("localhost:9092", "https://broker.test:9092")
    payload = _clean_input().model_copy(
        update={
            "delegation_profiles": (
                ModelRoutingAuthorityFile(path="profile.yaml", text=bad),
            )
        }
    )
    report = evaluate(payload)
    assert not report.passed
    assert any("must not be a URL" in f.message for f in report.findings)
