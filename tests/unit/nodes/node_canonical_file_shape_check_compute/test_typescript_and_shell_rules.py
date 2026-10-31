# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""TypeScript/React and shell shape rules for OMN-21332."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.handlers.handler_canonical_location_rules import (
    HandlerCanonicalLocationRules,
)
from omnibase_core.models.validation.model_canonical_file_shape_tree import (
    ModelCanonicalFileShapeTree,
)
from omnibase_core.models.validation.model_canonical_location_request import (
    ModelCanonicalLocationRequest,
)
from omnibase_core.validation.checker_canonical_file_shape import file_rule_refusals
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    BASELINE,
    RULES,
    baseline_text,
    init_repo,
    issues,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    git as _git,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    rules_hit as _rules,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    write as _write,
)

pytestmark = pytest.mark.unit

OLD_TOOL = "scripts/old_tool.py"
BASE_TEXT = "#!/usr/bin/env python3\na=1\nb=2\nc=3\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return init_repo(tmp_path)


_LOCATION_RULES = HandlerCanonicalLocationRules()


def typescript_workspace_roots(files: tuple[str, ...]) -> frozenset[str]:
    request = ModelCanonicalLocationRequest(tracked_files=files)
    return _LOCATION_RULES.handle(request).workspace_roots


def is_shell_script(path: str, head_bytes: bytes | None) -> bool:
    request = ModelCanonicalLocationRequest(path=path, head_bytes=head_bytes)
    return _LOCATION_RULES.handle(request).is_shell_script


def _is_canonical_location(
    path: str, workspace_roots: frozenset[str] = frozenset()
) -> bool:
    tree = ModelCanonicalFileShapeTree(
        files=(path, *(f"{root}/package.json" for root in sorted(workspace_roots))),
    )
    return path not in file_rule_refusals(tree, RULES)


def test_typescript_shape_workspace_needs_package_json(repo: Path) -> None:
    refused = {"scripts/src/api/runtime.ts", "lib/src/models/helper.ts"}
    web = "web/src/components/Nav.tsx"
    scoped = "packages/@omninode/ui/src/components/Button.tsx"
    for path in (*refused, web, scoped):
        _write(repo, path, "export const value = 1;\n")
    _write(repo, "packages/@omninode/ui/package.json", "{}\n")
    _git(repo, "add", "-A")

    expected = {(path, "noncanonical-file") for path in refused | {web}}
    assert {(f.file_path.as_posix(), f.code) for f in issues(repo)} == expected
    _write(repo, "web/package.json", "{}\n")
    assert {(f.file_path.as_posix(), f.code) for f in issues(repo)} == expected

    _git(repo, "add", "web/package.json")
    assert {(f.file_path.as_posix(), f.code) for f in issues(repo)} == {
        (path, "noncanonical-file") for path in refused
    }


def test_typescript_shape_workspace_roots_exact_forms() -> None:
    files = [
        "package.json",
        "web/package.json",
        "packages/package.json",
        "packages/ui/package.json",
        "packages/@omninode/ui/package.json",
        "src/package.json",
        "src/web/package.json",
        "nested/web/package.json",
        "packages/@omninode/package.json",
        "packages/@/ui/package.json",
        "packages/ui/nested/package.json",
        "packages/@omninode/ui/nested/package.json",
        "web/src/package.json",
        "other/package-lock.json",
        "web/src/components/Nav.tsx",
    ]
    assert typescript_workspace_roots(tuple(files)) == frozenset(
        {"web", "packages", "packages/ui", "packages/@omninode/ui"}
    )
    assert typescript_workspace_roots(()) == frozenset()


def test_typescript_shape_planted_outside_refused_and_admitted_in_location(
    repo: Path,
) -> None:
    pairs = (
        ("src/lib/fetchPlans.ts", "src/api/fetchPlans.ts"),
        ("src/widgets/PlanCard.tsx", "src/components/PlanCard.tsx"),
    )
    for refused, admitted in pairs:
        for path in (refused, admitted):
            _write(repo, path, "export const value = 1;\n")
    _git(repo, "add", "-A")
    findings = issues(repo)
    assert {(f.file_path.as_posix(), f.code) for f in findings} == {
        (refused, "noncanonical-file") for refused, _ in pairs
    }
    for finding in findings:
        assert finding.message == RULES.parameters.noncanonical_text


@pytest.mark.parametrize(
    "path",
    [
        "src/components/dashboard/Card.tsx",
        "src/pages/DashboardView.tsx",
        "src/hooks/useTimeRange.ts",
        "src/hooks/index.ts",
        "src/models/plan.ts",
        "src/api/client.ts",
        "src/generated/platform.ts",
        "src/contracts/envelope.ts",
        "src/handlers/health.ts",
        "src/store/session.ts",
        "src/theme/tokens.ts",
        "src/main.tsx",
        "src/App.tsx",
        "src/proxy.ts",
        "src/instrumentation.ts",
        "src/vite-env.d.ts",
        "src/lib/format.test.ts",
        "src/App.test.tsx",
        "src/app/(marketing)/about/page.tsx",
        "src/app/api/plans/route.ts",
        "src/app/sitemap.ts",
        "src/app/robots.ts",
        "src/app/icon.tsx",
        "src/app/(app)/forbidden.tsx",
        "web/src/components/Nav.tsx",
        "packages/@omninode/ui/src/components/Button.tsx",
        "packages/api-types/src/models/platform.ts",
        "vite.config.ts",
        "web/vitest.setup.ts",
        "eslint.config.js",
        "next-env.d.ts",
        ".storybook/main.ts",
        ".storybook/preview.tsx",
        "tests/e2e/login.spec.ts",
        "server/__tests__/auth.test.ts",
        "e2e/support/fixtures.ts",
        "docs/example.ts",
    ],
)
def test_typescript_shape_admitted(repo: Path, path: str) -> None:
    workspace_roots = frozenset(
        root
        for root in ("web", "packages/@omninode/ui", "packages/api-types")
        if path.startswith(f"{root}/")
    )
    for root in workspace_roots:
        _write(repo, f"{root}/package.json", "{}\n")
    _write(repo, path, "export const value = 1;\n")
    _git(repo, "add", "-A")
    assert issues(repo) == ()
    assert _is_canonical_location(path, workspace_roots)
    if workspace_roots:
        assert not _is_canonical_location(path)


@pytest.mark.parametrize(
    "path",
    [
        "src/lib/format.ts",
        "src/utils/x.ts",
        "src/services/plans.ts",
        "src/data-source/source.ts",
        "src/hooks/readState.ts",
        "src/hooks/nested/useX.ts",
        "src/app/(marketing)/_components/Hero.tsx",
        "src/app/_lib/queries.ts",
        ".storybook/addons/x.ts",
        "src/random.ts",
        "src/components/Legacy.js",
        "app/(marketing)/page.tsx",
        "lib/dashboard/source.ts",
        "server/index.ts",
        "shared/types/chart.ts",
        "scripts/build.ts",
        "proxy.ts",
        "eslint-rules/no-fetch.js",
        "src/omnibase_x/nodes/node_y/widget.ts",
        "plugins/onex/src/components/X.tsx",
        "src/src/components/X.tsx",
    ],
)
def test_typescript_shape_refused(repo: Path, path: str) -> None:
    _write(repo, path, "export const value = 1;\n")
    _git(repo, "add", "-A")
    findings = issues(repo)
    assert [(f.file_path.as_posix(), f.code) for f in findings] == [
        (path, "noncanonical-file")
    ]
    assert not _is_canonical_location(path)


@pytest.mark.parametrize("suffix", ["ts", "tsx", "js", "jsx", "mjs", "cjs"])
@pytest.mark.parametrize(
    "directory",
    ["test/", "nested/__tests__/", "e2e/", "docs/", ".storybook/"],
)
def test_typescript_shape_all_suffixes_in_shared_locations(
    suffix: str, directory: str
) -> None:
    assert _is_canonical_location(f"{directory}example.{suffix}")


@pytest.mark.parametrize("prefix", ["", "web/", "packages/ui/", "packages/@scope/ui/"])
@pytest.mark.parametrize(
    "relative",
    [
        "src/index.ts",
        "src/middleware.tsx",
        "src/app/nested/global-error.tsx",
        "src/app/layout.ts",
        "src/app/loading.tsx",
        "src/app/error.tsx",
        "src/app/not-found.tsx",
        "src/app/template.tsx",
        "src/app/default.tsx",
        "src/hooks/useX2.tsx",
        "src/lib/format.spec.tsx",
        "build.config.mjs",
        "test.setup.cjs",
        "next-env.d.ts",
        ".storybook/main.jsx",
    ],
)
def test_typescript_shape_workspace_locations(prefix: str, relative: str) -> None:
    workspace_roots = frozenset({prefix.rstrip("/")}) if prefix else frozenset()
    assert _is_canonical_location(prefix + relative, workspace_roots)
    if prefix:
        assert not _is_canonical_location(prefix + relative)


@pytest.mark.parametrize("suffix", ["ts", "tsx"])
@pytest.mark.parametrize(
    "name",
    [
        "page",
        "layout",
        "loading",
        "error",
        "not-found",
        "forbidden",
        "unauthorized",
        "route",
        "template",
        "default",
        "global-error",
        "global-not-found",
        "sitemap",
        "robots",
        "manifest",
        "icon",
        "apple-icon",
        "opengraph-image",
        "twitter-image",
    ],
)
def test_typescript_shape_next_route_names(name: str, suffix: str) -> None:
    assert _is_canonical_location(f"src/app/(app)/nested/{name}.{suffix}")


@pytest.mark.parametrize("suffix", ["ts", "tsx"])
@pytest.mark.parametrize(
    "name",
    [
        "index",
        "main",
        "App",
        "middleware",
        "proxy",
        "instrumentation",
        "instrumentation-client",
    ],
)
def test_typescript_shape_next_entry_names(name: str, suffix: str) -> None:
    assert _is_canonical_location(f"src/{name}.{suffix}")


@pytest.mark.parametrize(
    "path",
    [
        "src/hooks/usex.ts",
        "src/hooks/useX_extra.ts",
        "src/hooks/use.ts",
        "src/hooks/useX.test.js",
        "src/lib/x.d.ts",
        "src/app/page.js",
        "src/components/x.mjs",
        "web/docs/example.ts",
        "web/vite.config.tsx",
        "web/build.setup.jsx",
        "web/nested/vite.config.ts",
        "src/.storybook/main.ts",
        "web/nested/.storybook/main.ts",
        "packages/@scope/ui/nested/src/components/X.tsx",
        "web/.storybook/addons/x.ts",
        "packages/@scope/ui/.storybook/addons/x.ts",
    ],
)
def test_typescript_shape_boundaries(path: str) -> None:
    assert not _is_canonical_location(path, frozenset({"web", "packages/@scope/ui"}))


def test_shell_script_refused_in_every_location(repo: Path) -> None:
    paths = [
        "scripts/run.sh",
        "tests/run_tests.sh",
        "docs/example.sh",
        "src/pkg/nodes/node_x/run.sh",
        "src/components/run.sh",
        "tests/helper.bash",
        "tools/x.zsh",
        "tests/bin/run",
        "bin/tool",
    ]
    for path in paths:
        shebang = "#!/bin/sh" if path == "bin/tool" else "#!/usr/bin/env bash"
        _write(repo, path, f"{shebang}\necho hi\n")
    _write(repo, "tests/python_tool", "#!/usr/bin/env python3\nprint('hi')\n")
    _git(repo, "add", "-A")
    findings = issues(repo)
    assert {(f.file_path.as_posix(), f.code) for f in findings} == {
        (path, "noncanonical-file") for path in paths
    }
    for finding in findings:
        assert (
            "shell scripts have no canonical location in any repository"
            in finding.message
        )
        assert "OMN-21332" in finding.message
    for path in paths:
        if Path(path).suffix:
            assert not _is_canonical_location(path)


@pytest.mark.parametrize(
    ("path", "head_bytes", "expected"),
    [
        ("docs/example.sh", None, True),
        ("test/run.bash", b"", True),
        ("src/pkg/nodes/node_x/run.zsh", None, True),
        ("run", b"#!/bin/sh\necho hi\n", True),
        ("run", b"#!/usr/bin/env bash\necho hi\n", True),
        ("run", b"#!/bin/bash -e\necho hi\n", True),
        ("run", b"#! /bin/zsh -f\r\n", True),
        ("run", b"#!/usr/bin/dash\n", True),
        ("run", b"#!/bin/ksh\n", True),
        ("run", b"#!/usr/bin/env -S bash -e\n", True),
        ("run", b"#!/usr/bin/env python3\n", False),
        ("run", b"#!/usr/bin/bashful\n", False),
        ("run", b"#!/usr/bin/env python3 bash\n", False),
        ("run", b"text\n#!/bin/sh\n", False),
        ("run", b"#!\n", False),
        ("run", b"", False),
        ("run", None, False),
        ("example.py", b"#!/bin/bash\n", False),
    ],
)
def test_shell_script_refused_detection(
    path: str, head_bytes: bytes | None, expected: bool
) -> None:
    assert is_shell_script(path, head_bytes) is expected


def test_shell_script_refused_existing_baselined_only_shrinks(repo: Path) -> None:
    old, new = "tests/old.sh", "tests/new.sh"
    _write(repo, old, "#!/bin/sh\necho old\n")
    _write(repo, BASELINE, baseline_text([old]))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "baselined shell")
    assert issues(repo) == ()

    _write(repo, new, "#!/bin/sh\necho new\n")
    _git(repo, "add", "-A")
    findings = issues(repo)
    assert [(f.file_path.as_posix(), f.code) for f in findings] == [
        (new, "noncanonical-file")
    ]

    _write(repo, BASELINE, baseline_text([old, new]))
    _git(repo, "add", "-A")
    findings = issues(repo)
    assert [f.code for f in findings] == ["baseline-growth"]
    assert new in findings[0].message

    _write(repo, BASELINE, baseline_text([old]))
    (repo / new).unlink()
    (repo / old).unlink()
    _git(repo, "add", "-A")
    findings = issues(repo)
    assert [f.code for f in findings] == ["baseline-stale"]
    assert old in findings[0].message

    _write(repo, BASELINE, baseline_text([]))
    _git(repo, "add", "-A")
    assert issues(repo) == ()


def test_shell_script_refused_python_unchanged(repo: Path) -> None:
    for path in (
        "src/pkg/nodes/node_x/handler.py",
        "tests/test_x.py",
        "scripts/tool.py",
    ):
        _write(repo, path, "X = 1\n")
    _git(repo, "add", "-A")
    findings = issues(repo)
    assert [(f.file_path.as_posix(), f.code) for f in findings] == [
        ("scripts/tool.py", "noncanonical-file")
    ]
    assert findings[0].message == (
        "new code file outside a canonical location "
        "(src/<pkg>/{nodes,handlers,models,protocols,contracts,enums}/, "
        "src/<pkg>/validation/{checker_*,validator_*}.py, tests/, docs/). "
        "Build it as a contract + node + handler."
    )


def _commit_baselined_file(repo: Path, path: str = OLD_TOOL) -> None:
    _write(repo, path, BASE_TEXT)
    _write(repo, BASELINE, baseline_text([path]))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")


@pytest.mark.parametrize(
    "path",
    [
        OLD_TOOL,
        "src/pkg/runtime/a.py",
        "bin/tool",
        "tool.sh",
        ".github/scripts/a.py",
        "plugins/p/hooks/lib/h.py",
    ],
)
def test_baselined_file_growth_any_surface_refused(repo: Path, path: str) -> None:
    _commit_baselined_file(repo, path)
    _write(repo, path, BASE_TEXT + "d=4\n")
    _git(repo, "add", "-A")

    assert _rules(repo) == ["baselined-file-growth"]
    finding = issues(repo)[0]
    assert finding.file_path == Path(path)
    assert finding.message == (
        "code lines 3 -> 4; a baselined file only shrinks. "
        "Put the new behaviour in a contract + node + handler "
        "(rulings 2026-10-01T12:36:54Z, 2026-10-15T08:14:15Z)"
    )


@pytest.mark.parametrize("baseline_form", ["untouched", "swap"])
def test_baselined_file_growth_any_surface_rename_refused(
    repo: Path, baseline_form: str
) -> None:
    _commit_baselined_file(repo)
    new_path = "scripts/renamed_tool.py"
    _git(repo, "mv", OLD_TOOL, new_path)
    _write(repo, new_path, BASE_TEXT + "d=4\n")
    if baseline_form == "swap":
        _write(repo, BASELINE, baseline_text([new_path]))
    _git(repo, "add", "-A")

    assert _rules(repo) == ["baselined-file-growth"]
    finding = issues(repo)[0]
    assert finding.file_path == Path(new_path)
    assert "3 -> 4" in finding.message


@pytest.mark.parametrize(
    "head_text",
    [
        pytest.param("a=1\n", id="shrink"),
        pytest.param(BASE_TEXT.replace("b=2", "b=20"), id="equal-size-edit"),
        pytest.param(
            BASE_TEXT + "\n# more prose\n// more prose\n", id="comments-blanks"
        ),
    ],
)
def test_baselined_file_growth_any_surface_controls_accepted(
    repo: Path, head_text: str
) -> None:
    _commit_baselined_file(repo)
    _write(repo, OLD_TOOL, head_text)
    _git(repo, "add", "-A")
    assert _rules(repo) == []


def test_baselined_file_growth_any_surface_unbaselined_canonical_growth_accepted(
    repo: Path,
) -> None:
    canonical_path = "src/pkg/nodes/node_x/handler.py"
    _write(repo, canonical_path, BASE_TEXT)
    _commit_baselined_file(repo)
    _write(repo, canonical_path, BASE_TEXT + "d=4\n")
    _git(repo, "add", "-A")
    assert _rules(repo) == []
