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
* ``E-LAN``: an RFC 1918 host inside a URL, or any literal on our own lab subnet.
* ``R``: an exact retired lab value. Matched in comments too.
* ``L``: a ``.example.`` file handed to a loader (``open``, ``read_text``,
  ``safe_load``, ``json.load``) in Python source.

No inline suppression marker is honoured; the policy file is the whole
allowlist. Several matches of one family on one line are one finding, because
the baseline is keyed by line content.
"""

from __future__ import annotations

import hashlib
import io
import re
import tokenize
from collections import Counter
from collections.abc import Iterable, Sequence
from functools import lru_cache
from typing import Final

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

_FAMILY_ORDER: Final[dict[str, int]] = {"M": 0, "E": 1, "E-LAN": 2, "R": 3, "L": 4}

_PYTHON_SUFFIXES: Final[frozenset[str]] = frozenset({".py", ".pyi"})
_SLASH_COMMENT_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
)
_NO_COMMENT_SUFFIXES: Final[frozenset[str]] = frozenset({".json"})

_URL: Final[str] = r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s\"'<>`]+"
_URL_HOST_IPV4: Final[re.Pattern[str]] = re.compile(
    r"[A-Za-z][A-Za-z0-9+.\-]*://(?:[^\s/@\"'<>`]*@)?"
    r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\d.])"
)
_ENV_READ_DEFAULT: Final[re.Pattern[str]] = re.compile(
    r"\bos\.(?:getenv|environ\.get)\(\s*[^,()]+,\s*[rbuRBU]?[\"'](?P<url>" + _URL + r")"
)
_LOADER_CALL: Final[re.Pattern[str]] = re.compile(
    r"(?:\bopen|\.read_text|\bsafe_load|\bjson\.load)\s*\("
)
_EXAMPLE_MARK: Final[str] = ".example."
_STATEMENT_START: Final[frozenset[int]] = frozenset(
    {tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}
)


# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------


@lru_cache(maxsize=512)
def _glob_regex(glob: str) -> re.Pattern[str]:
    """Translate a repository glob: ``**/`` spans zero or more directories,
    ``**`` spans anything, ``*`` and ``?`` stay within one path segment."""
    out: list[str] = []
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


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
        if any(_glob_regex(glob).match(norm) for glob in path_class.globs):
            return path_class
    # The policy loader guarantees a final catch-all SOURCE class; reaching
    # here means the policy was built without one.
    raise ValueError(  # error-ok: pure handler invariant, the runtime validates the policy first
        f"policy has no path class matching {norm!r}"
    )


# ---------------------------------------------------------------------------
# Per-line views: code with comments and docstrings removed, and literals
# ---------------------------------------------------------------------------


def _suffix(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def _strip_hash_comment(line: str) -> str:
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            return line[:i]
    return line


def _strip_slash_comment(line: str) -> str:
    stripped = line.lstrip()
    if stripped.startswith(("/*", "*")):
        return ""
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in ("'", '"', "`"):
            quote = ch
        elif line.startswith("//", i) and (i == 0 or line[i - 1] != ":"):
            return line[:i]
    return line


def _blank(code: dict[int, str], start: tuple[int, int], end: tuple[int, int]) -> None:
    (srow, scol), (erow, ecol) = start, end
    for row in range(srow, erow + 1):
        line = code.get(row, "")
        lo = scol if row == srow else 0
        hi = ecol if row == erow else len(line)
        code[row] = line[:lo] + " " * max(hi - lo, 0) + line[hi:]


def _python_views(
    text: str, lines: Sequence[str]
) -> tuple[dict[int, str], dict[int, list[str]]] | None:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        return None
    code = dict(enumerate(lines, start=1))
    literals: dict[int, list[str]] = {}
    prev_type: int | None = None
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            _blank(code, tok.start, tok.end)
            continue
        if tok.type in (tokenize.NL, tokenize.ENCODING):
            continue
        if tok.type == tokenize.STRING:
            if prev_type is None or prev_type in _STATEMENT_START:
                # A string that opens a statement is a docstring or a bare
                # expression: prose, not configuration.
                _blank(code, tok.start, tok.end)
            else:
                for offset, part in enumerate(tok.string.split("\n")):
                    literals.setdefault(tok.start[0] + offset, []).append(part)
        elif tok.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
            for offset, part in enumerate(tok.string.split("\n")):
                literals.setdefault(tok.start[0] + offset, []).append(part)
        prev_type = tok.type
    return code, literals


def _generic_views(
    path: str, lines: Sequence[str]
) -> tuple[dict[int, str], dict[int, list[str]]]:
    suffix = _suffix(path)
    code: dict[int, str] = {}
    for n, line in enumerate(lines, start=1):
        if suffix in _NO_COMMENT_SUFFIXES:
            code[n] = line
        elif suffix in _SLASH_COMMENT_SUFFIXES:
            code[n] = _strip_slash_comment(line)
        else:
            code[n] = _strip_hash_comment(line)
    # Outside Python every value on a line is a candidate literal.
    literals = {n: [text] for n, text in code.items() if text.strip()}
    return code, literals


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------


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
    return None


def content_sha1(line: str) -> str:
    """The baseline key of a line: sha1 of its stripped text."""
    return hashlib.sha1(line.strip().encode("utf-8"), usedforsecurity=False).hexdigest()


def scan(
    path: str, text: str, policy: ModelHardcodedModelConfigPolicy
) -> list[ModelHardcodedModelConfigFinding]:
    """Return every finding in ``text`` for the families ``path``'s class allows."""
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

    if families & {"M", "E", "E-LAN", "L"}:
        model_id, endpoint_url, endpoint_key, lab_subnet = _compiled(policy)
        is_python = _suffix(path) in _PYTHON_SUFFIXES
        views = _python_views(text, lines) if is_python else None
        if views is None:
            views = _generic_views(path, lines)
        code, literals = views
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
            if "L" in families and is_python:
                if _LOADER_CALL.search(line_code) and any(
                    _EXAMPLE_MARK in literal for literal in line_literals
                ):
                    record(n, "L", _EXAMPLE_MARK)

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
) -> tuple[
    list[ModelHardcodedModelConfigFinding], list[ModelHardcodedModelConfigBaselineEntry]
]:
    """Split into (new findings, stale baseline entries).

    A finding is new when its key occurs more often than the baseline allows. A
    retired-value finding is always new. An entry is stale when its file was
    scanned (or no longer exists) and its key occurs less often than recorded.
    Entries for files this run did not read are not judged.
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

    def __init__(self, policy: ModelHardcodedModelConfigPolicy) -> None:
        self._policy = policy

    @property
    def handler_id(self) -> str:
        return "validator-hardcoded-model-config-compute"

    def handle(
        self, request: ModelHardcodedModelConfigScanInput
    ) -> ModelHardcodedModelConfigScanResult:
        path_class = classify_path(request.path, self._policy)
        findings = scan(request.path, request.content, self._policy)
        return ModelHardcodedModelConfigScanResult(
            path=_normalise(request.path),
            path_class=path_class.name,
            findings=tuple(findings),
        )
