# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure ticket-creation admission checker: a tracker payload in, findings out (OMN-22850).

Ported rule by rule from the omniclaude ticket-creation guard (rules 1-7, 10, 15 and the
lane-intake rules 11-13), which this replaces for every caller that can import the core
package. The checker performs no I/O: the payload, the lane identity and an injected
ledger-line lookup are arguments, and every vocabulary, pattern, threshold and text is a
rule row of ``contracts/ticket_creation.validation.yaml``. A row that is absent or
mistyped raises, so a broken contract refuses every payload instead of admitting them.

An UPDATE that does not touch the description is admitted. An update that writes a
description or a patch needs the current body to be judged (guard rule 9); this checker
holds none, so it refuses that update rather than assuming it clean.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from functools import lru_cache

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.ticket_creation.model_ticket_creation_check_result import (
    ModelTicketCreationCheckResult,
)
from omnibase_core.models.ticket_creation.model_ticket_creation_finding import (
    ModelTicketCreationFinding,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

__all__ = ["LedgerLineLookup", "check_ticket_creation", "rows_of"]

#: Whether a ledger file name has a non-blank line at a line number. ``None`` resolves nothing.
type LedgerLineLookup = Callable[[str, int], bool]

type _Rows = Mapping[str, ModelValidatorRule]
type _Unit = tuple[str, str | None, str | None]


def _contract_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


def rows_of(contract: ModelValidatorSubcontract) -> dict[str, ModelValidatorRule]:
    """The rule rows of ``contract`` by rule id."""
    return {rule.rule_id: rule for rule in contract.rules}


def _row(rows: _Rows, rule_id: str) -> ModelValidatorRule:
    row = rows.get(rule_id)
    if row is None:
        raise _contract_error(f"the contract has no rule row {rule_id!r}")
    return row


@lru_cache(maxsize=512)
def _re(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise _contract_error(f"pattern {pattern!r} is not a regex ({exc})") from exc


def _res(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    return tuple(_re(p) for p in patterns)


def _finding(
    rows: _Rows, code: str, field: str, variant: str = "", **fmt: str
) -> tuple[ModelTicketCreationFinding, ...]:
    """The finding of rule ``code``, or nothing when the contract disables that rule."""
    row = _row(rows, code)
    if not row.enabled:
        return ()
    suffix = f"_{variant}" if variant else ""
    return (
        ModelTicketCreationFinding(
            code=code,
            field=field,
            reason=rule_string(row, f"message{suffix}").format(**fmt),
            fix=rule_string(row, f"fix{suffix}").format(**fmt),
        ),
    )


def _is_present(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _quote(text: str, limit: int) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"


def _render_ids(ids: tuple[str, ...]) -> str:
    def key(value: str) -> tuple[str, int]:
        digits = "".join(c for c in value if c.isdigit())
        return (value.rstrip("0123456789"), int(digits) if digits else 0)

    return ", ".join(sorted(ids, key=key)) or "(none configured)"


# -- the binding line (rule 3), the epic marker (rule 1), the residual title (rule 4) --


def _declares_epic(description: str, markers: tuple[str, ...]) -> bool:
    wanted = {m.lower() for m in markers}
    return any(line.strip().lower() in wanted for line in description.splitlines())


def _binding_kind(description: str, rows: _Rows) -> str | None:
    """The declared form id of the strongest binding line, or ``None``."""
    row = _row(rows, "binding_grammar")
    line = _re(rule_string(row, "line_pattern"))
    norm_patterns = rule_strings(row, "normalization_patterns")
    norm_replacements = rule_strings(row, "normalization_replacements")
    form_ids = rule_strings(row, "form_ids")
    form_patterns = rule_strings(row, "form_patterns")
    if len(norm_patterns) != len(norm_replacements) or len(form_ids) != len(
        form_patterns
    ):
        raise _contract_error("binding_grammar parallel lists differ in length")
    exempting = rule_string(row, "residual_exempting_form_id")
    vocabularies = {
        rule_string(row, "criterion_form_id"): {
            i.upper() for i in rule_strings(row, "criterion_ids")
        },
        rule_string(row, "invariant_form_id"): {
            i.upper() for i in rule_strings(row, "invariant_ids")
        },
    }

    def normalize(binding: str) -> str:
        for pattern, replacement in zip(norm_patterns, norm_replacements, strict=True):
            binding = _re(pattern).sub(replacement, binding)
        return binding.strip()

    kinds: set[str] = set()
    for match in line.finditer(description):
        binding = normalize(match.group("binding"))
        if not binding:
            continue
        form = next(
            (
                fid
                for fid, fpat in zip(form_ids, form_patterns, strict=True)
                if _re(fpat).match(binding)
            ),
            None,
        )
        if form is None:
            continue
        allowed = vocabularies.get(form)
        if allowed is not None and binding.upper() not in allowed:
            continue
        kinds.add(form)
    for preferred in (exempting, *form_ids):
        if preferred in kinds:
            return preferred
    return None


def _word_hits(terms: tuple[str, ...], text: str) -> list[str]:
    return [t for t in terms if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", text, re.I)]


# -- the criteria section (rules 6, 7, 10) ---------------------------------------------


def _is_heading(line: str, rows: _Rows) -> bool:
    row = _row(rows, "criteria_parsing")
    headings = {h.lower() for h in rule_strings(row, "acceptance_criteria_headings")}
    text = line.strip()
    if not text:
        return False
    text = text.lstrip(rule_string(row, "heading_marker")).strip()
    text = text.strip(rule_string(row, "emphasis_chars")).strip()
    text = _re(rule_string(row, "heading_enum_pattern")).sub("", text).strip()
    text = text.rstrip(rule_string(row, "heading_suffix")).strip()
    folded = text.lower()
    if folded in headings:
        return True
    qualifier = _re(rule_string(row, "trailing_qualifier_pattern"))
    return qualifier.sub("", folded).strip() in headings


def _item_text(line: str, rows: _Rows) -> str | None:
    row = _row(rows, "criteria_parsing")
    listed = _re(rule_string(row, "list_item_pattern")).match(line)
    if listed:
        return (
            _re(rule_string(row, "task_marker_pattern"))
            .sub("", listed.group(1))
            .strip()
        )
    ac = _re(rule_string(row, "ac_item_pattern")).match(line)
    if ac:
        lead, token, rest = ac.groups()
        text = f"{token}{rest}".strip()
        if lead:
            text = (
                _re(rule_string(row, "trailing_emphasis_pattern")).sub("", text).strip()
            )
        return text
    return None


def _criteria_items(description: str, rows: _Rows) -> list[str]:
    lines = description.splitlines()
    if not any(_is_heading(line, rows) for line in lines):
        return []
    marker = rule_string(_row(rows, "criteria_parsing"), "heading_marker")
    items: list[list[str]] = []
    in_section = False
    open_item = False
    for line in lines:
        if _is_heading(line, rows):
            in_section, open_item = True, False
            continue
        if not in_section:
            continue
        if line.lstrip().startswith(marker):
            break
        text = _item_text(line, rows)
        if text is not None:
            if text:
                items.append([text])
                open_item = True
            else:
                open_item = False
            continue
        if not line.strip():
            continue
        if open_item:
            items[-1].append(line.strip())
    joined = (" ".join(parts).strip() for parts in items)
    return [item for item in joined if item]


def _falsifier_of(item: str, rows: _Rows) -> str | None:
    row = _row(rows, "criteria_parsing")
    strip = rule_string(row, "falsifier_tail_strip")
    folded = item.lower()
    best: str | None = None
    for marker in (m.lower() for m in rule_strings(row, "falsifier_markers")):
        start = folded.rfind(marker)
        if start == -1:
            continue
        tail = item[start + len(marker) :].strip(strip)
        if tail and (best is None or start > folded.rfind(best.lower())):
            best = tail
    return best


def _units(description: str, rows: _Rows) -> list[_Unit]:
    """``(canonical text, label or None, falsifier or None)`` per criterion."""
    label_re = _re(
        rule_string(_row(rows, "criteria_parsing"), "criterion_label_pattern")
    )
    units: list[_Unit] = []
    for item in _criteria_items(description, rows):
        text = " ".join(item.split())
        match = label_re.match(text)
        label = (
            f"{match.group(1).upper()}{match.group(2)}{match.group(3)}"
            if match
            else None
        )
        units.append((text, label, _falsifier_of(item, rows)))
    return units


def _criterion_findings(
    description: str, rows: _Rows
) -> tuple[ModelTicketCreationFinding, ...]:
    units = _units(description, rows)
    if not units:
        return ()
    parsing = _row(rows, "criteria_parsing")
    limit = rule_int(parsing, "max_quoted")
    named_max = rule_int(parsing, "max_named")
    merge = _row(rows, "merge_state_falsifier_on_behaviour_criterion")
    state = _res(rule_strings(merge, "state_criterion_markers"))
    behaviour = _res(rule_strings(merge, "behaviour_criterion_markers"))
    merge_state = _res(rule_strings(merge, "merge_state_falsifier_markers"))
    runners = tuple(w.lower() for w in rule_strings(merge, "behaviour_runner_words"))
    unfalsified: list[str] = []
    offenders: list[tuple[str, str]] = []
    for text, _label, falsifier in units:
        if falsifier is None:
            unfalsified.append(text)
            continue
        behaviour_shaped = not any(m.search(text) for m in state) and any(
            m.search(text) for m in behaviour
        )
        reads_merge_state = any(m.search(falsifier) for m in merge_state) and not any(
            re.search(rf"(?<!\w){re.escape(w)}(?!\w)", falsifier.lower())
            for w in runners
        )
        if behaviour_shaped and reads_merge_state:
            offenders.append((text, falsifier))
    out: tuple[ModelTicketCreationFinding, ...] = ()
    if unfalsified:
        named = unfalsified[:named_max]
        quoted = "; ".join(f'"{_quote(t, limit)}"' for t in named)
        if len(unfalsified) > len(named):
            quoted += f"; and {len(unfalsified) - len(named)} more"
        out += _finding(
            rows,
            "unfalsified_criterion",
            "description",
            count=str(len(unfalsified)),
            total=str(len(units)),
            quoted=quoted,
            grammar=rule_string(
                _row(rows, "unfalsified_criterion"), "falsifier_grammar"
            ),
        )
    for text, falsifier in offenders[:named_max]:
        out += _finding(
            rows,
            "merge_state_falsifier_on_behaviour_criterion",
            "description",
            item=_quote(text, limit),
            falsifier=_quote(falsifier, limit),
            runners=", ".join(runners[:5]),
        )
    return out


def _labelled_findings(
    description: str, binding: str | None, rows: _Rows
) -> tuple[ModelTicketCreationFinding, ...]:
    row = _row(rows, "missing_acceptance_criteria")
    epic = rule_strings(_row(rows, "missing_parent"), "epic_markers")
    if _declares_epic(description, epic):
        return ()
    if binding is not None and binding in rule_strings(row, "exempt_binding_forms"):
        return ()
    minimum = rule_int(row, "min_labelled_criteria")
    grammar = rule_string(row, "labelled_grammar")
    forms = rule_string(row, "label_forms")
    units = _units(description, rows)
    if not units:
        headings = ", ".join(
            sorted(
                rule_strings(
                    _row(rows, "criteria_parsing"), "acceptance_criteria_headings"
                )
            )
        )
        return _finding(
            rows,
            "missing_acceptance_criteria",
            "description",
            headings=headings,
            grammar=grammar,
        )
    if sum(1 for _t, label, _f in units if label is not None) >= minimum:
        return ()
    return _finding(
        rows,
        "unlabelled_criteria",
        "description",
        total=str(len(units)),
        forms=forms,
        minimum=str(minimum),
        grammar=grammar,
    )


# -- the probe line (rule 5) ----------------------------------------------------------


def _probe_findings(
    description: str, rows: _Rows
) -> tuple[ModelTicketCreationFinding, ...]:
    row = _row(rows, "missing_probe_line")
    separator = rule_string(row, "probe_separator")
    grammar = rule_string(row, "probe_grammar")
    candidates = [
        m.group("probe").strip()
        for m in _re(rule_string(row, "probe_line_pattern")).finditer(description)
    ]
    candidates = [c for c in candidates if c]
    if not candidates:
        return _finding(rows, "missing_probe_line", "description", grammar=grammar)
    for candidate in candidates:
        head, sep, tail = candidate.partition(separator)
        if sep and head.strip() and tail.strip():
            return ()
    return _finding(
        rows,
        "malformed_probe_line",
        "description",
        separator=separator,
        grammar=grammar,
    )


# -- the diagnosis citation (rule 15) -------------------------------------------------


def _label_names(tool_input: Mapping[str, object], rows: _Rows) -> set[str]:
    raw: object = None
    for key in rule_strings(_row(rows, "payload_fields"), "label_fields"):
        if key in tool_input:
            raw = tool_input[key]
            break
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return set()
    return {x.strip().lower() for x in raw if isinstance(x, str) and x.strip()}


def _diagnosis_findings(
    tool_input: Mapping[str, object],
    title: str,
    description: str,
    rows: _Rows,
    ledger: LedgerLineLookup | None,
) -> tuple[ModelTicketCreationFinding, ...]:
    row = _row(rows, "missing_diagnosis")
    signals = _word_hits(rule_strings(row, "defect_title_terms"), title)
    labels = {n.lower() for n in rule_strings(row, "defect_label_names")}
    signals.extend(sorted(_label_names(tool_input, rows) & labels))
    if not signals:
        return ()
    strip = rule_string(row, "citation_strip_chars")
    cited = [
        text
        for m in _re(rule_string(row, "line_pattern")).finditer(description)
        if (text := m.group("citation").replace(strip, "").strip())
    ]
    patterns = rule_strings(row, "citation_patterns")
    resolutions = rule_strings(row, "citation_resolutions")
    spellings = " | ".join(f"'{e}'" for e in rule_strings(row, "citation_examples"))

    def resolves(citation: str) -> bool:
        for pattern, resolution in zip(patterns, resolutions, strict=True):
            match = _re(pattern).match(citation)
            if match is None:
                continue
            if resolution == "shape":
                return True
            return ledger is not None and ledger(
                match.group("path"), int(match.group("line"))
            )
        return False

    if any(resolves(c) for c in cited):
        return ()
    if not cited:
        return _finding(
            rows,
            "missing_diagnosis",
            "description",
            signals=", ".join(signals),
            spellings=spellings,
        )
    return _finding(
        rows,
        "unresolvable_diagnosis",
        "description",
        cited=", ".join(f"'{c}'" for c in cited),
        spellings=spellings,
    )


# -- the lane intake rules (11-13) ----------------------------------------------------


def _lane_findings(
    tool_input: Mapping[str, object], lane: str, rows: _Rows
) -> tuple[ModelTicketCreationFinding, ...]:
    intake = _row(rows, "lane_intake")
    label = rule_string(intake, "label")
    prefix = rule_string(intake, "stamp_prefix")
    lane = lane.strip()
    out: tuple[ModelTicketCreationFinding, ...] = ()
    if not lane:
        out += _finding(rows, "lane_identity_missing", "lane")
    if label.lower() not in _label_names(tool_input, rows):
        out += _finding(rows, "lane_label_missing", "labels", label=label)
    description = tool_input.get(
        rule_string(_row(rows, "payload_fields"), "description_field")
    )
    first = (
        description.split("\n", 1)[0].strip() if isinstance(description, str) else ""
    )
    stamp = f"{prefix} {lane}"
    if lane and first != stamp:
        out += _finding(
            rows, "lane_stamp_missing", "description", first=first[:80], stamp=stamp
        )
    return out


# -- the entry point ------------------------------------------------------------------


def check_ticket_creation(
    tool_input: object,
    contract: ModelValidatorSubcontract,
    *,
    lane: str | None = None,
    ledger_line_exists: LedgerLineLookup | None = None,
) -> ModelTicketCreationCheckResult:
    """Every failing admission rule for one ``save_issue`` payload; no finding admits it.

    ``lane`` is ``None`` for a payload that is not from a lane or node (the lane-intake
    rules do not run) and the filing lane's identity otherwise (``""`` is a lane context
    that declares none). ``ledger_line_exists`` resolves a ledger ``Diagnosis:`` citation;
    absent, such a citation resolves nothing.
    """
    rows = rows_of(contract)
    fields = _row(rows, "payload_fields")
    if not isinstance(tool_input, Mapping):
        return ModelTicketCreationCheckResult(
            findings=_finding(rows, "unevaluable", "tool_input", "tool_input")
        )
    id_field = rule_string(fields, "id_field")
    description_field = rule_string(fields, "description_field")
    if id_field in tool_input:
        value = tool_input[id_field]
        if not _is_present(value):
            return ModelTicketCreationCheckResult(
                findings=_finding(
                    rows, "unevaluable", id_field, "id", value=repr(value)
                )
            )
        touches_body = (
            rule_string(fields, "patch_field") in tool_input
            or tool_input.get(description_field) is not None
        )
        if not touches_body:
            return ModelTicketCreationCheckResult()
        return ModelTicketCreationCheckResult(
            findings=_finding(rows, "criterion_text_unreadable", description_field)
        )

    findings: tuple[ModelTicketCreationFinding, ...] = ()
    title_field = rule_string(fields, "title_field")
    title = tool_input.get(title_field)
    if not _is_present(title):
        findings += _finding(
            rows, "unevaluable", title_field, "title", value=repr(title)
        )
        title = ""
    assert isinstance(title, str)
    raw = tool_input.get(description_field)
    readable = raw is None or isinstance(raw, str)
    description = raw if isinstance(raw, str) else ""
    if not readable:
        findings += _finding(
            rows,
            "unevaluable",
            description_field,
            "description",
            value=type(raw).__name__,
        )

    parent = _row(rows, "missing_parent")
    markers = rule_strings(parent, "epic_markers")
    parent_field = rule_string(fields, "parent_field")
    if not _is_present(tool_input.get(parent_field)) and not _declares_epic(
        description, markers
    ):
        findings += _finding(
            rows, "missing_parent", parent_field, markers=" | ".join(markers)
        )
    if any(
        _is_present(tool_input.get(f)) for f in rule_strings(fields, "project_fields")
    ):
        findings += _finding(rows, "project_set", "project")

    binding_row = _row(rows, "binding_grammar")
    binding = _binding_kind(description, rows) if readable else None
    if binding is None:
        examples = rule_strings(binding_row, "form_examples")
        findings += _finding(
            rows,
            "missing_gate_line",
            description_field,
            summary="Gate: <" + " | ".join(examples) + ">",
            criterion_ids=_render_ids(rule_strings(binding_row, "criterion_ids")),
            invariant_ids=_render_ids(rule_strings(binding_row, "invariant_ids")),
        )
    exempting = rule_string(binding_row, "residual_exempting_form_id")
    if binding != exempting:
        hits = _word_hits(
            rule_strings(_row(rows, "residual_title"), "residual_title_terms"), title
        )
        if hits:
            ids = rule_strings(binding_row, "form_ids")
            example = rule_strings(binding_row, "form_examples")[ids.index(exempting)]
            findings += _finding(
                rows,
                "residual_title",
                title_field,
                hits=", ".join(hits),
                exempt_example=example,
            )

    if readable:
        probe = _row(rows, "missing_probe_line")
        in_progress = {
            n.lower() for n in rule_strings(probe, "in_progress_state_names")
        }
        names = {
            str(tool_input.get(f, "")).strip().lower()
            for f in rule_strings(fields, "state_fields")
        }
        if names & in_progress:
            findings += _probe_findings(description, rows)
        findings += _criterion_findings(description, rows)
        findings += _labelled_findings(description, binding, rows)
        findings += _diagnosis_findings(
            tool_input, title, description, rows, ledger_line_exists
        )
    if lane is not None:
        findings += _lane_findings(tool_input, lane, rows)
    return ModelTicketCreationCheckResult(findings=findings)
