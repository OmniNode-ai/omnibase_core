# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule data of the ci-inheritance node moves with its contract (OMN-21518).

Every ``parameters`` key of ``ci_inheritance.validation.yaml`` changes a verdict, a
message or a command line default when mutated, and the node ``contract.yaml``
binds the handler.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input import (
    ModelCiInheritanceCheckInput,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_reference_input import (
    ModelCiInheritanceReferenceInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_ci_inheritance_check_compute import (
    runtime_ci_inheritance_check as runtime,
)
from omnibase_core.nodes.node_ci_inheritance_check_compute.handler_ci_inheritance import (
    HandlerCiInheritance,
)

pytestmark = pytest.mark.unit

NODE_DIR = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "omnibase_core"
    / "nodes"
    / "node_ci_inheritance_check_compute"
)

_OTHER = "jobs:\n  a:\n    uses: OmniNode-ai/omniclaude/.github/workflows/x.yml@abc\n"
_CORE = "jobs:\n  a:\n    uses: OmniNode-ai/omnibase_core/.github/workflows/g.yml@abc\n"


def _mutated(rule_id: str, key: str, value: object) -> ModelValidatorSubcontract:
    contract = runtime.load_contract()
    rules = tuple(
        row.model_copy(update={"parameters": {**(row.parameters or {}), key: value}})
        if row.rule_id == rule_id
        else row
        for row in contract.rules
    )
    return contract.model_copy(update={"rules": rules})


def _handle(
    contract: ModelValidatorSubcontract, base: dict[str, str], head: dict[str, str]
) -> tuple[str, list[str], list[str | None]]:
    report = HandlerCiInheritance().handle(
        ModelCiInheritanceReferenceInput(
            check=ModelCiInheritanceCheckInput(
                organization="OmniNode-ai",
                host_repository="omnibase_core",
                base_files=[ModelSourceFile(path=p, source=s) for p, s in base.items()],
                head_files=[ModelSourceFile(path=p, source=s) for p, s in head.items()],
            ),
            rules=runtime.rules_from_contract(contract),
        )
    )
    return (
        report.overall_status,
        [f.message for f in report.findings],
        [f.remediation for f in report.findings],
    )


def test_every_rule_parameter_is_covered_by_a_mutation_case() -> None:
    declared = {
        (row.rule_id, key)
        for row in runtime.load_contract().rules
        for key in (row.parameters or {})
    }
    assert declared == set(_HANDLER_CASES) | set(_CLI_CASES)


_HANDLER_CASES: dict[tuple[str, str], str] = {
    ("org_reference_pattern", "uses_pattern"): "pattern",
    ("new_org_reference", "message_template"): "new message",
    ("new_org_reference", "remediation_template"): "remediation",
    ("existing_org_reference", "message_template"): "existing message",
}

_CLI_CASES: dict[tuple[str, str], str] = {
    ("command_line_defaults", "head_dir"): "head",
    ("command_line_defaults", "organization"): "org",
    ("command_line_defaults", "host_repository"): "host",
    ("command_line_defaults", "workflow_patterns"): "patterns",
}


def test_uses_pattern_decides_what_is_a_reference() -> None:
    changed = _mutated(
        "org_reference_pattern",
        "uses_pattern",
        r"^\s*(?:-\s+)?calls:\s*(?P<value>\S+)",
    )
    assert _handle(runtime.load_contract(), {}, {"a.yml": _OTHER})[0] == "FAIL"
    assert _handle(changed, {}, {"a.yml": _OTHER})[0] == "PASS"
    assert (
        _handle(changed, {}, {"a.yml": _OTHER.replace("uses:", "calls:")})[0] == "FAIL"
    )


def test_new_reference_message_template_is_read_from_the_rule() -> None:
    changed = _mutated(
        "new_org_reference", "message_template", "NEW {location} {target} {host}"
    )
    _, messages, _ = _handle(changed, {}, {"a.yml": _OTHER})
    assert messages == [
        "NEW a.yml:3 OmniNode-ai/omniclaude/.github/workflows/x.yml omnibase_core"
    ]


def test_new_reference_remediation_template_is_read_from_the_rule() -> None:
    changed = _mutated(
        "new_org_reference", "remediation_template", "FIX {organization} {host}"
    )
    _, _, remediation = _handle(changed, {}, {"a.yml": _OTHER})
    assert remediation == ["FIX OmniNode-ai omnibase_core"]


def test_existing_reference_message_template_is_read_from_the_rule() -> None:
    changed = _mutated("existing_org_reference", "message_template", "OLD {target}")
    status, messages, _ = _handle(changed, {"a.yml": _OTHER}, {"a.yml": _OTHER})
    assert status == "WARN"
    assert messages == ["OLD OmniNode-ai/omniclaude/.github/workflows/x.yml"]


def _cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    contract: ModelValidatorSubcontract,
) -> tuple[int, str]:
    """Run the CLI over tmp_path with `contract` in place of the packaged one."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runtime, "load_contract", lambda: contract)
    buffer: list[str] = []
    monkeypatch.setattr(runtime.sys.stdout, "write", lambda text: buffer.append(text))
    exit_code = runtime.main(["--base-dir", "base"])
    return exit_code, "".join(buffer)


def _tree(tmp_path: Path, files: dict[str, str]) -> None:
    (tmp_path / "base").mkdir()
    for name, text in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)


def test_head_dir_default_is_read_from_the_rule(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _tree(tmp_path, {".github/workflows/ci.yml": _CORE, "wf/new.yaml": _OTHER})
    packaged = runtime.load_contract()
    assert _cli(monkeypatch, tmp_path, packaged)[0] == 0
    code, out = _cli(
        monkeypatch, tmp_path, _mutated("command_line_defaults", "head_dir", "wf")
    )
    assert code == 1
    assert "FAIL: 1 new reusable CI reference(s)" in out


def test_organization_default_is_read_from_the_rule(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _tree(tmp_path, {".github/workflows/new.yml": _OTHER})
    assert _cli(monkeypatch, tmp_path, runtime.load_contract())[0] == 1
    code, out = _cli(
        monkeypatch,
        tmp_path,
        _mutated("command_line_defaults", "organization", "acme"),
    )
    assert code == 0
    assert out.startswith("OK: no new reusable CI reference")


def test_host_repository_default_is_read_from_the_rule(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _tree(tmp_path, {".github/workflows/new.yml": _CORE})
    assert _cli(monkeypatch, tmp_path, runtime.load_contract())[0] == 0
    code, out = _cli(
        monkeypatch,
        tmp_path,
        _mutated("command_line_defaults", "host_repository", "omniclaude"),
    )
    assert code == 1
    assert "outside omniclaude" in out


def test_workflow_patterns_default_is_read_from_the_rule(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _tree(
        tmp_path,
        {".github/workflows/ci.yml": _CORE, ".github/workflows/new.yaml": _OTHER},
    )
    assert _cli(monkeypatch, tmp_path, runtime.load_contract())[0] == 1
    code, _ = _cli(
        monkeypatch,
        tmp_path,
        _mutated("command_line_defaults", "workflow_patterns", ["*.yml"]),
    )
    assert code == 0


def test_node_contract_binds_the_handler() -> None:
    contract = yaml.safe_load((NODE_DIR / "contract.yaml").read_text("utf-8"))
    routing = contract["handler_routing"]
    module_name, class_name = routing["default_handler"].split(":")
    assert (NODE_DIR / f"{module_name}.py").is_file()
    module = importlib.import_module(
        f"omnibase_core.nodes.node_ci_inheritance_check_compute.{module_name}"
    )
    assert getattr(module, class_name) is HandlerCiInheritance
    for key in ("input_model", "output_model"):
        model_module, model_name = contract[key].rsplit(".", 1)
        assert hasattr(importlib.import_module(model_module), model_name)
    assert contract["input_model"].endswith(".ModelCiInheritanceReferenceInput")
