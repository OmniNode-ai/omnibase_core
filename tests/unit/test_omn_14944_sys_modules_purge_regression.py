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
"""

from __future__ import annotations

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
