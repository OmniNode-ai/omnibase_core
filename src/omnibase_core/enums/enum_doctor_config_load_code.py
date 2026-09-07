# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""How the doctor's declared configuration binding source resolved (OMN-17554)."""

from enum import StrEnum


class EnumDoctorConfigLoadCode(StrEnum):
    """Outcome of resolving ``~/.onex/config.yaml`` for the env-binding check.

    Internal to the loader and its tests. These values are never serialized
    into a ``ModelDoctorCheckResult``, either doctor renderer, or a log line —
    the public surface is a fixed, secret-safe message with category
    ``ENVIRONMENT``.
    """

    MISSING = "MISSING"
    EMPTY = "EMPTY"
    UNREADABLE = "UNREADABLE"
    INVALID_ENCODING = "INVALID_ENCODING"
    INVALID_YAML = "INVALID_YAML"
    INVALID_MODEL = "INVALID_MODEL"
    VALID = "VALID"
