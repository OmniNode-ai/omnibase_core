# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Callable contracts shared by node-dispatch selection modules."""

from collections.abc import Callable

DispatcherCallable = Callable[..., object]
DlqTopicDeriver = Callable[[str | None, str], str | None]

__all__ = ["DispatcherCallable", "DlqTopicDeriver"]
