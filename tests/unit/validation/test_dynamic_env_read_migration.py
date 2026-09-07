# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The ten dynamic env reads are migrated to typed bindings (OMN-17554).

The OMN-13566 AST gate (``omnibase_core.validators.no_new_os_environ``) can only
see reads whose key is a string literal. Every read this ticket owns had a
*computed* key — ``os.environ.get(env_var)`` inside a mapping loop, a
``f"{prefix}{field.upper()}"`` builder, a comprehension over an indicator list —
so all ten were invisible to it and returned a clean bill of health while the
raw reads were still there.

This test closes that hole for the owned files: it counts every ``os.environ`` /
``os.getenv`` reference by AST, literal key or not, and pins the exact residual
per file. A residual is not a suppression — each one is named below with the
reason it is out of this ticket's slice — but the count cannot grow silently and
the migrated sites cannot come back.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SRC = Path(__file__).resolve().parents[3] / "src" / "omnibase_core"

# path -> (expected env-read count, why any residual is out of this slice)
EXPECTED_ENV_READS: dict[str, tuple[int, str]] = {
    "constants/constants_workflow.py": (
        0,
        "the three workflow limits are fixed immutable Core ceilings",
    ),
    "doctor/checks/check_env_vars.py": (
        0,
        "the binding source is the declared ~/.onex/config.yaml",
    ),
    "infrastructure/node_config_provider.py": (
        0,
        "node config keys resolve through declared ${env.ONEX_*} references",
    ),
    "mixins/mixin_effect_execution.py": (
        0,
        "${env.VAR} placeholders resolve through the shared overlay resolver",
    ),
    "models/configuration/model_database_connection_config.py": (
        0,
        "declared ONEX_DB_* binding table",
    ),
    "models/configuration/model_event_bus_config.py": (
        2,
        "ModelEventBusConfig.default() bootstrap reads: pre-existing, allowlisted, "
        "not among the ten dynamic reads this ticket owns",
    ),
    "models/configuration/model_rest_api_connection_config.py": (
        0,
        "declared ONEX_API_* binding table",
    ),
    "models/security/model_secret_backend.py": (
        3,
        "structural platform-detection reads (KUBERNETES_SERVICE_HOST, NODE_ENV, "
        "ENVIRONMENT): literal, allowlisted, owned by OMN-17525/OMN-17555",
    ),
    "models/security/model_secure_credentials.py": (
        1,
        "the os.environ prefix scan in create_from_env_with_fallbacks is a key "
        "enumeration, not a keyed read, and is not among the ten",
    ),
    "overlays/contract_env_ref.py": (
        2,
        "the sanctioned ${env.VAR} overlay boundary every migrated site resolves "
        "through; explicitly outside this migration slice",
    ),
}


class _EnvReadCounter(ast.NodeVisitor):
    """Count every ``os.environ`` / ``os.getenv`` reference, literal key or not."""

    def __init__(self) -> None:
        self.hits: list[int] = []

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if (
            node.attr in {"environ", "getenv"}
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
        ):
            self.hits.append(node.lineno)
        self.generic_visit(node)


def _count(path: Path) -> list[int]:
    counter = _EnvReadCounter()
    counter.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    return counter.hits


@pytest.mark.parametrize("relative", sorted(EXPECTED_ENV_READS))
def test_env_read_count_is_pinned(relative: str) -> None:
    expected, reason = EXPECTED_ENV_READS[relative]
    path = _SRC / relative
    assert path.is_file(), path
    lines = _count(path)
    assert len(lines) == expected, (
        f"{relative}: expected {expected} os.environ/os.getenv reference(s) "
        f"({reason}), found {len(lines)} at lines {lines}"
    )


def test_counter_reports_a_true_nonzero() -> None:
    """Positive control: a zero from this counter is a measured zero."""
    tree = ast.parse("import os\nx = os.environ.get(k)\ny = os.getenv(j)\n")
    counter = _EnvReadCounter()
    counter.visit(tree)
    assert counter.hits == [2, 3]


def test_counter_reports_a_true_zero() -> None:
    """Negative control: unrelated attribute access is not counted."""
    tree = ast.parse("import os\nx = os.path.join('a', 'b')\ny = other.environ\n")
    counter = _EnvReadCounter()
    counter.visit(tree)
    assert counter.hits == []


def test_static_env_gate_is_clean_for_every_owned_file() -> None:
    """The OMN-13566 literal-key gate also passes on every owned file."""
    from omnibase_core.validators.no_new_os_environ import validate_paths

    paths = [_SRC / relative for relative in sorted(EXPECTED_ENV_READS)]
    findings = validate_paths(paths)
    assert findings == [], [f.format() for f in findings]
