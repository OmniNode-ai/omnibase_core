# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the cross-repository dependency-direction COMPUTE node (OMN-19998).

One positive fixture per channel plus a negative control for each. Fixture
text is assembled from ``_ORG`` and ``_UP`` so this file holds no literal
install or clone line naming another repository.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_dependency_channel import EnumDependencyChannel
from omnibase_core.models.dependency_direction import (
    ModelDependencyDirectionBaselineEntry,
    ModelDependencyDirectionCheckInput,
    ModelRepoLayer,
    ModelRepoLayerMap,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_dependency_direction_check_effect.handler_dependency_direction import (
    HandlerDependencyDirection,
)
from omnibase_core.validation.checker_dependency_direction import (
    load_dependency_direction_rules,
    load_layer_map,
)

pytestmark = pytest.mark.unit

_ORG = "OmniNode-ai"
_UP = "omnimarket"  # the higher repository the fixtures reach for
_UP_DIST = "omnimarket"
_DOWN = "omnibase_core"

LAYERS = ModelRepoLayerMap(
    github_org=_ORG,
    repos=(
        ModelRepoLayer(
            repo="omnibase_core",
            layer=1,
            python_modules=("omnibase_core",),
            distributions=("omnibase-core",),
        ),
        ModelRepoLayer(
            repo="omnibase_spi",
            layer=2,
            python_modules=("omnibase_spi",),
            distributions=("omnibase-spi",),
        ),
        ModelRepoLayer(
            repo="onex_change_control",
            layer=2,
            python_modules=("onex_change_control",),
            distributions=("onex-change-control",),
        ),
        ModelRepoLayer(
            repo="omnibase_infra",
            layer=3,
            python_modules=("omnibase_infra",),
            distributions=("omnibase-infra",),
        ),
        ModelRepoLayer(
            repo="omnimarket",
            layer=5,
            python_modules=("omnimarket",),
            distributions=("omnimarket",),
        ),
    ),
)


def _check(
    files: dict[str, str],
    repo: str = "omnibase_infra",
    baseline: tuple[ModelDependencyDirectionBaselineEntry, ...] = (),
    stale: bool = False,
) -> ModelValidationReport:
    return HandlerDependencyDirection().handle(
        ModelDependencyDirectionCheckInput(
            repo=repo,
            rules=load_dependency_direction_rules(),
            layer_map=LAYERS,
            files=tuple(ModelSourceFile(path=p, source=s) for p, s in files.items()),
            baseline=baseline,
            report_stale_baseline=stale,
        )
    )


def _fails(report: ModelValidationReport) -> list[str]:
    return [f.message for f in report.findings if f.severity == "FAIL"]


# --- one positive and one negative control per channel ---------------------


@pytest.mark.parametrize(
    ("path", "source", "channel"),
    [
        ("src/pkg/mod.py", f"import {_UP}.nodes\n", "python_import"),
        ("tests/test_x.py", f"from {_UP}.nodes import thing\n", "python_import"),
        (
            "pyproject.toml",
            f'[project]\nname = "omnibase-infra"\ndependencies = ["{_UP_DIST}>=0.4"]\n',
            "pyproject",
        ),
        (
            "pyproject.toml",
            f'[project]\nname = "x"\n[dependency-groups]\ndev = ["{_UP_DIST}"]\n',
            "pyproject",
        ),
        (
            "pyproject.toml",
            f'[project]\nname = "x"\n[tool.uv.sources]\n{_UP} = {{ path = "../{_UP}" }}\n',
            "pyproject",
        ),
        ("requirements-dev.txt", f"{_UP_DIST}==0.4.1\n", "requirements"),
        (
            "docker/Dockerfile.runtime",
            "RUN uv pip install --no-deps \\\n"
            f'    "git+https://github.com/{_ORG}/{_UP}.git@dev#egg={_UP}"\n',
            "dockerfile",
        ),
        (
            "Dockerfile",
            f"RUN for repo in omnibase_core {_UP}; do \\\n"
            '      uv pip install "/workspace/$repo"; done\n',
            "dockerfile",
        ),
        (
            ".github/workflows/ci.yml",
            f"      - uses: actions/checkout@v4\n        with:\n          repository: {_ORG}/{_UP}\n",
            "workflow",
        ),
        (
            ".github/workflows/ci.yml",
            f'        run: uv pip install "{_UP_DIST}==1.0"\n',
            "workflow",
        ),
        (".github/sibling-pins.yaml", f"repository: {_ORG}/{_UP}\n", "workflow"),
        (
            "scripts/bootstrap.sh",
            f"git clone https://github.com/{_ORG}/{_UP}.git ../{_UP}\n",
            "script",
        ),
        ("scripts/fetch.py", f'CMD = "gh repo clone {_ORG}/{_UP}"\n', "script"),
        ("Makefile", f"deps:\n\tpip install -e ../{_UP}\n", "script"),
    ],
)
def test_upward_reference_fails(path: str, source: str, channel: str) -> None:
    report = _check({path: source})
    fails = _fails(report)
    assert report.overall_status == "FAIL"
    assert len(fails) == 1, fails
    assert f"depends on {_UP} (layer 5, above it) via {channel}" in fails[0]
    assert fails[0].startswith(f"{path}:")


@pytest.mark.parametrize(
    ("path", "source"),
    [
        # downward references are allowed on every channel
        ("src/pkg/mod.py", f"from {_DOWN}.models import X\nimport omnibase_spi\n"),
        (
            "pyproject.toml",
            '[project]\nname = "x"\ndependencies = ["omnibase-core>=1"]\n',
        ),
        ("requirements.txt", "omnibase-core==1.0\n"),
        ("Dockerfile", f"RUN git clone https://github.com/{_ORG}/{_DOWN}.git\n"),
        (".github/workflows/ci.yml", f"          repository: {_ORG}/{_DOWN}\n"),
        # a reusable workflow or action is CI inheritance, not a dependency
        (
            ".github/workflows/ci.yml",
            f"    uses: {_ORG}/{_UP}/.github/workflows/gate.yml@0123abcd\n",
        ),
        # a mention without an install, clone or fetch verb
        ("Dockerfile", f"# installs {_UP} later\nLABEL note={_UP}\n"),
        ("scripts/run.sh", f'echo "{_UP} is downstream"\n'),
        # prose with a capitalised name is not a path or a distribution
        ("scripts/check.sh", "echo 'Omnimarket: curl -sf http://localhost:3000'\n"),
        # a relative import and a module that merely shares a prefix
        ("src/pkg/mod.py", f"from . import {_UP}\nimport {_UP}_extras\n"),
        # fixture data and test strings are not scanned for installs or imports
        ("tests/fixtures/sample.py", f"import {_UP}\n"),
        ("tests/scripts/test_x.py", f'LINE = "pip install {_UP}"\n'),
        # a file type the check does not read
        ("docs/guide.md", f"pip install {_UP}\n"),
        # the repository's own name
        (
            "scripts/self.sh",
            "git clone https://github.com/OmniNode-ai/omnibase_infra\n",
        ),
    ],
)
def test_negative_controls_pass(path: str, source: str) -> None:
    report = _check({path: source})
    assert report.overall_status == "PASS", [f.message for f in report.findings]


def test_same_layer_reference_fails() -> None:
    report = _check(
        {
            "pyproject.toml": '[project]\nname = "x"\ndependencies = ["onex-change-control"]\n'
        },
        repo="omnibase_spi",
    )
    fails = _fails(report)
    assert len(fails) == 1
    assert "onex_change_control (layer 2, same layer as it) via pyproject" in fails[0]


def test_baselined_violation_warns_and_stale_entry_warns() -> None:
    baseline = (
        ModelDependencyDirectionBaselineEntry(
            path="src/pkg/mod.py",
            channel=EnumDependencyChannel.PYTHON_IMPORT,
            target=_UP,
            ticket="OMN-19998",
        ),
        ModelDependencyDirectionBaselineEntry(
            path="src/gone.py",
            channel=EnumDependencyChannel.PYTHON_IMPORT,
            target=_UP,
            ticket="OMN-19998",
        ),
    )
    files = {"src/pkg/mod.py": f"import {_UP}\nimport {_UP}.x\n"}

    report = _check(files, baseline=baseline, stale=True)
    assert report.overall_status == "WARN"
    messages = [f.message for f in report.findings]
    assert len(messages) == 2, messages
    assert messages[0].startswith("baselined (OMN-19998): src/pkg/mod.py:1:")
    assert messages[1].startswith("stale baseline entry (OMN-19998): src/gone.py")

    # pre-commit mode reads a subset of files: no stale reporting
    assert len(_check(files, baseline=baseline, stale=False).findings) == 1


def test_baseline_does_not_cover_a_new_channel_or_file() -> None:
    baseline = (
        ModelDependencyDirectionBaselineEntry(
            path="src/pkg/mod.py",
            channel=EnumDependencyChannel.PYTHON_IMPORT,
            target=_UP,
            ticket="OMN-19998",
        ),
    )
    report = _check(
        {"src/pkg/mod.py": f"import {_UP}\n", "src/pkg/new.py": f"import {_UP}\n"},
        baseline=baseline,
    )
    assert report.overall_status == "FAIL"
    assert [f.location for f in report.findings if f.severity == "FAIL"] == [
        "src/pkg/new.py:1"
    ]


def test_undeclared_repository_is_error() -> None:
    report = _check({"src/a.py": "import os\n"}, repo="not_a_repo")
    assert report.overall_status == "ERROR"


def test_duplicate_name_across_repositories_is_refused() -> None:
    with pytest.raises(ValueError, match="declared by two repositories"):
        ModelRepoLayerMap(
            github_org=_ORG,
            repos=(
                ModelRepoLayer(repo="a", layer=0, distributions=("shared",)),
                ModelRepoLayer(repo="b", layer=1, python_modules=("shared",)),
            ),
        )


def test_packaged_layer_map_keeps_rule_7_and_the_market_ruling() -> None:
    layer_map = load_layer_map()
    layer = {entry.repo: entry.layer for entry in layer_map.repos}
    assert (
        layer["omnibase_compat"]
        < layer["omnibase_core"]
        < layer["omnibase_spi"]
        < layer["omnibase_infra"]
        < layer["omnimarket"]
    )
