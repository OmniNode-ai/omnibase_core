# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427: discover private git sources and scope lock-time credentials.

Execute workflow scripts with GitHub's Bash errexit/pipefail settings and fake
git/uv commands, without contacting GitHub or exposing a real token.
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency-cascade.yml"
FIND_STEP = "Find private OmniNode git sources (OMN-17427)"
MINT_STEP = "Mint read token for private git sources (OMN-17427)"


def _step(name: str) -> dict[str, object]:
    with WORKFLOW_PATH.open() as handle:
        document = yaml.safe_load(handle)
    for step in document["jobs"]["open-bump-pr"]["steps"]:
        if step.get("name") == name:
            assert isinstance(step, dict)
            return step
    raise AssertionError(f"No step named {name!r}")


def _run_find(
    tmp_path: Path,
    pyproject: str | None,
    lockfile: str | None,
    *,
    private: bool = False,
) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    if pyproject is not None:
        (repo / "pyproject.toml").write_text(pyproject)
    if lockfile is not None:
        (repo / "uv.lock").write_text(lockfile)
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_git = bin_dir / "git"
    fake_git.write_text(
        """#!/bin/bash
set -eu
printf '%s\\t' "$@" >> "$GIT_PROBES"
printf '\\n' >> "$GIT_PROBES"
printf '%s\\n' "$PWD" >> "$GIT_PROBE_DIRS"
test "$GIT_TERMINAL_PROMPT" = 0
for arg in "$@"; do
  if [ "$PRIVATE_SOURCE" = true ] && [[ "$arg" = */omnibase_internal ]]; then
    exit 2
  fi
done
exit 0
"""
    )
    fake_git.chmod(0o755)
    run = _step(FIND_STEP).get("run")
    assert isinstance(run, str)
    script = tmp_path / "find.sh"
    script.write_text(run)
    return subprocess.run(
        [
            "env",
            f"PATH={bin_dir}:/usr/bin:/bin",
            f"RUNNER_TEMP={runner_temp}",
            f"GIT_PROBES={tmp_path / 'probes'}",
            f"GIT_PROBE_DIRS={tmp_path / 'probe-dirs'}",
            f"PRIVATE_SOURCE={str(private).lower()}",
            f"GITHUB_OUTPUT={tmp_path / 'github-output'}",
            "REPO_NAME=omninode_infra",
            "bash",
            "--noprofile",
            "--norc",
            "-eo",
            "pipefail",
            str(script),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


@pytest.mark.unit
def test_find_private_sources_deduplicates_and_probes_outside_checkout(
    tmp_path: Path,
) -> None:
    result = _run_find(
        tmp_path,
        """[project.urls]
Homepage = "https://github.com/OmniNode-ai/omninode_infra"
[dependency-groups]
dev = [
  "omnibase-internal @ git+https://github.com/OmniNode-ai/omnibase_internal@2d9981b6c57108a27d924dcf51c0517ae0756061",
  "self @ git+https://github.com/OmniNode-ai/omninode_infra.git@abc123",
]
[tool.uv.sources]
omnimarket = { git = "https://github.com/OmniNode-ai/omnimarket.git", rev = "abc123" }
""",
        'source = { git = "https://github.com/OmniNode-ai/omnibase_internal?rev=abc123#abc123" }\n',
        private=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (tmp_path / "github-output").read_text() == "repos=omnibase_internal\n"
    assert result.stdout.splitlines() == [
        "CASCADE-GIT-SOURCE name=omnibase_internal access=private",
        "CASCADE-GIT-SOURCE name=omnimarket access=public",
    ]
    probes = [
        line.split("\t")[:-1] for line in (tmp_path / "probes").read_text().splitlines()
    ]
    assert len(probes) == 2
    assert [probe[-2] for probe in probes] == [
        "https://github.com/OmniNode-ai/omnibase_internal",
        "https://github.com/OmniNode-ai/omnimarket",
    ]
    for probe in probes:
        assert probe == [
            "-c",
            "credential.helper=",
            "ls-remote",
            "--exit-code",
            probe[-2],
            "HEAD",
        ]
        assert not any("omninode_infra" in arg for arg in probe)
    assert (tmp_path / "probe-dirs").read_text().splitlines() == [
        str(tmp_path / "runner-temp")
    ] * 2


@pytest.mark.unit
@pytest.mark.parametrize(
    ("pyproject", "lockfile"),
    [
        ('dep = "git+https://github.com/OmniNode-ai/omnimarket@abc123"\n', None),
        (None, 'source = { git = "https://github.com/OmniNode-ai/omnimarket.git" }\n'),
    ],
)
def test_only_public_sources_need_no_token(
    tmp_path: Path, pyproject: str | None, lockfile: str | None
) -> None:
    result = _run_find(tmp_path, pyproject, lockfile)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (tmp_path / "github-output").read_text() == "repos=\n"
    assert result.stdout == "CASCADE-GIT-SOURCE name=omnimarket access=public\n"
    assert len((tmp_path / "probes").read_text().splitlines()) == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    ("pyproject", "lockfile"),
    [
        (
            '[project.urls]\nHomepage = "https://github.com/OmniNode-ai/omniclaude"\n',
            "version = 1\n",
        ),
        (None, None),
    ],
)
def test_no_git_sources_need_no_probes(
    tmp_path: Path, pyproject: str | None, lockfile: str | None
) -> None:
    result = _run_find(tmp_path, pyproject, lockfile)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (tmp_path / "github-output").read_text() == "repos=\n"
    assert result.stdout == ""
    assert not (tmp_path / "probes").exists()


@pytest.mark.unit
def test_private_source_token_wiring_and_step_order() -> None:
    find = _step(FIND_STEP)
    assert find["id"] == "git_sources"
    assert find["if"] == "steps.token_check.outputs.has_token == 'true'"
    assert find["env"] == {"REPO_NAME": "${{ matrix.repo }}"}
    mint = _step(MINT_STEP)
    assert mint["id"] == "git-source-token"
    assert mint["uses"] == (
        "actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1"
    )
    assert mint["if"] == (
        "steps.token_check.outputs.has_token == 'true' && "
        "steps.git_sources.outputs.repos != ''"
    )
    assert mint["with"] == {
        "app-id": "${{ secrets.onexbot-occ-app-id }}",
        "private-key": "${{ secrets.onexbot-occ-private-key }}",
        "owner": "OmniNode-ai",
        "repositories": "${{ steps.git_sources.outputs.repos }}",
        "permission-contents": "read",
    }
    with WORKFLOW_PATH.open() as handle:
        document = yaml.safe_load(handle)
    names = [step["name"] for step in document["jobs"]["open-bump-pr"]["steps"]]
    assert names.index("Checkout downstream repo") < names.index(FIND_STEP)
    assert names.index(FIND_STEP) == names.index("Set up uv") + 1
    assert names.index(MINT_STEP) == names.index(FIND_STEP) + 1
    assert names.index("Set branch and PR variables") == names.index(MINT_STEP) + 1
    assert names.index(MINT_STEP) < names.index("Upgrade lockfile")
    env = _step("Upgrade lockfile").get("env")
    assert isinstance(env, dict)
    assert env["GIT_SOURCE_TOKEN"] == "${{ steps.git-source-token.outputs.token }}"
    assert env["GIT_SOURCE_REPOS"] == "${{ steps.git_sources.outputs.repos }}"


def _run_lock(tmp_path: Path, token: str) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "test"\nversion = "0.1.0"\n'
    )
    (repo / "uv.lock").write_text("version = 1\n# original lock\n")
    for args in (
        ["git", "init", "-q"],
        ["git", "add", "pyproject.toml", "uv.lock"],
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Initial files",
        ],
    ):
        subprocess.run(args, cwd=repo, check=True, capture_output=True, timeout=10)

    (tmp_path / "cache").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(
        """#!/bin/bash
set -eu
cd "$UV_STATE/cache"
for name in omnibase_internal omnibase_internal.git omnimarket; do
  git config --get-urlmatch http.extraheader "https://github.com/OmniNode-ai/$name" > "$UV_STATE/header-$name" || true
done
exit 0
"""
    )
    fake_uv.chmod(0o755)
    run = _step("Upgrade lockfile").get("run")
    assert isinstance(run, str)
    assert "${{" not in run
    script = tmp_path / "lock.sh"
    script.write_text(run)
    return subprocess.run(
        [
            "env",
            f"PATH={bin_dir}:/usr/bin:/bin",
            f"UV_STATE={tmp_path}",
            "BUMP_PACKAGE=omnibase_core",
            "PKG_HYPHEN=omnibase-core",
            "RESOLVED=0.47.49",
            "CASCADE_WAIT_INTERVAL_S=1",
            "CASCADE_WAIT_TOTAL_S=5",
            f"GITHUB_ENV={tmp_path / 'github-env'}",
            "REPO_NAME=omnimemory",
            f"GIT_SOURCE_TOKEN={token}",
            "GIT_SOURCE_REPOS=omnibase_internal",
            "bash",
            "--noprofile",
            "--norc",
            "-eo",
            "pipefail",
            str(script),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


@pytest.mark.unit
@pytest.mark.parametrize("token", ["test-token", ""])
def test_lock_auth_is_scoped_to_private_sources(tmp_path: Path, token: str) -> None:
    result = _run_lock(tmp_path, token)
    assert result.returncode == 0, (result.stdout, result.stderr)
    auth = base64.b64encode(b"x-access-token:test-token").decode("ascii")
    expected = f"AUTHORIZATION: basic {auth}\n" if token else ""
    for name in ("omnibase_internal", "omnibase_internal.git"):
        assert (tmp_path / f"header-{name}").read_text() == expected
    assert (tmp_path / "header-omnimarket").read_text() == ""
    assert "test-token" not in result.stdout
    assert "test-token" not in result.stderr
    if token:
        assert f"::add-mask::{auth}\n" in result.stdout
        assert "CASCADE-GIT-SOURCE-AUTH repos=omnibase_internal\n" in result.stdout
    else:
        assert "::add-mask::" not in result.stdout
        assert "CASCADE-GIT-SOURCE-AUTH" not in result.stdout
