# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Factory protocol of overlay-bound handler dependencies (OMN-21595)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolDependencyFactory(Protocol):
    """Builds one dependency from the configuration its overlay binding carries.

    The factory reads nothing but ``config``: no environment variable, no file, no
    module-level constant. The overlay names the factory and supplies the config, so
    swapping a local implementation for a hosted one is an overlay change.
    """

    def __call__(self, config: Mapping[str, str]) -> object:
        """Return the dependency built from the binding's configuration."""
        ...
