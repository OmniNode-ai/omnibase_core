# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Base model configuration module for events.

A simple re-export of Pydantic's BaseModel
for consistent imports across the events package.
"""

from pydantic import BaseModel

__all__ = ["BaseModel"]
