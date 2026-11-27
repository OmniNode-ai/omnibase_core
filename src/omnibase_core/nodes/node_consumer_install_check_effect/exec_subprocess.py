# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The command-executing handler of the consumer install check (OMN-26670)."""

from __future__ import annotations

import subprocess

from omnibase_core.models.nodes.consumer_install_check.model_command_outcome import (
    ModelCommandOutcome,
)
from omnibase_core.models.nodes.consumer_install_check.model_command_request import (
    ModelCommandRequest,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

__all__ = ["HandlerSubprocessExec"]


class HandlerSubprocessExec:
    """Runs a command with the git location variables scrubbed, a hard timeout and no shell."""

    def handle(self, request: ModelCommandRequest) -> ModelCommandOutcome:
        """Run the command; a timeout is an outcome, not an exception."""
        env = scrub_git_location_env()
        env["GIT_TERMINAL_PROMPT"] = "0"
        try:
            done = subprocess.run(
                list(request.argv),
                cwd=request.cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as expired:
            partial = expired.stdout if isinstance(expired.stdout, str) else ""
            return ModelCommandOutcome(returncode=-1, output=partial, timed_out=True)
        return ModelCommandOutcome(
            returncode=done.returncode, output=done.stdout + done.stderr
        )
