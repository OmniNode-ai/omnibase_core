# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EFFECT boundary for the exposed identifier oracle's Git enumeration."""

from __future__ import annotations

import subprocess
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
    """List repository paths without reading source content or changing Git."""

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
