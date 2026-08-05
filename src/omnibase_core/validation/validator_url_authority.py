# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorUrlAuthority — reject new URL/endpoint literals outside contracts.

Part of OMN-12803 (PR-2, the enforcement gate). Every URL and ``*_URL`` /
``*_ENDPOINT`` env read must resolve from a contract (routing authority /
integration catalog), not a literal string or a bare env read.

Detects five classes of violations. The first four are Python-source-only;
the fifth (``msk-direct-broker-endpoint``, OMN-15692) additionally scans
non-Python on-prem-facing config/script files (see below):

1. **public-https-literal** — a quoted ``https://`` URL targeting a public
   host with a dotted TLD.  Excludes localhost/loopback, example placeholders,
   VCS display permalinks, and JSON-schema refs (audit cosmetic-exclusion
   class 1K).

2. **env-url-read** — ``os.environ[...]`` subscript or ``os.environ.get(...)``
   call whose variable NAME ends in ``_URL`` or ``_ENDPOINT``.  API-key /
   token / secret variable names do NOT end in those suffixes and remain legal.

3. **url-const-assignment** — module-level constant assignment whose name
   ends in ``URL`` or ``ENDPOINT``, sourced from ``os.environ`` or a bare
   ``https://`` literal.

4. **localhost-literal** (OMN-13480) — a hardcoded ``http(s)://`` loopback
   connection-target literal (``localhost``, ``127.x.x.x``, ``0.0.0.0``,
   ``[::1]``) that is NOT a ``*_URL`` / ``*_ENDPOINT`` constant.  The
   public-https rule deliberately skips localhost (no dotted TLD), so a bare
   loopback literal passed directly to an HTTP client call was otherwise
   invisible.  A connection target should resolve from the routing authority,
   not a hardcoded loopback literal.

5. **msk-direct-broker-endpoint** (OMN-15692, operator ruling 2026-08-04:
   "nothing in either .200 or .201 should be contacting MSK directly,
   everything should be going through the gateway") — a literal MSK broker
   hostname (``_MSK_BROKER_HOSTNAME`` — an ``*.kafka.<region>[.]amazonaws
   [.]com``-shaped host, any AWS region) appearing **anywhere** on a
   non-comment line, OR the raw SNI-passthrough bastion IP on its own
   (``_MSK_BASTION_IP``), appearing in an on-prem-facing config/script file.
   (Deliberately not spelled out as a bare literal here — this docstring is
   itself scanned, and an unbroken literal would trip the very rule it
   documents; see the pattern constants for the exact strings.)

   The hostname trigger is deliberately **not** gated on a co-occurring port
   literal. An earlier revision required the SASL_SSL/MSK-IAM port (9098 or
   9096) on the *same line* as the hostname; that missed the ordinary
   split-key config shape (``MSK_HOST:``/``MSK_PORT:`` on separate lines —
   the default shape for Docker Compose and ``.env`` files, not an edge
   case), a hostname with no port literal at all, and any other broker port
   (e.g. plaintext/TLS 9092/9094). The hostname literal alone is already an
   unambiguous, single-purpose DNS name for one live AWS resource — its mere
   presence in a non-comment, non-test line of a scanned config/script file
   is sufficient evidence of a direct-MSK reference regardless of port or
   which line the port (if any) appears on.

   Unlike rules 1-4, this rule also scans **non-Python** files
   (``.yaml``/``.yml``/``.sh``/``.env``/``.cfg``/``.conf``/``.toml``/``.ini``/
   ``.json``/``.tf`` in addition to ``.py`` — see ``_MSK_SCAN_SUFFIXES`` —
   plus, by basename rather than suffix, the extensionless ``.env`` file
   itself, the ``.env.<profile>`` family (``.env.local``, ``.env.production``,
   ...), and ``Dockerfile``/``Dockerfile.<variant>`` — see
   ``_is_msk_scannable``, which a pure suffix check cannot select), because
   the on-prem surface it targets (Docker Compose ``extra_hosts``, shell
   profiles, SSH config, env files, Terraform, Dockerfiles) is overwhelmingly
   non-Python. It is intentionally narrower in *match* scope than rules 1-4
   are in *file* scope: only the two literal patterns above trigger it, so
   widening the scanned file set does not import rules 1-4's broader (and
   here, un-triaged) match surface.

   **Not suppressible.** Rules 1-4 accept ``# url-authority-ok: <reason>`` as
   a free-text escape hatch. Rule 5 mechanizes a hard operator ruling with no
   stated exception path ("nothing ... should be contacting MSK directly"),
   so a self-authored justification comment must not be able to waive it —
   the same self-judgement-is-not-evidence reasoning CLAUDE.md rule 10 was
   hardened around for `[skip-*]` tokens. ``scan_source`` enforces this by
   checking the suppression annotation only for non-rule-5 matches.

Ratchet (OMN-12818, mirrors OMN-12791 receipt-honesty gate): existing
violations are grandfathered by content fingerprint (sha256 of {repo, path,
normalized-snippet}).  Only NEW fingerprints fail the gate.  The baseline may
only shrink — the ``--update-baseline`` / ``--seed`` modes enforce the
burn-down invariant.

Baseline per repo lives at:
``src/omnibase_core/validation/baselines/url_authority_baseline.json``

Usage Examples:
    Programmatic usage::

        from omnibase_core.validation import ValidatorUrlAuthority

        v = ValidatorUrlAuthority()
        result = v.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI — pre-commit (staged files)::

        python -m omnibase_core.validation.validator_url_authority file1.py ...

    CLI — full repo scan (CI)::

        python -m omnibase_core.validation.validator_url_authority --all \\
            --repo omnibase_core --repo-root .

    CLI — seed / update baseline::

        python -m omnibase_core.validation.validator_url_authority \\
            --seed --repo omnibase_core --repo-root .

Suppression:
    Add ``# url-authority-ok: <reason>`` on the offending line (rules 1-4 only).
    Config-PATH env reads annotated with ``# contract-config-ok:`` are also exempt.
    Rule 5 (msk-direct-broker-endpoint, OMN-15692) is NOT suppressible by either
    annotation — it mechanizes a hard operator ruling with no stated exception
    path; fix the reference, do not annotate around it.

Migration debt tickets:
    - omnibase_core: OMN-12806
    - omnibase_infra: OMN-12807
    - other repos: OMN-12808

Schema Version:
    v1.0.0 - Initial version (OMN-12818)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import ClassVar, Final

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_url_authority_violation import (
    ModelUrlAuthorityViolation,
)
from omnibase_core.validation.validator_base import ValidatorBase

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# 1. Public HTTPS endpoint literal.  Connection-target scope only: excludes
#    localhost/loopback, example/placeholder hosts, VCS display permalinks,
#    JSON-schema refs, and raw-content refs (audit cosmetic-exclusion class 1K).
_PUBLIC_HTTPS_LITERAL: Final[re.Pattern[str]] = re.compile(
    r"""["']https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:[/"':]|$)""",
    re.IGNORECASE,
)

# Hosts/paths that are NOT connection targets (excluded from the public-https rule).
_NON_ENDPOINT_MARKERS: Final[tuple[str, ...]] = (
    "example.com",
    "example.org",
    ".invalid",
    "://github.com/",  # display permalinks; api.github.com IS matched
    "://gitlab.com/",
    "raw.githubusercontent.com",
    "$schema",
    "schemastore.org",
    "json-schema.org",
    "w3.org",
    "spdx.org",
)

# 2. ``*_URL`` / ``*_ENDPOINT`` env read.
_ENV_URL_READ: Final[re.Pattern[str]] = re.compile(
    r"""os\.environ(?:\.get\(\s*|\[\s*)["'][A-Z0-9_]*(?:_URL|_ENDPOINT)["']""",
)

# 3. ``*_URL`` / ``*_ENDPOINT`` module-constant assignment.
_CONST_URL_FROM_ENV: Final[re.Pattern[str]] = re.compile(
    r"""^[A-Z0-9_]*(?:URL|ENDPOINT)[A-Z0-9_]*\s*=\s*os\.environ""",
)
_CONST_URL_FROM_LITERAL: Final[re.Pattern[str]] = re.compile(
    r"""^[A-Z0-9_]*(?:URL|ENDPOINT)[A-Z0-9_]*\s*=\s*["']https?://""",
)

# 4. Hardcoded localhost / loopback connection-target literal (OMN-13480).
#    The public-https rule deliberately skips localhost (no dotted TLD), and
#    a bare loopback literal that is NOT assigned to a ``*_URL`` / ``*_ENDPOINT``
#    constant is otherwise invisible — e.g. ``httpx.get("http://localhost:9000")``.  # onex-allow-internal-ip: doc example, not a real endpoint (pre-existing, OMN-15692 remediation)
#    A connection target should resolve from the routing authority, not a
#    hardcoded loopback literal. Matches http(s):// to:
#      * ``localhost`` (optionally with a ``:port``)
#      * IPv4 loopback ``127.x.x.x`` and the wildcard bind address ``0.0.0.0``
#      * IPv6 loopback ``[::1]``
_LOCALHOST_LITERAL: Final[re.Pattern[str]] = re.compile(
    r"""["']https?://(?:localhost|127\.\d{1,3}\.\d{1,3}\.\d{1,3}|0\.0\.0\.0|\[::1\])(?:[:/?#"']|$)""",
    re.IGNORECASE,
)

# 5. Direct MSK broker endpoint / bastion IP (OMN-15692, ruling 39: on-prem
#    hosts must go through the gateway, never a direct MSK broker connection).
#    Two independent triggers, either is sufficient:
#      * an MSK broker hostname, on its own — NOT gated on a co-occurring
#        port literal (see the module docstring rule-5 section for why: a
#        port-gate misses split-key configs, no-port hostnames, and any port
#        other than 9098/9096). Any AWS region, not just us-east-1.
#      * the raw SNI-passthrough bastion IP, on its own, regardless of port
#        (the on-prem /etc/hosts and Docker `extra_hosts` overrides that this
#        rule exists to catch map the hostname straight to this IP with no
#        port literal at all).
#    Both patterns end with a negative-lookahead token boundary
#    (`(?![a-z0-9.-])` / `(?![0-9])`) so a longer hostname/IP that merely
#    contains the MSK endpoint as a substring — e.g.
#    ``amazonaws.com.example`` or ``100.53.215.198.example`` — does not
#    false-positive (CodeRabbit round-#3, defect: unbounded substring match).
_MSK_BROKER_HOSTNAME: Final[re.Pattern[str]] = re.compile(
    r"""[a-z0-9][a-z0-9.-]*\.kafka\.[a-z0-9-]+\.amazonaws\.com(?![a-z0-9.-])""",
    re.IGNORECASE,
)
_MSK_BASTION_IP: Final[re.Pattern[str]] = re.compile(
    r"""(?<![0-9.])100\.53\.215\.198(?![0-9.])"""
)

RULE_MSK_DIRECT_BROKER: Final[str] = "msk-direct-broker-endpoint"

# File suffixes scanned for the msk-direct-broker-endpoint rule ONLY (rules
# 1-4 stay Python-only via scan_tree's existing *.py glob). On-prem-facing
# config/script surfaces are overwhelmingly non-Python.
_MSK_SCAN_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".py",
        ".yaml",
        ".yml",
        ".sh",
        ".env",
        ".cfg",
        ".conf",
        ".toml",
        ".ini",
        ".json",
        ".tf",
    }
)

# Basename-based selection for files a pure suffix check misses entirely
# (OMN-15692 verifier round #3 — proven evasions):
#   * ``.env`` itself has an EMPTY ``Path.suffix`` — pathlib treats a leading
#     dot as part of the stem, not a suffix, so ``Path(".env").suffix ==
#     ""``. A pure suffix filter silently drops it.
#   * the ``.env.<profile>`` family (``.env.local``, ``.env.production``, ...)
#     has a suffix equal to the PROFILE (``.local``, ``.production``), not
#     ``.env`` — also invisible to a suffix check.
#   * ``Dockerfile`` (and the ``Dockerfile.<variant>`` family, e.g.
#     ``Dockerfile.gateway``) has no extension at all.
_MSK_SCAN_EXACT_BASENAMES: Final[frozenset[str]] = frozenset({".env", "Dockerfile"})
_MSK_SCAN_BASENAME_PREFIXES: Final[tuple[str, ...]] = (".env.", "Dockerfile.")


def _is_msk_scannable(path: Path) -> bool:
    """True when ``path`` is in-scope for the msk-direct-broker-endpoint
    file-selection surface (rule 5 only — see module docstring). Suffix
    membership covers the ordinary case; the basename checks close the
    extensionless-dotfile / no-extension gaps a pure suffix filter cannot
    see (OMN-15692 evasion fix — see ``_MSK_SCAN_EXACT_BASENAMES`` above).
    """
    if path.suffix in _MSK_SCAN_SUFFIXES:
        return True
    name = path.name
    if name in _MSK_SCAN_EXACT_BASENAMES:
        return True
    return any(name.startswith(prefix) for prefix in _MSK_SCAN_BASENAME_PREFIXES)


# Suppression annotations.
_SUPPRESS_ANNOTATION: Final[str] = "# url-authority-ok:"
_CONFIG_PATH_ANNOTATION: Final[str] = "# contract-config-ok:"

# Authority files: the URL literals inside them ARE canonical — skip.
_AUTHORITY_PATH_SUFFIXES: Final[tuple[str, ...]] = (
    "configs/bifrost_delegation.yaml",
    "contracts/integrations/catalog.yaml",
)

# Rule identifiers (must match the validation contract).
RULE_PUBLIC_HTTPS: Final[str] = "public-https-literal"
RULE_ENV_URL_READ: Final[str] = "env-url-read"
RULE_CONST_ASSIGNMENT: Final[str] = "url-const-assignment"
RULE_LOCALHOST_LITERAL: Final[str] = "localhost-literal"

# Directories excluded from full-tree scans.
_EXCLUDED_PARTS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        "dod_receipts",
        "evidence",
        ".onex_state",
    }
)

# Default baseline path (relative to this file's parent → baselines/ subdir).
_DEFAULT_BASELINE: Final[Path] = (
    Path(__file__).parent / "baselines" / "url_authority_baseline.json"
)


# ---------------------------------------------------------------------------
# Fingerprinting helpers
# ---------------------------------------------------------------------------


def _normalize(snippet: str) -> str:
    """Normalize the offending snippet for a stable, line-number-independent hash."""
    return re.sub(r"\s+", " ", snippet.strip())


def make_fingerprint(repo: str, path: str, snippet: str) -> str:
    """sha256({repo}\\0{path}\\0{normalized-snippet}) — survives unrelated edits."""
    payload = f"{repo}\0{path}\0{_normalize(snippet)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Per-line matching helpers
# ---------------------------------------------------------------------------


def _is_authority_path(path: str) -> bool:
    """True when the file IS a URL authority (its literals are canonical)."""
    norm = path.replace("\\", "/")
    return any(norm.endswith(suffix) for suffix in _AUTHORITY_PATH_SUFFIXES)


def _is_test_path(path: str) -> bool:
    """True when ``path`` is a real test file/directory — NOT merely a path
    that happens to contain "test" as a bare substring (OMN-15692 verifier
    round #3 evasion fix). A bare-substring check waived real, non-test
    on-prem-facing files whose name coincidentally contains the four
    characters "test": ``deploy/latest.yaml`` ("la-TEST-.yaml"),
    ``docker/stability-test/**`` (an infra deployment LANE name, not test
    code), and ``attestation.yaml`` ("at-TEST-ation.yaml") all evaded
    detection entirely under the old check. Anchored to real test-path
    segments only:
      * a path component that IS (exactly, case-insensitively) ``test`` or
        ``tests`` — e.g. ``tests/x.py``, ``some/test/y.yaml``.
      * a basename that starts with ``test_`` (``test_foo.py``) or ends
        with ``_test`` before its final extension (``foo_test.py``).
      * the exact basename ``conftest.py``.
    A hyphenated/compound segment such as ``stability-test`` does NOT match
    — those are real deployment-lane paths (e.g. the ``stability-test``
    runtime lane) that MUST stay in-scope for this gate.
    """
    norm = path.replace("\\", "/")
    parts = [p for p in norm.split("/") if p]
    if not parts:
        return False
    basename = parts[-1]
    if basename == "conftest.py":
        return True
    if any(part.lower() in ("test", "tests") for part in parts[:-1]):
        return True
    stem = basename.rsplit(".", 1)[0] if "." in basename else basename
    lowered_stem = stem.lower()
    return lowered_stem.startswith("test_") or lowered_stem.endswith("_test")


def _is_connection_target(raw_line: str) -> bool:
    """True when an https literal is a real connection endpoint, not a placeholder."""
    lowered = raw_line.lower()
    if any(marker in lowered for marker in _NON_ENDPOINT_MARKERS):
        return False
    # Heuristic: the line is (part of) a JSON-object literal, not an assignment.
    stripped = raw_line.strip()
    if stripped.startswith(("{", '{"')) or '":{"' in stripped:
        return False
    return True


def _match_rule(raw_line: str, stripped: str) -> str | None:
    """Return the first matching rule id for a line, or None."""
    if _ENV_URL_READ.search(raw_line):
        return RULE_ENV_URL_READ
    if _CONST_URL_FROM_ENV.match(stripped) or _CONST_URL_FROM_LITERAL.match(stripped):
        return RULE_CONST_ASSIGNMENT
    if _PUBLIC_HTTPS_LITERAL.search(raw_line) and _is_connection_target(raw_line):
        return RULE_PUBLIC_HTTPS
    # Bare loopback connection-target literal not captured by the rules above
    # (the public-https rule skips localhost; this is not a *_URL constant).
    if _LOCALHOST_LITERAL.search(raw_line) and _is_connection_target(raw_line):
        return RULE_LOCALHOST_LITERAL
    return None


def _match_msk_rule(raw_line: str) -> str | None:
    """Return RULE_MSK_DIRECT_BROKER when the line carries a direct-MSK
    literal (OMN-15692), else None.

    Two independent triggers, either is sufficient:
      * an MSK broker hostname, on its own — NOT gated on a co-occurring
        port literal. A port-gate misses the ordinary split-key config shape
        (hostname and port declared on separate lines/keys — the default
        Docker Compose / .env shape, not an edge case), a hostname with no
        port literal anywhere, and any broker port other than 9098/9096
        (e.g. 9092/9094). The hostname alone is an unambiguous single-purpose
        DNS literal for one live AWS resource, so its presence is sufficient.
      * the raw bastion IP on its own (the host-level and container-level
        overrides this rule targets map hostname -> bare IP with no port
        literal at all, e.g. Docker Compose ``extra_hosts``)

    Extension-agnostic by design — callers decide which file suffixes route
    through this function (see ``_MSK_SCAN_SUFFIXES``).
    """
    if _MSK_BASTION_IP.search(raw_line):
        return RULE_MSK_DIRECT_BROKER
    if _MSK_BROKER_HOSTNAME.search(raw_line):
        return RULE_MSK_DIRECT_BROKER
    return None


# ---------------------------------------------------------------------------
# Source scanner
# ---------------------------------------------------------------------------


def scan_source(repo: str, path: str, source: str) -> list[ModelUrlAuthorityViolation]:
    """Scan one source file's text for url-authority violations.

    Test files and authority files are skipped.  Lines carrying
    ``# url-authority-ok:`` or (for env reads) ``# contract-config-ok:`` are
    suppressed for rules 1-4.  Rule 5 (msk-direct-broker-endpoint) is NOT
    suppressible by either annotation — see the module docstring and
    ``RULE_MSK_DIRECT_BROKER``.  Returns at most one violation per line.

    Rules 1-4 (public-https-literal, env-url-read, url-const-assignment,
    localhost-literal) only apply to ``.py`` sources — their patterns are
    Python-syntax-specific (``os.environ[...]``, module-constant assignment).
    Rule 5 (msk-direct-broker-endpoint, OMN-15692) applies regardless of
    file extension — the caller decides which files reach this function
    (see ``_MSK_SCAN_SUFFIXES`` / ``scan_tree``).

    Args:
        repo: Repo name used in fingerprints (e.g. ``"omnibase_core"``).
        path: Repo-relative path for fingerprints (e.g. ``"src/pkg/file.py"``).
        source: Full source text of the file.

    Returns:
        List of violations found in the file.
    """
    if _is_test_path(path) or _is_authority_path(path):
        return []
    is_python = path.endswith(".py")
    # Line-comment conventions vary by file type (CodeRabbit round-#3
    # finding): '#' is universal across every scanned suffix, but '.ini'/
    # '.cfg' also use ';' and '.tf' also uses '//' plus '/* ... */' block
    # comments. Rule 5 is non-suppressible, so a hostname/IP literal inside
    # a documentation span in ANY of these must not become an unfixable
    # gate failure.
    is_ini_or_cfg = path.endswith((".ini", ".cfg"))
    is_tf = path.endswith(".tf")

    violations: list[ModelUrlAuthorityViolation] = []
    # Multi-line documentation-span state, carried across the loop:
    #   * py_docstring_delim: the delimiter ('"""' or "'''") of a currently
    #     OPEN Python triple-quoted docstring, or None when not inside one.
    #   * in_tf_block_comment: True while inside an open Terraform /* ... */
    #     block comment.
    # A prior revision only recognized a docstring/comment by checking
    # whether EACH line individually starts with '#'/'"""'/"'''" — so an
    # interior line of a multi-line docstring (which starts with ordinary
    # text, not a delimiter) was still scanned as code. Tracking open/close
    # state here closes that gap.
    py_docstring_delim: str | None = None
    in_tf_block_comment = False
    for index, raw_line in enumerate(source.splitlines(), start=1):
        stripped = raw_line.strip()

        if py_docstring_delim is not None:
            # Inside a multi-line Python docstring: this whole line is
            # documentation, not code — skip it regardless of content, and
            # check whether it closes the block.
            if py_docstring_delim in stripped:
                py_docstring_delim = None
            continue

        if in_tf_block_comment:
            if "*/" in stripped:
                in_tf_block_comment = False
            continue

        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if is_ini_or_cfg and stripped.startswith(";"):
            continue
        if is_tf and stripped.startswith("//"):
            continue
        if is_tf and stripped.startswith("/*"):
            if "*/" not in stripped[2:]:
                in_tf_block_comment = True
            continue
        if is_python and stripped.startswith(('"""', "'''")):
            delim = stripped[:3]
            if delim not in stripped[3:]:
                # Opens here, does not close on this same line.
                py_docstring_delim = delim
            continue

        rule = _match_rule(raw_line, stripped) if is_python else None
        if rule == RULE_ENV_URL_READ and _CONFIG_PATH_ANNOTATION in raw_line:
            # Config-PATH env reads annotated with contract-config-ok are exempt.
            rule = None
        if rule is None:
            rule = _match_msk_rule(raw_line)
        if rule is None:
            continue

        # Suppression applies to rules 1-4 only. Rule 5 mechanizes a hard
        # operator ruling with no exception path (OMN-15692) — a free-text
        # justification comment must not be able to waive it (see module
        # docstring "Not suppressible" note).
        if rule != RULE_MSK_DIRECT_BROKER and _SUPPRESS_ANNOTATION in raw_line:
            continue

        snippet = stripped[:200]
        violations.append(
            ModelUrlAuthorityViolation(
                repo=repo,
                path=path,
                line=index,
                rule=rule,
                snippet=snippet,
                fingerprint=make_fingerprint(repo, path, snippet),
            )
        )
    return violations


def scan_tree(repo: str, repo_root: Path) -> list[ModelUrlAuthorityViolation]:
    """Scan ``repo_root`` for url-authority violations.

    ``.py`` files are scanned for all five rules. Non-``.py`` files selected
    by ``_is_msk_scannable`` — suffix membership in ``_MSK_SCAN_SUFFIXES``
    (``.yaml``/``.yml``/``.sh``/``.env``/``.cfg``/``.conf``/``.toml``/
    ``.ini``/``.json``/``.tf``) OR a basename match for the extensionless
    ``.env``/``.env.<profile>``/``Dockerfile``/``Dockerfile.<variant>``
    families (OMN-15692 evasion fix — a pure suffix glob cannot see these) —
    are scanned for rule 5 (msk-direct-broker-endpoint, OMN-15692) only.
    ``scan_source`` enforces the rules-1-4-vs-rule-5 split via its
    ``is_python`` gate, so widening the file set here does not resurface
    rules 1-4's un-triaged match surface on non-Python files.

    Paths in the returned violations are repo-relative so fingerprints are
    machine-independent.  Excludes vendored, build, test, and evidence dirs.

    Args:
        repo: Repo name for fingerprints.
        repo_root: Absolute path to the repository root.

    Returns:
        Sorted list of violations.
    """
    violations: list[ModelUrlAuthorityViolation] = []
    candidates: list[Path] = [
        p for p in repo_root.rglob("*") if p.is_file() and _is_msk_scannable(p)
    ]
    for candidate in sorted(set(candidates)):
        if set(candidate.parts) & _EXCLUDED_PARTS:
            continue
        try:
            rel = str(candidate.relative_to(repo_root))
        except ValueError:
            rel = str(candidate)
        if _is_test_path(rel):
            continue
        try:
            source = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        violations.extend(scan_source(repo, rel, source))
    return violations


# ---------------------------------------------------------------------------
# Ratchet baseline helpers
# ---------------------------------------------------------------------------


def load_baseline(baseline_path: Path) -> set[str]:
    """Load the frozen fingerprint set from the baseline JSON.  Missing file = empty."""
    if not baseline_path.exists():
        return set()
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    entries = data.get("violations", []) if isinstance(data, dict) else []
    return {
        str(e["fingerprint"])
        for e in entries
        if isinstance(e, dict) and "fingerprint" in e
    }


def partition_against_baseline(
    violations: list[ModelUrlAuthorityViolation],
    baseline_fingerprints: set[str],
) -> tuple[list[ModelUrlAuthorityViolation], list[ModelUrlAuthorityViolation]]:
    """Split violations into (new, grandfathered) by baseline membership.

    Returns:
        Tuple of (new_violations, grandfathered_violations).  New violations
        fail the gate; grandfathered ones pass.
    """
    new: list[ModelUrlAuthorityViolation] = []
    grandfathered: list[ModelUrlAuthorityViolation] = []
    for v in violations:
        if v.fingerprint in baseline_fingerprints:
            grandfathered.append(v)
        else:
            new.append(v)
    return new, grandfathered


def assert_baseline_shrinks_only(before: set[str], after: set[str]) -> None:
    """Anti-gaming: the baseline may shrink (burn-down) but never grow.

    Raises:
        ValueError: If ``after`` introduces fingerprints not present in ``before``.
    """
    added = after - before
    if added:
        raise ValueError(  # error-ok: function-boundary validation guard (anti-gaming baseline check, CLI-surfaced)
            "url-authority baseline grew: "
            f"{len(added)} new fingerprint(s) added. The baseline is burn-down only "
            "— fix the violation or annotate with # url-authority-ok:, never add it "
            "to the baseline. Offending fingerprints: "
            f"{sorted(added)[:5]}"
        )


def serialize_baseline(
    violations: list[ModelUrlAuthorityViolation],
) -> dict[str, object]:
    """Build the on-disk baseline document — sorted, deterministic, fingerprint-keyed."""
    entries: list[dict[str, str]] = sorted(
        (
            {
                "repo": v.repo,
                "path": v.path,
                "rule": v.rule,
                "fingerprint": v.fingerprint,
            }
            for v in violations
        ),
        key=lambda e: (e["repo"], e["path"], e["fingerprint"]),
    )
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for e in entries:
        fp = e["fingerprint"]
        if fp in seen:
            continue
        seen.add(fp)
        unique.append(e)
    return {"schema_version": "1.0.0", "count": len(unique), "violations": unique}


# ---------------------------------------------------------------------------
# ValidatorBase subclass
# ---------------------------------------------------------------------------


class ValidatorUrlAuthority(ValidatorBase):
    """Reject NEW URL/endpoint literals outside contracts.

    Wraps the url-authority ratchet as a standard ValidatorBase subclass so it
    participates in the ecosystem-wide validation pipeline (pre-commit hooks,
    CI required checks, cross-repo wiring).

    The validator ONLY reports violations that are NEW (not in the per-repo
    baseline).  Existing (grandfathered) violations are silently skipped until
    they are fixed and the baseline is shrunk.

    See migration debt tickets OMN-12806 (omnibase_core), OMN-12807
    (omnibase_infra), OMN-12808 (other repos).
    """

    validator_id: ClassVar[str] = "url_authority"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        repo: str = "omnibase_core",
        baseline_path: Path | None = None,
        repo_root: Path | None = None,
    ) -> None:
        super().__init__(contract=contract)
        self._repo = repo
        self._baseline_path = baseline_path or _DEFAULT_BASELINE
        self._baseline: set[str] | None = None
        # repo_root anchors fingerprints to a stable repo-relative path.
        # When None, the absolute path is used (consistent per machine run).
        self._repo_root = repo_root

    def _get_baseline(self) -> set[str]:
        if self._baseline is None:
            self._baseline = load_baseline(self._baseline_path)
        return self._baseline

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        if path.suffix not in {".py"}:
            return ()

        # Determine repo-relative path for stable fingerprints.
        if self._repo_root is not None:
            try:
                rel = str(path.relative_to(self._repo_root))
            except ValueError:
                rel = path.name
        else:
            rel = path.name

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ()

        raw_violations = scan_source(self._repo, rel, source)
        baseline = self._get_baseline()
        new, _ = partition_against_baseline(raw_violations, baseline)

        issues: list[ModelValidationIssue] = []
        for v in new:
            enabled, severity = self._get_rule_config(v.rule, contract)
            if not enabled:
                continue
            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=(
                        f"url-authority violation [{v.rule}]: {v.snippet!r} — "
                        "migrate to the routing authority/integration catalog, or "
                        "annotate # url-authority-ok: <reason>"
                    ),
                    code=v.rule,
                    file_path=path,
                    line_number=v.line,
                    rule_name=v.rule,
                )
            )
        return tuple(issues)


# ---------------------------------------------------------------------------
# CLI — pre-commit hook + CI gate
# ---------------------------------------------------------------------------


def _err(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def _out(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def _update_baseline(
    repo: str, repo_root: Path, baseline_path: Path, *, seed: bool
) -> int:
    """Regenerate this repo's baseline subset (burn-down only)."""
    prior_entries: list[dict[str, str]] = []
    if baseline_path.exists():
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
        all_entries = data.get("violations", []) if isinstance(data, dict) else []
        prior_entries = [
            e for e in all_entries if isinstance(e, dict) and "fingerprint" in e
        ]
    repo_before = {e["fingerprint"] for e in prior_entries if e.get("repo") == repo}
    other_entries = [e for e in prior_entries if e.get("repo") != repo]

    fresh_violations = scan_tree(repo, repo_root)
    fresh: list[dict[str, str]] = [
        {
            "repo": v.repo,
            "path": v.path,
            "rule": v.rule,
            "fingerprint": v.fingerprint,
        }
        for v in fresh_violations
    ]
    repo_after = {e["fingerprint"] for e in fresh}

    if not seed:
        try:
            assert_baseline_shrinks_only(repo_before, repo_after)
        except ValueError as exc:
            _err(f"URL-AUTHORITY BASELINE REJECTED: {exc}")
            return 1

    merged = sorted(
        [*other_entries, *fresh],
        key=lambda e: (e["repo"], e["path"], e["fingerprint"]),
    )
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(
            {"schema_version": "1.0.0", "count": len(merged), "violations": merged},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    action = "seeded" if seed else f"burned down {len(repo_before) - len(repo_after)}"
    _out(
        f"URL-AUTHORITY BASELINE updated for {repo}: {len(repo_after)} violation(s) "
        f"({action}). Total across repos: {len(merged)}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Staged-files mode (pre-commit): pass file paths as positional args.
    Full-repo mode (CI): pass ``--all --repo <name> --repo-root <path>``.
    Baseline update: pass ``--seed`` or ``--update-baseline``.

    Exit codes:
        0 — no new violations (or grandfathered-only)
        1 — new violation(s) found or baseline grew
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="check-url-authority",
        description="url-authority ratchet gate (OMN-12818).",
    )
    parser.add_argument(
        "paths", nargs="*", help="Explicit files to scan (staged set, pre-commit mode)."
    )
    parser.add_argument(
        "--repo", default="omnibase_core", help="Repo name for fingerprints."
    )
    parser.add_argument(
        "--repo-root", default=".", help="Repo root for repo-relative paths."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Full-repo scan (CI mode) instead of explicit staged files.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Regenerate this repo's baseline subset (burn-down only).",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="One-time initialization of this repo's baseline subset (no shrink check).",
    )
    parser.add_argument(
        "--baseline",
        default=str(_DEFAULT_BASELINE),
        help="Path to the baseline JSON.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    baseline_path = Path(args.baseline)

    if args.update_baseline or args.seed:
        return _update_baseline(args.repo, repo_root, baseline_path, seed=args.seed)

    if args.all:
        violations = scan_tree(args.repo, repo_root)
    else:
        if not args.paths:
            _out("URL-AUTHORITY GATE: no files to scan.")
            return 0
        violations = []
        for raw in args.paths:
            p = Path(raw)
            if not p.is_file() or not _is_msk_scannable(p):
                continue
            try:
                source = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                rel = str(p.resolve().relative_to(repo_root.resolve()))
            except ValueError:
                rel = str(p)
            violations.extend(scan_source(args.repo, rel, source))

    baseline = load_baseline(baseline_path)
    new, grandfathered = partition_against_baseline(violations, baseline)

    if new:
        _err(
            f"URL-AUTHORITY GATE FAILED: {len(new)} NEW violation(s) — every URL must "
            "resolve from a contract (routing authority / integration catalog), not a "
            "literal or a *_URL/*_ENDPOINT env read.\n"
        )
        for v in new:
            _err(f"  [{v.rule}] {v.repo}/{v.path}:{v.line}")
            _err(f"    {v.snippet}")
            _err(
                "    -> migrate to the resolver, or annotate "
                "# url-authority-ok: <reason>"
            )
        return 1

    _out(
        f"URL-AUTHORITY GATE PASSED: 0 new violations "
        f"({len(grandfathered)} grandfathered)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
