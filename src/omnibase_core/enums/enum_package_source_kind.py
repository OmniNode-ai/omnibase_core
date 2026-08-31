# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Package-source-kind enum (OMN-17308).

Where an installed distribution's code actually came from. This is the field
that separates "I know which commit ran" from "I only know a version string",
and it exists because the second was repeatedly mistaken for the first: a Mac
venv pinning ``omnimarket 0.4.11`` produced a probe read as a statement about
the ``.201`` lane (OMN-16932/OMN-17295), and a lane container wore a fresh
``0.38.16`` registry label over week-old vendored content (OMN-17291).

The distinction is load-bearing rather than descriptive. :attr:`REGISTRY` is an
honest admission that no commit is recoverable; :attr:`UNKNOWN` is an honest
admission that even the source could not be determined. Neither may be silently
rendered as :attr:`VCS`, and a :attr:`VCS` entry that cannot name a commit is a
gate violation, not a pass.
"""

from enum import StrEnum, unique


@unique
class EnumPackageSourceKind(StrEnum):
    """How an installed distribution was sourced."""

    VCS = "vcs"
    """Installed from a git URL; PEP 610 ``direct_url.json`` records a
    ``vcs_info.commit_id``, so the exact content is nameable."""

    LOCAL_PATH = "local_path"
    """Installed from a local directory (``file://``, editable or workspace
    staging). The commit, when known, comes from a build-time provenance
    manifest rather than from the install metadata itself."""

    REGISTRY = "registry"
    """Installed from a package index (PyPI). Carries a version and NO commit —
    the OMN-14064 case. A registry install can never be commit-identified."""

    ABSENT = "absent"
    """The distribution is not installed in this interpreter at all. Recorded
    explicitly because "omnimarket is missing" is itself an identity fact and
    the exact regression OMN-14060/OMN-14531 kept re-discovering."""

    UNKNOWN = "unknown"
    """The distribution is installed but its source could not be determined
    (unreadable or malformed install metadata). Fails closed downstream."""

    SHADOWED = "shadowed"
    """The distribution's install metadata describes one tree, but the
    interpreter imports the module from a DIFFERENT one — a ``PYTHONPATH``
    entry, a ``.pth`` file, or a `sys.path` prepend winning over site-packages.

    The version and commit recorded by ``importlib.metadata`` then describe
    code that will not execute, which is the OMN-17306 lie in its purest form:
    every field is individually true and the block as a whole is false. This is
    the OMN-17190 stale-binary case one layer in — there the wrong ``onex``
    resolved on ``PATH``; here the right entry point imports the wrong library.

    Reproduced live 2026-08-31 while verifying OMN-17310: a stamp collected
    under ``PYTHONPATH=<core-worktree>/src`` reported
    ``omnibase_core=0.47.1@registry`` while executing 0.47.2 worktree source.
    Carries no commit — metadata's commit names the tree that LOST."""


__all__: list[str] = ["EnumPackageSourceKind"]
