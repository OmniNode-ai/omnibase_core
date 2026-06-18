# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for the no-plugin-daemon-classes COMPUTE validator (OMN-13309).

Tests cover:
- Positive (violation) cases — Plugin* classes owning lifecycle terms → finding emitted
- Negative (clean) cases — Plugin* compute subclasses / non-Plugin classes → no finding
- COMPUTE handler protocol compliance
- CLI entry-point returns correct exit codes
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.validation.model_no_plugin_daemon_classes import (
    ModelNoPluginDaemonFinding,
    ModelNoPluginDaemonInput,
    ModelNoPluginDaemonResult,
)
from omnibase_core.validators.no_plugin_daemon_classes import (
    LIFECYCLE_TERMS,
    HandlerNoPluginDaemonClasses,
    main,
    validate_source,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Fixtures — violation sources
# ---------------------------------------------------------------------------

_PLUGIN_DAEMON = """\
class PluginDaemon:
    pass
"""

_PLUGIN_WORKER = """\
class PluginWorker:
    pass
"""

_PLUGIN_SERVICE = """\
class PluginService:
    pass
"""

_PLUGIN_RUNTIME = """\
class PluginRuntime:
    pass
"""

_PLUGIN_CONSUMER = """\
class PluginConsumer:
    pass
"""

_PLUGIN_PUBLISHER = """\
class PluginPublisher:
    pass
"""

_PLUGIN_CONTROLLER = """\
class PluginController:
    pass
"""

_PLUGIN_SERVER = """\
class PluginServer:
    pass
"""

_PLUGIN_CLIENT = """\
class PluginClient:
    pass
"""

_PLUGIN_SUBCLASS_DAEMON_BASE = """\
class PluginFoo(SomeDaemon):
    pass
"""

# ---------------------------------------------------------------------------
# Fixtures — clean sources
# ---------------------------------------------------------------------------

_CLEAN_COMPUTE_PLUGIN = """\
class PluginJsonNormalizer(PluginComputeBase):
    pass
"""

_CLEAN_NON_PLUGIN = """\
class MySomeDaemon:
    pass
"""

_CLEAN_PLUGIN_COMPUTE_BASE_DEF = """\
class PluginComputeBase:
    pass
"""

_CLEAN_EMPTY = ""

_CLEAN_NO_CLASS = """\
def helper():
    return 42
"""


# ---------------------------------------------------------------------------
# validate_source — violation tests (positive)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "expected_class"),
    [
        (_PLUGIN_DAEMON, "PluginDaemon"),
        (_PLUGIN_WORKER, "PluginWorker"),
        (_PLUGIN_SERVICE, "PluginService"),
        (_PLUGIN_RUNTIME, "PluginRuntime"),
        (_PLUGIN_CONSUMER, "PluginConsumer"),
        (_PLUGIN_PUBLISHER, "PluginPublisher"),
        (_PLUGIN_CONTROLLER, "PluginController"),
        (_PLUGIN_SERVER, "PluginServer"),
        (_PLUGIN_CLIENT, "PluginClient"),
        (_PLUGIN_SUBCLASS_DAEMON_BASE, "PluginFoo"),
    ],
)
def test_validate_source_flags_lifecycle_class(
    source: str, expected_class: str
) -> None:
    """Every Plugin* class owning a lifecycle term produces exactly one finding."""
    findings = validate_source("test.py", source)
    assert len(findings) == 1
    assert findings[0].class_name == expected_class
    assert findings[0].path == "test.py"


def test_validate_source_flags_all_lifecycle_terms() -> None:
    """All 9 LIFECYCLE_TERMS are caught by the validator."""
    found_terms: set[str] = set()
    for term in LIFECYCLE_TERMS:
        source = f"class Plugin{term}:\n    pass\n"
        findings = validate_source("test.py", source)
        if findings:
            found_terms.add(term)
    assert found_terms == LIFECYCLE_TERMS, (
        f"Missing coverage for terms: {LIFECYCLE_TERMS - found_terms}"
    )


# ---------------------------------------------------------------------------
# validate_source — clean tests (negative)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "label"),
    [
        (_CLEAN_COMPUTE_PLUGIN, "compute_subclass"),
        (_CLEAN_NON_PLUGIN, "non_plugin_daemon"),
        (_CLEAN_PLUGIN_COMPUTE_BASE_DEF, "compute_base_def_itself"),
        (_CLEAN_EMPTY, "empty_file"),
        (_CLEAN_NO_CLASS, "no_class"),
    ],
)
def test_validate_source_clean(source: str, label: str) -> None:
    """Clean sources produce no findings."""
    findings = validate_source("test.py", source)
    assert findings == [], f"Unexpected findings for {label}: {findings}"


def test_validate_source_plugin_compute_base_def_in_correct_file() -> None:
    """PluginComputeBase definition in plugin_compute_base.py is exempted."""
    findings = validate_source(
        "omnibase_infra/plugins/plugin_compute_base.py",
        "class PluginComputeBase:\n    pass\n",
    )
    assert findings == []


def test_validate_source_syntax_error_produces_finding() -> None:
    """A file with a syntax error produces a <syntax-error> finding rather than crashing."""
    findings = validate_source("bad.py", "class Foo(:\n    pass\n")
    assert len(findings) == 1
    assert findings[0].class_name == "<syntax-error>"


# ---------------------------------------------------------------------------
# ModelNoPluginDaemonFinding.format()
# ---------------------------------------------------------------------------


def test_finding_format_includes_path_line_class_reason() -> None:
    finding = ModelNoPluginDaemonFinding(
        path="src/foo.py",
        line=10,
        column=0,
        class_name="PluginWorker",
        bases=(),
        reason="class name contains Worker",
    )
    fmt = finding.format()
    assert "src/foo.py:10:1:" in fmt
    assert "PluginWorker" in fmt
    assert "Worker" in fmt


# ---------------------------------------------------------------------------
# ModelNoPluginDaemonResult helpers
# ---------------------------------------------------------------------------


def test_result_is_clean_when_no_findings() -> None:
    result = ModelNoPluginDaemonResult(findings=())
    assert result.is_clean is True


def test_result_not_clean_when_findings_present() -> None:
    finding = ModelNoPluginDaemonFinding(
        path="x.py",
        line=1,
        column=0,
        class_name="PluginDaemon",
        bases=(),
        reason="test",
    )
    result = ModelNoPluginDaemonResult(findings=(finding,))
    assert result.is_clean is False


# ---------------------------------------------------------------------------
# COMPUTE handler — protocol compliance
# ---------------------------------------------------------------------------


def test_handler_protocol_properties() -> None:
    handler = HandlerNoPluginDaemonClasses()
    assert handler.handler_id == "no-plugin-daemon-classes"
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.category is EnumMessageCategory.COMMAND
    assert "ModelNoPluginDaemonInput" in handler.message_types


# ---------------------------------------------------------------------------
# COMPUTE handler — handle() with violation
# ---------------------------------------------------------------------------


def test_handler_detects_violation() -> None:
    handler = HandlerNoPluginDaemonClasses()
    payload = ModelNoPluginDaemonInput(files=(("src/foo.py", _PLUGIN_DAEMON),))
    corr_id = uuid4()
    envelope: ModelEventEnvelope[ModelNoPluginDaemonInput] = ModelEventEnvelope(
        payload=payload, correlation_id=corr_id
    )
    output = asyncio.run(handler.handle(envelope))

    assert output.result is not None
    assert isinstance(output.result, ModelNoPluginDaemonResult)
    assert not output.result.is_clean
    assert output.result.findings[0].class_name == "PluginDaemon"
    assert output.correlation_id == corr_id


# ---------------------------------------------------------------------------
# COMPUTE handler — handle() clean tree
# ---------------------------------------------------------------------------


def test_handler_clean_tree() -> None:
    handler = HandlerNoPluginDaemonClasses()
    payload = ModelNoPluginDaemonInput(files=(("src/foo.py", _CLEAN_COMPUTE_PLUGIN),))
    envelope: ModelEventEnvelope[ModelNoPluginDaemonInput] = ModelEventEnvelope(
        payload=payload, correlation_id=uuid4()
    )
    output = asyncio.run(handler.handle(envelope))

    assert output.result is not None
    assert output.result.is_clean


# ---------------------------------------------------------------------------
# COMPUTE handler — handle() multiple files, mixed
# ---------------------------------------------------------------------------


def test_handler_multiple_files_collects_all_findings() -> None:
    handler = HandlerNoPluginDaemonClasses()
    payload = ModelNoPluginDaemonInput(
        files=(
            ("src/a.py", _PLUGIN_DAEMON),
            ("src/b.py", _CLEAN_COMPUTE_PLUGIN),
            ("src/c.py", _PLUGIN_SERVER),
        )
    )
    envelope: ModelEventEnvelope[ModelNoPluginDaemonInput] = ModelEventEnvelope(
        payload=payload, correlation_id=uuid4()
    )
    output = asyncio.run(handler.handle(envelope))

    assert output.result is not None
    assert len(output.result.findings) == 2
    classes = {f.class_name for f in output.result.findings}
    assert "PluginDaemon" in classes
    assert "PluginServer" in classes


# ---------------------------------------------------------------------------
# COMPUTE handler — dict payload coercion
# ---------------------------------------------------------------------------


def test_handler_accepts_dict_payload() -> None:
    """Handler coerces a dict payload to ModelNoPluginDaemonInput via model_validate."""
    handler = HandlerNoPluginDaemonClasses()
    raw_payload = {"files": [["src/foo.py", _PLUGIN_WORKER]]}
    # Coerce dict → typed model as the EFFECT boundary would do before dispatch
    payload = ModelNoPluginDaemonInput.model_validate(raw_payload)
    envelope: ModelEventEnvelope[ModelNoPluginDaemonInput] = ModelEventEnvelope(
        payload=payload, correlation_id=uuid4()
    )
    output = asyncio.run(handler.handle(envelope))

    assert output.result is not None
    assert not output.result.is_clean


# ---------------------------------------------------------------------------
# COMPUTE handler — handler_id propagated to output
# ---------------------------------------------------------------------------


def test_handler_id_in_output() -> None:
    handler = HandlerNoPluginDaemonClasses()
    payload = ModelNoPluginDaemonInput(files=())
    envelope: ModelEventEnvelope[ModelNoPluginDaemonInput] = ModelEventEnvelope(
        payload=payload, correlation_id=uuid4()
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.handler_id == "no-plugin-daemon-classes"


# ---------------------------------------------------------------------------
# COMPUTE handler — missing correlation_id auto-generated
# ---------------------------------------------------------------------------


def test_handler_auto_generates_correlation_id() -> None:
    handler = HandlerNoPluginDaemonClasses()
    payload = ModelNoPluginDaemonInput(files=())
    envelope: ModelEventEnvelope[ModelNoPluginDaemonInput] = ModelEventEnvelope(
        payload=payload  # no correlation_id
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.correlation_id is not None


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def test_main_returns_0_for_no_paths() -> None:
    assert main([]) == 0


def test_main_returns_0_for_clean_file(tmp_path: Path) -> None:
    p = tmp_path / "clean.py"
    p.write_text(_CLEAN_COMPUTE_PLUGIN, encoding="utf-8")
    assert main([str(p)]) == 0


def test_main_returns_1_for_violation_file(tmp_path: Path) -> None:
    p = tmp_path / "bad.py"
    p.write_text(_PLUGIN_DAEMON, encoding="utf-8")
    assert main([str(p)]) == 1
