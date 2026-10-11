# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The canonical-file-shape ratchet admits an imperative-guard allowlist (OMN-20946).

A workflow job that calls omnibase_core's imperative contract guard reusable
declares its ``allowlist-path`` the way an omnibase_core pre-commit hook
declares ``--baseline``: the reusable enforces that list shrink-only. Any other
caller (another repository's reusable, a local workflow, no caller at all)
declares nothing, and the allowlist is still a new exception file.

Every case runs ``check`` / ``main`` of the validator over a real git tree, so
the positive cases fail on a validator that does not read workflow callers.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.validators.canonical_file_shape import INDEX, GitRepo, check, main
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@example.com")
GUARD = "OmniNode-ai/omnibase_core/.github/workflows/imperative-contract-guard.yml"
# Short refs: the ratchet reads any ref, and a 40-hex literal trips detect-secrets.
CORE_SHA = "688ef17"
OCC_SHA = "725d296"
ALLOWLIST = "imperative-contract-allowlist.yaml"
CALLER = ".github/workflows/imperative-contract-guard.yml"
SELF_GATING = (
    "# self-gating"
    "-ok: central guard is intentionally shared across repos; caller PRs do not modify the referenced workflow."
)

# omnimemory's allowlist at onex_change_control 725d2967 (allowlists/omnimemory.yaml),
# byte for byte (sha256 e270f18453e84963c3a395e2fe7b0a543de5ceecc7bad7632180228b0e2e8953).
OMNIMEMORY_ALLOWLIST = """---
allowlisted_handlers:
  - path: src/omnimemory/handlers/adapters/adapter_valkey.py
    violations:
      - direct_db_cache_connection
    ticket: OMN-12673
    note: Existing live freestanding runtime adapter debt; dependency sweep must not broaden it.
  - path: src/omnimemory/nodes/node_memory_retrieval_effect/adapters/adapter_embedding_client.py
    violations:
      - raw_http_call
    ticket: OMN-12673
    note: Existing live freestanding runtime adapter debt; dependency sweep must not broaden it.
  - path: src/omnimemory/runtime/plugin.py
    violations:
      - hardcoded_private_ip
    ticket: OMN-12673
    note: Existing live freestanding runtime plugin debt; dependency sweep must not broaden it.
  - path: src/omnimemory/topics.py
    violations:
      - hardcoded_topic
    ticket: OMN-12673
    note: Existing live topic registry literals; dependency sweep must not broaden them.
"""

OMNIMEMORY_CALLER_HEAD = """name: Imperative Contract Guard

on:
  pull_request:
  push:
    branches:
      - main

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.sha }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

permissions:
  contents: read

jobs:
  imperative-contract-guard:
"""


def _omnimemory_caller(uses: str, with_line: str) -> str:
    return (
        OMNIMEMORY_CALLER_HEAD
        + f"    {SELF_GATING}\n"
        + f"    uses: {uses}\n"
        + "    with:\n"
        + f"      {with_line}\n"
    )


# omnimemory dev's caller before the repoint, and the canary's repointed caller
# (the lines of the occ-ret-g-mem-guard-g1-5d21 patch; only the refs are shortened).
OMNIMEMORY_CALLER_OCC = _omnimemory_caller(
    f"OmniNode-ai/onex_change_control/.github/workflows/imperative-contract-guard.yml@{OCC_SHA}",
    f"onex-change-control-ref: {OCC_SHA}",
)
OMNIMEMORY_CALLER_CORE = _omnimemory_caller(
    f"{GUARD}@{CORE_SHA}", f"allowlist-path: {ALLOWLIST}"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *IDENTITY, *args],
        cwd=repo,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _caller(uses: str, allowlist_path: str | None = ALLOWLIST) -> str:
    text = (
        "name: Imperative Contract Guard\n"
        "on:\n"
        "  pull_request:\n"
        "jobs:\n"
        "  imperative-contract-guard:\n"
        f"    uses: {uses}\n"
    )
    if allowlist_path is not None:
        text += f"    with:\n      allowlist-path: {allowlist_path}\n"
    return text


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "dev")
    _write(tmp_path, "src/pkg/nodes/node_x/handler.py", "X = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _rules(repo: Path) -> list[str]:
    _git(repo, "add", "-A")
    git = GitRepo(root=repo, env=scrub_git_location_env())
    return sorted(f.rule for f in check(git, INDEX, "HEAD"))


def _main(repo: Path) -> int:
    _git(repo, "add", "-A")
    return main(["--base", "HEAD"], repo_root=repo, env=scrub_git_location_env())


# --- AC1: a caller of omnibase_core's guard reusable declares its allowlist ---


@pytest.mark.parametrize(
    ("caller_path", "uses", "allowlist_path", "allowlist_file"),
    [
        (CALLER, f"{GUARD}@{CORE_SHA}", ALLOWLIST, ALLOWLIST),
        (".github/workflows/ci.yaml", f"{GUARD}@dev", ALLOWLIST, ALLOWLIST),
        (
            CALLER,
            f"{GUARD}@v1",
            "config/guard_allowlist.yaml",
            "config/guard_allowlist.yaml",
        ),
        (CALLER, f"{GUARD}@{CORE_SHA}", f"./{ALLOWLIST}", ALLOWLIST),
    ],
)
def test_core_guard_caller_declares_allowlist(
    repo: Path, caller_path: str, uses: str, allowlist_path: str, allowlist_file: str
) -> None:
    _write(repo, caller_path, _caller(uses, allowlist_path))
    _write(repo, allowlist_file, OMNIMEMORY_ALLOWLIST)
    assert _rules(repo) == []


def test_core_guard_declared_allowlist_only_shrinks_by_guard(repo: Path) -> None:
    _write(repo, CALLER, _caller(f"{GUARD}@{CORE_SHA}"))
    _write(repo, ALLOWLIST, "allowlisted_handlers:\n  - path: a.py\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "guard")
    _write(repo, ALLOWLIST, "allowlisted_handlers:\n  - path: a.py\n  - path: b.py\n")
    assert _rules(repo) == []


def test_core_guard_caller_beside_an_unparseable_workflow(repo: Path) -> None:
    _write(repo, ".github/workflows/broken.yml", "jobs: [unclosed\n")
    _write(repo, CALLER, _caller(f"{GUARD}@{CORE_SHA}"))
    _write(repo, ALLOWLIST, OMNIMEMORY_ALLOWLIST)
    assert _rules(repo) == []


# --- AC2: anything else declares nothing; the allowlist is still refused ---


@pytest.mark.parametrize(
    ("caller_path", "caller_text"),
    [
        pytest.param(None, None, id="no_declaring_caller"),
        pytest.param(
            CALLER, _caller(f"{GUARD}@{CORE_SHA}", None), id="no_declaring_caller_input"
        ),
        pytest.param(
            CALLER,
            _caller(f"{GUARD}@{CORE_SHA}", "other_allowlist.yaml"),
            id="no_declaring_caller_other_path",
        ),
        pytest.param(
            CALLER,
            _caller(
                "OmniNode-ai/onex_change_control/.github/workflows/"
                f"imperative-contract-guard.yml@{OCC_SHA}"
            ),
            id="not_core_reusable_other_repo",
        ),
        pytest.param(
            CALLER,
            _caller(
                f"SomeFork/omnibase_core/.github/workflows/imperative-contract-guard.yml@{CORE_SHA}"
            ),
            id="not_core_reusable_other_owner",
        ),
        pytest.param(
            CALLER,
            _caller("./.github/workflows/imperative-contract-guard.yml"),
            id="not_core_reusable_local_workflow",
        ),
        pytest.param(
            CALLER,
            _caller(f"OmniNode-ai/omnibase_core/.github/workflows/ci.yml@{CORE_SHA}"),
            id="not_core_reusable_other_core_workflow",
        ),
        pytest.param(CALLER, _caller(GUARD), id="not_core_reusable_without_ref"),
        pytest.param(
            ".github/workflows/nested/guard.yml",
            _caller(f"{GUARD}@{CORE_SHA}"),
            id="no_declaring_caller_nested_directory",
        ),
        pytest.param(
            "ci/imperative-contract-guard.yml",
            _caller(f"{GUARD}@{CORE_SHA}"),
            id="no_declaring_caller_outside_workflows",
        ),
        pytest.param(
            CALLER,
            _caller(f"{GUARD}@{CORE_SHA}") + "  broken: [unclosed\n",
            id="no_declaring_caller_unparseable",
        ),
    ],
)
def test_allowlist_without_core_guard_caller_refused(
    repo: Path, caller_path: str | None, caller_text: str | None
) -> None:
    if caller_path is not None and caller_text is not None:
        _write(repo, caller_path, caller_text)
    _write(repo, ALLOWLIST, OMNIMEMORY_ALLOWLIST)
    assert _rules(repo) == ["new-exception-file"]


def test_core_guard_caller_does_not_admit_other_allowlists(repo: Path) -> None:
    _write(repo, CALLER, _caller(f"{GUARD}@{CORE_SHA}"))
    _write(repo, ALLOWLIST, OMNIMEMORY_ALLOWLIST)
    _write(repo, ".onex_ratchets/other_allowlist.yaml", "- a\n")
    assert _rules(repo) == ["new-exception-file"]


# --- AC3: the omnimemory canary tree ---


@pytest.fixture
def omnimemory(repo: Path) -> Path:
    _write(repo, CALLER, OMNIMEMORY_CALLER_OCC)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "omnimemory dev caller")
    return repo


def test_omnimemory_canary_repointed_caller_passes(omnimemory: Path) -> None:
    _write(omnimemory, CALLER, OMNIMEMORY_CALLER_CORE)
    _write(omnimemory, ALLOWLIST, OMNIMEMORY_ALLOWLIST)
    assert _rules(omnimemory) == []
    assert _main(omnimemory) == 0


def test_omnimemory_canary_without_allowlist_path_refused(omnimemory: Path) -> None:
    _write(
        omnimemory,
        CALLER,
        OMNIMEMORY_CALLER_CORE.replace(
            f"    with:\n      allowlist-path: {ALLOWLIST}\n", ""
        ),
    )
    _write(omnimemory, ALLOWLIST, OMNIMEMORY_ALLOWLIST)
    assert _rules(omnimemory) == ["new-exception-file"]
    assert _main(omnimemory) == 1
