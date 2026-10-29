# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import re

PATTERN = re.compile(r"x")


def handle(text: str) -> bool:
    return PATTERN.search(text) is not None
