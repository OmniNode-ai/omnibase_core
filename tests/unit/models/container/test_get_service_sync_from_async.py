# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests: sync container helpers must not crash from an async context.

Handler ``__init__`` methods are inherently sync (Python has no ``async
__init__``) but run during async auto-wiring. They call
``container.get_service_sync(...)`` for DI resolution. Prior to OMN-9235 the
container used ``asyncio.run()`` internally, which raises ``RuntimeError:
asyncio.run() cannot be called from a running event loop`` in that scenario,
breaking all auto-wiring.

OMN-9241 Task 6 supersedes the inline ``_run_coro_sync`` helper (PR #853) with
the canonical ``omnibase_compat.concurrency.run_coro_sync`` import. These tests
lock in that contract:

1. ``get_service_sync`` run inside ``asyncio.run`` does not raise the
   forbidden ``RuntimeError``.
2. ``get_model_onex_container_sync`` (the "get_or_create_container_sync"
   referenced in the plan) run inside ``asyncio.run`` returns a container
   without raising.
3. ``model_onex_container.py`` imports ``run_coro_sync`` from
   ``omnibase_compat.concurrency`` rather than shipping its own inline copy —
   enforced via ``inspect.getsource`` grep so a future rebase cannot
   silently reintroduce a duplicate helper.
"""

from __future__ import annotations

import ast
import asyncio
import inspect

import pytest

from omnibase_core.models.container import model_onex_container
from omnibase_core.models.container.model_onex_container import (
    create_model_onex_container,
    get_model_onex_container_sync,
)

_FORBIDDEN_ASYNCIO_RUN_MESSAGE = (
    "asyncio.run() cannot be called from a running event loop"
)


@pytest.mark.unit
def test_get_service_sync_does_not_crash_inside_running_event_loop() -> None:
    """``get_service_sync`` must not raise ``RuntimeError`` from async context."""

    async def _scenario() -> None:
        container = await create_model_onex_container()
        # Construct a dummy protocol type; registration isn't required — the
        # point is to exercise the sync-from-async bridge, not service lookup.
        dummy_protocol = type("UnregisteredProtocol", (), {})
        try:
            container.get_service_sync(dummy_protocol)
        except RuntimeError as exc:
            if _FORBIDDEN_ASYNCIO_RUN_MESSAGE in str(exc):
                pytest.fail(
                    "get_service_sync raised the forbidden asyncio.run() "
                    "RuntimeError when called from within a running event "
                    "loop; it must dispatch to run_coro_sync instead."
                )
            # Any other RuntimeError (e.g. resolution failure) is acceptable —
            # this test guards only the async-context regression.
        except Exception:  # noqa: BLE001
            # Unrelated resolution failures (service not found, etc.) are
            # fine; this test asserts ONLY the async-context invariant.
            pass

    asyncio.run(_scenario())


@pytest.mark.unit
def test_get_model_onex_container_sync_does_not_crash_inside_running_loop() -> None:
    """``get_model_onex_container_sync`` must not raise inside a running loop.

    This is the "get_or_create_container_sync" call site referenced in the
    plan: the third ``asyncio.run(...)`` that PR #853 patched. A handler
    ``__init__`` running during async auto-wiring may call this helper if it
    needs the container itself (not a service).
    """

    async def _scenario() -> None:
        try:
            result = get_model_onex_container_sync()
        except RuntimeError as exc:
            if _FORBIDDEN_ASYNCIO_RUN_MESSAGE in str(exc):
                pytest.fail(
                    "get_model_onex_container_sync raised the forbidden "
                    "asyncio.run() RuntimeError when called from within a "
                    "running event loop; it must dispatch to run_coro_sync."
                )
            raise
        assert result is not None, (
            "get_model_onex_container_sync must return a container instance, "
            f"got {result!r}"
        )

    asyncio.run(_scenario())


def _collect_asyncio_run_lines_outside_except(source: str) -> list[int]:
    """Return line numbers of asyncio.run() calls NOT inside an except ImportError handler.

    The canonical import of run_coro_sync is wrapped in a try/except ImportError
    fallback (OMN-9241 SDK-boundary fix): the except branch contains an inline
    equivalent that must call asyncio.run() internally. That single allowed
    occurrence is exempted here; any asyncio.run() outside that block is a bug.
    """
    tree = ast.parse(source)

    # Collect line ranges covered by `except ImportError:` handlers.
    except_ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            if handler.type is None:
                continue
            names = [handler.type.id] if isinstance(handler.type, ast.Name) else []
            if "ImportError" in names and handler.body:
                start = handler.lineno
                end = max(
                    getattr(n, "lineno", start)
                    for n in ast.walk(ast.Module(body=handler.body, type_ignores=[]))
                )
                except_ranges.append((start, end))

    def in_except_import_error(lineno: int) -> bool:
        return any(start <= lineno <= end for start, end in except_ranges)

    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "run"
            and isinstance(func.value, ast.Name)
            and func.value.id == "asyncio"
            and not in_except_import_error(node.lineno)
        ):
            violations.append(node.lineno)
    return violations


@pytest.mark.unit
def test_container_delegates_to_compat_run_coro_sync() -> None:
    """Source must use ``omnibase_compat.concurrency.run_coro_sync``, not an inline copy.

    This lock-in prevents a future rebase from silently reintroducing the
    inline ``_run_coro_sync`` helper (as existed in PR #853) — which would
    defeat the purpose of extracting the helper into ``omnibase_compat``.

    omnibase-compat is an optional dep (SDK boundary rule). The import is
    wrapped in try/except ImportError with an inline fallback that calls
    asyncio.run() internally — that one location is exempted by the AST check.
    """
    source = inspect.getsource(model_onex_container)

    # Contract-first: the canonical try-import pattern is present.
    assert "from omnibase_compat.concurrency import run_coro_sync" in source, (
        "model_onex_container.py must attempt to import run_coro_sync from "
        "omnibase_compat.concurrency (OMN-9237). The inline _run_coro_sync "
        "helper from PR #853 is superseded and should be removed."
    )

    # Explicitly assert no duplicate private inline helper definition remains.
    assert "def _run_coro_sync" not in source, (
        "Inline _run_coro_sync helper must be removed in favor of the compat "
        "shim import. Found a local def _run_coro_sync in "
        "model_onex_container.py."
    )

    # All three production call sites must delegate to run_coro_sync, not
    # asyncio.run() directly. asyncio.run() inside an except ImportError fallback
    # is explicitly allowed (see OMN-9241 SDK-boundary fix).
    asyncio_run_calls = _collect_asyncio_run_lines_outside_except(source)
    assert not asyncio_run_calls, (
        "model_onex_container.py must not call asyncio.run() directly outside "
        "an except ImportError fallback — all three sync-from-async call sites "
        "should delegate to run_coro_sync(...). "
        f"Lingering calls at line(s): {asyncio_run_calls}"
    )
