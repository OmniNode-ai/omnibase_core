# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Core handler: derive learned_patterns from code_entities.

Pipeline per entity:
    1. Filter below min_confidence or unsupported entity_type
    2. Build a deterministic pattern_signature from entity metadata
    3. SHA256 the canonicalized signature for stable lineage identity
    4. Build keywords from entity name, qualified_name, decorators, bases
    5. Build compiled_snippet for context injection
    6. Collect into ModelDerivedPattern

Supported entity types:
    class, protocol, model, function
    (import, constant, module are skipped — too generic for pattern injection)

Pattern signature format:
    "{entity_type}:{qualified_name}[:{base_classes}][:{docstring_first_line}]"

This is a pure compute handler — no I/O, no side effects.

Ticket: OMN-7863
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid

from omniintelligence.nodes.node_ast_extraction_compute.models.model_code_entity import (
    ModelCodeEntity,
)
from omniintelligence.nodes.node_code_entity_bridge_compute.models.model_input import (
    ModelCodeEntityBridgeInput,
)
from omniintelligence.nodes.node_code_entity_bridge_compute.models.model_output import (
    ModelCodeEntityBridgeOutput,
    ModelDerivedPattern,
)

logger = logging.getLogger(__name__)

# Entity types that produce meaningful learned patterns for context injection.
# import/constant/module are intentionally excluded — they are too generic.
_SUPPORTED_ENTITY_TYPES: frozenset[str] = frozenset(
    {"class", "protocol", "model", "function"}
)


def handle_code_entity_bridge(
    input_data: ModelCodeEntityBridgeInput,
) -> ModelCodeEntityBridgeOutput:
    """Derive learned_patterns from a batch of code_entities.

    Args:
        input_data: Bridge input containing entities and derivation config.

    Returns:
        ModelCodeEntityBridgeOutput with derived patterns and counters.
    """
    start = time.perf_counter()

    derived: list[ModelDerivedPattern] = []
    skipped = 0
    errors = 0

    for entity in input_data.entities:
        if entity.entity_type not in _SUPPORTED_ENTITY_TYPES:
            skipped += 1
            continue

        if entity.confidence < input_data.min_confidence:
            skipped += 1
            logger.debug(
                "Skipping entity %s (confidence=%.2f < min=%.2f, correlation_id=%s)",
                entity.qualified_name,
                entity.confidence,
                input_data.min_confidence,
                input_data.correlation_id,
            )
            continue

        try:
            pattern = _derive_pattern(entity, input_data)
            derived.append(pattern)
        except Exception:
            errors += 1
            logger.exception(
                "Failed to derive pattern for entity %s (correlation_id=%s)",
                entity.qualified_name,
                input_data.correlation_id,
            )

    duration_ms = (time.perf_counter() - start) * 1000.0

    logger.info(
        "Bridge complete: derived=%d skipped=%d errors=%d repo=%s duration_ms=%.1f correlation_id=%s",
        len(derived),
        skipped,
        errors,
        input_data.source_repo,
        duration_ms,
        input_data.correlation_id,
    )

    return ModelCodeEntityBridgeOutput(
        correlation_id=input_data.correlation_id,
        source_repo=input_data.source_repo,
        derived_patterns=derived,
        skipped_count=skipped,
        error_count=errors,
        duration_ms=duration_ms,
    )


# =============================================================================
# Internals
# =============================================================================


def _derive_pattern(
    entity: ModelCodeEntity,
    input_data: ModelCodeEntityBridgeInput,
) -> ModelDerivedPattern:
    """Derive a single ModelDerivedPattern from a ModelCodeEntity."""
    signature = _build_signature(entity)
    sig_hash = _sha256(signature)
    keywords = _extract_keywords(entity)
    snippet = _build_snippet(entity)

    return ModelDerivedPattern(
        pattern_id=uuid.uuid4(),
        pattern_signature=signature,
        signature_hash=sig_hash,
        domain_id=input_data.domain_id,
        domain_version="1.0",
        confidence=entity.confidence,
        keywords=keywords,
        source_entity_ids=[entity.id],
        entity_type=entity.entity_type,
        project_scope=input_data.project_scope,
        canary_id=input_data.canary_id,
        compiled_snippet=snippet,
    )


def _build_signature(entity: ModelCodeEntity) -> str:
    """Build a deterministic, human-readable pattern signature.

    Format: "{entity_type}:{qualified_name}[:{bases}][:{docstring_first_line}]"

    The signature is stable across re-extractions of the same entity as long
    as the qualified name and bases do not change.
    """
    parts = [entity.entity_type, entity.qualified_name]

    if entity.bases:
        parts.append(",".join(sorted(entity.bases)))

    if entity.docstring:
        first_line = entity.docstring.splitlines()[0].strip()
        if first_line:
            # Truncate to 120 chars to keep signatures bounded
            parts.append(first_line[:120])

    return ":".join(parts)


def _sha256(text: str) -> str:
    """Compute SHA256 of the canonicalized (lowercased, stripped) text."""
    canonical = text.strip().lower()
    return hashlib.sha256(canonical.encode()).hexdigest()


def _extract_keywords(entity: ModelCodeEntity) -> list[str]:
    """Extract searchable keywords from entity metadata."""
    seen: set[str] = set()
    kws: list[str] = []

    def _add(token: str) -> None:
        token = token.strip().lower()
        if token and token not in seen:
            seen.add(token)
            kws.append(token)

    _add(entity.entity_name)

    # Split qualified_name on dots for individual module/class/function tokens
    for part in entity.qualified_name.split("."):
        _add(part)

    for base in entity.bases:
        _add(base)

    for dec in entity.decorators:
        _add(dec)

    # Method names (list of dicts with "name" key)
    for method in entity.methods:
        if isinstance(method, dict) and "name" in method:
            _add(str(method["name"]))

    if entity.source_repo:
        _add(entity.source_repo)

    return kws


def _build_snippet(entity: ModelCodeEntity) -> str | None:
    """Build a concise context-injection snippet from entity metadata.

    Returns None when there is insufficient metadata to produce a useful snippet.
    """
    lines: list[str] = []

    if entity.entity_type in {"class", "protocol", "model"}:
        base_str = f"({', '.join(entity.bases)})" if entity.bases else ""
        lines.append(f"class {entity.entity_name}{base_str}:")
        if entity.docstring:
            first_line = entity.docstring.splitlines()[0].strip()
            if first_line:
                lines.append(f'    """{first_line}"""')
        if entity.methods:
            for m in entity.methods[:5]:  # cap at 5 methods to keep snippet small
                if isinstance(m, dict) and "name" in m:
                    lines.append(f"    def {m['name']}(self, ...): ...")
    elif entity.entity_type == "function":
        sig = entity.signature or f"def {entity.entity_name}(...):"
        lines.append(sig)
        if entity.docstring:
            first_line = entity.docstring.splitlines()[0].strip()
            if first_line:
                lines.append(f'    """{first_line}"""')

    if not lines:
        return None

    return "\n".join(lines)


__all__ = ["handle_code_entity_bridge"]
