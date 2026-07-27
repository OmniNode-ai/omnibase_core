# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the non-canonical lifecycle-class ratchet gate (OMN-14350)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators.no_noncanonical_lifecycle_classes import (
    DEFAULT_ALLOWLIST_PATH,
    load_allowlist,
    main,
    validate_paths,
)

pytestmark = pytest.mark.unit

_CORE_SRC = Path(__file__).resolve().parents[3] / "src" / "omnibase_core"


def _write_allowlist(path: Path, fqns: list[str]) -> Path:
    body = "allowlist:\n" + "".join(f'  - "{fqn}"\n' for fqn in fqns)
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# (a) NEW non-canonical class not in the allowlist -> gate RED
# ---------------------------------------------------------------------------
def test_new_noncanonical_class_outside_allowlist_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "src" / "pkg" / "service_new.py"
    source.parent.mkdir(parents=True)
    source.write_text("class PaymentService:\n    pass\n", encoding="utf-8")
    allowlist = _write_allowlist(tmp_path / "allow.yaml", [])

    exit_code = main([str(source), "--allowlist", str(allowlist)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "PaymentService" in captured.err
    assert "NEW non-canonical" in captured.err


def test_new_class_passes_once_allowlisted(tmp_path: Path) -> None:
    source = tmp_path / "src" / "pkg" / "service_new.py"
    source.parent.mkdir(parents=True)
    source.write_text("class PaymentService:\n    pass\n", encoding="utf-8")
    allowlist = _write_allowlist(
        tmp_path / "allow.yaml", ["pkg.service_new:PaymentService"]
    )

    assert main([str(source), "--allowlist", str(allowlist)]) == 0


# ---------------------------------------------------------------------------
# (b) core's current tree + generated allowlist -> GREEN
# ---------------------------------------------------------------------------
def test_core_tree_green_against_generated_allowlist() -> None:
    """The canary's frozen baseline must leave core green on day one."""
    assert _CORE_SRC.is_dir(), f"expected core src at {_CORE_SRC}"
    exit_code = main([str(_CORE_SRC), "--allowlist", str(DEFAULT_ALLOWLIST_PATH)])
    assert exit_code == 0


def test_core_tree_green_with_check_stale() -> None:
    """Every allowlisted FQN must still exist -- no stale entries in the baseline."""
    exit_code = main(
        [str(_CORE_SRC), "--check-stale", "--allowlist", str(DEFAULT_ALLOWLIST_PATH)]
    )
    assert exit_code == 0


def test_generated_allowlist_covers_every_current_hardfail() -> None:
    allowlist = load_allowlist(DEFAULT_ALLOWLIST_PATH)
    hardfail = {f.fqn for f in validate_paths([_CORE_SRC]) if f.severity == "hardfail"}
    assert hardfail, "expected core to have some residual hard-fail classes"
    assert hardfail - allowlist == set(), "allowlist missing a current residual"
    assert allowlist - hardfail == set(), "allowlist has an entry not in the tree"


# ---------------------------------------------------------------------------
# (c) canonical false positives -> NOT flagged
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "class_name",
    [
        "RegistryInfraFoo",  # per-node DI registry prefix
        "ModelBar",  # Model DTO first-word
        "HandlerBaz",  # Handler archetype first-word
        "ServiceResolutionError",  # DTO Error suffix
        "FooProtocol",  # Protocol suffix
        "NodeRedeployOrchestrator",  # Node first-word
        "RegistryEffect",  # Registry + archetype suffix
        "RouterConfig",  # Config DTO suffix
        "TypedDictServiceInfo",  # TypedDict prefix + Info suffix
        "EnumServiceType",  # Enum first-word
    ],
)
def test_canonical_names_not_flagged(tmp_path: Path, class_name: str) -> None:
    source = tmp_path / "src" / "pkg" / "mod.py"
    source.parent.mkdir(parents=True)
    source.write_text(f"class {class_name}:\n    pass\n", encoding="utf-8")

    assert validate_paths([source]) == []


def test_registry_file_path_excluded(tmp_path: Path) -> None:
    """A registry_* class inside a registry/ dir is a canonical per-node registry."""
    source = tmp_path / "src" / "pkg" / "registry" / "registry_thing.py"
    source.parent.mkdir(parents=True)
    source.write_text("class ThingRouter:\n    pass\n", encoding="utf-8")

    assert validate_paths([source]) == []


def test_genuine_noncanonical_names_flagged(tmp_path: Path) -> None:
    source = tmp_path / "src" / "pkg" / "mod.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "class PaymentService:\n    pass\n\n\nclass DispatchEngine:\n    pass\n",
        encoding="utf-8",
    )

    findings = validate_paths([source])
    flagged = {f.class_name: f.matched_word for f in findings}
    assert flagged == {"PaymentService": "Service", "DispatchEngine": "Engine"}
    assert all(f.severity == "hardfail" for f in findings)


# ---------------------------------------------------------------------------
# (d) --check-stale -> RED when an allowlisted FQN is deleted
# ---------------------------------------------------------------------------
def test_check_stale_fails_on_deleted_allowlisted_fqn(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "src" / "pkg" / "mod.py"
    source.parent.mkdir(parents=True)
    source.write_text("class LiveService:\n    pass\n", encoding="utf-8")
    # Allowlist references a class that no longer exists in the tree.
    allowlist = _write_allowlist(
        tmp_path / "allow.yaml",
        ["pkg.mod:LiveService", "pkg.mod:DeletedService"],
    )

    exit_code = main([str(source), "--check-stale", "--allowlist", str(allowlist)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "STALE allowlist" in captured.err
    assert "pkg.mod:DeletedService" in captured.err


def test_check_stale_passes_when_all_entries_present(tmp_path: Path) -> None:
    source = tmp_path / "src" / "pkg" / "mod.py"
    source.parent.mkdir(parents=True)
    source.write_text("class LiveService:\n    pass\n", encoding="utf-8")
    allowlist = _write_allowlist(tmp_path / "allow.yaml", ["pkg.mod:LiveService"])

    assert main([str(source), "--check-stale", "--allowlist", str(allowlist)]) == 0


# ---------------------------------------------------------------------------
# (e) underscore-private class -> soft list, not hard-fail
# ---------------------------------------------------------------------------
def test_underscore_private_is_soft_not_hardfail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "src" / "pkg" / "mod.py"
    source.parent.mkdir(parents=True)
    source.write_text("class _CacheManager:\n    pass\n", encoding="utf-8")
    allowlist = _write_allowlist(tmp_path / "allow.yaml", [])

    findings = validate_paths([source])
    assert len(findings) == 1
    assert findings[0].severity == "soft"
    assert findings[0].class_name == "_CacheManager"

    # Soft findings are report-only: empty allowlist still yields exit 0.
    exit_code = main([str(source), "--allowlist", str(allowlist)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "soft (report-only)" in captured.err


# ---------------------------------------------------------------------------
# Module-path resolution + finding identity
# ---------------------------------------------------------------------------
def test_module_and_fqn_resolution(tmp_path: Path) -> None:
    source = tmp_path / "src" / "omnibase_core" / "services" / "service_foo.py"
    source.parent.mkdir(parents=True)
    source.write_text("class FooService:\n    pass\n", encoding="utf-8")

    findings = validate_paths([source])
    assert len(findings) == 1
    assert findings[0].module == "omnibase_core.services.service_foo"
    assert findings[0].fqn == "omnibase_core.services.service_foo:FooService"


def test_missing_allowlist_file_fails_closed(tmp_path: Path) -> None:
    """A missing allowlist means every residual is treated as NEW (fail-closed)."""
    source = tmp_path / "src" / "pkg" / "mod.py"
    source.parent.mkdir(parents=True)
    source.write_text("class FooService:\n    pass\n", encoding="utf-8")

    assert load_allowlist(tmp_path / "does_not_exist.yaml") == set()
    exit_code = main([str(source), "--allowlist", str(tmp_path / "nope.yaml")])
    assert exit_code == 1
