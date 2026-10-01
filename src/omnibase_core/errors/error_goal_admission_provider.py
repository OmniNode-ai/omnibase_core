# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Error raised when a protected goal-admission provider cannot read trust data."""


class GoalAdmissionProviderError(RuntimeError):
    """A protected goal-admission lookup failed without exposing internals."""
