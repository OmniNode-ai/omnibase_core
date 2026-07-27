# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Equivalence-oracle canary for a pure T1 COMPUTE node (OMN-14353).

Proves the compute-golden oracle is NON-VACUOUS on a real node
(``NodeRoutingAuthorityCheckCompute``): a golden recorded from its legacy
input->output catches a behavior regression. This is the de-risking proof for
the self-verifying codegen factory — the piece that makes "self-verifying" mean
"behavior is pinned", not "a file exists".

The canary is hermetic: it records goldens in-process, asserts replay
equivalence + determinism, and proves the comparator discriminates by PERTURBING
a recorded output field (never by editing handler source). The live
source-mutation proof (off-by-one ``>``/``>=`` in the residue ratchet, caught by
the ``residue_at_baseline`` golden) is documented in the OMN-14353 report.
"""

from __future__ import annotations

import pytest

from omnibase_core.nodes.node_routing_authority_check_compute.handler import (
    ModelResidueEntry,
    ModelRoutingAuthorityCheckInput,
    ModelRoutingContractEntry,
    NodeRoutingAuthorityCheckCompute,
)
from scripts.ci.compute_golden import (
    compare_output,
    outputs_equivalent,
    record_golden,
)

pytestmark = pytest.mark.unit

_GOOD_CONTRACT = """\
name: node_generation_consumer
node_type: compute
model_routing:
  provider: "google"
  served_model_id: "gemini-1.5-pro"
  endpoint_ref: "gemini_pro"
  routing_source: "bifrost_delegation.yaml"
"""
_MISSING_ROUTING = "name: node_bad\nnode_type: compute\n"
_GOOD_BIFROST = """\
backends:
  - backend_id: "gemini_pro"
    tier: "cloud"
    endpoint_url_env: "GEMINI_PRO_URL"
    endpoint_url: null
"""
_CLI_BIFROST = """\
backends:
  - backend_id: "cli-claude"
    tier: "cli_agents"
    endpoint_url: "cli://claude"
"""
_CLEAN_SOURCE = "def handle(p):\n    return p\n"
_DIRTY_SOURCE = 'import os\nED = os.getenv("SERVICE_ENDPOINT")\n'
# Two endpoint env reads; neither matches the api-key hints — so a residue
# baseline of 2 is exactly at the ratchet edge (the off-by-one canary input).
_RESIDUE_SRC = (
    'import os\nA = os.getenv("SERVICE_ENDPOINT")\nB = os.getenv("PROVIDER_HOST")\n'
)


def _clean_input() -> ModelRoutingAuthorityCheckInput:
    return ModelRoutingAuthorityCheckInput(
        demo_path_contracts=(ModelRoutingContractEntry(contract_rel="c.yaml"),),
        contract_contents={"c.yaml": _GOOD_CONTRACT},
        bifrost_config_rel="bifrost.yaml",
        bifrost_config_content=_GOOD_BIFROST,
        demo_path_sources=("clean.py",),
        source_contents={"clean.py": _CLEAN_SOURCE},
        residue_entries=(),
        residue_contents={},
    )


def _violations_input() -> ModelRoutingAuthorityCheckInput:
    return ModelRoutingAuthorityCheckInput(
        demo_path_contracts=(ModelRoutingContractEntry(contract_rel="bad.yaml"),),
        contract_contents={"bad.yaml": _MISSING_ROUTING},
        bifrost_config_rel="bifrost.yaml",
        bifrost_config_content=_CLI_BIFROST,
        demo_path_sources=("dirty.py",),
        source_contents={"dirty.py": _DIRTY_SOURCE},
        residue_entries=(),
        residue_contents={},
    )


def _residue_at_baseline_input() -> ModelRoutingAuthorityCheckInput:
    return ModelRoutingAuthorityCheckInput(
        demo_path_contracts=(ModelRoutingContractEntry(contract_rel="c.yaml"),),
        contract_contents={"c.yaml": _GOOD_CONTRACT},
        bifrost_config_rel="bifrost.yaml",
        bifrost_config_content=_GOOD_BIFROST,
        demo_path_sources=("clean.py",),
        source_contents={"clean.py": _CLEAN_SOURCE},
        residue_entries=(
            ModelResidueEntry(
                file_rel="legacy.py",
                baseline_count=2,
                debt_ticket="OMN-0000",
                description="known env-authority debt",
            ),
        ),
        residue_contents={"legacy.py": _RESIDUE_SRC},
    )


_INPUTS = {
    "clean": _clean_input,
    "violations": _violations_input,
    "residue_at_baseline": _residue_at_baseline_input,
}


@pytest.fixture
def handler() -> NodeRoutingAuthorityCheckCompute:
    return NodeRoutingAuthorityCheckCompute()


@pytest.mark.parametrize("name", list(_INPUTS))
def test_handler_is_deterministic(
    handler: NodeRoutingAuthorityCheckCompute, name: str
) -> None:
    """Legacy handler is deterministic — a prerequisite for a stable golden."""
    inp = _INPUTS[name]()
    out1 = handler.check(inp)
    out2 = handler.check(inp)
    assert outputs_equivalent(out1, out2, volatile_mask=[])


@pytest.mark.parametrize("name", list(_INPUTS))
def test_record_then_replay_is_equivalent(
    handler: NodeRoutingAuthorityCheckCompute, name: str
) -> None:
    """A recorded golden replays clean against the (unchanged) handler."""
    inp = _INPUTS[name]()
    golden = record_golden(input_model=inp, output=handler.check(inp), volatile_mask=[])
    # Replay from the SERIALIZED input proves the golden is self-contained.
    replayed_inp = ModelRoutingAuthorityCheckInput.model_validate(golden["input"])
    assert compare_output(golden, handler.check(replayed_inp)) == []


def test_comparator_discriminates_a_regression(
    handler: NodeRoutingAuthorityCheckCompute,
) -> None:
    """THE oracle proof: a behavior change in the output is caught by the comparator.

    Hermetic stand-in for the live source-mutation (off-by-one residue ratchet):
    perturb the recorded verdict and confirm the comparator flags the exact path,
    proving it is not vacuously empty.
    """
    inp = _residue_at_baseline_input()
    golden = record_golden(input_model=inp, output=handler.check(inp), volatile_mask=[])
    assert golden["output"]["residue_ok"] is True  # baseline pins clean
    # Simulate the regressed verdict the off-by-one mutation produces.
    golden["output"]["residue_ok"] = False
    golden["output"]["passed"] = False
    diffs = compare_output(golden, handler.check(inp))
    assert diffs, (
        "comparator MUST catch the regressed verdict (oracle is vacuous otherwise)"
    )
    assert any("residue_ok" in d for d in diffs)
    assert any("passed" in d for d in diffs)


def test_volatile_mask_excludes_declared_fields(
    handler: NodeRoutingAuthorityCheckCompute,
) -> None:
    """A field named in the volatile mask is excluded from the compare."""
    inp = _clean_input()
    golden = record_golden(
        input_model=inp, output=handler.check(inp), volatile_mask=["passed"]
    )
    # Corrupt the masked field in the recorded output; the mask must ignore it.
    golden["output"]["passed"] = not golden["output"]["passed"]
    assert compare_output(golden, handler.check(inp)) == []
