# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
def build(mod, name):
    return getattr(mod, name)()
