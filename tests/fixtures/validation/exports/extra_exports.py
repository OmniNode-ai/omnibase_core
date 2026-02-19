# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Module with extra items in __all__ that are not defined."""

__all__ = ["RealClass", "NonExistentClass", "ghost_function"]  # noqa: F822


class RealClass:
    """This class exists."""


# Note: NonExistentClass and ghost_function are NOT defined
# This should trigger an ERROR
