#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pre-commit wrapper for SPDX header validation.

Thin wrapper that reuses core logic from ``onex spdx validate`` without
Click overhead. Accepts file paths as arguments (pass_filenames mode).

See: onex spdx validate
"""

from __future__ import annotations

import sys

from omnibase_core.cli.cli_spdx import validate_files

if __name__ == "__main__":
    sys.exit(validate_files(sys.argv[1:]))
