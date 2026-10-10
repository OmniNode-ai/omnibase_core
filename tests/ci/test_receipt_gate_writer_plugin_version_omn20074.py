# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Execute the writer-app plugin manifest version verdict against real git objects.

omniclaude's post-merge plugin version bump (OMN-20710, omniclaude#2644) moves
only the ``version`` of ``.claude-plugin/plugin.json`` and of the matching
``.claude-plugin/marketplace.json`` entry. The dod-verify writer_pin_only step
refused it ("changed path is not a dependency manifest or lockfile"), so a
required repo-evidence check would block every such bump. The step now hands a
manifest-only diff to the pinned verifier's
``classify_plugin_manifest_version_only`` (OMN-20074).
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from tests.ci.test_receipt_gate_writer_pin_only_in_job_omn17427 import (
    _assert_output,
    _run,
)
from tests.ci.test_receipt_gate_writer_workflow_pin_omn20074 import (
    _git,
    _write_files,
)

pytestmark = pytest.mark.unit

PLUGIN = "plugins/p/.claude-plugin/plugin.json"
MARKET = "plugins/m/.claude-plugin/marketplace.json"


def _plugin(version: str, description: str = "plugin") -> str:
    return json.dumps(
        {"name": "p", "description": description, "version": version}, indent=2
    )


def _market(version: str) -> str:
    return json.dumps(
        {"name": "m", "plugins": [{"name": "p", "version": version}]}, indent=2
    )


# A recording stand-in for the pinned verifier's classifiers. The plugin
# classifier mirrors the real one's contract: refuse non-manifest paths and
# unreadable sides, and admit a diff whose only change is a version value.
PROBE = dedent("""\
    import json, os
    from pathlib import Path

    def is_release_artifact_only_diff(paths):
        return False

    def classify_dependency_pin_only(paths, *, pyproject_head, pyproject_base):
        return False, "changed path is not a dependency manifest or lockfile: " + paths[0]

    def classify_workflow_core_pin_only(changed_paths, *, contents):
        return False, "changed path is not a workflow file: " + changed_paths[0]

    def classify_plugin_manifest_version_only(changed_paths, *, contents):
        Path(os.environ["CLASSIFIER_RECORD"]).write_text(json.dumps(
            {"paths": list(changed_paths), "contents": contents}))
        def strip(text):
            doc = json.loads(text)
            doc.pop("version", None)
            for entry in doc.get("plugins", []):
                entry.pop("version", None)
            return doc
        for path in changed_paths:
            head, base = contents.get(path, (None, None))
            if head is None or base is None:
                return False, f"plugin manifest unreadable at one or both refs: {path}"
            if strip(head) != strip(base):
                return False, f"{path} changes outside its version keys: description"
        return True, "plugin manifest version only: " + ", ".join(changed_paths)
    """)


def _prepare(
    tmp_path: Path,
    head_changes: dict[str, str | None],
    *,
    probe: str = PROBE,
) -> tuple[dict[str, str], Path]:
    workspace = tmp_path / "ws"
    repo = workspace / ".dod-verify/head_home/x"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _write_files(
        repo,
        {
            "pyproject.toml": '[project]\nname = "x"\nversion = "0.1.0"\n',
            PLUGIN: _plugin("2.4.59"),
            MARKET: _market("2.4.59"),
        },
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    _write_files(repo, head_changes)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "head")
    head = _git(repo, "rev-parse", "HEAD")
    # The verdict must come from git objects, never from the working tree.
    _write_files(repo, {PLUGIN: "not the committed manifest\n"})
    runner = tmp_path / "runner"
    runner.mkdir()
    stub = tmp_path / "stub"
    package = stub / "omnimarket"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "occ_content_probe.py").write_text(probe)
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "sys.argv = ['-', *sys.argv[2:]]; "
        "exec(compile(sys.stdin.read(), '<stdin>', 'exec'))"
    )
    launcher = tmp_path / "verifier"
    launcher.write_text(
        "#!/bin/bash\n"
        '[ "$1" = -I ] && [ "$2" = - ] || exit 1\n'
        "shift 2\n"
        f"exec {shlex.quote(sys.executable)} -I -c {shlex.quote(code)} "
        f'{shlex.quote(str(stub))} "$@"\n'
    )
    launcher.chmod(0o755)
    record = tmp_path / "classifier.json"
    return {
        "PATH": "/usr/bin:/bin",
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(tmp_path / "github_output"),
        "RUNNER_TEMP": str(runner),
        "REPO_SHORT": "x",
        "BASE_SHA": base,
        "HEAD_SHA": head,
        "DOD_VERIFY_PY": str(launcher),
        "CLASSIFIER_RECORD": str(record),
    }, record


def test_writer_plugin_version_bump_is_exempt(tmp_path: Path) -> None:
    env, record = _prepare(
        tmp_path, {PLUGIN: _plugin("2.4.60"), MARKET: _market("2.4.60")}
    )
    result = _run(env)
    _assert_output(env, exempt=True)
    recorded = json.loads(record.read_text())
    assert sorted(recorded["paths"]) == sorted([PLUGIN, MARKET])
    assert recorded["contents"] == {
        PLUGIN: [_plugin("2.4.60"), _plugin("2.4.59")],
        MARKET: [_market("2.4.60"), _market("2.4.59")],
    }
    assert "OCC writer app authored a plugin version bump" in result.stdout
    assert f"at {env['HEAD_SHA']}" in result.stdout
    assert f"merge base {env['BASE_SHA']}" in result.stdout
    assert "classify_plugin_manifest_version_only" in result.stdout


@pytest.mark.parametrize(
    ("head_changes", "reason"),
    [
        pytest.param(
            {PLUGIN: _plugin("2.4.60", description="edited")},
            "changes outside its version keys",
            id="version-and-description",
        ),
        pytest.param(
            {"plugins/q/.claude-plugin/plugin.json": _plugin("2.4.60")},
            "plugin manifest unreadable at one or both refs",
            id="added-manifest",
        ),
        pytest.param(
            {PLUGIN: None},
            "plugin manifest unreadable at one or both refs",
            id="deleted-manifest",
        ),
    ],
)
def test_writer_plugin_version_fails_closed(
    tmp_path: Path, head_changes: dict[str, str | None], reason: str
) -> None:
    env, _ = _prepare(tmp_path, head_changes)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert reason in result.stdout


def test_writer_plugin_version_never_reaches_the_classifier_for_a_mixed_diff(
    tmp_path: Path,
) -> None:
    env, record = _prepare(tmp_path, {PLUGIN: _plugin("2.4.60"), "src/x.py": "x\n"})
    _run(env)
    _assert_output(env, exempt=False)
    assert not record.exists()


def test_writer_plugin_version_fails_closed_on_a_verifier_without_the_classifier(
    tmp_path: Path,
) -> None:
    older = PROBE.split("def classify_plugin_manifest_version_only", 1)[0]
    env, _ = _prepare(tmp_path, {PLUGIN: _plugin("2.4.60")}, probe=older)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert "the pinned classifier failed" in result.stdout
