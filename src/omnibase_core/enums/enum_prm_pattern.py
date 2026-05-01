# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumPrmPattern(StrEnum):
    REPETITION_LOOP = "repetition_loop"
    PING_PONG = "ping_pong"
    EXPANSION_DRIFT = "expansion_drift"
    STUCK_ON_TEST = "stuck_on_test"
    CONTEXT_THRASH = "context_thrash"
