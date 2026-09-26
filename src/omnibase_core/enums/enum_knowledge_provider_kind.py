# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic knowledge-provider classification (OMN-18372).

Context sections are assembled from several backends, and until this enum
existed the backend was recorded as a free string that in practice carried a
vendor name. That made the vendor part of the type: a model field's documented
example named one product, and every consumer that branched on the string was
coupled to it.

The split this enum introduces is the correction. The KIND — what class of
backend produced an item — is a closed, vendor-neutral set and belongs in the
type. The vendor identity is DATA the adapter supplies alongside it, in a
sibling free-text field, and it is the only place a product name may appear.
An adapter can be swapped without changing a model, a contract, or a
consumer's branch.

There is deliberately no ``UNKNOWN`` member. An assembler always knows which
class of backend it called; a fallback value would let a caller record that it
did not, and every downstream reader would then have to treat the field as
optional.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumKnowledgeProviderKind(StrEnum):
    """The class of backend that produced a context item."""

    CODE_INDEX = "code_index"
    """An index over source code, answering structural and architectural
    questions about a repository."""

    DOCUMENT_STORE = "document_store"
    """A document corpus with semantic retrieval over its contents."""

    DECISION_RECORD = "decision_record"
    """A store of architecture decision records."""

    ANTIPATTERN_REGISTRY = "antipattern_registry"
    """A registry of known antipatterns and the rules that detect them."""

    LEARNING_STORE = "learning_store"
    """A store of prior learnings matched by similarity to the current task."""

    DEPENDENCY_GRAPH = "dependency_graph"
    """A graph of dependencies between packages, modules, or nodes."""

    ISSUE_TRACKER = "issue_tracker"
    """A ticketing system supplying issue and epic context."""

    VERSION_CONTROL = "version_control"
    """A version-control history supplying commit and authorship context."""


__all__ = ["EnumKnowledgeProviderKind"]
