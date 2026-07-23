# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDict for validator information.

Type definition for validator metadata used in validation CLI.

The ``func`` return type is intentionally widened to ``object`` (OMN-14339):
annotating the concrete ``ModelValidationResult[None]`` here created a
``types -> models`` import-layering back-edge forbidden by the
``core-foundation-no-upward`` contract in ``.importlinter`` (OMN-3210).
The sole consumer (``ServiceValidationSuite``) constructs the registry from
concrete validator functions and narrows the call result back to
``ModelValidationResult[None]`` with a single ``cast`` at the call site,
where importing models is legal.
"""

from collections.abc import Callable
from typing import TypedDict


class TypedDictValidatorInfo(TypedDict):
    """Type definition for validator information.

    Contains validator metadata including function, description, and arguments.
    """

    func: Callable[..., object]
    description: str
    args: list[str]


__all__ = ["TypedDictValidatorInfo"]
