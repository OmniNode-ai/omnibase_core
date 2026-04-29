# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: env_silent_fallback gate clean cases."""

import os

# Allowed: fail-fast key access
HOST = os.environ["HOST"]

# Allowed: get with no default (returns None, caller must handle)
PORT = os.environ.get("PORT")

# Allowed: getenv with no default
TIMEOUT = os.getenv("TIMEOUT")

# Allowed: annotated bootstrap fallback suppressed
DB_URL = os.environ.get("DB_URL", "sqlite:///")  # substrate-allow: bootstrap-fallback
