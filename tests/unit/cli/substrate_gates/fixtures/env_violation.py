# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: env_silent_fallback gate violation cases."""

import os

# Variant 1: os.environ.get with default
HOST = os.environ.get("HOST", "localhost")

# Variant 2: os.getenv with default
PORT = os.getenv("PORT", "8080")

# Variant 3: os.environ.get(...) or default (BoolOp)
TIMEOUT = os.environ.get("TIMEOUT") or "30"
