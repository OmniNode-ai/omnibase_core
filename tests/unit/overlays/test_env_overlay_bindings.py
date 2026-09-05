# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-17554 — declared overlay bindings, and the single environment read.

The migration these tests pin has two halves. The *declaration* half is
``ModelEnvOverlayBinding``: an env-var-to-field mapping that is validated and
enumerable, so a binding table can be asserted rather than inferred from a loop
body. The *resolution* half is
``omnibase_core.overlays.contract_env_ref``: the one module in core product code
that reads the process environment.

The test that matters most here is the last one — it walks the nine files the
ticket names and asserts none of them performs an environment read of its own.
Without it, a later change could quietly reintroduce one and every other test in
this file would still pass.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.models.configuration.model_env_overlay_binding import (
    ModelEnvOverlayBinding,
)
from omnibase_core.overlays.contract_env_ref import (
    expand_contract_env_refs,
    has_env_prefix,
    resolve_env_value,
    resolve_overlay_binding,
)

pytestmark = pytest.mark.unit

VAR = "ONEX_OMN17554_PROBE"

# The nine files the ticket enumerates, plus the CLI/registry the doctor slice
# touches. None of them may read the environment directly.
MIGRATED_SOURCES = (
    "constants/constants_workflow.py",
    "doctor/checks/check_env_vars.py",
    "doctor/doctor_registry.py",
    "cli/cli_doctor.py",
    "infrastructure/node_config_provider.py",
    "mixins/mixin_effect_execution.py",
    "models/configuration/model_database_connection_config.py",
    "models/configuration/model_event_bus_config.py",
    "models/configuration/model_rest_api_connection_config.py",
    "models/security/model_secret_backend.py",
    "models/security/model_secure_credentials.py",
)

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "omnibase_core"


# ---------------------------------------------------------------------------
# The declaration
# ---------------------------------------------------------------------------


def test_binding_declares_a_variable_and_the_field_it_supplies() -> None:
    binding = ModelEnvOverlayBinding(env_var="ONEX_DB_HOST", field_name="host")
    assert binding.env_var == "ONEX_DB_HOST"
    assert binding.field_name == "host"


def test_binding_accepts_a_dotted_field_path() -> None:
    """The node config provider keys on dotted paths, not bare identifiers."""
    binding = ModelEnvOverlayBinding(
        env_var="ONEX_COMPUTE_MAX_PARALLEL_WORKERS",
        field_name="compute.max_parallel_workers",
    )
    assert binding.field_name == "compute.max_parallel_workers"


def test_binding_is_frozen_and_rejects_extra_fields() -> None:
    binding = ModelEnvOverlayBinding(env_var="ONEX_DB_HOST", field_name="host")
    with pytest.raises(ValidationError):
        binding.env_var = "OTHER"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ModelEnvOverlayBinding(
            env_var="ONEX_DB_HOST",
            field_name="host",
            note="unknown",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    "env_var",
    ["", "ONEX DB HOST", "ONEX-DB-HOST", "1ONEX", "ONEX/DB", "ONEX;rm -rf /"],
)
def test_binding_rejects_a_name_that_is_not_a_legal_variable(env_var: str) -> None:
    """A composed name is validated at declaration, not discovered at read time.

    ``validate_environment_variables`` builds its binding from a caller-supplied
    prefix; a prefix that cannot form a legal name must fail loudly rather than
    resolve to nothing and report the field as merely missing.
    """
    with pytest.raises(ValidationError):
        ModelEnvOverlayBinding(env_var=env_var, field_name="host")


@pytest.mark.parametrize("field_name", ["", "not a field", "trailing.", ".leading"])
def test_binding_rejects_a_malformed_field_path(field_name: str) -> None:
    with pytest.raises(ValidationError):
        ModelEnvOverlayBinding(env_var="ONEX_DB_HOST", field_name=field_name)


# ---------------------------------------------------------------------------
# The resolution
# ---------------------------------------------------------------------------


def test_unset_binding_resolves_to_none_so_the_typed_default_survives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(VAR, raising=False)
    binding = ModelEnvOverlayBinding(env_var=VAR, field_name="probe")
    assert resolve_overlay_binding(binding) is None


def test_set_binding_resolves_to_the_operator_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VAR, "supplied")
    binding = ModelEnvOverlayBinding(env_var=VAR, field_name="probe")
    assert resolve_overlay_binding(binding) == "supplied"


def test_a_blank_value_is_a_value_not_an_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An operator blanking a variable is a deliberate act.

    Collapsing "" to the default would make it impossible to clear a setting,
    and would silently reinstate a value the operator removed on purpose.
    """
    monkeypatch.setenv(VAR, "")
    assert resolve_env_value(VAR, "a-default") == ""
    assert (
        resolve_overlay_binding(ModelEnvOverlayBinding(env_var=VAR, field_name="probe"))
        == ""
    )


def test_inline_default_applies_only_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(VAR, raising=False)
    assert resolve_env_value(VAR, "fallback") == "fallback"
    assert resolve_env_value(VAR) is None
    monkeypatch.setenv(VAR, "real")
    assert resolve_env_value(VAR, "fallback") == "real"


def test_template_expansion_still_rides_the_same_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VAR, "host.example")
    assert (
        expand_contract_env_refs(f"https://${{env.{VAR}}}/x")
        == "https://host.example/x"
    )
    monkeypatch.delenv(VAR, raising=False)
    assert expand_contract_env_refs(f"https://${{env.{VAR}}}/x") == "https:///x"
    assert expand_contract_env_refs(f"${{env.{VAR}:fallback}}") == "fallback"


def test_prefix_probe_reports_namespace_presence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(VAR, raising=False)
    assert has_env_prefix("ONEX_OMN17554_") is False
    monkeypatch.setenv(VAR, "x")
    assert has_env_prefix("ONEX_OMN17554_") is True


# ---------------------------------------------------------------------------
# The invariant
# ---------------------------------------------------------------------------


def _env_read_lines(path: Path) -> list[int]:
    """Line numbers of ``os.environ`` / ``os.getenv`` expressions in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        value = node.value
        if isinstance(value, ast.Name) and value.id == "os":
            if node.attr in {"environ", "getenv"}:
                hits.append(node.lineno)
    return sorted(hits)


def test_the_sanctioned_boundary_does_read_the_environment() -> None:
    """Positive control for the invariant test below.

    An AST walk that returned an empty list because it was looking for the wrong
    node shape would make every file below look clean. This asserts the same
    walk finds the reads that are supposed to be there.
    """
    assert _env_read_lines(_SRC_ROOT / "overlays" / "contract_env_ref.py")


@pytest.mark.parametrize("relative", MIGRATED_SOURCES)
def test_migrated_source_performs_no_environment_read(relative: str) -> None:
    path = _SRC_ROOT / relative
    assert path.is_file(), f"{relative} moved; update MIGRATED_SOURCES"
    assert _env_read_lines(path) == [], (
        f"{relative} reads the process environment directly. "
        "Declare a ModelEnvOverlayBinding and resolve it through "
        "omnibase_core.overlays.contract_env_ref instead."
    )
