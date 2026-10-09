# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-17427: importing RuntimeLocal and the in-memory bus stays cheap.

A hook process that starts ``RuntimeLocal`` with the in-memory event bus
(``backend_overrides={"event_bus": "inmemory"}``) paid about 1 s of import
before the runtime did 0.09 s of work: the ``runtime``, ``event_bus`` and
``models.*`` package ``__init__`` files eagerly re-exported whole subtrees, and
Python always runs a package's ``__init__`` before any of its submodules, so
importing one leaf module dragged in ``models.core``, ``models.contracts``,
``models.events``, ``mixins`` and about 2,400 modules in all.

Those package ``__init__`` files now resolve their re-exports lazily (PEP 562
module ``__getattr__``). These tests pin:

1. The import footprint: a fresh interpreter that imports ``RuntimeLocal``, its
   event-driven ``LocalRuntimeBusAdapter`` and ``EventBusInmemory`` loads none of
   the leaf modules that dominated the old import tree, and stays inside a
   module-count budget (2,088 ``omnibase_core`` modules before, 549 after).
   Asserted on the module set, which is deterministic; wall time is not
   asserted.
2. The public surface: every name a lazy package ``__init__`` exports still
   resolves to the same object its defining module holds, ``__all__`` names
   resolve, and ``dir()`` lists them.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

import omnibase_core

PACKAGE_ROOT = Path(omnibase_core.__file__).parent

# Leaf modules that dominated the RuntimeLocal + in-memory bus import tree when
# package __init__ files re-exported eagerly. None of them is needed to
# construct or run the runtime or the bus. (The lazy package __init__ modules
# themselves, such as ``omnibase_core.models.core``, are cheap and may load.)
HEAVY_MODULES = (
    "omnibase_core.mixins.mixin_canonical_serialization",
    "omnibase_core.mixins.mixin_node_type_validator",
    "omnibase_core.models.contracts.model_algorithm_config",
    "omnibase_core.models.core.model_contract_content",
    "omnibase_core.models.core.model_node_base",
    "omnibase_core.models.core.model_node_metadata",
    "omnibase_core.models.discovery.model_introspection_response_event",
    "omnibase_core.models.events.model_event_publish_intent",
    "omnibase_core.models.health.model_health_check",
    "omnibase_core.models.security.model_secret_config",
    "omnibase_core.models.services.model_external_service_config",
    "omnibase_core.models.validation.model_cross_repo_validation_orchestrator_result",
)

# 549 measured on 2026-10-09 (2,088 before the lazy package __init__ files).
MODULE_BUDGET = 700

# RuntimeLocal imports LocalRuntimeBusAdapter on first use of the
# event-driven (handler_routing) path, which is the path a node contract such
# as omniclaude's node_git_effect takes.
HOOK_IMPORT = (
    "from omnibase_core.runtime.runtime_local import RuntimeLocal\n"
    "from omnibase_core.runtime.runtime_local_adapter import LocalRuntimeBusAdapter\n"
    "from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory\n"
)


def _modules_after(source: str) -> list[str]:
    probe = (
        "import json, sys\n"
        f"{source}"
        "print(json.dumps(sorted(m for m in sys.modules "
        "if m == 'omnibase_core' or m.startswith('omnibase_core.'))))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    loaded: list[str] = json.loads(completed.stdout.strip().splitlines()[-1])
    return loaded


@pytest.mark.unit
def test_heavy_module_names_still_exist() -> None:
    """A renamed sentinel would make the footprint assertion pass vacuously."""
    missing = [name for name in HEAVY_MODULES if importlib.util.find_spec(name) is None]
    assert missing == []


@pytest.mark.unit
def test_runtime_local_and_inmemory_bus_do_not_load_heavy_trees() -> None:
    loaded = set(_modules_after(HOOK_IMPORT))

    # Positive control: the probe sees the modules the import did load.
    assert "omnibase_core.runtime.runtime_local" in loaded
    assert "omnibase_core.runtime.runtime_local_adapter" in loaded
    assert "omnibase_core.event_bus.event_bus_inmemory" in loaded

    dragged = sorted(set(HEAVY_MODULES) & loaded)
    assert dragged == [], (
        "importing RuntimeLocal and EventBusInmemory loaded heavy modules "
        f"({len(loaded)} omnibase_core modules in all): {dragged}"
    )
    assert len(loaded) <= MODULE_BUDGET, (
        f"importing RuntimeLocal and EventBusInmemory loaded {len(loaded)} "
        f"omnibase_core modules, over the budget of {MODULE_BUDGET}"
    )


@pytest.mark.unit
def test_footprint_probe_detects_a_heavy_import() -> None:
    """Positive control: the probe reports a heavy module when it is loaded."""
    loaded = set(_modules_after("import omnibase_core.models.core.model_node_base\n"))
    assert "omnibase_core.models.core.model_node_base" in loaded
    assert set(HEAVY_MODULES) & loaded
    assert len(loaded) > MODULE_BUDGET


def _lazy_package_names() -> list[str]:
    names: list[str] = []
    for init in sorted(PACKAGE_ROOT.rglob("__init__.py")):
        tree = ast.parse(init.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "_LAZY_IMPORTS"
            for node in tree.body
        ):
            rel = init.parent.relative_to(PACKAGE_ROOT.parent)
            names.append(".".join(rel.parts))
    return names


LAZY_PACKAGES = _lazy_package_names()


@pytest.mark.unit
def test_lazy_packages_cover_runtime_event_bus_and_models() -> None:
    assert "omnibase_core.runtime" in LAZY_PACKAGES
    assert "omnibase_core.event_bus" in LAZY_PACKAGES
    assert "omnibase_core.models.common" in LAZY_PACKAGES
    assert "omnibase_core.models.contracts" in LAZY_PACKAGES
    assert "omnibase_core.protocols" in LAZY_PACKAGES
    assert "omnibase_core.models.event_bus" in LAZY_PACKAGES


@pytest.mark.unit
@pytest.mark.parametrize("package_name", LAZY_PACKAGES)
def test_lazy_package_exports_resolve(package_name: str) -> None:
    package = importlib.import_module(package_name)
    table: dict[str, tuple[str, str | None]] = package._LAZY_IMPORTS
    assert table, f"{package_name} has an empty lazy table"
    for name, (module_name, attr) in table.items():
        value = getattr(package, name)
        source = importlib.import_module(module_name)
        expected = source if attr is None else getattr(source, attr)
        assert value is expected, f"{package_name}.{name} resolved to another object"
    for name in getattr(package, "__all__", ()):
        assert hasattr(package, name), f"{package_name}.__all__ names missing {name}"
    assert set(table) <= set(dir(package))
    assert not hasattr(package, "no_such_attribute_omn17427")
