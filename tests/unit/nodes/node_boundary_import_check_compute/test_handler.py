# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Paired fixtures and pure AST/ratchet regressions for OMN-17427."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_check_input import (
    ModelBoundaryImportCheckInput,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_source_file import (
    ModelBoundaryImportSourceFile,
)
from omnibase_core.nodes.node_boundary_import_check_compute.analyzer import (
    EXCLUDED_SEGMENTS,
    REGISTRY_PACKAGES,
    extract_edges,
    parse_baseline,
    render_baseline,
)
from omnibase_core.nodes.node_boundary_import_check_compute.handler import (
    NodeBoundaryImportCheckCompute,
)

pytestmark = pytest.mark.unit

NODE_A = "src/omnibase_core/nodes/node_alpha"
NODE_B = "src/omnibase_core/nodes/node_beta"
FIXTURES = Path(__file__).parent / "fixtures"


def request_for(path: str, source: str) -> ModelBoundaryImportCheckInput:
    """Known local directory inventory, including a non-node base class module."""
    inventory = (
        f"{NODE_A}/__init__.py",
        f"{NODE_A}/internals.py",
        f"{NODE_B}/__init__.py",
        f"{NODE_B}/handlers.py",
        f"{NODE_B}/services.py",
        "src/omnibase_core/nodes/node_effect.py",
    )
    return ModelBoundaryImportCheckInput(
        repo_packages=("omnibase_core",),
        files=tuple(
            ModelBoundaryImportSourceFile(path=item, source="") for item in inventory
        )
        + (ModelBoundaryImportSourceFile(path=path, source=source),),
    )


@pytest.mark.parametrize(
    ("fixture", "path", "kind", "seam"),
    [
        ("outside", "src/omnibase_core/client.py", "outside->node", "protocol"),
        ("node", f"{NODE_A}/handler.py", "node->node", "event"),
        ("foreign_node", "src/omnibase_core/client.py", "cross-repo->node", "protocol"),
        ("private", "plugins/plugin.py", "cross-repo-private", "private-api"),
    ],
)
def test_fixture_pairs(fixture: str, path: str, kind: str, seam: str) -> None:
    bad = request_for(path, (FIXTURES / f"{fixture}_bad.py").read_text())
    edges, errors = extract_edges(bad)
    assert not errors
    assert len(edges) == 1
    assert (edges[0].kind, edges[0].seam) == (kind, seam)
    assert edges[0].importer_path == path
    assert edges[0].line == 4
    assert NodeBoundaryImportCheckCompute().handle(bad).overall_status == "FAIL"
    valid = request_for(path, (FIXTURES / f"{fixture}_valid.py").read_text())
    assert extract_edges(valid) == ((), ())
    assert NodeBoundaryImportCheckCompute().handle(valid).overall_status == "PASS"


@pytest.mark.parametrize(
    "source",
    [
        "from omnibase_core.nodes.node_effect import NodeEffect",
        "import omnibase_core.nodes.node_effect",
        "from omnibase_infra.nodes.node_remote import ModelRemote",
        "import omnibase_infra.nodes.node_remote",
        "from omnibase_infra.__dunder.api import handle",
        "from unregistered._private.api import handle",
        "from unregistered.nodes.node_remote.handler import handle",
    ],
)
def test_non_edges(source: str) -> None:
    assert extract_edges(request_for("hooks/check.py", source)) == ((), ())


@pytest.mark.parametrize(
    ("path", "source", "target"),
    [
        (
            f"{NODE_A}/handler.py",
            "from ..node_beta.handlers import handle",
            "omnibase_core.nodes.node_beta.handlers",
        ),
        (
            f"{NODE_A}/__init__.py",
            "from ..node_beta import handlers",
            "omnibase_core.nodes.node_beta.handlers",
        ),
        (
            "src/omnibase_core/client.py",
            "from .nodes import node_beta",
            "omnibase_core.nodes.node_beta",
        ),
        (
            "src/omnibase_core/client.py",
            "from omnibase_core.nodes import node_beta",
            "omnibase_core.nodes.node_beta",
        ),
        (
            "src/omnibase_core/client.py",
            "from omnibase_core.nodes.node_beta import Missing",
            "omnibase_core.nodes.node_beta",
        ),
    ],
)
def test_relative_and_from_resolution(path: str, source: str, target: str) -> None:
    edges, errors = extract_edges(request_for(path, source))
    assert not errors
    assert len(edges) == 1
    assert edges[0].target == target


@pytest.mark.parametrize("path", [f"{NODE_A}/handler.py", f"{NODE_A}/__init__.py"])
def test_own_node_internals(path: str) -> None:
    assert not extract_edges(request_for(path, "from .internals import dispatch"))[0]


def test_type_checking_and_function_imports_are_counted_and_deduplicated() -> None:
    request = request_for(
        "scripts/check.py",
        """from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from omnibase_core.nodes.node_beta.handlers import handle
def check():
    from omnibase_core.nodes.node_beta.handlers import other
    import omnibase_core.nodes.node_beta.services
""",
    )
    edges, errors = extract_edges(request)
    assert not errors
    assert len(edges) == 2
    assert (edges[0].importer, edges[0].line, edges[0].imported_name) == (
        "scripts/check.py",
        3,
        "handle",
    )


@pytest.mark.parametrize("excluded", sorted(EXCLUDED_SEGMENTS))
def test_excluded_paths(excluded: str) -> None:
    request = request_for(f"src/omnibase_core/{excluded}/bad.py", "invalid python !!!")
    assert extract_edges(request) == ((), ())


@pytest.mark.parametrize(
    ("sub", "name", "seam"),
    [
        ("handlers", "ModelReply", "model"),
        ("models", "ProtocolReply", "protocol"),
        ("protocols", "EnumReply", "model"),
        ("models", "CONTRACT_NAME", "contract"),
        ("models", "reply", "model"),
        ("model", "reply", "model"),
        ("enums", "reply", "model"),
        ("types", "reply", "model"),
        ("schemas", "reply", "model"),
        ("dto", "reply", "model"),
        ("model_reply", "reply", "model"),
        ("enum_reply", "reply", "model"),
        ("protocols", "reply", "protocol"),
        ("protocol", "reply", "protocol"),
        ("ports", "reply", "protocol"),
        ("protocol_reply", "reply", "protocol"),
        ("constants_bus", "reply", "contract"),
        ("topics_bus", "reply", "contract"),
        ("contract", "reply", "contract"),
        ("contracts", "reply", "contract"),
        ("config", "reply", "contract"),
        ("registry", "reply", "protocol"),
    ],
)
def test_seam_precedence_and_surface(sub: str, name: str, seam: str) -> None:
    edges, _ = extract_edges(
        request_for(
            "src/omnibase_core/client.py",
            f"from omnibase_core.nodes.node_beta.{sub} import {name}",
        )
    )
    assert edges[0].seam == seam


@pytest.mark.parametrize("package", REGISTRY_PACKAGES)
def test_registry_packages(package: str) -> None:
    if package == "omnibase_core":
        source = "from omnibase_core.nodes.node_beta.handlers import handle"
        expected = "outside->node"
    else:
        source = f"from {package}.nodes.node_remote.handlers import handle"
        expected = "cross-repo->node"
    edges, _ = extract_edges(request_for("client.py", source))
    assert edges[0].kind == expected


def test_node_without_initializer_is_still_a_directory() -> None:
    request = ModelBoundaryImportCheckInput(
        repo_packages=("example",),
        files=(
            ModelBoundaryImportSourceFile(
                path="src/example/nested/nodes/node_x/handler.py", source=""
            ),
            ModelBoundaryImportSourceFile(
                path="src/example/client.py",
                source="import example.nested.nodes.node_x",
            ),
        ),
    )
    assert extract_edges(request)[0][0].kind == "outside->node"


def test_new_stale_and_baselined_findings() -> None:
    request = request_for(
        "src/omnibase_core/client.py",
        "from omnibase_core.nodes.node_beta.handlers import handle",
    )
    edge = extract_edges(request)[0][0]
    handler = NodeBoundaryImportCheckCompute()
    report = handler.handle(request)
    assert report.overall_status == "FAIL"
    assert report.provenance.validators_run == ("node-boundary-imports",)
    finding = report.findings[0]
    assert finding.rule_id == "new-boundary-edge"
    assert finding.location == "src/omnibase_core/client.py:1"
    for text in (
        edge.identity,
        edge.kind,
        edge.seam,
        "core/compat",
        "spi/core",
        "layering-exceptions.yaml",
        "contract on the bus",
        "never widen the baseline",
    ):
        assert text in finding.message
    baselined = request.model_copy(update={"baseline_edges": (edge.identity,)})
    assert handler.handle(baselined).overall_status == "PASS"
    retired = baselined.model_copy(update={"files": request.files[:-1]})
    report = handler.handle(retired)
    assert report.overall_status == "FAIL"
    assert report.findings[0].rule_id == "stale-baseline-entry"


@pytest.mark.parametrize("source", ["bad python !!!", "\x00", "\udcff"])
def test_unparseable_error(source: str) -> None:
    report = NodeBoundaryImportCheckCompute().handle(request_for("broken.py", source))
    assert report.overall_status == "ERROR"
    assert any(f.rule_id == "unparseable-file" for f in report.findings)


@pytest.mark.parametrize(
    "edges", [("broken",), ("z -> x", "a -> b"), ("a -> b", "a -> b")]
)
def test_malformed_inline_baseline_error(edges: tuple[str, ...]) -> None:
    report = NodeBoundaryImportCheckCompute().handle(
        request_for("valid.py", "").model_copy(update={"baseline_edges": edges})
    )
    assert report.overall_status == "ERROR"
    assert report.findings[0].rule_id == "malformed-baseline"


def test_zero_files_error() -> None:
    report = NodeBoundaryImportCheckCompute().handle(ModelBoundaryImportCheckInput())
    assert report.overall_status == "ERROR"
    assert "zero files" in report.findings[0].message


def test_baseline_render_roundtrip() -> None:
    assert parse_baseline(render_baseline(("z -> x", "a -> b")), "baseline.yaml") == (
        "a -> b",
        "z -> x",
    )


def test_frozen_extra_forbid_models() -> None:
    source = ModelBoundaryImportSourceFile(path="a.py", source="")
    with pytest.raises(ValidationError):
        source.path = "b.py"
    with pytest.raises(ValidationError):
        ModelBoundaryImportCheckInput.model_validate({"unknown": True})
