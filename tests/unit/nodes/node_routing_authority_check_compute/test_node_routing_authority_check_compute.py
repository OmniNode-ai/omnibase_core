# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for the routing-authority check node (OMN-21520)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_routing_authority_check_input import (
    ModelRoutingAuthorityCheckInput,
)
from omnibase_core.models.validation.model_routing_contract_entry import (
    ModelRoutingContractEntry,
)
from omnibase_core.nodes.node_routing_authority_check_compute.handler import (
    NodeRoutingAuthorityCheckCompute,
)
from omnibase_core.nodes.node_routing_authority_check_compute.runtime_routing_authority_check import (
    main,
)

pytestmark = pytest.mark.unit

_CONTRACT = """\
name: node_generation_consumer
node_type: compute
model_routing:
  provider: "google"
  served_model_id: "served-model-a"
  endpoint_ref: "backend_a"
  routing_source: "bifrost_delegation.yaml"
"""

_BIFROST = """\
backends:
  - backend_id: "backend_a"
    tier: "cloud"
    endpoint_url_env: "BACKEND_A_URL"
    endpoint_url: null
"""

_CLEAN_SOURCE = """\
from omnibase_core.dispatch.dispatch_bus_client import DispatchBusClient

def handle(payload):
    return DispatchBusClient().dispatch(payload)
"""

_ENV_READ_SOURCE = """\
import os

def handle(payload):
    return os.environ.get("LLM_CODER_URL")
"""


def _input(source: str) -> ModelRoutingAuthorityCheckInput:
    return ModelRoutingAuthorityCheckInput(
        demo_path_contracts=(ModelRoutingContractEntry(contract_rel="contract.yaml"),),
        contract_contents={"contract.yaml": _CONTRACT},
        bifrost_config_rel="bifrost.yaml",
        bifrost_config_content=_BIFROST,
        demo_path_sources=("handler.py",),
        source_contents={"handler.py": source},
        residue_entries=(),
        residue_contents={},
    )


def _repo(tmp_path: Path, source: str) -> list[str]:
    (tmp_path / "contract.yaml").write_text(_CONTRACT, encoding="utf-8")
    (tmp_path / "bifrost.yaml").write_text(_BIFROST, encoding="utf-8")
    (tmp_path / "handler.py").write_text(source, encoding="utf-8")
    return [
        "--repo-root",
        str(tmp_path),
        "--contract",
        "contract.yaml",
        "--source",
        "handler.py",
        "--bifrost",
        "bifrost.yaml",
        "--no-default-residue",
    ]


def test_handle_passes_clean_source() -> None:
    result = NodeRoutingAuthorityCheckCompute().handle(_input(_CLEAN_SOURCE))
    assert result.passed is True


def test_handle_fails_env_read_source() -> None:
    result = NodeRoutingAuthorityCheckCompute().handle(_input(_ENV_READ_SOURCE))
    assert result.passed is False


def test_main_exit_zero_on_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_repo(tmp_path, _CLEAN_SOURCE)) == 0
    assert "[routing-authority-gate] PASS" in capsys.readouterr().out


def test_main_exit_one_on_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_repo(tmp_path, _ENV_READ_SOURCE)) == 1
    assert "[routing-authority-gate] FAIL" in capsys.readouterr().out


def test_main_json_packet_reports_verdict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*_repo(tmp_path, _CLEAN_SOURCE), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True
