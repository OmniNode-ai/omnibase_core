# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EFFECT boundary for version-file reads and read-only Git fact collection."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.release_identity_check.model_release_identity_check_input import (
    ModelReleaseIdentityCheckInput,
)
from omnibase_core.models.nodes.release_identity_check.model_release_identity_gather_input import (
    ModelReleaseIdentityGatherInput,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.nodes.node_release_identity_check_compute.release_identity_rules import (
    latest_published_version,
    version_error,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)


class NodeReleaseIdentityGatherEffect:
    """Gather one checkout's facts without consulting or importing infra."""

    def handle(
        self, request: ModelReleaseIdentityGatherInput
    ) -> ModelReleaseIdentityCheckInput:
        """Read the declared version before collecting its tree's Git facts."""
        root = Path(request.repo_root).resolve()
        path = str(root / "pyproject.toml")
        try:
            gathered = NodeSourceFileGatherEffect().handle(
                ModelSourceFileGatherInput(
                    root=str(root),
                    explicit_paths=[path],
                    include_patterns=["**/pyproject.toml"],
                )
            )
        except UnicodeDecodeError as exc:
            return ModelReleaseIdentityCheckInput(
                pyproject_path=path,
                runtime_errors=(f"ERROR: {exc}",),
                runtime_exit_code=2,
            )
        files = tuple(
            ModelSourceFile(path=file.path, source=file.source)
            for file in gathered.files
        )
        if not files:
            errors = tuple(
                f"ERROR: {skipped.path}: {skipped.reason}"
                for skipped in gathered.skipped
                if skipped.reason.startswith(
                    ("read error:", "error checking file size:")
                )
            )
            if not errors:
                errors = (
                    f"ERROR: zero files scanned under {root}: a full-tree run that scans nothing is ERROR, never PASS",
                )
            return ModelReleaseIdentityCheckInput(
                pyproject_path=path, runtime_errors=errors
            )
        try:
            document = tomllib.loads(files[0].source)
        except tomllib.TOMLDecodeError as exc:
            return ModelReleaseIdentityCheckInput(
                pyproject_path=path,
                files=files,
                runtime_errors=(f"ERROR: {exc}",),
                runtime_exit_code=2,
            )
        project: object = document.get("project", {})
        if not isinstance(project, dict):
            return ModelReleaseIdentityCheckInput(
                pyproject_path=path,
                files=files,
                runtime_errors=(
                    f"ERROR: '{type(project).__name__}' object has no attribute 'get'",
                ),
                runtime_exit_code=1,
            )
        raw: object = project.get("version")
        version_raw = str(raw) if raw else None
        facts = ModelReleaseIdentityCheckInput(
            pyproject_version_raw=version_raw,
            pyproject_version_repr=repr(raw),
            pyproject_path=path,
            files=files,
        )
        if version_error(facts) is not None:
            return facts
        try:
            shallow = (
                self._stdout(root, "rev-parse", "--is-shallow-repository") == "true"
            )
            if shallow:
                tags = self._stdout(root, "tag", "--list")
            else:
                tags = self._stdout(root, "tag", "--merged", "HEAD") or self._stdout(
                    root, "tag", "--list"
                )
            published_tags = tuple(tags.splitlines())
            changed = (
                self._changed_paths(root, request)
                if latest_published_version(published_tags) is not None
                else None
            )
            return ModelReleaseIdentityCheckInput(
                pyproject_version_raw=version_raw,
                pyproject_version_repr=repr(raw),
                pyproject_path=path,
                files=files,
                published_tags=published_tags,
                changed_files=changed,
            )
        except OSError as exc:
            return ModelReleaseIdentityCheckInput(
                pyproject_version_raw=version_raw,
                pyproject_path=path,
                files=files,
                runtime_errors=(f"ERROR: {exc}",),
                runtime_exit_code=1,
            )

    @staticmethod
    def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        """Use core's inherited Git context for read-only repository commands."""
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

    def _stdout(self, root: Path, *args: str) -> str:
        """Preserve core's stdout-only Git reads, including failed commands."""
        return self._git(root, *args).stdout.strip()

    def _changed_paths(
        self, root: Path, request: ModelReleaseIdentityGatherInput
    ) -> tuple[str, ...] | None:
        if request.explicit_paths:
            return request.explicit_paths
        if request.base is None:
            return None
        if not self._stdout(
            root, "rev-parse", "--verify", "--quiet", f"{request.base}^{{commit}}"
        ):
            return None
        if not self._stdout(root, "merge-base", request.base, "HEAD"):
            return None
        diffs = (
            self._stdout(root, "diff", "--name-only", f"{request.base}...HEAD"),
            self._stdout(root, "diff", "--cached", "--name-only"),
            self._stdout(root, "diff", "--name-only"),
        )
        return tuple(
            path for diff in diffs for path in diff.splitlines() if path.strip()
        )
