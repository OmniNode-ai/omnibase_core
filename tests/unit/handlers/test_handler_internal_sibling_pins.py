# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the internal sibling pin check (OMN-19998).

RULINGs 2026-10-16T07:34:18Z and 2026-10-16T09:35:49Z: internal siblings
resolve from dev merge tags, never a release. The negative control is the
dev-tag case: a consumer that pins every sibling to a dev merge tag passes,
and every release, sha or branch form of the same pin fails.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.handlers import handler_internal_sibling_pins_cli as cli
from omnibase_core.handlers.handler_internal_sibling_pins import (
    HandlerInternalSiblingPins,
    classify_ref,
    declared_sibling_repos,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_contract import (
    ModelInternalSiblingPinsContract,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_input import (
    ModelInternalSiblingPinsInput,
)
from omnibase_core.models.version_drift.model_sibling_dev_tags import (
    ModelSiblingDevTags,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "internal-sibling-pins.yml"
DEV_TAG = "dev-20261019100700-c330f5a7d597"
CORE_GIT = "https://github.com/OmniNode-ai/omnibase_core.git"
SHA = "ab" * 20  # a 40-hex commit sha


def _pyproject(
    sources: str = "", deps: str = '"omnibase-core>=0.47.0,<0.48.0"', extra: str = ""
) -> str:
    return (
        '[project]\nname = "omninode-claude"\nversion = "0.1.0"\n'
        f"dependencies = [{deps}]\n{extra}\n"
        f"[tool.uv.sources]\n{sources}\n"
    )


def _judge(
    source: str,
    dev_tags: tuple[ModelSiblingDevTags, ...] | None = None,
    contract: ModelInternalSiblingPinsContract | None = None,
) -> ModelValidationReport:
    return HandlerInternalSiblingPins().handle(
        ModelInternalSiblingPinsInput(
            files=(ModelSourceFile(path="pyproject.toml", source=source),),
            contract=contract if contract is not None else cli.load_contract(),
            dev_tags=dev_tags,
        )
    )


def _rules(report: ModelValidationReport) -> list[str]:
    return [f.message.rsplit("(rule ", 1)[-1].rstrip(")") for f in report.findings]


def _tag_after(*, hours: int = 0, seconds: int = 0) -> str:
    pinned = datetime.strptime(DEV_TAG.split("-")[1], "%Y%m%d%H%M%S").replace(
        tzinfo=UTC
    )
    stamp = (pinned + timedelta(hours=hours, seconds=seconds)).strftime("%Y%m%d%H%M%S")
    return f"dev-{stamp}-abcdef012345"


def _judge_tags(tags: tuple[str, ...]) -> ModelValidationReport:
    return _judge(
        _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", tag = "{DEV_TAG}" }}'),
        (ModelSiblingDevTags(repo="omnibase_core", tags=tags),),
    )


def test_pin_at_newest_passes_with_unordered_duplicate_and_non_dev_tags() -> None:
    older = "dev-20261018000000-abcdef012345"
    assert _judge_tags((DEV_TAG, "v99.0.0", older, DEV_TAG)).overall_status == "PASS"


@pytest.mark.parametrize("extra", [0, 1])
def test_merge_staleness_boundary(extra: int) -> None:
    bound = cli.load_contract().max_trailing_merges
    tags = (DEV_TAG,) + tuple(
        _tag_after(seconds=i) for i in range(1, bound + extra + 1)
    )
    report = _judge_tags(tags)
    if extra:
        assert report.overall_status == "FAIL"
        assert _rules(report) == ["stale_pin"]
        message = report.findings[0].message
        assert DEV_TAG in message and tags[-1] in message
        assert f"{bound + extra} merges" in message
        assert f"{bound} merges" in message
        assert "newest dev tag" in report.findings[0].remediation
    else:
        assert report.overall_status == "PASS"


@pytest.mark.parametrize("extra_seconds", [0, 1])
def test_hours_only_staleness_boundary(extra_seconds: int) -> None:
    newest = _tag_after(
        hours=cli.load_contract().max_trailing_hours, seconds=extra_seconds
    )
    report = _judge_tags((newest, DEV_TAG))
    assert _rules(report) == (["stale_pin"] if extra_seconds else [])
    if extra_seconds:
        assert "1 merges" in report.findings[0].message
        assert (
            f"{cli.load_contract().max_trailing_hours} hours"
            in report.findings[0].message
        )


@pytest.mark.parametrize("tags", [(), (_tag_after(seconds=1),)])
def test_absent_pin_fails_closed(tags: tuple[str, ...]) -> None:
    report = _judge_tags(tags)
    assert report.overall_status == "FAIL"
    assert _rules(report) == ["unverifiable_pin"]
    assert DEV_TAG in report.findings[0].message


def test_missing_sibling_inventory_fails_closed() -> None:
    source = _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", tag = "{DEV_TAG}" }}')
    for dev_tags in ((), (ModelSiblingDevTags(repo="omnibase_spi", tags=(DEV_TAG,)),)):
        report = _judge(source, dev_tags)
        assert report.overall_status == "FAIL"
        assert _rules(report) == ["unverifiable_pin"]
    assert _judge(source, None).overall_status == "PASS"


def test_invalid_timestamp_fails_closed() -> None:
    report = _judge_tags((DEV_TAG, "dev-20269999000000-abcdef012345"))
    assert _rules(report) == ["unverifiable_pin"]


def test_staleness_only_judges_tag_form_and_each_marker_entry() -> None:
    source = (
        f'omnibase-core = [{{ git = "{CORE_GIT}", tag = "{DEV_TAG}" }}, '
        f'{{ git = "{CORE_GIT}", tag = "v0.47.48" }}]'
    )
    assert _rules(_judge(_pyproject(source), ())) == ["unverifiable_pin", "release_tag"]


@pytest.mark.parametrize("field", ["max_trailing_merges", "max_trailing_hours"])
def test_contract_bounds_are_required_positive_ints_from_yaml(
    field: str, tmp_path: Path
) -> None:
    document = yaml.safe_load(cli.DEFAULT_CONTRACT.read_text())
    value = document[field]
    assert type(value) is int and value > 0
    assert getattr(cli.load_contract(), field) == value
    assert ModelInternalSiblingPinsContract.model_fields[field].is_required()
    for invalid in (0, -1, True, "1", 1.5):
        with pytest.raises(ValidationError):
            ModelInternalSiblingPinsContract.model_validate(
                {**document, field: invalid}
            )
    del document[field]
    with pytest.raises(ValidationError):
        ModelInternalSiblingPinsContract.model_validate(document)
    document[field] = value + 1
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump(document))
    contract = cli.load_contract(path)
    assert getattr(contract, field) == value + 1
    # The handler must honor a bound changed only in YAML, without code defaults.
    tags = (
        (DEV_TAG,) + tuple(_tag_after(seconds=i) for i in range(1, value + 2))
        if field == "max_trailing_merges"
        else (DEV_TAG, _tag_after(hours=value + 1))
    )
    source = _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", tag = "{DEV_TAG}" }}')
    inventories = (ModelSiblingDevTags(repo="omnibase_core", tags=tags),)
    assert _rules(_judge(source, inventories)) == ["stale_pin"]
    assert _judge(source, inventories, contract).overall_status == "PASS"


def test_sibling_dev_tags_is_frozen_and_strict() -> None:
    inventory = ModelSiblingDevTags(repo="omnibase_core", tags=(DEV_TAG,))
    with pytest.raises(ValidationError):
        inventory.repo = "omnibase_spi"
    with pytest.raises(ValidationError):
        ModelSiblingDevTags.model_validate({"repo": "omnibase_core", "tags": [DEV_TAG]})


def test_dev_tag_source_passes() -> None:
    report = _judge(
        _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", tag = "{DEV_TAG}" }}')
    )
    assert report.overall_status == "PASS"
    assert report.findings == ()


@pytest.mark.parametrize(
    ("ref", "rule"),
    [
        ("v0.47.48", "release_tag"),
        ("1.2", "release_tag"),
        ("1.2.3rc1", "release_tag"),
        ("1.2alpha4-post2", "release_tag"),
        ("1.2.\u0660rc1", "release_tag"),
        ("1.2--rc1", "not_dev_tag"),
        ("1.2.", "not_dev_tag"),
        ("v1", "not_dev_tag"),
        (DEV_TAG, None),
    ],
)
def test_release_ref_classification(ref: str, rule: str | None) -> None:
    assert classify_ref(ref, re.compile(cli.load_contract().dev_tag_pattern)) == rule


@pytest.mark.timeout(5)
@pytest.mark.parametrize("suffix", ["0" * 10_000, "a" * 10_000, ".0" * 10_000])
def test_long_invalid_release_ref_is_rejected(suffix: str) -> None:
    ref = "0.0" + suffix + "!"
    report = _judge(
        _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", tag = "{ref}" }}')
    )
    assert _rules(report) == ["not_dev_tag"]


@pytest.mark.parametrize(
    ("source", "rule"),
    [
        (f'omnibase-core = {{ git = "{CORE_GIT}", tag = "v0.47.48" }}', "release_tag"),
        (f'omnibase-core = {{ git = "{CORE_GIT}", rev = "{SHA}" }}', "bare_sha"),
        (f'omnibase-core = {{ git = "{CORE_GIT}", branch = "dev" }}', "branch"),
        (f'omnibase-core = {{ git = "{CORE_GIT}" }}', "branch"),
        (f'omnibase-core = {{ git = "{CORE_GIT}", tag = "nightly" }}', "not_dev_tag"),
        (f'omnibase-core = {{ git = "{CORE_GIT}", rev = "{DEV_TAG}" }}', "not_dev_tag"),
        (
            'omnibase-core = { path = "../omnibase_core", editable = true }',
            "not_dev_tag",
        ),
        ('omnibase-core = { index = "pypi" }', "not_dev_tag"),
        ("", "missing_source"),
    ],
)
def test_non_dev_tag_pin_fails(source: str, rule: str) -> None:
    report = _judge(_pyproject(source))
    assert report.overall_status == "FAIL"
    assert _rules(report) == [rule]


def test_git_source_of_another_repository_fails() -> None:
    other = "https://github.com/someone/omnibase_core.git"
    report = _judge(
        _pyproject(f'omnibase-core = {{ git = "{other}", tag = "{DEV_TAG}" }}')
    )
    assert _rules(report) == ["wrong_repo"]


def test_exact_release_version_fails_and_range_passes() -> None:
    source = f'omnibase-core = {{ git = "{CORE_GIT}", tag = "{DEV_TAG}" }}'
    assert _rules(_judge(_pyproject(source, deps='"omnibase-core==0.47.48"'))) == [
        "release_pin"
    ]
    assert _judge(_pyproject(source, deps='"omnibase-core>=0.47,<0.48"')).findings == ()
    assert _judge(_pyproject(source, deps='"omnibase-core==0.47.*"')).findings == ()


def test_override_direct_url_is_judged_by_its_ref() -> None:
    url = "https://github.com/OmniNode-ai/omnimarket.git"
    sha_override = (
        f'[tool.uv]\noverride-dependencies = ["omnimarket @ git+{url}@{SHA}"]\n'
    )
    tag_override = (
        f'[tool.uv]\noverride-dependencies = ["omnimarket @ git+{url}@{DEV_TAG}"]\n'
    )
    # [tool.uv] must precede [tool.uv.sources] for the TOML to stay one table each.
    sha_text = _pyproject(deps="").replace(
        "[tool.uv.sources]", sha_override + "[tool.uv.sources]"
    )
    tag_text = _pyproject(deps="").replace(
        "[tool.uv.sources]", tag_override + "[tool.uv.sources]"
    )
    assert _rules(_judge(sha_text)) == ["bare_sha"]
    assert _judge(tag_text).findings == ()


def test_sibling_in_extras_and_groups_needs_a_source() -> None:
    extra = (
        '[project.optional-dependencies]\nspi = ["omnibase-spi>=0.20"]\n'
        '[dependency-groups]\ndev = ["omnimarket>=0.4", {include-group = "x"}]\n'
    )
    report = _judge(_pyproject(deps="", extra=extra))
    assert sorted(f.location for f in report.findings) == [
        "pyproject.toml:tool.uv.sources.omnibase-spi",
        "pyproject.toml:tool.uv.sources.omnimarket",
    ]


def test_own_distribution_and_external_packages_are_not_judged() -> None:
    text = (
        '[project]\nname = "omnibase_core"\nversion = "0.1.0"\n'
        'dependencies = ["omnibase-core==1.0", "pydantic==2.11.0"]\n'
    )
    assert _judge(text).findings == ()


def test_marker_list_judges_every_entry() -> None:
    source = (
        f'omnibase-core = [{{ git = "{CORE_GIT}", tag = "{DEV_TAG}", marker = "sys_platform == \'linux\'" }}, '
        f'{{ git = "{CORE_GIT}", tag = "v0.47.48", marker = "sys_platform == \'darwin\'" }}]'
    )
    assert _rules(_judge(_pyproject(source))) == ["release_tag"]


def test_same_input_same_report() -> None:
    text = _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", rev = "{SHA}" }}')
    assert _judge(text).findings == _judge(text).findings


def test_unparseable_pyproject_is_an_error() -> None:
    assert _judge("[project\n").overall_status == "ERROR"


def test_contract_names_the_dev_tagged_producers() -> None:
    contract = cli.load_contract()
    assert {s.repo for s in contract.siblings} == {
        "omnibase_core",
        "omnibase_spi",
        "omnibase_infra",
        "omnimemory",
        "omnimarket",
        "omniintelligence",
    }
    layers = yaml.safe_load(
        (
            REPO_ROOT / "src" / "omnibase_core" / "contracts" / "repo_layers.yaml"
        ).read_text()
    )
    declared = {e["repo"]: e.get("distributions", []) for e in layers["repos"]}
    for sibling in contract.siblings:
        assert sibling.distribution in declared[sibling.repo]


def test_cli_fails_a_release_pin_and_passes_a_dev_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def read_tags(
        contract: ModelInternalSiblingPinsContract, repo: str
    ) -> ModelSiblingDevTags:
        calls.append((contract.github_org, repo))
        return ModelSiblingDevTags(repo=repo, tags=(DEV_TAG,))

    monkeypatch.setattr(cli, "read_dev_tags", read_tags)
    (tmp_path / "pyproject.toml").write_text(
        _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", tag = "v0.47.48" }}')
    )
    report_path = tmp_path / "report.json"
    assert cli.main(["--root", str(tmp_path), "--report-json", str(report_path)]) == 1
    assert "release_tag" in report_path.read_text()

    (tmp_path / "pyproject.toml").write_text(
        _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", tag = "{DEV_TAG}" }}')
    )
    assert cli.main(["--root", str(tmp_path)]) == 0
    assert calls == [("OmniNode-ai", "omnibase_core")] * 2


def test_cli_missing_pyproject_is_an_error(tmp_path: Path) -> None:
    assert cli.main(["--root", str(tmp_path)]) == 1


@pytest.mark.parametrize(
    "error",
    [
        OSError("git unavailable"),
        subprocess.CalledProcessError(1, ["git"]),
        subprocess.TimeoutExpired(["git"], 30),
    ],
)
def test_cli_tag_read_failure_is_an_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", tag = "{DEV_TAG}" }}')
    )

    def fail(
        contract: ModelInternalSiblingPinsContract, repo: str
    ) -> ModelSiblingDevTags:
        raise error

    monkeypatch.setattr(cli, "read_dev_tags", fail)
    report_path = tmp_path / "report.json"
    assert cli.main(["--root", str(tmp_path), "--report-json", str(report_path)]) == 1
    assert "ERROR:" in capsys.readouterr().out
    assert '"ERROR"' in report_path.read_text()
    assert cli.main(["--root", str(tmp_path), "--no-staleness"]) == 0


@pytest.mark.parametrize("missing", [False, True])
def test_cli_enforces_staleness_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing: bool,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        _pyproject(f'omnibase-core = {{ git = "{CORE_GIT}", tag = "{DEV_TAG}" }}')
    )
    newest = _tag_after(hours=cli.load_contract().max_trailing_hours + 1)
    monkeypatch.setattr(
        cli,
        "read_dev_tags",
        lambda contract, repo: ModelSiblingDevTags(
            repo=repo, tags=(newest,) if missing else (DEV_TAG, newest)
        ),
    )
    assert cli.main(["--root", str(tmp_path)]) == 1
    assert ("unverifiable_pin" if missing else "stale_pin") in capsys.readouterr().out


def test_tag_reader_uses_bounded_argv_and_ignores_peeled_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(
        argv: list[str], *, check: bool, capture_output: bool, text: bool, timeout: int
    ) -> subprocess.CompletedProcess[str]:
        assert argv == ["git", "ls-remote", "--tags", CORE_GIT, "refs/tags/dev-*"]
        assert check and capture_output and text and timeout > 0
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=f"{SHA}\trefs/tags/{DEV_TAG}\n{SHA}\trefs/tags/{DEV_TAG}^{{}}\n{SHA}\trefs/tags/{DEV_TAG}\n",
        )

    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli.read_dev_tags(
        cli.load_contract(), "omnibase_core"
    ) == ModelSiblingDevTags(
        repo="omnibase_core",
        tags=(DEV_TAG,),
    )


def test_declared_repos_include_all_dependency_channels_except_self() -> None:
    source = """
[project]
name = "omnibase-core"
dependencies = ["omnibase-core", "pydantic"]
[project.optional-dependencies]
spi = ["omnibase-spi"]
[dependency-groups]
dev = ["omnimarket"]
[tool.uv]
override-dependencies = ["omninode-memory"]
constraint-dependencies = ["omninode-intelligence"]
[tool.uv.sources]
omnibase-infra = {git = "https://github.com/OmniNode-ai/omnibase_infra.git"}
"""
    assert set(declared_sibling_repos(tomllib.loads(source), cli.load_contract())) == {
        sibling.repo
        for sibling in cli.load_contract().siblings
        if sibling.repo != "omnibase_core"
    }


def test_cli_precommit_mode_reads_only_pyproject_files(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(_pyproject(""))
    (tmp_path / "README.md").write_text("x")
    assert cli.main(["--root", str(tmp_path), "README.md"]) == 0
    assert cli.main(["--root", str(tmp_path), "--no-staleness", "pyproject.toml"]) == 1


def test_reusable_workflow_is_called_only_hosted_and_runs_the_handler() -> None:
    document = yaml.safe_load(WORKFLOW.read_text())
    triggers = document.get("on", document.get(True))
    assert set(triggers) == {"workflow_call"}
    job = document["jobs"]["internal-sibling-pins"]
    assert job["name"] == "Internal Sibling Pins"
    assert job["runs-on"] == "ubuntu-latest"
    run = job["steps"][-1]["run"]
    assert "python -m omnibase_core.handlers.handler_internal_sibling_pins_cli" in run
    assert '--root "$GITHUB_WORKSPACE/target"' in run
    assert "--no-staleness" not in run


def test_precommit_hook_runs_the_handler_module() -> None:
    hooks = yaml.safe_load((REPO_ROOT / ".pre-commit-hooks.yaml").read_text())
    hook = next(h for h in hooks if h["id"] == "check-internal-sibling-pins")
    assert (
        hook["entry"]
        == "python -m omnibase_core.handlers.handler_internal_sibling_pins_cli"
    )
    assert hook["files"] == r"(^|/)pyproject\.toml$"
    assert "--no-staleness" in hook["args"]
