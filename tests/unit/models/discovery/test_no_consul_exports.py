# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression test: no consul exports in models/discovery or models/intents.

Validates via AST import-graph inspection (not grep) that omnibase_core exposes
no consul-specific types from its public module surfaces.

Related ticket: OMN-3993 — omnibase_core consul model/intent/enum removal
"""

import ast
import importlib.util
from pathlib import Path

import pytest


def _parse_all_exports(init_path: Path) -> list[str]:
    """Parse __all__ list from an __init__.py file using AST (not import)."""
    tree = ast.parse(init_path.read_text())
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
            and isinstance(node.value, ast.List)
        ):
            return [
                elt.s  # type: ignore[attr-defined]
                for elt in node.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.s, str)
            ]
    return []


def _find_src_root() -> Path:
    """Locate the omnibase_core src root from the installed package location."""
    spec = importlib.util.find_spec("omnibase_core")
    assert spec is not None and spec.origin is not None, "omnibase_core not installed"
    return Path(spec.origin).parent


@pytest.mark.unit
class TestNoConsulExports:
    """Assert that consul types and fields are absent from public module exports."""

    def test_discovery_init_has_no_consul_exports(self) -> None:
        """models/discovery/__init__.py __all__ must not contain any consul-named names."""
        src_root = _find_src_root()
        init_path = src_root / "models" / "discovery" / "__init__.py"
        assert init_path.exists(), f"Missing: {init_path}"

        exports = _parse_all_exports(init_path)
        consul_exports = [n for n in exports if "consul" in n.lower()]
        assert consul_exports == [], (
            f"consul exports found in models/discovery/__init__.py: {consul_exports}"
        )

    def test_intents_init_has_no_consul_exports(self) -> None:
        """models/intents/__init__.py __all__ must not contain any consul-named names."""
        src_root = _find_src_root()
        init_path = src_root / "models" / "intents" / "__init__.py"
        assert init_path.exists(), f"Missing: {init_path}"

        exports = _parse_all_exports(init_path)
        consul_exports = [n for n in exports if "consul" in n.lower()]
        assert consul_exports == [], (
            f"consul exports found in models/intents/__init__.py: {consul_exports}"
        )

    def test_discovery_module_has_no_consul_model_files(self) -> None:
        """Deleted consul model files must not exist in the discovery package."""
        src_root = _find_src_root()
        discovery_dir = src_root / "models" / "discovery"

        deleted_files = [
            "model_consul_event_bridge_input.py",
            "model_consul_event_bridge_output.py",
            "model_hub_consul_registration_io.py",
            "model_hubconsulregistrationoutput.py",
        ]
        for filename in deleted_files:
            path = discovery_dir / filename
            assert not path.exists(), f"Deleted consul model file still present: {path}"

    def test_intents_module_has_no_consul_intent_files(self) -> None:
        """Deleted consul intent files must not exist in the intents package."""
        src_root = _find_src_root()
        intents_dir = src_root / "models" / "intents"

        deleted_files = [
            "model_consul_deregister_intent.py",
            "model_consul_register_intent.py",
        ]
        for filename in deleted_files:
            path = intents_dir / filename
            assert not path.exists(), (
                f"Deleted consul intent file still present: {path}"
            )

    def test_discovery_model_files_have_no_consul_field_names(self) -> None:
        """Public discovery model files must not define consul_* field names."""
        src_root = _find_src_root()
        discovery_dir = src_root / "models" / "discovery"

        for py_file in discovery_dir.glob("model_*.py"):
            tree = ast.parse(py_file.read_text())
            consul_assigns: list[str] = []
            for node in ast.walk(tree):
                # Check class-level annotated assignments (Pydantic fields)
                if isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name
                ):
                    name = node.target.id
                    if "consul" in name.lower():
                        consul_assigns.append(name)
            assert consul_assigns == [], (
                f"{py_file.name} still defines consul field(s): {consul_assigns}"
            )

    def test_enum_service_type_has_no_consul_member(self) -> None:
        """EnumServiceType must not contain a CONSUL member."""
        from omnibase_core.enums.enum_service_type import EnumServiceType

        member_names = [m.name for m in EnumServiceType]
        assert "CONSUL" not in member_names, (
            "EnumServiceType.CONSUL still present after consul removal"
        )
