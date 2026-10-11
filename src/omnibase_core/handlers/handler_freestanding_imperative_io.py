# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Freestanding imperative-IO scan of one source module (OMN-20918).

Ported from onex_change_control ``scanners.handler_contract_compliance
.scan_freestanding_imperative_io`` at 725d2967 for OCC retirement step S8. AST-based
detection of contract-bypassing imperative IO that the node / handler scanner cannot
see because the module is not under a ``node_*/handlers/`` path:

- raw HTTP (``httpx`` / ``requests`` / ``aiohttp`` / ``urllib``)
- raw Kafka producer/consumer construction
- direct DB / cache connections (``asyncpg`` / ``psycopg`` / ``sqlite3``)
- hardcoded inference params (numeric ``max_tokens`` / ``temperature`` / ...)
- hardcoded ONEX topic string literals
- hardcoded LAN / private-range IP literals
- ``subprocess`` invocations of network / git operations

A finding on a line carrying an inline ``# no-contract-check: <reason>`` comment is
retained but marked ``suppressed`` and excluded from the verdict.
"""

from __future__ import annotations

import ast
import re
from typing import Final

from omnibase_core.enums.governance.enum_compliance_verdict import EnumComplianceVerdict
from omnibase_core.enums.governance.enum_compliance_violation import (
    EnumComplianceViolation,
)
from omnibase_core.handlers.handler_arch_handler_contract_compliance import (
    _BARE_TOPIC_NAMES,
    _ONEX_TOPIC_RE,
    _determine_verdict,
    _get_call_string,
    _get_docstring_nodes,
)
from omnibase_core.models.governance.model_freestanding_imperative_finding import (
    ModelFreestandingImperativeFinding,
)
from omnibase_core.models.governance.model_freestanding_imperative_result import (
    ModelFreestandingImperativeResult,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_freestanding_scan_input import (
    ModelFreestandingScanInput,
)

_RawFinding = tuple[int, EnumComplianceViolation, str]

# Inline suppression comment. A finding on a line carrying this comment is
# retained for visibility but does not count as an active violation.
_NO_CONTRACT_CHECK_RE: Final[re.Pattern[str]] = re.compile(r"#\s*no-contract-check:")

# Dotted-call substrings that constitute raw HTTP inference / transport.
_RAW_HTTP_CALL_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "httpx.get",
        "httpx.post",
        "httpx.put",
        "httpx.patch",
        "httpx.delete",
        "httpx.request",
        "httpx.stream",
        "httpx.Client",
        "httpx.AsyncClient",
        "requests.get",
        "requests.post",
        "requests.put",
        "requests.patch",
        "requests.delete",
        "requests.request",
        "requests.Session",
        "aiohttp.ClientSession",
        "aiohttp.request",
        "urllib.request.urlopen",
        "urlopen",
    }
)

# Dotted-call substrings that construct a raw Kafka client.
_RAW_KAFKA_CALL_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "KafkaProducer",
        "KafkaConsumer",
        "AIOKafkaProducer",
        "AIOKafkaConsumer",
        "confluent_kafka.Producer",
        "confluent_kafka.Consumer",
        "Producer",
        "Consumer",
    }
)

# Dotted-call substrings that open a direct DB / cache connection.
_DIRECT_DB_CALL_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "asyncpg.connect",
        "asyncpg.create_pool",
        "psycopg.connect",
        "psycopg2.connect",
        "sqlite3.connect",
        "redis.Redis",
        "redis.from_url",
        "redis.asyncio.Redis",
        "redis.asyncio.from_url",
        "aioredis.from_url",
    }
)

# subprocess argv[0] tokens that are unconditionally network/remote tools.
# ``git`` is intentionally NOT here: local git plumbing (rev-parse, log,
# status, ...) performs no network IO and is a legitimate freestanding op.
# Network git is handled separately via _GIT_NETWORK_VERBS below.
_SUBPROCESS_NETWORK_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "ssh",
        "scp",
        "rsync",
        "curl",
        "wget",
    }
)

# argv[0] value for the git CLI (after stripping any path prefix).
_GIT_ARGV0: Final = "git"

# git subcommands that actually contact a remote. Only these make a
# ``git ...`` subprocess a network op; local plumbing/porcelain such as
# rev-parse, log, describe, status, branch, show, diff, rev-list, commit,
# add, and tag stay unflagged (git commit-SHA provenance is the canonical
# legitimate local use).
_GIT_NETWORK_VERBS: Final[frozenset[str]] = frozenset(
    {
        "fetch",
        "clone",
        "push",
        "pull",
        "ls-remote",
    }
)
_SUBPROCESS_CALL_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.Popen",
    }
)

# Call-keyword names whose numeric literal values are hardcoded inference config.
# ``timeout`` is intentionally excluded: it is a control-flow safety bound on
# local IO (``subprocess.run``, socket reads, ``asyncio.wait_for``, file-lock
# acquisition), not an LLM sampling/generation knob. Flagging every numeric
# ``timeout=`` over-flagged legitimate local timeouts. The remaining params are
# unambiguously inference-only and stay flagged per contract-config doctrine.
_INFERENCE_PARAM_KWARGS: Final[frozenset[str]] = frozenset(
    {
        "max_tokens",
        "max_new_tokens",
        "temperature",
        "top_p",
        "top_k",
        "presence_penalty",
        "frequency_penalty",
    }
)

# LAN / private-range IP literals are hardcoded config.
_LAN_IP_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:192\.168|10\.|172\.(?:1[6-9]|2\d|3[01])|127\.0\.0\.1)"
    r"(?:\.\d{1,3}){1,3}\b"
)


def scan_freestanding_imperative_io(
    request: ModelFreestandingScanInput,
) -> ModelFreestandingImperativeResult:
    """Detect freestanding imperative IO in a non-handler source module."""
    source = request.module.source
    rel_path = request.module.path
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ModelFreestandingImperativeResult(
            module_path=rel_path,
            repo=request.repo,
            findings=[],
            verdict=EnumComplianceVerdict.COMPLIANT,
            allowlisted=request.allowlisted,
            reachability=request.reachability,
        )

    suppressed_lines = _suppressed_lines(source)
    docstring_nodes = _get_docstring_nodes(tree)
    raw_findings: list[_RawFinding] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            _scan_call_node(node, raw_findings)
        elif isinstance(node, ast.Dict):
            _scan_dict_literal(node, raw_findings)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_nodes
        ):
            _scan_string_constant(node.lineno, node.value, raw_findings)

    findings = [
        ModelFreestandingImperativeFinding(
            violation=violation,
            line=line,
            detail=detail,
            suppressed=line in suppressed_lines,
            reachability=request.reachability,
        )
        for line, violation, detail in sorted(raw_findings, key=lambda item: item[0])
    ]
    active = [f.violation for f in findings if not f.suppressed]
    verdict = _determine_verdict(active, is_allowlisted=request.allowlisted)

    return ModelFreestandingImperativeResult(
        module_path=rel_path,
        repo=request.repo,
        findings=findings,
        verdict=verdict,
        allowlisted=request.allowlisted,
        reachability=request.reachability,
    )


class HandlerFreestandingImperativeIo:
    """Decide which imperative-IO findings one freestanding module carries."""

    def handle(
        self, request: ModelFreestandingScanInput
    ) -> ModelFreestandingImperativeResult:
        """Return the per-module result: every finding, suppressed ones marked."""
        return scan_freestanding_imperative_io(request)


def _scan_call_node(
    node: ast.Call,
    findings: list[_RawFinding],
) -> None:
    """Inspect a Call node for transport, subprocess, and inference-param debt."""
    call_str = _get_call_string(node)
    if call_str is not None:
        _classify_call(node, call_str, findings)

    for keyword in node.keywords:
        if (
            keyword.arg in _INFERENCE_PARAM_KWARGS
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, (int, float))
            and not isinstance(keyword.value.value, bool)
        ):
            findings.append(
                (
                    node.lineno,
                    EnumComplianceViolation.HARDCODED_CONFIG,
                    f"hardcoded inference param '{keyword.arg}="
                    f"{keyword.value.value}' passed as call kwarg",
                )
            )


def _scan_dict_literal(
    node: ast.Dict,
    findings: list[_RawFinding],
) -> None:
    """Flag inference params hardcoded as dict keys (e.g. JSON request bodies)."""
    for key, value in zip(node.keys, node.values, strict=True):
        if (
            isinstance(key, ast.Constant)
            and isinstance(key.value, str)
            and key.value in _INFERENCE_PARAM_KWARGS
            and isinstance(value, ast.Constant)
            and isinstance(value.value, (int, float))
            and not isinstance(value.value, bool)
        ):
            param_name: str = key.value
            param_value: int | float = value.value
            findings.append(
                (
                    value.lineno,
                    EnumComplianceViolation.HARDCODED_CONFIG,
                    f"hardcoded inference param '{param_name}={param_value}' "
                    "in dict literal",
                )
            )


def _classify_call(
    node: ast.Call,
    call_str: str,
    findings: list[_RawFinding],
) -> None:
    """Map a dotted call string to its imperative-IO violation, if any."""
    if any(pattern in call_str for pattern in _RAW_HTTP_CALL_PATTERNS):
        findings.append(
            (
                node.lineno,
                EnumComplianceViolation.RAW_HTTP_INFERENCE,
                f"raw HTTP call '{call_str}' bypasses contract transport",
            )
        )
        return
    if any(pattern in call_str for pattern in _DIRECT_DB_CALL_PATTERNS):
        findings.append(
            (
                node.lineno,
                EnumComplianceViolation.DIRECT_DB,
                f"direct DB/cache connection '{call_str}' bypasses injected services",
            )
        )
        return
    if call_str in _RAW_KAFKA_CALL_PATTERNS:
        findings.append(
            (
                node.lineno,
                EnumComplianceViolation.RAW_KAFKA,
                f"raw Kafka client '{call_str}' bypasses injected event bus",
            )
        )
        return
    if call_str in _SUBPROCESS_CALL_PATTERNS and _subprocess_is_network(node):
        findings.append(
            (
                node.lineno,
                EnumComplianceViolation.SUBPROCESS_NETWORK,
                f"subprocess network/git op via '{call_str}'",
            )
        )


def _subprocess_is_network(node: ast.Call) -> bool:
    """Return True if a subprocess call performs a network/remote operation.

    A plain remote tool (``ssh``/``scp``/``rsync``/``curl``/``wget``) always
    counts. ``git`` only counts when its subcommand is a network verb
    (``fetch``/``clone``/``push``/``pull``/``ls-remote``); local git plumbing
    such as ``git rev-parse HEAD`` performs no network IO and is not flagged.
    """
    if not node.args:
        return False
    first = node.args[0]
    tokens: list[str] = []
    if isinstance(first, ast.List):
        tokens = [
            elt.value
            for elt in first.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
    elif isinstance(first, ast.Constant) and isinstance(first.value, str):
        tokens = first.value.split()
    if not tokens:
        return False
    head = tokens[0].rsplit("/", 1)[-1]
    if head in _SUBPROCESS_NETWORK_TOKENS:
        return True
    if head == _GIT_ARGV0:
        return _git_argv_is_network(tokens[1:])
    return False


def _git_argv_is_network(argv: list[str]) -> bool:
    """Return True if a git argv (excluding the ``git`` arg) hits a remote.

    Scans for the first non-option arg (the subcommand), skipping global
    flags like ``-C <dir>`` / ``--no-pager``, and flags it only when that
    subcommand is in _GIT_NETWORK_VERBS. Local plumbing stays unflagged.
    """
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg == "-C":
            # ``git -C <dir>`` — the dir is the next arg; skip both.
            skip_next = True
            continue
        if arg.startswith("-"):
            continue
        return arg in _GIT_NETWORK_VERBS
    return False


def _scan_string_constant(
    lineno: int,
    value: str,
    findings: list[_RawFinding],
) -> None:
    """Inspect a non-docstring string literal for topics and LAN IPs."""
    if _ONEX_TOPIC_RE.search(value) or value in _BARE_TOPIC_NAMES:
        findings.append(
            (
                lineno,
                EnumComplianceViolation.HARDCODED_TOPIC,
                f"hardcoded topic literal '{value}'",
            )
        )
    if _LAN_IP_RE.search(value):
        findings.append(
            (
                lineno,
                EnumComplianceViolation.HARDCODED_CONFIG,
                f"hardcoded LAN/private IP literal '{value}'",
            )
        )


def _suppressed_lines(source: str) -> set[int]:
    """Return 1-based line numbers carrying a '# no-contract-check:' comment."""
    return {
        index
        for index, line in enumerate(source.splitlines(), start=1)
        if _NO_CONTRACT_CHECK_RE.search(line)
    }


# --- Internal helpers ---
