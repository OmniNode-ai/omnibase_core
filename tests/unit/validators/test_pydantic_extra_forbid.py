# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the ``extra="forbid"`` ratchet gate (OMN-14515).

The five mandatory proofs are parametrized over BOTH engines (runtime introspection and
static AST). Proof (b) — a model with no ``model_config`` at all — is the one that makes
the difference between a real gate and a vacuous one: Pydantic's default is
``extra="ignore"``, so a model that declares nothing is already silently dropping
fields. A validator that only greps for the literal string ``extra="ignore"`` passes (b)
and is worthless.
"""

from __future__ import annotations

import os
import subprocess
from datetime import timedelta
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_extra_forbid_finding import (
    STATUS_EXPLICIT_ALLOW,
    STATUS_EXPLICIT_FORBID,
    STATUS_EXPLICIT_IGNORE,
    STATUS_IMPLICIT_DEFAULT,
)
from omnibase_core.validators.pydantic_extra_forbid import (
    load_waivers,
    main,
    render_baseline,
    scan_paths,
    today_utc,
)

pytestmark = pytest.mark.unit

ENGINES = [
    pytest.param(True, id="runtime"),
    pytest.param(False, id="static"),
]


def _pkg(tmp_path: Path, name: str, body: str) -> Path:
    """Write ``<tmp>/<unique-pkg>/<name>.py`` as an importable package module."""
    package = tmp_path / f"pkg_{abs(hash(tmp_path)) % 10_000_000}"
    package.mkdir(exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    module = package / f"{name}.py"
    module.write_text(body, encoding="utf-8")
    return module


def _statuses(paths: list[Path], *, use_runtime: bool) -> dict[str, str]:
    return {f.class_name: f.status for f in scan_paths(paths, use_runtime=use_runtime)}


def _violations(paths: list[Path], *, use_runtime: bool) -> set[str]:
    return {
        f.class_name
        for f in scan_paths(paths, use_runtime=use_runtime)
        if f.is_violation
    }


# ===========================================================================
# The five mandatory RED / PASS proofs
# ===========================================================================
@pytest.mark.parametrize("use_runtime", ENGINES)
def test_proof_a_explicit_ignore_is_a_violation(
    tmp_path: Path, use_runtime: bool
) -> None:
    """(a) MUST FAIL — an explicit extra="ignore"."""
    module = _pkg(
        tmp_path,
        "mod_a",
        "from pydantic import BaseModel, ConfigDict\n"
        "\n"
        "class ModelExplicitIgnore(BaseModel):\n"
        '    model_config = ConfigDict(extra="ignore")\n'
        "    field: str\n",
    )
    statuses = _statuses([module], use_runtime=use_runtime)
    assert statuses["ModelExplicitIgnore"] == STATUS_EXPLICIT_IGNORE
    assert _violations([module], use_runtime=use_runtime) == {"ModelExplicitIgnore"}


@pytest.mark.parametrize("use_runtime", ENGINES)
def test_proof_b_no_model_config_at_all_is_a_violation(
    tmp_path: Path, use_runtime: bool
) -> None:
    """(b) MUST FAIL — NO ``model_config`` whatsoever.

    THE vacuity test. Pydantic's default for an undeclared ``extra`` is ``"ignore"``, so
    this model already drops unknown fields silently. A string-grep validator passes this
    and is worthless. Absence must be a violation.
    """
    module = _pkg(
        tmp_path,
        "mod_b",
        "from pydantic import BaseModel\n"
        "\n"
        "class ModelNoConfigAtAll(BaseModel):\n"
        "    field: str\n",
    )
    statuses = _statuses([module], use_runtime=use_runtime)
    assert statuses["ModelNoConfigAtAll"] == STATUS_IMPLICIT_DEFAULT
    assert _violations([module], use_runtime=use_runtime) == {"ModelNoConfigAtAll"}


@pytest.mark.parametrize("use_runtime", ENGINES)
def test_proof_c_inherits_permissive_base_is_a_violation(
    tmp_path: Path, use_runtime: bool
) -> None:
    """(c) MUST FAIL — inherits a permissive base (cross-file, resolved through the MRO)."""
    base = _pkg(
        tmp_path,
        "mod_c_base",
        "from pydantic import BaseModel, ConfigDict\n"
        "\n"
        "class ModelPermissiveBase(BaseModel):\n"
        '    model_config = ConfigDict(extra="allow")\n',
    )
    child = _pkg(
        tmp_path,
        "mod_c_child",
        "from .mod_c_base import ModelPermissiveBase\n"
        "\n"
        "class ModelInheritsPermissive(ModelPermissiveBase):\n"
        "    field: str\n",
    )
    statuses = _statuses([base, child], use_runtime=use_runtime)
    assert statuses["ModelInheritsPermissive"] == STATUS_EXPLICIT_ALLOW
    assert _violations([base, child], use_runtime=use_runtime) == {
        "ModelPermissiveBase",
        "ModelInheritsPermissive",
    }


@pytest.mark.parametrize("use_runtime", ENGINES)
def test_proof_d_explicit_forbid_passes(tmp_path: Path, use_runtime: bool) -> None:
    """(d) MUST PASS — an explicit extra="forbid"."""
    module = _pkg(
        tmp_path,
        "mod_d",
        "from pydantic import BaseModel, ConfigDict\n"
        "\n"
        "class ModelExplicitForbid(BaseModel):\n"
        '    model_config = ConfigDict(extra="forbid")\n'
        "    field: str\n",
    )
    statuses = _statuses([module], use_runtime=use_runtime)
    assert statuses["ModelExplicitForbid"] == STATUS_EXPLICIT_FORBID
    assert _violations([module], use_runtime=use_runtime) == set()


@pytest.mark.parametrize("use_runtime", ENGINES)
def test_proof_e_inherits_forbid_passes(tmp_path: Path, use_runtime: bool) -> None:
    """(e) MUST PASS — inherits extra="forbid" from a compliant base, declaring nothing."""
    base = _pkg(
        tmp_path,
        "mod_e_base",
        "from pydantic import BaseModel, ConfigDict\n"
        "\n"
        "class ModelStrictBase(BaseModel):\n"
        '    model_config = ConfigDict(extra="forbid")\n',
    )
    child = _pkg(
        tmp_path,
        "mod_e_child",
        "from .mod_e_base import ModelStrictBase\n"
        "\n"
        "class ModelInheritsForbid(ModelStrictBase):\n"
        "    field: str\n",
    )
    statuses = _statuses([base, child], use_runtime=use_runtime)
    assert statuses["ModelInheritsForbid"] == STATUS_EXPLICIT_FORBID
    assert _violations([base, child], use_runtime=use_runtime) == set()


# ===========================================================================
# The four extractor bugs a prior census lane hit — each would be a FALSE violation
# ===========================================================================
@pytest.mark.parametrize("use_runtime", ENGINES)
def test_extractor_bug_1_model_config_as_annassign(
    tmp_path: Path, use_runtime: bool
) -> None:
    """AnnAssign (annotated) model_config, not a bare Assign."""
    module = _pkg(
        tmp_path,
        "mod_ann",
        "from pydantic import BaseModel, ConfigDict\n"
        "\n"
        "class ModelAnnotatedConfig(BaseModel):\n"
        '    model_config: ConfigDict = ConfigDict(extra="forbid")\n'
        "    field: str\n",
    )
    assert _violations([module], use_runtime=use_runtime) == set()


@pytest.mark.parametrize("use_runtime", ENGINES)
def test_extractor_bug_2_plain_dict_literal_config(
    tmp_path: Path, use_runtime: bool
) -> None:
    """``model_config = {"extra": "forbid"}`` — a plain dict, not ConfigDict(...) (70 files)."""
    module = _pkg(
        tmp_path,
        "mod_dict",
        "from pydantic import BaseModel\n"
        "\n"
        "class ModelDictLiteralConfig(BaseModel):\n"
        '    model_config = {"extra": "forbid"}\n'
        "    field: str\n",
    )
    assert _violations([module], use_runtime=use_runtime) == set()


@pytest.mark.parametrize("use_runtime", ENGINES)
def test_extractor_bug_3_class_keyword_arg(tmp_path: Path, use_runtime: bool) -> None:
    """``class Foo(Base, extra="forbid")`` — extra as a class kwarg, not in the body.

    Mirrors the real ``ModelContextBundleL0``-``L4`` chain: the kwarg is declared once at
    the root and inherited down. Every level must read as compliant.
    """
    module = _pkg(
        tmp_path,
        "mod_kwarg",
        "from pydantic import BaseModel\n"
        "\n"
        'class ModelBundleL0(BaseModel, frozen=True, extra="forbid"):\n'
        "    a: str\n"
        "\n"
        "class ModelBundleL1(ModelBundleL0):\n"
        "    b: str\n"
        "\n"
        "class ModelBundleL2(ModelBundleL1):\n"
        "    c: str\n",
    )
    statuses = _statuses([module], use_runtime=use_runtime)
    assert statuses == {
        "ModelBundleL0": STATUS_EXPLICIT_FORBID,
        "ModelBundleL1": STATUS_EXPLICIT_FORBID,
        "ModelBundleL2": STATUS_EXPLICIT_FORBID,
    }
    assert _violations([module], use_runtime=use_runtime) == set()


@pytest.mark.parametrize("use_runtime", ENGINES)
def test_extractor_bug_4_relative_path_arg_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, use_runtime: bool
) -> None:
    """A path given RELATIVELY must resolve identically to the absolute form."""
    module = _pkg(
        tmp_path,
        "mod_rel",
        "from pydantic import BaseModel\n"
        "\n"
        "class ModelRelativePath(BaseModel):\n"
        "    field: str\n",
    )
    monkeypatch.chdir(tmp_path)
    relative = module.relative_to(tmp_path)
    assert _violations([relative], use_runtime=use_runtime) == {"ModelRelativePath"}


def test_rootmodel_is_exempt(tmp_path: Path) -> None:
    """RootModel cannot carry `extra` (Pydantic raises), so demanding it would be impossible."""
    module = _pkg(
        tmp_path,
        "mod_root",
        "from pydantic import RootModel\n"
        "\n"
        "class ModelRootList(RootModel[list[str]]):\n"
        "    pass\n",
    )
    assert scan_paths([module], use_runtime=True) == []
    assert scan_paths([module], use_runtime=False) == []


def test_non_pydantic_classes_are_ignored(tmp_path: Path) -> None:
    module = _pkg(
        tmp_path,
        "mod_plain",
        "from dataclasses import dataclass\n"
        "\n"
        "@dataclass\n"
        "class PlainDataclass:\n"
        "    field: str = ''\n"
        "\n"
        "class PlainClass:\n"
        "    pass\n",
    )
    assert scan_paths([module], use_runtime=True) == []


# ===========================================================================
# Ratchet mechanics: baseline, new violations, stale entries
# ===========================================================================
def _write_baseline(path: Path, fqns: list[str]) -> Path:
    body = "violations:\n" + "".join(f'  - "{fqn}"\n' for fqn in fqns)
    path.write_text(body, encoding="utf-8")
    return path


def _empty_waivers(path: Path) -> Path:
    path.write_text("waivers: []\n", encoding="utf-8")
    return path


def test_new_violation_outside_baseline_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _pkg(
        tmp_path,
        "mod_new",
        "from pydantic import BaseModel\n\nclass ModelBrandNew(BaseModel):\n    f: str\n",
    )
    exit_code = main(
        [
            str(module),
            "--baseline",
            str(_write_baseline(tmp_path / "baseline.yaml", [])),
            "--waivers",
            str(_empty_waivers(tmp_path / "waivers.yaml")),
        ]
    )
    assert exit_code == 1
    assert "ModelBrandNew" in capsys.readouterr().err


def test_baselined_violation_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _pkg(
        tmp_path,
        "mod_old",
        "from pydantic import BaseModel\n\nclass ModelLegacy(BaseModel):\n    f: str\n",
    )
    from omnibase_core.validators.pydantic_extra_forbid import module_for_path

    fqn = f"{module_for_path(module)[0]}:ModelLegacy"
    exit_code = main(
        [
            str(module),
            "--baseline",
            str(_write_baseline(tmp_path / "baseline.yaml", [fqn])),
            "--waivers",
            str(_empty_waivers(tmp_path / "waivers.yaml")),
        ]
    )
    assert exit_code == 0
    assert "OK" in capsys.readouterr().out


def test_stale_baseline_entry_fails_check_stale(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A model that got fixed must be removed from the baseline — the count only goes down."""
    module = _pkg(
        tmp_path,
        "mod_fixed",
        "from pydantic import BaseModel, ConfigDict\n"
        "\n"
        "class ModelNowFixed(BaseModel):\n"
        '    model_config = ConfigDict(extra="forbid")\n',
    )
    from omnibase_core.validators.pydantic_extra_forbid import module_for_path

    fqn = f"{module_for_path(module)[0]}:ModelNowFixed"
    exit_code = main(
        [
            str(module),
            "--check-stale",
            "--baseline",
            str(_write_baseline(tmp_path / "baseline.yaml", [fqn])),
            "--waivers",
            str(_empty_waivers(tmp_path / "waivers.yaml")),
        ]
    )
    assert exit_code == 1
    assert "STALE" in capsys.readouterr().err


def test_write_baseline_round_trips(tmp_path: Path) -> None:
    module = _pkg(
        tmp_path,
        "mod_seed",
        "from pydantic import BaseModel\n\nclass ModelSeed(BaseModel):\n    f: str\n",
    )
    baseline = tmp_path / "baseline.yaml"
    assert (
        main(
            [
                str(module),
                "--write-baseline",
                "--baseline",
                str(baseline),
                "--waivers",
                str(_empty_waivers(tmp_path / "waivers.yaml")),
            ]
        )
        == 0
    )
    assert "ModelSeed" in baseline.read_text(encoding="utf-8")
    # Second run against the freshly-written baseline is green.
    assert (
        main(
            [
                str(module),
                "--baseline",
                str(baseline),
                "--waivers",
                str(_empty_waivers(tmp_path / "waivers.yaml")),
            ]
        )
        == 0
    )


def test_render_baseline_is_deterministic(tmp_path: Path) -> None:
    module = _pkg(
        tmp_path,
        "mod_det",
        "from pydantic import BaseModel\n"
        "\n"
        "class ModelB(BaseModel):\n    f: str\n"
        "\n"
        "class ModelA(BaseModel):\n    f: str\n",
    )
    findings = [f for f in scan_paths([module]) if f.is_violation]
    first = render_baseline(findings, [module])
    second = render_baseline(list(reversed(findings)), [module])
    assert first == second


# ===========================================================================
# Expiring waivers: ticket + PR + expiry, hard-fail on expiry / malformation
# ===========================================================================
def test_active_waiver_suppresses_a_new_violation(tmp_path: Path) -> None:
    module = _pkg(
        tmp_path,
        "mod_waived",
        "from pydantic import BaseModel\n\nclass ModelInFlight(BaseModel):\n    f: str\n",
    )
    from omnibase_core.validators.pydantic_extra_forbid import module_for_path

    fqn = f"{module_for_path(module)[0]}:ModelInFlight"
    waivers = tmp_path / "waivers.yaml"
    waivers.write_text(
        "waivers:\n"
        f'  - fqn: "{fqn}"\n'
        "    ticket: OMN-14515\n"
        "    pr: https://github.com/OmniNode-ai/omnibase_core/pull/1436\n"
        f"    expires_at: {(today_utc() + timedelta(days=14)).isoformat()}\n"
        '    reason: "time-boxed graduation"\n',
        encoding="utf-8",
    )
    assert (
        main(
            [
                str(module),
                "--baseline",
                str(_write_baseline(tmp_path / "baseline.yaml", [])),
                "--waivers",
                str(waivers),
            ]
        )
        == 0
    )


def test_expired_waiver_is_a_hard_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An expired waiver fails LOUDLY — that is what stops it decaying into an allowlist."""
    module = _pkg(
        tmp_path,
        "mod_expired",
        "from pydantic import BaseModel\n\nclass ModelStale(BaseModel):\n    f: str\n",
    )
    from omnibase_core.validators.pydantic_extra_forbid import module_for_path

    fqn = f"{module_for_path(module)[0]}:ModelStale"
    waivers = tmp_path / "waivers.yaml"
    waivers.write_text(
        "waivers:\n"
        f'  - fqn: "{fqn}"\n'
        "    ticket: OMN-14515\n"
        "    pr: https://github.com/OmniNode-ai/omnibase_core/pull/1436\n"
        f"    expires_at: {(today_utc() - timedelta(days=1)).isoformat()}\n",
        encoding="utf-8",
    )
    exit_code = main(
        [
            str(module),
            "--baseline",
            str(_write_baseline(tmp_path / "baseline.yaml", [])),
            "--waivers",
            str(waivers),
        ]
    )
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "EXPIRED" in err
    assert "ModelStale" in err


@pytest.mark.parametrize(
    ("entry", "expected_error"),
    [
        ('  - fqn: "m:M"\n    pr: x\n    expires_at: 2099-01-01\n', "OMN-NNNN"),
        ('  - fqn: "m:M"\n    ticket: OMN-1\n    expires_at: 2099-01-01\n', "'pr'"),
        ('  - fqn: "m:M"\n    ticket: OMN-1\n    pr: x\n', "expires_at"),
        ("  - ticket: OMN-1\n    pr: x\n    expires_at: 2099-01-01\n", "'fqn'"),
    ],
    ids=["no-ticket", "no-pr", "no-expiry", "no-fqn"],
)
def test_malformed_waiver_is_an_error(
    tmp_path: Path, entry: str, expected_error: str
) -> None:
    waivers = tmp_path / "waivers.yaml"
    waivers.write_text(f"waivers:\n{entry}", encoding="utf-8")
    active, errors = load_waivers(waivers, today_utc())
    assert active == set()
    assert any(expected_error in error for error in errors)


# ===========================================================================
# Modified-model enforcement: touch a broken model -> you must fix it
# ===========================================================================
def _git(repo: Path, *args: str) -> None:
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith("GIT_CONFIG"):
            env.pop(key, None)
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ):
        env.pop(key, None)
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


def test_git_helper_does_not_inherit_parent_git_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    monkeypatch.setenv("GIT_DIR", "/parent/worktree/.git")

    _git(tmp_path, "init", "-q", str(repo))
    (repo / "fixture.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", "fixture.py")

    assert (repo / ".git" / "index").exists()


def test_modifying_a_baselined_model_fails(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Editing the body of a baselined, still-broken model is a failure: fix it now."""
    module = git_repo / "pkg" / "mod_touched.py"
    module.write_text(
        "from pydantic import BaseModel\n"
        "\n"
        "class ModelUntouched(BaseModel):\n"
        "    a: str\n"
        "\n"
        "class ModelTouched(BaseModel):\n"
        "    b: str\n",
        encoding="utf-8",
    )
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "seed")

    from omnibase_core.validators.pydantic_extra_forbid import module_for_path

    prefix = module_for_path(module)[0]
    baseline = _write_baseline(
        git_repo / "baseline.yaml",
        [f"{prefix}:ModelUntouched", f"{prefix}:ModelTouched"],
    )
    waivers = _empty_waivers(git_repo / "waivers.yaml")

    # Baselined + untouched -> green.
    monkeypatch.chdir(git_repo)
    assert (
        main(
            [
                "pkg",
                "--baseline",
                str(baseline),
                "--waivers",
                str(waivers),
                "--enforce-modified",
                ":staged",
            ]
        )
        == 0
    )

    # Now edit ModelTouched's body only, and stage it.
    module.write_text(
        "from pydantic import BaseModel\n"
        "\n"
        "class ModelUntouched(BaseModel):\n"
        "    a: str\n"
        "\n"
        "class ModelTouched(BaseModel):\n"
        "    b: str\n"
        "    c: int = 0\n",
        encoding="utf-8",
    )
    _git(git_repo, "add", "-A")

    exit_code = main(
        [
            "pkg",
            "--baseline",
            str(baseline),
            "--waivers",
            str(waivers),
            "--enforce-modified",
            ":staged",
        ]
    )
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "MODIFIED" in err
    assert "ModelTouched" in err
    # The untouched sibling in the same file must NOT be dragged in.
    assert "ModelUntouched" not in err


def test_enforce_modified_fails_closed_on_bad_ref(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """If the diff cannot be read, the gate fails CLOSED rather than skipping the check."""
    (git_repo / "pkg" / "m.py").write_text(
        "from pydantic import BaseModel\n\nclass ModelX(BaseModel):\n    a: str\n",
        encoding="utf-8",
    )
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "seed")
    monkeypatch.chdir(git_repo)

    exit_code = main(
        [
            "pkg",
            "--baseline",
            str(_write_baseline(git_repo / "baseline.yaml", [])),
            "--waivers",
            str(_empty_waivers(git_repo / "waivers.yaml")),
            "--enforce-modified",
            "origin/does-not-exist",
        ]
    )
    assert exit_code == 1
    assert "failing closed" in capsys.readouterr().err


# ===========================================================================
# Dogfood: the shipped core baseline must be honest about the tree it describes
# ===========================================================================
def test_core_baseline_matches_the_tree() -> None:
    """The committed core baseline must equal the live violation set — no drift.

    This is the same assertion CI makes; running it here means a stale baseline fails
    locally too, not just in CI.
    """
    from omnibase_core.validators.pydantic_extra_forbid import (
        DEFAULT_BASELINE_PATH,
        load_baseline,
    )

    core_src = Path(__file__).resolve().parents[3] / "src" / "omnibase_core"
    live = {f.fqn for f in scan_paths([core_src]) if f.is_violation}
    baselined = load_baseline(DEFAULT_BASELINE_PATH)

    assert not (live - baselined), (
        "NEW extra=forbid violations not in the baseline: "
        f"{sorted(live - baselined)[:10]}"
    )
    assert not (baselined - live), (
        "STALE baseline entries (model fixed or gone) — remove them: "
        f"{sorted(baselined - live)[:10]}"
    )
