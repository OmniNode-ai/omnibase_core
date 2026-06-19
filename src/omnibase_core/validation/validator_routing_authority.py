# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorRoutingAuthority — canonical routing-authority COMPUTE validator (OMN-13285).

Single canonical port of two previously-fragmented surfaces (W6 / GAP-3,
validator-standardization-remediation-plan §3):

  1. omnimarket-local ``scripts/ci/check_routing_authority.py`` (OMN-12821 /
     12877 / 12883) — positive route-source proof, negative AST audit, residue
     burn-down ratchet, and provider-class endpoint-shape audit.
  2. the previously-UNWIRED ``omnibase_core.validation.delegation.
     validator_delegation_profile`` (O3) — delegation runtime profile schema +
     semantic validation (no raw URL/IP in symbolic-ref fields, token-limit
     consistency).

Both are folded into ONE validator implemented as a **COMPUTE handler** on
``omnibase_core.protocols.runtime.ProtocolMessageHandler`` — NOT a
``ValidatorBase`` subclass (the 3-primitives doctrine forbids bespoke validator
base classes; OMN-13279 removed the prior Generic Validator Node mechanism).

The handler is pure and deterministic: it reads nothing from the filesystem.
The runner / EFFECT boundary loads every file and supplies the corpus as
``ModelRoutingAuthorityInput`` on the envelope ``payload``; the handler returns
a ``ModelRoutingAuthorityReport`` (a JSON-ledger-safe ``result``) whose
``passed`` bit and ``findings`` drive the gate.

This validator's *scope* unions with the canonical-inference gate
(``validator_canonical_inference``, OMN-13219): canonical-inference owns shelled
model CLIs + ``*_MODEL``/``*_PROVIDER`` env reads everywhere; this validator owns
the demo-path routing-source proof, the residue ratchet, the bifrost endpoint
shape, and delegation-profile schema/semantics. They are complementary — neither
re-implements the other.

CLI (the EFFECT boundary that loads files, then invokes the pure handler):

    # pre-commit / CI full audit (repo-relative, reads the configured corpus)
    python -m omnibase_core.validation.validator_routing_authority \\
        --repo omnimarket --repo-root .

    # JSON evidence packet
    python -m omnibase_core.validation.validator_routing_authority \\
        --repo omnimarket --repo-root . --json

Exit codes: 0 = passed (no findings), 1 = at least one FAIL/ERROR finding.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import re
import sys
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.validation.model_routing_authority_file import (
    ModelRoutingAuthorityFile,
)
from omnibase_core.models.validation.model_routing_authority_input import (
    ModelRoutingAuthorityInput,
)
from omnibase_core.models.validation.model_routing_authority_report import (
    VALIDATOR_ID,
    ModelRoutingAuthorityReport,
)
from omnibase_core.models.validation.model_routing_residue_file import (
    ModelRoutingResidueFile,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.utils.util_safe_yaml_loader import parse_yaml_content_as_mapping

# ---------------------------------------------------------------------------
# Report model (the COMPUTE result)
# ---------------------------------------------------------------------------

HANDLER_ID = "routing-authority-compute"

# Default audit configuration for the canonical demo path (omnimarket).
# Supplied as CLI defaults; the pure handler takes the resolved corpus, so a
# different repo's boundary may supply a different config without code change.
_DEFAULT_DEMO_PATH_CONTRACTS: tuple[str, ...] = (
    "src/omnimarket/nodes/node_generation_consumer/contract.yaml",
)
_DEFAULT_DEMO_PATH_SOURCES: tuple[str, ...] = (
    "src/omnimarket/nodes/node_generation_consumer/handlers/handler_generation_consumer.py",
    "src/omnimarket/nodes/node_llm_delegation_call_effect/handlers/handler_inference_intent.py",
    "src/omnimarket/adapters/llm/bifrost/config_loader_bifrost_delegation.py",
)
_DEFAULT_REQUIRED_ROUTING_KEYS: tuple[str, ...] = (
    "provider",
    "served_model_id",
    "endpoint_ref",
    "routing_source",
)
_DEFAULT_SKIP_TOKENS: tuple[str, ...] = (
    "ONEX_FLAG_EXEMPT",
    "ONEX_EXCLUDE",
    "contract-config-ok",
)
_DEFAULT_PROVIDER_LITERAL_TOKENS: tuple[str, ...] = (
    "generativelanguage.googleapis.com",
    "openrouter.ai",
    "api.openai.com",
    "api.anthropic.com",
)
_DEFAULT_FALLBACK_ENDPOINT_ENV_TOKENS: tuple[str, ...] = (
    "LLM_CODER_URL",
    "LLM_REASONER_URL",
    "LLM_BASE_URL",
    "OPENROUTER_BASE_URL",
    "endpoint_url_env",
)
# (path, baseline, debt_ticket, kind, description)
_DEFAULT_RESIDUE_FILES: tuple[tuple[str, int, str, str, str], ...] = (
    (
        "src/omnimarket/inference/bridge_config_loader.py",
        2,
        "OMN-12877",
        "python",
        "bootstrap config loader reads LLM_*_URL and LLM_*_MODEL_NAME from env vars",
    ),
    (
        "src/omnimarket/cli/cli_ab_compare_suite.py",
        2,
        "OMN-12877",
        "python",
        "CLI A/B compare suite reads LLM_GLM_URL and LLM_GLM_MODEL_NAME directly",
    ),
    (
        "src/omnimarket/model_policy.yaml",
        6,
        "OMN-12877",
        "yaml_policy",
        "model_policy.yaml carries 6 env_var declarations superseded by bifrost authority",
    ),
)
_DEFAULT_BIFROST_CONFIG_REL = "src/omnimarket/configs/bifrost_delegation.yaml"
_DEFAULT_DELEGATION_PROFILES: tuple[str, ...] = ()

_CLI_URL_PREFIX = "cli://"

_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
_IP_PATTERN = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

_API_KEY_REF_HINTS: tuple[str, ...] = ("api_key", "api-key", "_KEY", "_TOKEN")


# ---------------------------------------------------------------------------
# Pure audit helpers (no I/O — operate on supplied text)
# ---------------------------------------------------------------------------


def _has_skip_token(line: str, skip_tokens: tuple[str, ...]) -> bool:
    return any(token in line for token in skip_tokens)


def _looks_like_endpoint(value: str) -> bool:
    return bool(_URL_PATTERN.search(value) or _IP_PATTERN.search(value))


def _env_arg_repr(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _is_api_key_resolution(arg_repr: str) -> bool:
    lowered = arg_repr.lower()
    return any(hint.lower() in lowered for hint in _API_KEY_REF_HINTS)


def _scan_env_reads(
    source: str, lines: list[str], skip_tokens: tuple[str, ...]
) -> list[tuple[int, str]]:
    """Return (lineno, detail) for endpoint/provider/model env reads.

    Mirrors the omnimarket script: flags os.environ/os.getenv reads but exempts
    secret-value resolution (``api_key``/``_TOKEN``) and skip-token lines.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    found: dict[int, tuple[str, str, int]] = {}
    for node in ast.walk(tree):
        lineno: int | None = None
        detail: str | None = None
        arg_repr: str = ""
        end_lineno: int = 0

        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "environ"
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "os"
        ):
            lineno = node.lineno
            detail = "os.environ[...]"
            arg_repr = _env_arg_repr(node.slice)
            end_lineno = getattr(node, "end_lineno", node.lineno)
        elif isinstance(node, ast.Call):
            func = node.func
            is_getenv = (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            )
            is_environ_get = (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "environ"
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "os"
            )
            if is_getenv or is_environ_get:
                lineno = node.lineno
                detail = "os.getenv" if is_getenv else "os.environ.get"
                if node.args:
                    arg_repr = _env_arg_repr(node.args[0])
                end_lineno = getattr(node, "end_lineno", node.lineno)

        if lineno is not None and detail is not None and lineno not in found:
            found[lineno] = (detail, arg_repr, end_lineno)

    violations: list[tuple[int, str]] = []
    for lineno in sorted(found):
        detail, arg_repr, end_lineno = found[lineno]
        span = (
            lines[lineno - 1 : end_lineno]
            if end_lineno > lineno
            else [lines[lineno - 1] if lineno <= len(lines) else ""]
        )
        if any(_has_skip_token(ln, skip_tokens) for ln in span):
            continue
        if _is_api_key_resolution(arg_repr):
            continue
        text = (lines[lineno - 1] if lineno <= len(lines) else "").strip()
        violations.append((lineno, f"{detail}({arg_repr!r}) — {text}"))
    return violations


def _iter_string_literals(source: str) -> list[tuple[int, str]]:
    """Return (lineno, value) for non-docstring string literals in the AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    docstring_ids: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstring_ids.add(id(first.value))

    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            out.append((node.lineno, node.value))
    return out


def _scan_literal_tokens(
    source: str,
    lines: list[str],
    tokens: tuple[str, ...],
    label: str,
    skip_tokens: tuple[str, ...],
) -> list[tuple[int, str]]:
    """Flag tokens embedded in non-docstring string literals only."""
    violations: list[tuple[int, str]] = []
    for lineno, literal in _iter_string_literals(source):
        line_text = lines[lineno - 1] if lineno <= len(lines) else ""
        if _has_skip_token(line_text, skip_tokens):
            continue
        for token in tokens:
            if token in literal:
                violations.append((lineno, f"{label}: {token!r} — {line_text.strip()}"))
                break
    return violations


def _find_routing_key_line(contract_text: str, key: str) -> int | None:
    for idx, line in enumerate(contract_text.splitlines(), start=1):
        if line.strip().startswith(f"{key}:"):
            return idx
    return None


def _count_yaml_env_var_fields(data: dict[str, object]) -> int:
    policies = data.get("policies", {})
    if not isinstance(policies, dict):
        return 0
    count = 0
    for policy in policies.values():
        if isinstance(policy, dict) and policy.get("env_var"):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Audit passes — each returns a list of ModelValidationFinding (FAIL on error)
# ---------------------------------------------------------------------------


def _fail(
    message: str, location: str | None, rule_id: str, remediation: str | None = None
) -> ModelValidationFinding:
    return ModelValidationFinding(
        validator_id=VALIDATOR_ID,
        severity="FAIL",
        location=location,
        message=message,
        remediation=remediation,
        rule_id=rule_id,
    )


def _audit_positive(
    payload: ModelRoutingAuthorityInput, backend_index: dict[str, dict[str, object]]
) -> list[ModelValidationFinding]:
    """Demo-path routing fields must resolve from the contract + authority."""
    findings: list[ModelValidationFinding] = []
    for contract in payload.demo_path_contracts:
        try:
            data = parse_yaml_content_as_mapping(contract.text)
        except ModelOnexError as exc:
            findings.append(
                _fail(f"contract did not parse: {exc}", contract.path, "positive-proof")
            )
            continue
        model_routing = data.get("model_routing")
        if not isinstance(model_routing, dict):
            findings.append(
                _fail("missing model_routing block", contract.path, "positive-proof")
            )
            continue

        resolved: dict[str, object] = {}
        for key in payload.required_routing_keys:
            value = model_routing.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                line = _find_routing_key_line(contract.text, key)
                findings.append(
                    _fail(
                        f"model_routing.{key} is absent/blank — it must be declared in "
                        "the contract, not defaulted in code",
                        f"{contract.path}:{line}" if line else contract.path,
                        "positive-proof",
                    )
                )
                continue
            resolved[key] = value

        endpoint_ref = resolved.get("endpoint_ref")
        if isinstance(endpoint_ref, str) and endpoint_ref:
            if endpoint_ref not in backend_index:
                findings.append(
                    _fail(
                        f"endpoint_ref={endpoint_ref!r} does not map to a declared "
                        "bifrost backend in the routing authority — the demo path is "
                        "not authority-backed",
                        contract.path,
                        "positive-proof",
                    )
                )
    return findings


def _audit_negative(
    payload: ModelRoutingAuthorityInput,
) -> list[ModelValidationFinding]:
    """No env read / provider literal / fallback endpoint on demo-path sources."""
    findings: list[ModelValidationFinding] = []
    for src in payload.demo_path_sources:
        lines = src.text.splitlines()
        for ln, detail in _scan_env_reads(src.text, lines, payload.skip_tokens):
            findings.append(
                _fail(f"env-read: {detail}", f"{src.path}:{ln}", "negative-audit")
            )
        for ln, detail in _scan_literal_tokens(
            src.text,
            lines,
            payload.provider_literal_tokens,
            "provider-literal",
            payload.skip_tokens,
        ):
            findings.append(_fail(detail, f"{src.path}:{ln}", "negative-audit"))
        for ln, detail in _scan_literal_tokens(
            src.text,
            lines,
            payload.fallback_endpoint_env_tokens,
            "fallback-endpoint-env",
            payload.skip_tokens,
        ):
            findings.append(_fail(detail, f"{src.path}:{ln}", "negative-audit"))
    return findings


def _audit_residue(
    payload: ModelRoutingAuthorityInput,
) -> list[ModelValidationFinding]:
    """Burn-down ratchet: FAIL only when a residue file EXCEEDS its baseline."""
    findings: list[ModelValidationFinding] = []
    for residue in payload.residue_files:
        if residue.kind == "yaml_policy":
            try:
                data = parse_yaml_content_as_mapping(residue.text)
            except ModelOnexError as exc:
                findings.append(
                    _fail(
                        f"residue yaml did not parse: {exc}",
                        residue.path,
                        "residue-audit",
                    )
                )
                continue
            actual = _count_yaml_env_var_fields(data)
        else:
            actual = len(
                _scan_env_reads(
                    residue.text, residue.text.splitlines(), payload.skip_tokens
                )
            )

        if actual > residue.baseline_count:
            findings.append(
                _fail(
                    f"{actual - residue.baseline_count} new env-authority violation(s) "
                    f"(actual={actual}, baseline={residue.baseline_count}, "
                    f"debt-ticket={residue.debt_ticket})",
                    residue.path,
                    "residue-audit",
                    remediation="Do not add new env reads to a residue file; the "
                    "baseline is burn-down only.",
                )
            )
    return findings


def _is_cli_backend(
    backend_id: str, url_text: str, tier: str, cli_agent_tiers: tuple[str, ...]
) -> bool:
    """True if a backend declares the FORBIDDEN shelled-CLI shape (OMN-13215).

    Explicit branches (not an or-chain) so each signal is independently auditable:
    a ``cli-`` backend_id, a ``cli://`` endpoint_url, or a CLI agent tier.
    """
    if backend_id.startswith("cli-"):
        return True
    if url_text.lower().startswith(_CLI_URL_PREFIX):
        return True
    if tier in cli_agent_tiers:
        return True
    return False


def _audit_shape(
    payload: ModelRoutingAuthorityInput, backends: list[dict[str, object]]
) -> list[ModelValidationFinding]:
    """Provider-class endpoint URL shape audit over the bifrost config backends."""
    findings: list[ModelValidationFinding] = []
    config_path = payload.bifrost_config.path if payload.bifrost_config else "bifrost"
    for backend in backends:
        backend_id = str(backend.get("backend_id", "<unnamed>"))
        tier = str(backend.get("tier", ""))
        endpoint_url = backend.get("endpoint_url")
        endpoint_url_env = backend.get("endpoint_url_env")

        has_env = bool(endpoint_url_env)
        url_text = str(endpoint_url).strip() if endpoint_url is not None else ""
        has_url = bool(url_text)
        is_cli = _is_cli_backend(backend_id, url_text, tier, payload.cli_agent_tiers)

        loc = f"{config_path} (backend_id={backend_id!r})"
        if is_cli:
            findings.append(
                _fail(
                    f"backend_id={backend_id!r} tier={tier!r}: shelled-CLI backends are "
                    "forbidden (OMN-13215) — every tier must declare a complete HTTP(S) "
                    "chat-completions endpoint resolved from contract/overlay",
                    loc,
                    "shape-audit",
                )
            )
        elif has_env:
            if endpoint_url is not None:
                findings.append(
                    _fail(
                        f"backend_id={backend_id!r}: endpoint_url_env={endpoint_url_env!r} is "
                        f"set (overlay-supplied) but endpoint_url={endpoint_url!r} is non-null "
                        "— only one URL source is allowed; set endpoint_url to null",
                        loc,
                        "shape-audit",
                    )
                )
        elif not has_url:
            findings.append(
                _fail(
                    f"backend_id={backend_id!r} tier={tier!r}: endpoint_url is "
                    "absent/empty but endpoint_url_env is not set — a non-local backend "
                    "must carry a complete static endpoint_url (full chat path verbatim)",
                    loc,
                    "shape-audit",
                )
            )
    return findings


def _audit_delegation_profile(
    payload: ModelRoutingAuthorityInput,
) -> list[ModelValidationFinding]:
    """Folded-in validator_delegation_profile: schema + semantic checks (O3)."""
    # Import here so the schema model dependency is only loaded when profiles
    # are supplied (keeps the cold-start path minimal for the common case).
    from omnibase_core.models.contracts.model_delegation_runtime_profile import (
        ModelDelegationRuntimeProfile,
    )

    findings: list[ModelValidationFinding] = []
    for profile_file in payload.delegation_profiles:
        try:
            data = parse_yaml_content_as_mapping(profile_file.text)
        except ModelOnexError as exc:
            findings.append(
                _fail(
                    f"delegation profile did not parse: {exc}",
                    profile_file.path,
                    "delegation-profile",
                )
            )
            continue
        try:
            profile = ModelDelegationRuntimeProfile.model_validate(data)
        except ValidationError as exc:
            for err in exc.errors():
                findings.append(
                    _fail(str(err["msg"]), profile_file.path, "delegation-profile")
                )
            continue

        for backend_name, backend in profile.llm_backends.items():
            if _looks_like_endpoint(backend.bifrost_endpoint_ref):
                findings.append(
                    _fail(
                        f"llm_backends[{backend_name!r}].bifrost_endpoint_ref must be a "
                        f"symbolic ref, not a raw URL or IP: {backend.bifrost_endpoint_ref!r}",
                        profile_file.path,
                        "delegation-profile",
                    )
                )
            if backend.max_tokens_hard_limit < backend.max_tokens_default:
                findings.append(
                    _fail(
                        f"llm_backends[{backend_name!r}].max_tokens_hard_limit "
                        f"({backend.max_tokens_hard_limit}) must be >= max_tokens_default "
                        f"({backend.max_tokens_default})",
                        profile_file.path,
                        "delegation-profile",
                    )
                )
        for server in profile.event_bus.bootstrap_servers:
            if _URL_PATTERN.search(server):
                findings.append(
                    _fail(
                        f"event_bus.bootstrap_servers entry must not be a URL "
                        f"(use host:port form): {server!r}",
                        profile_file.path,
                        "delegation-profile",
                    )
                )
    return findings


def _load_bifrost_backends(
    payload: ModelRoutingAuthorityInput,
) -> tuple[list[dict[str, object]], list[ModelValidationFinding]]:
    findings: list[ModelValidationFinding] = []
    if payload.bifrost_config is None:
        return [], findings
    try:
        data = parse_yaml_content_as_mapping(payload.bifrost_config.text)
    except ModelOnexError as exc:
        findings.append(
            _fail(
                f"bifrost config did not parse: {exc}",
                payload.bifrost_config.path,
                "shape-audit",
            )
        )
        return [], findings
    backends = data.get("backends", [])
    if not isinstance(backends, list):
        findings.append(
            _fail(
                "'backends' is not a list", payload.bifrost_config.path, "shape-audit"
            )
        )
        return [], findings
    return [b for b in backends if isinstance(b, dict)], findings


def evaluate(payload: ModelRoutingAuthorityInput) -> ModelRoutingAuthorityReport:
    """Pure evaluation: run every audit over the supplied corpus.

    No I/O. Deterministic. Findings are sorted by a stable key so the verdict is
    order-independent (in-memory bus pub/sub ordering is not guaranteed).
    """
    backends, shape_load_findings = _load_bifrost_backends(payload)
    backend_index = {
        str(b.get("backend_id")): b for b in backends if b.get("backend_id") is not None
    }

    findings: list[ModelValidationFinding] = []
    findings.extend(_audit_positive(payload, backend_index))
    findings.extend(_audit_negative(payload))
    findings.extend(_audit_residue(payload))
    findings.extend(shape_load_findings)
    findings.extend(_audit_shape(payload, backends))
    findings.extend(_audit_delegation_profile(payload))

    findings.sort(key=lambda f: (f.rule_id or "", f.location or "", f.message))
    passed = not any(f.severity in {"FAIL", "ERROR"} for f in findings)
    return ModelRoutingAuthorityReport(passed=passed, findings=tuple(findings))


# ---------------------------------------------------------------------------
# COMPUTE handler (ProtocolMessageHandler) — pure, no I/O
# ---------------------------------------------------------------------------


class ValidatorRoutingAuthority:
    """Routing-authority validator as a COMPUTE handler on ProtocolMessageHandler.

    Pure and deterministic: the handler reads nothing from disk. The runner /
    EFFECT boundary loads files and supplies them as
    ``ModelRoutingAuthorityInput`` on the envelope payload. The verdict is
    returned as the ``result`` of a COMPUTE ``ModelHandlerOutput``.
    """

    @property
    def handler_id(self) -> str:
        return HANDLER_ID

    @property
    def category(self) -> EnumMessageCategory:
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"RoutingAuthorityValidate"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self, envelope: ModelEventEnvelope[ModelRoutingAuthorityInput]
    ) -> ModelHandlerOutput[ModelRoutingAuthorityReport]:
        report = evaluate(envelope.payload)
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=envelope.correlation_id or uuid4(),
            handler_id=self.handler_id,
            result=report,
        )


# ---------------------------------------------------------------------------
# CLI / EFFECT boundary — loads files, dispatches the pure handler, exits
# ---------------------------------------------------------------------------


def _read(repo_root: Path, rel: str) -> ModelRoutingAuthorityFile | None:
    path = repo_root / rel
    if not path.is_file():
        return None
    return ModelRoutingAuthorityFile(path=rel, text=path.read_text(encoding="utf-8"))


def build_input_from_disk(
    repo: str, repo_root: Path
) -> tuple[ModelRoutingAuthorityInput, list[str], int]:
    """EFFECT boundary: load the configured corpus from disk into a pure input.

    Returns (input, missing, present_count) where ``missing`` lists configured
    files absent on disk and ``present_count`` is how many configured artifacts
    were found. A repo that hosts NONE of the configured artifacts does not own
    the routing-authority demo path and is skipped cleanly by the caller; a repo
    that hosts SOME but is missing others has a broken/partial demo path and the
    missing entries are hard errors.
    """
    missing: list[str] = []
    present_count = 0

    demo_contracts: list[ModelRoutingAuthorityFile] = []
    for rel in _DEFAULT_DEMO_PATH_CONTRACTS:
        f = _read(repo_root, rel)
        if f is None:
            missing.append(rel)
        else:
            present_count += 1
            demo_contracts.append(f)

    demo_sources: list[ModelRoutingAuthorityFile] = []
    for rel in _DEFAULT_DEMO_PATH_SOURCES:
        f = _read(repo_root, rel)
        if f is None:
            missing.append(rel)
        else:
            present_count += 1
            demo_sources.append(f)

    residue: list[ModelRoutingResidueFile] = []
    for rel, baseline, ticket, kind, desc in _DEFAULT_RESIDUE_FILES:
        path = repo_root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        present_count += 1
        residue.append(
            ModelRoutingResidueFile(
                path=rel,
                text=path.read_text(encoding="utf-8"),
                kind=kind,
                baseline_count=baseline,
                debt_ticket=ticket,
                description=desc,
            )
        )

    bifrost = _read(repo_root, _DEFAULT_BIFROST_CONFIG_REL)
    if bifrost is None:
        missing.append(_DEFAULT_BIFROST_CONFIG_REL)
    else:
        present_count += 1

    delegation_profiles: list[ModelRoutingAuthorityFile] = []
    for rel in _DEFAULT_DELEGATION_PROFILES:
        f = _read(repo_root, rel)
        if f is not None:
            delegation_profiles.append(f)

    payload = ModelRoutingAuthorityInput(
        repo=repo,
        demo_path_contracts=tuple(demo_contracts),
        required_routing_keys=_DEFAULT_REQUIRED_ROUTING_KEYS,
        demo_path_sources=tuple(demo_sources),
        provider_literal_tokens=_DEFAULT_PROVIDER_LITERAL_TOKENS,
        fallback_endpoint_env_tokens=_DEFAULT_FALLBACK_ENDPOINT_ENV_TOKENS,
        skip_tokens=_DEFAULT_SKIP_TOKENS,
        residue_files=tuple(residue),
        bifrost_config=bifrost,
        delegation_profiles=tuple(delegation_profiles),
    )
    return payload, missing, present_count


def _run_handler(payload: ModelRoutingAuthorityInput) -> ModelRoutingAuthorityReport:
    """Dispatch the pure COMPUTE handler at the async→sync git-hook edge."""
    handler = ValidatorRoutingAuthority()
    envelope: ModelEventEnvelope[ModelRoutingAuthorityInput] = ModelEventEnvelope(
        payload=payload
    )
    output = asyncio.run(handler.handle(envelope))
    report = output.result
    assert report is not None  # COMPUTE always returns result
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check-routing-authority",
        description="Routing-authority + delegation-profile COMPUTE validator (OMN-13285).",
    )
    parser.add_argument("paths", nargs="*", help="Ignored (full-corpus audit).")
    parser.add_argument("--repo", default="omnimarket", help="Repo name for findings.")
    parser.add_argument("--repo-root", default=".", help="Repo root.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    payload, missing, present_count = build_input_from_disk(args.repo, repo_root)

    # A repo that hosts NONE of the configured demo-path artifacts does not own
    # the routing-authority demo path → skip cleanly (PASS). The gate only audits
    # the repos that actually carry the routing/delegation surface.
    if present_count == 0:
        if not args.json:
            sys.stdout.write(
                f"[routing-authority-gate] SKIP — {args.repo} hosts no configured "
                "routing-authority demo-path artifacts (nothing to audit).\n"
            )
        else:
            sys.stdout.write(
                json.dumps(
                    {
                        "validator_id": VALIDATOR_ID,
                        "repo": args.repo,
                        "passed": True,
                        "skipped": True,
                        "findings": [],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        return 0

    report = _run_handler(payload)

    # Partial demo path (some artifacts present, some missing) is a hard error.
    missing_findings = [
        _fail(f"configured demo-path artifact missing: {rel}", rel, "missing-artifact")
        for rel in missing
    ]
    all_findings = (*missing_findings, *report.findings)
    passed = report.passed and not missing_findings

    if args.json:
        out = {
            "validator_id": VALIDATOR_ID,
            "repo": args.repo,
            "passed": passed,
            "findings": [f.model_dump() for f in all_findings],
        }
        sys.stdout.write(json.dumps(out, indent=2, sort_keys=True, default=str) + "\n")
        return 0 if passed else 1

    if passed:
        sys.stdout.write(
            f"[routing-authority-gate] PASS — {len(payload.demo_path_contracts)} "
            f"demo-path contract(s) authority-backed; negative audit clean; "
            f"{len(payload.residue_files)} residue file(s) within baseline; "
            "bifrost shape + delegation profiles clean.\n"
        )
        return 0

    sys.stderr.write("[routing-authority-gate] FAIL\n")
    for f in all_findings:
        sys.stderr.write(f"  [{f.rule_id}] {f.location}: {f.message}\n")
    sys.stderr.write(
        "\nFix: every demo-path routing field must resolve from contract / overlay / "
        "routing authority; no env reads / provider literals / fallback endpoint "
        "strings on the demo path; residue files must not exceed baselines; bifrost "
        "backends must respect endpoint-shape rules; delegation profiles must use "
        "symbolic refs.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
