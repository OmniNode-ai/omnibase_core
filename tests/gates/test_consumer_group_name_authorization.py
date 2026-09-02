# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-15639 AC3 — consumer-group names must be authorized by the MSK IAM policy.

Why this gate exists
--------------------
``onex delegate --bus kafka`` died on onex-dev with ``GroupAuthorizationFailedError``
*before publishing anything*, because ``runtime_local.py`` minted the ad-hoc group
``runtime-local-HandlerDelegateSkill.__t.onex.cmd.omnimarket.delegate-skill.v1`` and the
MSK IAM policy authorizes no ``runtime-local-`` prefix. Two individually-correct
components, no field-by-field agreement, 100% runtime failure — the OMN-14208 seam
class. A prose rule saying "keep these in sync" is not a mechanism
(``feedback_a_rule_is_not_a_mechanism``), so this is a pre-merge gate.

It is collected by ``testpaths = ["tests"]`` in ``pyproject.toml`` and therefore runs
inside the existing required CI job. No new workflow and no new required status check
were added — a standalone workflow would have to be wired into branch protection
separately to gate anything.

Structure
---------
- **A (static, default-deny):** no module under ``src/`` may bind a consumer-group
  name from a string literal or f-string. This is the defect class itself, and it is
  fail-closed: a newly-added literal fails without anyone remembering to update a list.
- **B (real producers):** the group names the migrated call sites actually mint —
  obtained by importing those modules, not by re-deriving a surrogate — are authorized
  under every managed environment.
- **C (reserved prefixes):** every reserved prefix yields an authorized name when
  scoped, and refuses to render when unscoped (the bare prefix is unauthorized because
  the IAM glob requires the trailing separator).
- **D (matcher semantics):** the falsifier. The exact OMN-15639 defect names are
  rejected. A substring matcher would accept them (they contain ``onex.``) and would
  make this whole gate vacuous.
- **E (pin integrity):** the pinned pattern set still matches its recorded digest.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest

import omnibase_core
from omnibase_core.enums.enum_consumer_group_purpose import EnumConsumerGroupPurpose
from omnibase_core.enums.enum_reserved_group_prefix import EnumReservedGroupPrefix
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.util_consumer_group import (
    compute_consumer_group_id,
    compute_pattern_set_digest,
    derive_prefixed_group_id,
    derive_service_group_id,
    is_authorized_group_name,
    load_authorized_group_patterns,
    load_iam_pattern_document,
    load_managed_environments,
)
from omnibase_core.models.event_bus.model_consumer_group_scope import (
    ModelConsumerGroupScope,
)

SRC_ROOT = Path(omnibase_core.__file__).resolve().parent

# Keyword arguments whose value names a Kafka consumer group.
#
# Deliberately excludes the bare keyword ``group``: ``EventBusInmemory(group="default")``
# takes a source-header label, and ``runtime/transport/runtime_transport_conformance.py``
# is a pytest conformance suite that lives under ``src/`` and passes ``group="g-order"``
# and friends. Neither is a Kafka consumer group, and widening the keyword set to catch
# them would only manufacture an exclusion list.
_GROUP_KEYWORDS = frozenset({"group_id", "consumer_group", "kafka_group_id"})

# Dict-literal keys that carry a consumer group. ``"group.id"`` is the librdkafka
# config key: ``cli_run_node.py`` used ``Consumer({"group.id": f"onex-run-node-{...}"})``,
# which a keyword-only scan would miss entirely — that call site is the seam's own
# worked ephemeral example.
_GROUP_DICT_KEYS = frozenset({"group.id", "group_id", "consumer_group"})

# The exact names observed failing in the field, plus the bare reserved prefix.
# Every one of these MUST be rejected; each is a distinct way a lazy matcher passes.
_MUST_BE_UNAUTHORIZED = (
    # Substring trap: contains "onex." but does not begin with it.
    "runtime-local-HandlerDelegateSkill.__t.onex.cmd.omnimarket.delegate-skill.v1",
    # The literal at runtime_local.py:563 / :1195 before OMN-15639.
    "runtime-local-terminal",
    # The literal at runtime_local.py:1180 before OMN-15639.
    "runtime-local-HandlerDelegateSkill",
    # The dict-literal value at cli_run_node.py:213 before OMN-15639.
    "onex-run-node-9f2c0000-0000-4000-8000-000000000000",
    # Reserved prefix without its trailing separator: "pattern-b-broker-*" needs the "-".
    "pattern-b-broker",
    "phase5-msk-smoke",
    # Prefix-ish but not prefixed.
    "not-onex-dev.omnimarket.node.consume.v1",
    "",
    # Trailing newline: Python's `$` matches immediately before it, so an anchor of
    # `^...$` instead of `^...\\Z` would authorize this. MSK would not.
    "onex-dev.omnimarket.node.consume.v1\n",
    "onex-dev.omnimarket.node.consume.v1\n\n",
)

_SAMPLE_CORRELATION_ID = UUID("9f2c0000-0000-4000-8000-000000000000")

# The eight validation runtimes bind their consumer groups at MODULE level, so the
# env-parametrized tests below must reload them to observe a managed environment.
_VALIDATOR_RUNTIME_SLUGS = (
    "doc_content_scan",
    "hardcoded_topic",
    "local_paths",
    "localhost_url",
    "no_faked_boundary",
    "pin_hygiene",
    "private_ip",
    "todo_marker",
)


def _validator_runtime_modules() -> tuple[str, ...]:
    return tuple(
        f"omnibase_core.validation.{slug}.runtime_{slug}"
        for slug in _VALIDATOR_RUNTIME_SLUGS
    )


@pytest.fixture(autouse=True, scope="module")
def _restore_validator_module_state() -> Iterator[None]:
    """Reload the validation runtimes after this module runs.

    ``_real_producer_group_names`` reloads them under ``ENVIRONMENT=onex-dev`` to read
    the names they actually mint. ``monkeypatch`` restores the env var, but NOT the
    module-level ``_RUNNER_GROUP`` / ``_HANDLER_GROUP`` constants those reloads already
    recomputed — so without this teardown a later test in the same worker would see
    ``onex-dev.*`` groups instead of its own environment's, and the in-memory bus keys
    subscriptions by group id. ``runtime_local`` and ``cli_run_node`` resolve the
    environment lazily per call and need no cleanup.
    """
    import importlib

    yield
    for module_name in _validator_runtime_modules():
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])


# ---------------------------------------------------------------------------
# A — static default-deny scan
# ---------------------------------------------------------------------------


def _python_sources() -> Iterator[Path]:
    yield from sorted(SRC_ROOT.rglob("*.py"))


def _module_level_string_bindings(tree: ast.Module) -> dict[str, ast.expr]:
    """Map module-level names bound to a string literal or f-string.

    Without this, the eight validation runtimes escape the scan: they bind
    ``_RUNNER_GROUP: Final[str] = "validator-x-runner"`` at module level and then pass
    ``group_id=_RUNNER_GROUP``, so the keyword's value is a ``Name``, not a literal.
    """
    bindings: dict[str, ast.expr] = {}
    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        if value is None or not _is_string_valued(value):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value
    return bindings


def _is_string_valued(node: ast.expr) -> bool:
    """True for a ``str`` constant or an f-string.

    Scoped to string-valued expressions on purpose. ``model_event_bus_config.py:150``
    passes ``group_id=uuid4()`` — a UUID field, not a Kafka group. A blanket
    "the value must be a call to the canonical util" rule would force ``uuid4`` onto an
    allowlist, which weakens the gate. Restricting to string values has zero false
    positives here while still failing closed on any newly-added literal.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    return isinstance(node, ast.JoinedStr)


def _literal_group_bindings(path: Path) -> list[tuple[int, str]]:
    """Return ``(lineno, description)`` for every literal-valued group name in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_strings = _module_level_string_bindings(tree)
    findings: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg in _GROUP_KEYWORDS:
            if _is_string_valued(node.value):
                findings.append((node.value.lineno, f"{node.arg}=<string literal>"))
            elif isinstance(node.value, ast.Name) and node.value.id in module_strings:
                findings.append(
                    (
                        node.value.lineno,
                        f"{node.arg}={node.value.id} "
                        f"(module-level string constant at line "
                        f"{module_strings[node.value.id].lineno})",
                    )
                )
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if (
                    isinstance(key, ast.Constant)
                    and key.value in _GROUP_DICT_KEYS
                    and _is_string_valued(value)
                ):
                    findings.append((value.lineno, f'"{key.value}": <string literal>'))
    return findings


@pytest.mark.unit
def test_no_literal_consumer_group_names_in_src() -> None:
    """Default-deny: consumer-group names are derived, never written as literals.

    A literal group name is unauthorizable by construction — nothing forces it to lead
    with an IAM-matched environment token. Derivation through
    ``util_consumer_group`` is the only way the name is guaranteed to be authorized,
    so the absence of literals is the enforceable form of AC3.
    """
    violations: list[str] = []
    for path in _python_sources():
        for lineno, description in _literal_group_bindings(path):
            violations.append(
                f"{path.relative_to(SRC_ROOT.parent)}:{lineno}: {description}"
            )

    assert not violations, (
        "Consumer-group names must be derived via "
        "omnibase_core.event_bus.util_consumer_group, never written as string literals "
        "(OMN-15639: an ad-hoc literal is not matched by the MSK IAM pattern set and "
        "fails at the broker with GroupAuthorizationFailedError before publishing).\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# B — real producers, real names
# ---------------------------------------------------------------------------


def _real_producer_group_names(
    monkeypatch: pytest.MonkeyPatch, env: str
) -> dict[str, str]:
    """Import the migrated call sites under ``env`` and return the names they mint.

    Modules are re-imported after the environment is set so that module-level
    ``Final`` group constants are recomputed. These are the production symbols, not
    re-derived copies — a surrogate here would make the gate vacuous
    (``feedback_test_the_artifact_that_runs``).
    """
    import importlib

    monkeypatch.setenv("ENVIRONMENT", env)

    names: dict[str, str] = {}
    for module_name in _validator_runtime_modules():
        module = importlib.reload(importlib.import_module(module_name))
        names[f"{module_name}._RUNNER_GROUP"] = module._RUNNER_GROUP
        names[f"{module_name}._HANDLER_GROUP"] = module._HANDLER_GROUP

    runtime_local = importlib.reload(
        importlib.import_module("omnibase_core.runtime.runtime_local")
    )
    names["runtime_local.terminal"] = runtime_local.derive_runtime_local_group_id(
        runtime_local.TERMINAL_CONSUMER_NODE_NAME
    )
    # OMN-15660 run-scoped the terminal group for every correlated run, in host
    # mode as well as client mode — so this variant, not the bare one, is what
    # `onex delegate` now mints against MSK. An unauthorized name here is the
    # OMN-15639 failure mode again (GroupAuthorizationFailedError before publish),
    # so the gate has to see the shape that actually reaches the broker.
    names["runtime_local.terminal_run_scoped"] = (
        runtime_local.derive_runtime_local_group_id(
            f"{runtime_local.TERMINAL_CONSUMER_NODE_NAME}_run_"
            f"{_SAMPLE_CORRELATION_ID.hex[:12]}"
        )
    )
    names["runtime_local.handler"] = runtime_local.derive_runtime_local_group_id(
        "HandlerDelegateSkill"
    )

    cli_run_node = importlib.reload(
        importlib.import_module("omnibase_core.cli.cli_run_node")
    )
    names["cli_run_node.ephemeral"] = cli_run_node.derive_run_node_group_id(
        _SAMPLE_CORRELATION_ID
    )
    return names


@pytest.mark.unit
@pytest.mark.parametrize("env", load_managed_environments())
def test_real_producer_group_names_are_authorized(
    monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    """Every group name the migrated producers mint is IAM-authorized."""
    names = _real_producer_group_names(monkeypatch, env)
    assert names, "no producer names collected — the scan would be vacuous"

    unauthorized = {
        site: name for site, name in names.items() if not is_authorized_group_name(name)
    }
    assert not unauthorized, (
        f"consumer-group names minted for managed environment {env!r} are not matched "
        f"by any pattern in {list(load_authorized_group_patterns())}:\n"
        + "\n".join(f"  {site}: {name}" for site, name in sorted(unauthorized.items()))
    )


@pytest.mark.unit
@pytest.mark.parametrize("env", load_managed_environments())
def test_managed_environment_token_leads_and_is_authorized(env: str) -> None:
    """Structural argument behind assertion B: authorization is decided by the env token.

    Identity-derived names lead with ``"<env>."``. If that prefix is itself authorized,
    every derived name under that environment is authorized regardless of service or
    node name. Adding an environment to ``managed_environments`` without matching IAM
    coverage therefore fails here at CI time, not at runtime.
    """
    derived = compute_consumer_group_id(
        env=env,
        service="omnimarket",
        node_name="delegate_skill",
        version="v1",
        purpose=EnumConsumerGroupPurpose.CONSUME,
    )
    assert derived.startswith(f"{env}."), (
        f"identity-derived group {derived!r} does not lead with the environment token"
    )
    assert is_authorized_group_name(derived), (
        f"managed environment {env!r} has no IAM coverage: {derived!r} is matched by "
        f"none of {list(load_authorized_group_patterns())}"
    )


@pytest.mark.unit
@pytest.mark.parametrize("env", load_managed_environments())
@pytest.mark.parametrize("purpose", list(EnumConsumerGroupPurpose))
def test_every_purpose_stays_authorized(
    env: str, purpose: EnumConsumerGroupPurpose
) -> None:
    """Purpose is a group-ID component; no purpose value may break authorization."""
    derived = compute_consumer_group_id(
        env=env,
        service="omnibase_core",
        node_name="node",
        version="v1",
        purpose=purpose,
    )
    assert is_authorized_group_name(derived)


@pytest.mark.unit
@pytest.mark.parametrize("env", load_managed_environments())
def test_scoped_names_stay_authorized(
    monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    """Topic and instance scoping must not displace the leading environment token."""
    monkeypatch.setenv("ENVIRONMENT", env)
    scoped = derive_service_group_id(
        "delegate_skill",
        service="omnimarket",
        scope=ModelConsumerGroupScope(
            topic="onex.cmd.omnimarket.delegate-skill.v1",
            ephemeral_tag="terminal",
            correlation_id=_SAMPLE_CORRELATION_ID,
        ),
    )
    assert is_authorized_group_name(scoped), scoped


# ---------------------------------------------------------------------------
# C — reserved prefixes
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("prefix", list(EnumReservedGroupPrefix))
def test_reserved_prefix_with_scope_is_authorized(
    prefix: EnumReservedGroupPrefix,
) -> None:
    """A scoped reserved-prefix name is authorized, and matches its declared glob."""
    derived = derive_prefixed_group_id(
        prefix,
        ModelConsumerGroupScope(
            ephemeral_tag="terminal", correlation_id=_SAMPLE_CORRELATION_ID
        ),
    )
    assert derived.startswith(f"{prefix.value}{prefix.separator()}")
    assert is_authorized_group_name(derived), derived
    assert prefix.authorized_glob() in load_authorized_group_patterns(), (
        f"reserved prefix {prefix.value!r} declares glob "
        f"{prefix.authorized_glob()!r}, which is absent from the pinned IAM pattern set"
    )


@pytest.mark.unit
@pytest.mark.parametrize("prefix", list(EnumReservedGroupPrefix))
def test_reserved_prefix_without_scope_refuses(
    prefix: EnumReservedGroupPrefix,
) -> None:
    """Fail-closed: the bare prefix is unauthorized, so minting it must raise.

    ``pattern-b-broker-*`` requires the trailing ``-``. Rendering the bare
    ``pattern-b-broker`` would produce a name the broker refuses, so the derivation
    refuses first rather than deferring the failure to runtime.
    """
    assert not is_authorized_group_name(prefix.value), (
        f"bare prefix {prefix.value!r} is authorized — the trailing-separator "
        f"requirement of {prefix.authorized_glob()!r} is not being enforced"
    )
    with pytest.raises(ModelOnexError, match="requires a non-empty scope"):
        derive_prefixed_group_id(prefix, ModelConsumerGroupScope())


# ---------------------------------------------------------------------------
# D — matcher semantics (the falsifier)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("group_name", _MUST_BE_UNAUTHORIZED)
def test_known_unauthorized_names_are_rejected(group_name: str) -> None:
    """The matcher does whole-name glob matching, not substring matching.

    ``runtime-local-HandlerDelegateSkill.__t.onex.cmd...`` contains ``onex.`` and would
    pass a substring test while still failing at the broker. If this test ever passes
    trivially, the gate above is vacuous.
    """
    assert not is_authorized_group_name(group_name), (
        f"{group_name!r} must NOT be authorized — it is (or is shaped like) a name "
        f"the MSK broker rejected with GroupAuthorizationFailedError"
    )


@pytest.mark.unit
def test_wildcard_is_the_only_metacharacter() -> None:
    """``.`` in a pattern is a literal, not a regex any-char.

    ``onex.*`` must not match ``onexZfoo``; if it did, the matcher would be a regex
    evaluator and the authorized surface would be far wider than the IAM policy's.
    """
    assert is_authorized_group_name("onex.anything")
    assert not is_authorized_group_name("onexZanything")
    assert not is_authorized_group_name("onex")


@pytest.mark.unit
def test_match_is_anchored_against_a_trailing_newline() -> None:
    """Regression: the end anchor must be ``\\Z``, not ``$``.

    Python's ``$`` matches immediately before a trailing newline, so ``^onex-dev\\..*$``
    accepts ``"onex-dev.svc\\n"``. MSK matches the whole group name with no such
    allowance, so a ``$`` anchor authorizes names the broker would refuse.
    """
    assert is_authorized_group_name("onex-dev.svc.node.consume.v1")
    assert not is_authorized_group_name("onex-dev.svc.node.consume.v1\n")
    assert not is_authorized_group_name("onex-dev.svc\nnot-authorized")


# ---------------------------------------------------------------------------
# E — pin integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pinned_pattern_set_matches_recorded_digest() -> None:
    """The pinned mirror still matches its recorded digest and expected contents.

    ``load_iam_pattern_document`` already fails closed on digest drift; this asserts it
    explicitly and pins the exact six patterns, so silently widening the authorized
    surface requires editing this test and is visible in review.
    """
    document = load_iam_pattern_document()
    patterns = load_authorized_group_patterns()

    assert patterns == (
        "onex-dev.*",
        "local.runtime_config.*",
        "pattern-b-broker-*",
        "onex.*",
        "omninode.*",
        "phase5-msk-smoke-*",
    )
    assert document.pattern_set_sha256 == compute_pattern_set_digest(patterns)
    assert (
        document.source.file_sha256
        == "46b1742a195afffc5b6291d51d2be28b941ef355b79983e12a3c719cee5fd528"  # pragma: allowlist secret
    )
    assert document.source.path == ("aws/cluster-dev/managed-data-plane.auto.tfvars")


@pytest.mark.unit
def test_pinned_pattern_file_is_git_tracked_and_ships_in_the_wheel() -> None:
    """The mirror must be tracked by git and inside a packaged directory.

    Regression guard for a real miss on this ticket: the file was first placed at
    ``src/omnibase_core/data/consumer_group_iam_patterns.yaml``, which
    ``.gitignore:251`` (``data/``, for Docker runtime data dirs) silently excluded.
    Every local run passed against the untracked working-tree copy while the file was
    absent from the commit — the gate would have shipped green and then failed at
    collection on any fresh checkout. Asserting git-trackedness here makes that
    failure mode impossible to reintroduce.

    ``[tool.hatch.build] artifacts`` globs ``src/omnibase_core/**/*.yaml``, so any
    tracked YAML under the package ships in the wheel; being tracked is the whole
    remaining condition.
    """
    import os
    import subprocess

    from omnibase_core.validators.no_unguarded_git_subprocess import (
        scrub_git_location_env,
    )

    resource_path = SRC_ROOT / "contracts" / "consumer_group_iam_patterns.yaml"
    assert resource_path.is_file(), resource_path

    repo_root = SRC_ROOT.parent.parent
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(resource_path)],
        cwd=repo_root,
        capture_output=True,
        check=False,
        env=scrub_git_location_env(os.environ),
    )
    assert tracked.returncode == 0, (
        f"{resource_path} is not tracked by git — it would be missing from a fresh "
        f"checkout and from the wheel. stderr: {tracked.stderr.decode().strip()}"
    )
