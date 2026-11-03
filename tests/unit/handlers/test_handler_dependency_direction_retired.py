# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A retired repository is refused through every channel (OMN-22385).

The fixtures run through the layer order shipped in the package, so the retired
list is read from ``contracts/repo_layers.yaml`` and no test row restates it.
Each fixture is legal while the repository sits on layer 0 (the lowest layer is
below every consumer) and is refused once the contract lists it as retired.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.dependency_direction import (
    ModelDependencyDirectionCheckInput,
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

_RETIRED = "omnibase_compat"
_RETIRED_DIST = "omnibase-compat"
_ORG = "OmniNode-ai"


def _check(
    files: dict[str, str], repo: str = "omnibase_infra"
) -> ModelValidationReport:
    return HandlerDependencyDirection().handle(
        ModelDependencyDirectionCheckInput(
            repo=repo,
            rules=load_dependency_direction_rules(),
            layer_map=load_layer_map(),
            files=tuple(ModelSourceFile(path=p, source=s) for p, s in files.items()),
        )
    )


def _fails(report: ModelValidationReport) -> list[str]:
    return [f.message for f in report.findings if f.severity == "FAIL"]


def test_packaged_layer_map_lists_the_retired_repository_and_no_layer_for_it() -> None:
    layer_map = load_layer_map()
    assert [entry.repo for entry in layer_map.retired] == [_RETIRED]
    assert layer_map.get(_RETIRED) is None
    assert all(entry.repo != _RETIRED for entry in layer_map.repos)


@pytest.mark.parametrize(
    ("path", "source"),
    [
        (
            "pyproject.toml",
            f'[project]\nname = "omnibase-infra"\ndependencies = ["{_RETIRED_DIST}==0.5.7"]\n',
        ),
        (
            "pyproject.toml",
            f'[project]\nname = "omnibase-infra"\n[project.optional-dependencies]\nx = ["{_RETIRED_DIST}>=0.5"]\n',
        ),
        (
            "pyproject.toml",
            f'[project]\nname = "omnibase-infra"\n[dependency-groups]\ndev = ["{_RETIRED_DIST}"]\n',
        ),
        (
            "pyproject.toml",
            f'[project]\nname = "omnibase-infra"\n[tool.uv]\noverride-dependencies = ["{_RETIRED_DIST}>=0.5,<0.6"]\n',
        ),
        (
            "pyproject.toml",
            f'[project]\nname = "omnibase-infra"\n[tool.uv.sources]\n{_RETIRED_DIST} = {{ path = "../{_RETIRED}" }}\n',
        ),
        ("requirements.txt", f"{_RETIRED_DIST}==0.5.7\n"),
        ("src/pkg/mod.py", f"from {_RETIRED}.contracts import thing\n"),
        (
            "docker/Dockerfile.runtime",
            f'RUN uv pip install "git+https://github.com/{_ORG}/{_RETIRED}.git@main"\n',
        ),
        (
            ".github/workflows/ci.yml",
            f"      - uses: actions/checkout@v4\n        with:\n          repository: {_ORG}/{_RETIRED}\n",
        ),
        (
            ".github/workflows/ci.yml",
            f"      - run: git clone https://github.com/{_ORG}/{_RETIRED}.git\n",
        ),
        (
            "scripts/setup.sh",
            f"git clone https://github.com/{_ORG}/{_RETIRED}.git ../{_RETIRED}\n",
        ),
    ],
    ids=[
        "pyproject-dependency",
        "pyproject-extra",
        "pyproject-group",
        "pyproject-override",
        "pyproject-uv-source",
        "requirements",
        "python-import",
        "dockerfile-install",
        "workflow-checkout",
        "workflow-clone",
        "script-clone",
    ],
)
def test_a_reference_to_the_retired_repository_is_refused(
    path: str, source: str
) -> None:
    fails = _fails(_check({path: source}))
    assert len(fails) == 1, fails
    assert "retired" in fails[0].lower()
    assert _RETIRED in fails[0]


def test_a_retired_reference_cannot_be_baselined_into_a_warning() -> None:
    report = _check(
        {
            "pyproject.toml": f'[project]\nname = "x"\ndependencies = ["{_RETIRED_DIST}"]\n'
        },
        repo="omnibase_infra",
    )
    assert [f.severity for f in report.findings] == ["FAIL"]


def test_a_repository_without_the_retired_name_passes() -> None:
    report = _check(
        {
            "pyproject.toml": '[project]\nname = "omnibase-infra"\ndependencies = ["omnibase-core>=0.47.60"]\n',
            "src/pkg/mod.py": "from omnibase_core.models import thing\n",
        }
    )
    assert _fails(report) == []
