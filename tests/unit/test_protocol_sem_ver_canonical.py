# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Regression tests for OMN-14624: single canonical ``ProtocolSemVer`` object and
no order-dependent circular import.

Background
----------
Two ``ProtocolSemVer`` definitions used to exist in ``omnibase_core``:

* ``types/type_semver.py`` — the richer structural surface (major/minor/patch,
  prerelease, build, ``to_string()``, ``is_prerelease()``).
* ``protocols/base/protocol_sem_ver.py`` — a narrower duplicate
  (major/minor/patch + ``__str__``).

OMN-14624 collapses these to ONE canonical object living in
``types.type_semver`` and makes ``protocols.base.protocol_sem_ver`` a one-line
re-export. That re-export creates a ``protocols -> types`` edge. Because
``types/__init__.py`` used to *eagerly* import ``type_constraints`` and
``type_core`` (both of which import UP into ``omnibase_core.protocols``), the
re-export closed a ``protocols -> types -> protocols`` loop that raised an
order-dependent ``ImportError`` whenever ``protocols`` was imported before
``types`` (``cannot import name 'ProtocolConfigurable' from partially
initialized module 'omnibase_core.protocols'``).

The fix routes ``type_constraints`` / ``type_core`` through the lazy
``__getattr__`` loader in ``types/__init__.py`` so the package no longer imports
protocols at module-init time.

These tests are the independent oracle. The both-order subprocess tests FAIL on
the re-export-only (unfixed) state and PASS once the eager back-edge is removed.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

# Each script imports ProtocolSemVer via all three public paths and asserts they
# are one and the same object (criterion D identity). A fresh interpreter is used
# so module import ORDER is exactly what the script dictates — the whole point of
# the regression. All lines are top-level (zero indent) so the script is valid.
_IDENTITY_ASSERTIONS = (
    "from omnibase_core.protocols.base import ProtocolSemVer as p_base\n"
    "from omnibase_core.protocols import ProtocolSemVer as p_pkg\n"
    "from omnibase_core.types.type_semver import ProtocolSemVer as t_canon\n"
    "assert p_base is t_canon, 'protocols.base.ProtocolSemVer is not canonical'\n"
    "assert p_pkg is t_canon, 'protocols.ProtocolSemVer is not canonical'\n"
    "print('IMPORT_ORDER_OK')\n"
)

_PROTOCOLS_FIRST = "import omnibase_core.protocols\nimport omnibase_core.types\n"
_TYPES_FIRST = "import omnibase_core.types\nimport omnibase_core.protocols\n"


def _run_fresh_interpreter(body: str) -> subprocess.CompletedProcess[str]:
    """Run ``body`` in a fresh interpreter (no pytest/conftest pollution).

    Uses ``sys.executable`` and inherits the environment so the child resolves
    the same ``omnibase_core`` source tree as the parent test process.
    """
    script = body + _IDENTITY_ASSERTIONS
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.unit
def test_protocols_first_import_order() -> None:
    """Importing ``protocols`` BEFORE ``types`` must not deadlock the cycle."""
    result = _run_fresh_interpreter(_PROTOCOLS_FIRST)
    assert result.returncode == 0, (
        "protocols-first import failed (circular import regression):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "IMPORT_ORDER_OK" in result.stdout


@pytest.mark.unit
def test_types_first_import_order() -> None:
    """Importing ``types`` BEFORE ``protocols`` must also import cleanly."""
    result = _run_fresh_interpreter(_TYPES_FIRST)
    assert result.returncode == 0, (
        "types-first import failed:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "IMPORT_ORDER_OK" in result.stdout


@pytest.mark.unit
def test_single_canonical_protocol_identity() -> None:
    """All three public import paths resolve to one canonical object (criterion D)."""
    from omnibase_core.protocols import ProtocolSemVer as ProtocolSemVerFromPkg
    from omnibase_core.protocols.base import ProtocolSemVer as ProtocolSemVerFromBase
    from omnibase_core.protocols.base.protocol_sem_ver import (
        ProtocolSemVer as ProtocolSemVerFromModule,
    )
    from omnibase_core.types.type_semver import (
        ProtocolSemVer as ProtocolSemVerCanonical,
    )

    assert ProtocolSemVerFromBase is ProtocolSemVerCanonical
    assert ProtocolSemVerFromPkg is ProtocolSemVerCanonical
    assert ProtocolSemVerFromModule is ProtocolSemVerCanonical


@pytest.mark.unit
def test_canonical_protocol_is_runtime_checkable() -> None:
    """The canonical protocol is ``@runtime_checkable`` and enforces the full surface.

    ``ModelSemVer`` (the only concrete implementation) satisfies it; a bare object
    and a narrow-only duck (major/minor/patch but no ``to_string``/``is_prerelease``)
    do NOT — proving the isinstance check tests the real richer surface rather than
    passing vacuously.
    """
    from omnibase_core.models.primitives.model_semver import ModelSemVer
    from omnibase_core.types.type_semver import ProtocolSemVer

    version = ModelSemVer(major=1, minor=2, patch=3, prerelease=("alpha", 1))
    assert isinstance(version, ProtocolSemVer)

    # EXISTS-but-WRONG: object missing the method surface must NOT match.
    class _NarrowOnly:
        major = 1
        minor = 2
        patch = 3

    assert not isinstance(_NarrowOnly(), ProtocolSemVer)
    assert not isinstance(object(), ProtocolSemVer)
