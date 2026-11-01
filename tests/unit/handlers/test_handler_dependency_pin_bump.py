# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dependency pin rewrite and manifest opt-in regression tests (OMN-21478)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.version_drift import (
    ModelDependencyPin,
    ModelDependencyPinBumpRequest,
    ModelDependencyPinManifest,
)
from omnibase_core.nodes.node_dependency_pin_bump_effect.handler_dependency_pin_bump import (
    HandlerDependencyPinBump,
)
from omnibase_core.nodes.node_dependency_pin_bump_effect.runtime_dependency_pin_bump import (
    main,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

pytestmark = pytest.mark.unit

OLD_TAG = "dev-20261027010203-aaaaaaaaaaaa"
NEW_TAG = "dev-20261028010203-bbbbbbbbbbbb"
GIT_URL = "https://github.com/OmniNode-ai/omnibase_core"


@pytest.fixture
def manifest(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(
        "version: 1\nrepos:\n  - name: consumer\n    owner: OmniNode-ai\n    dependency_pin: {}\n"
        "    pin_sites: []\n  - name: handshake\n    owner: OmniNode-ai\n    pin_sites: []\n",
        encoding="utf-8",
    )
    return path


def _arguments(
    manifest: Path, repo_root: Path, tag: str = NEW_TAG, repo: str = "consumer"
) -> list[str]:
    return [
        "--manifest",
        str(manifest),
        "--repo",
        repo,
        "--repo-root",
        str(repo_root),
        "--dependency-tag",
        tag,
    ]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("inline", [True, False])
def test_rewrite_changes_only_source_tag_and_preserves_comments(
    tmp_path: Path,
    manifest: Path,
    capsys: pytest.CaptureFixture[str],
    newline: str,
    inline: bool,
) -> None:
    source = (
        f"[tool.uv.sources]\nomnibase-core = {{ git = '{GIT_URL}.git/', "
        f"tag = '{OLD_TAG}' }} # keep source comment\n"
        if inline
        else f'[tool.uv.sources.omnibase-core]\ngit = "{GIT_URL}"\n'
        f'tag  =  "{OLD_TAG}" # keep source comment\n'
    )
    content = (
        f'# keep quoted "{OLD_TAG}" in this comment\n'
        f'[project]\nname = "consumer"\ndescription = "{OLD_TAG}"\n'
        f"{source}\n[tool.uv.sources.other]\ntag = '{OLD_TAG}'\n"
    ).replace("\n", newline)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_bytes(content.encode("utf-8"))

    assert main(_arguments(manifest, tmp_path)) == 0

    expected = content.replace(f"tag = '{OLD_TAG}' }}", f"tag = '{NEW_TAG}' }}")
    if not inline:
        expected = content.replace(f'tag  =  "{OLD_TAG}"', f'tag  =  "{NEW_TAG}"')
    assert pyproject.read_bytes() == expected.encode("utf-8")
    assert capsys.readouterr().out == f"CHANGED: {pyproject} (tag -> {NEW_TAG})\n"
    assert main(_arguments(manifest, tmp_path)) == 0
    assert capsys.readouterr().out == ""
    assert pyproject.read_bytes() == expected.encode("utf-8")


@pytest.mark.parametrize("tag", ["v0.47.0", "dev-main", NEW_TAG + "\n"])
def test_rejects_non_dev_tag(
    tmp_path: Path, manifest: Path, capsys: pytest.CaptureFixture[str], tag: str
) -> None:
    assert main(_arguments(manifest, tmp_path, tag=tag)) == 1
    captured = capsys.readouterr()
    assert "not a dev merge tag" in captured.err
    assert captured.out == ""


@pytest.mark.parametrize(
    ("repo", "message"),
    [("absent", "is absent from"), ("handshake", "no declared dependency_pin")],
)
def test_requires_manifest_entry_with_dependency_opt_in(
    tmp_path: Path,
    manifest: Path,
    capsys: pytest.CaptureFixture[str],
    repo: str,
    message: str,
) -> None:
    assert main(_arguments(manifest, tmp_path, repo=repo)) == 1
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "source",
    [
        "",
        'omnibase-core = { path = "../omnibase_core" }',
        f'omnibase-core = {{ git = "{GIT_URL}_other", tag = "{OLD_TAG}" }}',
        f'omnibase-core = {{ git = "{GIT_URL}" }}',
        f'omnibase-core = {{ git = "{GIT_URL}", tag = 123 }}',
        f'omnibase-core = {{ git = "{GIT_URL}", tag = "{OLD_TAG}", rev = "abc" }}',
        f'omnibase-core = {{ git = "{GIT_URL}", tag = "{OLD_TAG}", branch = "dev" }}',
        'omnibase-core = "registry"',
        f'omnibase-core = [{{ git = "{GIT_URL}", tag = "{OLD_TAG}" }}]',
    ],
)
def test_refuses_missing_or_invalid_git_source(
    tmp_path: Path, manifest: Path, source: str
) -> None:
    content = f"[tool.uv.sources]\n{source}\n"
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(content, encoding="utf-8")
    with pytest.raises(ModelOnexError, match=r"omnibase-core.*git source"):
        HandlerDependencyPinBump().handle(
            ModelDependencyPinBumpRequest(
                manifest=manifest,
                repo="consumer",
                repo_root=tmp_path,
                dependency_tag=NEW_TAG,
            )
        )
    assert pyproject.read_text("utf-8") == content


def test_uses_configured_pyproject_and_case_insensitive_git_url(
    tmp_path: Path, manifest: Path
) -> None:
    manifest.write_text(
        "version: 1\nrepos:\n  - name: consumer\n    owner: OmniNode-ai\n    dependency_pin:\n      pyproject: custom.toml\n",
        encoding="utf-8",
    )
    pyproject = tmp_path / "custom.toml"
    pyproject.write_text(
        f'[tool.uv.sources.omnibase-core]\ngit = "{GIT_URL.upper()}"\n'
        f'tag = "{OLD_TAG}"\n',
        encoding="utf-8",
    )
    assert (
        HandlerDependencyPinBump()
        .handle(
            ModelDependencyPinBumpRequest(
                manifest=manifest,
                repo="consumer",
                repo_root=tmp_path,
                dependency_tag=NEW_TAG,
            )
        )
        .changed_path
        == pyproject
    )
    assert (
        tomllib.loads(pyproject.read_text())["tool"]["uv"]["sources"]["omnibase-core"][
            "tag"
        ]
        == NEW_TAG
    )


def test_real_manifest_dependency_opt_ins() -> None:
    """OMN-17427: no consumer is opted in, so no core-only dependency bump is emitted.

    omnimarket was the one opt-in. omnibase_infra pins omnibase-core by a dev merge
    tag in its own ``[tool.uv.sources]`` and uv honours a git dependency's sources, so
    an omnimarket head whose core tag differs from the one its pinned omnibase_infra
    commit names carries two conflicting omnibase-core URLs and its Sibling Release
    Compatibility Gate (OMN-20381) refuses the head. The opt-in is withdrawn; the
    defaults stay asserted so a future opt-in still gets pyproject.toml and uv.lock.
    """
    manifest = Path(__file__).resolve().parents[3] / "docs" / "downstream-repos.yaml"
    settings = load_yaml_content_as_model(
        manifest.read_text("utf-8"), ModelDependencyPinManifest
    )
    repos = {entry.name: entry.dependency_pin for entry in settings.repos}
    assert ModelDependencyPin().pyproject == "pyproject.toml"
    assert ModelDependencyPin().lock == "uv.lock"
    assert {name for name, pin in repos.items() if pin is not None} == set()
    for repo in ("omnimarket", "omnidash", "omniweb", "omninode_infra"):
        assert repos[repo] is None


def test_source_url_comes_from_repository_layer_map() -> None:
    """Pin the layer-map-derived source URL and fail where the helper is absent."""
    from omnibase_core.nodes.node_dependency_pin_bump_effect.handler_dependency_pin_bump import (
        _source_url,
    )

    assert _source_url() == GIT_URL
