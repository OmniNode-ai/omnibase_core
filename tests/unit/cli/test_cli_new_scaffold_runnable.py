# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Executable acceptance test for the ``onex new node`` scaffold (OMN-16679).

The getting-started flow is ``onex init`` → ``onex new node`` → run it. Before
OMN-16679 that flow dead-ended: the generated ``contract.yaml`` declared
``handler_routing.default`` (a bare module path) while
:meth:`RuntimeLocal._resolve_default_handler` reads ``handler_routing.default_handler``
in ``module_ref:ClassName`` form, the generated handler was a module-level
function rather than a canonical definition-B handler *class*, and the contract
declared no ``terminal_event`` — so ``run_async`` took its hard-fail branch and a
freshly scaffolded node was not runnable without hand edits.

These tests scaffold a real project into ``tmp_path`` and actually EXECUTE the
generated node through :class:`RuntimeLocal`. A shape-only assertion would not
have caught the original defect, so the acceptance bar here is a real run.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli
from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.runtime.runtime_local import RuntimeLocal

NODE_TYPES = ("compute", "effect", "reducer", "orchestrator")


@pytest.fixture
def importable_src() -> Iterator[list[str]]:
    """Restore ``sys.path`` and ``sys.modules`` around a scaffold import.

    Scaffolded packages are imported by the runtime under a name that only
    exists for the duration of the test; leaving either global mutated would
    leak across xdist-shared workers.
    """
    added: list[str] = []
    original_path = list(sys.path)
    original_modules = dict(sys.modules)
    yield added
    sys.path[:] = original_path
    for name in set(sys.modules) - set(original_modules):
        del sys.modules[name]
    # Put the pre-existing entries back verbatim. The purge above only removes
    # names the scaffold run itself introduced, so this restore is a no-op in
    # the common case -- but it makes the fixture provably incapable of leaking
    # an OMN-14944-class eviction even if a scaffold import displaces an
    # already-cached module, and it is the explicit restore the OMN-14985
    # ratchet (test_no_unrestored_del_sys_modules_in_tests) requires to see.
    sys.modules.update(original_modules)


def _scaffold(
    tmp_path: Path, project_name: str, node_name: str, node_type: str
) -> Path:
    """Run ``onex init`` + ``onex new node`` and return the contract path.

    Args:
        tmp_path: pytest temporary directory.
        project_name: Project (and package) name to initialize.
        node_name: Node name to scaffold.
        node_type: One of :data:`NODE_TYPES`.

    Returns:
        Path to the generated ``contract.yaml``.
    """
    runner = CliRunner()

    init_result = runner.invoke(cli, ["init", project_name, "--path", str(tmp_path)])
    assert init_result.exit_code == 0, f"onex init failed: {init_result.output}"

    project_root = tmp_path / project_name
    new_result = runner.invoke(
        cli,
        [
            "new",
            "node",
            node_name,
            "--type",
            node_type,
            "--project-root",
            str(project_root),
        ],
    )
    assert new_result.exit_code == 0, f"onex new node failed: {new_result.output}"

    contract = (
        project_root / "src" / project_name / "nodes" / node_name / "contract.yaml"
    )
    assert contract.exists(), f"scaffold produced no contract at {contract}"
    return contract


@pytest.mark.unit
def test_scaffolded_compute_node_runs_with_zero_hand_edits(
    tmp_path: Path, importable_src: list[str]
) -> None:
    """AC3: ``onex init`` → ``onex new node`` → run completes, no hand edits.

    This is the acceptance bar for OMN-16679. It fails on the pre-fix scaffold
    with ``EnumWorkflowResult.FAILED``.
    """
    contract = _scaffold(tmp_path, "runnable_proj", "my_first_node", "compute")

    src_root = str(tmp_path / "runnable_proj" / "src")
    sys.path.insert(0, src_root)
    importable_src.append(src_root)

    runtime = RuntimeLocal(contract, state_root=tmp_path / ".onex_state")
    assert runtime.run() == EnumWorkflowResult.COMPLETED


@pytest.mark.unit
@pytest.mark.parametrize("node_type", NODE_TYPES)
def test_scaffolded_node_of_every_type_runs(
    tmp_path: Path, importable_src: list[str], node_type: str
) -> None:
    """AC5: every archetype the CLI offers scaffolds into a runnable node."""
    project = f"all_types_{node_type}"
    contract = _scaffold(tmp_path, project, f"node_{node_type}", node_type)

    src_root = str(tmp_path / project / "src")
    sys.path.insert(0, src_root)
    importable_src.append(src_root)

    runtime = RuntimeLocal(contract, state_root=tmp_path / ".onex_state")
    assert runtime.run() == EnumWorkflowResult.COMPLETED


@pytest.mark.unit
def test_scaffolded_contract_binds_handler_in_module_ref_class_form(
    tmp_path: Path,
) -> None:
    """AC1: the binding key and value shape the runtime actually reads.

    ``handler_routing.default`` (the pre-fix key) is read by nothing;
    ``_resolve_default_handler`` requires ``default_handler`` and rejects any
    value without a ``:`` separator.
    """
    contract_path = _scaffold(tmp_path, "binding_proj", "parser_node", "compute")
    contract = yaml.safe_load(contract_path.read_text())

    routing = contract["handler_routing"]
    assert "default" not in routing, (
        "handler_routing.default is a dead key — the runtime reads default_handler"
    )
    default_handler = routing["default_handler"]
    module_ref, _, class_name = default_handler.partition(":")
    assert class_name, (
        f"default_handler must be module_ref:ClassName, got {default_handler!r}"
    )
    assert module_ref == "binding_proj.nodes.parser_node.handlers.handler_parser_node"
    assert class_name == "HandlerParserNode"

    assert contract["terminal_event"], "contract must declare a terminal_event topic"

    handler_block = contract["handler"]
    assert handler_block["module"] == module_ref
    assert handler_block["class"] == class_name
    assert (
        handler_block["input_model"]
        == "binding_proj.nodes.parser_node.models.models_parser_node.ParserNodeInput"
    ), "the runtime builds its initial payload from handler.input_model"


@pytest.mark.unit
def test_scaffolded_handler_is_canonical_definition_b(tmp_path: Path) -> None:
    """AC2: definition-B handler class, no envelope types in the core.

    Returning ``ModelHandlerOutput`` or referencing ``ModelEventEnvelope`` would
    hard-fail the OMN-14355 canon-shape ratchet as ``envelope_in_core``.
    """
    contract = _scaffold(tmp_path, "canon_proj", "widget_node", "compute")
    handler = (contract.parent / "handlers" / "handler_widget_node.py").read_text()

    assert "class HandlerWidgetNode:" in handler
    assert "def handle(self, request: WidgetNodeInput) -> WidgetNodeOutput:" in handler
    assert "ModelEventEnvelope" not in handler
    assert "ModelHandlerOutput" not in handler
    assert "NotImplementedError" not in handler, (
        "a scaffolded handler must run; the TODO marks where to add real logic"
    )


@pytest.mark.unit
def test_scaffolded_node_payload_is_the_typed_input_model(
    tmp_path: Path, importable_src: list[str]
) -> None:
    """The handler receives its declared input model, not ``None``.

    ``handler.input_model`` is what ``_build_initial_payload`` resolves; without
    it the runtime passes ``None`` into a handler typed for a request model.
    """
    contract = _scaffold(tmp_path, "payload_proj", "typed_node", "compute")

    src_root = str(tmp_path / "payload_proj" / "src")
    sys.path.insert(0, src_root)
    importable_src.append(src_root)

    from importlib import import_module

    models = import_module("payload_proj.nodes.typed_node.models.models_typed_node")
    handler_mod = import_module(
        "payload_proj.nodes.typed_node.handlers.handler_typed_node"
    )

    seen: list[object] = []
    original_handle = handler_mod.HandlerTypedNode.handle

    def _recording_handle(self: object, request: object) -> object:
        seen.append(request)
        return original_handle(self, request)

    handler_mod.HandlerTypedNode.handle = _recording_handle  # type: ignore[method-assign]
    try:
        runtime = RuntimeLocal(contract, state_root=tmp_path / ".onex_state")
        assert runtime.run() == EnumWorkflowResult.COMPLETED
    finally:
        handler_mod.HandlerTypedNode.handle = original_handle  # type: ignore[method-assign]

    assert len(seen) == 1
    assert isinstance(seen[0], models.TypedNodeInput)
