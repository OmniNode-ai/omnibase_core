# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelContractConfig and sub-models (OMN-11430)."""

import pytest
from pydantic import SecretStr, ValidationError

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_contract_config import ModelContractConfig
from omnibase_core.models.contracts.model_llm_endpoint_config import (
    ModelLlmEndpointConfig,
)
from omnibase_core.models.contracts.model_operational_config import (
    ModelOperationalConfig,
)
from omnibase_core.models.contracts.model_storage_config import ModelStorageConfig
from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract
from omnibase_core.models.primitives.model_semver import ModelSemVer


class _SampleContract(ModelContractBase):
    def validate_node_specific_config(self) -> None:
        pass


_SEMVER = ModelSemVer(major=1, minor=0, patch=0)
_MINIMAL = {
    "name": "test_contract",
    "contract_version": _SEMVER,
    "description": "Test",
    "node_type": EnumNodeType.COMPUTE_GENERIC,
    "input_model": "omnibase_core.models.test.In",
    "output_model": "omnibase_core.models.test.Out",
}


@pytest.mark.unit
class TestModelContractConfig:
    """Unit tests for ModelContractConfig and its sub-models."""

    def test_default_construction_gives_empty_submodels(self):
        cfg = ModelContractConfig()
        assert cfg.llm.coder_url is None
        assert cfg.storage.postgres_host is None
        assert cfg.operational.linear_api_key is None

    def test_llm_endpoint_config_valid(self):
        llm = ModelLlmEndpointConfig(
            coder_url="http://192.168.86.201:8000",
            coder_model_name="Qwen3-Coder-30B",
        )
        assert llm.coder_url == "http://192.168.86.201:8000"
        assert llm.coder_model_name == "Qwen3-Coder-30B"

    def test_llm_endpoint_config_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            ModelLlmEndpointConfig(unknown_field="bad")  # type: ignore[call-arg]  # NOTE(OMN-11430): negative Pydantic validation case.

    def test_storage_config_valid(self):
        s = ModelStorageConfig(
            postgres_host="192.168.86.201",
            postgres_port=5436,
            kafka_bootstrap_servers="192.168.86.201:19092",
        )
        assert s.postgres_host == "192.168.86.201"
        assert s.postgres_port == 5436

    def test_storage_config_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            ModelStorageConfig(bad_key="x")  # type: ignore[call-arg]  # NOTE(OMN-11430): negative Pydantic validation case.

    def test_operational_config_secrets_are_secret_str(self):
        op = ModelOperationalConfig(linear_api_key="secret123")
        assert isinstance(op.linear_api_key, SecretStr)
        assert op.linear_api_key.get_secret_value() == "secret123"

    def test_operational_config_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            ModelOperationalConfig(bogus="x")  # type: ignore[call-arg]  # NOTE(OMN-11430): negative Pydantic validation case.

    def test_model_contract_config_allows_extra_fields(self):
        """extra="allow" on ModelContractConfig lets node-specific keys pass through."""
        cfg = ModelContractConfig.model_validate(
            {"node_specific_key": "value", "llm": {}, "storage": {}, "operational": {}}
        )
        assert cfg.model_extra is not None
        assert cfg.model_extra.get("node_specific_key") == "value"

    def test_model_contract_config_is_frozen(self):
        cfg = ModelContractConfig()
        with pytest.raises(ValidationError):
            cfg.llm = ModelLlmEndpointConfig()  # type: ignore[misc]  # NOTE(OMN-11430): intentional frozen-model mutation test.

    def test_llm_endpoint_config_is_frozen(self):
        llm = ModelLlmEndpointConfig()
        with pytest.raises(ValidationError):
            llm.coder_url = "http://new"  # type: ignore[misc]  # NOTE(OMN-11430): intentional frozen-model mutation test.

    def test_storage_config_is_frozen(self):
        s = ModelStorageConfig()
        with pytest.raises(ValidationError):
            s.postgres_port = 9999  # type: ignore[misc]  # NOTE(OMN-11430): intentional frozen-model mutation test.

    def test_nested_config_parsed_from_dict(self):
        cfg = ModelContractConfig.model_validate(
            {
                "llm": {"coder_url": "http://host:8000", "coder_model_name": "model-x"},
                "storage": {"postgres_host": "db.host", "postgres_port": 5432},
                "operational": {"github_token": "ghp_abc"},
            }
        )
        assert cfg.llm.coder_url == "http://host:8000"
        assert cfg.storage.postgres_port == 5432
        assert isinstance(cfg.operational.github_token, SecretStr)

    def test_bad_type_for_port_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ModelStorageConfig(postgres_port="not-an-int")  # type: ignore[arg-type]  # NOTE(OMN-11430): negative Pydantic validation case.


@pytest.mark.unit
class TestModelYamlContractConfig:
    """Config field on ModelYamlContract is ModelContractConfig."""

    def test_config_defaults_to_empty_model_contract_config(self):
        contract = ModelYamlContract(
            contract_version=_SEMVER,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )
        assert isinstance(contract.config, ModelContractConfig)
        assert contract.config.llm.coder_url is None

    def test_config_parsed_from_dict_at_load_time(self):
        contract = ModelYamlContract.model_validate(
            {
                "contract_version": {"major": 1, "minor": 0, "patch": 0},
                "node_type": "COMPUTE_GENERIC",
                "config": {
                    "llm": {"coder_url": "http://host:8000"},
                    "storage": {"postgres_port": 5436},
                },
            }
        )
        assert contract.config.llm.coder_url == "http://host:8000"
        assert contract.config.storage.postgres_port == 5436

    def test_invalid_config_type_raises_at_load_time(self):
        """Wrong type in config sub-model fails at parse time, not silently."""
        with pytest.raises(ValidationError):
            ModelYamlContract.model_validate(
                {
                    "contract_version": {"major": 1, "minor": 0, "patch": 0},
                    "node_type": "COMPUTE_GENERIC",
                    "config": {"storage": {"postgres_port": "bad"}},
                }
            )


@pytest.mark.unit
class TestModelContractBaseConfig:
    """Config field on ModelContractBase is ModelContractConfig."""

    def test_config_defaults_to_empty_model_contract_config(self):
        contract = _SampleContract(**_MINIMAL)
        assert isinstance(contract.config, ModelContractConfig)
        assert contract.config.storage.postgres_host is None

    def test_config_with_values_parsed(self):
        data = {
            **_MINIMAL,
            "config": {
                "llm": {"coder_model_name": "Qwen3"},
                "operational": {"linear_team_id": "TEAM-1"},
            },
        }
        contract = _SampleContract.model_validate(data)
        assert contract.config.llm.coder_model_name == "Qwen3"
        assert contract.config.operational.linear_team_id == "TEAM-1"

    def test_bad_config_value_fails_at_construction(self):
        data = {
            **_MINIMAL,
            "config": {"storage": {"redpanda_admin_port": "bad-port"}},
        }
        with pytest.raises(ValidationError):
            _SampleContract.model_validate(data)
