# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Kinds of direct model call site the OMN-20295 gate refuses."""

from __future__ import annotations

from enum import StrEnum


class EnumDirectModelCallKind(StrEnum):
    """What makes a site a direct model call."""

    SDK_IMPORT = "sdk_import"
    """A model provider SDK is imported."""

    CLI_EXEC = "cli_exec"
    """A model CLI (crush, codex, claude -p, llama-cli, ...) is executed."""

    HTTP = "http"
    """An HTTP request is built to a model endpoint, a provider host or a base_url."""

    CALL_VIA = "call_via"
    """A function calls a model-calling function in another file."""

    EXEC_VIA = "exec_via"
    """A file executes another file of the repository that calls a model."""


__all__ = ["EnumDirectModelCallKind"]
