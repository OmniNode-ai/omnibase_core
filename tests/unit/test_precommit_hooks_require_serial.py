# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Enforce serial filename hooks to avoid interpreter fan-out (OMN-20241).

pre-commit 4.6.1 partitions filenames into max(4, ceil(N / cpu_count)) files
per process and runs up to cpu_count processes concurrently. Each Python
process pays the full omnibase_core import cost. Our validators already
aggregate a whole file list, so require_serial hands that list to one process.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml


def find_non_serial_hooks(config: object, *, manifest: bool = False) -> list[str]:
    """Return offending ids in a shared manifest or a consumer configuration."""
    if manifest:
        hooks = cast("list[dict[str, object]]", config)
    else:
        repositories = cast("dict[str, list[dict[str, object]]]", config)["repos"]
        hooks = []
        for repository in repositories:
            repo = repository["repo"]
            if repo == "local" or (
                isinstance(repo, str)
                and repo.startswith("https://github.com/OmniNode-ai/")
            ):
                hooks.extend(cast("list[dict[str, object]]", repository["hooks"]))

    return [
        cast("str", hook["id"])
        for hook in hooks
        if hook.get("pass_filenames") is not False
        and (manifest or hook.get("language") != "fail")
        and hook.get("require_serial") is not True
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("filename", "manifest"),
    [(".pre-commit-hooks.yaml", True), (".pre-commit-config.yaml", False)],
)
def test_filename_hooks_require_serial(filename: str, manifest: bool) -> None:
    root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load((root / filename).read_text(encoding="utf-8"))
    offenders = find_non_serial_hooks(config, manifest=manifest)
    assert not offenders, f"{filename}: hooks missing require_serial: true: {offenders}"


@pytest.mark.unit
def test_local_hook_missing_require_serial_is_reported() -> None:
    config = {"repos": [{"repo": "local", "hooks": [{"id": "missing-serial"}]}]}
    assert find_non_serial_hooks(config) == ["missing-serial"]


@pytest.mark.unit
def test_hook_without_filenames_is_exempt() -> None:
    hook = {"id": "whole-repo", "pass_filenames": False}
    config = {"repos": [{"repo": "local", "hooks": [hook]}]}
    assert find_non_serial_hooks(config) == []
    assert find_non_serial_hooks([hook], manifest=True) == []


@pytest.mark.unit
def test_third_party_hook_is_exempt() -> None:
    config = {
        "repos": [
            {
                "repo": "https://github.com/pre-commit/pre-commit-hooks",
                "hooks": [{"id": "end-of-file-fixer"}],
            }
        ]
    }
    assert find_non_serial_hooks(config) == []


@pytest.mark.unit
def test_omninode_remote_override_is_required() -> None:
    config = {
        "repos": [
            {
                "repo": "https://github.com/OmniNode-ai/omnibase_core",
                "hooks": [{"id": "missing-override"}],
            }
        ]
    }
    assert find_non_serial_hooks(config) == ["missing-override"]


@pytest.mark.unit
def test_fail_language_hook_is_exempt_only_in_consumer_config() -> None:
    hook = {"id": "blocked-file", "language": "fail"}
    config = {"repos": [{"repo": "local", "hooks": [hook]}]}
    assert find_non_serial_hooks(config) == []
    assert find_non_serial_hooks([hook], manifest=True) == ["blocked-file"]


@pytest.mark.unit
@pytest.mark.parametrize("serial", [False, "true", 1, None])
def test_require_serial_must_be_boolean_true(serial: object) -> None:
    config = {
        "repos": [
            {
                "repo": "local",
                "hooks": [{"id": "not-true", "require_serial": serial}],
            }
        ]
    }
    assert find_non_serial_hooks(config) == ["not-true"]
