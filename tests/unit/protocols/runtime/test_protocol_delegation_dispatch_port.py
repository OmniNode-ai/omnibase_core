# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED-first tests for ``ProtocolDelegationDispatchPort`` (OMN-19838, Task A).

The protocol is the single definition that every delegation dispatch
implementation satisfies: ``async def dispatch(request) -> result``, typed with
``ModelDelegationDispatchRequest`` and ``ModelDelegationDispatchResult``.

It is generic in the request and result types, and the protocol module imports
no ``omnibase_core.models`` symbol. The protocols -> models edge set is frozen at
its ceiling by the OMN-14340 growth ratchet
(``scripts/ci/check_import_ratchet.py``), so the concrete pair is bound where
the port is used: ``ProtocolDelegationDispatchPort[ModelDelegationDispatchRequest,
ModelDelegationDispatchResult]``. This follows the structural precedent of
``ProtocolDeliveryContext`` (OMN-15665).

Signature conformance is a static fact. ``isinstance`` against a
runtime-checkable protocol only sees that a ``dispatch`` attribute exists, so the
negative case (the keyword-only signature every implementation has today) is
proven by running ``mypy --strict`` over a typed module, with a conforming module
as the positive control.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
import uuid
from pathlib import Path

import pytest
from mypy import api as mypy_api

from omnibase_core.models.delegation.wire import (
    ModelDelegationDispatchRequest,
    ModelDelegationDispatchResult,
)
from omnibase_core.protocols.runtime import ProtocolDelegationDispatchPort

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[4]

_PREAMBLE = """\
from __future__ import annotations

from uuid import UUID

from omnibase_core.models.delegation.wire import (
    ModelDelegationDispatchRequest,
    ModelDelegationDispatchResult,
)
from omnibase_core.protocols.runtime import ProtocolDelegationDispatchPort

TypeDispatchPort = ProtocolDelegationDispatchPort[
    ModelDelegationDispatchRequest, ModelDelegationDispatchResult
]
"""

_CONFORMING_MODULE = (
    _PREAMBLE
    + """

class ConformingPort:
    async def dispatch(
        self, request: ModelDelegationDispatchRequest
    ) -> ModelDelegationDispatchResult:
        return ModelDelegationDispatchResult(content=request.prompt)


port: TypeDispatchPort = ConformingPort()
"""
)

# The keyword-only signature both repos' implementations carry today.
_KEYWORD_ONLY_MODULE = (
    _PREAMBLE
    + """

class KeywordOnlyPort:
    async def dispatch(
        self,
        *,
        prompt: str,
        task_type: str,
        correlation_id: UUID,
        no_escalation: bool = False,
    ) -> dict[str, object]:
        return {"content": prompt}


port: TypeDispatchPort = KeywordOnlyPort()
"""
)


class _ConformingPort:
    async def dispatch(
        self, request: ModelDelegationDispatchRequest
    ) -> ModelDelegationDispatchResult:
        return ModelDelegationDispatchResult(content=request.prompt)


class _KeywordOnlyPort:
    async def dispatch(
        self,
        *,
        prompt: str,
        task_type: str,
        correlation_id: uuid.UUID,
        no_escalation: bool = False,
    ) -> dict[str, object]:
        return {"content": prompt}


class _NoDispatchPort:
    async def send(
        self, request: ModelDelegationDispatchRequest
    ) -> ModelDelegationDispatchResult:
        return ModelDelegationDispatchResult(content=request.prompt)


def _run_mypy_strict(tmp_path: Path, source: str) -> tuple[str, int]:
    module = tmp_path / "dispatch_port_conformance.py"
    module.write_text(textwrap.dedent(source), encoding="utf-8")
    stdout, stderr, exit_status = mypy_api.run(
        [
            "--strict",
            "--config-file",
            str(_REPO_ROOT / "pyproject.toml"),
            "--no-error-summary",
            "--show-error-codes",
            str(module),
        ]
    )
    return stdout + stderr, exit_status


@pytest.mark.timeout(300)  # a cold mypy cache analyses the model graph
def test_a_conforming_port_passes_mypy_strict(tmp_path: Path) -> None:
    """Positive control: the same harness reports a conforming port as clean."""
    output, exit_status = _run_mypy_strict(tmp_path, _CONFORMING_MODULE)

    assert exit_status == 0, output


@pytest.mark.timeout(300)  # a cold mypy cache analyses the model graph
def test_the_keyword_only_signature_fails_mypy_strict(tmp_path: Path) -> None:
    output, exit_status = _run_mypy_strict(tmp_path, _KEYWORD_ONLY_MODULE)

    assert exit_status == 1, output
    assert "[assignment]" in output, output
    assert "KeywordOnlyPort" in output, output


def test_a_conforming_port_is_an_instance_at_runtime() -> None:
    assert isinstance(_ConformingPort(), ProtocolDelegationDispatchPort)


def test_a_port_without_dispatch_is_not_an_instance_at_runtime() -> None:
    assert not isinstance(_NoDispatchPort(), ProtocolDelegationDispatchPort)


def test_isinstance_cannot_see_the_signature() -> None:
    """Pinned limitation: a runtime-checkable protocol checks attribute presence
    only, so the keyword-only port still passes ``isinstance``. Conformance
    checks must be static (the mypy cases above), never ``isinstance``."""
    assert isinstance(_KeywordOnlyPort(), ProtocolDelegationDispatchPort)


@pytest.mark.asyncio
async def test_a_conforming_port_round_trips_a_request() -> None:
    port: ProtocolDelegationDispatchPort[
        ModelDelegationDispatchRequest, ModelDelegationDispatchResult
    ] = _ConformingPort()
    request = ModelDelegationDispatchRequest(
        prompt="hello",
        task_type="research",
        correlation_id=uuid.UUID("00000000-0000-4000-8000-000000000003"),
        execution_timeout_seconds=240,
        terminal_delivery_margin_seconds=60,
    )

    result = await port.dispatch(request)

    assert result.content == "hello"


def test_protocol_module_does_not_import_models() -> None:
    """Ratchet guard: a protocols -> models edge would hard-fail the OMN-14340
    import ratchet, whose protocols -> models set is at its frozen ceiling."""
    from omnibase_core.protocols.runtime import protocol_delegation_dispatch_port

    tree = ast.parse(inspect.getsource(protocol_delegation_dispatch_port))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("omnibase_core.models"), node.module
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("omnibase_core.models"), alias.name
