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
from datetime import date, timedelta
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_extra_forbid_finding import (
    STATUS_EXPLICIT_ALLOW,
    STATUS_EXPLICIT_FORBID,
    STATUS_EXPLICIT_IGNORE,
    STATUS_IMPLICIT_DEFAULT,
    STATUS_UNRESOLVED,
)
from omnibase_core.validators import pydantic_extra_forbid as pyd
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from omnibase_core.validators.pydantic_extra_forbid import (
    changed_line_ranges,
    load_baseline,
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


@pytest.mark.parametrize("use_runtime", ENGINES)
@pytest.mark.parametrize(
    "classes",
    [
        "class ModelA(ModelB, BaseModel):\n    pass\nclass ModelB(ModelA):\n    pass\n",
        "class ModelA(ModelA, BaseModel):\n    pass\n",
        "class ModelA(ModelB, RootModel[int]):\n    pass\n"
        "class ModelB(ModelA):\n    pass\n",
        "class ModelA(RootModel[int], ModelB):\n    pass\n"
        "class ModelB(ModelA):\n    pass\n",
        "class ModelA(ModelB, BaseModel):\n"
        "    model_config = ConfigDict(extra='forbid')\n"
        "class ModelB(ModelA):\n    pass\n",
        "class ModelStrict(BaseModel):\n"
        "    model_config = ConfigDict(extra='forbid')\n"
        "class ModelA(ModelB, ModelStrict):\n    pass\n"
        "class ModelB(ModelA):\n    pass\n",
    ],
    ids=[
        "two-class",
        "self",
        "root-last",
        "root-first",
        "own-config",
        "strict-sibling",
    ],
)
def test_cyclic_ancestry_is_unresolved(
    tmp_path: Path, use_runtime: bool, classes: str
) -> None:
    """Cycles fail closed even beside RootModel or an explicit forbid config."""
    module = _pkg(
        tmp_path,
        "mod_cycle",
        "from pydantic import BaseModel, ConfigDict, RootModel\n\n" + classes,
    )
    for _ in range(2):
        findings = scan_paths([module], use_runtime=use_runtime)
        cyclic = [
            finding for finding in findings if finding.class_name != "ModelStrict"
        ]
        assert {finding.class_name for finding in cyclic} == (
            {"ModelA", "ModelB"} if "class ModelB" in classes else {"ModelA"}
        )
        assert all(finding.status == STATUS_UNRESOLVED for finding in cyclic)
        assert all(finding.effective_extra is None for finding in cyclic)
        assert all(finding.is_violation for finding in cyclic)


def test_cyclic_ancestry_gate_fails_without_recursion_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _pkg(
        tmp_path,
        "mod_cycle_gate",
        "from pydantic import BaseModel\n"
        "class ModelA(ModelB, BaseModel):\n    pass\n"
        "class ModelB(ModelA):\n    pass\n",
    )
    assert (
        main(
            [
                str(module),
                "--baseline",
                str(_write_baseline(tmp_path / "baseline.yaml", [])),
                "--waivers",
                str(_empty_waivers(tmp_path / "waivers.yaml")),
            ]
        )
        == 1
    )
    stderr = capsys.readouterr().err
    assert STATUS_UNRESOLVED in stderr
    assert "RecursionError" not in stderr


@pytest.mark.parametrize("use_runtime", ENGINES)
@pytest.mark.parametrize("extra", ["forbid", "allow"])
def test_conflicting_diamond_uses_last_base_config(
    tmp_path: Path, use_runtime: bool, extra: str
) -> None:
    """Each branch inherits independently, then the rightmost config wins."""
    module = _pkg(
        tmp_path,
        "mod_diamond",
        "from pydantic import BaseModel, ConfigDict\n"
        "class ModelTop(BaseModel):\n"
        f"    model_config = ConfigDict(extra={extra!r})\n"
        "class ModelLeft(ModelTop):\n"
        f"    model_config = ConfigDict(extra={'allow' if extra == 'forbid' else 'forbid'!r})\n"
        "class ModelRight(ModelTop):\n    pass\n"
        "class ModelDiamond(ModelLeft, ModelRight):\n    pass\n",
    )
    findings = scan_paths([module], use_runtime=use_runtime)
    diamond = next(
        finding for finding in findings if finding.class_name == "ModelDiamond"
    )
    assert diamond.effective_extra == extra
    assert diamond.status == (
        STATUS_EXPLICIT_FORBID if extra == "forbid" else STATUS_EXPLICIT_ALLOW
    )


@pytest.mark.parametrize("use_runtime", ENGINES)
@pytest.mark.parametrize("base", ["BaseModel", "RootModel[int]"])
def test_noncyclic_diamond_revisits_shared_ancestor(
    tmp_path: Path, use_runtime: bool, base: str
) -> None:
    module = _pkg(
        tmp_path,
        "mod_shared_ancestor",
        "from pydantic import BaseModel, RootModel\n"
        f"class ModelTop({base}):\n    pass\n"
        "class ModelLeft(ModelTop):\n    pass\n"
        "class ModelRight(ModelTop):\n    pass\n"
        "class ModelDiamond(ModelLeft, ModelRight):\n    pass\n",
    )
    findings = scan_paths([module], use_runtime=use_runtime)
    if base == "BaseModel":
        assert len(findings) == 4
        assert all(finding.status == STATUS_IMPLICIT_DEFAULT for finding in findings)
    else:
        assert findings == []


@pytest.mark.parametrize("use_runtime", ENGINES)
def test_cross_module_cycle_is_unresolved(tmp_path: Path, use_runtime: bool) -> None:
    first = _pkg(
        tmp_path,
        "mod_cycle_first",
        "from pydantic import BaseModel\n"
        "from .mod_cycle_second import ModelB\n"
        "class ModelA(ModelB, BaseModel):\n    pass\n",
    )
    second = _pkg(
        tmp_path,
        "mod_cycle_second",
        "from .mod_cycle_first import ModelA\nclass ModelB(ModelA):\n    pass\n",
    )
    findings = scan_paths([first, second], use_runtime=use_runtime)
    assert {finding.class_name for finding in findings} == {"ModelA", "ModelB"}
    assert all(finding.status == STATUS_UNRESOLVED for finding in findings)
    assert all(finding.effective_extra is None for finding in findings)


@pytest.mark.parametrize("base", ["BaseModel", "RootModel[int]"])
def test_unknown_ancestry_cannot_grant_config_or_exemption(
    tmp_path: Path, base: str
) -> None:
    module = _pkg(
        tmp_path,
        "mod_unknown_ancestor",
        "from pydantic import BaseModel, ConfigDict, RootModel\n"
        f"class ModelUnknown({base}, MissingBase):\n"
        "    model_config = ConfigDict(extra='forbid')\n",
    )
    findings = scan_paths([module], use_runtime=False)
    assert len(findings) == 1
    assert findings[0].status == STATUS_UNRESOLVED
    assert findings[0].effective_extra is None


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
    from omnibase_core.validation.pydantic_module_index import module_for_path

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
    from omnibase_core.validation.pydantic_module_index import module_for_path

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


def _header_count(text: str) -> int:
    """Return the integer from the ``# count: N`` metadata line of a baseline."""
    matches = [line for line in text.splitlines() if line.startswith("# count: ")]
    assert len(matches) == 1
    return int(matches[0].removeprefix("# count: "))


def _entry_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("  - "))


def test_rendered_baseline_count_header_matches_entries(tmp_path: Path) -> None:
    """OMN-17885: the generated ``# count`` line must equal the rendered entries."""
    module = _pkg(
        tmp_path,
        "mod_count",
        "from pydantic import BaseModel\n"
        "\n"
        "class ModelA(BaseModel):\n    f: str\n"
        "\n"
        "class ModelB(BaseModel):\n    f: str\n",
    )
    findings = [f for f in scan_paths([module]) if f.is_violation]
    rendered = render_baseline(findings, [module])
    assert _entry_count(rendered) == 2
    assert _header_count(rendered) == _entry_count(rendered)


def test_rendered_baseline_preserves_spdx_and_document_marker(
    tmp_path: Path,
) -> None:
    """OMN-17885: regeneration must not drop the SPDX header or the ``---`` marker."""
    module = _pkg(
        tmp_path,
        "mod_spdx",
        "from pydantic import BaseModel\n\nclass ModelA(BaseModel):\n    f: str\n",
    )
    findings = [f for f in scan_paths([module]) if f.is_violation]
    lines = render_baseline(findings, [module]).splitlines()
    assert lines[0].startswith("# SPDX-FileCopyrightText:")
    assert lines[1] == "# SPDX-License-Identifier: MIT"
    assert lines[2] == "---"


def test_committed_baseline_count_header_matches_entries() -> None:
    """OMN-17885: the committed baseline's ``# count`` must equal its entries."""
    baseline = Path(pyd.__file__).with_name("extra_forbid_baseline.yaml")
    text = baseline.read_text(encoding="utf-8")
    assert _header_count(text) == _entry_count(text)
    assert _entry_count(text) == len(load_baseline(baseline))


# ===========================================================================
# Expiring waivers: ticket + PR + expiry, hard-fail on expiry / malformation
# ===========================================================================
def test_active_waiver_suppresses_a_new_violation(tmp_path: Path) -> None:
    module = _pkg(
        tmp_path,
        "mod_waived",
        "from pydantic import BaseModel\n\nclass ModelInFlight(BaseModel):\n    f: str\n",
    )
    from omnibase_core.validation.pydantic_module_index import module_for_path

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
    from omnibase_core.validation.pydantic_module_index import module_for_path

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


@pytest.mark.parametrize("content", ["null\n", "{}\n"])
def test_absent_or_empty_mapping_baseline_and_waivers_are_explicit_empty_documents(
    tmp_path: Path, content: str
) -> None:
    """Null and empty mappings retain the deliberate empty-document policy."""
    baseline = tmp_path / "baseline.yaml"
    waivers = tmp_path / "waivers.yaml"
    baseline.write_text(content, encoding="utf-8")
    waivers.write_text(content, encoding="utf-8")

    assert load_baseline(baseline) == set()
    assert load_waivers(waivers, today_utc()) == (set(), [])


# ===========================================================================
# Modified-model enforcement: touch a broken model -> you must fix it
# ===========================================================================
def _git(repo: Path, *args: str, extra_env: dict[str, str] | None = None) -> None:
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
    env.update(extra_env or {})
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

    from omnibase_core.validation.pydantic_module_index import module_for_path

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
# OMN-17910: the diff reader takes its repository authority from cwd alone
# ===========================================================================
def _init_repo(path: Path, module: str, staged_line: str) -> Path:
    """A repo with one committed module and ``staged_line`` staged onto it."""
    (path / "pkg").mkdir(parents=True)
    _git(path.parent, "init", "-q", str(path))
    _git(path, "config", "user.email", "t@t.t")
    _git(path, "config", "user.name", "t")
    _git(path, "config", "commit.gpgsign", "false")
    target = path / "pkg" / module
    target.write_text("A = 1\nB = 2\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-qm", "seed")
    target.write_text(f"A = 1\nB = 2\n{staged_line}\n", encoding="utf-8")
    _git(path, "add", "-A")
    return target


@pytest.fixture
def two_repos(tmp_path: Path) -> tuple[Path, Path]:
    """(target module, other module): each repo has its own staged edit."""
    target = _init_repo(tmp_path / "target", "target_mod.py", "C = 3")
    other = _init_repo(tmp_path / "other", "other_mod.py", "VALUE = 'OTHER'")
    return target, other


def _injections(other_repo: Path, tmp_path: Path) -> dict[str, dict[str, str]]:
    noprefix = tmp_path / "noprefix.gitconfig"
    noprefix.write_text("[diff]\n\tnoprefix = true\n", encoding="utf-8")
    return {
        "GIT_DIR": {"GIT_DIR": str(other_repo / ".git")},
        "GIT_WORK_TREE": {"GIT_WORK_TREE": str(other_repo)},
        "GIT_COMMON_DIR": {"GIT_COMMON_DIR": str(other_repo / ".git")},
        "GIT_OBJECT_DIRECTORY": {
            "GIT_OBJECT_DIRECTORY": str(other_repo / ".git" / "objects")
        },
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": {
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(other_repo / ".git" / "objects")
        },
        "GIT_CONFIG_COUNT": {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "diff.noprefix",
            "GIT_CONFIG_VALUE_0": "true",
        },
        "GIT_CONFIG_PARAMETERS": {"GIT_CONFIG_PARAMETERS": "'diff.noprefix=true'"},
        "GIT_CONFIG_GLOBAL": {"GIT_CONFIG_GLOBAL": str(noprefix)},
    }


@pytest.mark.parametrize(
    "selector",
    [
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_GLOBAL",
    ],
)
def test_changed_line_ranges_ignores_inherited_repository_authority(
    two_repos: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    selector: str,
) -> None:
    """An inherited repo/object/config selector never changes which bytes are read."""
    target, other = two_repos
    for key, value in _injections(other.parent.parent, tmp_path)[selector].items():
        monkeypatch.setenv(key, value)

    ranges = changed_line_ranges(":staged", target.parent.parent)

    assert ranges == {target.resolve(): [(3, 3)]}


def test_changed_line_ranges_ref_mode_ignores_inherited_git_dir(
    two_repos: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ``<ref>...HEAD`` form reads the same sanitized repository as ``:staged``."""
    target, other = two_repos
    _git(target.parent.parent, "commit", "-qm", "staged edit")
    monkeypatch.setenv("GIT_DIR", str(other.parent.parent / ".git"))

    assert changed_line_ranges("HEAD~1", target.parent.parent) == {
        target.resolve(): [(3, 3)]
    }


@pytest.mark.parametrize("relative", [False, True], ids=["absolute", "relative"])
@pytest.mark.parametrize(
    "inherited_git_dir", [False, True], ids=["clean-env", "inherited-git-dir"]
)
def test_explicit_git_index_file_is_still_honoured(
    two_repos: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    relative: bool,
    inherited_git_dir: bool,
) -> None:
    """A hook's index selects staged bytes even with another repository inherited."""
    target, other = two_repos
    repo = target.parent.parent
    # Distinct base bytes prevent Git's rename detection from making the
    # other repository's HEAD look like the target's baseline.
    other.write_text("DECOY = 'another repository'\n", encoding="utf-8")
    _git(other.parent.parent, "add", "-A")
    _git(other.parent.parent, "commit", "-qm", "seed")
    real_index = repo / ".git" / "index"
    alt_index = repo / ".git" / "alt-index"
    alt_index.write_bytes(real_index.read_bytes())
    extra = repo / "pkg" / "extra.py"
    extra.write_text("X = 1\n", encoding="utf-8")
    _git(repo, "add", "pkg/extra.py", extra_env={"GIT_INDEX_FILE": str(alt_index)})
    real_before, alt_before = real_index.read_bytes(), alt_index.read_bytes()

    assert changed_line_ranges(":staged", repo) == {target.resolve(): [(3, 3)]}

    if inherited_git_dir:
        monkeypatch.setenv("GIT_DIR", str(other.parent.parent / ".git"))
    monkeypatch.setenv(
        "GIT_INDEX_FILE", ".git/alt-index" if relative else str(alt_index)
    )
    assert changed_line_ranges(":staged", repo) == {
        target.resolve(): [(3, 3)],
        extra.resolve(): [(1, 1)],
    }
    assert real_index.read_bytes() == real_before
    assert alt_index.read_bytes() == alt_before


def test_main_enforce_modified_ignores_inherited_git_dir(
    two_repos: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """End to end: the gate judges the target repo's staged edit, not the other's."""
    target, other = two_repos
    repo = target.parent.parent
    target.write_text(
        "from pydantic import BaseModel\n\nclass ModelX(BaseModel):\n    a: str\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    from omnibase_core.validation.pydantic_module_index import module_for_path

    baseline = _write_baseline(
        tmp_path / "baseline.yaml", [f"{module_for_path(target)[0]}:ModelX"]
    )
    waivers = _empty_waivers(tmp_path / "waivers.yaml")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("GIT_DIR", str(other.parent.parent / ".git"))

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
    assert "ModelX" in capsys.readouterr().err


# ===========================================================================
# Working-tree modified-model enforcement (OMN-17572): ``pre-commit run
# --all-files`` runs on an unstaged tree, so ``:staged`` alone is blind to it.
# ===========================================================================
BROKEN_BASE = (
    "from pydantic import BaseModel\n"
    "\n"
    "class ModelUntouched(BaseModel):\n"
    "    a: str\n"
    "\n"
    "class ModelTouched(BaseModel):\n"
    "    b: str\n"
)
BROKEN_EDITED = BROKEN_BASE + "    c: int = 0\n"


def _seed_baselined(
    git_repo: Path, module_name: str = "mod_touched"
) -> tuple[Path, Path, Path]:
    """Commit a module with two baselined, still-broken models.

    Returns ``(module, baseline, waivers)``.
    """
    from omnibase_core.validation.pydantic_module_index import module_for_path

    module = git_repo / "pkg" / f"{module_name}.py"
    module.write_text(BROKEN_BASE, encoding="utf-8")
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "seed")
    prefix = module_for_path(module)[0]
    baseline = _write_baseline(
        git_repo / "baseline.yaml",
        [f"{prefix}:ModelUntouched", f"{prefix}:ModelTouched"],
    )
    return module, baseline, _empty_waivers(git_repo / "waivers.yaml")


def _run_gate(baseline: Path, waivers: Path, ref: str, *paths: str) -> int:
    return main(
        [
            *(paths or ("pkg",)),
            "--baseline",
            str(baseline),
            "--waivers",
            str(waivers),
            "--enforce-modified",
            ref,
        ]
    )


def test_unstaged_modification_of_baselined_model_fails_under_worktree_ref(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The ``pre-commit run --all-files`` shape: edit on disk, nothing staged."""
    module, baseline, waivers = _seed_baselined(git_repo)
    monkeypatch.chdir(git_repo)
    assert _run_gate(baseline, waivers, ":worktree") == 0

    module.write_text(BROKEN_EDITED, encoding="utf-8")  # unstaged

    assert _run_gate(baseline, waivers, ":worktree") == 1
    err = capsys.readouterr().err
    assert "MODIFIED" in err
    assert "ModelTouched" in err
    assert "ModelUntouched" not in err


def test_staged_modification_of_baselined_model_fails_under_worktree_ref(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, baseline, waivers = _seed_baselined(git_repo)
    monkeypatch.chdir(git_repo)
    module.write_text(BROKEN_EDITED, encoding="utf-8")
    _git(git_repo, "add", "-A")

    assert _run_gate(baseline, waivers, ":worktree") == 1


def test_partly_staged_modification_fails_under_worktree_ref(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Staged edit to one model plus an unstaged edit to the other: both are seen."""
    module, baseline, waivers = _seed_baselined(git_repo)
    monkeypatch.chdir(git_repo)
    module.write_text(
        BROKEN_BASE.replace("a: str", "a: str\n    z: int = 1"), encoding="utf-8"
    )
    _git(git_repo, "add", "-A")
    module.write_text(
        BROKEN_BASE.replace("a: str", "a: str\n    z: int = 1") + "    c: int = 0\n",
        encoding="utf-8",
    )

    assert _run_gate(baseline, waivers, ":worktree") == 1


def test_untouched_baselined_models_pass_under_worktree_ref(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dirty tree that does not touch the baselined classes stays green."""
    _, baseline, waivers = _seed_baselined(git_repo)
    monkeypatch.chdir(git_repo)
    (git_repo / "pkg" / "unrelated.py").write_text("VALUE = 1\n", encoding="utf-8")
    (git_repo / "NOTES.md").write_text("notes\n", encoding="utf-8")
    _git(git_repo, "add", "NOTES.md")

    assert _run_gate(baseline, waivers, ":worktree") == 0


def test_new_model_without_forbid_fails_under_worktree_ref(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, baseline, waivers = _seed_baselined(git_repo)
    monkeypatch.chdir(git_repo)
    (git_repo / "pkg" / "brand_new.py").write_text(
        "from pydantic import BaseModel\n\nclass ModelBrandNew(BaseModel):\n"
        "    a: str\n",
        encoding="utf-8",
    )

    assert _run_gate(baseline, waivers, ":worktree") == 1
    assert "ModelBrandNew" in capsys.readouterr().err


def test_explicit_and_inherited_forbid_pass_when_modified_under_worktree_ref(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (git_repo / "pkg" / "good.py").write_text(
        "from pydantic import BaseModel, ConfigDict\n"
        "\n"
        "class ModelBase(BaseModel):\n"
        '    model_config = ConfigDict(extra="forbid")\n'
        "    a: str\n"
        "\n"
        "class ModelChild(ModelBase):\n"
        "    b: str\n",
        encoding="utf-8",
    )
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "seed")
    monkeypatch.chdir(git_repo)
    (git_repo / "pkg" / "good.py").write_text(
        (git_repo / "pkg" / "good.py").read_text(encoding="utf-8") + "    c: int = 0\n",
        encoding="utf-8",
    )
    baseline = _write_baseline(git_repo / "baseline.yaml", [])
    waivers = _empty_waivers(git_repo / "waivers.yaml")

    assert _run_gate(baseline, waivers, ":worktree") == 0


AWKWARD_FILENAMES = [
    pytest.param("with space.py", id="space"),
    pytest.param('quo"te.py', id="double-quote"),
    pytest.param("new\nline.py", id="newline"),
    pytest.param("tab\there.py", id="tab"),
    pytest.param("ünï.py", id="non-ascii"),
]


@pytest.mark.parametrize("ref", [":staged", ":worktree"])
@pytest.mark.parametrize("filename", AWKWARD_FILENAMES)
def test_changed_line_ranges_keeps_files_git_would_quote(
    git_repo: Path, filename: str, ref: str
) -> None:
    """git C-quotes these names in patch headers; the diff reader must still see them."""
    module = git_repo / "pkg" / filename
    module.write_text(BROKEN_BASE, encoding="utf-8")
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "seed")
    module.write_text(BROKEN_EDITED, encoding="utf-8")
    _git(git_repo, "add", "-A")

    ranges = changed_line_ranges(ref, git_repo)

    assert list(ranges) == [module.resolve()]
    assert ranges[module.resolve()] == [(8, 8)]


@pytest.mark.parametrize(
    "filename", [p for p in AWKWARD_FILENAMES if p.id in {"space", "tab", "non-ascii"}]
)
def test_awkward_filenames_are_not_silently_dropped_by_the_gate(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, filename: str
) -> None:
    """End to end: a baselined model in such a file counts as touched when edited."""
    module = git_repo / "pkg" / filename
    module.write_text(BROKEN_BASE, encoding="utf-8")
    _git(git_repo, "add", "-A")
    _git(git_repo, "commit", "-qm", "seed")
    baseline = _write_baseline(
        git_repo / "baseline.yaml",
        [f.fqn for f in scan_paths([module], use_runtime=True)],
    )
    waivers = _empty_waivers(git_repo / "waivers.yaml")
    monkeypatch.chdir(git_repo)
    assert _run_gate(baseline, waivers, ":worktree", str(module)) == 0

    module.write_text(BROKEN_EDITED, encoding="utf-8")

    assert _run_gate(baseline, waivers, ":worktree", str(module)) == 1


def test_worktree_ref_does_not_touch_the_index(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Preserve the index while rejecting a modified model, not an invalid ref."""
    module, baseline, waivers = _seed_baselined(git_repo)
    monkeypatch.chdir(git_repo)
    module.write_text(BROKEN_EDITED, encoding="utf-8")
    index = git_repo / ".git" / "index"
    before = index.read_bytes()

    assert _run_gate(baseline, waivers, ":worktree") == 1

    err = capsys.readouterr().err
    assert "MODIFIED" in err
    assert "ModelTouched" in err
    assert "ModelUntouched" not in err
    assert index.read_bytes() == before
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(os.environ),
    ).stdout
    assert staged == ""


def test_nonexistent_scan_path_fails_closed(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A supplied path that does not exist must not be skipped as 'nothing to scan'."""
    _, baseline, waivers = _seed_baselined(git_repo)
    monkeypatch.chdir(git_repo)

    assert _run_gate(baseline, waivers, ":worktree", "pkg/gone.py") == 1
    assert "pkg/gone.py" in capsys.readouterr().err


def test_precommit_hook_enforces_the_working_tree_not_only_the_index() -> None:
    """The shipped hook must pass ``:worktree`` so ``--all-files`` sees unstaged edits."""
    config = Path(__file__).resolve().parents[3] / ".pre-commit-config.yaml"
    text = config.read_text(encoding="utf-8")
    start = text.index("id: pydantic-extra-forbid")
    entry = text[start : text.index("stages:", start)]

    assert "--enforce-modified :worktree" in " ".join(entry.split())
    assert ":staged" not in entry


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


def test_waiver_expiring_within_horizon_fails_the_pull_request(tmp_path: Path) -> None:
    """omnibase_core run 36794165897 (OMN-20354): the ModelHandlerRoutingEntry
    waiver expired 2026-09-30; the PR's hook passed at 23:53 that day and the
    push at 00:04 on 10-01 went red. On its last valid day the waiver now fails
    with the pull-request horizon and stays active with none."""
    waivers = tmp_path / "waivers.yaml"
    waivers.write_text(
        'waivers:\n  - fqn: "m:M"\n    ticket: OMN-1\n    pr: x\n'
        "    expires_at: 2026-09-30\n",
        encoding="utf-8",
    )
    today = date(2026, 9, 30)
    active, errors = load_waivers(waivers, today, horizon_days=1)
    assert active == set()
    assert any("pull-request horizon" in error for error in errors)
    assert load_waivers(waivers, today) == ({"m:M"}, [])
    assert load_waivers(waivers, date(2026, 9, 29), horizon_days=1) == ({"m:M"}, [])
    expired_active, expired = load_waivers(waivers, date(2026, 10, 1))
    assert expired_active == set()
    assert any("EXPIRED" in error for error in expired)
