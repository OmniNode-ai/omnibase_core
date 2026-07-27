# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Regression tests for OMN-14944.

``del sys.modules[...]`` loops with no restore (used by several tests to
force a fresh import of ``omnibase_core.*``) permanently evicted matched
entries from the interpreter's module cache for the rest of that pytest
worker process. Two independent downstream failure modes were confirmed:

- B2 (enum identity split): a later local/deferred re-import of an evicted
  module mints a NEW class object distinct from one already bound at
  collection time elsewhere in the process (identity-based ``in`` /
  ``==`` checks then fail even though both sides print identically).
- B1 (Pydantic forward-ref break): ``RegistryNode`` in
  ``model_contract_graph.py`` uses ``from __future__ import annotations``
  and resolves its ``RegistryTransitionDecl`` forward reference lazily via
  ``sys.modules[cls.__module__].__dict__``; once that module entry is
  evicted, construction raises
  ``PydanticUserError: RegistryNode is not fully defined``.

These tests pin both minimal repros from the OMN-14944 diagnosis as
permanent regressions.

OMN-14985 residual: OMN-14944 named five contaminator sites but the merged
fix (omnibase_core#1484) only converted three of them
(``test_init_exports.py``, ``test_init_fast.py``,
``test_no_circular_imports.py``) to ``isolated_sys_modules``. Two more
(``tests/unit/models/contracts/test_model_fast_imports.py`` and
``test_model_lazy_imports.py``, two sites) were converted here.
``test_no_unrestored_del_sys_modules_in_tests`` below is a static guard
against this whole class recurring anywhere in ``tests/``.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from tests.unit.conftest import isolated_sys_modules


def test_init_purge_no_circular_imports_does_not_pollute_reserved_enum_validator() -> (
    None
):
    """B2 regression: the exact minimal-repro pair from the OMN-14944 diagnosis.

    Running ``test_init_no_circular_imports`` (an unconditional
    ``omnibase_core.*`` purge) ahead of
    ``TestCanonicalImportPaths`` in the same pytest process previously left
    ``EnumExecutionMode`` (imported at collection time by the reserved-enum
    validator test module) permanently desynced from the class object a
    later local re-import inside the test bodies would mint -- failing
    ``EnumExecutionMode.CONDITIONAL in RESERVED_EXECUTION_MODES`` by
    identity. Restoring the purged ``sys.modules`` entries (OMN-14944 fix,
    ``isolated_sys_modules`` in ``tests/unit/conftest.py``) makes this pair
    pass in a single process. Invoked as a subprocess (not in-process) so
    this test's own collection/imports cannot mask the ordering effect
    under test.
    """
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        check=False,
        args=[
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            "tests/unit/test_init_exports.py::TestInitCircularImports::test_init_no_circular_imports",
            "tests/unit/validation/test_validator_reserved_enum.py::TestCanonicalImportPaths",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        "sys.modules-purge pollution regressed (OMN-14944 B2):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_registry_node_construction_survives_omnibase_core_purge() -> None:
    """B1 regression: RegistryNode construction after an omnibase_core purge.

    Direct-script proof from the OMN-14944 diagnosis, adapted to restore
    ``sys.modules`` afterward via ``isolated_sys_modules`` so this
    regression test does not itself become a ninth contaminator.
    """
    from omnibase_core.navigation.model_contract_graph import RegistryNode

    with isolated_sys_modules(lambda key: key.startswith("omnibase_core")):
        node = RegistryNode(node_id="n1", schema_version="1.0.0")

    assert node.node_id == "n1"
    assert node.schema_version == "1.0.0"


def _is_sys_modules_subscript(expr: ast.expr) -> bool:
    """True if ``expr`` is the AST for ``sys.modules[...]``."""
    return (
        isinstance(expr, ast.Subscript)
        and isinstance(expr.value, ast.Attribute)
        and expr.value.attr == "modules"
        and isinstance(expr.value.value, ast.Name)
        and expr.value.value.id == "sys"
    )


def _enclosing_function(
    parents: dict[ast.AST, ast.AST], node: ast.AST
) -> ast.AST | None:
    current: ast.AST | None = node
    while current is not None:
        parent = parents.get(current)
        if isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef):
            return parent
        current = parent
    return None


def _function_restores_sys_modules(func: ast.AST) -> bool:
    """True if ``func`` either uses ``isolated_sys_modules`` as a context
    manager, or manually restores an evicted ``sys.modules`` entry
    (``sys.modules[key] = ...`` or ``sys.modules.update(...)``) somewhere
    in its body.
    """
    for node in ast.walk(func):
        if isinstance(node, ast.With):
            for item in node.items:
                call = item.context_expr
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "isolated_sys_modules"
                ):
                    return True
        if isinstance(node, ast.Assign) and any(
            _is_sys_modules_subscript(target) for target in node.targets
        ):
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "modules"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "sys"
        ):
            return True
    return False


def test_no_unrestored_del_sys_modules_in_tests() -> None:
    """Guard (OMN-14985): no test file may evict a ``sys.modules`` entry
    without restoring it.

    A bare ``del sys.modules[key]`` loop with no restore is exactly the
    OMN-14944 contaminator class -- it permanently evicts matched entries
    for the rest of that pytest worker process, corrupting unrelated later
    tests via class-identity splits or Pydantic forward-ref breaks. This
    statically scans every ``tests/**/*.py`` file (excluding ``conftest.py``,
    which implements the restore primitive itself) and fails if any
    ``del sys.modules[...]`` is not covered, within its enclosing function,
    by either an ``isolated_sys_modules`` context manager or an explicit
    manual restore assignment.
    """
    repo_root = Path(__file__).resolve().parents[2]
    tests_root = repo_root / "tests"
    conftest_paths = {p.resolve() for p in tests_root.rglob("conftest.py")}
    violations: list[str] = []

    for path in sorted(tests_root.rglob("*.py")):
        resolved = path.resolve()
        if resolved in conftest_paths:
            continue
        source = path.read_text(encoding="utf-8")
        if "del sys.modules[" not in source:
            continue

        tree = ast.parse(source, filename=str(path))
        parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent

        for node in ast.walk(tree):
            if not isinstance(node, ast.Delete):
                continue
            if not any(_is_sys_modules_subscript(t) for t in node.targets):
                continue

            func = _enclosing_function(parents, node)
            if func is not None and _function_restores_sys_modules(func):
                continue

            violations.append(f"{path.relative_to(repo_root)}:{node.lineno}")

    assert not violations, (
        "Unrestored `del sys.modules[...]` found (OMN-14944 contaminator "
        "class -- see OMN-14985). Wrap the deletion in "
        "`with isolated_sys_modules(predicate):` "
        "(tests/unit/conftest.py) or add an explicit restore:\n" + "\n".join(violations)
    )
