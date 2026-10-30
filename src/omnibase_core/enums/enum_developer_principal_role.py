# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a declared broker principal is for (OMN-21622).

A ``developer.principal`` overlay row names who holds a principal. Its role
says whether the principal is a person's development machine or a machine the
deployment installs and runs itself. It is never a grant: every principal's
grants are derived from the declaration ``grants_source`` names. The lab
issuer's machine grant audit reads it to audit the deployment's own machines,
and only those.

The vocabulary is closed. A role is added in the same core change as the first
code that reads it.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDeveloperPrincipalRole(StrEnum):
    """The role a ``developer.principal`` overlay row gives its principal."""

    DEVELOPER = "developer"
    """A person's development machine. The default, so a row written before
    roles existed reads as it did. The machine grant audit never reads one."""

    MACHINE = "machine"
    """A machine the deployment installs and runs itself (a lab host, the
    operator's workstation). Read by the issuer's ``audit-grants --role
    machine``, which fails naming each one that lacks a grant of its profile."""


__all__ = ["EnumDeveloperPrincipalRole"]
