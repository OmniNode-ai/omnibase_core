# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumDodCheckType — allowed check_type values for ModelDodEvidenceCheck. OMN-10241"""

from __future__ import annotations

from enum import StrEnum


class EnumDodCheckType(StrEnum):
    """Allowed mechanical check types for DoD evidence checks.

    Members
    -------
    TEST_EXISTS
        Assert that a test file exists at the given path.
    TEST_PASSES
        Assert that a test suite passes.
    FILE_EXISTS
        Assert that a file exists. Structurally weak — must be paired with
        a stronger check type per ModelDodEvidenceItem validation rules.
    GREP
        Assert that a pattern is present in a file. check_value must be a
        dict[str, str] with 'pattern' and 'path' keys.
    COMMAND
        Assert that a shell command exits 0.
    ENDPOINT
        Assert that an HTTP endpoint returns a successful response.
    BEHAVIOR_PROVEN
        Assert that observable behavior was proven via a live pipeline probe.
    RENDERED_OUTPUT
        Assert that UI output was verified to render correctly.
    RUNTIME_SHA_MATCH
        Assert that a deployed binary SHA matches the expected contract SHA.
    COMMAND_EXIT_0
        Assert that a shell command exits with code 0 (explicit exit-code variant).
    """

    TEST_EXISTS = "test_exists"
    TEST_PASSES = "test_passes"
    FILE_EXISTS = "file_exists"
    GREP = "grep"
    COMMAND = "command"
    ENDPOINT = "endpoint"
    BEHAVIOR_PROVEN = "behavior_proven"
    RENDERED_OUTPUT = "rendered_output"
    RUNTIME_SHA_MATCH = "runtime_sha_match"
    COMMAND_EXIT_0 = "command_exit_0"


__all__ = ["EnumDodCheckType"]
