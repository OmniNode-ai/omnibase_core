# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the typed contract ``skill_surface:`` block (OMN-21373 S-c0)."""

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts import (
    ModelAlgorithmConfig,
    ModelAlgorithmFactorConfig,
    ModelContractCompute,
    ModelPerformanceRequirements,
)
from omnibase_core.models.contracts.model_contract_skill_surface import (
    ModelContractSkillSurface,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _create_minimal_compute(**overrides: object) -> ModelContractCompute:
    defaults: dict[str, object] = {
        "name": "test_node",
        "contract_version": ModelSemVer(major=1, minor=0, patch=0),
        "description": "Test compute contract",
        "node_type": EnumNodeType.COMPUTE_GENERIC,
        "input_model": "omnibase_core.models.ModelTestInput",
        "output_model": "omnibase_core.models.ModelTestOutput",
        "algorithm": ModelAlgorithmConfig(
            algorithm_type="test",
            factors={
                "f1": ModelAlgorithmFactorConfig(
                    weight=1.0,
                    calculation_method="default",
                ),
            },
        ),
        "performance": ModelPerformanceRequirements(single_operation_max_ms=1000),
    }
    defaults.update(overrides)
    return ModelContractCompute.model_validate(defaults)


_VALID: dict[str, object] = {
    "id": "merge-sweep",
    "cli_id": "merge_sweep",
    "description": "Sweep open PRs.",
}


@pytest.mark.unit
class TestModelContractSkillSurface:
    def test_contract_with_skill_surface_validates(self) -> None:
        contract = _create_minimal_compute(skill_surface=_VALID)
        assert isinstance(contract.skill_surface, ModelContractSkillSurface)
        assert contract.skill_surface.id == "merge-sweep"
        assert contract.skill_surface.cli_command == "merge_sweep"
        assert contract.skill_surface.description == "Sweep open PRs."

    def test_skill_surface_defaults_to_none(self) -> None:
        assert _create_minimal_compute().skill_surface is None

    def test_unknown_key_in_skill_surface_is_refused(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _create_minimal_compute(
                skill_surface={
                    "id": "merge-sweep",
                    "cli_id": "merge_sweep",
                    "tier": "x",
                }
            )
        assert any(
            e["type"] == "extra_forbidden" and e["loc"] == ("skill_surface", "tier")
            for e in exc_info.value.errors()
        )

    @pytest.mark.parametrize(
        "skill_id",
        ["bad_name", "Bad-Name", "-lead", "trail-", "double--hyphen", "a" * 65, ""],
    )
    def test_refused_id_on_contract(self, skill_id: str) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _create_minimal_compute(skill_surface={**_VALID, "id": skill_id})
        assert any(e["loc"] == ("skill_surface", "id") for e in exc_info.value.errors())

    @pytest.mark.parametrize("skill_id", ["a", "a" * 64, "merge-sweep"])
    def test_accepted_id_on_contract(self, skill_id: str) -> None:
        contract = _create_minimal_compute(skill_surface={**_VALID, "id": skill_id})
        assert contract.skill_surface is not None
        assert contract.skill_surface.id == skill_id

    def test_id_uses_reference_normalization(self) -> None:
        contract = _create_minimal_compute(
            skill_surface={**_VALID, "id": " \uff4derge-sweep "}
        )
        assert contract.skill_surface is not None
        assert contract.skill_surface.id == "merge-sweep"

    def test_description_at_limit_validates(self) -> None:
        description = "a" * 1024
        contract = _create_minimal_compute(
            skill_surface={**_VALID, "description": description}
        )
        assert contract.skill_surface is not None
        assert contract.skill_surface.description == description

    @pytest.mark.parametrize("description", ["a" * 1025, "   "])
    def test_description_invalid_is_refused(self, description: str) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _create_minimal_compute(
                skill_surface={**_VALID, "description": description}
            )
        assert any(
            e["loc"] == ("skill_surface", "description")
            for e in exc_info.value.errors()
        )

    def test_description_omitted_defaults_to_none(self) -> None:
        contract = _create_minimal_compute(
            skill_surface={"id": "merge-sweep", "cli_id": "merge_sweep"}
        )
        assert contract.skill_surface is not None
        assert contract.skill_surface.description is None

    def test_description_explicit_none_validates(self) -> None:
        contract = _create_minimal_compute(
            skill_surface={**_VALID, "description": None}
        )
        assert contract.skill_surface is not None
        assert contract.skill_surface.description is None

    def test_empty_cli_id_is_refused(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _create_minimal_compute(skill_surface={**_VALID, "cli_id": ""})
        assert any(
            e["loc"] == ("skill_surface", "cli_id") for e in exc_info.value.errors()
        )

    @pytest.mark.parametrize("missing", ["id", "cli_id"])
    def test_id_and_cli_id_are_required(self, missing: str) -> None:
        data = {k: v for k, v in _VALID.items() if k != missing}
        with pytest.raises(ValidationError) as exc_info:
            _create_minimal_compute(skill_surface=data)
        assert any(
            e["type"] == "missing" and e["loc"] == ("skill_surface", missing)
            for e in exc_info.value.errors()
        )

    def test_is_frozen(self) -> None:
        assert ModelContractSkillSurface.model_config.get("frozen") is True

    def test_contract_yaml_shape_validates(self) -> None:
        data = yaml.safe_load(
            """
name: merge_sweep
description: Sweep pull requests.
skill_surface:
  id: merge-sweep
  cli_id: merge_sweep
  description: Sweep open PRs.
"""
        )
        contract = _create_minimal_compute(**data)
        assert isinstance(contract.skill_surface, ModelContractSkillSurface)
        assert contract.skill_surface.model_dump(by_alias=True) == _VALID
