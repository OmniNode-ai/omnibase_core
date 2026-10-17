# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The typed client_verdict.action the adapter maps to a hook return (OMN-18531; relocated by OMN-21093)."""

from enum import StrEnum


class EnumClientVerdictAction(StrEnum):
    """Delegation: answer/refuse/proceed_native. Compaction: install/native. Additive: inject/none."""

    ANSWER = "answer"
    REFUSE = "refuse"
    PROCEED_NATIVE = "proceed_native"
    INSTALL = "install"
    NATIVE = "native"
    INJECT = "inject"
    NONE = "none"
