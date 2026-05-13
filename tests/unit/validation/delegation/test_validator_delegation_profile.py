# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import yaml

from omnibase_core.validation.delegation.validator_delegation_profile import (
    validate_delegation_profile,
)

VALID_YAML = """
name: delegation-runtime-profile
version: 1
runtime_profile: main
event_bus:
  provider: kafka
  bootstrap_servers:
    - redpanda:9092
  topic_policy_ref: default-topics
llm_backends:
  default:
    bifrost_endpoint_ref: local-bifrost
    default_task_model_ref: qwen3-coder
    max_tokens_default: 2048
    max_tokens_hard_limit: 8192
    timeout_ms: 120000
"""


def test_valid_profile_passes() -> None:
    data = yaml.safe_load(VALID_YAML)
    result = validate_delegation_profile(data)
    assert result.is_valid
    assert result.errors == []


def test_rejects_endpoint_url_in_bifrost_ref() -> None:
    data = yaml.safe_load(VALID_YAML)
    data["llm_backends"]["default"]["bifrost_endpoint_ref"] = (
        "http://192.168.86.201:8000"
    )
    result = validate_delegation_profile(data)
    assert not result.is_valid
    assert any("bifrost_endpoint_ref" in e for e in result.errors)


def test_rejects_ip_in_bifrost_ref() -> None:
    data = yaml.safe_load(VALID_YAML)
    data["llm_backends"]["default"]["bifrost_endpoint_ref"] = "192.168.86.201:8000"
    result = validate_delegation_profile(data)
    assert not result.is_valid
    assert any("bifrost_endpoint_ref" in e for e in result.errors)


def test_rejects_missing_bootstrap_servers() -> None:
    data = yaml.safe_load(VALID_YAML)
    data["event_bus"]["bootstrap_servers"] = []
    result = validate_delegation_profile(data)
    assert not result.is_valid


def test_rejects_max_tokens_hard_limit_below_default() -> None:
    data = yaml.safe_load(VALID_YAML)
    data["llm_backends"]["default"]["max_tokens_hard_limit"] = 512
    data["llm_backends"]["default"]["max_tokens_default"] = 2048
    result = validate_delegation_profile(data)
    assert not result.is_valid
    assert any("max_tokens" in e for e in result.errors)


def test_rejects_raw_value_in_secret_ref() -> None:
    data = yaml.safe_load(VALID_YAML)
    data["security"] = {
        "broker_allowlist_ref": "broker-list",
        "endpoint_cidr_allowlist_ref": "cidr-list",
        "shared_secret_ref": {
            "ref_name": "MY_SECRET",
            "raw_value": "super-secret-value",
        },
    }
    result = validate_delegation_profile(data)
    assert not result.is_valid


def test_rejects_url_in_bootstrap_server() -> None:
    data = yaml.safe_load(VALID_YAML)
    data["event_bus"]["bootstrap_servers"] = ["http://redpanda:9092"]
    result = validate_delegation_profile(data)
    assert not result.is_valid
    assert any("bootstrap_servers" in e for e in result.errors)


def test_multiple_llm_backends_all_validated() -> None:
    data = yaml.safe_load(VALID_YAML)
    data["llm_backends"]["fast"] = {
        "bifrost_endpoint_ref": "https://bad-url.example.com/api",
        "default_task_model_ref": "haiku",
        "max_tokens_default": 1024,
        "max_tokens_hard_limit": 4096,
        "timeout_ms": 30000,
    }
    result = validate_delegation_profile(data)
    assert not result.is_valid
    assert any("fast" in e for e in result.errors)


def test_invalid_yaml_structure_rejected() -> None:
    result = validate_delegation_profile({"not": "a valid profile"})
    assert not result.is_valid
