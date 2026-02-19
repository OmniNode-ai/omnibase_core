# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Module testing various import patterns."""

import os
import sys as system_module
from pathlib import Path
from typing import Any as AnyType

__all__ = ["os", "system_module", "Path", "AnyType", "my_function"]


def my_function() -> None:
    """A sample function."""
