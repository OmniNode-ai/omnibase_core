# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EFFECT boundary for Git enumeration and selected snapshot blob reads."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_input import (
    ModelGitFileListingInput,
)
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_output import (
    ModelGitFileListingOutput,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env


class NodeGitFileListingEffect:
    """List repository paths and read immutable Git snapshots without changing Git."""

    def resolve_root(self, directory: Path) -> Path:
        """Resolve a checkout root, retaining the CWD fallback outside Git."""
        try:
            result = subprocess.run(
                ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=False,
                env=scrub_git_location_env(),
            )
        except OSError:
            return directory.resolve()
        return (
            Path(result.stdout.strip()).resolve()
            if result.returncode == 0
            else directory.resolve()
        )

    def handle(self, request: ModelGitFileListingInput) -> ModelGitFileListingOutput:
        """Use the oracle's rev-parse probe and fallback-to-all behavior."""
        if request.snapshot is not None:
            return self._snapshot(request)
        prefix = ["git", "-C", str(request.root)]
        env = scrub_git_location_env()
        fallback = False
        if request.scope == "diff":
            probe = subprocess.run(
                [*prefix, "rev-parse", "--verify", request.base_ref],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            fallback = probe.returncode != 0
        command = (
            ["diff", "--name-only", "-z", f"{request.base_ref}...HEAD"]
            if request.scope == "diff" and not fallback
            else ["ls-files", "-coz", "--exclude-standard"]
        )
        try:
            output = subprocess.run(
                [*prefix, *command], capture_output=True, text=True, check=True, env=env
            ).stdout
        except subprocess.CalledProcessError as exc:
            raise ModelOnexError(
                message=str(exc), error_code=EnumCoreErrorCode.OPERATION_FAILED
            ) from exc
        return ModelGitFileListingOutput(
            paths=[name for name in output.split("\0") if name],
            fell_back_to_all=fallback,
        )

    def _run(
        self, root: Path, *args: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        """Run snapshot plumbing with a scrubbed location and bounded runtime."""
        try:
            return subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True,
                check=check,
                timeout=30,
                env=scrub_git_location_env(),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ModelOnexError(
                message=str(exc), error_code=EnumCoreErrorCode.OPERATION_FAILED
            ) from exc

    def _snapshot(self, request: ModelGitFileListingInput) -> ModelGitFileListingOutput:
        """Enumerate stage-zero index entries or a pinned commit, skipping gitlinks."""
        # A missing revision is evidence, but a non-repository must fail closed.
        self._run(request.root, "rev-parse", "--show-toplevel")
        revision_exists: bool | None = None
        if request.snapshot == "revision":
            probe = self._run(
                request.root,
                "rev-parse",
                "--verify",
                "--quiet",
                "--end-of-options",
                f"{request.base_ref}^{{commit}}",
                check=False,
            )
            revision_exists = probe.returncode == 0
            if not revision_exists:
                return ModelGitFileListingOutput(
                    revision_exists=False,
                    blobs=dict.fromkeys(request.blob_paths),
                )
            raw = self._run(
                request.root, "ls-tree", "-r", "-z", probe.stdout.decode().strip()
            ).stdout
        else:
            raw = self._run(request.root, "ls-files", "--stage", "-z").stdout
        objects: dict[str, str] = {}
        has_unmerged = False
        for entry in raw.split(b"\0"):
            if not entry:
                continue
            metadata, path = entry.split(b"\t", 1)
            if request.snapshot == "index":
                mode, object_id, stage = metadata.split()
                if stage != b"0":
                    has_unmerged = True
                    continue
            else:
                mode, _object_type, object_id = metadata.split()
            if mode != b"160000":
                objects[path.decode("utf-8", errors="surrogateescape")] = (
                    object_id.decode("ascii")
                )
        return ModelGitFileListingOutput(
            paths=list(objects),
            revision_exists=revision_exists,
            has_unmerged_entries=has_unmerged,
            blobs=self._read_blobs(request.root, objects, request.blob_paths),
        )

    def _read_blobs(
        self, root: Path, objects: dict[str, str], paths: list[str]
    ) -> dict[str, bytes | None]:
        """Batch selected object IDs, preserving arbitrary filenames and blob bytes."""
        blobs: dict[str, bytes | None] = dict.fromkeys(paths)
        wanted = [path for path in blobs if path in objects]
        if not wanted:
            return blobs
        # Temporary streams avoid the established large stdin-pipe stall on macOS.
        try:
            with (
                tempfile.TemporaryFile() as requests,
                tempfile.TemporaryFile() as responses,
            ):
                requests.write(
                    "".join(f"{objects[path]}\n" for path in wanted).encode()
                )
                requests.seek(0)
                subprocess.run(
                    ["git", "-C", str(root), "cat-file", "--batch"],
                    stdin=requests,
                    stdout=responses,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=30,
                    env=scrub_git_location_env(),
                )
                responses.seek(0)
                for path in wanted:
                    header = responses.readline().split()
                    if len(header) != 3 or header[1] != b"blob":
                        raise ModelOnexError(
                            message=f"could not read snapshot blob: {path}",
                            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                        )
                    size = int(header[2])
                    blob = responses.read(size)
                    if len(blob) != size or responses.read(1) != b"\n":
                        raise ModelOnexError(
                            message=f"truncated snapshot blob: {path}",
                            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                        )
                    blobs[path] = blob
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise ModelOnexError(
                message=str(exc), error_code=EnumCoreErrorCode.OPERATION_FAILED
            ) from exc
        return blobs
