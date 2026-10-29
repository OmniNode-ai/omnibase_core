# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerInternalSiblingPins -- internal siblings resolve from dev merge tags.

RULINGs 2026-10-16T07:34:18Z and 2026-10-16T09:35:49Z (OMN-19998): internal
siblings are consumed from the tag ``dev-merge-tag.yml`` puts on every dev
merge, not from a release, and that is part of the process, "not up to for
somebody to remember". This handler judges a consumer's ``pyproject.toml``
against ``contracts/internal_sibling_pins.yaml``. For every internal sibling
the consumer declares (``[project]`` dependencies and extras,
``[dependency-groups]``, ``[tool.uv]`` override and constraint dependencies)
other than the consumer itself:

* ``missing_source`` -- no ``[tool.uv.sources]`` entry and no direct URL, so
  ``uv sync`` resolves a release from the index.
* ``bare_sha`` -- a ``rev`` (or a direct URL ref) that is a commit sha.
* ``release_tag`` -- a ``tag`` (or ref) that is a release tag such as ``v0.47.48``.
* ``branch`` -- a ``branch``, or a git source or URL with no ref, which moves.
* ``not_dev_tag`` -- any other ref, a ``rev`` naming a dev tag (spell it
  ``tag =``), or a non-git source (index, path, url, workspace).
* ``wrong_repo`` -- a git source that is not the sibling's own repository.
* ``release_pin`` -- an exact ``==`` version of a sibling, which pins a release
  and refuses the dev tag's version; keep a range for external installs.
* ``stale_pin`` -- a dev tag trails the newest dev tag by more than the
  contract's merge or timestamp bound; repin to the newest dev tag.
* ``unverifiable_pin`` -- the sibling's tag inventory or pinned tag is absent
  when staleness is evaluated, or a tag timestamp cannot be read.

The PyPI range stays in ``[project]`` dependencies for external installs; the
source is what CI and the lab resolve. Every finding is FAIL. There is no
suppression marker and no baseline: a consumer adopts the check when it
converts.

Pure: parses the TOML text it is given; no filesystem, no clock. Ticket: OMN-19998.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Final, Literal

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_contract import (
    ModelInternalSiblingPinsContract,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_input import (
    ModelInternalSiblingPinsInput,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_rules import (
    ModelInternalSiblingPinsRules,
)

__all__ = [
    "VALIDATOR_ID",
    "HandlerInternalSiblingPins",
    "classify_ref",
    "declared_sibling_repos",
    "normalize_name",
]

VALIDATOR_ID: Final[str] = "internal_sibling_pins"
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


@lru_cache(maxsize=32)
def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def normalize_name(name: str) -> str:
    """PEP 503 normalised distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def classify_ref(
    ref: str | None, dev_tag: re.Pattern[str], rules: ModelInternalSiblingPinsRules
) -> str | None:
    """None for a dev merge tag; else the rule a git ref breaks."""
    if ref is None or not ref.strip():
        return "branch"
    ref = ref.strip()
    if dev_tag.match(ref):
        return None
    if _re(rules.sha_pattern).match(ref):
        return "bare_sha"
    if _re(rules.release_tag_pattern).match(ref):
        return "release_tag"
    return "not_dev_tag"


def _repo_url(url: str) -> str:
    return re.sub(r"\.git$", "", url.strip().rstrip("/")).lower()


def _requirement_strings(document: Mapping[str, object]) -> Iterator[tuple[str, str]]:
    """(table, requirement) for every requirement string the pyproject declares."""
    project = document.get("project")
    if isinstance(project, Mapping):
        for item in _strings(project.get("dependencies")):
            yield "project.dependencies", item
        extras = project.get("optional-dependencies")
        if isinstance(extras, Mapping):
            for extra, items in extras.items():
                for item in _strings(items):
                    yield f"project.optional-dependencies.{extra}", item
    groups = document.get("dependency-groups")
    if isinstance(groups, Mapping):
        for group, items in groups.items():
            for item in _strings(items):
                yield f"dependency-groups.{group}", item
    uv = _uv(document)
    for key in ("override-dependencies", "constraint-dependencies", "dev-dependencies"):
        for item in _strings(uv.get(key)):
            yield f"tool.uv.{key}", item


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, list):
        yield from (item for item in value if isinstance(item, str))


def _uv(document: Mapping[str, object]) -> Mapping[str, object]:
    tool = document.get("tool")
    if isinstance(tool, Mapping):
        uv = tool.get("uv")
        if isinstance(uv, Mapping):
            return uv
    return {}


def declared_sibling_repos(
    document: Mapping[str, object],
    contract: ModelInternalSiblingPinsContract,
    rules: ModelInternalSiblingPinsRules,
) -> tuple[str, ...]:
    """Sibling repositories judged in this document, excluding the consumer."""
    names = set()
    for _, requirement in _requirement_strings(document):
        match = _re(rules.name_pattern).match(requirement)
        if match:
            names.add(normalize_name(match.group(1)))
    sources = _uv(document).get("sources")
    if isinstance(sources, Mapping):
        names.update(normalize_name(str(name)) for name in sources)
    project = document.get("project")
    if isinstance(project, Mapping):
        names.discard(normalize_name(str(project.get("name", ""))))
    return tuple(
        sorted(
            s.repo for s in contract.siblings if normalize_name(s.distribution) in names
        )
    )


class HandlerInternalSiblingPins:
    """Require internal sibling dev merge tags within the contract's bounds."""

    def handle(self, request: ModelInternalSiblingPinsInput) -> ModelValidationReport:
        """Definition-B canonical entry-point (OMN-14355). Pure, no I/O, no clock."""
        contract = request.contract
        rules = request.rules
        dev_tag = re.compile(contract.dev_tag_pattern)
        dev_tags = (
            {sibling.repo: sibling.tags for sibling in request.dev_tags}
            if request.dev_tags is not None
            else None
        )
        errors: list[str] = []
        findings: list[ModelValidationFinding] = []
        for file in request.files:
            try:
                document = tomllib.loads(file.source)
            except tomllib.TOMLDecodeError as exc:
                errors.append(f"{file.path}: pyproject does not parse: {exc}")
                continue
            findings.extend(
                self._judge(file.path, document, contract, rules, dev_tag, dev_tags)
            )
        if errors:
            return ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID, tuple(errors)
            )
        return self._report(tuple(findings))

    def _judge(
        self,
        path: str,
        document: Mapping[str, object],
        contract: ModelInternalSiblingPinsContract,
        rules: ModelInternalSiblingPinsRules,
        dev_tag: re.Pattern[str],
        dev_tags: Mapping[str, tuple[str, ...]] | None,
    ) -> Iterator[ModelValidationFinding]:
        siblings = {normalize_name(s.distribution): s for s in contract.siblings}
        project = document.get("project")
        own = (
            normalize_name(str(project.get("name", "")))
            if isinstance(project, Mapping)
            else ""
        )
        raw_sources = _uv(document).get("sources")
        sources = (
            {normalize_name(str(k)): v for k, v in raw_sources.items()}
            if isinstance(raw_sources, Mapping)
            else {}
        )

        declared: dict[str, list[str]] = {}
        for table, requirement in _requirement_strings(document):
            match = _re(rules.name_pattern).match(requirement)
            if not match:
                continue
            name = normalize_name(match.group(1))
            if name not in siblings or name == own:
                continue
            declared.setdefault(name, [])
            location = f"{path}:{table}"
            head, _, url = requirement.partition(" @ ")
            if url:
                declared[name].append("url")
                yield from self._judge_url(
                    location, name, url, siblings[name].repo, contract, rules, dev_tag
                )
                continue
            specifier = head[match.end() :].split(";", 1)[0]
            if _re(rules.exact_pattern).search(specifier):
                yield self._finding(
                    location,
                    f"{location}: {name} is pinned to an exact release "
                    f"({requirement.strip()}) (rule release_pin)",
                    rules,
                )

        for name in sorted(set(declared) | (set(sources) & set(siblings))):
            if name == own:
                continue
            sibling = siblings[name]
            location = f"{path}:tool.uv.sources.{name}"
            if name not in sources:
                if "url" not in declared.get(name, []):
                    yield self._finding(
                        location,
                        f"{location}: {name} has no [tool.uv.sources] entry, so uv "
                        "sync resolves a release from the index (rule missing_source)",
                        rules,
                    )
                continue
            entries = sources[name]
            items = entries if isinstance(entries, list) else [entries]
            for item in items:
                yield from self._judge_source(
                    location,
                    name,
                    item,
                    sibling.repo,
                    contract,
                    rules,
                    dev_tag,
                    dev_tags,
                )

    def _judge_source(
        self,
        location: str,
        name: str,
        source: object,
        repo: str,
        contract: ModelInternalSiblingPinsContract,
        rules: ModelInternalSiblingPinsRules,
        dev_tag: re.Pattern[str],
        dev_tags: Mapping[str, tuple[str, ...]] | None,
    ) -> Iterator[ModelValidationFinding]:
        if not isinstance(source, Mapping) or "git" not in source:
            kind = (
                ", ".join(sorted(str(k) for k in source))
                if isinstance(source, Mapping)
                else type(source).__name__
            )
            yield self._finding(
                location,
                f"{location}: {name} resolves from a non-git source ({kind}), not a "
                "dev merge tag (rule not_dev_tag)",
                rules,
            )
            return
        expected = _repo_url(f"https://github.com/{contract.github_org}/{repo}")
        if _repo_url(str(source["git"])) != expected:
            yield self._finding(
                location,
                f"{location}: {name} git source {source['git']} is not "
                f"{expected} (rule wrong_repo)",
                rules,
            )
        if "branch" in source:
            yield self._finding(
                location,
                f"{location}: {name} follows branch {source['branch']!r}, which "
                "moves (rule branch)",
                rules,
            )
            return
        if "rev" in source:
            rev = str(source["rev"])
            rev_rule = classify_ref(rev, dev_tag, rules) or "not_dev_tag"
            yield self._finding(
                location,
                f"{location}: {name} is pinned by rev {rev!r}; pin tag = a dev "
                f"merge tag (rule {rev_rule})",
                rules,
            )
            return
        tag = source.get("tag")
        rule = classify_ref(None if tag is None else str(tag), dev_tag, rules)
        if rule is not None:
            shown = f"tag {tag!r}" if tag is not None else "no ref"
            yield self._finding(
                location,
                f"{location}: {name} git source has {shown}, not a dev merge tag "
                f"(rule {rule})",
                rules,
            )
        elif dev_tags is not None:
            yield from self._judge_staleness(
                location,
                name,
                str(tag).strip(),
                repo,
                contract,
                rules,
                dev_tag,
                dev_tags,
            )

    def _judge_staleness(
        self,
        location: str,
        name: str,
        pinned: str,
        repo: str,
        contract: ModelInternalSiblingPinsContract,
        rules: ModelInternalSiblingPinsRules,
        dev_tag: re.Pattern[str],
        dev_tags: Mapping[str, tuple[str, ...]],
    ) -> Iterator[ModelValidationFinding]:
        tags = {tag for tag in dev_tags.get(repo, ()) if dev_tag.match(tag)}
        if pinned not in tags:
            yield self._finding(
                location,
                f"{location}: {name} pinned tag {pinned!r} is absent from the "
                f"supplied dev tags for {repo} (rule unverifiable_pin)",
                rules,
            )
            return
        newest = max(tags)
        merges = sum(tag > pinned for tag in tags)
        try:
            pinned_time = datetime.strptime(
                pinned.split("-")[1], "%Y%m%d%H%M%S"
            ).replace(tzinfo=UTC)
            newest_time = datetime.strptime(
                newest.split("-")[1], "%Y%m%d%H%M%S"
            ).replace(tzinfo=UTC)
        except ValueError:
            yield self._finding(
                location,
                f"{location}: {name} cannot read UTC timestamps for pinned tag "
                f"{pinned!r} and newest tag {newest!r} (rule unverifiable_pin)",
                rules,
            )
            return
        hours = (newest_time - pinned_time) / timedelta(hours=1)
        if merges > contract.max_trailing_merges or hours > contract.max_trailing_hours:
            yield self._finding(
                location,
                f"{location}: {name} pinned tag {pinned!r} trails newest tag "
                f"{newest!r} by {merges} merges and {hours:g} hours; bounds are "
                f"{contract.max_trailing_merges} merges and "
                f"{contract.max_trailing_hours} hours (rule stale_pin)",
                rules,
            )

    def _judge_url(
        self,
        location: str,
        name: str,
        url: str,
        repo: str,
        contract: ModelInternalSiblingPinsContract,
        rules: ModelInternalSiblingPinsRules,
        dev_tag: re.Pattern[str],
    ) -> Iterator[ModelValidationFinding]:
        match = _re(rules.git_url_pattern).match(url.split(";", 1)[0].strip())
        if not match:
            yield self._finding(
                location,
                f"{location}: {name} is a non-git direct URL, not a dev merge tag "
                "(rule not_dev_tag)",
                rules,
            )
            return
        expected = _repo_url(f"https://github.com/{contract.github_org}/{repo}")
        if _repo_url(match.group("url")) != expected:
            yield self._finding(
                location,
                f"{location}: {name} direct URL {match.group('url')} is not "
                f"{expected} (rule wrong_repo)",
                rules,
            )
        ref = match.group("ref")
        rule = classify_ref(ref, dev_tag, rules)
        if rule is not None:
            yield self._finding(
                location,
                f"{location}: {name} direct URL ref {ref!r} is not a dev merge tag "
                f"(rule {rule})",
                rules,
            )

    @staticmethod
    def _finding(
        location: str, message: str, rules: ModelInternalSiblingPinsRules
    ) -> ModelValidationFinding:
        return ModelValidationFinding(
            validator_id=VALIDATOR_ID,
            severity="FAIL",
            location=location,
            message=message,
            remediation=rules.remediation,
        )

    @staticmethod
    def _report(findings: tuple[ModelValidationFinding, ...]) -> ModelValidationReport:
        return ModelValidationReport.from_findings(
            findings=tuple(
                ModelValidationFindingEmbed(**f.model_dump(mode="json"))
                for f in findings
            ),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )
