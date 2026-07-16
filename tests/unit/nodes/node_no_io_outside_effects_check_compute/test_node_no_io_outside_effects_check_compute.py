# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Perturbation-corpus tests for node_no_io_outside_effects_check_compute.

The load-bearing case is the per-surface RED-against-exists-but-wrong proof:
for EACH forbidden I/O surface (database, network, subprocess, git, Linear,
filesystem write, direct bus/adapter instantiation), the SAME I/O-doing source
is FLAGGED when it lives in a non-EFFECT node package (COMPUTE / REDUCER /
ORCHESTRATOR) and PASSED when the identical source lives in an EFFECT package.
That discriminator proves the gate keys off the declared archetype — it is not
green merely because no I/O exists anywhere (green-on-absence), and it is not a
blind every-file scan.

Ticket: OMN-14694 (WS8 seed) → OMN-14662 (archetype-purity collapse).
"""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.no_io_outside_effects_check.model_no_io_outside_effects_check_input import (
    ModelNoIoOutsideEffectsCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_no_io_outside_effects_check_compute.handler import (
    NodeNoIoOutsideEffectsCheckCompute,
)

pytestmark = pytest.mark.unit

VALIDATOR_ID = "arch-no-io-outside-effects"


def _contract(archetype: str) -> str:
    return (
        f"name: node_x\nnode_type: {archetype}\n"
        f"descriptor:\n  node_archetype: {archetype}\n"
    )


_ORCHESTRATOR_CONTRACT = _contract("orchestrator")
_COMPUTE_CONTRACT = _contract("compute")
_REDUCER_CONTRACT = _contract("reducer")
_EFFECT_CONTRACT = _contract("effect")


def _run(*files: tuple[str, str]) -> ModelValidationReport:
    return NodeNoIoOutsideEffectsCheckCompute().handle(
        ModelNoIoOutsideEffectsCheckInput(
            files=[ModelSourceFile(path=p, source=s) for p, s in files]
        )
    )


def _scan(contract: str, handler_source: str) -> ModelValidationReport:
    return _run(
        ("nodes/node_x/contract.yaml", contract),
        ("nodes/node_x/handler.py", handler_source),
    )


# =============================================================================
# Per-surface RED-against-exists-but-wrong — the load-bearing proof.
#
# Each row is a real I/O snippet. The SAME snippet must FAIL in a non-EFFECT
# package and PASS in an EFFECT package. The (surface, snippet) label is used
# only for readable test ids.
# =============================================================================

_FORBIDDEN_SURFACES: list[tuple[str, str, str]] = [
    # (surface id, handler source, substring expected in the finding message)
    ("db-import", "import asyncpg\n", "database driver"),
    ("db-import-from", "from sqlalchemy import create_engine\n", "database driver"),
    ("network-httpx", "import httpx\n", "network/HTTP client"),
    ("network-requests", "import requests\n", "network/HTTP client"),
    ("network-socket", "import socket\n", "network/HTTP client"),
    ("network-urllib-request", "from urllib.request import urlopen\n", "network/HTTP"),
    ("subprocess-import", "import subprocess\n", "subprocess execution"),
    (
        "subprocess-call",
        "import subprocess\nsubprocess.run(['ls', '-la'])\n",
        "subprocess execution",
    ),
    (
        "git-subprocess",
        "import subprocess\nsubprocess.run(['git', 'status'])\n",
        "git invocation",
    ),
    ("git-os-system", "import os\nos.system('git pull')\n", "git invocation"),
    ("git-lib", "import git\n", "git invocation"),
    ("git-pygit2", "import pygit2\n", "git invocation"),
    ("linear-sdk", "import linear_sdk\n", "Linear API access"),
    (
        "linear-url",
        "import httpx\n\n\ndef go(c):\n    return c.get('https://api.linear.app/graphql')\n",
        "network/HTTP client",  # the httpx import fires first (line 1)
    ),
    (
        "fs-path-write-text",
        "from pathlib import Path\n\n\ndef w(p):\n    Path(p).write_text('x')\n",
        "filesystem write",
    ),
    (
        "fs-path-mkdir",
        "from pathlib import Path\n\n\ndef w(p):\n    Path(p).mkdir()\n",
        "filesystem write",
    ),
    ("fs-open-write", "def w(p):\n    return open(p, 'w')\n", "filesystem write"),
    ("fs-os-remove", "import os\nos.remove('x')\n", "filesystem write"),
    ("fs-shutil-rmtree", "import shutil\nshutil.rmtree('d')\n", "filesystem write"),
    (
        "bus-kafka-producer",
        "def make():\n    return KafkaProducer(bootstrap_servers='x')\n",
        "direct event-bus instantiation",
    ),
    (
        "bus-eventbus-suffix",
        "def make():\n    return InMemoryEventBus()\n",
        "direct event-bus instantiation",
    ),
    (
        "adapter-suffix",
        "def make():\n    return PostgresRepoAdapter()\n",
        "direct infra-adapter instantiation",
    ),
]


@pytest.mark.parametrize(
    "handler_source",
    [src for _, src, _ in _FORBIDDEN_SURFACES],
    ids=[sid for sid, _, _ in _FORBIDDEN_SURFACES],
)
@pytest.mark.parametrize(
    "non_effect_contract",
    [_COMPUTE_CONTRACT, _REDUCER_CONTRACT, _ORCHESTRATOR_CONTRACT],
    ids=["compute", "reducer", "orchestrator"],
)
def test_forbidden_surface_fails_in_non_effect(
    non_effect_contract: str, handler_source: str
) -> None:
    """EXISTS-BUT-WRONG: every forbidden surface FAILS in a non-EFFECT package."""
    report = _scan(non_effect_contract, handler_source)

    assert report.overall_status == "FAIL"
    assert report.metrics.fail_count >= 1
    assert all(f.validator_id == VALIDATOR_ID for f in report.findings)


@pytest.mark.parametrize(
    "handler_source",
    [src for _, src, _ in _FORBIDDEN_SURFACES],
    ids=[sid for sid, _, _ in _FORBIDDEN_SURFACES],
)
def test_forbidden_surface_passes_in_effect(handler_source: str) -> None:
    """ARCHETYPE-KEYING: the IDENTICAL I/O source PASSES inside an EFFECT
    package — proving the gate discriminates by declared archetype, not by the
    mere presence of I/O code anywhere."""
    report = _scan(_EFFECT_CONTRACT, handler_source)

    assert report.overall_status == "PASS"
    assert report.findings == ()


@pytest.mark.parametrize(
    ("handler_source", "expected_label"),
    [(src, label) for _, src, label in _FORBIDDEN_SURFACES],
    ids=[sid for sid, _, _ in _FORBIDDEN_SURFACES],
)
def test_forbidden_surface_message_names_the_surface(
    handler_source: str, expected_label: str
) -> None:
    """The finding message names the specific forbidden surface."""
    report = _scan(_COMPUTE_CONTRACT, handler_source)

    assert report.overall_status == "FAIL"
    assert any(expected_label in f.message for f in report.findings)


# =============================================================================
# Archetype seam — EFFECT is the sole exemption; both seam fields are read.
# =============================================================================


def test_effect_via_node_type_only_is_exempt() -> None:
    report = _scan("name: node_x\nnode_type: effect\n", "import asyncpg\n")
    assert report.overall_status == "PASS"


def test_effect_via_descriptor_only_is_exempt() -> None:
    report = _scan(
        "name: node_x\ndescriptor:\n  node_archetype: effect\n", "import asyncpg\n"
    )
    assert report.overall_status == "PASS"


def test_non_effect_via_descriptor_only_is_scanned() -> None:
    """A contract that declares compute ONLY via descriptor still arms the rule."""
    report = _scan(
        "name: node_x\ndescriptor:\n  node_archetype: compute\n", "import asyncpg\n"
    )
    assert report.overall_status == "FAIL"


def test_unknown_archetype_fails_closed_and_is_scanned() -> None:
    """A parseable contract that names no recognised archetype is treated as
    non-EFFECT (fail-closed) — I/O there is still flagged."""
    report = _scan("name: node_x\nunrelated: true\n", "import asyncpg\n")
    assert report.overall_status == "FAIL"


# =============================================================================
# Non-violations — reads, pure helpers, suppression, scoping.
# =============================================================================


def test_filesystem_read_is_not_flagged() -> None:
    """The gate scopes filesystem to WRITES — reads stay clean."""
    report = _scan(
        _COMPUTE_CONTRACT,
        "from pathlib import Path\n\n\ndef r(p):\n    return Path(p).read_text()\n",
    )
    assert report.overall_status == "PASS"


def test_open_read_mode_is_not_flagged() -> None:
    report = _scan(_COMPUTE_CONTRACT, "def r(p):\n    return open(p)\n")
    assert report.overall_status == "PASS"


def test_str_replace_is_not_a_filesystem_write() -> None:
    """``str.replace`` shares a name with ``Path.replace`` but is pure — the
    gate must not confuse them (method-name-only matching trap)."""
    report = _scan(_COMPUTE_CONTRACT, "def n(p):\n    return p.replace('/', '-')\n")
    assert report.overall_status == "PASS"


def test_urllib_parse_is_not_network() -> None:
    """``urllib.parse`` is pure string manipulation — only urllib.request/error
    are the network surface."""
    report = _scan(
        _COMPUTE_CONTRACT, "from urllib.parse import urlencode\n\nq = urlencode\n"
    )
    assert report.overall_status == "PASS"


def test_relative_import_passes() -> None:
    """`from . import x` (node.module is None) must not trip the check."""
    report = _scan(_COMPUTE_CONTRACT, "from . import sibling\n")
    assert report.overall_status == "PASS"


def test_pure_stdlib_import_passes() -> None:
    report = _scan(_COMPUTE_CONTRACT, "import json\nimport dataclasses\n")
    assert report.overall_status == "PASS"


def test_io_ok_annotation_suppresses_violation() -> None:
    report = _scan(
        _COMPUTE_CONTRACT,
        "import asyncpg  # io-ok: bootstrap-only, no runtime connect\n",
    )
    assert report.overall_status == "PASS"


def test_io_ok_annotation_suppresses_call_violation() -> None:
    report = _scan(
        _COMPUTE_CONTRACT,
        "import os\nos.remove('x')  # io-ok: test fixture teardown\n",
    )
    assert report.overall_status == "PASS"


def test_io_outside_any_node_package_passes() -> None:
    """A .py file whose directory has NO contract is not a node package — even a
    real I/O import there is out of scope (dir-scoping, not blind scan)."""
    report = _run(("scripts/adhoc_backfill.py", "import asyncpg\n"))
    assert report.overall_status == "PASS"


def test_io_in_sibling_effect_package_passes() -> None:
    """I/O in an EFFECT package that is a sibling of a compute node is correct
    architecture — only the non-EFFECT dir's modules are scanned."""
    report = _run(
        ("nodes/node_x_compute/contract.yaml", _COMPUTE_CONTRACT),
        ("nodes/node_x_compute/handler.py", "import json\n"),
        ("nodes/node_db_effect/contract.yaml", _EFFECT_CONTRACT),
        ("nodes/node_db_effect/handler.py", "import asyncpg\nimport httpx\n"),
    )
    assert report.overall_status == "PASS"


# =============================================================================
# Error findings — fail loud, never silent-green.
# =============================================================================


def test_unparseable_contract_yields_error_finding() -> None:
    report = _run(("nodes/node_x/contract.yaml", "name: [unclosed\n"))
    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.severity == "ERROR"
    assert "unparseable contract.yaml" in finding.message


def test_syntax_error_in_non_effect_module_yields_error() -> None:
    report = _scan(_COMPUTE_CONTRACT, "def f(:\n    pass\n")
    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    assert report.findings[0].message.startswith(
        "nodes/node_x/handler.py: SyntaxError:"
    )


# =============================================================================
# Aggregation.
# =============================================================================


def test_multiple_surfaces_in_one_module_aggregate() -> None:
    source = "import asyncpg\nimport httpx\nimport subprocess\n"
    report = _scan(_COMPUTE_CONTRACT, source)
    assert report.overall_status == "FAIL"
    assert report.metrics.fail_count == 3
    assert report.provenance.validators_run == (VALIDATOR_ID,)


def test_two_non_effect_nodes_aggregate_findings() -> None:
    report = _run(
        ("nodes/node_a_compute/contract.yaml", _COMPUTE_CONTRACT),
        ("nodes/node_a_compute/handler.py", "import asyncpg\n"),
        ("nodes/node_b_orchestrator/contract.yaml", _ORCHESTRATOR_CONTRACT),
        ("nodes/node_b_orchestrator/handler.py", "import httpx\n"),
    )
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 2


def test_empty_input_passes_trivially() -> None:
    report = NodeNoIoOutsideEffectsCheckCompute().handle(
        ModelNoIoOutsideEffectsCheckInput(files=[])
    )
    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert report.metrics.total == 0


def test_finding_location_points_at_the_import_line() -> None:
    report = _scan(_COMPUTE_CONTRACT, "import json\nimport asyncpg\n")
    assert report.overall_status == "FAIL"
    assert report.findings[0].location == "nodes/node_x/handler.py:2"
