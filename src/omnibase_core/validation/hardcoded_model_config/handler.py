# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerHardcodedModelConfigCompute: pure scanner for hardcoded lab model config.

Task A1 of knowledge-base-internal
``beta/plans/2026-09-23-remove-hardcoded-model-config.md`` (OMN-19252), as
amended by that plan's 2026-09-23 review. Everything in this module is PURE and
DETERMINISTIC: it reads the text and the policy it is handed and performs no
filesystem, network, environment or clock I/O. Loading files, the policy and
the baseline is the EFFECT boundary's job (``runtime_hardcoded_model_config``).

Families (the policy decides which apply to a path):

* ``M``: a model id (the plan's P1 family regex) in a string literal or a
  YAML/JSON/TOML value. Comments and docstrings are skipped.
* ``E``: an inference endpoint: a URL literal ending in one of the policy's
  ``/v1/...`` paths, a URL-valued literal assigned to one of the policy's
  endpoint keys, or a URL default of ``os.getenv``/``os.environ.get``.
* ``E-LAN``: an RFC 1918 address in a literal (inside a URL or bare), or any
  literal on our own lab subnet.
* ``D``: a lab deployment fact, a lab host name or a lab port the policy carries
  (OMN-21147), matched as a whole value in code. Comments and docstrings are
  skipped.
* ``R``: an exact retired lab value. Matched in comments too.
* ``L``: a ``.example.`` file handed to a loader (``open``, ``read_text``,
  ``safe_load``, ``json.load``) in Python source.
* ``T`` and ``N``: a model tier alias and an engine name of the engine ladder
  (OMN-21463); judged by ``validation.checker_hardcoded_model_tier``.
* ``O``, ``G``, ``F``, ``P``, ``S``, ``H`` and ``B``: operational numbers, first-party
  URLs, filesystem locations, repository lists, ruling stamps, host lists and budgets
  (OMN-21537); judged by ``validation.checker_hardcoded_model_literals`` over the rule
  rows of its ``.validation.yaml``, handed in as a rule set.

No inline suppression marker is honoured; the policy file is the whole
allowlist. Several matches of one family on one line are one finding, because
the baseline is keyed by line content.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from functools import lru_cache
from typing import Final, get_args

from omnibase_core.models.validation.model_hardcoded_literal_rule_set import (
    ModelHardcodedLiteralRuleSet,
)
from omnibase_core.validation.checker_hardcoded_model_literals import scan_literals
from omnibase_core.validation.checker_hardcoded_model_tier import scan_tier_engine
from omnibase_core.validation.checker_hardcoded_model_views import (
    file_suffix,
    generic_views,
    glob_regex,
    python_views,
)
from omnibase_core.validation.hardcoded_model_config.models import (
    LiteralFamily,
    ModelHardcodedModelConfigBaselineEntry,
    ModelHardcodedModelConfigFinding,
    ModelHardcodedModelConfigPathClass,
    ModelHardcodedModelConfigPolicy,
    ModelHardcodedModelConfigScanInput,
    ModelHardcodedModelConfigScanResult,
)

__all__ = [
    "HandlerHardcodedModelConfigCompute",
    "added_entries",
    "classify_path",
    "compare_with_baseline",
    "content_sha1",
    "finding_key",
    "scan",
]

_FAMILY_ORDER: Final[dict[str, int]] = {
    f: i for i, f in enumerate(get_args(LiteralFamily))
}


_URL: Final[str] = r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s\"'<>`]+"
_URL_HOST_IPV4: Final[re.Pattern[str]] = re.compile(
    r"[A-Za-z][A-Za-z0-9+.\-]*://(?:[^\s/@\"'<>`]*@)?"
    r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\d.])"
)
_BARE_IPV4: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\w.])"
)
_ENV_READ_DEFAULT: Final[re.Pattern[str]] = re.compile(
    r"\bos\.(?:getenv|environ\.get)\(\s*[^,()]+,\s*[rbuRBU]?[\"'](?P<url>" + _URL + r")"
)
_LOADER_CALL: Final[re.Pattern[str]] = re.compile(
    r"(?:\bopen|\.read_text|\bsafe_load|\bjson\.load)\s*\("
)
_EXAMPLE_MARK: Final[str] = ".example."

# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------


def _normalise(path: str) -> str:
    norm = path.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


def classify_path(
    path: str, policy: ModelHardcodedModelConfigPolicy
) -> ModelHardcodedModelConfigPathClass:
    """Return the first path class that names or globs ``path``."""
    norm = _normalise(path)
    for path_class in policy.path_classes:
        if norm in path_class.files:
            return path_class
        if any(glob_regex(glob).match(norm) for glob in path_class.globs):
            return path_class
    # The policy loader guarantees a final catch-all SOURCE class; reaching
    # here means the policy was built without one.
    raise ValueError(  # error-ok: pure handler invariant, the runtime validates the policy first
        f"policy has no path class matching {norm!r}"
    )


# ---------------------------------------------------------------------------
# Per-line views: code with comments and docstrings removed, and literals
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8)
def _deployment_fact(policy: ModelHardcodedModelConfigPolicy) -> re.Pattern[str] | None:
    """Family D: any lab host name or lab port as a whole value, or None."""
    parts: list[str] = []
    if policy.lab_host_names:
        names = "|".join(re.escape(n) for n in policy.lab_host_names)
        parts.append(r"(?<![\w.\-])(?:" + names + r")(?![\w\-])")
    if policy.lab_ports:
        ports = "|".join(str(p) for p in policy.lab_ports)
        parts.append(r"(?<![\w.])(?:" + ports + r")(?![\w.])")
    return re.compile("|".join(parts), re.IGNORECASE) if parts else None


@lru_cache(maxsize=8)
def _compiled(
    policy: ModelHardcodedModelConfigPolicy,
) -> tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    model_id = re.compile(policy.model_id_pattern, re.IGNORECASE)
    suffixes = "|".join(re.escape(s) for s in policy.endpoint_path_suffixes)
    endpoint_url = re.compile(
        r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s\"'<>`]*?(?:" + suffixes + r")(?![\w/\-])"
    )
    keys = "|".join(re.escape(k) for k in policy.endpoint_keys)
    endpoint_key = re.compile(
        r"(?<![\w\-])[\"']?(?:" + keys + r")[\"']?\s*"
        r"(?::\s*[\w\[\], |.]+?\s*)?[:=]\s*[rbuRBU]?[\"']?(?P<url>" + _URL + r")"
    )
    lab_subnet = re.compile(policy.lab_subnet_pattern)
    return model_id, endpoint_url, endpoint_key, lab_subnet


def _is_rfc1918(octets: Iterable[str]) -> bool:
    o1, o2, o3, o4 = (int(o) for o in octets)
    if any(o > 255 for o in (o1, o2, o3, o4)):
        return False
    return o1 == 10 or (o1 == 172 and 16 <= o2 <= 31) or (o1 == 192 and o2 == 168)


def _first_private_url_host(text: str) -> str | None:
    for match in _URL_HOST_IPV4.finditer(text):
        if _is_rfc1918(match.groups()):
            return match.group(0)
    for match in _BARE_IPV4.finditer(text):
        if _is_rfc1918(match.groups()):
            return match.group(0)
    return None


def content_sha1(line: str) -> str:
    """The baseline key of a line: sha1 of its stripped text."""
    return hashlib.sha1(line.strip().encode("utf-8"), usedforsecurity=False).hexdigest()


def scan(
    path: str,
    text: str,
    policy: ModelHardcodedModelConfigPolicy,
    literal_rules: ModelHardcodedLiteralRuleSet | None = None,
) -> list[ModelHardcodedModelConfigFinding]:
    """Return every finding in ``text`` for the families ``path``'s class allows.

    ``literal_rules`` carries the rule rows of families O, G, F, P, S, H and B; without it
    those families are not judged.
    """
    path_class = classify_path(path, policy)
    families = set(path_class.families)
    if not families:
        return []
    lines = text.splitlines()
    hits: dict[tuple[int, LiteralFamily], str] = {}

    def record(line_no: int, family: LiteralFamily, matched: str) -> None:
        hits.setdefault((line_no, family), matched)

    if "R" in families:
        for n, line in enumerate(lines, start=1):
            for value in policy.retired_values:
                if value in line:
                    record(n, "R", value)
                    break

    if families & {"M", "E", "E-LAN", "D", "L", "T", "N"}:
        model_id, endpoint_url, endpoint_key, lab_subnet = _compiled(policy)
        fact = _deployment_fact(policy)
        is_python = file_suffix(path) in policy.python_suffixes
        views = python_views(text, lines) if is_python else None
        if views is None:
            views = generic_views(
                path, lines, policy.slash_comment_suffixes, policy.no_comment_suffixes
            )
        code, literals = views
        for hit in scan_tier_engine(text, code, is_python, policy, families):
            record(*hit)
        for n in range(1, len(lines) + 1):
            line_code = code.get(n, "")
            line_literals = literals.get(n, [])
            if not line_code.strip() and not line_literals:
                continue
            if "M" in families:
                for literal in line_literals:
                    m = model_id.search(literal)
                    if m:
                        record(n, "M", m.group(0))
                        break
            if "E" in families:
                for literal in line_literals:
                    e = endpoint_url.search(literal)
                    if e:
                        record(n, "E", e.group(0))
                        break
                k = endpoint_key.search(line_code) or _ENV_READ_DEFAULT.search(
                    line_code
                )
                if k:
                    record(n, "E", k.group("url"))
            if "E-LAN" in families:
                for literal in line_literals:
                    host = _first_private_url_host(literal)
                    lab = lab_subnet.search(literal)
                    if host or lab:
                        record(n, "E-LAN", host or (lab.group(0) if lab else ""))
                        break
            if "D" in families and fact is not None:
                d = fact.search(line_code)
                if d:
                    record(n, "D", d.group(0))
            if "L" in families and is_python:
                if _LOADER_CALL.search(line_code) and any(
                    _EXAMPLE_MARK in literal for literal in line_literals
                ):
                    record(n, "L", _EXAMPLE_MARK)

    if literal_rules is not None:
        for line_no, family, matched in scan_literals(path, text, literal_rules):
            if family in families:
                record(line_no, family, matched)

    ordered = sorted(hits.items(), key=lambda kv: (kv[0][0], _FAMILY_ORDER[kv[0][1]]))
    return [
        ModelHardcodedModelConfigFinding(
            path=_normalise(path),
            line=line_no,
            family=family,
            path_class=path_class.name,
            matched_text=matched,
            content_sha1=content_sha1(lines[line_no - 1]),
        )
        for (line_no, family), matched in ordered
    ]


# ---------------------------------------------------------------------------
# Baseline arithmetic (multisets keyed by path, family and line content)
# ---------------------------------------------------------------------------


def finding_key(finding: ModelHardcodedModelConfigFinding) -> tuple[str, str, str]:
    return (finding.path, finding.family, finding.content_sha1)


def compare_with_baseline(
    findings: Sequence[ModelHardcodedModelConfigFinding],
    baseline: Sequence[ModelHardcodedModelConfigBaselineEntry],
    scanned_paths: frozenset[str],
    missing_paths: frozenset[str],
    unjudged_families: frozenset[str] = frozenset(),
) -> tuple[
    list[ModelHardcodedModelConfigFinding], list[ModelHardcodedModelConfigBaselineEntry]
]:
    """Split into (new findings, stale baseline entries).

    A finding is new when its key occurs more often than the baseline allows. A
    retired-value finding is always new. An entry is stale when its file was
    scanned (or no longer exists) and its key occurs less often than recorded.
    Entries for files this run did not read are not judged, nor entries of a
    family this run cannot detect (``unjudged_families``: D without the
    private vocabulary).
    """
    allowed: Counter[tuple[str, str, str]] = Counter(e.key() for e in baseline)
    seen: Counter[tuple[str, str, str]] = Counter()
    new: list[ModelHardcodedModelConfigFinding] = []
    for finding in findings:
        key = finding_key(finding)
        seen[key] += 1
        if finding.family == "R" or seen[key] > allowed[key]:
            new.append(finding)
    stale: list[ModelHardcodedModelConfigBaselineEntry] = []
    by_key = {e.key(): e for e in baseline}
    for key, count in sorted(allowed.items()):
        path = key[0]
        if path not in scanned_paths and path not in missing_paths:
            continue
        if key[1] in unjudged_families:
            continue
        excess = count - seen[key]
        stale.extend([by_key[key]] * max(excess, 0))
    return new, stale


def added_entries(
    base: Sequence[ModelHardcodedModelConfigBaselineEntry],
    head: Sequence[ModelHardcodedModelConfigBaselineEntry],
) -> list[ModelHardcodedModelConfigBaselineEntry]:
    """Entries ``head`` carries beyond ``base`` (the baseline may only shrink)."""
    grown = Counter(e.key() for e in head) - Counter(e.key() for e in base)
    by_key = {e.key(): e for e in head}
    return [by_key[key] for key, count in sorted(grown.items()) for _ in range(count)]


class HandlerHardcodedModelConfigCompute:
    """COMPUTE handler: scan one file's text against the policy.

    Canonical definition-B shape: ``handle(request) -> response``, typed in and
    typed out, no envelope, no I/O. Stateless apart from the injected policy.
    """

    def __init__(
        self,
        policy: ModelHardcodedModelConfigPolicy,
        literals: ModelHardcodedLiteralRuleSet | None = None,
    ) -> None:
        self._policy = policy
        self._literals = literals

    @property
    def handler_id(self) -> str:
        return "validator-hardcoded-model-config-compute"

    def handle(
        self, request: ModelHardcodedModelConfigScanInput
    ) -> ModelHardcodedModelConfigScanResult:
        path_class = classify_path(request.path, self._policy)
        findings = scan(request.path, request.content, self._policy, self._literals)
        return ModelHardcodedModelConfigScanResult(
            path=_normalise(request.path),
            path_class=path_class.name,
            findings=tuple(findings),
        )
