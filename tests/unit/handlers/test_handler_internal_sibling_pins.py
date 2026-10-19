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
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers import handler_internal_sibling_pins_cli as cli
from omnibase_core.handlers.handler_internal_sibling_pins import (
    HandlerInternalSiblingPins,
    classify_ref,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_input import (
    ModelInternalSiblingPinsInput,
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


def _judge(source: str) -> ModelValidationReport:
    return HandlerInternalSiblingPins().handle(
        ModelInternalSiblingPinsInput(
            files=(ModelSourceFile(path="pyproject.toml", source=source),),
            contract=cli.load_contract(),
        )
    )


def _rules(report: ModelValidationReport) -> list[str]:
    return [f.message.rsplit("(rule ", 1)[-1].rstrip(")") for f in report.findings]


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


def test_cli_fails_a_release_pin_and_passes_a_dev_tag(tmp_path: Path) -> None:
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


def test_cli_missing_pyproject_is_an_error(tmp_path: Path) -> None:
    assert cli.main(["--root", str(tmp_path)]) == 1


def test_cli_precommit_mode_reads_only_pyproject_files(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(_pyproject(""))
    (tmp_path / "README.md").write_text("x")
    assert cli.main(["--root", str(tmp_path), "README.md"]) == 0
    assert cli.main(["--root", str(tmp_path), "pyproject.toml"]) == 1


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


def test_precommit_hook_runs_the_handler_module() -> None:
    hooks = yaml.safe_load((REPO_ROOT / ".pre-commit-hooks.yaml").read_text())
    hook = next(h for h in hooks if h["id"] == "check-internal-sibling-pins")
    assert (
        hook["entry"]
        == "python -m omnibase_core.handlers.handler_internal_sibling_pins_cli"
    )
    assert hook["files"] == r"(^|/)pyproject\.toml$"
