# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Git effects of the dependency-pin check: release tag inventories and hook history (OMN-22360)."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from omnibase_core.models.dependency_pins.model_dependency_hook_history import (
    ModelDependencyHookHistory,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_request import (
    ModelDependencyPinFactsRequest,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_result import (
    ModelDependencyPinFactsResult,
)
from omnibase_core.models.dependency_pins.model_dependency_release_inventory import (
    ModelDependencyReleaseInventory,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time import (
    ModelPrecommitRevTime,
)
from omnibase_core.validation.checker_precommit_pin_parity import normalize_repo_url
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

__all__ = ["NodeDependencyPinsCheckEffect"]


class NodeDependencyPinsCheckEffect:
    """Own every git call of the check; a failed read is returned as an error, never raised."""

    @staticmethod
    def _git(args: list[str], timeout: int) -> tuple[int, str, str]:
        try:
            result = subprocess.run(
                ["git", *args],
                capture_output=True,
                text=True,
                check=False,
                env=scrub_git_location_env(),
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return 1, "", str(exc)
        return result.returncode, result.stdout, result.stderr.strip()

    def _inventory(
        self, request: ModelDependencyPinFactsRequest, repo: str
    ) -> ModelDependencyReleaseInventory:
        policy = request.policy
        url = policy.tag_inventory_url.format(org=request.github_org, repo=repo)
        code, out, err = self._git(
            ["ls-remote", "--tags", "--refs", url], request.git_timeout_seconds
        )
        if code != 0:
            reason = err.splitlines()[-1] if err else f"git ls-remote exit {code}"
            return ModelDependencyReleaseInventory(repo=repo, error=reason)
        pattern = re.compile(policy.release_tag_pattern)
        versions: list[str] = []
        for line in out.splitlines():
            ref = line.partition("\t")[2]
            match = pattern.match(ref.rpartition("/")[2] if ref else "")
            if match:
                versions.append(match.group("version"))
        return ModelDependencyReleaseInventory(repo=repo, versions=tuple(versions))

    def _history(
        self,
        request: ModelDependencyPinFactsRequest,
        url: str,
        revs: tuple[str, ...],
        clone: Path,
    ) -> ModelDependencyHookHistory:
        timeout = request.git_timeout_seconds
        times: list[ModelPrecommitRevTime] = []
        for rev in revs:
            code, out, _ = self._git(
                ["-C", str(clone), "show", "-s", "--format=%ct", f"{rev}^{{commit}}"],
                timeout,
            )
            if code == 0 and out.strip().isdigit():
                times.append(
                    ModelPrecommitRevTime(repo=url, rev=rev, committed_at=int(out))
                )
        code, out, err = self._git(
            [
                "-C",
                str(clone),
                "for-each-ref",
                "--format=%(refname:strip=2)%00%(*committerdate:unix)%00%(committerdate:unix)",
                "refs/tags",
            ],
            timeout,
        )
        if code != 0:
            return ModelDependencyHookHistory(
                url=url, rev_times=tuple(times), error=err or f"exit {code}"
            )
        pattern = re.compile(request.policy.release_tag_pattern)
        releases: list[int] = []
        for line in out.splitlines():
            name, _, rest = line.partition("\0")
            peeled, _, direct = rest.partition("\0")
            stamp = peeled or direct
            if pattern.match(name) and stamp.isdigit():
                releases.append(int(stamp))
        return ModelDependencyHookHistory(
            url=url, rev_times=tuple(times), release_times=tuple(sorted(releases))
        )

    def _hook_histories(
        self, request: ModelDependencyPinFactsRequest
    ) -> tuple[ModelDependencyHookHistory, ...]:
        histories: list[ModelDependencyHookHistory] = []
        for hook in request.policy.hook_repos:
            key = normalize_repo_url(hook.url)
            revs = tuple(
                sorted(
                    {
                        pin.rev
                        for pin in request.hook_pins
                        if normalize_repo_url(pin.repo) == key
                    }
                )
            )
            if not revs:
                continue
            if request.hook_history_dir is not None:
                histories.append(
                    self._history(
                        request, hook.url, revs, Path(request.hook_history_dir)
                    )
                )
                continue
            scratch = Path(tempfile.mkdtemp(prefix="onex-dependency-pins-"))
            try:
                code, _, err = self._git(
                    [
                        "clone",
                        "--bare",
                        "--quiet",
                        "--filter=tree:0",
                        hook.url,
                        str(scratch / "history"),
                    ],
                    request.git_timeout_seconds,
                )
                if code != 0:
                    histories.append(
                        ModelDependencyHookHistory(
                            url=hook.url, error=err or f"git clone exit {code}"
                        )
                    )
                    continue
                histories.append(
                    self._history(request, hook.url, revs, scratch / "history")
                )
            finally:
                shutil.rmtree(scratch, ignore_errors=True)
        return tuple(histories)

    def handle(
        self, request: ModelDependencyPinFactsRequest
    ) -> ModelDependencyPinFactsResult:
        """Read the requested inventories and hook histories."""
        return ModelDependencyPinFactsResult(
            inventories=tuple(self._inventory(request, repo) for repo in request.repos),
            hook_histories=self._hook_histories(request),
        )
