# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Cross-repository dependency-pin check (OMN-22360): each rule fires and passes.

Every repository, distribution, layer and bound below is fixture data handed to the
check through its two overlays, once in memory (models) and once from files, so a
rule value in the checker code would make the overlay-swap tests fail.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.dependency_direction.model_repo_layer import ModelRepoLayer
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.dependency_pins.model_dependency_hook_history import (
    ModelDependencyHookHistory,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_request import (
    ModelDependencyPinFactsRequest,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_result import (
    ModelDependencyPinFactsResult,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_hook_repo import (
    ModelDependencyPinHookRepo,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_policy import (
    ModelDependencyPinPolicy,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_style_override import (
    ModelDependencyPinStyleOverride,
)
from omnibase_core.models.dependency_pins.model_dependency_pins_input import (
    ModelDependencyPinsInput,
)
from omnibase_core.models.dependency_pins.model_dependency_release_inventory import (
    ModelDependencyReleaseInventory,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time import (
    ModelPrecommitRevTime,
)
from omnibase_core.validation import checker_dependency_pins as checker
from omnibase_core.validation.validator_dependency_pins import (
    ValidatorDependencyPins,
    load_dependency_pin_policy,
    load_layer_order,
)

pytestmark = pytest.mark.unit

HOOK_URL = "https://example.invalid/acme/hooks"


def _rules() -> dict[str, ModelValidatorRule]:
    validator = ValidatorDependencyPins(lambda _r: ModelDependencyPinFactsResult())
    return {r.rule_id: r for r in validator.contract.rules}


RULES = _rules()


def _layers(order: dict[str, int] | None = None) -> ModelRepoLayerMap:
    order = order or {"base": 0, "middle": 1, "top": 2}
    return ModelRepoLayerMap(
        github_org="acme",
        repos=tuple(
            ModelRepoLayer(repo=repo, layer=layer, distributions=(f"{repo}-pkg",))
            for repo, layer in order.items()
        ),
    )


def _policy(**update: object) -> ModelDependencyPinPolicy:
    base = ModelDependencyPinPolicy(
        edge_tables=("project", "optional", "group", "uv_dev", "override"),
        pin_style="range",
        release_tag_pattern=r"^v(?P<version>[0-9]+(?:\.[0-9]+)*)$",
        tag_inventory_url="https://example.invalid/{org}/{repo}.git",
        max_releases_behind=1,
        specifier_must_admit_newest_release=True,
        hook_repos=(ModelDependencyPinHookRepo(url=HOOK_URL, repo="base"),),
        hook_rev_max_releases_behind=1,
    )
    return base.model_copy(update=update)


def _manifest(name: str, *deps: str, extra: str | None = None) -> str:
    lines = ["[project]", f'name = "{name}"', "dependencies = ["]
    lines += [f'    "{dep}",' for dep in deps]
    lines.append("]")
    if extra is not None:
        lines += ["[project.optional-dependencies]", f'x = ["{extra}"]']
    return "\n".join(lines) + "\n"


def _lock(*packages: tuple[str, str, tuple[str, ...]]) -> str:
    chunks = []
    for name, version, deps in packages:
        chunk = f'[[package]]\nname = "{name}"\nversion = "{version}"\n'
        if deps:
            chunk += (
                "dependencies = ["
                + ", ".join(f'{{ name = "{d}" }}' for d in deps)
                + "]\n"
            )
        chunks.append(chunk)
    return "version = 1\n\n" + "\n".join(chunks)


def _inventory(repo: str, *versions: str) -> ModelDependencyReleaseInventory:
    return ModelDependencyReleaseInventory(repo=repo, versions=versions)


def _request(
    manifest: str,
    *,
    lock: str | None = None,
    precommit: str | None = None,
    layers: ModelRepoLayerMap | None = None,
    policy: ModelDependencyPinPolicy | None = None,
    inventories: tuple[ModelDependencyReleaseInventory, ...] = (),
    histories: tuple[ModelDependencyHookHistory, ...] = (),
) -> ModelDependencyPinsInput:
    return ModelDependencyPinsInput(
        manifest_path="pyproject.toml",
        manifest_text=manifest,
        lock_path="uv.lock",
        lock_text=lock,
        precommit_path=".pre-commit-config.yaml",
        precommit_text=precommit,
        layer_map=layers or _layers(),
        policy=policy or _policy(),
        inventories=inventories,
        hook_histories=histories,
    )


def _codes(issues: Iterable[ModelValidationIssue]) -> list[str]:
    return sorted(str(i.code) for i in issues)


def _run(request: ModelDependencyPinsInput) -> list[str]:
    return _codes(checker.check_dependency_pins(request, RULES))


ALL_RELEASED = (
    _inventory("base", "1.0.0", "1.1.0"),
    _inventory("middle", "2.0.0"),
    _inventory("top", "3.0.0"),
)


# --- layer order ------------------------------------------------------------


def test_layer_order_refuses_an_edge_up_the_order() -> None:
    request = _request(
        _manifest("middle-pkg", "top-pkg>=3.0,<4"), inventories=ALL_RELEASED
    )
    assert _run(request) == ["layer_order"]


def test_layer_order_refuses_an_edge_on_the_same_layer() -> None:
    layers = _layers({"base": 0, "middle": 1, "top": 1})
    request = _request(
        _manifest("middle-pkg", "top-pkg>=3.0,<4"),
        layers=layers,
        inventories=ALL_RELEASED,
    )
    assert _run(request) == ["layer_order"]


def test_layer_order_passes_an_edge_down_the_order() -> None:
    request = _request(
        _manifest("top-pkg", "middle-pkg>=2.0,<3", "base-pkg>=1.1,<2"),
        inventories=ALL_RELEASED,
    )
    assert _run(request) == []


def test_layer_order_reads_extras_groups_and_overrides() -> None:
    manifest = (
        _manifest("base-pkg", extra="middle-pkg>=2,<3")
        + '[dependency-groups]\ndev = ["top-pkg>=3,<4"]\n'
        + '[tool.uv]\noverride-dependencies = ["middle-pkg>=2,<3"]\n'
    )
    issues = checker.check_dependency_pins(
        _request(manifest, inventories=ALL_RELEASED), RULES
    )
    assert _codes(issues) == ["layer_order"] * 3
    assert {"extra:x", "group:dev", "override"} == {
        m
        for i in issues
        for m in ("extra:x", "group:dev", "override")
        if m in i.message
    }


def test_layer_order_ignores_a_table_the_policy_does_not_count() -> None:
    manifest = _manifest("base-pkg") + '[dependency-groups]\ndev = ["top-pkg>=3,<4"]\n'
    request = _request(
        manifest,
        policy=_policy(edge_tables=("project",)),
        inventories=ALL_RELEASED,
    )
    assert _run(request) == []


def test_repo_not_in_layer_map_refuses_an_undeclared_repository() -> None:
    request = _request(_manifest("stranger-pkg"))
    assert _run(request) == ["repo_not_in_layer_map"]


# --- cycle -----------------------------------------------------------------


def test_cycle_refuses_a_declared_edge_closed_by_the_locked_graph() -> None:
    lock = _lock(
        ("base-pkg", "1.1.0", ("middle-pkg",)),
        ("middle-pkg", "2.0.0", ("base-pkg",)),
    )
    request = _request(
        _manifest("base-pkg", extra="middle-pkg>=2,<3"),
        lock=lock,
        inventories=ALL_RELEASED,
    )
    issues = checker.check_dependency_pins(request, RULES)
    assert _codes(issues) == ["dependency_cycle", "layer_order"]
    cycle = next(i for i in issues if i.code == "dependency_cycle")
    assert "base-pkg -> middle-pkg -> base-pkg" in cycle.message


def test_cycle_refuses_a_cycle_among_other_locked_packages() -> None:
    lock = _lock(
        ("top-pkg", "3.0.0", ("middle-pkg",)),
        ("middle-pkg", "2.0.0", ("base-pkg",)),
        ("base-pkg", "1.1.0", ("middle-pkg",)),
    )
    request = _request(
        _manifest("top-pkg", "middle-pkg>=2,<3"), lock=lock, inventories=ALL_RELEASED
    )
    assert _run(request) == ["dependency_cycle"]


def test_cycle_passes_an_acyclic_graph() -> None:
    lock = _lock(
        ("top-pkg", "3.0.0", ("middle-pkg", "base-pkg")),
        ("middle-pkg", "2.0.0", ("base-pkg",)),
        ("base-pkg", "1.1.0", ()),
    )
    request = _request(
        _manifest("top-pkg", "middle-pkg>=2,<3", "base-pkg>=1.1,<2"),
        lock=lock,
        inventories=ALL_RELEASED,
    )
    assert _run(request) == []


# --- release bound -----------------------------------------------------------


def test_release_bound_refuses_a_locked_version_past_the_bound() -> None:
    inventories = (_inventory("base", "1.0.0", "1.1.0", "1.2.0", "1.3.0"),)
    request = _request(
        _manifest("middle-pkg", "base-pkg>=1.0,<2"),
        lock=_lock(("middle-pkg", "2.0.0", ("base-pkg",)), ("base-pkg", "1.1.0", ())),
        inventories=inventories,
    )
    issues = checker.check_dependency_pins(request, RULES)
    assert _codes(issues) == ["release_behind"]
    assert "2 release(s) behind the newest release 1.3.0" in issues[0].message


def test_release_bound_passes_a_locked_version_inside_the_bound() -> None:
    inventories = (_inventory("base", "1.0.0", "1.1.0", "1.2.0"),)
    request = _request(
        _manifest("middle-pkg", "base-pkg>=1.0,<2"),
        lock=_lock(("middle-pkg", "2.0.0", ("base-pkg",)), ("base-pkg", "1.1.0", ())),
        inventories=inventories,
    )
    assert _run(request) == []


def test_release_bound_uses_the_specifier_floor_without_a_lock() -> None:
    inventories = (_inventory("base", "1.0.0", "1.1.0", "1.2.0", "1.3.0"),)
    behind = _request(
        _manifest("middle-pkg", "base-pkg>=1.0,<2"), inventories=inventories
    )
    inside = _request(
        _manifest("middle-pkg", "base-pkg>=1.2,<2"), inventories=inventories
    )
    assert _run(behind) == ["release_behind"]
    assert _run(inside) == []


def test_release_bound_refuses_a_specifier_that_excludes_the_newest_release() -> None:
    inventories = (_inventory("base", "1.0.0", "2.0.0"),)
    request = _request(
        _manifest("middle-pkg", "base-pkg>=1.0,<2"),
        lock=_lock(("base-pkg", "2.0.0", ())),
        inventories=inventories,
    )
    assert _run(request) == ["specifier_excludes_newest_release"]


def test_release_bound_specifier_rule_follows_the_policy_switch() -> None:
    inventories = (_inventory("base", "1.0.0", "2.0.0"),)
    request = _request(
        _manifest("middle-pkg", "base-pkg>=1.0,<2"),
        lock=_lock(("base-pkg", "2.0.0", ())),
        policy=_policy(specifier_must_admit_newest_release=False),
        inventories=inventories,
    )
    assert _run(request) == []


def test_release_bound_fails_closed_on_an_unreadable_inventory() -> None:
    inventory = ModelDependencyReleaseInventory(repo="base", error="host unreachable")
    request = _request(
        _manifest("middle-pkg", "base-pkg>=1.0,<2"), inventories=(inventory,)
    )
    missing = _request(_manifest("middle-pkg", "base-pkg>=1.0,<2"))
    assert _run(request) == ["release_inventory_unreadable"]
    assert _run(missing) == ["release_inventory_unreadable"]


# --- pin style -------------------------------------------------------------


def test_pin_style_refuses_an_exact_pin_where_the_policy_wants_a_range() -> None:
    request = _request(
        _manifest("middle-pkg", "base-pkg==1.1.0"), inventories=ALL_RELEASED
    )
    assert _run(request) == ["pin_style"]


def test_pin_style_refuses_a_range_where_the_policy_wants_an_exact_pin() -> None:
    policy = _policy(
        pin_style_overrides=(
            ModelDependencyPinStyleOverride(distribution="base-pkg", style="exact"),
        )
    )
    request = _request(
        _manifest("middle-pkg", "base-pkg>=1.1,<2"),
        policy=policy,
        inventories=ALL_RELEASED,
    )
    assert _run(request) == ["pin_style"]


def test_pin_style_passes_the_style_the_policy_wants() -> None:
    exact = _policy(pin_style="exact")
    assert (
        _run(
            _request(
                _manifest("middle-pkg", "base-pkg>=1.1,<2"), inventories=ALL_RELEASED
            )
        )
        == []
    )
    assert (
        _run(
            _request(
                _manifest("middle-pkg", "base-pkg==1.1.0"),
                policy=exact,
                inventories=ALL_RELEASED,
            )
        )
        == []
    )


# --- pre-commit hook revisions ---------------------------------------------


def _precommit(rev: str) -> str:
    return yaml.safe_dump(
        {
            "repos": [
                {"repo": HOOK_URL, "rev": rev, "hooks": [{"id": "a-hook"}]},
                {
                    "repo": "https://example.invalid/other/hooks",
                    "rev": "x1",
                    "hooks": [{"id": "b"}],
                },
            ]
        }
    )


def _history(rev: str, committed_at: int, *releases: int) -> ModelDependencyHookHistory:
    return ModelDependencyHookHistory(
        url=HOOK_URL,
        rev_times=(
            ModelPrecommitRevTime(repo=HOOK_URL, rev=rev, committed_at=committed_at),
        ),
        release_times=releases,
    )


def test_precommit_rev_refuses_a_revision_past_the_bound() -> None:
    request = _request(
        _manifest("top-pkg"),
        precommit=_precommit("abc"),
        histories=(_history("abc", 100, 50, 150, 200),),
    )
    issues = checker.check_dependency_pins(request, RULES)
    assert _codes(issues) == ["hook_rev_behind"]
    assert issues[0].line_number is not None


def test_precommit_rev_passes_a_revision_inside_the_bound() -> None:
    request = _request(
        _manifest("top-pkg"),
        precommit=_precommit("abc"),
        policy=_policy(hook_rev_max_releases_behind=14),
        histories=(_history("abc", 160, 50, 150, 200),),
    )
    assert _run(request) == []


# --- hook rev near the bound (warning half, no change to the bound) ---------

NEAR_BOUND = 14


def _near_request(behind: int, bound: int = NEAR_BOUND) -> ModelDependencyPinsInput:
    """A hook rev committed at 100 with ``behind`` release tags cut after it."""
    return _request(
        _manifest("top-pkg"),
        precommit=_precommit("abc"),
        policy=_policy(hook_rev_max_releases_behind=bound),
        histories=(_history("abc", 100, 50, *range(101, 101 + behind)),),
    )


def test_near_bound_stays_silent_below_the_window() -> None:
    assert _run(_near_request(11)) == []


def test_near_bound_warns_at_the_bound_minus_two() -> None:
    issues = checker.check_dependency_pins(_near_request(12), RULES)
    assert _codes(issues) == ["hook_rev_near_bound"]
    assert issues[0].severity == EnumSeverity.WARNING
    assert issues[0].line_number is not None
    assert "12" in issues[0].message
    assert str(NEAR_BOUND) in issues[0].message


def test_near_bound_warns_at_the_bound_and_does_not_refuse() -> None:
    issues = checker.check_dependency_pins(_near_request(14), RULES)
    assert _codes(issues) == ["hook_rev_near_bound"]
    assert issues[0].severity == EnumSeverity.WARNING


def test_near_bound_hands_over_to_the_refusal_past_the_bound() -> None:
    issues = checker.check_dependency_pins(_near_request(15), RULES)
    assert _codes(issues) == ["hook_rev_behind"]
    assert issues[0].severity == EnumSeverity.ERROR


def test_near_bound_reads_the_bound_from_the_policy() -> None:
    assert _run(_near_request(2, bound=4)) == ["hook_rev_near_bound"]
    assert _run(_near_request(1, bound=4)) == []
    assert _run(_near_request(5, bound=4)) == ["hook_rev_behind"]


def test_near_bound_reads_the_margin_from_the_rule_row() -> None:
    row = RULES["hook_rev_near_bound"]
    narrow = {
        **RULES,
        "hook_rev_near_bound": row.model_copy(
            update={"parameters": {**(row.parameters or {}), "margin": 0}}
        ),
    }
    assert _codes(checker.check_dependency_pins(_near_request(13), narrow)) == []
    assert _codes(checker.check_dependency_pins(_near_request(14), narrow)) == [
        "hook_rev_near_bound"
    ]


def test_near_bound_does_not_flag_a_current_pin_under_a_small_bound() -> None:
    assert _run(_near_request(0, bound=1)) == []


def test_near_bound_warning_does_not_fail_the_validator(tmp_path: Path) -> None:
    root = _repo(tmp_path, _manifest("top-pkg"))
    (root / ".pre-commit-config.yaml").write_text(_precommit("abc"), "utf-8")

    def read(_r: ModelDependencyPinFactsRequest) -> ModelDependencyPinFactsResult:
        return ModelDependencyPinFactsResult(
            inventories=ALL_RELEASED,
            hook_histories=(_history("abc", 100, 50, *range(101, 115)),),
        )

    validator = ValidatorDependencyPins(
        read,
        layer_order=_layers(),
        policy=_policy(hook_rev_max_releases_behind=NEAR_BOUND),
    )
    result = validator.validate(root)
    assert _codes(result.issues) == ["hook_rev_near_bound"]
    assert result.is_valid


def test_precommit_rev_fails_closed_on_an_unresolved_revision() -> None:
    unresolved = ModelDependencyHookHistory(url=HOOK_URL, release_times=(1,))
    errored = ModelDependencyHookHistory(url=HOOK_URL, error="clone failed")
    for histories in ((unresolved,), (errored,), ()):
        request = _request(
            _manifest("top-pkg"), precommit=_precommit("abc"), histories=histories
        )
        assert _run(request) == ["hook_rev_unresolved"]


def test_precommit_rev_ignores_a_hook_repository_the_policy_does_not_bound() -> None:
    request = _request(
        _manifest("top-pkg"),
        precommit=_precommit("abc"),
        policy=_policy(hook_repos=()),
    )
    assert _run(request) == []


def test_manifest_unreadable_is_a_finding_not_a_pass() -> None:
    assert _run(_request("[project\n")) == ["manifest_unreadable"]


# --- overlays --------------------------------------------------------------


def test_overlay_swap_layer_order_flips_the_verdict() -> None:
    manifest = _manifest("middle-pkg", "base-pkg>=1.1,<2")
    swapped = _layers({"base": 2, "middle": 1, "top": 0})
    assert _run(_request(manifest, inventories=ALL_RELEASED)) == []
    assert _run(_request(manifest, layers=swapped, inventories=ALL_RELEASED)) == [
        "layer_order"
    ]


def test_overlay_swap_policy_bounds_flip_the_verdict() -> None:
    inventories = (_inventory("base", "1.0.0", "1.1.0", "1.2.0", "1.3.0"),)
    manifest = _manifest("middle-pkg", "base-pkg>=1.1,<2")
    assert _run(_request(manifest, inventories=inventories)) == ["release_behind"]
    loose = _policy(max_releases_behind=5)
    assert _run(_request(manifest, policy=loose, inventories=inventories)) == []


def _write_overlays(
    tmp_path: Path, layers: ModelRepoLayerMap, policy: ModelDependencyPinPolicy
) -> tuple[Path, Path]:
    layer_file = tmp_path / "layers.yaml"
    policy_file = tmp_path / "policy.yaml"
    layer_file.write_text(yaml.safe_dump(layers.model_dump(mode="json")), "utf-8")
    policy_file.write_text(yaml.safe_dump(policy.model_dump(mode="json")), "utf-8")
    return layer_file, policy_file


def _repo(tmp_path: Path, manifest: str) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text(manifest, "utf-8")
    return root


def _facts(
    *inventories: ModelDependencyReleaseInventory,
) -> Callable[[ModelDependencyPinFactsRequest], ModelDependencyPinFactsResult]:
    def read(request: ModelDependencyPinFactsRequest) -> ModelDependencyPinFactsResult:
        return ModelDependencyPinFactsResult(
            inventories=tuple(i for i in inventories if i.repo in request.repos)
        )

    return read


def test_overlay_swap_from_files_follows_the_file(tmp_path: Path) -> None:
    root = _repo(tmp_path, _manifest("middle-pkg", "base-pkg>=1.1,<2"))
    straight = tmp_path / "straight"
    swapped = tmp_path / "swapped"
    straight.mkdir()
    swapped.mkdir()
    files = {
        "straight": _write_overlays(straight, _layers(), _policy()),
        "swapped": _write_overlays(
            swapped, _layers({"base": 2, "middle": 1, "top": 0}), _policy()
        ),
    }
    verdicts = {}
    for name, (layer_file, policy_file) in files.items():
        validator = ValidatorDependencyPins(
            _facts(*ALL_RELEASED),
            layer_order=load_layer_order(layer_file),
            policy=load_dependency_pin_policy(policy_file),
        )
        verdicts[name] = _codes(validator.validate(root).issues)
    assert verdicts == {"straight": [], "swapped": ["layer_order"]}


def test_overlay_in_memory_validator_reads_lock_and_precommit_beside_the_manifest(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path, _manifest("base-pkg", extra="middle-pkg>=2,<3"))
    (root / "uv.lock").write_text(
        _lock(("base-pkg", "1.1.0", ()), ("middle-pkg", "2.0.0", ("base-pkg",))),
        "utf-8",
    )
    (root / ".pre-commit-config.yaml").write_text(_precommit("abc"), "utf-8")
    seen: list[ModelDependencyPinFactsRequest] = []

    def read(request: ModelDependencyPinFactsRequest) -> ModelDependencyPinFactsResult:
        seen.append(request)
        return ModelDependencyPinFactsResult(
            inventories=ALL_RELEASED, hook_histories=(_history("abc", 10, 20, 30),)
        )

    validator = ValidatorDependencyPins(read, layer_order=_layers(), policy=_policy())
    for target in (root, root / "uv.lock", root / ".pre-commit-config.yaml"):
        assert _codes(validator.validate(target).issues) == [
            "dependency_cycle",
            "hook_rev_behind",
            "layer_order",
        ]
    assert seen[0].repos == ("middle",)
    assert [p.rev for p in seen[0].hook_pins] == ["abc"]


def test_overlay_shipped_files_parse_and_name_no_bound_in_code() -> None:
    layers = load_layer_order()
    policy = load_dependency_pin_policy()
    assert layers.repos
    assert policy.edge_tables
    source = Path(checker.__file__).read_text("utf-8")
    for entry in layers.repos:
        assert f'"{entry.repo}"' not in source
        for dist in entry.distributions:
            assert f'"{dist}"' not in source
