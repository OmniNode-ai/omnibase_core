# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
_config = None


def get_config():
    global _config
    if _config is None:
        _config = object()
    return _config
