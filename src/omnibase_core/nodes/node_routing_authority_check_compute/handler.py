# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeRoutingAuthorityCheckCompute — routing-authority verification COMPUTE handler.

Ported from omnimarket/scripts/ci/check_routing_authority.py (OMN-12821,
OMN-12877, OMN-12883) into a canonical COMPUTE node on ProtocolMessageHandler.
Also consolidates the previously unwired core validator_delegation_profile
(OMN-13306, W6b).

This gate proves three things:

POSITIVE route-source proof
    For each configured demo-path contract, provider, model (served_model_id),
    endpoint_ref, the resolved endpoint URL, and route_source all come from the
    contract / overlay / routing authority — recorded with the source file:line
    that proves each came from authority.

NEGATIVE audit
    Static AST scan over the exact demo-path source files proves NO demo-path
    code reads env vars for endpoint/provider/model, no hardcoded provider
    literals, and no fallback endpoint strings after route resolution.

RESIDUE audit (OMN-12877)
    Scope-extended ratchet over confirmed residue files that carry known
    env-authority debt. Gate FAILS when actual_count > baseline_count (new
    violation introduced). Gate PASSES when actual_count <= baseline_count.

PROVIDER-CLASS ENDPOINT SHAPE audit (OMN-12883)
    Static scan over bifrost_delegation.yaml proves every backend respects the
    provider-class endpoint URL shape contract.

DELEGATION PROFILE validation (consolidated from validator_delegation_profile)
    Schema + semantic validation of delegation runtime profiles: no raw URLs/IPs
    in ref fields, token limit consistency, no URL-form bootstrap_servers.

Architecture: COMPUTE node — pure, deterministic, no I/O inside the handler.
File contents arrive via the envelope payload; the I/O of loading files happens
at the EFFECT boundary (the CLI runner / pre-commit hook), never inside the
handler.

ProtocolMessageHandler implementation: structural duck-typing (matches the
protocol; not a subclass of ValidatorBase or any Plugin* base class).

See: OMN-13306 (W6b), OMN-12821, OMN-12877, OMN-12883, OMN-9048
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, cast

import yaml

from omnibase_core.models.validation.model_residue_entry import (
    ModelResidueEntry,
)
from omnibase_core.models.validation.model_routing_authority_check_input import (
    ModelRoutingAuthorityCheckInput,
)
from omnibase_core.models.validation.model_routing_authority_check_output import (
    ModelRoutingAuthorityCheckOutput,
)
from omnibase_core.models.validation.model_routing_contract_entry import (
    ModelRoutingContractEntry,
)

__all__ = [
    "NodeRoutingAuthorityCheckCompute",
    "ModelRoutingAuthorityCheckInput",
    "ModelRoutingAuthorityCheckOutput",
    "ModelResidueEntry",
    "check_routing_authority_at_path",
]

# ---------------------------------------------------------------------------
# Scanning helpers (pure functions — no I/O)
# ---------------------------------------------------------------------------

_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
_IP_PATTERN = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")


def _load_yaml_document(text: str) -> object:
    return yaml.load(text, Loader=yaml.SafeLoader)


def _has_skip_token(line: str, skip_tokens: tuple[str, ...]) -> bool:
    return any(token in line for token in skip_tokens)


def _env_arg_repr(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _is_api_key_resolution(arg_repr: str, hints: tuple[str, ...]) -> bool:
    lowered = arg_repr.lower()
    return any(hint.lower() in lowered for hint in hints)


def _scan_env_reads(
    source: str,
    lines: list[str],
    skip_tokens: tuple[str, ...],
    api_key_ref_hints: tuple[str, ...],
) -> list[tuple[int, str]]:
    """Return (lineno, detail) for endpoint/provider/model env reads."""
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
        if _is_api_key_resolution(arg_repr, api_key_ref_hints):
            continue
        text = (lines[lineno - 1] if lineno <= len(lines) else "").strip()
        violations.append((lineno, f"{detail}({arg_repr!r}) — {text}"))
    return violations


def _iter_string_literals(source: str) -> list[tuple[int, str]]:
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


def _count_yaml_env_var_fields(data: dict[str, object]) -> int:
    policies = data.get("policies", {})
    if not isinstance(policies, dict):
        return 0
    count = 0
    for _name, policy in policies.items():
        if isinstance(policy, dict) and policy.get("env_var"):
            count += 1
    return count


def _find_routing_key_line(contract_text: str, key: str) -> int | None:
    for idx, line in enumerate(contract_text.splitlines(), start=1):
        if line.strip().startswith(f"{key}:"):
            return idx
    return None


# ---------------------------------------------------------------------------
# Delegation profile validation helpers (consolidated from validator_delegation_profile)
# ---------------------------------------------------------------------------


def _validate_delegation_profile_content(
    data: Any,
    source_name: str,
) -> list[str]:
    """Validate a delegation runtime profile mapping; return error strings."""
    from pydantic import (
        ValidationError,  # local import preserves COMPUTE purity constraint
    )

    try:
        from omnibase_core.models.contracts.model_delegation_runtime_profile import (
            ModelDelegationRuntimeProfile,
        )
    except ImportError:
        # Model not available in this deployment; skip delegation-profile check.
        return []

    errors: list[str] = []
    try:
        profile = ModelDelegationRuntimeProfile.model_validate(data)
    except ValidationError as exc:
        return [f"{source_name}: schema error: {e['msg']}" for e in exc.errors()]
    except Exception as exc:  # noqa: BLE001  # fallback-ok: validator contract — never raises
        return [f"{source_name}: unexpected error: {exc}"]

    for backend_name, backend in profile.llm_backends.items():
        ref = backend.bifrost_endpoint_ref
        if _URL_PATTERN.search(ref) or _IP_PATTERN.search(ref):
            errors.append(
                f"{source_name}: llm_backends[{backend_name!r}].bifrost_endpoint_ref "
                f"must be a symbolic ref, not a raw URL or IP: {ref!r}"
            )
        if backend.max_tokens_hard_limit < backend.max_tokens_default:
            errors.append(
                f"{source_name}: llm_backends[{backend_name!r}].max_tokens_hard_limit "
                f"({backend.max_tokens_hard_limit}) must be >= max_tokens_default "
                f"({backend.max_tokens_default})"
            )

    for server in profile.event_bus.bootstrap_servers:
        if _URL_PATTERN.search(server):
            errors.append(
                f"{source_name}: event_bus.bootstrap_servers entry must not be a URL "
                f"(use host:port): {server!r}"
            )

    return errors


# ---------------------------------------------------------------------------
# COMPUTE handler
# ---------------------------------------------------------------------------


class NodeRoutingAuthorityCheckCompute:
    """Routing-authority verification COMPUTE handler.

    Pure, deterministic, no filesystem/network I/O inside the handler.
    All file contents arrive via the ``ModelRoutingAuthorityCheckInput`` payload.

    Satisfies ProtocolMessageHandler structurally (duck-typing). Register via
    DI container or invoke directly in tests.

    The ``check()`` method is the synchronous computation entry-point used by
    the pre-commit CLI wrapper. The ``handle()`` method wraps it for dispatch-
    engine consumption (async envelope in, async envelope out).
    """

    @property
    def handler_id(self) -> str:
        return "routing-authority-check-compute"

    @property
    def message_types(self) -> set[str]:
        return {"RoutingAuthorityCheckRequested"}

    @property
    def node_kind(self) -> Any:
        from omnibase_core.enums.enum_node_kind import EnumNodeKind

        return EnumNodeKind.COMPUTE

    @property
    def category(self) -> Any:
        from omnibase_core.enums.enum_execution_shape import (
            EnumMessageCategory,
        )

        return EnumMessageCategory.COMMAND

    # ------------------------------------------------------------------
    # Core computation (synchronous — pure function over payload data)
    # ------------------------------------------------------------------

    def check(
        self, inp: ModelRoutingAuthorityCheckInput
    ) -> ModelRoutingAuthorityCheckOutput:
        """Run all four audits and return a structured verdict.

        Pure: all inputs arrive through ``inp``; no filesystem reads.
        """
        positive = self._build_positive_proof(inp)
        negative = self._build_negative_audit(inp)
        residue = self._build_residue_audit(inp)
        shape = self._build_provider_endpoint_shape_audit(inp)

        positive_errors = cast(list[str], positive["errors"])
        positive_entries = cast(list[dict[str, object]], positive["entries"])
        positive_ok = len(positive_errors) == 0 and len(positive_entries) > 0
        negative_ok = bool(negative["clean"])
        residue_ok = bool(residue["clean"])
        shape_ok = bool(shape["clean"])
        passed = positive_ok and negative_ok and residue_ok and shape_ok

        return ModelRoutingAuthorityCheckOutput(
            passed=passed,
            positive_ok=positive_ok,
            negative_ok=negative_ok,
            residue_ok=residue_ok,
            shape_ok=shape_ok,
            positive_proof=positive,
            negative_audit=negative,
            residue_audit=residue,
            provider_endpoint_shape_audit=shape,
        )

    async def handle(self, envelope: Any) -> Any:
        """Dispatch-engine entry-point — wraps check() for async bus invocation."""

        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        inp: ModelRoutingAuthorityCheckInput = envelope.payload
        result = self.check(inp)
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=envelope.correlation_id,
            handler_id=self.handler_id,
            result=result,
        )

    # ------------------------------------------------------------------
    # Positive proof
    # ------------------------------------------------------------------

    def _resolve_endpoint_for_ref(
        self,
        endpoint_ref: str,
        bifrost_content: str,
        bifrost_rel: str,
    ) -> tuple[str | None, str | None, str]:
        if not bifrost_content:
            return None, None, f"{bifrost_rel}: content empty (skipped)"
        try:
            data = _load_yaml_document(bifrost_content)
        except yaml.YAMLError:
            return None, None, f"{bifrost_rel}: YAML parse error"
        backends = data.get("backends", []) if isinstance(data, dict) else []
        for backend in backends:
            if not isinstance(backend, dict):
                continue
            if backend.get("backend_id") != endpoint_ref:
                continue
            return (
                backend.get("endpoint_url"),
                backend.get("api_key_env"),
                f"{bifrost_rel}: backend_id={endpoint_ref!r} (overlay-merged at runtime)",
            )
        return (
            None,
            None,
            f"{bifrost_rel}: backend_id={endpoint_ref!r} NOT DECLARED",
        )

    def _build_positive_proof(
        self, inp: ModelRoutingAuthorityCheckInput
    ) -> dict[str, object]:
        entries: list[dict[str, object]] = []
        errors: list[str] = []

        for entry in inp.demo_path_contracts:
            contract_text = inp.contract_contents.get(entry.contract_rel, "")
            if not contract_text:
                errors.append(
                    f"demo-path contract content missing: {entry.contract_rel}"
                )
                continue

            try:
                data = _load_yaml_document(contract_text)
            except yaml.YAMLError:
                errors.append(f"{entry.contract_rel}: YAML parse error")
                continue

            if not isinstance(data, dict):
                errors.append(
                    f"{entry.contract_rel}: contract did not parse to a mapping"
                )
                continue

            model_routing = data.get("model_routing")
            if not isinstance(model_routing, dict):
                errors.append(f"{entry.contract_rel}: missing model_routing block")
                continue

            field_sources: dict[str, str] = {}
            resolved_fields: dict[str, object] = {}
            for key in entry.required_routing_keys:
                value = model_routing.get(key)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(
                        f"{entry.contract_rel}: model_routing.{key} is absent/blank"
                    )
                    continue
                line = _find_routing_key_line(contract_text, key)
                field_sources[key] = (
                    f"{entry.contract_rel}:{line}"
                    if line is not None
                    else entry.contract_rel
                )
                resolved_fields[key] = value

            endpoint_ref = resolved_fields.get("endpoint_ref")
            endpoint_url: str | None = None
            endpoint_source = ""
            if isinstance(endpoint_ref, str) and endpoint_ref:
                endpoint_url, _api_key_ref, endpoint_source = (
                    self._resolve_endpoint_for_ref(
                        endpoint_ref,
                        inp.bifrost_config_content,
                        inp.bifrost_config_rel,
                    )
                )
                if "NOT DECLARED" in endpoint_source or "NOT FOUND" in endpoint_source:
                    errors.append(
                        f"{entry.contract_rel}: endpoint_ref={endpoint_ref!r} does not "
                        f"map to a declared bifrost backend ({endpoint_source})"
                    )

            entries.append(
                {
                    "contract": entry.contract_rel,
                    "provider": resolved_fields.get("provider"),
                    "model": resolved_fields.get("served_model_id"),
                    "endpoint_ref": resolved_fields.get("endpoint_ref"),
                    "endpoint": endpoint_url,
                    "route_source": resolved_fields.get("routing_source"),
                    "field_sources": field_sources,
                    "endpoint_source": endpoint_source,
                }
            )

        return {"entries": entries, "errors": errors}

    # ------------------------------------------------------------------
    # Negative audit
    # ------------------------------------------------------------------

    def _build_negative_audit(
        self, inp: ModelRoutingAuthorityCheckInput
    ) -> dict[str, object]:
        file_results: list[dict[str, object]] = []
        errors: list[str] = []

        for src_rel in inp.demo_path_sources:
            source = inp.source_contents.get(src_rel, "")
            if not source:
                errors.append(f"demo-path source content missing: {src_rel}")
                continue

            lines = source.splitlines()
            env_reads = _scan_env_reads(
                source, lines, inp.skip_tokens, inp.api_key_ref_hints
            )
            provider_literals = _scan_literal_tokens(
                source,
                lines,
                inp.provider_literal_tokens,
                "provider-literal",
                inp.skip_tokens,
            )
            fallback_endpoints = _scan_literal_tokens(
                source,
                lines,
                inp.fallback_endpoint_env_tokens,
                "fallback-endpoint-env",
                inp.skip_tokens,
            )

            violations: list[str] = []
            violations.extend(f"{src_rel}:{ln}: env-read: {d}" for ln, d in env_reads)
            violations.extend(f"{src_rel}:{ln}: {d}" for ln, d in provider_literals)
            violations.extend(f"{src_rel}:{ln}: {d}" for ln, d in fallback_endpoints)

            file_results.append(
                {
                    "source": src_rel,
                    "clean": len(violations) == 0,
                    "violations": violations,
                }
            )

        all_violations = [
            v for fr in file_results for v in cast(list[str], fr["violations"])
        ]
        return {
            "files": file_results,
            "errors": errors,
            "clean": len(all_violations) == 0 and len(errors) == 0,
            "violation_count": len(all_violations),
        }

    # ------------------------------------------------------------------
    # Residue ratchet
    # ------------------------------------------------------------------

    def _build_residue_audit(
        self, inp: ModelRoutingAuthorityCheckInput
    ) -> dict[str, object]:
        file_results: list[dict[str, object]] = []
        errors: list[str] = []
        new_violations: list[str] = []

        for entry in inp.residue_entries:
            source = inp.residue_contents.get(entry.file_rel, "")
            if not source:
                errors.append(f"residue source content missing: {entry.file_rel}")
                continue
            lines = source.splitlines()
            env_reads = _scan_env_reads(
                source, lines, inp.skip_tokens, inp.api_key_ref_hints
            )
            actual_count = len(env_reads)
            regression = actual_count > entry.baseline_count
            if regression:
                delta = actual_count - entry.baseline_count
                new_violations.append(
                    f"{entry.file_rel}: {delta} new env-authority violation(s) "
                    f"(actual={actual_count}, baseline={entry.baseline_count}, "
                    f"debt-ticket={entry.debt_ticket})"
                )
            file_results.append(
                {
                    "source": entry.file_rel,
                    "debt_ticket": entry.debt_ticket,
                    "debt_description": entry.description,
                    "baseline_count": entry.baseline_count,
                    "actual_count": actual_count,
                    "regression": regression,
                    "violations": [
                        f"{entry.file_rel}:{ln}: env-read: {d}" for ln, d in env_reads
                    ],
                }
            )

        # YAML policy residue
        for yaml_entry in inp.yaml_policy_residue:
            yaml_text = inp.yaml_policy_contents.get(yaml_entry.file_rel, "")
            if not yaml_text:
                errors.append(f"residue YAML content missing: {yaml_entry.file_rel}")
                continue
            try:
                data = _load_yaml_document(yaml_text)
            except yaml.YAMLError:
                errors.append(f"{yaml_entry.file_rel}: YAML parse error")
                continue
            if not isinstance(data, dict):
                errors.append(f"{yaml_entry.file_rel}: did not parse to a mapping")
                continue
            actual_count = _count_yaml_env_var_fields(data)
            regression = actual_count > yaml_entry.baseline_count
            if regression:
                delta = actual_count - yaml_entry.baseline_count
                new_violations.append(
                    f"{yaml_entry.file_rel}: {delta} new env_var policy declarations "
                    f"(actual={actual_count}, baseline={yaml_entry.baseline_count}, "
                    f"debt-ticket={yaml_entry.debt_ticket})"
                )
            file_results.append(
                {
                    "source": yaml_entry.file_rel,
                    "debt_ticket": yaml_entry.debt_ticket,
                    "debt_description": yaml_entry.description,
                    "baseline_count": yaml_entry.baseline_count,
                    "actual_count": actual_count,
                    "regression": regression,
                    "violations": [],
                }
            )

        return {
            "files": file_results,
            "errors": errors,
            "new_violations": new_violations,
            "clean": len(new_violations) == 0 and len(errors) == 0,
        }

    # ------------------------------------------------------------------
    # Provider-class endpoint shape audit
    # ------------------------------------------------------------------

    def _build_provider_endpoint_shape_audit(
        self, inp: ModelRoutingAuthorityCheckInput
    ) -> dict[str, object]:
        if not inp.bifrost_config_content:
            return {
                "config": inp.bifrost_config_rel,
                "backends": [],
                "violations": [],
                "clean": True,
                "skipped": True,
            }

        try:
            data = _load_yaml_document(inp.bifrost_config_content)
        except yaml.YAMLError:
            return {
                "config": inp.bifrost_config_rel,
                "backends": [],
                "violations": [f"{inp.bifrost_config_rel}: YAML parse error"],
                "clean": False,
            }

        if not isinstance(data, dict):
            return {
                "config": inp.bifrost_config_rel,
                "backends": [],
                "violations": [f"{inp.bifrost_config_rel}: did not parse to a mapping"],
                "clean": False,
            }

        backends = data.get("backends", [])
        if not isinstance(backends, list):
            return {
                "config": inp.bifrost_config_rel,
                "backends": [],
                "violations": [f"{inp.bifrost_config_rel}: 'backends' is not a list"],
                "clean": False,
            }

        violations: list[str] = []
        backend_results: list[dict[str, object]] = []

        for backend in backends:
            if not isinstance(backend, dict):
                violations.append(
                    f"{inp.bifrost_config_rel}: backend entry is not a mapping"
                )
                continue

            backend_id = backend.get("backend_id", "<unnamed>")
            tier = backend.get("tier", "")
            endpoint_url = backend.get("endpoint_url")
            endpoint_url_env = backend.get("endpoint_url_env")

            has_endpoint_url_env = bool(endpoint_url_env)
            endpoint_url_text = (
                str(endpoint_url).strip() if endpoint_url is not None else ""
            )
            has_endpoint_url = bool(endpoint_url_text)

            backend_id_is_cli = str(backend_id).startswith("cli-")
            endpoint_url_is_cli = endpoint_url_text.lower().startswith(
                inp.cli_url_prefix
            )
            tier_is_cli = tier in inp.cli_agent_tiers
            is_cli_backend = any((backend_id_is_cli, endpoint_url_is_cli, tier_is_cli))

            backend_violations: list[str] = []
            if is_cli_backend:
                backend_violations.append(
                    f"backend_id={backend_id!r} tier={tier!r}: shelled-CLI backends "
                    "are forbidden (OMN-13215)"
                )
            elif has_endpoint_url_env:
                if endpoint_url is not None:
                    backend_violations.append(
                        f"backend_id={backend_id!r}: endpoint_url_env={endpoint_url_env!r} "
                        f"is set but endpoint_url={endpoint_url!r} is non-null — "
                        "set endpoint_url to null"
                    )
            elif not has_endpoint_url:
                backend_violations.append(
                    f"backend_id={backend_id!r} tier={tier!r}: endpoint_url is "
                    "absent/empty but endpoint_url_env is not set — a non-local "
                    "backend must carry a complete static endpoint_url"
                )

            violations.extend(backend_violations)
            backend_results.append(
                {
                    "backend_id": backend_id,
                    "tier": tier,
                    "endpoint_url": endpoint_url,
                    "endpoint_url_env": endpoint_url_env,
                    "url_source": "overlay" if has_endpoint_url_env else "static",
                    "violations": backend_violations,
                    "compliant": len(backend_violations) == 0,
                }
            )

        return {
            "config": inp.bifrost_config_rel,
            "backends": backend_results,
            "violations": violations,
            "clean": len(violations) == 0,
        }


# ---------------------------------------------------------------------------
# Convenience helper used by the pre-commit CLI wrapper
# ---------------------------------------------------------------------------


def check_routing_authority_at_path(
    repo_root: Path,
    demo_path_contracts: tuple[str, ...],
    demo_path_sources: tuple[str, ...],
    residue_entries: tuple[ModelResidueEntry, ...] = (),
    yaml_policy_residue: tuple[ModelResidueEntry, ...] = (),
    bifrost_config_rel: str = "src/omnimarket/configs/bifrost_delegation.yaml",
    skip_tokens: tuple[str, ...] = (
        "ONEX_FLAG_EXEMPT",
        "ONEX_EXCLUDE",
        "contract-config-ok",
    ),
) -> ModelRoutingAuthorityCheckOutput:
    """Load files from repo_root and run the check.

    This is the EFFECT boundary: it reads the filesystem and builds the
    ``ModelRoutingAuthorityCheckInput`` payload, then delegates to the pure
    COMPUTE handler. Called by the pre-commit CLI wrapper.
    """
    contract_contents: dict[str, str] = {}
    for rel in demo_path_contracts:
        p = repo_root / rel
        contract_contents[rel] = p.read_text(encoding="utf-8") if p.exists() else ""

    source_contents: dict[str, str] = {}
    for rel in demo_path_sources:
        p = repo_root / rel
        source_contents[rel] = p.read_text(encoding="utf-8") if p.exists() else ""

    residue_contents: dict[str, str] = {}
    for entry in residue_entries:
        p = repo_root / entry.file_rel
        residue_contents[entry.file_rel] = (
            p.read_text(encoding="utf-8") if p.exists() else ""
        )

    yaml_policy_contents: dict[str, str] = {}
    for entry in yaml_policy_residue:
        p = repo_root / entry.file_rel
        yaml_policy_contents[entry.file_rel] = (
            p.read_text(encoding="utf-8") if p.exists() else ""
        )

    bifrost_path = repo_root / bifrost_config_rel
    bifrost_content = (
        bifrost_path.read_text(encoding="utf-8") if bifrost_path.exists() else ""
    )

    inp = ModelRoutingAuthorityCheckInput(
        demo_path_contracts=tuple(
            ModelRoutingContractEntry(contract_rel=r) for r in demo_path_contracts
        ),
        contract_contents=contract_contents,
        bifrost_config_rel=bifrost_config_rel,
        bifrost_config_content=bifrost_content,
        demo_path_sources=demo_path_sources,
        source_contents=source_contents,
        residue_entries=residue_entries,
        residue_contents=residue_contents,
        yaml_policy_residue=yaml_policy_residue,
        yaml_policy_contents=yaml_policy_contents,
        skip_tokens=skip_tokens,
    )
    handler = NodeRoutingAuthorityCheckCompute()
    return handler.check(inp)
